#!/usr/bin/python

import os
import sys
import json

"""
Trivial callback example enumerating pods.
"""

if __name__ == '__main__':

    #
    # - fetch the current pod snapshot via $POD
    # - $POD is guaranteed to be always available
    #
    pods = json.loads(os.environ['PODS'])

    #
    # - display our pods on stderr
    # - $POD is guaranteed to contain consistenly ordered pod information
    #
    print >> sys.stderr, 'monitoring %s pods' % len(pods)
    for pod in pods:
        print >> sys.stderr, ' - #%d (%s) -> %s' % (pod['seq'], pod['uuid'], pod['ip'])
      