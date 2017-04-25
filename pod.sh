#!/bin/sh

#
# - attempt to retrieve the pod metadata via the service API
# - timeout at 5 seconds
#
BEARER_TOKEN_PATH=/var/run/secrets/kubernetes.io/serviceaccount/token
TOKEN="$(cat $BEARER_TOKEN_PATH)"
URL=https://$KUBERNETES_SERVICE_HOST/api/v1/namespaces/default/pods/$HOSTNAME
POD=$(curl -f -m 5 $URL --insecure --header "Authorization: Bearer $TOKEN")
if [ 0 -ne $? ]; then POD='{}'; fi;

#
# - set the required $KONTROL_* variables
# - default $KONTROL_MODE to slave
# - default $KONTROL_ETCD to the docker host (right now the assumption
#   is that each etcd2 proxy listens on 0.0.0.0 so that we can reach it
#   from within the pod)
#
# @todo how will we implement key isolation and/or authorization ?
#
export KONTROL_HOST=${KONTROL_HOST:=$(echo $POD | jq -r '.status.hostIP')}
export KONTROL_ETCD=${KONTROL_ETCD:=$KONTROL_HOST}
export KONTROL_MODE=${KONTROL_MODE:=slave}

#
# $KONTROL_IP and $KONTROL_LABELS are derived from the pod metadata
# and can't be overriden
#
export KONTROL_IP=$(echo $POD | jq -r '.status.podIP')
export KONTROL_LABELS=$(echo $POD | jq -r '.metadata.labels')

#
# - set the same graceful shutdown timeout as what supervisord uses
# #todo the worker_int() callback appears to be invoked twice (!?)
#
cat << EOT >> cfg.py
loglevel = 'error'
daemon = False
bind = '0.0.0.0:8000'
timeout = 15
graceful_timeout = 60
worker_class = 'sync'
workers = 1
from kontrol.endpoint import up, down
def post_worker_init(worker):
    up()
def worker_int(worker):
    down()
EOT
gunicorn --capture-output --error-logfile - -c cfg.py kontrol.endpoint:http