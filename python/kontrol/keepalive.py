import json
import logging
import requests

from kontrol.fsm import Aborted, FSM

#: our ochopod logger
logger = logging.getLogger('kontrol')

class Actor(FSM):

    """
    Actor emitting a periodic HTTP POST request against the controlling party. This enables us
    to report relevant information about the pod.
    """

    def __init__(self, cfg):
        super(Actor, self).__init__()

        self.cfg = cfg
        self.path = 'keepalive actor'

    def reset(self, data):

        if self.terminate:
            super(Actor, self).reset(data)

        return 'initial', data, 0.0

    def initial(self, data):
        
        if self.terminate:
            raise Aborted('resetting')

        #
        # - simply HTTP PUT our cfg with a 1 second timeout
        # - default ping frequency is once every 5 seconds
        # - please note any failure to post will be handled with exponential backoff by
        #   the state-machine
        #
        # @todo use TLS
        #
        assert 'controller' in self.cfg['labels'], 'invalid labels (bug?)'
        url = 'http://%s:8000/ping' % self.cfg['labels']['controller']
        state = \
        {
            'ip': self.cfg['ip'],
            'labels': self.cfg['labels']
        }
        logger.debug('%s : PUT /ping -> %s' % (self.path, url))
        resp = requests.put(url, data=json.dumps(state), headers={'Content-Type':'application/json'}, timeout=1.0)
        resp.raise_for_status()
        logger.debug('%s : HTTP %d <- PUT /ping %s' % (self.path, resp.status_code, url))            
        return 'initial', data, 5.0