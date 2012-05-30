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

import consumer
from _canvas import Canvas

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
        builder = gtk.Builder()
        builder.add_from_file(join(dirname(__file__),'main.ui'))
        builder.connect_signals(self)
        self.window = builder.get_object('main')
        self.notebook = builder.get_object('notebook1')
        self.cursor_timer = None

        # ctrl+q shortcut
        def quit(*args, **kwargs):
            gtk.main_quit()
        gtk.accel_map_add_entry("<visualizer>/quit", gtk.accelerator_parse("q")[0], gtk.gdk.CONTROL_MASK)
        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<visualizer>/quit", quit)
        self.window.add_accel_group(self.accel_group)
        signal(SIGINT, quit)

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

        # retrieve consumers from config
        pattern = re.compile('(\w+:)?(\w+)(/[0-9]+)?') # might want to consider lookahead
        for section in config.sections():
            x = pattern.match(section)
            if x is None:
                print >> sys.stderr, 'Failed to parse section "%s", ignoring.' % section
                continue
            ns, key, index = x.groups()
            if ns is None:
                ns = key
            else:
                ns = ns[:-1] # strip trailing ':'

            if ns == 'consumer':
                host = config.get(section, 'host')
                port = config.getint(section, 'port')

                con = consumer.Consumer(host, port)
                self.consumers.append(con)

                try:
                    con.connect()
                except socket.error, e:
                    if e.errno != 111: # connection refused
                        traceback.print_exc()
                        print >> sys.stderr, 'Consumer %s:%d' % (host, port)
                except:
                    traceback.print_exc()
                    print >> sys.stderr, 'Consumer %s:%d' % (host, port)

        print 'Available consumers'
        print '-------------------'
        for con in self.consumers:
            print ' *', con
        print

        # retrieve datasets from consumers
        self.dataset = {}
        for con in self.consumers:
            for ds in con.dataset:
                self.dataset[ds] = con

        print 'Available datasets'
        print '------------------'
        for k,v in self.dataset.iteritems():
            print ' *', k, v
        print

        self.n = 0
        def foo(self, *args):
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

        # cursor
        pix = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        self.cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)

        # setup visualizer
        self.visualizer = Canvas(gl_config, size=(800, 600), transition_time=self.transition)

        # fulhack
        self.visualizer.dataset = self.dataset

        # load plugins
        pattern = re.compile('(\w+:)?(\w+)(/[0-9]+)?') # might want to consider lookahead
        for section in config.sections():
            x = pattern.match(section)
            if x is None:
                print >> sys.stderr, 'Failed to parse section "%s", ignoring.' % section
                continue
            ns, key, index = x.groups()
            if ns is None:
                ns = key
            else:
                ns = ns[:-1] # strip trailing ':'

            if ns == 'plugin':
                try:
                    self.visualizer.add_module(key, **dict(config.items(section)))
                except Exception, e:
                    print >> sys.stderr, e

        #self.visualizer.add_module('overview')
        #self.visualizer.add_module('overview_stats')
        #self.visualizer.add_module('http_host')
        #self.visualizer.add_module('bitrate')
        #self.visualizer.add_module('utilization')
        #self.visualizer.add_module('stub')
        #self.visualizer.add_module('static', filename='info.txt', text_font="Verdana 12")
        self.visualizer.connect('motion_notify_event', self.cursor_show)

        self.area.pack_start(self.visualizer)
        self.window.show_all()

        if self.fullscreen:
            self.window.fullscreen()
            self.notebook.set_show_tabs(False)
            self.visualizer.window.set_cursor(self.cursor)

        signal(SIGHUP, self.reload)

        gobject.idle_add(foo, self)


    def reload(self, signum, frame):
        print 'herp derp, should reload config...'

    def destroy(self, widget, data=None):
        gtk.main_quit()

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

def run():
    print >> sys.stderr
    print >> sys.stderr, '#' * 60
    print >> sys.stderr, 'DPMI Visualizer 0.7'
    print >> sys.stderr, '(c) 2011 David Sveningsson <dsv@bth.se>'
    print >> sys.stderr, 'GNU GPLv3'
    print >> sys.stderr

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--config', type=argparse.FileType('r'), default=None, help='Configuration-file')
    args = parser.parse_args()

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
