import os
import re
import itertools
import ConfigParser as configparser
from functools import wraps

# optional yaml support
try:
    import yaml
except ImportError:
    yaml = None

# Emulates the behaviour of SafeConfigParser but uses "section/option" path
# instead of two keys and supports default values.
class ConfigParser(configparser.SafeConfigParser):
    def get(self, path, default=None):
        [section, option] = path.split('/')
        try:
            return configparser.SafeConfigParser.get(self, section, option)
        except (configparser.NoOptionError, configparser.NoSectionError):
            if default is not None:
                return default
            raise

    def getint(self, path, default=None):
        return int(self.get(path, default))

    def getfloat(self, path, default=None):
        return float(self.get(path, default))

    def getboolean(self, path, default):
        val = self.get(path, repr(default)).lower()
        return val in ['1', 'true', 'yes', 'on']

    def has_option(self, path):
        [section, option] = path.split('/')
        return configparser.SafeConfigParser.has_option(self, section, option)

    def components(self, filter):
        pattern = re.compile('(?:(\w+):)?(\w+)(?:/(\w+))?')
        for section in self.sections():
            x = pattern.match(section)
            if x is None: continue

            ns, key, index = x.groups()
            if ns is None: ns = key
            if ns != filter: continue
            if index is None: index = '0'

            d = dict(self.items(section))
            d.update({
                'type': key,
                'name': index,
            })
            yield d

    def plugins(self):
        return self.components('plugin')

    def consumers(self):
        return itertools.chain(self.components('consumer'), self.components('process'))

    def hbox(self):
        return self.components('hbox')

class YamlConfig(object):
    def __init__(self, obj):
        self.obj = obj

    def get(self, path, default=None):
        d = self.obj
        try:
            for c in path.split('/'):
                d = d[c]
            return d
        except KeyError:
            if default is not None:
                return default
            raise

    def getint(self, path, default=None):
        return int(self.get(path, default))

    def getfloat(self, path, default=None):
        return float(self.get(path, default))

    def getboolean(self, path, default):
        return bool(self.get(path, default))

    def has_option(self, path):
        try:
            self.get(path)
            return True
        except KeyError:
            return False

    def plugins(self):
        return self.obj.get('plugins', []) or []

    def consumers(self):
        return self.obj.get('consumers', []) or []

    def hbox(self):
        return self.obj.get('hbox', []) or []

def read(filename):
    ext = os.path.splitext(filename)[1]

    if ext in ['.yml', '.yaml']:
        if not yaml: raise ValueError, 'Python without YAML support, install python-yaml'
        return YamlConfig(yaml.load(open(filename).read(), Loader=yaml.Loader))
    else:
        cfg = ConfigParser()
        cfg.read(filename)
        return cfg
