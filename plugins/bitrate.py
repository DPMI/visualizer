from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *
from visualizer.picotime import picotime

parser = htmlcolor.Parser(factory=htmlcolor.FloatFactory, components=4)

class UI(PluginUI):
    def __init__(self, *args, **kwargs):
        PluginUI.__init__(self, *args, **kwargs)

        self.font = PluginUI.create_font(self.cr, size=16)
    
    def do_render(self):
        cr = self.cr
        font = self.font
        
        self.clear(cr)

        cr.translate(5,5)
        self.text(cr, "Bitrate (Kb/s)", font)

class Bitrate(Plugin):
    name = 'NPL bitrate plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-06-08'
    version = 0
    api = 1

    # How often this plugin needs to render
    # -1 Static content (only redrawn on expose)
    #  0 As often as possible (i.e. realtime)
    #  N Fixed framerate (requests N frames per second)
    interval = 0

    @attribute(type=str)
    def background(self, value):
        self.color = parser.parse(value)

    @attribute(type=int)
    def rate(self, value):
        self._rate = value

    def __init__(self):
        Plugin.__init__(self)
        self.color = (1,1,1,1)
        self._rate = 100
        self.time = picotime.now()
        self._accum = 0
        self.ui = UI((1,1))

    def on_resize(self, size):
        Plugin.on_resize(self, size)
        self.ui.on_resize(size)
        print size
    
    def on_packet(self, stream, frame):
        ts = picotime(frame.tv_sec, frame.tv_psec)

        delta = ts - self.time
        rate = self._rate * 1000000000

        if delta > rate:
            self.time += rate
            m = 1000.0 / self._rate
            #print 'tick', '%.2fKb/s' % ((self._accum * m) / 1024)
            self._accum = 0

        self._accum += frame.len

    def on_render(self):
        glClearColor(1,1,1,1)
        glClear(GL_COLOR_BUFFER_BIT)
            
        self.ui.render()
        self.ui.display()

def factory():
    return Bitrate()
