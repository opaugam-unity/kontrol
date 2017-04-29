FROM alpine:3.5
WORKDIR /home/kontrol
RUN apk add --no-cache openssl socat curl jq g++ make python2 python2-dev ca-certificates py2-pip && \
    adduser -D kontrol && \
    chown kontrol /home/kontrol && \
    pip install --upgrade pip pyyaml jsonschema eventlet shell supervisor cython gunicorn flask requests

COPY ./ ./
RUN (cd code && /usr/bin/python setup.py install) && \
    rm -rf docs code README.md Dockerfile && \
    mkdir -p /etc/supervisor/conf.d && \
    mv *.conf /etc/supervisor && \
    apk del g++ make && \
    chmod +x *.sh

#
# - our entry point is to simply spawn supervisord
# - use the default configuration under /etc/supervisor
# - derived images are expected to add their jobs under /etc/supervisor/conf.d
#
ENTRYPOINT ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]