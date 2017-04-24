import json
import logging
import requests
import string
import struct

from kontrol.fsm import Aborted, FSM
from math import floor
from os.path import isfile
from socket import inet_aton


#: our ochopod logger
logger = logging.getLogger('kontrol')


class Actor(FSM):

    """
    Actor emitting a periodic HTTP POST request against the controlling party. This enables us
    to report relevant information about the pod. The pod UUID is derived from its IPv4 address
    shortened via base 62 encoding.
    """

    tag = 'keepalive'

    def __init__(self, cfg):
        super(Actor, self).__init__()

        self.cfg = cfg
        self.path = '%s actor' % self.tag
        self.uuid = '%s-%s' % (cfg['labels']['app'], self._shorten(struct.unpack("!I", inet_aton(cfg['ip']))[0]))
        logger.info('%s : now using UUID %s' % (self.path, self.uuid))

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
            'uuid': self.uuid,
            'ip': self.cfg['ip'],
            'role': self.cfg['labels']['role']
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
        # - default ping frequency is once every 5 seconds
        # - please note any failure to post will be handled with exponential backoff by
        #   the state-machine
        #
        # @todo use TLS
        #
        url = 'http://%s:8000/ping' % self.cfg['labels']['master']
        resp = requests.put(url, data=json.dumps(state), headers={'Content-Type':'application/json'}, timeout=1.0)
        resp.raise_for_status()
        logger.debug('%s : HTTP %d <- PUT /ping %s' % (self.path, resp.status_code, url))            
        return 'initial', data, 5.0

    def _shorten(self, n):
        out = ''
        alphabet = string.digits + string.lowercase + string.uppercase
        while n:
            out = alphabet[n % 62] + out
            n = int(n / 62)
        return out