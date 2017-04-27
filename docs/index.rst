
Overview
========

Kontrol & Automaton
___________________

*Kontrol* is a distributed control loop managing Kubernetes_ pods. You can include its
Docker_ container in your pods to quickly implement monitoring, distributed configuration
and more.

It comes with *Automaton* which is a finite-state machine that runs shell scripts and which
can be transitioned by writing to a local unix socket. This is a convenient way to script
what the lifecycle of your software should be.

You can use both *Kontrol* and *Automaton* in tandem to implement strong distributed system
with consistent behavior.

Contents
________

.. toctree::
   :maxdepth: 3

   kontrol
   automaton

Indices and tables
__________________

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. include:: links.rst