from OpenGL.GL import *
from OpenGL.GL.framebufferobjects import *

class Framebuffer(object):
    def __init__(self, format=GL_RGBA8, depth=True, alpha=True, filter=GL_NEAREST):
        self.format = format
        self.filter = filter
        self.fbo = glGenFramebuffers(1)
        self.color = glGenTextures(2)
        self.depth = None
        self.current = 0

        if depth:
            self.depth = glGenTextures(1)

        self.resize((1,1))

    def resize(self, size):
        self._generate_framebuffer(size)

    def bind_texture(self):
        glBindTexture(GL_TEXTURE_2D, self.color[1-self.current])

    def _generate_framebuffer(self, size):
        for target in self.color:
            glBindTexture(GL_TEXTURE_2D, target)
            glTexImage2D(GL_TEXTURE_2D, 0, self.format, size[0], size[1], 0, self.format == GL_RGB8 and GL_RGB or GL_RGBA, GL_UNSIGNED_INT, None)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, self.filter)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, self.filter)

        if self.depth:
            glBindTexture(GL_TEXTURE_2D, self.depth)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT24, size[0], size[1], 0, GL_DEPTH_COMPONENT, GL_UNSIGNED_BYTE, None)

        with self:
            if self.depth: glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, self.depth, 0)

            status = glCheckFramebufferStatus(GL_FRAMEBUFFER)
            if status != GL_FRAMEBUFFER_COMPLETE:
                raise RuntimeError, 'Framebuffer not complete, status: %d' % status

            glEnable(GL_TEXTURE_2D)
            glDisable(GL_CULL_FACE)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)

        # clear first buffer
        with self:
            self.clear(0,0,0,1)

        # clear second buffer
        with self:
            self.clear(0,0,0,1)

    def __enter__(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.color[self.current], 0);
        return self

    def __exit__(self, type, value, traceback):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        self.current = 1 - self.current

    def clear(self, *color):
        glClearColor(*color)
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
