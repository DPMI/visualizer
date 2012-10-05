from visualizer.plugin import PluginOpenGL, attribute

name = 'NPL stub plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2011-08-15'
version = 0
api = 1

class Stub(PluginOpenGL):
    def __init__(self):
        PluginOpenGL.__init__(self)
        self.color = (0,1,1,1)

    def do_render(self):
        glClearColor(*self.color)
        glClear(GL_COLOR_BUFFER_BIT)

def factory():
    return Stub()
