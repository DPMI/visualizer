import re

# used for attribute type
class color:
    def __init__(self, val):
        if isinstance(val, basestring):
            val = color.from_string(val)

        # append alpha if only using r,g,b
        if len(val) == 3:
            val = val + (1,)

        self.value = val

    @staticmethod
    def from_string(val):
        val = val.strip().lower()

        # (r,g,b) or (r,g,b,a)
        m = re.match(r'\((.*)\)', val)
        if m is not None:
            return tuple([float(x.strip()) for x in m.group(1).split(',')])

        # rrggbb or rrggbbaa
        m = re.match(r'#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})?', val)
        if m is not None:
            return tuple([float(int('0x'+x,16)) / 255.0 for x in m.groups() if x is not None])

        # rgb or rgba
        m = re.match(r'#([0-9a-f])([0-9a-f])([0-9a-f])([0-9a-f])?', val)
        if m is not None:
            return tuple([float(int('0x'+x+x,16)) / 255.0 for x in m.groups() if x is not None])

        raise ValueError, '%s is not a valid color' % val

    def as_tuple(self):
        return self.value

    def __getitem__(self, i):
        return self.value[i]

# prefixed float, e.g. 100M -> 100,000,000
prefix_match = re.compile(r'([\-0-9\.E]+)((?:k|K|M|G|T)(?:iB)?)?$')
prefix_mul = {
    'k': 1e3,
    'm': 1e6,
    'g': 1e9,
    't': 1e12,
    'kib': 2**10,
    'mib': 2**30,
    'gib': 2**40,
    'tib': 2**50,
}
def unprefix(value):
    global prefix_match, prefix_mul

    if not isinstance(value, basestring):
        return value

    match = prefix_match.match(value.strip())
    if not match:
        raise ValueError, 'invalid literal for prefix: %s' % value

    value, prefix = match.groups()
    value = float(value)
    if prefix is not None:
        value *= prefix_mul[prefix.lower()]
    return value

class Attribute():
    # @param name Name of this attribute
    # @param type Datatype
    # @param default Default value (only used if auto is true)
    # @param sample String used for documentation, should be valid configuration.
    # @param auto If false, the attribute isn't initialized using default value.
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
