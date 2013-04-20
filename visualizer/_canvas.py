import pygtk
pygtk.require('2.0')
import gtk
import gtk.gtkgl
import gobject
import imp
import sys
import itertools
import traceback
import time
import threading
import logging
from functools import wraps
from OpenGL.GL import *
from OpenGL.GLX import *
from OpenGL.arrays import vbo
import numpy
from ctypes import c_void_p

import consumer
from _cairo import CairoWidget
from container import Frame, HBox, Blank

class MessageWidget(CairoWidget):
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&apos;",
        ">": "&gt;",
        "<": "&lt;",
        }

    def __init__(self, size):
        CairoWidget.__init__(self, size)
        self.font = self.create_font('Monospace', size=32)
        self.message = ''
        self.invalidate()
        self.time = 0

    def write(self, text):
        self.message = ''.join(self.html_escape_table.get(c,c) for c in text)
        self.time = time.time()
        self.invalidate()

    def do_render(self):
        self.clear((0,0,0,0))
        self.cr.save()
        self.cr.set_source_rgba(0.1, 0.1, 0.5, 0.85)
        self.cr.rectangle(0, 0, 10 + 26.5 * len(self.message), self.size[1])
        self.cr.fill()
        self.cr.translate(5,10)
        self.text(self.message, font=self.font, color=(1,1,1,1))
        self.cr.restore()

class GLContext:
    def __init__(self, widget):
        self.widget = widget

    def __enter__(self):
        gldrawable = self.widget.get_gl_drawable()
        glcontext = self.widget.get_gl_context()

        if not gldrawable.gl_begin(glcontext):
            raise RuntimeError, 'gl_begin failed'

        return gldrawable

    def __exit__(self, type, value, traceback):
        gldrawable = self.widget.get_gl_drawable()
        glcontext = self.widget.get_gl_context()
        gldrawable.gl_end()
        return False # exceptions should propagate

