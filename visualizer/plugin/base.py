from visualizer.plugin.attribute import attribute
import visualizer.filters as filters
from threading import Lock
import inspect
import functools

class PluginBase(object):
    # Rendering framerate
    #    -1: Static content, only rendered once
    #     0: Rendered every frame
    #  1..N: Rendered at N frames per second
    framerate = -1

    def __init__(self):
        self._lock = Lock()
        self.filter = {}
        self.dataset = []
        self._invalidated = True
        self._last_render = 0

        methods = inspect.getmembers(self, lambda x: inspect.ismethod(x) and hasattr(x, '_attribute'))
        self._attributes = dict([(func._attribute.name, func._attribute) for name, func in methods])

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def __enter__(self):
        self.lock()

    def __exit__(self, type, value, traceback):
        self.unlock()

    def attr_default(self, name, value):
        """Change the attribute default value
        Useful for plugins which inherits from other plugins but want a different default value"""
        try:
            self._attributes[name].default = value
        except KeyError:
            raise AttributeError, "'%s'" % name

    @attribute(type=int, name='framerate', default=-1, auto=False)
    def set_framerate(self, value):
        """Override rendering framerate."""
        self.framerate = int(value)

    @attribute(type=str, sample="NAME:csv:extract(2)")
    def source(self, value):
        """Datasource for histogram.
        Format: DATASET:FILTER..."""
        for pair in value.split(';'):
            p = pair.split(':')
            ds = p[0]
            self.dataset.append(ds)

            flt = []
            for func in p[1:]:
                args = None
                if '(' in func:
                    i = func.index('(')
                    args = eval(func[i:]) # this works because "(..)" in "foo(..)" happens to be a interpretable as a tuple
                    if not isinstance(args,tuple): args = (args,) # happens when there is only a single arg
                    func = func[:i]

                func = filters.__dict__[func]
                if args:
                    func = functools.partial(func, *args)
                flt.append(func)

            def pipe(value, func, *remaining):
                for x in func(value):
                    if len(remaining) == 0:
                        yield x
                    else:
                        for y in pipe(x, *remaining):
                            yield y

            if len(flt) == 0:
                func = lambda x: x
            elif len(flt) == 1:
                func = flt[0]
            else:
                func = lambda x: pipe(x, *flt)

            self.filter[ds] = func

    def invalidate(self):
        self._invalidated = True

    def is_invalidated(self, t):
        if self.framerate > 0:
            frac = 1.0 / self.framerate
            dt = t - self._last_render
            if dt >= frac: return True
        elif self.framerate == 0:
            return True

        return self._invalidated

    # Called after all attributes has been setup
    def init(self):
        pass # do nothing

    def on_packet(self, stream, frame):
        pass # do nothing

    def on_update(self, consumer):
        pass # do nothing

    def attributes(self):
        return self._attributes

    def on_resize(self, size):
        raise NotImplementedError

    def render(self, t):
        raise NotImplementedError

    def bind_texture(self):
        raise NotImplementedError
