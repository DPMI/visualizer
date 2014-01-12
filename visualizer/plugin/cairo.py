from visualizer.plugin.base import PluginBase
from visualizer._cairo import Cairo

class PluginCairo(PluginBase, Cairo):
    def __init__(self):
        PluginBase.__init__(self)
        Cairo.__init__(self, (1,1))

    def on_resize(self, size):
        Cairo.on_resize(self, size)

    def bind_texture(self):
        Cairo.bind_texture(self)

    def render(self, t):
        if not self.is_invalidated(t):
            return False

        Cairo.render(self)
        self._last_render = t
        self._invalidated = False
