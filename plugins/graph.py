from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *
from visualizer.picotime import picotime
import sys
import numpy
import cairo
import pango
import math

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
        self._range_y = [-100, 100]
        self.offset = None
        self._xtitle= 'Default [s]'
        self._ytitle=' Default [unit]'

    @attribute(type=str)
    def source(self, value):
        [ds, flt] = value.split(':')
        self.dataset.append(ds)
        self.filter[ds] = sys.modules[__name__].__dict__[flt]

    @attribute(type=str)
    def title(self, value):
        self._title = value

    @attribute(type=str)
    def xtitle(self, value):
        self._xtitle = value

    @attribute(type=str)
    def ytitle(self, value):
        self._ytitle = value

    @attribute(type=str)
    def range_x(self, value):
        self._range_x = tuple([float(x) for x in value.split(':')])
        self.interval = 1.0 / (float(abs(self._range_x[0])) / self.n_samples)

    @attribute(type=str)
    def range_y(self, value):
        self._range_y = tuple([float(x) for x in value.split(':')])

    @attribute(type=int)
    def samples(self, value):
        self.data = numpy.array([0]*int(value), numpy.float)
        self.n_samples = int(value)
        self.interval = 1.0 / (float(abs(self._range_x[0])) / self.n_samples)

    def normalize(self, value):
        yoffset = self._range_y[1]
        yscale = float(self.size[1]) / (self._range_y[1] - self._range_y[0])
        return (value + yoffset) * yscale

    def on_data(self, dataset, raw):
        delta = float(abs(self._range_x[0])) / self.n_samples
        flt = self.filter[dataset]
        for x,y in flt(raw):
            if not self.offset:
                self.offset = x
                self.iteration = 1
            elif x - self.offset > delta:
                print self.data[self.pos]
                self.data[self.pos] = self.normalize(self.data[self.pos])
                print self.data[self.pos]
                
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

    def render_title(self):
        self.cr.save()
        self.cr.translate(5, 5)
        self.text("<u>%s</u>" % self._title, self.font_a)
        self.cr.restore()

    def render_chart(self):
        cr = self.cr
        cr.save()
        cr.translate(5, 30)
        cr.rectangle(0, 0, self.size[0]-10, self.size[1]-35);
        cr.set_source_rgba(1,1,1,1)
        cr.fill()
        cr.rectangle(0, 0, self.size[0]-10, self.size[1]-35);
        cr.set_line_width(1.0)
        cr.set_source_rgba(0,0,0,1)
        cr.stroke()
        cr.restore()

    def render_labels(self):
        cr = self.cr
        
        cr.save()
        cr.translate(-5+self.size[0]-175, -25+self.size[1]-30)
        self.text(self._xtitle, self.font_a,alignment=pango.ALIGN_RIGHT,width=165)
        cr.restore()

        cr.save()
        cr.rotate(math.pi/2)
        cr.translate(0, -30)
        self.text(self._ytitle, self.font_a,alignment=pango.ALIGN_RIGHT,width=165)
        cr.restore()

    def render_graph(self):
        cr = self.cr
        
        cr.save()
        cr.translate(5,30)
        cr.set_antialias(cairo.ANTIALIAS_NONE)
        cr.set_source_rgba(0,0,0,1)
        w = float(self.size[0]) / (self.n_samples-1)
        #yoffset = self._range_y[1]
        #yscale = float(self.size[1]) / (self._range_y[1] - self._range_y[0])
        n = 0
        c = (self.pos+1) % self.n_samples
        cr.move_to(n, self.data[c])
        while True:
            n += w
            c = (c+1)%self.n_samples
            if c == self.pos: break

            cr.line_to(n, self.data[c])
        cr.stroke()

        cr.restore()

    # cairo
    def do_render(self):
        cr = self.cr

        self.clear((0.95, 0.95, 1.0, 1.0))
        self.render_title()
        self.render_chart()
        self.render_labels()
        self.render_graph()

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
