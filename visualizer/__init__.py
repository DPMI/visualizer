import pygtk
pygtk.require('2.0')
import gtk
import gobject
import argparse
import sys, os
from os.path import dirname, join
import re
import traceback
import time
from select import select
import errno
import socket
from signal import signal, SIGUSR1, SIGINT, SIGHUP
import itertools
import logging
import config

import consumer, plugin
from _canvas import Canvas
from statistics import Statistics

re_attrib = re.compile(r'\$[{]([^}]*)[}]')

class Main:
    cursor_timeout = 2000 # delay in ms until hiding cursor

    def __init__(self, config, filename):
        self.log = logging.getLogger('main')
        self.cursor_create()
        self.consumers = []
        self.dataset = {}
        self.filename = filename

        # config defaults
        rows = config.getint('general/rows', 3)
        self.fullscreen = config.getboolean('general/fullscreen', False)

        # Create window and get widget handles.
        builder = gtk.Builder()
        builder.add_from_file(join(dirname(__file__),'main.ui'))
        builder.connect_signals(self)
        self.window = builder.get_object('main')
        self.notebook = builder.get_object('notebook1')
        self.area = builder.get_object('area')

        # Setup keyboard shortcuts
        gtk.accel_map_add_entry("<visualizer>/quit", gtk.accelerator_parse("q")[0], gtk.gdk.CONTROL_MASK)
        self.accel_group = gtk.AccelGroup()
        self.accel_group.connect_by_path("<visualizer>/quit", self.quit)
        self.window.add_accel_group(self.accel_group)

        # guess resolution
        size = (800,600)
        if self.fullscreen:
            dgd = gtk.gdk.display_get_default()
            gsd = dgd.get_default_screen()
            size = (gsd.get_width(), gsd.get_height())

        # setup visualizer
        self.log.debug('Creating canvas')
        self.visualizer = Canvas(size=size, rows=rows)
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

        # Setup statistics
        self.stats = Statistics()
        self.add_consumer(self.stats)
        gobject.timeout_add(1000, self.update_stats)

        # retrieve datasets from consumers
        self.load_dataset()

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
        self.visualizer.init_all_plugins()

        # Setup signal and event handling
        signal(SIGHUP, self.handle_sighup)
        signal(SIGINT, self.handle_sigint)
        gobject.idle_add(self.expire)

    def load_dataset(self):
        self.dataset = {}
        for con in self.consumers:
            try:
                con.connect()
            except socket.error:
                pass
            except:
                traceback.print_exc()

            for ds in con.dataset:
                self.dataset[ds] = con

    def handle_sighup(self, signum, frame):
        self.log.info('Reloading config')
        self.consumers = []
        self.dataset = {}
        self.visualizer.dataset = []
        self.visualizer.plugins = []

        config = ConfigParser()
        config.read(self.filename)
        self.parse_config(config)
        self.load_dataset()
        self.visualizer.dataset = self.dataset # fulhack
        self.visualizer.rows = config.getint('general', 'rows', Main.rows)
        self.visualizer.init_all_plugins()
        self.visualizer.resize()
        self.visualizer.write_message('Reloaded config')

    def handle_sigint(self, *args):
        self.quit()

    def quit(self, *args):
        self.log.debug('Application quit')

        # Stop GTK main loop
        gtk.main_quit()

    def update_stats(self, *args):
        num_consumers = len(self.consumers)
        connected_consumers = len([x for x in self.consumers if x.fileno()])

        self.stats.update(
            consumers=(connected_consumers, num_consumers),
            framerate=self.visualizer.framerate,
        )
        return True

    def destroy(self, widget, data=None):
        self.quit()

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
            timeout = 0.005 # 5 ms
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
                    self.visualizer.write_message('Lost connection to %s' % con)
                except Exception, e:
                    traceback.print_exc()
                    self.visualizer.write_message('%s: %s' % (con, e))

            # try to reconnect disconnected consumers
            for con in [x for x in self.consumers if x.fileno() is None]:
                try:
                    con.reconnect()
                except:
                    pass

        except:
            traceback.print_exc()
        finally:
            return True

    def cursor_create(self):
        pix = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        self.cursor_timer = None
        self.cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)

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
            if k == 'comment': continue
            if isinstance(v, basestring):
                d[k] = re_attrib.sub(sub, v)
            else:
                d[k] = v
        return d

    def parse_consumers(self, config):
        for i, desc in enumerate(config.consumers()):
            what = desc.pop('type')
            name = 'name' in desc and desc.pop('name') or str(i)
            attrib = self.parse_attrib(desc)

            if what in ['consumer', 'tcp']:
                if 'host' not in attrib:
                    self.log.error('consumer/%s missing host, ignored' % name)
                    continue
                if 'port' not in attrib:
                    self.log.error('consumer/%s missing port, ignored' % name)
                    continue
                con = consumer.Consumer(attrib['host'], attrib['port'], name)
            elif what == 'process':
                if 'command' not in attrib:
                    self.log.error('process/%s missing command, ignored' % name)
                    continue
                if 'dataset' not in attrib:
                    self.log.error('process/%s missing dataset, ignored' % name)
                    continue
                con = consumer.Process(attrib['command'], attrib['dataset'], name)
            else:
                self.log.error('consumer/%s has unknown type %s, ignored', name, what)
                continue
            self.add_consumer(con)

    def parse_plugins(self, config):
        for i, desc in enumerate(config.plugins()):
            what = desc.pop('type')
            name = 'name' in desc and desc.pop('name') or str(i)
            attrib = self.parse_attrib(desc)

            try:
                self.visualizer.add_plugin(what, name, attrib)
            except Exception, e:
                self.log.error('failed to add plugin %s/%s: %s', what, name, e)

    def parse_hbox(self, config):
        for i, desc in enumerate(config.hbox()):
            name = 'name' in desc and desc.pop('name') or str(i)
            if 'type' in desc: desc.pop('type')
            attrib = self.parse_attrib(desc)

            hbox = self.visualizer.get_hbox(name)
            for k,v in attrib.iteritems():
                if k == 'width':
                    hbox.set_width(v)
                else:
                    self.log.warning('hbox has no such attribute: %s', k)

    def parse_config(self, config):
        self.visualizer.set_transition(config)
        self.parse_consumers(config)
        self.parse_plugins(config)
        self.parse_hbox(config)

