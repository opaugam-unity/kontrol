import json
import logging
import requests
import time

from kontrol.fsm import Aborted, FSM
from os.path import isfile


#: our ochopod logger
logger = logging.getLogger('kontrol')


class Actor(FSM):

    """
    Actor emitting a periodic HTTP POST request against the controlling party. This enables us
    to report relevant information about the pod. The pod UUID is derived from its IPv4 address
    and launch time shortened via base 62 encoding.
    """

    tag = 'keepalive'

    def __init__(self, cfg):
        super(Actor, self).__init__()

        self.cfg = cfg
        self.path = '%s actor' % self.tag

    def reset(self, data):

        if self.terminate:
            super(Actor, self).reset(data)

        return 'initial', data, 0.0

    def initial(self, data):
        
        if self.terminate:
            raise Aborted('resetting')

        #
        # -
        #
        assert 'master' in self.cfg['labels'], 'invalid labels, "master" missing (bug?)'
        state = \
        {
            'id': self.cfg['id'],
            'ip': self.cfg['ip'],
            'role': self.cfg['labels']['role'],
            'payload': {}
        }

        #
        # - $KONTROL_PAYLOAD is optional and can be set to point to a file
        #   on disk that contains json user-data (for instance some statistics)
        # - this free-form payload will be included in the keepalive HTTP PUT,
        #   persisted in etcd and made available to the callback script
        #
        if 'payload' in self.cfg:
            try:
                with open(self.cfg['payload'], 'r') as f:
                    state['payload'] = json.loads(f.read())
        
            except IOError:
                pass
            except ValueError:
                pass

        #
        # - simply HTTP PUT our cfg with a 1 second timeout
        # - the ping frequency is once every TTL * 0.75 seconds
        # - please note any failure to post will be handled with exponential backoff by
        #   the state-machine
        #
        # @todo use TLS
        #
        ttl = int(self.cfg['ttl'])
        url = 'http://%s:8000/ping' % self.cfg['labels']['master']
        resp = requests.put(url, data=json.dumps(state), headers={'Content-Type':'application/json'}, timeout=1.0)
        resp.raise_for_status()
        logger.debug('%s : HTTP %d <- PUT /ping %s' % (self.path, resp.status_code, url))            
        return 'initial', data, ttl * 0.75