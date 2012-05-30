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

class Consumer(object):
    def __init__(self, host, port):
        self.peer = (host,port)
        self.sock = None
        self.sockerr = None
        self.subscriptions = set()
        self._stamp = time.time()
        self.callback = {}
        self.dataset = {}

    def __str__(self):
        state = self.sock is not None and "connected" or ("disconnected: %s" % self.sockerr)
        tmp = self.peer + (state,)
        return '<Consumer %s:%d (%s)>' % tmp

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(self.peer)
        except socket.error, e:
            self.sockerr = e.strerror
            raise
        self.sock = sock

        payload = self.get('/info').get_payload()
        info = json.loads(payload)
        self.dataset = info['dataset']

    def reconnect(self):
        if time.time() - self._stamp < 60:
            return
        self._stamp = time.time()
        print >> sys.stderr, 'Reconnecting to %s:%d' % self.peer
        self.connect()
        for x in self.subscriptions:
            self.subscribe(x, None)

    def get(self, path):
        headers = {
            'Accept': 'application/json',
            'Host': self.peer[0]
        }
        return self.request('GET %s HTTP/1.1' % path, headers)

    def subscribe(self, dataset, callback):
        headers = {
            'Accept': 'application/json',
            'Host': self.peer[0]
        }
        if callback is not None:
            self.callback[dataset] = self.callback.get(dataset,[]) + [callback]
        result = self.request('SUBSCRIBE /dataset/%s HTTP/1.1' % dataset, headers)
        self.subscriptions.add(dataset)
        return result

    def pull(self):
        header = struct.Struct('!I64s')
        raw = self.sock.recv(header.size)

        if raw == '':
            raise socket.error, 'socket shutdown'

        size, name = header.unpack(raw)
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
        [result, data] = buffer.split('\r\n', 1)
        result = result.split(' ')

        if int(result[1]) != 200:
            raise httplib.BadStatusLine(' '.join(result))

        response = FeedParser()
        response.feed(data)
        return response.close()

    def fileno(self):
        if self.sock is None: return None
        return self.sock.fileno()

class Process:
    def __init__(self, command, dataset):
        self.command = shlex.split(command)
        self.dataset = [dataset]
        self.callback = []
        self.proc = None

    def __str__(self):
        return '<Process "%s">' % self.command

    def fileno(self):
        if self.proc is None: return None
        if self.proc.poll() is not None: return None
        return self.proc.stdout.fileno()

    def connect(self):
        self.proc = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def reconnect(self):
        self.connect()

    def subscribe(self, dataset, callback):
        self.callback.append(callback)

    def pull(self):
        data = self.proc.stdout.readline().strip()
        for func in self.callback:
            func(self.dataset[0], data)
