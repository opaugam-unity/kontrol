Configuration
=============

Setup
_____

Kontrol is run via its own Docker_ container. You can include it in your own pod manifests.

Environment variables
_____________________

Kontrol is configured via a few environments variables. Those are mostly defaulted based on what
the Kubernetes_ pod provides. A few can be specified in the manifest.

- **$KONTROL_HOST**: IPv4 address for the kube proxy (defaulted).
- **$KONTROL_IP**: IPv4 address for the pod (defaulted).
- **$KONTROL_ETCD**: IPv4 address for a Etcd_ proxy (defaulted).
- **$KONTROL_LABELS**: pod's label dictionary (defaulted).
- **$KONTROL_MODE**: pod operating mode, see below (defaulted).
- **$KONTROL_CALLBACK**: executable to run upon callback.
 

Operating mode
______________

Kontrol can run in different modes. The **$KONTROL_MODE** variable is a comma separated list of tokens
indicating what underlying actors to run. Valid token values include *slave*, *master*, *debug* and *verbose*.
The default value is set to *slave* meaning that Kontrol will just attempt to report keepalive messages.
Specifying *master* will enable receiving keepalives and tracking the MD5 digest. Please note you can
specify both *master* and *slave* at the same time.

The *verbose* token will turn debug logs on. Those are piped to the container standard output.

Adding *debug* will allow to run in local debugging mode. In that case *slave* and *master* will be added
as well and **$KONTROL_HOST** used for both the pod IPv4 and Etcd_. In other words you can run a self contained
master/slave instance of your Kontrol image by doing:

.. code-block:: shell

    $ sudo ifconfig lo0 alias 172.16.123.1
    $ docker run -e KONTROL_MODE=debug -e KONTROL_HOST=172.16.123.1 -p 8000:8000 <image>

Please note this assumes you have a local Etcd_ running on your local host.


Etcd
____

The **$KONTROL_ETCD** variable is defaulted to the kube proxy IPv4. This assumes the Etcd_ proxy running in there
is listening on all interfaces. If you want to use a dedicated Etcd_ proxy you can override this variable.


Callback
________

Kontrol will periodically run a user-defined callback whenever a change is detected. This callback is an
arbitrary command you can specify via the **$KONTROL_CALLBACK** variable. This subprocess is tracked and its
standard error and output piped back.

The callback sub-process will be passed 3 environment variables:

- **$HASH**: latest MD5 digest.
- **$PODS**: ordered list of pods as a JSON array.
- **$STATE**: optional user-data.

the **$PODS** variable contains a snapshot of the current pod ensemble. It is passed as a serialized JSON
array whose entries are consistently ordered.

For instance the following Python_ callback will display the IPv4 address assigned to each pod:

.. code-block:: python

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
        

.. include:: links.rst