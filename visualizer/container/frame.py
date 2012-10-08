from . import container
from OpenGL.GL import *

class Frame(container.Container):
    def __init__(self, plugin, mod, size):
        self.plugin = plugin
        self.mod = mod
        self.on_resize(size)

    def on_resize(self, size):
        self.plugin.on_resize(size)
        self.plugin.invalidate()

    def bind_texture(self):
        self.plugin.bind_texture()

    def render(self, t):
        self.plugin.render(t)

    def blit(self):
        self.bind_texture()
        glColor(1,1,1,1)
        glDrawArrays(GL_QUADS, 0, 4)
