from visualizer.plugin import Plugin, attribute, color, PluginUI
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

name = 'NPL Histogram plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2012-05-31'
version = 1
api = 1

def csv_filter(value):
    for line in value.splitlines():
        yield tuple([float(x.strip('\x00')) for x in line.split(';')])

clamp = lambda v,a,b: min(max(v,a),b)

class Histogram(Plugin, PluginUI):
    interval = 1

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, (1,1))
        self.title = None
        self.font_a = PluginUI.create_font(self.cr, size=16)
        self.font_b = PluginUI.create_font(self.cr, size=12)
        self.font_label = PluginUI.create_font(self.cr, size=10)
        self.dataset = []
        self.filter = {}
        self.data = numpy.array([0]*100, numpy.float)
        self.n_samples = 100
        self.pos = 0
        self.value_range = None
        self.num_bins = 1
        self.fill_color = (1,1,1,1)

        # chart margins
        self.margin = [30, 5, 60, 30] # top right bottom left

    @attribute(type=str, sample="NAME:csv_filter")
    def source(self, value):
        """Datasource for histogram.
        Format: DATASET:FILTER"""
        for pair in value.split(';'):
            [ds, flt] = pair.split(':')
            self.dataset.append(ds)
            self.filter[ds] = sys.modules[__name__].__dict__[flt]

    @attribute(name="title", type=str, default='Unnamed histogram')
    def set_title(self, value):
        """Title of histogram"""
        self.title = value

    @attribute(type=str, default="0:100")
    def range(self, value):
        """Expected range of values.

        Values outside range will be clamped to fit.
        """
        self.value_range = tuple([float(x) for x in value.split(':')])

    @attribute(type=int, default="1000")
    def samples(self, value):
        """Number of samples to save."""
        self.data = numpy.array([0]*int(value), numpy.float)
        self.n_samples = int(value)
        self.pos = 0

    @attribute(type=int, default="25")
    def bins(self, value):
        """Number of bins to store values in."""
        self.num_bins = int(value)

    @attribute(type=color, sample="(1,0,0,1)")
    def fill(self, value):
        """Fill bars with color.

        If set bars will be filled with the specified color.
        """
        self.fill_color = eval(value)

    def on_data(self, dataset, raw):
        flt = self.filter[dataset]
        for timestamp, value in flt(raw):
            # clamp to y-axis range.
            value = clamp(value, self.value_range[0], self.value_range[1])

            self.data[self.pos] = value
            self.pos += 1
            self.pos %= self.n_samples

    def render_title(self):
        self.cr.save()
        self.cr.translate(5, 5)
        self.cr.set_source_rgba(0,0,0,1)
        self.text("%s" % self.title, self.font_a, width=self.size[0])
        self.cr.restore()

    def render_chart(self):
        cr = self.cr
        w = self.size[0] - self.margin[1] - self.margin[3]
        h = self.size[1] - self.margin[0] - self.margin[2]

        # background
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

    def render_graph(self):
        cr = self.cr

        h,_ = numpy.histogram(self.data, bins=self.num_bins, density=False, range=self.value_range)
        y = [float(x)/self.n_samples for x in h]

        cr.save()
        cr.set_line_width(1.0)

        w = self.size[0] - self.margin[1] - self.margin[3] - 2
        h = self.size[1] - self.margin[0] - self.margin[2] - 2
        dx = float(w) / self.num_bins

        cr.translate(self.margin[3], self.margin[0]+1)
        for i, value in enumerate(y):
            x = i * dx
            y = value * h
            cr.rectangle(x, h, dx, -y);

            cr.set_source_rgba(*self.fill_color)
            cr.fill_preserve()
            cr.set_source_rgba(0,0,0,1)
            cr.stroke()

        cr.restore()

    def render_labels(self):
        cr = self.cr
        span = self.value_range[1] - self.value_range[0]
        delta = float(span) / self.num_bins
        w = self.size[0] - self.margin[1] - self.margin[3] - 2
        dx = float(w) / self.num_bins

        prefix = ['', 'K', 'M', 'G', 'T']
        def format(x):
            n = 0
            while x > 1000 and n+1 < len(prefix):
                x /= 1000
                n += 1
            return '%.1f%s' % (x, prefix[n])

        cr.save()
        cr.translate(self.margin[3]+dx*0.75, self.size[1] - self.margin[2] + 5)
        cr.rotate(math.pi / 2)
        for i in range(self.num_bins):
            self.text(format(delta*(i+1)), self.font_label, alignment=pango.ALIGN_LEFT, width=dx)
            cr.translate(0, -dx)
        cr.restore()

    # cairo
    def do_render(self):
        cr = self.cr

        self.clear((0.95, 0.95, 1.0, 1.0))
        self.render_title()
        self.render_chart()
        self.render_graph()
        self.render_labels()

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
    item = Histogram()
    for key, value in kwargs.items():
        try:
            getattr(item, key)(value)
        except:
            traceback.print_exc()
    return item
