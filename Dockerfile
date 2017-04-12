FROM alpine:3.5
RUN apk update && apk add --no-cache openssl curl jq g++ make python2 python2-dev ca-certificates py2-pip && \
    adduser -D kontrol && \
    mkdir kontrol && \
    chown kontrol /home/kontrol && \
    pip install --upgrade pip shell supervisor cython gevent gunicorn flask requests
WORKDIR /home/kontrol
COPY ./ ./
RUN cd python && /usr/bin/python setup.py install
EXPOSE 8000
CMD /usr/bin/supervisord -n -c boot.conf