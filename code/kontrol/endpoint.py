import json
import logging
import kontrol
import os
import sys
import urllib3

from flask import Flask, request
from logging import DEBUG
from logging.config import fileConfig
from kontrol import bag, fsm
from kontrol.action import Actor as Action
from kontrol.callback import Actor as Callback
from kontrol.keepalive import Actor as KeepAlive
from kontrol.leader import Actor as Leader
from kontrol.sequence import Actor as Sequence
from os.path import dirname
from pykka import ThreadingFuture, Timeout
from signal import signal, SIGINT, SIGQUIT, SIGTERM


#: our ochopod logger
logger = logging.getLogger('kontrol')

#: our flask endpoint (fronted by gunicorn)
http = Flask('kontrol')

#: simple trigger which will fail any request to GET /health
terminating = False


@http.route('/ping', methods=['PUT'])
def _ping():

    #
    # - PUT /ping (e.g keepalive updates from supervised containers)
    # - post to the sequence actor
    #
    js = request.get_json(silent=True, force=True)
    logger.debug('PUT /ping <- keepalive from %s' % js['ip'] )
    kontrol.actors['sequence'].tell({'request': 'update', 'state': js})
    return '', 200


@http.route('/action/<key>', methods=['PUT'])
def _action(key):

    #
    # - PUT /action (e.g script evaluation request from the controller)
    # - post it to the action actor
    # - block on a latch and reply
    #
    script = bag()
    script.cmd = key
    script.env = {'INPUT': request.data}
    script.latch = ThreadingFuture()     
    logger.debug('PUT /action <- invoking "%s"' % key)
    kontrol.actors['action'].tell({'request': 'invoke', 'script': script})
    return script.latch.get(timeout=5), 200


def up():
    
    #
    # - disable the default 3 retries that urllib3 enforces
    # - that causes the etcd watch to potentially wait 3X
    #
    from urllib3.util import Retry
    urllib3.util.retry.Retry.DEFAULT = Retry(1)

    #
    # - load our logging configuration from the local log.cfg resource
    # - make sure to disable any existing logger otherwise urllib3 will flood us
    #
    fileConfig('%s/log.cfg' % dirname(__file__), disable_existing_loggers=True)
    try:

        def _try(key):
            value = os.environ[key]
            try:
                return json.loads(value)
            except ValueError:
                return value

        #
        # - grep the env. variables we need
        # - anything prefixed by KONTROL_ will be kept around
        # - $KONTROL_MODE is a comma separated list of tokens used to define
        #   the operation mode (e.g slave,debug)
        #
        stubs = []
        keys = [key for key in os.environ if key.startswith('KONTROL_')]            
        js = {key[8:].lower():_try(key) for key in keys}
        logger.info('$KONTROL_* defined: %s' % ','.join(keys))
        assert all(key in js for key in ['etcd', 'ip', 'labels', 'mode']), '1+ environment variables missing'
        tokens = set(js['mode'].split(','))
        assert all(key in ['slave', 'master', 'debug', 'verbose'] for key in tokens), 'invalid $KONTROL_MODE value'

        #
        # - if $KONTROL_MODE contains "debug" switch the debug/local mode on
        # - this will force etcd and the local http/rest endpoint to be either
        #   127.0.0.1 or whateer $KONTROL_HOST is set at
        # - if you want to test drive your container locally alias lo0 to some
        #   ip (e.g sudo ifconfig lo0 alias <ip>)
        # - then docker run as follow:
        #     docker run -e KONTROL_MODE=verbose,debug -e KONTROL_HOST=<ip> -p 8000:8000 <image>
        #
        if 'verbose' in tokens:
            logger.setLevel(DEBUG)

        if 'debug' in tokens:
            tokens |= set(['master', 'slave'])
            ip = js['host'] if 'host' in js else '127.0.0.1'
            logger.debug('switching debug mode on (host ip @ %s)' % ip)
            overrides = \
            {
                'etcd': ip,
                'ip': ip,
                'mode': 'mixed',
                'labels': {'app':'local', 'role': 'test', 'master': ip}
            }
            js.update(overrides)
        
        #
        # -
        #
        if 'slave' in tokens:
            stubs += [KeepAlive]
        
        #
        # -
        #
        if 'master' in tokens:
            stubs += [Action, Callback, Leader, Sequence]

        #
        # - start our various actors
        # - we rely on the "app" label to identify the pod
        # - the "role" label is also used when sending keepalive updates
        #
        assert all(key in js['labels'] for key in ['app', 'role']), '1+ labels missing'
        for stub in stubs:
            logger.debug('starting actor <%s>' % stub.tag)
            kontrol.actors[stub.tag] = stub.start(js)
    
    except Exception as failure:

        #
        # - bad, probably some missing environment variables
        # - abort the worker
        #
        why = fsm.diagnostic(failure)
        logger.error('top level failure -> %s' % why)

def down():

    global actors, terminating
    if terminating:
        for key, actor in kontrol.actors.items():
            logger.debug('terminating actor <%s>' % key)
            fsm.shutdown(actor)
    #
    # - gunicorn appears to trigger this callback twice
    # - use a flag and only react the 2nd time
    #
    # @todo fix that mess
    #        
    terminating = True

    