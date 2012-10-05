# -*- coding: utf-8; -*-
from plugins.table import Table

name = 'NPL Statistics plugin'
author = ('David Sveningsson', 'dsv@bth.se')
date = '2012-10-05'
version = 1
api = 1

class statistics(Table):
    def __init__(self):
        Table.__init__(self)
        self.hosts = []
        
        self.attr_default('title', 'Statistics')
        self.attr_default('tabstop', '0;120')
        self.attr_default('source', 'stats')

factory = statistics
