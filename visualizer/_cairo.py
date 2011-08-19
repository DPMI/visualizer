#!/usr/bin/python
# -*- coding: utf-8 -*-

import array, math
import cairo, pango, pangocairo
from OpenGL.GL import *
from OpenGL.GLU import *

from pango import ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT

class CairoWidget:
	def __init__(self, size, format=cairo.FORMAT_ARGB32, filter=GL_NEAREST):
		self.size = size
		self.width, self.height = size
		self._format = format
		self._filter = filter
		self._invalidated = True
		self._generate_surface()
		
	def _generate_surface(self):
		bpp = 4
		#if self._format == cairo.FORMAT_RGB32:
		#	bpp = 3
		
		self._data = array.array('c', chr(0) * self.width * self.height * bpp)
		stride = self.width * bpp
		self.surface = cairo.ImageSurface.create_for_data(self._data, self._format, self.width, self.height, stride)
		self._texture = glGenTextures(1);
		
		self.cr = cairo.Context(self.surface)
		
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

	def invalidate(self):
		self._invalidated = True

	def is_invalidated(self):
		return self._invalidated
	
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
	
	@classmethod
	def clear(cls, cr, color=(0,0,0,0)):
		cr.save()
		cr.set_source_rgba(*color)
		cr.set_operator(cairo.OPERATOR_SOURCE)
		cr.paint()
		cr.restore()
	
	@classmethod
	def text(cls, cr, text, font, color=(0,0,0,1), alignment=pango.ALIGN_LEFT, justify=False, width=None):
		cr.set_source_rgba(*color)
		
		ctx = pangocairo.CairoContext(cr)
		layout = ctx.create_layout()
		layout.set_font_description(font)
		
		if width:
			layout.set_width(int(width * pango.SCALE))
		
		layout.set_alignment(alignment)
		layout.set_justify(justify)
		
		layout.set_markup(text);
		ctx.show_layout(layout)

		return layout.get_pixel_extents()