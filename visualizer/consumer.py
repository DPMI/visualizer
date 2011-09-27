import socket
import json
from email.message import Message
from email.parser import FeedParser
import httplib

class Consumer(object):
    def __init__(self, host, port):
        self.peer = (host,port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
    
        payload = self.get('/info').get_payload()
        info = json.loads(payload)
        
        self.dataset = info['dataset']

    def get(self, path):
        headers = {
            'Accept': 'application/json',
            'Host': self.peer[0]
        }
        return self.request('GET %s HTTP/1.1' % path, headers)

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
