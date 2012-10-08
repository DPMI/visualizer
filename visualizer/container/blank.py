from . import container
from OpenGL.GL import *

class Blank(container.Container):
    """Stub container"""

    def render(self, t):
        pass

    def on_resize(self, size):
        pass

    def blit(self):
        glBindTexture(GL_TEXTURE_2D, 0)
        glColor(0,0,0,1)
        glDrawArrays(GL_QUADS, 0, 4)
