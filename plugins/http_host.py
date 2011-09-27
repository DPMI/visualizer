# -*- coding: utf-8; -*-

from visualizer.plugin import Plugin, attribute, PluginUI
import math
import traceback
import sqlite3
from socket import ntohs, ntohl
from OpenGL.GL import *

class HTTPHost(Plugin, PluginUI):
    name = 'NPL HTTP host detection plugin'
    author = ('David Sveningsson', 'dsv@bth.se')
    date = '2011-06-08'
    version = 0
    api = 1
    interval = 60
    dataset = ['http_hostname']

    def __init__(self):
        Plugin.__init__(self)
        PluginUI.__init__(self, size=(1,1))
        
        self.font_a = PluginUI.create_font(self.cr, size=16)
        self.font_b = PluginUI.create_font(self.cr, size=12)
        self.hosts = sqlite3.connect(':memory:')
        self.hosts.execute("CREATE TABLE hosts (host TEXT PRIMARY KEY, hit INT default 1)")
        self.tmp = []

    def on_resize(self, size):
        Plugin.on_resize(self, size)
        PluginUI.on_resize(self, size)
    
    def on_packet(self, stream, pkt):
        if not pkt.tcphdr or \
           ntohs(pkt.tcphdr.dest) != 80 or\
           len(pkt.payload) == 0:
            return

        raw = str(pkt.payload)
        if raw[:3] != 'GET': # only handle GET
            return

        lines = raw.splitlines()[1:] # ignore request
        headers = dict([tuple(x.split(': ',1)) for x in lines if ':' in x])

        if 'Host' in headers:
            host = headers['Host']
            self.tmp.append(host)

    # cairo
    def do_render(self):
        cr = self.cr
        cr.save()
        self.clear(cr, (1,1,1,1))

        cr.translate(5,5)
        self.text(cr, "<u>Top HTTP hostnames</u>", self.font_a)


        # fulhack!
        if len(self.tmp) > 0:
            cur = self.hosts.cursor()
            for host in self.tmp:
                cur.execute('UPDATE hosts SET hit = hit+1 WHERE host = ?', (host,))
                if cur.rowcount == 0:
                    cur.execute('INSERT INTO hosts (host) VALUES (?)', (host,))
            self.tmp = []

        
        for host, hits in self.hosts.execute('SELECT host, hit FROM hosts ORDER BY hit DESC LIMIT 10').fetchall():
            cr.translate(0,25)
            self.text(cr, "%s (%d hits)" % (host, hits), self.font_b)

        cr.restore()

    def on_resize(self, size):
        PluginUI.on_resize(self, size)

    # plugin
    def render(self):
        PluginUI.invalidate(self)
        PluginUI.render(self)

    def bind(self):
        PluginUI.bind_texture(self)

    def _generate_framebuffer(self, size):
        pass # do not want

def factory():
    return HTTPHost()
