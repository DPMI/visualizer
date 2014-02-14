from visualizer.plugin import PluginCairo, attribute, color
from pango import ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT

name = 'Static text content plugin'
author = ('David Sveningsson', 'ext@sidvind.com')
date = '2013-01-31'
version = 2
api = 1

alignment = {
    'left': ALIGN_LEFT,
    'right': ALIGN_RIGHT,
    'center': ALIGN_CENTER,
    'justify': 'justify',
}

class TextPlugin(PluginCairo):
    """Render static text"""

    framerate = -1

    # added so it wont show up in help
    def source(self):
        pass

    @attribute(name='align', type=str, default='left')
    def set_alignment(self, name):
        global alignment
        val = alignment.get(name.lower(), None)
        if val is None:
            raise ValueError, '%s is not a valid alignment' % name
        self.alignment = val

    @attribute(type=str, sample="monospace 14")
    def font(self, value):
        self.text_font = self.create_font(raw=value)

    @attribute(type=str, sample="sample.txt")
    def filename(self, value):
        """Set text from filename"""
        with open(value) as fp:
            self.content = fp.read()

    @attribute(name='text', type=str, sample="Lorem ipsum dot sit amet")
    def set_text(self, value):
        """Set text from string"""
        self.content = value.replace('\\n', "\n")

    @attribute(type=color, default="(0.95, 0.95, 1.0)")
    def background(self, value):
        self.bgcolor = value

    @attribute(type=color, default="(0.0, 0.0, 0.0)")
    def foreground(self, value):
        self.fgcolor = value

    def __init__(self):
        PluginCairo.__init__(self)
        self.content = ''
        self.text_font = self.create_font(self.cr, size=16)

    # cairo
    def do_render(self):
        self.clear(self.bgcolor)
        self.cr.translate(10,5)

        kwargs = {
            'width': self.width-20,
            'color': self.fgcolor,
        }
        if self.alignment != 'justify':
            kwargs['alignment'] = self.alignment
        else:
            kwargs['justify'] = True

        self.text(self.content, self.text_font, **kwargs)

def factory(**kwargs):
    item = TextPlugin()
    for key, value in kwargs.items():
        getattr(item, key)(value)
    return item
