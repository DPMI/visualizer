from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
import zlib, hashlib
from OpenGL.GL import *
from visualizer.picotime import picotime

parser = htmlcolor.Parser(factory=htmlcolor.FloatFactory, components=4)

class UI(PluginUI):
    def __init__(self, parent, *args, **kwargs):
        PluginUI.__init__(self, *args, **kwargs)

        self.parent = parent
        self.font = PluginUI.create_font(self.cr, size=12)

    def do_render(self):
        cr = self.cr
        font = self.font
        
        self.clear(cr)
        cr.identity_matrix()
        cr.save()

        cr.move_to(5, 5)
        self.text(cr,"""<b>Traffic</b>
Inbound:  {self.inbound}
Outbound: {self.outbound}
""".format(self=self.parent), font)

        cr.restore()

class overview(Plugin):
    name = 'NPL Overview stats plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-08-17'
    version = 1
    api = 1
    interval = 1

    prefix = ['', 'Kb', 'Mb', 'Gb', 'Tb']

    def __init__(self):
        Plugin.__init__(self)
        self.ui = UI(self, (1,1))

        self.inbound_cnt = 0
        self.outbound_cnt = 0
        self.inbound = ''
        self.outbound = ''

    def on_resize(self, size):
        Plugin.on_resize(self, size)
        self.ui.on_resize(size)

    def on_packet(self, stream, pkt):
        self.inbound_cnt += pkt.len

    def on_update(self, consumer):
        n = 0
        tmp = self.inbound_cnt
        while tmp > 900 and n < len(self.prefix):
            tmp /= 1024.0
            n += 1

        self.inbound = '%.2f%s' % (tmp, self.prefix[n])

    def on_render(self):
        glClearColor(1,1,1,1)
        glClear(GL_COLOR_BUFFER_BIT)

        self.ui.invalidate()
        self.ui.render()
        self.ui.display()

def factory():
    return overview()

proto_by_number = {}

def init_lut():
    global proto_by_number

    with open('/etc/protocols') as fp:
        for line in fp:
            line = line.strip()
            if len(line) == 0 or line[0] == '#': continue
            parts = line.split('\t')
            proto_by_number[int(parts[1])] = parts[0]
init_lut()
