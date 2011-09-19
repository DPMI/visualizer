import socket
import json
from email.message import Message
from email.parser import FeedParser

class Consumer(object):
    def __init__(self, host, port):
        self.peer = (host,port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(('10.0.42.254',80))
    
        print self.get('/info')

    def get(self, path):
        headers = {
            'Acccept': 'application/json',
            'Host': self.peer[0]
        }
        return self.request('GET %s HTTP/1.1' % path, headers)

    def request(self, query, headers):
        # httplib would really help but there isn't any trivial way
        # that I know of to use your own socket with it.
        request = Message()
        for k,v in headers.iteritems():
            request[k] = v
        self.sock.send(query + "\n" + request.as_string())
        response = FeedParser()
        response.feed(self.sock.recv(4096))
        return response.close()
