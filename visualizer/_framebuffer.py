from OpenGL.GL import *
from OpenGL.GL.framebufferobjects import *

class Framebuffer(object):
    def __init__(self):
        self._fbo = None
        self._texture = None
        self._current = 0
        self._generate_framebuffer((1,1))

    def resize(self, size):
        self._generate_framebuffer(size)

    def bind_texture(self):
        glBindTexture(GL_TEXTURE_2D, self._texture[self._current])

    def _generate_framebuffer(self, size):
        if self._fbo is None:
            self._fbo = glGenFramebuffers(2)
            self._texture = glGenTextures(2)

        w = size[0]
        h = size[1]

        try:
            for i in range(2):
                glBindFramebuffer(GL_FRAMEBUFFER, self._fbo[i])
                glBindTexture(GL_TEXTURE_2D, self._texture[i])
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_INT, None)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self._texture[i], 0)

                err = glCheckFramebufferStatus(GL_FRAMEBUFFER);
                if ( err != GL_FRAMEBUFFER_COMPLETE ):
                    raise RuntimeError, "Framebuffer incomplete\n"

            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)
        finally:
            glBindFramebuffer(GL_FRAMEBUFFER, 0)

    def __enter__(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self._fbo[self._current])
        return self

    def __exit__(self, type, value, traceback):
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        self._current = 1 - self._current
