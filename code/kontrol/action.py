import json
import logging

from collections import deque
from kontrol.fsm import Aborted, FSM
from subprocess import Popen, PIPE, STDOUT
from threading import Event, Thread

#: our ochopod logger
logger = logging.getLogger('kontrol')

class Actor(FSM):

    """
    Actor in charge of invoking an arbitrary command sent by the controller. The
    sub-process stdout is piped back into the HTTP response. The controller is
    free to include free-form json data in its request. This json will be passed
    down as the $INPUT environment variable.

    @todo add some authentication mechanism to make sure the request is not forged
    #todo anything to do to secure/sandbox/limit what the controller can request ?
    """

    tag = 'action'
    
    def __init__(self, cfg):
        super(Actor, self).__init__()

        self.cfg = cfg
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
        #
        what = self.fifo[0]
        data.latch = what.latch
        env = what.env
        data.pid = Popen(what.cmd.split(' '),
        close_fds=True,
        bufsize=0,
        env=env,
        stderr=PIPE,
        stdout=PIPE)

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
            # -
            #  
            data.latch.set(''.join([line.rstrip('\n') for line in iter(data.pid.stdout.readline, b'')]))
            Event()

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
        