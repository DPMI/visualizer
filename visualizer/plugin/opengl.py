from visualizer.plugin.base import PluginBase
from visualizer._framebuffer import Framebuffer
from OpenGL.GL import *
from OpenGL.GL.ARB.framebuffer_object import *

class PluginOpenGL(PluginBase):
    def __init__(self):
        PluginBase.__init__(self)
        self.__fbo = self.create_fbo()

    # Creates a framebuffer, override this if you need a custom format, etc
    def create_fbo(self):
        return Framebuffer()

    def on_resize(self, size):
        self.__fbo.resize(size)

    def bind_texture(self):
        self.__fbo.bind_texture()

    def render(self, t):
        if not self.is_invalidated(t):
            return False

        with self.__fbo:
            self.do_render()
        self._last_render = t
        self._invalidated = False

    def clear(self, *color):
        self.__fbo.clear(*color)

    def print_shader_log(self, obj):
        if glIsShader(obj):
            raw = glGetShaderInfoLog(obj)
        else:
            raw = glGetProgramInfoLog(obj)

        for line in raw.splitlines():
            self.log.error(raw)

    @staticmethod
    def shader_type(str):
        if str == 'vertex': return GL_VERTEX_SHADER
        if str == 'fragment': return GL_FRAGMENT_SHADER
        if str == 'geometry': return GL_GEOMETRY_SHADER
        raise ValueError, '%s is not a valid shader type' % str

    def create_shader(self, **source):
        if not glCreateProgram:
            raise RuntimeError, 'Hardware does not support glCreateProgram'
        program = glCreateProgram()

        for k, v in source.iteritems():
            type = PluginOpenGL.shader_type(k)
            shader = glCreateShader(type)

            glShaderSource(shader, v)
            glCompileShader(shader)
            glAttachShader(program, shader)

            self.print_shader_log(shader)

        glLinkProgram(program)
        self.print_shader_log(program)

        return program
