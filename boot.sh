#!/bin/sh
BEARER_TOKEN_PATH=/var/run/secrets/kubernetes.io/serviceaccount/token
TOKEN="$(cat $BEARER_TOKEN_PATH)"
URL=https://$KUBERNETES_SERVICE_HOST/api/v1/namespaces/default/pods/$HOSTNAME
POD=$(curl $URL --insecure --header "Authorization: Bearer $TOKEN")
export IP=$(echo $POD  | jq -r '.status.podIP')
export LABELS=$(echo $POD | jq -r '.metadata.labels')
openssl req -newkey rsa:2048 -nodes -keyout domain.key -x509 -days 365 -out domain.crt -subj "/C=US/ST=New York/L=Brooklyn/O=Example Brooklyn Company/CN=examplebrooklyn.com"
cat << EOT >> cfg.py
loglevel = 'debug'
daemon = False
bind = '0.0.0.0:8000'
timeout = 5
graceful_timeout = 15
worker_class = 'gevent'
workers = 1
from kontrol.boot import up, down
def post_worker_init(worker):
    up()
def worker_int(worker):
    down()
EOT
gunicorn --capture-output --error-logfile - --access-logfile - -c cfg.py kontrol.boot:http