def usage():
    return """\
Plugins:
{plugin}

For help about a specific plugin use -H NAME
""".format(plugin='\n'.join(['  - %s: %s' % x for x in plugin.available()]))

def setup_logging():
    filename = 'visualizer.log'
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter('[%(name)-16s] [%(levelname)-8s] %(message)s'))
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('[%(asctime)s] [%(name)-12s] [%(levelname)-8s] %(message)s', '%a, %d %b %Y %H:%M:%S %z'))
    log = logging.getLogger('')
    log.addHandler(ch)
    log.addHandler(fh)
    log.setLevel(logging.DEBUG)
    logging.getLogger('OpenGL.extensions').setLevel(logging.WARNING)
    log.debug('Visualizer started')
    return log

def run():
    print >> sys.stderr
    print >> sys.stderr, '#' * 60
    print >> sys.stderr, 'DPMI Visualizer 0.7'
    print >> sys.stderr, '(c) 2011-2013 David Sveningsson <ext@sidvind.com>'
    print >> sys.stderr, 'GNU GPLv3'
    print >> sys.stderr

    parser = argparse.ArgumentParser(epilog=usage(), formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-f', '--config', default=None, help='Configuration-file')
    parser.add_argument('-H', dest='plugin', type=str, metavar='PLUGIN', help="Show help for plugin")
    parser.add_argument('--test', action='store_true', help="Run tests")
    args = parser.parse_args()

    if args.plugin:
        plugin.usage(args.plugin)
        sys.exit(0)

    if args.test:
        import tests
        tests.run() # calls sys.exit

    log = setup_logging()

    if not args.config:
        if not os.path.exists('visualizer.conf'):
            print >> sys.stderr, 'No config-file specified and "visualizer.conf" not found'
            sys.exit(1)
        args.config = 'visualizer.conf'
    if not os.path.exists(args.config):
        print >> sys.stderr, 'Failed to load configuration from %s: No such file or directory' % args.config
        sys.exit(1)

    # parse config
    cfg = config.read(args.config)

    pidlock = cfg.get('general/lockfile')
    if os.path.exists(pidlock):
        print >> sys.stderr, pidlock, 'exists, if the visualizer isn\'t running manually remove the file before continuing'
        sys.exit(1)

    with open(pidlock, 'w') as pid:
        pid.write(str(os.getpid()))

    try:
        main = Main(cfg, filename=args.config)
        gtk.main()
    finally:
        os.unlink(pidlock)

    log.debug('Visualizer stopped')
