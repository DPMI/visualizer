from visualizer.plugin import PluginCairo, attribute, color

name = 'Static text content plugin'
author = ('David Sveningsson', 'ext@sidvind.com')
date = '2013-01-31'
version = 2
api = 1

class TextPlugin(PluginCairo):
    framerate = -1

    @attribute(type=str)
    def text_font(self, value):
        self.font = self.create_font(raw=value)

    @attribute(type=str)
    def filename(self, value):
        with open(value) as fp:
            self.content = fp.read()

    @attribute(type=color, sample="(0.95, 0.95, 1.0, 1.0)")
    def background(self, value):
        self.bgcolor = eval(value)

    @attribute(type=color, sample="(0.0, 0.0, 0.0, 1.0)")
    def foreground(self, value):
        self.fgcolor = eval(value)

    def __init__(self):
        PluginCairo.__init__(self)
        self.content = ''
        self.font = self.create_font(self.cr, size=16)
        self.bgcolor = (0.95, 0.95, 1.0, 1.0)
        self.fgcolor = (0.0, 0.0, 0.0, 1.0)

    # cairo
    def do_render(self):
        self.clear(self.bgcolor)
        self.cr.translate(10,5)
        self.text(self.content, self.font, color=self.fgcolor, justify=True, width=self.width-20)

def factory(**kwargs):
    item = TextPlugin()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
