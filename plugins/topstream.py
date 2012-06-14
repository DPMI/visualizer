# -*- coding: utf-8; -*-

from visualizer.plugin import Plugin, attribute, PluginUI
import math
import traceback
import json
from socket import ntohs, ntohl
from OpenGL.GL import *

name = 'NPL Top Stream  plugin'
author = ('David Sveningsson, Patrik Arlos', 'dsv@bth.se,pal@bth.se')
date = '2011-06-08'
version = 0
api = 1

class TOPstream(Plugin, PluginUI):
    interval = 60
    dataset = ['topstream']

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, size=(1,1))

        self.font_a = PluginUI.create_font(self.cr, size=16)
        self.font_b = PluginUI.create_font(self.cr, size=12)
        self.hosts = []

    def on_resize(self, size):
        Plugin.on_resize(self, size)
        PluginUI.on_resize(self, size)

    def on_data(self, ds, data):
        assert ds == 'topstream'
        self.hosts = json.loads(data)

    # cairo
    def do_render(self):
        cr = self.cr
        cr.save()
        self.clear((0.95, 0.95, 1.0, 1.0))

        cr.translate(5,5)
        self.text( "<u>Top Streams </u>", self.font_a)

        for host, hits in self.hosts:
            cr.translate(0,25)
            self.text("%s (%d hits)" % (host, hits), self.font_b)

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

def factory():
    return TOPstream()
