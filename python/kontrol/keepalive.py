import logging
import requests

from kontrol.fsm import Aborted, FSM


#: our ochopod logger
logger = logging.getLogger('kontrol')

class Actor(FSM):

    """
    """

    def __init__(self, url):
        super(Actor, self).__init__()

        self.path = 'keepalive'
        self.payload = {}
        self.url = url

    def reset(self, data):

        if self.terminate:
            super(Actor, self).reset(data)

        return 'initial', data, 0.0

    def initial(self, data):
        return 'ping', data, 0.0

    def ping(self, data):
        
        if self.terminate:
            raise Aborted('resetting')

        #
        # - send with the state payload
        # - handle errors with exp. backoff
        #
        resp = requests.post(self.url, data=self.payload)
        logger.info('http -> %s -> %s' % (self.url, resp.text))

        return 'ping', data, 1.0