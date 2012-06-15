from OpenGL.GL import *
from OpenGL.GL.ARB.framebuffer_object import *
from threading import Lock

# easy access
from _cairo import CairoWidget as PluginUI

class Attribute():
    def __init__(self, name, doc, type=None, default=None, sample=None):
        self.name = name
        self.doc = doc
        self.type = type
        self.default = default
        self.sample = sample

    def __str__(self):
        return '<Attribute %s>' % self.name

    def get_config(self):
        if self.sample is not None:
            return '%s = %s' % (self.name, self.sample)

        if self.default is not None:
            return '%s = %s' % (self.name, self.default)

        return '# %s = ' % (self.name, )

def attribute(*args, **kwargs):
    def wrapper(func):
        func._attribute = Attribute(func.__name__, func.__doc__, *args, **kwargs)
        return func
    return wrapper

class Plugin(object):
    def __init__(self):
        self._fbo = None
        self._texture = None
        self._depth = None
        self._current = 0
        self._lock = Lock()

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def __enter__(self):
        self.lock()

    def __exit__(self, type, value, traceback):
        self.unlock()

    def on_packet(self, stream, frame):
        pass # do nothing

    def on_update(self, consumer):
        pass # do nothing

    def attributes(self):
        return [x._attribute for x in self.__class__.__dict__.values() if hasattr(x, '_attribute')]

    def on_resize(self, size):
        self._generate_framebuffer(size)

    def render(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self._fbo[self._current])
        self.on_render()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        self._current = 1 - self._current

    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self._texture[self._current])

    def _generate_framebuffer(self, size):
        if self._fbo is None:
            self._fbo = glGenFramebuffers(2)
            self._texture = glGenTextures(2)
            self._depth = glGenTextures(2)

        w = size[0]
        h = size[1]

        try:
            for i in range(2):
                glBindFramebuffer(GL_FRAMEBUFFER, self._fbo[i])
                glBindTexture(GL_TEXTURE_2D, self._texture[i])
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_INT, None)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self._texture[i], 0)

                err = glCheckFramebufferStatus(GL_FRAMEBUFFER);
                if ( err != GL_FRAMEBUFFER_COMPLETE ):
                    raise RuntimeError, "Framebuffer incomplete\n"

            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)
        finally:
            glBindFramebuffer(GL_FRAMEBUFFER, 0)