class Canvas(gtk.DrawingArea, gtk.gtkgl.Widget):
    def __init__(self, size, rows=3, transition_time=15):
        gtk.DrawingArea.__init__(self)

        self.size = size
        self.rows = rows
        self.plugins = []
        self.widgets = []
        self.hbox = {}
        self.dataset = []
        self.current = 0
        self.frames = 0                 # frame counter (resets every 1s)
        self.framerate = 0              # current framerate
        self.transition_timer = None    # id of timer
        self.transition_step = 0.0
        self.transition_enabled = False # @note should make a FSM
        self.msgwidget = None

        # widget setup
        self.set_gl_capability(gtk.gdkgl.Config(mode=gtk.gdkgl.MODE_RGB | gtk.gdkgl.MODE_DEPTH | gtk.gdkgl.MODE_DOUBLE))
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.set_size_request(size[0], size[1])

        # Connect the relevant signals.
        self.connect_after('realize',   self.realize)
        self.connect('configure_event', self.configure)
        self.connect('expose_event',    self.expose)
        gobject.timeout_add(1000/50, self.expire)
        gobject.timeout_add(1000, self.framerate_expire)

        # Create VBO
        self.vbo = vbo.VBO(numpy.array([
            [0, 0, 0, 0],
            [0, 1, 0, 1],
            [1, 1, 1, 1],
            [1, 0, 1, 0],
        ], GLfloat))

    def drawable(self):
        # this could be implemented in this class, but it is harder to understand "with self"
        return GLContext(self)

    def get_hbox(self, name):
        if not name: return None

        if name in self.hbox:
            return self.hbox[name]

        size = (self.size[0], self.size[1] / self.rows)
        hbox = HBox('hbox/%s' % name, size)
        self.hbox[name] = hbox
        self.widgets.append(hbox)
        return hbox

    def add_plugin(self, name, index, kwargs):
        log = logging.getLogger('%s/%s' % (name, index))

        info = imp.find_module(name, ['plugins'])
        if info[0] == None:
            log.error('No such plugin')
            return

        try:
            mod = imp.load_module('_vis__%s' % name, *info)

            if not hasattr(mod, 'api'):
                log.error('Plugin does not define API')

            # Allocate new plugin
            plugin = mod.factory()
            plugin.log = log
            attr_table = plugin.attributes()

            # Find ev. hbox
            hbox = self.get_hbox(kwargs.pop('hbox', None))

            # Set all attributes
            for attr in attr_table.values():
                if attr.name not in kwargs and not attr.auto: continue
                v = kwargs.get(attr.name, attr.default)
                try:
                    attr.set(plugin, v)
                except Exception, e:
                    traceback.print_exc()
                    log.error('When setting attibute %s: %s', attr.name, e)
                try:
                    del kwargs[attr.name]
                except:
                    pass

            # Warn about unused variables
            for attr in kwargs.keys():
                plugin.log.warning('No such attribute: %s', attr)

            plugin.log.info('Loaded plugin "{0.name}" v-{0.version} {0.date} ({0.author[0]} <{0.author[1]}>)'.format(mod))

            if not hbox:
                size = (self.size[0], self.size[1] / self.rows)
                frame = Frame(plugin, mod, size)
                self.widgets.append(frame)
            else:
                hbox.add_child(plugin)
            self.plugins.append((plugin, mod))
        except:
            traceback.print_exc()
            print >> sys.stderr, 'When trying to add plugin %s' % name
        finally:
            info[0].close()

    def init_all_plugins(self):
        for plugin, mod in self.plugins:
            self.init_plugin(plugin)
        while len(self.widgets) < self.rows:
            self.widgets.append(Blank())

    def init_plugin(self, plugin):
        req = getattr(plugin, 'dataset', [])
        for ds in req:
            if not ds in self.dataset:
                plugin.log.error('Requires dataset "%s" which is not available', ds)
                return
            func = plugin.on_data
            try:
                self.dataset[ds].subscribe(ds, func)
            except Exception, e:
                traceback.print_exc()
                plugin.log.error('Requires dataset "%s" but consumer refused subscription: %s', ds, str(e))
                return

    def configure(self, widget, event=None):
        with self.drawable():
            self.size = (widget.allocation.width, widget.allocation.height)
            glViewport (0, 0, widget.allocation.width, widget.allocation.height)

            # setup othogonal projection matrix with (0,0) in the upper left corner and with a size of 1x1
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0, 1, 0, 1, -1.0, 1.0)
            glScalef(1, -1, 1)
            glTranslated(0, -1, 0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # notify plugins of the new canvas size
            w = widget.allocation.width
            h = widget.allocation.height / self.rows
            self.size = (widget.allocation.width, widget.allocation.height)
            t = time.time()
            for container in self.widgets:
                container.on_resize((w,h))

                # Force a rerender of plugin.
                container.render(t)

            # Create widget for displaying messages'
            self.msgwidget = MessageWidget(size=(self.size[0], 70))

    def realize(self, widget, event=None):
        with self.drawable():
            glEnable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc (GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def expire(self):
        if self.transition_enabled:
            self.transition_action()

        self.queue_draw()
        return True

    def framerate_expire(self):
        self.framerate = self.frames
        self.frames = 0
        return True

    def set_transition(self, config):
        global logging
        log = logging.getLogger('canvas')

        if config.has_option('general', 'transition'):
            log.warning('Old style transition set, please migrate to new options (see documentation)')
            t = config.getfloat('general', 'transition', 15.0)
            d = 1.5
        else:
            t = config.getfloat('transition', 'time', 15.0)
            d = config.getfloat('transition', 'duration', 1.5)

        if t < d:
            log.warning('transition time is less than duration, setting t = d')
            t = d

        if self.transition_timer:
            gobject.source_remove(self.transition_timer)
        self.transition_timer = gobject.timeout_add(int(t * 1000), self.transition)
        self.transition_duration = d

    def transition(self):
        # lagging or to short, reset
        if self.transition_enabled:
            self.current = (self.current + 1) % max(self.rows, len(self.widgets))
            self.transition_step = 0.0

        self.transition_enabled = True
        self.transition_time = time.time()
        return True

    def transition_action(self):
        if self.transition_step > 1.0:
            self.transition_enabled = False
            self.transition_step = 0.0
            self.current = (self.current + 1) % max(self.rows, len(self.widgets))
            return

        # the value is allowed to be > 1.0 (clamped when used) so 1.0 will
        # actually be rendered.

        s = (time.time() - self.transition_time) / self.transition_duration
        self.transition_step = s ** 3.5 # lean-in

    def expose(self, widget, event=None):
        self.render()

    def write_message(self, text):
        self.msgwidget.write(text)

    def render_widgets(self, widgets):
        glViewport (0, 0, self.allocation.width, self.allocation.height / self.rows)

        t = time.time()
        for container in self.widgets:
            try:
                container.render(t)
            except:
                traceback.print_exc()

    def render_screen(self, widgets):
        glViewport (0, 0, self.allocation.width, self.allocation.height)
        glClearColor(1,0,1,1)
        glClear(GL_COLOR_BUFFER_BIT)

        glPushMatrix()
        glLoadIdentity()

        offset = (-1.0 / self.rows) * min(self.transition_step, 1.0)
        glTranslate(0, offset, 0)
        glScale(1, 1.0 / self.rows, 1)

        for container in widgets:
            try:
                container.blit()
            except:
                traceback.print_exc()
            glTranslate(0, 1, 0)

        glPopMatrix()

    def render_message(self):
        if time.time() - self.msgwidget.time > 7.0: return

        glPushMatrix()
        glLoadIdentity()

        glColor(1,1,1,1)
        glTranslate(1.0 / 50, 1.0 / 50, 0)
        glScale(float(self.msgwidget.size[0]) / self.size[0], float(self.msgwidget.size[1]) / self.size[1], 1)
        self.msgwidget.render()
        self.msgwidget.bind_texture()
        glDrawArrays(GL_QUADS, 0, 4)

        glPopMatrix()

    def render(self):
        self.frames += 1
        widgets = self.visible_widgets()

        with self.drawable() as gldrawable:
            self.render_widgets(widgets)

            self.vbo.bind()
            glEnableClientState(GL_VERTEX_ARRAY)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glVertexPointer(2,   GL_FLOAT, 4*4, c_void_p(0))
            glTexCoordPointer(2, GL_FLOAT, 4*4, c_void_p(2*4))

            self.render_screen(widgets)
            self.render_message()

            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisableClientState(GL_VERTEX_ARRAY)
            self.vbo.unbind()

            if gldrawable.is_double_buffered():
                gldrawable.swap_buffers()
            else:
                glFlush()

    def visible_rows(self):
        n = self.rows
        if self.transition_enabled:
            n += 1
        return n

    def visible_widgets(self):
        # this block of code gets N plugins from the list, wrapping when needed.
        cur = self.current
        rows = self.visible_rows()
        plugins = self.widgets[cur:cur+rows]
        if len(plugins) < rows:
            plugins += self.widgets[:rows-len(plugins)]
        return plugins
