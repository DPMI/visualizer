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
from functools import wraps
from OpenGL.GL import *
from OpenGL.GLX import *

import consumer

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
    def __init__(self, config, size, transition_time=15):
        gtk.DrawingArea.__init__(self)

        self.size = size
        self.rows = 3
        self.plugins = []
        self.current = 0
        self.transition_step = 0.0
        self.transition_enabled = False # @note should make a FSM

        # widget setup
        self.set_gl_capability(config)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK|gtk.gdk.POINTER_MOTION_MASK)
        self.set_size_request(size[0], size[1])

        # Connect the relevant signals.
        self.connect_after('realize',   self.realize)
        self.connect('configure_event', self.configure)
        self.connect('expose_event',    self.expose)
        gobject.timeout_add(1000/50, self.expire)
        gobject.timeout_add(transition_time * 1000, self.transition)

    def drawable(self):
        # this could be implemented in this class, but it is harder to understand "with self"
        return GLContext(self)

    def add_module(self, name, **kwargs):
        info = imp.find_module(name, ['plugins'])
        if info[0] == None:
            raise IOError, 'No such plugin: %s' % name
        try:
            mod = imp.load_module('_vis__%s' % name, *info)

            if not hasattr(mod, 'api'):
                raise IOError, 'plugin "%s" does not define api' % name

            try:
                # Allocate new plugin
                plugin = mod.factory()
                plugin.on_resize((self.size[0], self.size[1] / self.rows))
                attr_table = plugin.attributes()

                # Set all attributes
                for attr in attr_table.values():
                    v = kwargs.get(attr.name, attr.default)
                    try:
                        attr.set(plugin, v)
                    except Exception, e:
                        print >> sys.stderr, 'When setting %s.%s: %s' % (name, attr.name, e)
                    try:
                        del kwargs[attr.name]
                    except:
                        pass

                # Warn about unused variables
                for attr in kwargs.keys():
                    print >> sys.stderr, 'Plugin %s does not have an attribute %s' % (name, attr)
            except:
                traceback.print_exc()
                print >> sys.stderr, 'When trying to add plugin %s' % name
                return
            print 'Loaded plugin "{0.name}" v-{0.version} {0.date} ({0.author[0]} <{0.author[1]}>)'.format(mod)

            # initialize variables used by canvas
            plugin._last_render = 0

            # subscribe to required datasets
            req = getattr(plugin, 'dataset', [])
            for ds in req:
                if not ds in self.dataset:
                    raise RuntimeError, 'Plugin "%s" requires dataset "%s" which is not available' % (name, ds)
                func = plugin.on_data
                try:
                    self.dataset[ds].subscribe(ds, func)
                except Exception, e:
                    traceback.print_exc()
                    raise RuntimeError, 'Plugin "%s" requires dataset "%s" but consumer refused subscription: %s' % (name, ds, str(e))

            self.plugins.append((plugin,mod))
        finally:
            info[0].close()

    def configure(self, widget, event=None):
        with self.drawable():
            glViewport (0, 0, widget.allocation.width, widget.allocation.height);

            # setup othogonal projection matrix with (0,0) in the upper left corner and with a size of 1x1
            glLoadIdentity();
            glOrtho(0, 1, 0, 1, -1.0, 1.0);
            glScalef(1, -1, 1);
            glTranslated(0, -1, 0);

            # notify plugins of the new canvas size
            w = widget.allocation.width
            h = widget.allocation.height / self.rows
            self.size = (widget.allocation.width, widget.allocation.height)
            for plugin, mod in self.plugins:
                plugin.on_resize((w,h))

                # Force a rerender of plugin.
                plugin.render()

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

    def transition(self):
        self.transition_enabled = True
        self.transition_time = time.time()
        return True

    def transition_action(self):
        if self.transition_step > 1.0:
            self.transition_enabled = False
            self.transition_step = 0.0
            self.current = (self.current + 1) % max(self.rows, len(self.plugins))
            return

        # the value is allowed to be > 1.0 (clamped when used) so 1.0 will
        # actually be rendered.

        self.transition_step = ((time.time() - self.transition_time) / 1.5) ** 3

    def expose(self, widget, event=None):
        self.render()

    def render(self):
        plugins = self.visible_plugins()

        # yes, this is fugly, go make a VBO or something.
        dy = 1.0 / self.rows
        y = 0.0
        offset = (-1.0 / self.rows) * min(self.transition_step, 1.0)
        t = time.time()

        with self.drawable() as gldrawable:
            glViewport (0, 0, self.allocation.width, self.allocation.height / self.rows)
            for plugin, mod in self.plugins:
                if plugin.interval < 0: # static content, only rendered when invalidated
                    continue

                frac = 1.0 / plugin.interval

                if t - plugin._last_render < frac:
                    continue

                try:
                    with plugin:
                        plugin.render()
                    plugin._last_render = t
                except:
                    traceback.print_exc()

            glViewport (0, 0, self.allocation.width, self.allocation.height)
            glClearColor(1,0,1,1)
            glClear(GL_COLOR_BUFFER_BIT)

            for i, (plugin, mod) in enumerate(plugins):
                if plugin is not None:
                    plugin.bind()
                    glColor(1,1,1,1)
                else:
                    glBindTexture(GL_TEXTURE_2D, 0)
                    glColor(0,0,0,1)

                real_y = y + offset

                glBegin(GL_QUADS)
                glTexCoord2f(0, 0)
                glVertex3f(0, real_y, 0)

                glTexCoord2f(0, 1)
                glVertex3f(0, real_y+dy, 0)

                glTexCoord2f(1, 1)
                glVertex3f(1, real_y+dy, 0)

                glTexCoord2f(1, 0)
                glVertex3f(1, real_y, 0)
                glEnd()

                y += dy

            if gldrawable.is_double_buffered():
                gldrawable.swap_buffers()
            else:
                glFlush()

    def visible_plugins(self):
        # this block of code gets N plugins from the list (padding if len < N)
        # and wrapping the list when needed
        cur = self.current
        rows = self.rows + 1 # during a transition one extra row is visible
        pad = self.plugins + [(None,None)]*(self.rows-len(self.plugins)) # pad list to number of rows
        plugins = pad[cur:cur+rows]
        if len(plugins) < rows:
            plugins += pad[:rows-len(plugins)]
        return plugins
