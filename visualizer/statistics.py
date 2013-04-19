import os
import time
import datetime

class Statistics(object):
    dataset = ['stats']

    def __init__(self):
        self.pipe = os.pipe()
        self.callback = []
        self.start_time = time.time()

    def connect(self):
        pass

    def fileno(self):
        return self.pipe[0]

    def subscribe(self, dataset, callback):
        self.callback.append(callback)

    def pull(self):
        os.read(self.pipe[0], 1)
        for func in self.callback:
            func(self.dataset[0], self.data)

    def update(self, consumers, framerate):
        current_time = time.time()
        uptime = int(current_time - self.start_time)
        m, s = divmod(uptime, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        self.data = [
            ('Time', time.strftime("%d %b %Y %H:%M %Z", time.localtime(current_time))),
            ('Uptime', '%dd %02d:%02d' % (d,h,m)),
            ('Consumers', '%d / %d' % consumers),
            ('Framerate', framerate),
        ]
        os.write(self.pipe[1], '1')

    def __str__(self):
        return '<statistics (built-in)>'
