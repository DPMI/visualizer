from OpenGL.GL import *

class HBox(object):
    framerate = 0

    def __init__(self):
        self.children = []

    def add_child(self, plugin, mod):
        self.children.append((plugin, mod))

    def invalidate(self):
        pass

    def render(self):
        for plugin, mod in self.children:
            plugin.render()
        return True

    def blit(self):
        glBindTexture(GL_TEXTURE_2D, 0)
        # self.bind_texture()
        glColor(1,0,1,1)
        glDrawArrays(GL_QUADS, 0, 4)

    def __enter__(self):
        for plugin, mod in self.children:
            plugin.lock()

    def __exit__(self, type, value, traceback):
        for plugin, mod in self.children:
            plugin.unlock()
