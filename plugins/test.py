from visualizer.plugin import Plugin, attribute
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *

parser = htmlcolor.Parser(factory=htmlcolor.FloatFactory, components=4)

class picotime:
    def __init__(self, sec, psec):
        self.sec = sec
        self.psec = psec

    @staticmethod
    def now():
        n = time.time()
        sec  = int(math.floor(n))
        psec = picotime._sec_to_psec(n - math.floor(n))
        return picotime(sec, psec)

    def __str__(self):
        return '<picotime %d.%d>' % (self.sec, self.psec)

    def __sub__(self, rhs):
        if not isinstance(rhs, picotime):
            raise TypeError, 'Cannot subtract %s instance from picotime' % rhs.__class__.__name
        
        sec  = self.sec  - rhs.sec
        psec = self.psec - rhs.psec
        return picotime._sec_to_psec(sec) + psec

    def __iadd__(self, psec):
        self.psec += psec
        self.sec  += self.psec / 1000000000000
        self.psec  = self.psec % 1000000000000
        return self

    @staticmethod
    def _sec_to_psec(x):
        return int(x * 1000000000000)

class Test(Plugin):
    name = 'NPL Test plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-06-08'
    version = 0
    api = 1

    # How often this plugin needs to render
    # -1 Static content (only redrawn on expose)
    #  0 As often as possible (i.e. realtime)
    #  N Fixed framerate (requests N frames per second)
    interval = -1

    @attribute(type=str)
    def background(self, value):
        self.color = parser.parse(value)

    @attribute(type=int)
    def rate(self, value):
        self._rate = value

    def __init__(self):
        Plugin.__init__(self)
        self.color = (1,1,1,1)
        self._rate = 100
        self.time = picotime.now()
        self._accum = 0
    
    def on_packet(self, stream, frame):
        ts = picotime(frame.tv_sec, frame.tv_psec)

        delta = ts - self.time
        rate = self._rate * 1000000000
        
        if delta > rate:
            self.time += rate
            m = 1000.0 / self._rate
            print m
            print 'tick', '%.2fKb/s' % ((self._accum * m) / 1024)
            self._accum = 0

        self._accum += frame.len
        #print self._cur - frame.timestamp
        #if self._cur is None or self._cur - frame.timestamp > self
        #print self._accum

    def on_render(self):
        glClearColor(*self.color)
        glClear(GL_COLOR_BUFFER_BIT)

def factory():
    return Test()
