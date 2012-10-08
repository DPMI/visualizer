class Container(object):
    def blit(self):
        raise NotImplementedError

    def on_resize(self, size):
        raise NotImplementedError

    def render(self, t):
        raise NotImplementedError

