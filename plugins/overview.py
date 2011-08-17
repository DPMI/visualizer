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
        self.text(cr, "Overview", font)

        # ethernet protocols
        cr.translate(25, 35)
        self.render_piechart(self.ethernet, 'Ethernet protocols', size=(self.height*1.25, self.height-35))

        # IP protocols
        cr.translate(150+self.height*1.25, 0)
        self.render_piechart(self.transport, 'IP Protocols', size=(self.height*1.25, self.height-35))

        cr.restore()

    def render_piechart(self, segment, graph_title, size, background=None):
        cr = self.cr
        cr.save()

        start = 0.0
        width, height = size
        radius = min(width, height) * 0.5

        if background:
            cr.save()
            cr.set_source_rgba(*background)
            cr.rectangle(0, 0, width, height);
            cr.fill()
            cr.restore()

        def gen_color(str):
            hash = hashlib.md5(str).hexdigest()
            r = int(hash[0:2],16) / 255.0
            g = int(hash[2:4],16) / 255.0
            b = int(hash[4:6],16) / 255.0
            return r,g,b,1
            #hash = zlib.crc32(''.join(reversed(str)))
            #r,g,b = (hash&0x000000ff), (hash&0x0000ff00)>>8, (hash&0x00ff0000)>>16
            #return (float(r)/0xff, float(g)/0xff, float(b)/0xff, 1)

        cr.set_line_width(1.0)
        cr.translate(-width*0.5+radius, 0)
        items = [(title, value, gen_color(title), index) for index, (title, value) in enumerate(segment.items())]
        items.sort(key=lambda x: x[1], reverse=True)
        
        for title, value, color, index in items:
            end = start +  value * (2.0 * math.pi)
            mid = (start + end)*0.5

            cr.save()
            cr.move_to(width/2, height/2 )
            cr.line_to(width/2 + radius * math.cos(start), height/2 + radius * math.sin(start) )
            cr.arc(width/2, height/2, radius, start, end )
            cr.close_path()
      
            cr.set_line_width(1.0)
            cr.set_source_rgba(*color)
            cr.fill_preserve()
            cr.set_source_rgba(0, 0, 0, 1.0 )
            cr.stroke()

            start += (end-start);
        cr.restore()

        cr.save()
        #cr.move_to(0,0)
        cr.translate(width*0.5 + radius + 15, 5)
        cr.set_font_size(16)

        cr.set_source_rgba(0,0,0,1)
        cr.show_text(graph_title)
        cr.translate(0, 15)

        for title, value, color, index in items:
            cr.set_source_rgba(*color)
            cr.rectangle(0, 0, 25, 25)
            cr.fill()
 
            cr.translate(35, 15)
            cr.set_source_rgba(0,0,0,1)
            cr.show_text('%s (%2d%%)' % (title, int(value*100)))
           
            cr.translate(-35, 15)
        cr.restore()

class overview(Plugin):
    name = 'NPL Overview plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-08-16'
    version = 1
    api = 1
    interval = 1

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
                proto = proto_by_number[pkt.ipv4.ip_p]
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
            parts = line.split('\t')
            proto_by_number[int(parts[1])] = parts[0]
init_lut()
