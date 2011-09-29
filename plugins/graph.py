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
        yield tuple([float(x) for x in line.split(';')])

class Graph(Plugin, PluginUI):
    name = 'NPL Graph plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-09-29'
    version = 0
    api = 1
    interval = 10

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, (1,1))
        self._title = '<Unnamed graph>'
        self.content = '<b>Lorem</b> ipsum dot sit amet'
        self.font_a = PluginUI.create_font(self.cr, size=16)
        self.font_b = PluginUI.create_font(self.cr, size=12)
        self.dataset = []
        self.filter = {}
        self.data = numpy.array([0]*100, numpy.float)
        self.n_samples = 100
        self.pos = 0
        self._range_x = (-100,0)
        self.offset = None

    @attribute(type=str)
    def source(self, value):
        [ds, flt] = value.split(':')
        self.dataset.append(ds)
        self.filter[ds] = sys.modules[__name__].__dict__[flt]

    @attribute(type=str)
    def title(self, value):
        self._title = value

    @attribute(type=str)
    def range_x(self, value):
        self._range_x = tuple([float(x) for x in value.split(':')])
        self.interval = 1.0 / (float(abs(self._range_x[0])) / self.n_samples)

    @attribute(type=str)
    def range_y(self, value):
        pass

    @attribute(type=int)
    def samples(self, value):
        self.data = numpy.array([0]*int(value), numpy.float)
        self.n_samples = int(value)
        self.interval = 1.0 / (float(abs(self._range_x[0])) / self.n_samples)

    def on_data(self, dataset, raw):
        delta = float(abs(self._range_x[0])) / self.n_samples
        flt = self.filter[dataset]
        for x,y in flt(raw):
            if not self.offset:
                self.offset = x
                self.iteration = 1
            elif x - self.offset > delta:
                self.pos += 1
                self.pos %= self.n_samples
                self.iteration = 1
                self.data[self.pos]
                self.offset += delta
            #print x,y,delta,self.offset,self.pos,self.iteration
            
            prev = self.data[self.pos]
            tmp = ((y-prev)/(self.iteration))+prev # inc. avg.
            self.iteration += 1
            self.data[self.pos] = tmp

    # cairo
    def do_render(self):
        cr = self.cr
        cr.save()

        self.clear(cr, (0.95, 0.95, 1.0, 1.0))
        cr.translate(5, 5)
        self.text(cr, "<u>%s</u>" % self._title, self.font_a)

        w = float(self.size[0]) / (self.n_samples-1)
        n = 0
        c = (self.pos+1) % self.n_samples
        cr.move_to(n, self.data[c]+25)
        while True:
            n += w
            c = (c+1)%self.n_samples
            if c == self.pos: break

            cr.line_to(n, self.data[c]+25)
        cr.stroke()

        cr.restore()

    def on_resize(self, size):
        PluginUI.on_resize(self, size)

    # plugin
    def render(self):
        PluginUI.invalidate(self)
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
