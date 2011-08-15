import pygtk
pygtk.require('2.0')
import gtk
import gtk.gtkgl
import gobject
import imp
import itertools
from OpenGL.GL import *

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
    def __init__(self, config, size):
        gtk.DrawingArea.__init__(self)

        self.rows = 3
        self.plugins = []

        # widget setup
        self.set_gl_capability(config)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.set_size_request(size[0], size[1])
                
        # Connect the relevant signals.
        self.connect_after('realize',   self.realize)
        self.connect('configure_event', self.configure)
        self.connect('expose_event',    self.expose)
        gobject.timeout_add(1000/25, self.expire)

        # setup consumer library
        self.consumer = consumer.Consumer(packets=1024, delay=0.0)

    def add_stream(self, *args, **kwargs):
        self.consumer.add_stream(*args, **kwargs)
    add_stream.__doc__ = consumer.Consumer.add_stream.__doc__

    def drawable(self):
        # this could be implemented in this class, but it is harder to understand "with self" 
        return GLContext(self)

    def add_module(self, name):
        info = imp.find_module(name, ['plugins'])
        if info[0] == None:
            raise IOError, 'No such plugin: %s' % name
        try:
            mod = imp.load_module('_vis__%s' % name, *info)
            plugin = mod.factory()
            print 'Loaded plugin "{0.name}" v{0.version} {0.date} ({0.author[0]} <{0.author[1]}>)'.format(plugin)
            plugin.background('ff00ff')
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
            for plugin, mod in self.plugins:
                plugin.on_resize((w,h))

    def realize(self, widget, event=None):
        with self.drawable():
            glEnable(GL_TEXTURE_2D)

    def expire(self):
        while True:
            stream, frame = self.consumer.poll(timeout=1.0)
            if stream is None:
                break

            for plugin, mod in self.plugins:
                try:
                    plugin.on_packet(stream, frame)
                except:
                    traceback.print_exc()
        
        self.queue_draw()
        return True

    def expose(self, widget, event=None):
        c = [
            (1,0,0,1),
            (1,1,0,1),
            (0,0,1,1),
            (0,1,1,1)
            ]

        with self.drawable() as gldrawable:
            glClearColor(1,0,1,1)
            glClear(GL_COLOR_BUFFER_BIT)
            
            # yes, this is fugly, go make a VBO or something.
            dy = 1.0 / self.rows
            y = 0.0
            for i, (plugin, mod) in itertools.izip_longest(range(self.rows), self.plugins[:self.rows], fillvalue=(None, None)):
                if plugin is not None:
                    try:
                        plugin.render()
                    except:
                        traceback.print_exc()
                    plugin.bind()
                    glColor(1,1,1,1)
                else:
                    glColor(*c[i])

                glBegin(GL_QUADS)
                glTexCoord2f(0, 0)
                glVertex3f(0, y, 0)
                
                glTexCoord2f(0, 1)
                glVertex3f(0, y+dy, 0)
                
                glTexCoord2f(1, 1)
                glVertex3f(1, y+dy, 0)
                
                glTexCoord2f(1, 0)
                glVertex3f(1, y, 0)
                glEnd()
                
                y += dy
                
            if gldrawable.is_double_buffered():
                gldrawable.swap_buffers()
            else:
                glFlush()
