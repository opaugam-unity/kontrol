import etcd
import json
import logging

from collections import deque
from etcd import EtcdKeyNotFound
from kontrol.fsm import Aborted, FSM
from subprocess import Popen, PIPE, STDOUT
from threading import Thread


#: our ochopod logger
logger = logging.getLogger('kontrol')


class Actor(FSM):

    """
    State machine responsible for running the update callback (e.g whenever the observed
    MD5 digest changes). Please note this should only ever be scheduled on one single
    pod at any given time (e.g on the leading pod).
    """

    tag = 'callback'

    def __init__(self, cfg):
        super(Actor, self).__init__()

        self.cfg = cfg
        self.client = etcd.Client(host=cfg['etcd'], port=2379)
        self.fifo = deque()
        self.path = '%s actor' % self.tag

    def reset(self, data):

        if self.terminate:
            super(Actor, self).reset(data)

        return 'initial', data, 0.0

    def initial(self, data):
                
        if self.terminate and not self.fifo:
            raise Aborted('resetting')

        #
        # - just spin if there is nothing to invoke
        #
        if not self.fifo:
            return 'initial', data, 0.25

        #
        # - set the popen call to use piping if required
        # - spawn an ancillary thread to forward the lines to our logger
        # - this thread will go down automatically when the sub-process does
        # - set the $STATE env. variable which contains the persistent user-data
        #
        what = self.fifo[0]
        try:
            raw = self.client.read('/kontrol/%s/state' % self.cfg['labels']['app']).value
            if raw:
                what.env['STATE'] = raw
        except EtcdKeyNotFound:
            pass

        try:
            data.pid = Popen(what.cmd.split(' '),
            close_fds=True,
            bufsize=0,
            env=what.env,
            stderr=PIPE,
            stdout=PIPE)
       
        except OSError:
            logger.warning('%s : script "%s" could not be found (config bug ?)' % (self.path, what.cmd))   
            self.fifo.popleft()
            return 'initial', data, 0.0

        logger.debug('%s : invoking script "%s" (pid %s)' % (self.path, what.cmd, data.pid.pid))
        return 'wait_for_completion', data, 0.25

    def wait_for_completion(self, data):

        #
        # - stop spinning once the process has exited
        # - both stderr and stdout are piped
        #
        if data.pid.poll() is not None:
            code = data.pid.returncode
            err = [line.rstrip('\n') for line in iter(data.pid.stderr.readline, b'')]
            logger.info('%s : pid %s (exit %d) ->\n  . %s' % (self.path, data.pid.pid, code, '\n  . '.join(err)))
            
            #
            # - attempt to parse stdout into a json object
            #
            try:
                out = [line.rstrip('\n') for line in iter(data.pid.stdout.readline, b'')]
                self.client.write('/kontrol/%s/state' % self.cfg['labels']['app'], ''.join(out))
            except ValueError:
                logger.warning('%s : unable to parse stdout into json (script error ?)' % self.path)

            #
            # - dequeue the FIFO
            # - go back to the initial state
            #
            data.pid = None
            self.fifo.popleft()
            return 'initial', data, 0

        return 'wait_for_completion', data, 0.25
    

    def specialized(self, msg):
        assert 'request' in msg, 'bogus message received ?'
        req = msg['request']
        if req == 'invoke':

            #
            # - buffer the incoming script in our fifo
            # - we'll dequeue it upon the next spin
            #
            assert 'script' in msg, 'invalid message -> "%s" (bug ?)' % msg
            self.fifo.append(msg['script'])
        else:
            super(Actor, self).specialized(msg)
        