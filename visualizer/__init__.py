import pygtk
pygtk.require('2.0')
import gtk
import gobject
import argparse
import ConfigParser as configparser
import sys, os
from os.path import dirname, join
import re
import traceback
import time
from select import select
import errno
import socket
from functools import wraps
from signal import signal, SIGUSR1, SIGINT, SIGHUP
import itertools
import logging

import consumer, plugin
from _canvas import Canvas

re_attrib = re.compile(r'\$[{]([^}]*)[}]')

def ConfigParserWrapper(func):
    @wraps(func)
    def outer(x):
        def inner(self, section, option, default=None):
            try:
                return func(self, section, option)
            except configparser.NoOptionError:
                if default is not None:
                    return default
                raise
        return inner
    return outer

class ConfigParser(configparser.SafeConfigParser):
    @ConfigParserWrapper(configparser.SafeConfigParser.get)
    def get(self): pass

    @ConfigParserWrapper(configparser.SafeConfigParser.getint)
    def getint(self): pass

    @ConfigParserWrapper(configparser.SafeConfigParser.getfloat)
    def getfloat(self): pass

    @ConfigParserWrapper(configparser.SafeConfigParser.getboolean)
    def getboolean(self): pass

class Main:
    cursor_timeout = 2000 # delay in ms until hiding cursor
    transition = 15

    def __init__(self, config):
        self.log = logging.getLogger('main')
        builder = gtk.Builder()
        builder.add_from_file(join(dirname(__file__),'main.ui'))
        builder.connect_signals(self)
        self.window = builder.get_object('main')
        self.notebook = builder.get_object('notebook1')
        self.cursor_timer = None

        gtk.accel_map_add_entry("<visualizer>/quit", gtk.accelerator_parse("q")[0], gtk.gdk.CONTROL_MASK)
        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<visualizer>/quit", self.quit)
        self.window.add_accel_group(self.accel_group)
        signal(SIGINT, self.handle_sigint)

        self.area = builder.get_object('area')
        gl_config = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB | gtk.gdkgl.MODE_DEPTH | gtk.gdkgl.MODE_DOUBLE)

        # config defaults
        self.transition = config.getint('general', 'transition', Main.transition)
        self.consumers = []

        self.fullscreen = False
        try:
            self.fullscreen = config.getboolean('general', 'fullscreen')
        except:
            pass

        # cursor
        pix = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        self.cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)

        # guess resolution
        size = (800,600)
        if self.fullscreen:
            dgd = gtk.gdk.display_get_default()
            gsd = dgd.get_default_screen()
            size = (gsd.get_width(), gsd.get_height())

        # setup visualizer
        self.log.debug('Creating canvas')
        self.visualizer = Canvas(gl_config, size=size, transition_time=self.transition)
        self.visualizer.connect('motion_notify_event', self.cursor_show)
        self.area.pack_start(self.visualizer)
        self.window.show_all()

        if self.fullscreen:
            self.window.fullscreen()
            self.notebook.set_show_tabs(False)
            self.visualizer.window.set_cursor(self.cursor)

        # Process events so window is fully created after this point.
        gtk.main_iteration(True)
        while gtk.events_pending():
            gtk.main_iteration(False)

        # parse rest of config.
        self.log.debug('Parsing config')
        self.parse_config(config)

        # retrieve datasets from consumers
        self.dataset = {}
        for con in self.consumers:
            con.reconnect()
            for ds in con.dataset:
                self.dataset[ds] = con

        if len(self.consumers) > 0:
            print 'Available consumers'
            print '-------------------'
            for con in self.consumers:
                print ' *', con
            print

        if len(self.dataset) > 0:
            print 'Available datasets'
            print '------------------'
            for k,v in self.dataset.iteritems():
                print ' * %s: %s' % (k, v)
            print

        # Initialize plugins. Must be done after fullscreen-mode so variables depending on size will work.
        self.visualizer.dataset = self.dataset # fulhack
        self.visualizer.init_plugins()

        signal(SIGHUP, self.reload)
        gobject.idle_add(self.expire)

    def reload(self, signum, frame):
        print 'herp derp, should reload config...'

    def handle_sigint(self, *args):
        self.quit()

    def quit(self, *args):
        self.log.debug('Application quit')

        # Stop GTK main loop
        gtk.main_quit()

    def destroy(self, widget, data=None):
        gtk.quit()

    def on_main_window_state_event(self, window, event):
        self.fullscreen = bool(gtk.gdk.WINDOW_STATE_FULLSCREEN & event.new_window_state)

    def on_area_button_press_event(self, widget, event):
        if event.type != gtk.gdk._2BUTTON_PRESS:
            return

        if self.fullscreen:
            self.window.unfullscreen()
            self.visualizer.window.set_cursor(None)
            self.notebook.set_show_tabs(True)
        else:
            self.window.fullscreen()
            self.notebook.set_show_tabs(False)
            self.cursor_timer = gobject.timeout_add(self.cursor_timeout, self.cursor_hide)

    def expire(self, *args):
        try:
            timeout = 0.1
            if self.visualizer.transition_enabled:
                timeout = 0

            try:
                rl,wl,xl = select([x for x in self.consumers if x.fileno() is not None],[],[],timeout)
            except Exception, e:
                if e.args[0] == errno.EINTR:
                    # reloading?
                    return True
                raise

            # pull data from connected consumers
            for con in rl:
                try:
                    con.pull()
                except socket.error:
                    traceback.print_exc()
                    con.sock = None
                except:
                    traceback.print_exc()

            # try to reconnect disconnected consumers
            for con in [x for x in self.consumers if x.fileno() is None]:
                con.reconnect()

        except:
            traceback.print_exc()
        finally:
            return True

    def cursor_hide(self):
        if not self.fullscreen:
            return

        self.visualizer.window.set_cursor(self.cursor)

    def cursor_show(self, window, event):
        if not self.fullscreen:
            return

        if self.visualizer.window.get_cursor() is None:
            if self.cursor_timer:
                gobject.source_remove(self.cursor_timer)
            self.cursor_timer = gobject.timeout_add(self.cursor_timeout, self.cursor_hide)
        self.visualizer.window.set_cursor(None)

    def add_consumer(self, consumer):
        self.consumers.append(consumer)

    def parse_attrib(self, attrib):
        global re_attrib

        local = {
            'width': float(self.visualizer.size[0]),
            'height': float(self.visualizer.size[1]),
        }

        def sub(match):
            key = match.group(1)
            return str(eval(key, {}, local))

        d = {}
        for k,v in attrib.iteritems():
            d[k] = re_attrib.sub(sub, v)
        return d

    def parse_config(self, config):
        pattern = re.compile('(?:(\w+):)?(\w+)(?:/(\w+))?')
        for section in config.sections():
            x = pattern.match(section)
            if x is None:
                self.log.error('Failed to parse section "%s", ignoring.', section)
                continue
            ns, key, index = x.groups()
            if ns is None: ns = key
            if index is None: index = '0'
            a = self.parse_attrib(dict(config.items(section)))

            if ns == 'consumer':
                con = consumer.Consumer(a['host'], a['port'])
                self.add_consumer(con)

            if ns == 'process':
                con = consumer.Process(a['command'], a['dataset'])
                self.add_consumer(con)

            if ns == 'plugin':
                self.visualizer.add_plugin(key, index, a)

