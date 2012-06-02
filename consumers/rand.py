#!/usr/bin/env python

import random
import time
import sys

if len(sys.argv) != 4:
	print >> sys.stderr, 'usage: rand MIN MAX DT'
	sys.exit(1)

min = int(sys.argv[1])
max = int(sys.argv[2])
d = (max-min) / 10
dt = float(sys.argv[3])

t = 0.0
r = 0
while True:
	r += random.randint(-d, d)
	if r > max: r = max
	if r < min: r = min

	x = '%f;%d\n' % (t, r)
	sys.stdout.write(x)
	sys.stdout.flush()
	t += dt
	time.sleep(dt)

