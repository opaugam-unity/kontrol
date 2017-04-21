import json
import logging
import kontrol
import os
import sys
import urllib3

from flask import Flask, request
from logging.config import fileConfig
from kontrol import fsm
from kontrol.action import Actor as Action
from kontrol.keepalive import Actor as KeepAlive
from kontrol.leader import Actor as Leader
from kontrol.state import Actor as State
from kontrol.update import Actor as Update
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
    # - post to the state actor
    #
    js = request.get_json(silent=True, force=True)
    logger.debug('PUT /ping <- keepalive from %s' % js['ip'] )
    kontrol.actors['state'].tell({'request': 'update', 'state': js})
    return '', 200

@http.route('/action/<key>', methods=['PUT'])
def _action(key):

    #
    # -
    #
    js = request.get_json(silent=True, force=True)
    logger.debug('PUT /action <- invoking "%s"' % key)

    import fsm
    script = fsm._Container()
    script.cmd = key
    script.env = {'INPUT': request.data}
    script.latch = ThreadingFuture()     
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

        #
        # - prepare a small bundle of information about this pod
        #
        debug = 1
        if debug:
            os.environ['KONTROL_ETCD']='127.0.0.1'
            os.environ['KONTROL_IP']='127.0.0.1'
            os.environ['KONTROL_LABELS']='{"app":"foo","controller":"127.0.0.1"}'
            os.environ['KONTROL_TAG']='foo'
            os.environ['KONTROL_SCRIPTS'] = '../scripts'
            os.environ['KONTROL_UPDATE']='monitor'
       
        #
        # -
        #
        def _try(key):
            value = os.environ[key]
            try:
                return json.loads(value)
            except ValueError:
                return value

        keys = [key for key in os.environ if key.startswith('KONTROL_')]            
        js = {key[8:].lower():_try(key) for key in keys}
        logger.debug('env vars available: %s' % ','.join(keys))
        
        #
        # - we rely on the <app> label to identify ourselves (the pod identifier, e.g <tag>
        #   is hard to use for instance when running in a deployment)
        #
        assert 'app' in js['labels'], 'kontrol requires the "app" label to be defined'
        
        #
        # -
        #
        if 'controller' in js['labels']:
           kontrol.actors['keepalive'] = KeepAlive.start(js)

        kontrol.actors['action'] = Action.start(js)   
        kontrol.actors['update'] = Update.start(js)
        kontrol.actors['leader'] = Leader.start(js)
        kontrol.actors['state'] = State.start(js)

    except Exception as failure:

        #
        # - bad, probably some missing env. variable
        # - abort the worker
        #
        why = fsm.diagnostic(failure)
        logger.error('top level failure -> %s' % why)
        sys.exit(1)

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

    