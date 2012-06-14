from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
import cairo
from OpenGL.GL import *
from visualizer.picotime import picotime

name = 'NPL Static Image content plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2011-08-15'
version = 0
api = 1

class StaticContent(Plugin, PluginUI):
    interval = -1

    @attribute(type=str)
    def text_font(self, value):
        self.font = PluginUI.create_font(raw=value)

    @attribute(type=str)
    def filename(self, value):
        self.content = cairo.ImageSurface.create_from_png(value)
        self.imgw=self.content.get_width()
        self.imgh=self.content.get_height()
        self.imgscale=0.75*self.size[0]/self.imgw
        self.imgxpos=(self.size[0]-self.imgw*self.imgscale)*0.5

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, (1,1))
        self.content = None
        self.imgw = 0
        self.imgh = 0
        self.imgscale = 0
        self.imgxpos = 0
        self.font = PluginUI.create_font(self.cr, size=16)

    # cairo
    def do_render(self):
        self.clear((0.95, 0.95, 1.0, 1.0))
        if self.content is None: return

        self.cr.translate(self.imgxpos,5)
        self.cr.rectangle(0,0,self.size[0], self.size[1])
        self.cr.scale(self.imgscale,self.imgscale)
        self.cr.set_source_surface(self.content)
        self.cr.paint()

    def on_resize(self, size):
        PluginUI.on_resize(self, size)
        if self.content is not None:
            self.imgscale=0.75*self.size[0]/self.imgw
            self.imgxpos=(self.size[0]-self.imgw*self.imgscale)*0.5

    # plugin
    def render(self):
        PluginUI.render(self)

    def bind(self):
        PluginUI.bind_texture(self)

    def _generate_framebuffer(self, size):
        pass # do not want

def factory(**kwargs):
    item = StaticContent()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
