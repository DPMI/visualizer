#!/usr/bin/env python

import json
import time
import sys
from subprocess import Popen, PIPE

while True:
    p1 = Popen(['top', '-bn1'], stdout=PIPE)
    p2 = Popen(["tail", "-n+8"], stdin=p1.stdout, stdout=PIPE)
    p3 = Popen(["head", "-n10"], stdin=p2.stdout, stdout=PIPE)
    output = p3.communicate()[0]
    parsed = [x.split() for x in output.splitlines()]

    print json.dumps(parsed)
    sys.stdout.flush()
    time.sleep(1)
