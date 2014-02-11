from . import container
from OpenGL.GL import *
import logging

class HBox(container.Container):
    framerate = 0

    def __init__(self, name, size):
        container.Container.__init__(self)
        self.log = logging.getLogger(name)
        self.children = []
        self.size = size
        self.width = None
        self.factors = None

    def set_width(self, value):
        factors = [float(x) / 100 for x in value.split(';')]
        if sum(factors) != 1:
            raise ValueError, 'Sum of widths must be 100%% (was %.1f%%)' % (sum(factors)*100)
        self.width = value
        self.factors = factors
        self.do_resize()

    def add_child(self, plugin):
        self.children.append(plugin)

        if not self.width:
            self.factors = [1.0 / len(self.children)] * len(self.children)
        else:
            # manually set factors, ensure we have enough of them
            if len(self.children) > len(self.factors):
                self.log.error('Overfull hbox, excessive children will not be visible')
                self.factors.append(0.0)

        self.do_resize()

    def do_resize(self):
        width = [int(self.size[0] * x) for x in self.factors]
        height = self.size[1]
        for i, plugin in enumerate(self.children):
            plugin.on_resize((width[i], height))

    def on_resize(self, size):
        self.size = size
        self.do_resize()

    def invalidate(self):
        pass

    def render(self, t):
        for plugin in self.children:
            plugin.render(t)

    def blit(self):
        glPushMatrix()
        glColor(1,1,1,1)

        for plugin, factor in zip(self.children, self.factors):
            glPushMatrix()
            glScale(factor, 1, 1)

            plugin.bind_texture()
            glDrawArrays(GL_QUADS, 0, 4)

            glPopMatrix()
            glTranslate(factor, 0, 0)
        glPopMatrix()

    def __enter__(self):
        for plugin in self.children:
            plugin.lock()

    def __exit__(self, type, value, traceback):
        for plugin in self.children:
            plugin.unlock()
