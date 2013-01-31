from visualizer.plugin import PluginCairo, attribute, color

name = 'Static text content plugin'
author = ('David Sveningsson', 'ext@sidvind.com')
date = '2013-01-31'
version = 2
api = 1

class TextPlugin(PluginCairo):
    """Render static text"""

    framerate = -1

    # added so it wont show up in help
    def source(self):
        pass

    @attribute(type=str, sample="monospace 14")
    def font(self, value):
        self.text_font = self.create_font(raw=value)

    @attribute(type=str, sample="sample.txt")
    def filename(self, value):
        with open(value) as fp:
            self.content = fp.read()

    @attribute(type=color, default="(0.95, 0.95, 1.0, 1.0)")
    def background(self, value):
        self.bgcolor = eval(value)

    @attribute(type=color, default="(0.0, 0.0, 0.0, 1.0)")
    def foreground(self, value):
        self.fgcolor = eval(value)

    def __init__(self):
        PluginCairo.__init__(self)
        self.content = ''
        self.text_font = self.create_font(self.cr, size=16)

    # cairo
    def do_render(self):
        self.clear(self.bgcolor)
        self.cr.translate(10,5)
        self.text(self.content, self.text_font, color=self.fgcolor, justify=True, width=self.width-20)

def factory(**kwargs):
    item = TextPlugin()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
