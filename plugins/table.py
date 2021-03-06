# -*- coding: utf-8; -*-

from visualizer.plugin import PluginCairo, attribute
import sys
import traceback
import pango
import itertools

name = 'NPL Tabular data plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2012-10-05'
version = 1
api = 1

class Table(PluginCairo):
    """Displays tabular data.

    Each set of data represents a full table, e.g. a json-encoded list of lists.
    Number of columns is dynamically adjusted.

    """

    framerate = 1

    def __init__(self):
        PluginCairo.__init__(self)

        self.font_a = PluginCairo.create_font(self.cr, size=16)
        self.font_b = PluginCairo.create_font(self.cr, size=12)

        self.title = None
        self.header = None
        self.content = []
        self.dataset = []

        self.area = self.pango.create_layout()
        self.area.set_font_description(self.font_b)
        self.area.set_width(int(self.size[0] * pango.SCALE))

    @attribute(name='title', type=str, default='Unnamed table')
    def set_title(self, value):
        """Table title."""
        self.title = value

    @attribute(name="header", type=str, sample="Key;Value")
    def set_header(self, value):
        """Column headers.

        A semicolon separated list of column headers. Text is parsed
        using pango markup. If unset no headers will be displayed.
        """
        self.header = ['<b>%s</b>' % x for x in value.split(';')]

    @attribute(type=str, sample="0;+50;+50")
    def tabstop(self, value):
        """Sets tabstops for columns.

        A semicolon separated list of tab positions (in pixels). If the position
        is prefixed with a '+' sign it is relative to the previous position.
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
        PluginCairo.on_resize(self, size)
        self.area.set_width(int(self.size[0] * pango.SCALE))

    def on_data(self, dataset, data):
        func = self.filter[dataset]
        self.content = list(func(data))

    # cairo
    def do_render(self):
        cr = self.cr
        cr.save()
        self.clear((0.95, 0.95, 1.0, 1.0))

        cr.translate(5,5)
        self.text(self.title, self.font_a)

        cr.translate(0, 30)

        rows = self.content
        if self.header:
            rows = itertools.chain([self.header], rows)

        text = '\n'.join(['\t'.join([str(y) for y in x]) for x in rows])
        self.area.set_markup(text);
        self.pango.show_layout(self.area)

        cr.restore()

factory = Table
