import sys
import socket
import json
from email.message import Message
from email.parser import FeedParser
import httplib
import traceback
import struct
import time
import subprocess
import shlex
import errno
import logging

consumer_log = logging.getLogger('consumer')
fifo_log = logging.getLogger('fifo')

class Consumer(object):
    def __init__(self, host, port, index):
        self.peer = (host,int(port))
        self.sock = None
        self.sockerr = None
        self.subscriptions = set()
        self._stamp = time.time()
        self.callback = {}
        self.dataset = {}

        self.log = logging.getLogger('consumer/%s' % str(index))

    def __str__(self):
        state = self.sock is not None and "connected" or ("disconnected: %s" % self.sockerr)
        tmp = self.peer + (state,)
        return '<Consumer %s:%d (%s)>' % tmp

    def connect(self):
        self.log.info('Connecting to %s:%d', *self.peer)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(self.peer)
        except socket.error, e:
            self.log.info('Failed to connect to %s:%d', *self.peer)
            self.sockerr = e.strerror
            raise
        self.sock = sock

        payload = self.get('/info').get_payload()
        info = json.loads(payload)
        self.dataset = info['dataset']
        for ds in self.dataset:
            self.log.info('Dataset "%s" is available', ds)

    def reconnect(self):
        if time.time() - self._stamp < 60:
            return
        self._stamp = time.time()
        self.connect()
        for x in self.subscriptions:
            self.subscribe(x, None)

    def disable(self):
        self.sock = None

    def get(self, path):
        headers = {
            'Accept': 'application/json',
            'Host': self.peer[0]
        }
        return self.request('GET %s HTTP/1.1' % path, headers)

    def subscribe(self, dataset, callback):
        # store callback
        if callback is not None:
            self.callback[dataset] = self.callback.get(dataset,[]) + [callback]

        # check if we are already subscribed
        if dataset in self.subscriptions: return True

        # make new subscription
        headers = {
            'Accept': 'application/json',
            'Host': self.peer[0]
        }
        result = self.request('SUBSCRIBE /dataset/%s HTTP/1.1' % dataset, headers)
        self.subscriptions.add(dataset)
        return result

    def pull(self):
        self.sock.setblocking(False)
        try:
            header = struct.Struct('!I64s')
            raw = self.sock.recv(header.size)
        except socket.error, e:
            if e.errno == errno.EWOULDBLOCK:
                return
            raise
        self.sock.setblocking(True)

        if raw == '':
            self.log.info('Lost connection to %s:%d"', *self.peer)
            raise socket.error, 'socket shutdown'

        try:
            size, name = header.unpack(raw)
        except:
            traceback.print_exc()
            print >> sys.stderr, 'when unpacking', [raw]
            return

        name = name.rstrip('\x00')
        data = self.sock.recv(size)
        for func in self.callback.get(name,[]):
            func(name, data)

    def request(self, query, headers):
        # httplib would really help but there isn't any trivial way
        # that I know of to use your own socket with it.
        request = Message()
        for k,v in headers.iteritems():
            request[k] = v
        self.sock.send(query + "\r\n" + request.as_string())

        buffer = self.sock.recv(4096)
        try:
            [result, data] = buffer.split('\r\n', 1)
        except ValueError:
            traceback.print_exc()
            print >> sys.stderr, 'Buffer:', buffer
            print >> sys.stderr, 'Query:', query
            print >> sys.stderr, 'Headers:', headers
            return False
        result = result.split(' ')

        if int(result[1]) != 200:
            self.log.info('Request failed:', ' '.join(result))
            raise httplib.BadStatusLine(' '.join(result))

        response = FeedParser()
        response.feed(data)
        return response.close()

    def fileno(self):
        if self.sock is None: return None
        return self.sock.fileno()

class Process:
    def __init__(self, command, dataset, index):
        self.command = shlex.split(command)
        self.dataset = [dataset]
        self.callback = []
        self.proc = None
        self.log = logging.getLogger('process/%s' % str(index))

    def __str__(self):
        return '<Process "%s %s">' % (self.command[0], ' '.join(self.command[1:]))

    def fileno(self):
        if self.proc is None: return None
        if self.proc.poll() is not None: return None
        return self.proc.stdout.fileno()

    def connect(self):
        try:
            self.proc = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.log.info('Opened process %d as "%s"', self.proc.pid, ' '.join(self.command))
            self.log.info('Dataset "%s" is available', self.dataset[0])
        except Exception, e:
            traceback.print_exc()
            self.log.info('Failed to execute "%s": %s', ' '.join(self.command), str(e))

    def reconnect(self):
        self.connect()

    def subscribe(self, dataset, callback):
        self.callback.append(callback)

    def pull(self):
        data = self.proc.stdout.readline().strip()
        for func in self.callback:
            func(self.dataset[0], data)