def usage():
    return """\
Plugins:
{plugin}

For help about a specific plugin use -H NAME
""".format(plugin='\n'.join(['  - %s: %s' % x for x in plugin.available()]))

def run():
    print >> sys.stderr
    print >> sys.stderr, '#' * 60
    print >> sys.stderr, 'DPMI Visualizer 0.7'
    print >> sys.stderr, '(c) 2011 David Sveningsson <dsv@bth.se>'
    print >> sys.stderr, 'GNU GPLv3'
    print >> sys.stderr

    parser = argparse.ArgumentParser(epilog=usage(), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-f', '--config', type=argparse.FileType('r'), default=None, help='Configuration-file')
    parser.add_argument('-H', dest='plugin', type=str, metavar='PLUGIN', help="Show help for plugin")
    args = parser.parse_args()

    if args.plugin:
        plugin.usage(args.plugin)
        sys.exit(0)

    # setup logging
    filename = 'visualizer.log'
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('[%(name)-12s] [%(levelname)-8s] %(message)s'))
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s [%(name)-12s] [%(levelname)-8s] %(message)s', '%a, %d %b %Y %H:%M%S %z'))
    log = logging.getLogger('')
    log.addHandler(ch)
    log.addHandler(fh)
    log.setLevel(logging.DEBUG)
    logging.getLogger('OpenGL.extensions').setLevel(logging.WARNING)
    log.debug('Visualizer started')

    if not args.config:
        if not os.path.exists('visualizer.conf'):
            print >> sys.stderr, 'No config-file specified and "visualizer.conf" not found'
            sys.exit(1)
        args.config = open('visualizer.conf')

    # parse config
    config = ConfigParser()
    config.readfp(args.config)

    pidlock = config.get('general', 'lockfile', '/var/run/visualizer.lock')
    if os.path.exists(pidlock):
        print >> sys.stderr, pidlock, 'exists, if the visualizer isn\'t running manually remove the file before continuing'
        sys.exit(1)

    with open(pidlock, 'w') as pid:
        pid.write(str(os.getpid()))

    try:
        main = Main(config)
        gtk.main()
    finally:
        os.unlink(pidlock)

    log.debug('Visualizer stopped')
