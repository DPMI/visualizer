from visualizer.plugin.base import PluginBase

name = 'Test: normal'
author = ('David Sveningsson', 'ext-dpmi-visualizer@sidvind.com')
date = '2014-01-21'
version = 1
api = 1
deps = ['missing_library']

class Stub(PluginBase): pass
factory = Stub
