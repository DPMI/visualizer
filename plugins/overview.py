from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
from OpenGL.GL import *
from visualizer.picotime import picotime

# metadata
name = 'NPL Overview plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2011-08-16'
version = 1
api = 1

parser = htmlcolor.Parser(factory=htmlcolor.FloatFactory, components=4)

class UI(PluginUI):
    def __init__(self, *args, **kwargs):
        PluginUI.__init__(self, *args, **kwargs)

        self.font = PluginUI.create_font(self.cr, size=16)

        self.ethernet = {}
        self.transport = {}

    def set_ethernet(self, val):
        total = sum(val.values())
        self.ethernet.clear()
        for key, value in val.items():
            if value == 0:
                continue
            frac = float(value) / total
            self.ethernet[key] = frac

    def set_transport(self, val):
        total = sum(val.values())
        self.transport.clear()
        for key, value in val.items():
            if value == 0:
                continue
            frac = float(value) / total
            self.transport[key] = frac

    def do_render(self):
        cr = self.cr
        font = self.font

        self.clear(cr)
        cr.identity_matrix()
        cr.save()

        cr.move_to(5, 5)
        self.text(cr, "<u>Overview</u>", font)

        # ethernet protocols
        cr.translate(25, 35)
        self.render_piechart(self.ethernet, 'Ethernet protocols', size=(self.height*1.25, self.height-35))

        # IP protocols
        cr.translate(150+self.height*1.25, 0)
        self.render_piechart(self.transport, 'IP Protocols', size=(self.height*1.25, self.height-35))

        cr.restore()

class overview(Plugin):
    interval = 1
    dataset = ['overview']

    def __init__(self):
        Plugin.__init__(self)
        self.ui = UI((1,1))

    def on_resize(self, size):
        Plugin.on_resize(self, size)
        self.ui.on_resize(size)

    def on_update(self, consumer):
        global proto_by_number

        ethernet = {'ipv4': 0, 'ipv6': 0, 'arp': 0, 'other': 0}
        transport = {}
        for pkt in consumer:
            if pkt.ipv4:
                ethernet['ipv4'] += 1
                try:
                    proto = proto_by_number[pkt.ipv4.ip_p]
                except:
                    print pkt.ipv4.ip_p
                    traceback.print_exc()
                transport[proto] = transport.get(proto, 0) + 1
            elif pkt.ipv6:
                ethernet['ipv6'] += 1
                continue # not handled by library
            elif pkt.arp_header:
                ethernet['arp'] += 1
                continue
            else:
                ethernet['other'] += 1
                continue

        self.ui.set_ethernet(ethernet)
        self.ui.set_transport(transport)

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
            parts = line.split()
            proto_by_number[int(parts[1])] = parts[0]
init_lut()
