Configuration
=============


Environment variables
_____________________

Kontrol is configured via a few environments variables. Those are mostly defaulted based on what
the Kubernetes_ pod provides. A few can be specified in the manifest.

- **$KONTROL_HOST**: IPv4 address for the kube proxy (defaulted).
- **$KONTROL_IP**: IPv4 address for the pod (defaulted).
- **$KONTROL_ETCD**: IPv4 address for a Etcd_ proxy (defaulted).
- **$KONTROL_LABELS**: pod's label dictionary (defaulted).
- **$KONTROL_MODE**: pod operating mode, see below (defaulted).
- **$KONTROL_CALLBACK**: executable to run upon callback (optional).
- **$KONTROL_PAYLOAD**: local json file on disk to add to the keepalives (optional).

The labels are picked for you from the Kubernetes_ pod metadata. However you **must** at least
define the **app* and **role** labels as they are used by Kontrol.

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

Please note this assumes you have a local Etcd_ running on your local host and listening on all interfaces.


Etcd
____

The **$KONTROL_ETCD** variable is defaulted to the kube proxy IPv4. This assumes the Etcd_ proxy running in there
is listening on all interfaces. If you want to use a dedicated Etcd_ proxy you can override this variable.


Pod payload 
___________

Slaves have the ability to include arbirary json payload in their keepalives. Simply set the **$KONTROL_PAYLOAD**
variable to point to a file on disk containing valid serialized JSON. This content will be parsed and included
in the keepalive request.

If the variable is not set or if the file does not exist or contains invalid JSON this process will be skipped.


Callback
________

Kontrol will periodically run a user-defined callback whenever a change is detected. This callback is an
arbitrary command you can specify via the **$KONTROL_CALLBACK** variable. This subprocess is tracked and its
standard error and output piped back. It does not have to be a shell or Python_ script or anything
specific for that matter. The only requirement is to have it set to a valid command.

The callback sub-process will be passed 3 environment variables:

- **$HASH**: latest MD5 digest.
- **$PODS**: ordered list of pods as a JSON array.
- **$STATE**: optional user-data.

The **$PODS** variable contains a snapshot of the current pod ensemble. It is passed as a serialized JSON
array whose entries are consistently ordered. Anything written on the standard output is assumed to be
valid JSON syntax, will be persisted in Etcd_ and passed back upon the next invokation as the **$STATE**
variable.

Each entry in the **$POD** array is a small dict containing a few fields. For instance:

.. code-block:: json

    {
        "ip": 172.16.123.1
        "seq": 3
        "uuid": "redis-39mysN"
        "role": "redis"
        "payload": {"some": "stuff"}
    }

The UUID and sequence counter are guaranteed to be unique amongst all the monitored pods. The payload field is
optional and set if the slaves have **$KONTROL_PAYLOAD** set.

The following Python_ callback script will for instance display the UUID and IPv4 address assigned to each pod:

.. code-block:: python

    #!/usr/bin/python

    import os
    import sys
    import json

    if __name__ == '__main__':

        for pod in json.loads(os.environ['PODS']):
            print >> sys.stderr, ' - #%d (%s) -> %s' % (pod['seq'], pod['uuid'], pod['ip'])


.. include:: links.rst