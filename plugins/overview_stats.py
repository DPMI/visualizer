from visualizer.plugin import Plugin, attribute, PluginUI
import htmlcolor
import time, calendar
import math
import traceback
from socket import ntohs, getservbyport
from OpenGL.GL import *
from visualizer.picotime import picotime

parser = htmlcolor.Parser(factory=htmlcolor.FloatFactory, components=4)

class UI(PluginUI):
    def __init__(self, parent, *args, **kwargs):
        PluginUI.__init__(self, *args, **kwargs)

        self.parent = parent
        self.font = PluginUI.create_font(self.cr, size=12)
        self.proto = {}

    def set_proto(self, val):
        total = sum(val.values())
        self.proto.clear()
        for key, value in val.items():
            if value == 0:
                continue
            frac = float(value) / total
            self.proto[key] = frac

    def do_render(self):
        cr = self.cr
        font = self.font
        
        self.clear(cr)
        cr.identity_matrix()
        cr.save()

        # default location
        cr.move_to(5, 5)

        # ethernet protocols
        cr.translate(25, 35)
        self.render_piechart(self.proto, 'TCP/UDP protocols', size=(self.height*1.25, self.height-35))

        cr.identity_matrix()
        cr.move_to(150+self.height*1.25, 25)
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

        global tcpserv_by_port
        proto = {}
        for pkt in consumer:
            if not pkt.tcphdr:
                continue

            port = ntohs(pkt.tcphdr.dest)
            serv = tcpserv_by_port.get(port, 'port %d' % port)
            proto[serv] = proto.get(serv, 0) + pkt.len

        self.ui.set_proto(proto)

    def on_render(self):
        glClearColor(1,1,1,1)
        glClear(GL_COLOR_BUFFER_BIT)

        self.ui.invalidate()
        self.ui.render()
        self.ui.display()

def factory():
    return overview()

tcpserv_by_port = {}
udpserv_by_port = {}

def init_lut():
    global tcpserv_by_port
    global udpserv_by_port

    with open('/etc/services') as fp:
        for line in fp:
            line = line.strip().replace('\t', ' ')
            if len(line) == 0 or line[0] == '#': continue
            parts = [x for x in line.split(' ') if len(x.strip()) > 0]
            [port, proto] = parts[1].split('/')
            if proto == 'tcp': tcpserv_by_port[int(port)] = parts[0]
            if proto == 'udp': udpserv_by_port[int(port)] = parts[0]
init_lut()
