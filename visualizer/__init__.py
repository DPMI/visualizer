import pygtk
pygtk.require('2.0')
import gtk
import gobject
import argparse
import ConfigParser as configparser
from os.path import dirname, join

import consumer
from _canvas import Canvas

class Main:
    cursor_timeout = 2000 # delay in ms until hiding cursor

    def __init__(self, config_fp):
        builder = gtk.Builder()
        builder.add_from_file(join(dirname(__file__),'main.ui'))
        builder.connect_signals(self)
        self.window = builder.get_object('main')
        self.notebook = builder.get_object('notebook1')

        self.area = builder.get_object('area')
        gl_config = gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB | gtk.gdkgl.MODE_DEPTH | gtk.gdkgl.MODE_DOUBLE)

        # parse config
        transition = 15
        if config_fp:
            config = configparser.SafeConfigParser()
            config.readfp(config_fp)

            print config.sections()
            transition = config.getint('general', 'transition')

        # cursor
        pix = gtk.gdk.Pixmap(None, 1, 1, 1)
        color = gtk.gdk.Color()
        self.cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)

        # setup visualizer
        self.visualizer = Canvas(gl_config, size=(800, 600), transition_time=transition)

        self.visualizer.add_stream('01:00:00:00:00:01', consumer.SOURCE_ETHERNET, iface="eth0")
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

    main = Main(args.config)
    gtk.main()
