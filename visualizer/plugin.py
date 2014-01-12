import os, sys, re
import imp
import traceback
from OpenGL.GL import *
from OpenGL.GL.ARB.framebuffer_object import *
from threading import Lock
from glob import glob
import inspect
import functools
import filters

from _cairo import Cairo
from _framebuffer import Framebuffer

# used for attribute type
class color:
    pass

class Attribute():
    def __init__(self, func, name=None, type=None, default=None, sample=None, auto=True):
        self.func = func
        self.name = name is not None and name or func.__name__
        self.doc = func.__doc__
        self.type = type
        self.default = default
        self.sample = sample
        self.auto = auto

    def __str__(self):
        return '<Attribute %s>' % self.name

    def set(self, plugin, value):
        if value is None: return # users cannot set None in config, None is passed if default is unset.
        self.func(plugin, value)

    def get_config(self):
        if self.sample is not None:
            return '%s = %s' % (self.name, self.sample)

        if self.default is not None:
            return '%s = %s' % (self.name, self.default)

        return '# %s = ' % (self.name, )

def attribute(*args, **kwargs):
    def wrapper(func):
        func._attribute = Attribute(func, *args, **kwargs)
        return func
    return wrapper

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

class PluginOpenGL(PluginBase):
    def __init__(self):
        PluginBase.__init__(self)
        self.__fbo = self.create_fbo()

    # Creates a framebuffer, override this if you need a custom format, etc
    def create_fbo(self):
        return Framebuffer()

    def on_resize(self, size):
        self.__fbo.resize(size)

    def bind_texture(self):
        self.__fbo.bind_texture()

    def render(self, t):
        if not self.is_invalidated(t):
            return False

        with self.__fbo:
            self.do_render()
        self._last_render = t
        self._invalidated = False

    def clear(self, *color):
        self.__fbo.clear(*color)

def trim(docstring):
    """Parse docstring. From python docs."""
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

def usage(name):
    try:
        info = imp.find_module(name, ['plugins'])
    except ImportError, e:
        print >> sys.stderr, e
        return

    try:
        mod = imp.load_module('_vis_usage_%s' % name, *info)
        plugin = mod.factory()
        if not hasattr(mod, 'name'):
            print 'No such plugin:', name

        print mod.name
        print '-' * len(mod.name)
        print trim(plugin.__doc__)
        print
        print 'Attributes'
        print '----------'
        for attr in plugin.attributes().values():
            print
            print ' - %s (type: %s, default: %s)' % (attr.name, attr.type.__name__, attr.default is None and 'unset' or attr.default)
            if attr.doc:
                for line in trim(attr.doc).splitlines():
                    print '   %s' % line.strip()
        print
        print 'Sample'
        print '------'
        print '[plugin:%s/0]' % name
        for attr in plugin.attributes().values():
            print attr.get_config()

    except:
        traceback.print_exc()
    finally:
        info[0].close()

def available():
    ignore = re.compile('sample_|stub')
    for plugin in [os.path.splitext(os.path.basename(x))[0] for x in glob('plugins/*.py')]:
        if ignore.match(plugin) is not None: continue

        info = imp.find_module(plugin, ['plugins'])
        try:
            mod = imp.load_module('_vis_usage_%s' % plugin, *info)
            if not hasattr(mod, 'name'): continue
            yield (plugin, mod.name)
        except:
            traceback.print_exc()
        finally:
            info[0].close()
