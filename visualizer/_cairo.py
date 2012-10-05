#!/usr/bin/python
# -*- coding: utf-8 -*-

import array, math
import cairo, pango, pangocairo
from OpenGL.GL import *
from OpenGL.GLU import *
import hashlib

from pango import ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT

class Cairo(object):
    def __init__(self, size, format=cairo.FORMAT_ARGB32, filter=GL_NEAREST):
        self.size = size
        self.width, self.height = size
        self._format = format
        self._filter = filter
        self._generate_surface()

    def _generate_surface(self):
        bpp = 4
        #if self._format == cairo.FORMAT_RGB32:
        #    bpp = 3

        self._data = array.array('c', chr(0) * self.width * self.height * bpp)
        stride = self.width * bpp
        self.surface = cairo.ImageSurface.create_for_data(self._data, self._format, self.width, self.height, stride)
        self._texture = glGenTextures(1);
        self.cr = cairo.Context(self.surface)
        self.pango = pangocairo.CairoContext(self.cr)
        self.layout = self.pango.create_layout()

        # force subpixel rendering
        self.font_options = cairo.FontOptions()
        self.font_options.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.cr.set_font_options(self.font_options)

        glBindTexture(GL_TEXTURE_2D, self._texture);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, self._filter)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, self._filter)

        self.invalidate()

    def bind_texture(self):
        glBindTexture(GL_TEXTURE_2D, self._texture)

    def display(self):
        self.bind_texture()
        glColor4f(1,1,1,1)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 1)
        glVertex3f(0, 0, 0)

        glTexCoord2f(0, 0)
        glVertex3f(0, 1, 0)

        glTexCoord2f(1, 0)
        glVertex3f(1, 1, 0)

        glTexCoord2f(1, 1)
        glVertex3f(1, 0, 0)
        glEnd()

    def on_resize(self, size):
        self.size = size
        self.width, self.height = size
        self._generate_surface()

    def do_render(self):
        raise NotImplementedError

    def render(self):
        if not self._invalidated:
            return

        self.do_render()
        glBindTexture(GL_TEXTURE_2D, self._texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_BGRA, GL_UNSIGNED_BYTE, self._data.tostring());

        self._invalidated = False

    @classmethod
    def create_font(cls, font='Sans', size=12, raw=None):
        if raw is None:
            raw = '%s %f' % (font, size)
        return pango.FontDescription(raw)

    def clear(self, color=(0,0,0,0)):
        cr = self.cr
        cr.save()
        cr.set_source_rgba(*color)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.restore()

    def text(self, text, font, color=(0,0,0,1), alignment=pango.ALIGN_LEFT, justify=False, width=None):
        cr = self.cr
        cr.set_source_rgba(*color)

        self.layout.context_changed()
        self.layout.set_font_description(font)

        if width:
            self.layout.set_width(int(width * pango.SCALE))

        self.layout.set_alignment(alignment)
        self.layout.set_justify(justify)
        self.layout.set_markup(text);
        self.pango.show_layout(self.layout)

        return self.layout.get_pixel_extents()

    def render_piechart(self, segment, graph_title, size, max_rows=None, background=None):
        cr = self.cr
        cr.save()

        start = 0.0
        width, height = size
        radius = min(width, height) * 0.5

        if background:
            cr.save()
            cr.set_source_rgba(*background)
            cr.rectangle(0, 0, width, height);
            cr.fill()
            cr.restore()

        def gen_color(str):
            hash = hashlib.md5(str).hexdigest()
            r = int(hash[0:2],16) / 255.0
            g = int(hash[2:4],16) / 255.0
            b = int(hash[4:6],16) / 255.0
            return r,g,b,1

        cr.set_line_width(1.0)
        cr.translate(-width*0.5+radius, 0)
        items = [(title, value, gen_color(title), index) for index, (title, value) in enumerate(segment.items())]
        items.sort(key=lambda x: x[1], reverse=True)

        if max_rows is not None:
            items = items[:max_rows]

            # normalize
            if len(items) > 0:
                inv = 1.0 / sum([x[1] for x in items])
                items = [(x[0], x[1] * inv, x[2], x[3]) for x in items]

        for title, value, color, index in items:
            end = start +  value * (2.0 * math.pi)
            mid = (start + end)*0.5

            cr.save()
            cr.move_to(width/2, height/2 )
            cr.line_to(width/2 + radius * math.cos(start), height/2 + radius * math.sin(start) )
            cr.arc(width/2, height/2, radius, start, end )
            cr.close_path()

            cr.set_line_width(1.0)
            cr.set_source_rgba(*color)
            cr.fill_preserve()
            cr.set_source_rgba(0, 0, 0, 1.0 )
            cr.stroke()

            start += (end-start);
        cr.restore()

        cr.save()
        cr.translate(width*0.5 + radius + 15, 5)
        cr.set_font_size(16)

        cr.set_source_rgba(0,0,0,1)
        cr.show_text(graph_title)
        cr.translate(0, 15)

        for title, value, color, index in items:
            cr.set_source_rgba(*color)
            cr.rectangle(0, 0, 25, 25)
            cr.fill()

            cr.translate(35, 15)
            cr.set_source_rgba(0,0,0,1)
            cr.show_text('%s (%2.1f%%)' % (title, value*100))

            cr.translate(-35, 15)

        cr.restore()

class CairoWidget(Cairo):
    def __init__(self, size):
        Cairo.__init__(self, size)
        self._invalidated = True

    def invalidate(self):
        self._invalidated = True

    def is_invalidated(self):
        return self._invalidated
