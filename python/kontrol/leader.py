import etcd
import hashlib
import json
import kontrol
import logging
import os
import requests
import time

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
        self.path = 'leader actor'
        self.snapshot = {}
        self.stamp = None

    def reset(self, data):

        if hasattr(data, 'lock'):
            try:

                #
                # -
                #
                self.client.delete(data.lock.key)
            except Exception:
                pass

        if self.terminate:
            super(Actor, self).reset(data)

        return 'initial', data, 0.0

    def initial(self, data):

        #
        # - setup our lock key which has a unique sequential id
        # - this key will live with a TTL of 10 seconds under locks/ and be prefixed by "leader-"
        #
        data.trigger = 0
        data.dirty = False
        data.lock = self.client.write('/kontrol/%s/locks/leader' % self.cfg['labels']['app'], '', append=True, ttl=10).key
        logger.debug('%s : created lock key #%d' % (self.path, int(data.lock[data.lock.rfind('/')+1:])))
        return 'acquire', data, 0.0

    def acquire(self, data):
        
        if self.terminate:
            raise Aborted('resetting')

        #
        # -
        #
        if not self.client.refresh(data.lock, ttl=10):
            raise Aborted('lost key %s (excessive lag ?)' % data.lock.key)

        #
        # - query the lock directory
        # - sort the keys and compare against ours
        # - if we're first we own the lock
        #
        logger.debug('%s : attempting to grab lock' % self.path)
        items = [item for item in self.client.read('/kontrol/%s/locks' % self.cfg['labels']['app'], recursive=True).leaves] 
        ordered = sorted(item.key for item in items)        
        if data.lock == ordered[0]:
            logger.info('%s : now acting as leader' % self.path)
            return 'watch', data, 0.0

        return 'acquire', data, 5.0

    def watch(self, data):

        if self.terminate:
            raise Aborted('resetting')
        
        #
        # -
        #
        if not self.client.refresh(data.lock, ttl=10):
            raise Aborted('lost key %s (excessive lag ?)' % data.lock.key)

        #
        # - grab the latest snapshot of our reporting pods
        # - compute the MD5 digest for the corresponding json payload
        # - compare against our last hash
        #
        # @todo can we possibly use a watch and/or track indices?
        #
        pods = self.client.read('/kontrol/%s/pods' % self.cfg['labels']['app'], recursive=True)
        self.snapshot = {item.key:json.loads(item.value) for item in pods.leaves if item.value}
        hashed = hashlib.md5()
        hashed.update(json.dumps(sorted(self.snapshot.items())))
        stamp = ':'.join(c.encode('hex') for c in hashed.digest())

        #
        # - 
        #
        now = time.time()
        if stamp != self.stamp:
            data.dirty = True
            self.stamp = stamp
            data.trigger = now + 0.0
            logger.debug('%s : change detected, script invokation in 10 s' % self.path)

        if data.dirty and now > data.trigger:
                        
            #
            # -
            #
            data.dirty = False
            logger.info('%s : change detected (%d pods), MD5 -> ...%s' % (self.path, len(self.snapshot), stamp[-12:]))
            self.client.write('/kontrol/%s/stamp' % self.cfg['labels']['app'], stamp)
 
            #
            # -
            #
            if 'update' in self.cfg:
                import fsm
                script = fsm._Container()
                script.cmd = self.cfg['update']
                #
                # @todo check the script is really there
                #
                script.env = {'HASH': stamp, 'PODS': json.dumps(self.snapshot.values())}     
                kontrol.actors['update'].tell({'request': 'invoke', 'script': script})
               
        return 'watch', data, 1.0

