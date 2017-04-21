import etcd
import json
import logging
import requests

from collections import deque
from kontrol.fsm import Aborted, FSM


#: our ochopod logger
logger = logging.getLogger('kontrol')

class Actor(FSM):

    """
    """

    def __init__(self, cfg):
        super(Actor, self).__init__()

        self.cfg = cfg
        self.client = etcd.Client(host=cfg['etcd'], port=2379)
        self.fifo = deque()
        self.path = 'state actor'

    def reset(self, data):

        if self.terminate:
            super(Actor, self).reset(data)

        return 'initial', data, 0.0

    def initial(self, data):
                
        if self.terminate and not self.fifo:
            raise Aborted('resetting')

        while self.fifo:

            #
            # -
            #
            js = self.fifo[0]
            self.client.write('/kontrol/%s/pods/%s' % (self.cfg['labels']['app'], js['ip']), json.dumps(js), ttl=10)
            logger.debug('%s : etcd <- %s' % (self.path, js))
            self.fifo.popleft()

        return 'initial', data, 0.25

    def specialized(self, msg):
        assert 'request' in msg, 'bogus message received ?'
        req = msg['request']
        if req == 'update':

            #
            # - buffer the incoming payload in our fifo
            # - we'll dequeue it upon the next spin
            #
            assert 'state' in msg, 'invalid message -> "%s" (bug ?)' % msg
            self.fifo.append(msg['state'])
        else:
            super(Actor, self).specialized(msg)
        