from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *
from visualizer.picotime import picotime
import sys
import numpy

def csv_filter(value):
    for line in value.splitlines():
        yield tuple(line.split(';'))

class Graph(Plugin, PluginUI):
    name = 'NPL Graph plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-09-29'
    version = 0
    api = 1
    interval = -1

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, (1,1))
        self._title = '<Unnamed graph>'
        self.content = '<b>Lorem</b> ipsum dot sit amet'
        self.font_a = PluginUI.create_font(self.cr, size=16)
        self.font_b = PluginUI.create_font(self.cr, size=12)
        self.dataset = []
        self.filter = {}
        self.data = numpy.array([0,0]*100)
        self.size = 100
        self.rp = 0
        self.wp = 0

    @attribute(type=str)
    def source(self, value):
        [ds, flt] = value.split(':')
        self.dataset.append(ds)
        self.filter[ds] = sys.modules[__name__].__dict__[flt]

    @attribute(type=str)
    def title(self, value):
        self._title = value

    @attribute(type=int)
    def samples(self, value):
        self.data = numpy.array([0,0]*int(value))
        self.size = int(value)

    def on_data(self, dataset, raw):
        print [raw]
        flt = self.filter[dataset]
        #for x,y in flt(raw):
        #    self.data[self.wp][0] = x
        #    self.data[self.wp][1] = y
        #    self.wp = (self.wp+1)%self.size
        #print self.data

    # cairo
    def do_render(self):
        cr = self.cr
        self.clear(cr, (0.95, 0.95, 1.0, 1.0))
        cr.translate(5, 5)
        self.text(cr, "<u>%s</u>" % self._title, self.font_a)

    def on_resize(self, size):
        PluginUI.on_resize(self, size)

    # plugin
    def render(self):
        PluginUI.render(self)

    def bind(self):
        PluginUI.bind_texture(self)

    def _generate_framebuffer(self, size):
        pass # do not want

def factory(**kwargs):
    item = Graph()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
