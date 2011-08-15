from visualizer.plugin import Plugin, attribute
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *

class Stub(Plugin):
    name = 'NPL stub plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-08-15'
    version = 0
    api = 1
    interval = -1

    def __init__(self):
        Plugin.__init__(self)
        self.color = (0,1,1,1)
    
    def on_render(self):
        glClearColor(*self.color)
        glClear(GL_COLOR_BUFFER_BIT)

def factory():
    return Stub()
