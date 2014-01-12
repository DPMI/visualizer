# -*- coding: utf-8; -*-

from visualizer.plugin import PluginOpenGL, attribute
from OpenGL.GL import *
from ctypes import c_void_p
import numpy as np
import time

name = 'Sample OpenGL plugin'
author = ('David Sveningsson', 'ext-dpmi-visualizer@sidvind.com')
date = '2014-01-12'
version = 0
api = 1

# Vertex shader
# Input geometry is in clip-space already, thus ignoring need for
# transformation. UV is generated evenly.
vs = """
#version 330 core

in vec2 in_pos;
out vec2 texcoord;

void main() {
  texcoord = in_pos.xy * vec2(0.5,0.5) + vec2(0.5,0.5); // [-1,1] -> [0,1]
  gl_Position = vec4(in_pos.xy,0.0,1.0);
}
"""

# Fragment shader
fs = """
#version 330 core
#define PI 3.1415926535897932384626433832795

uniform float t;
in vec2 texcoord;
out vec4 ocolor;
const float k = 7.0f;

// simple plasma-like effect
void main(){
  vec2 c = texcoord * k-k/2.0;
  c.x *= 5.0;

  float v = 0.0;
  v += sin((c.x+t));
  v += sin((c.y+t)/2.0);
  v += sin((c.x+c.y+t)/2.0);
  c += k/2.0 * vec2(sin(t/3.0), cos(t/2.0));
  v += sin(sqrt(c.x*c.x+c.y*c.y+1.0)+t);
  v = v/2.0;

  vec3 c1 = vec3(1,sin(PI*v),cos(PI*v));
  vec3 c2 = vec3(sin(PI*v), sin(PI*v+2.0*PI/3), sin(PI*v+4*PI/3));

  float s = smoothstep(0,1,sin(t*0.5)*0.5+0.5);
  ocolor = vec4(mix(c1,c2,s),1);
}
"""

# Geometry data in clip-space
vertices = np.array([
    # x y
     1,  1,
    -1,  1,
     1, -1,
    -1, -1,
], np.float32)

class MyPlugin(PluginOpenGL):
    framerate = 0

    def __init__(self):
        PluginOpenGL.__init__(self)
        self.ref = time.time()

    def init(self):
        global vs, fs, vertices
        glDisable(GL_CULL_FACE)

        # create simple shader
        self.shader = self.create_shader(vertex=vs, fragment=fs)
        glBindAttribLocation(self.shader, 0, "in_pos")
        self.t = glGetUniformLocation(self.shader, "t")

        # create simple VBO
        self.buffer = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.buffer)
        glBufferData(GL_ARRAY_BUFFER, 4 * len(vertices), vertices, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)

    def do_render(self):
        global vertices
        stride = 4 * 2 # 2 floats per vertex

        d = self._last_render - self.ref
        self.clear(0,1,1,1)
        try:
            glUseProgram(self.shader)
            glUniform1f(self.t, d)
            glBindBuffer(GL_ARRAY_BUFFER, self.buffer)
            glEnableVertexAttribArray(0)
            glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, stride, c_void_p(0))
            glDrawArrays(GL_TRIANGLE_STRIP, 0, len(vertices))
        finally:
            glDisableVertexAttribArray(0)
            glBindBuffer(GL_ARRAY_BUFFER, 0)
            glUseProgram(0)

factory = MyPlugin
