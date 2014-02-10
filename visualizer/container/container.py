class Container(object):
    def __init__(self):
        self.rowspan = 1

    def blit(self):
        raise NotImplementedError

    def on_resize(self, size):
        raise NotImplementedError

    def render(self, t):
        raise NotImplementedError
