FROM alpine:3.5
RUN apk add --no-cache openssl curl jq g++ make python2 python2-dev ca-certificates py2-pip && \
    adduser -D kontrol && \
    mkdir kontrol && \
    chown kontrol /home/kontrol && \
    pip install --upgrade pip shell supervisor cython gunicorn flask requests && \
    apk del g++ make
WORKDIR /home/kontrol
COPY ./ ./
RUN cd python && /usr/bin/python setup.py install
EXPOSE 8000
ENV KONTROL_UPDATE "/usr/bin/python /home/kontrol/scripts/update.py"
ENTRYPOINT ["/usr/bin/supervisord","-n","-c","supervisord.conf"]