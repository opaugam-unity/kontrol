import json
import logging
import os
import sys

from flask import Flask
from kontrol import fsm
from kontrol.keepalive import Actor as KeepAlive
from signal import signal, SIGINT, SIGQUIT, SIGTERM

#: our ochopod logger
logger = logging.getLogger('kontrol')

#: our flask endpoint (fronted by gunicorn)
http = Flask('kontrol')

#: simple trigger which will fail any request to GET /health
terminating = False

#:
actors = {}

@http.route('/', methods=['POST'])
def _post_in():

    #
    # - default GET / placeholder
    #
    logger.info('http in [post]')
    return '', 200

def up():

    global actors
    try:

        os.environ['LABELS'] = '{"supervised_by":"127.0.0.1"}'
        logger.info('starting!')
        #
        # -
        #
        js = json.loads(os.environ['LABELS'])
        if 'supervised_by' in js:
            actors['keepalive'] = KeepAlive.start('http://%s:8000/' % js['supervised_by'])

    except Exception as failure:

        #
        # - 
        #
        why = fsm.diagnostic(failure)
        logger.error('top level failure -> %s' % why)
        sys.exit(1)

def down():

    global actors, terminating
    if terminating:
        return

    #
    # -
    #        
    terminating = True
    logger.warning('termination trigger on')
    for key, actor in actors.items():
        logger.debug('terminating actor %s' % key)
        fsm.shutdown(actor)

    logger.info('going down')
