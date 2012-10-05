# -*- coding: utf-8; -*-

from plugins.table import Table

name = 'NPL Top Stream  plugin'
author = ('David Sveningsson, Patrik Arlos', 'dsv@bth.se,pal@bth.se')
date = '2011-06-08'
version = 1
api = 1

class TOPstream(Table):
    interval = 1

    def __init__(self):
        Table.__init__(self)
        self.hosts = []

        self.attr_default('title', 'Topstream')
        self.attr_default('header', 'Host;Packets')
        self.attr_default('tabstop', '0;150')

def factory():
    return TOPstream()
