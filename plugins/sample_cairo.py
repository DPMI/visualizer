# -*- coding: utf-8; -*-

from visualizer.plugin import PluginCairo, attribute
import math, time

name = 'Sample Cairo plugin'
author = ('David Sveningsson', 'ext-dpmi-visualizer@sidvind.com')
date = '2014-01-12'
version = 0
api = 1

class MyPlugin(PluginCairo):
    """Brief description of plugin.

    Extended description visible when -H is used.

    """

    # See visualizer/plugin/base.py for description of framerate
    framerate = 1

    def __init__(self):
        PluginCairo.__init__(self)
        self.font = PluginCairo.create_font(self.cr, size=16)
        self.middle = (0,0)
        self.radius = 1

    def on_resize(self, size):
        PluginCairo.on_resize(self, size)
        self.middle = (size[0]*0.5, size[1]*0.5)
        self.radius = size[1] * 0.40

    # Sample attribute (see Attribute class for description)
    @attribute(name='content', type=str, default='No text')
    def set_content(self, value):
        """Description of the attribute (present in -H)."""
        self.content = value

    # Called when new data from consumer arrives
    # `dataset` is the name of the set. Up to developer to decide if it can be
    #  ignored or not. `data` is whatever chunk of data the consumer outputted.
    def on_data(self, dataset, data):
        pass

    # Called when content needs to be redrawn (e.g. periodical when framerate is
    # >= 1 or when the window is resized).
    def do_render(self):
        # convenience, not needed
        cr = self.cr
        x,y = self.middle

        # save current state
        cr.save()

        # fill with solid color
        self.clear((0.95, 0.95, 1.0, 1.0))

        # move position by (5,5) pixels
        cr.translate(5,5)

        # draw the text
        self.text(self.content, self.font)

        # draw clock outline
        cr.set_line_width(4.0)
        cr.arc(x, y, self.radius, 0, math.pi*2.0)
        cr.stroke()

        # draw ticks
        for i in range(12):
            a = i * math.pi / 6.0
            cr.arc(x, y, self.radius,    a, a)
            cr.arc(x, y, self.radius-5, a, a)
            cr.stroke()

        # draw center point
        cr.set_source_rgba(1.0, 0.2, 0.2, 0.6)
        cr.arc(x, y, 10.0, 0, math.pi*2.0)
        cr.fill()

        # draw lines
        t = time.localtime()
        sa = t.tm_sec / 60.0 * math.pi * 2 - math.pi * 0.5
        ma = t.tm_min / 60.0 * math.pi * 2 - math.pi * 0.5
        ha = t.tm_hour % 12 / 12.0 * math.pi * 2 - math.pi * 0.5
        cr.arc(x, y, self.radius * 0.95, sa, sa); cr.line_to(x, y)
        cr.set_line_width(2.0); cr.stroke()
        cr.arc(x, y, self.radius * 0.85, ma, ma); cr.line_to(x, y)
        cr.set_line_width(4.0); cr.stroke()
        cr.arc(x, y, self.radius * 0.65, ha, ha); cr.line_to(x, y)
        cr.set_line_width(6.0); cr.stroke()

        # restore state.
        # this must be done or else the translations would stack and each time
        # this method is called the text would move 5px in each direction
        cr.restore()

factory = MyPlugin
