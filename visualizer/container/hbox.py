from . import container
from OpenGL.GL import *

class HBox(container.Container):
    framerate = 0

    def __init__(self, size):
        self.children = []
        self.size = size

    def add_child(self, plugin):
        self.children.append(plugin)
        self.do_resize()

    def do_resize(self):
        width = self.size[0] / len(self.children)
        height = self.size[1]
        for plugin in self.children:
            plugin.on_resize((width, height))

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
        glScale(1.0 / len(self.children), 1, 1)
        glColor(1,1,1,1)

        for plugin in self.children:
            plugin.bind_texture()
            glDrawArrays(GL_QUADS, 0, 4)
            glTranslate(1, 0, 0)

        glPopMatrix()

    def __enter__(self):
        for plugin in self.children:
            plugin.lock()

    def __exit__(self, type, value, traceback):
        for plugin in self.children:
            plugin.unlock()
