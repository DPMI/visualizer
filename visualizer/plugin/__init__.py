from attribute import attribute, color
from cairo import PluginCairo
from opengl import PluginOpenGL

import os, sys, re
import imp
import traceback
from glob import glob

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

def available():
    ignore = re.compile('sample_|stub')
    for plugin in [os.path.splitext(os.path.basename(x))[0] for x in glob('plugins/*.py')]:
        if ignore.match(plugin) is not None: continue

        info = imp.find_module(plugin, ['plugins'])
        try:
            mod = imp.load_module(plugin, *info)
            if not hasattr(mod, 'name'): continue
            yield (plugin, mod.name)
        except:
            traceback.print_exc()
        finally:
            info[0].close()
