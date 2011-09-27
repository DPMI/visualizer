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

import consumer
from _canvas import Canvas

class Main:
    cursor_timeout = 2000 # delay in ms until hiding cursor
    transition = 15

    def __init__(self, config_fp):
        builder = gtk.Builder()
        builder.add_from_file(join(dirname(__file__),'main.ui'))
        builder.connect_signals(self)
        self.window = builder.get_object('main')
        self.notebook = builder.get_object('notebook1')

        self.area = builder.get_object('area')
        gl_config = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB | gtk.gdkgl.MODE_DEPTH | gtk.gdkgl.MODE_DOUBLE)

        # config defaults
        self.transition = Main.transition
        self.consumers = []

        # parse config
        config = configparser.SafeConfigParser()
        config.readfp(config_fp)
        
        self.transition = config.getint('general', 'transition')
        
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
                try:
                    self.consumers.append(consumer.Consumer(host, port))
                except:
                    traceback.print_exc()
                    print >> sys.stderr, 'Consumer', host, port
            elif ns == 'plugin':
                print 'plugin', key

        print self.consumers

        # cursor
        pix = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        self.cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)

        # setup visualizer
        self.visualizer = Canvas(gl_config, size=(800, 600), transition_time=self.transition)

        #self.visualizer.add_stream('01:00:00:00:00:01', consumer.SOURCE_ETHERNET, iface="eth0")
        self.visualizer.add_module('overview')
        self.visualizer.add_module('overview_stats')
        self.visualizer.add_module('http_host')
        self.visualizer.add_module('bitrate')
        self.visualizer.add_module('utilization')
        #self.visualizer.add_module('stub')
        self.visualizer.add_module('static', filename='info.txt', text_font="Verdana 12")
        self.visualizer.connect('motion_notify_event', self.cursor_show)
        
        self.area.pack_start(self.visualizer)
        
        self.window.show_all()
        self._fullscreen = False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def on_main_window_state_event(self, window, event):
        self._fullscreen = bool(gtk.gdk.WINDOW_STATE_FULLSCREEN & event.new_window_state)

    def on_area_button_press_event(self, widget, event):
        if event.type != gtk.gdk._2BUTTON_PRESS:
            return

        if self._fullscreen:
            self.window.unfullscreen()
            self.visualizer.window.set_cursor(None)
            self.notebook.set_show_tabs(True)
        else:
            self.window.fullscreen()
            self.notebook.set_show_tabs(False)
            self.cursor_timer = gobject.timeout_add(self.cursor_timeout, self.cursor_hide)

    def cursor_hide(self):
        if not self._fullscreen:
            return

        self.visualizer.window.set_cursor(self.cursor)
    
    def cursor_show(self, window, event):
        if not self._fullscreen:
            return

        if self.visualizer.window.get_cursor() is None:
            gobject.source_remove(self.cursor_timer)
            self.cursor_timer = gobject.timeout_add(self.cursor_timeout, self.cursor_hide)
        self.visualizer.window.set_cursor(None)

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--config', type=argparse.FileType('r'), default=None, help='Configuration-file')
    args = parser.parse_args()

    if not args.config:
        if not os.path.exists('visualizer.conf'):
            print >> sys.stderr, 'No config-file specified and "visualizer.conf" not found'
            sys.exit(1)
        args.config = open('visualizer.conf')

    main = Main(args.config)
    gtk.main()
