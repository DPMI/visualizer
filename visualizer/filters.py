from json import loads

def csv(value):
    for line in value.splitlines():
        yield tuple([float(x.strip('\x00')) for x in line.split(';')])

def json(value):
    for row in loads(value):
        yield row

def extract(index, value):
    yield value[index-1]

def split(value):
    yield value.split()
