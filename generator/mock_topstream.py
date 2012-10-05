#!/usr/bin/env python
import random
import time
import json
import sys

probability = [random.random()**2 for x in range(1,256)]
hosts = dict([('10.0.0.%d' % x, 0) for x in range(1,256)])

while True:
    for x in range(0,1000):
        index = random.randint(0,254)
        cur = '10.0.0.%d' % (index+1)
        hosts[cur] += probability[index]

    rows = sorted([(key, int(value)) for key, value in hosts.iteritems()], key=lambda x: x[1], reverse=True)[:10]

    sys.stdout.write(json.dumps(rows))
    sys.stdout.write('\n')
    sys.stdout.flush()

    time.sleep(0.25)
