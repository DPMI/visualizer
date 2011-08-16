from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *
from visualizer.picotime import picotime

class StaticContent(Plugin, PluginUI):
    name = 'NPL Static content plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-08-15'
    version = 0
    api = 1
    interval = -1

    @attribute(type=str)
    def text_font(self, value):
        self.font = PluginUI.create_font(raw=value)

    @attribute(type=str)
    def filename(self, value):
        with open(value) as fp:
            self.content = fp.read()

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, (1,1))
        self.content = '<b>Lorem</b> ipsum dot sit amet'
        self.font = PluginUI.create_font(self.cr, size=16)

    # cairo
    def do_render(self):
        self.clear(self.cr, (0.9,0.9,1.0,1.0))
        self.cr.translate(10,5)
        self.text(self.cr, self.content, self.font, justify=True, width=self.width-20)

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
    item = StaticContent()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
