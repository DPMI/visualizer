# -*- coding: utf-8; -*-

from visualizer.plugin import Plugin, attribute, PluginUI
import sys
import traceback
import pango
import itertools
from json import loads as json

name = 'NPL Tabular data plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2012-06-14'
version = 0
api = 1

def whitespace(value):
    return [value.split()]

class Table(Plugin, PluginUI):
    interval = 1

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, size=(1,1))

        self.font_a = PluginUI.create_font(self.cr, size=16)
        self.font_b = PluginUI.create_font(self.cr, size=12)

        self._title = 'Unnamed table'
        self._header = []
        self._content = []
        self.dataset = []
        self.filter = None

        self.area = self.pango.create_layout()
        self.area.set_font_description(self.font_b)
        self.area.set_width(int(self.size[0] * pango.SCALE))

    @attribute(type=str)
    def source(self, value):
        """Data source.

        Format: NAME;FILTER
        where filter is "json" or "whitespace".
        """
        [ds, flt] = value.split(':')
        self.dataset = [ds]
        self.filter = sys.modules[__name__].__dict__[flt]

    @attribute(type=str)
    def title(self, value):
        """Table title"""
        self._title = value

    @attribute(type=str)
    def header(self, value):
        """Column headers.

        A semicolon separated list of column headers. Text is parsed
        using pango markup.
        """
        self._header = ['<b>%s</b>' % x for x in value.split(';')]

    @attribute(type=str)
    def tabstop(self, value):
        """Sets tabstops for columns.

        A semicolon separated list of tab positions. If the position is prefixed
        with a '+' sign it is relative to the previous position.
        """
        v = value.split(';')
        t = pango.TabArray(len(v), True)
        c = 0
        for i, x in enumerate(v):
            if x[0] == '+':
                x = c + int(x[1:])
            else:
                x = int(x)
            c = x
            t.set_tab(i, pango.TAB_LEFT, x)
        self.area.set_tabs(t)

    def on_resize(self, size):
        Plugin.on_resize(self, size)
        PluginUI.on_resize(self, size)
        self.area.set_width(int(self.size[0] * pango.SCALE))

    def on_data(self, ds, data):
        self._content = self.filter(data)

    # cairo
    def do_render(self):
        cr = self.cr
        cr.save()
        self.clear((0.95, 0.95, 1.0, 1.0))

        cr.translate(5,5)
        self.text(self._title, self.font_a)

        cr.translate(0, 30)

        text = '\n'.join(['\t'.join([str(y) for y in x]) for x in itertools.chain([self._header], self._content)])
        self.area.set_markup(text);
        self.pango.show_layout(self.area)

        cr.restore()

    # plugin
    def render(self):
        PluginUI.invalidate(self)
        PluginUI.render(self)

    def bind(self):
        PluginUI.bind_texture(self)

    def _generate_framebuffer(self, size):
        pass # do not want

factory = Table

