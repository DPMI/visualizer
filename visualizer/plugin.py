import os, sys
import imp
import traceback
from OpenGL.GL import *
from OpenGL.GL.ARB.framebuffer_object import *
from threading import Lock
from glob import glob
import inspect
import functools
import filters

# easy access
from _cairo import CairoWidget as PluginUI

# used for attribute type
class color:
    pass

class Attribute():
    def __init__(self, func, name=None, type=None, default=None, sample=None):
        self.func = func
        self.name = name is not None and name or func.__name__
        self.doc = func.__doc__
        self.type = type
        self.default = default
        self.sample = sample

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

class Plugin(object):
    def __init__(self):
        self._fbo = None
        self._texture = None
        self._depth = None
        self._current = 0
        self._lock = Lock()

    def lock(self):
        self._lock.acquire()

    def unlock(self):
        self._lock.release()

    def __enter__(self):
        self.lock()

    def __exit__(self, type, value, traceback):
        self.unlock()

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

            self.filter[ds] = lambda x: pipe(x, *flt)

    def on_packet(self, stream, frame):
        pass # do nothing

    def on_update(self, consumer):
        pass # do nothing

    def attributes(self):
        methods = inspect.getmembers(self, lambda x: inspect.ismethod(x) and hasattr(x, '_attribute'))
        return dict([(func._attribute.name, func._attribute) for name, func in methods])

    def on_resize(self, size):
        self._generate_framebuffer(size)

    def render(self):
        glBindFramebuffer(GL_FRAMEBUFFER, self._fbo[self._current])
        self.on_render()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        self._current = 1 - self._current

    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self._texture[self._current])

    def _generate_framebuffer(self, size):
        if self._fbo is None:
            self._fbo = glGenFramebuffers(2)
            self._texture = glGenTextures(2)
            self._depth = glGenTextures(2)

        w = size[0]
        h = size[1]

        try:
            for i in range(2):
                glBindFramebuffer(GL_FRAMEBUFFER, self._fbo[i])
                glBindTexture(GL_TEXTURE_2D, self._texture[i])
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA8, w, h, 0, GL_RGBA, GL_UNSIGNED_INT, None)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
                glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
                glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self._texture[i], 0)

                err = glCheckFramebufferStatus(GL_FRAMEBUFFER);
                if ( err != GL_FRAMEBUFFER_COMPLETE ):
                    raise RuntimeError, "Framebuffer incomplete\n"

            glClearColor(0, 0, 0, 1)
            glClear(GL_COLOR_BUFFER_BIT)
        finally:
            glBindFramebuffer(GL_FRAMEBUFFER, 0)


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
    for plugin in [os.path.splitext(os.path.basename(x))[0] for x in glob('plugins/*.py')]:
        info = imp.find_module(plugin, ['plugins'])
        try:
            mod = imp.load_module('_vis_usage_%s' % plugin, *info)
            if not hasattr(mod, 'name'): continue
            yield (plugin, mod.name)
        except:
            traceback.print_exc()
        finally:
            info[0].close()
