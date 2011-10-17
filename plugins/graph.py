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
        self.font_label = PluginUI.create_font(self.cr, size=10)
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
        self.auto = False

        # chart margins
        self.margin = [30, 5, 20, 30] # top right bottom left

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
        self.interval = 1.0 / (float(abs(self._range_x[0])) / (self.n_samples-2))

    @attribute(type=str)
    def range_y(self, value):
        self._range_y = tuple([float(x) for x in value.split(':')])

    @attribute(type=int)
    def samples(self, value):
        if value == 'auto':
            self.auto = True
            value = (self.size[0] - self.margin[1] - self.margin[3]) / 4
        self.data = numpy.array([0]*int(value), numpy.float)
        self.n_samples = int(value)
        self.interval = 1.0 / (float(abs(self._range_x[0])) / (self.n_samples-2))
        self.pos = 0

    def normalize(self, value):
        yoffset = self._range_y[1]
        height = self.size[1] - self.margin[0] - self.margin[1]
        yscale = float(height) / (self._range_y[1] - self._range_y[0])
        return (value + yoffset) * yscale

    def on_data(self, dataset, raw):
        delta = float(abs(self._range_x[0])) / self.n_samples
        flt = self.filter[dataset]
        for timestamp, value in flt(raw):
            if not self.offset: # first run
                self.offset = timestamp
                self.iteration = 1
            elif timestamp - self.offset > delta: # accumulated enough points
                self.data[self.pos] = self.normalize(self.data[self.pos])

                # this loop is needed if the samplerate is higher than the
                # rate the consumer provides data.
                n = math.floor((timestamp - self.offset) / delta)

                while n > 0:
                    prev = self.data[self.pos]
                    self.pos += 1
                    self.pos %= self.n_samples
                    self.iteration = 1
                    if n == 1:
                        self.data[self.pos] = 0
                    else:
                        self.data[self.pos] = prev
                    self.offset += delta
                    n -= 1
            
            prev = self.data[self.pos]
            tmp = ((value-prev)/(self.iteration))+prev # inc. avg.
            self.iteration += 1
            self.data[self.pos] = tmp

    def render_title(self):
        self.cr.save()
        self.cr.translate(5, 5)
        self.text("<u>%s</u>" % self._title, self.font_a)
        self.cr.restore()

    def render_chart(self):
        cr = self.cr
        w = self.size[0] - self.margin[1] - self.margin[3]
        h = self.size[1] - self.margin[0] - self.margin[2]
        
        cr.save()
        cr.translate(self.margin[3], self.margin[0])
        cr.rectangle(0, 0, w, h);
        cr.set_source_rgba(1,1,1,1)
        cr.fill()
        cr.rectangle(0, 0, w, h);
        cr.set_line_width(1.0)
        cr.set_source_rgba(0,0,0,1)
        cr.stroke()
        cr.restore()

    def render_labels(self):
        cr = self.cr

        width  = self.size[0] - self.margin[1] - self.margin[3]
        height = self.size[1] - self.margin[0] - self.margin[1]

        # horizontal
        cr.save()
        cr.translate(self.margin[3], self.size[1]-15)
        self.text(self._xtitle, self.font_label, alignment=pango.ALIGN_CENTER, width=width)
        cr.restore()

        # vertical
        cr.save()
        cr.rotate(math.pi/2)
        cr.translate(20, -25)
        self.text(self._ytitle, self.font_label, alignment=pango.ALIGN_CENTER, width=height)
        cr.restore()

    def render_graph(self):
        cr = self.cr
        
        cr.save()
        cr.translate(0, self.margin[0])
        cr.set_source_rgba(0,0,0,1)

        w = self.size[0] - self.margin[1] - self.margin[3]
        dx = float(w) / (self.n_samples-2) # -1 because, and -1 because the latest sample isn't finished yet
        n = self.margin[3]
        c = (self.pos+1) % self.n_samples
        cr.move_to(n, self.data[c])
        while True:
            n += dx
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
        if self.auto:
            self.samples('auto')
        elif self.n_samples > size[0]:
            print >> sys.stderr, 'Warning: graph samplerate (%d) is greater than horizontal resolution (%d), it is a waste of CPU and GPU and yields subpar rendering (i.e moire patterns). Either lower the samplerate or preferably use "auto".' % (self.n_samples, size[0])

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
