from attribute import attribute, color
from cairo import PluginCairo
from opengl import PluginOpenGL

import os, sys, re
import imp, importlib
import traceback
import itertools
import logging
from glob import glob
from os.path import join, dirname, basename, splitext

def set_attributes(plugin, kwargs):
    attr_table = plugin.attributes()

    # Set all attributes
    for attr in attr_table.values():
        if attr.name not in kwargs and not attr.auto: continue
        v = kwargs.get(attr.name, attr.default)
        if v is None: continue

        try:
            attr.set(plugin, attr.type(v))
        except Exception, e:
            traceback.print_exc()
            plugin.log.error('When setting attibute %s: %s', attr.name, e)

        try:
            del kwargs[attr.name]
        except:
            pass

    # Warn about unused variables
    for attr in kwargs.keys():
        plugin.log.warning('No such attribute: %s', attr)

def load_deps(mod):
    deps = getattr(mod, 'deps', [])
    try:
        iter(deps)
    except TypeError:
        return

    for dep in deps:
        try:
            mod[dep] = importlib.import_module(dep)
        except ImportError, e:
            mod.log.error(e)
            return False
    return True

def load(name, index=0, kwargs={}):
    global search_path

    log = logging.getLogger('%s/%s' % (name, index))

    subpath = os.path.dirname(name)
    name = os.path.basename(name)
    info = imp.find_module(name, [os.path.join(x, subpath) for x in search_path])
    if info[0] == None:
        log.error('No such plugin')
        return None, None

    try:
        mod = imp.load_module(name, *info)
        mod.log = log

        if not hasattr(mod, 'api'):
            log.error('Plugin does not define API')

        # Load all additional libraries
        if not load_deps(mod):
            return None, None

        # Allocate new plugin
        plugin = mod.factory()
        plugin.log = log

        # Initialize plugin
        set_attributes(plugin, kwargs)
        plugin.init()

        plugin.log.info('Loaded plugin "{0.name}" v-{0.version} {0.date} ({0.author[0]} <{0.author[1]}>) from {1[1]}'.format(mod, info))
    except:
        traceback.print_exc()
        print >> sys.stderr, 'When trying to add plugin %s' % name
        return None, None
    finally:
        info[0].close()

    return plugin, mod

def platform_dir():
    try:
        from distutils.util import get_platform
        return 'lib.%s-%s' % (get_platform(), sys.version[0:3])
    except ImportError:
        pass

    # hack based on distutils
    (osname, host, release, version, machine) = os.uname()
    if osname[:5] == "linux":
        return  "lib.%s-%s-%s" % (osname, machine, sys.version[0:3])
    else:
        raise NotImplementedError, 'platform_dir not implemented for this platform, either install distutils or add custom implemenation'

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
    global search_path

    try:
        info = imp.find_module(name, search_path)
    except ImportError, e:
        print >> sys.stderr, e
        return

    try:
        mod = imp.load_module(name, *info)
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

def matching_files():
    global search_path
    patterns = itertools.product(search_path, ['*.py', '*.so'])
    for x in itertools.chain(*[glob(join(*args)) for args in patterns]):
        base = splitext(basename(x))
        dir = dirname(x)
        yield tuple(base + (dir,))

def available():
    global search_path
    ignore = re.compile('sample_|stub')

    for plugin, _, path in matching_files():
        if ignore.match(plugin) is not None: continue

        info = imp.find_module(plugin, search_path)
        try:
            mod = imp.load_module(plugin, *info)
            if not hasattr(mod, 'name'): continue
            yield (plugin, mod.name)
        except:
            traceback.print_exc()
        finally:
            info[0].close()

search_path = [
    'plugins',
    join('build', platform_dir())
]
