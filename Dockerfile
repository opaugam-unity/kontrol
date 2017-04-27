FROM alpine:3.5
WORKDIR /home/kontrol
RUN apk add --no-cache openssl curl jq g++ make python2 python2-dev ca-certificates py2-pip && \
    adduser -D kontrol && \
    chown kontrol /home/kontrol && \
    pip install --upgrade pip eventlet shell supervisor cython gunicorn flask requests

COPY ./ ./
RUN (cd code && /usr/bin/python setup.py install) && \
    rm -rf docs code README.md Dockerfile && \
    apk del g++ make
EXPOSE 8000
ENTRYPOINT ["/usr/bin/supervisord","-n","-c","supervisord.conf"]