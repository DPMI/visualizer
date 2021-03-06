from visualizer.plugin import PluginCairo, attribute
import cairo

name = 'Static image content plugin'
author = ('David Sveningsson', 'ext@sidvind.com')
date = '2013-01-31'
version = 2
api = 1

class ImagePlugin(PluginCairo):
    """Render a static image"""

    framerate = -1

    # added so it wont show up in help
    def source(self):
        pass

    @attribute(type=str, sample="sample.png")
    def filename(self, value):
        self.content = cairo.ImageSurface.create_from_png(value)
        self.imgw=self.content.get_width()
        self.imgh=self.content.get_height()
        self.imgscale=0.75*self.size[0]/self.imgw
        self.imgxpos=(self.size[0]-self.imgw*self.imgscale)*0.5

    def __init__(self):
        PluginCairo.__init__(self)
        self.content = None
        self.imgw = 0
        self.imgh = 0
        self.imgscale = 0
        self.imgxpos = 0

    def on_resize(self, size):
        PluginCairo.on_resize(self, size)
        if self.content is not None:
            self.imgscale=0.75*self.size[0]/self.imgw
            self.imgxpos=(self.size[0]-self.imgw*self.imgscale)*0.5

    def do_render(self):
        self.clear((0.95, 0.95, 1.0, 1.0))
        if self.content is None: return

        self.cr.translate(self.imgxpos,5)
        self.cr.rectangle(0,0,self.size[0], self.size[1])
        self.cr.scale(self.imgscale,self.imgscale)
        self.cr.set_source_surface(self.content)
        self.cr.paint()

def factory(**kwargs):
    item = ImagePlugin()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
