Introduction
============

Overview
________

Kontrol is a small Python_ package which implements a REST/HTTP endpoint plus a set of
Pykka_ state-machines. It can be used to report periodic keepalive messages and aggregate
them in Etcd_.

Kontrol operates in either slave, master or mixed mode. A **slave** will periodically emit a
keepalive payload to its **master** tier. This payload include information about the pod itself
plus some optional user-data. The masters will receive those keepalives and maintain a MD5 digest
reflecting the overall ensemble state. Any time this digest changes for whatever reason a
user defined callback is executed. The masters are HA and will fail-over in case of problem.
Any master can receive keepalives but only one at any given is in charge of tracking the digest
and executing the callback.

.. figure:: png/schematic.png
   :align: center
   :width: 90%

Please note you can run in both **master**/**slave** meaning the same pod deployment can run its
own monitoring logic.

.. include:: links.rst