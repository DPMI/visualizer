import time
import math

class picotime:
    def __init__(self, sec, psec):
        self.sec = sec
        self.psec = psec

    @staticmethod
    def now():
        n = time.time()
        sec  = int(math.floor(n))
        psec = picotime._sec_to_psec(n - math.floor(n))
        return picotime(sec, psec)

    def __str__(self):
        return '<picotime %d.%d>' % (self.sec, self.psec)

    def __sub__(self, rhs):
        if not isinstance(rhs, picotime):
            raise TypeError, 'Cannot subtract %s instance from picotime' % rhs.__class__.__name
        
        sec  = self.sec  - rhs.sec
        psec = self.psec - rhs.psec
        return picotime._sec_to_psec(sec) + psec

    def __iadd__(self, psec):
        self.psec += psec
        self.sec  += self.psec / 1000000000000
        self.psec  = self.psec % 1000000000000
        return self

    @staticmethod
    def _sec_to_psec(x):
        return int(x * 1000000000000)
