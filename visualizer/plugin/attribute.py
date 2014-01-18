# used for attribute type
class color:
    pass

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
