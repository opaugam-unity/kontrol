## Kontrol

### Overview

This project is a small [**Python**](https://www.python.org/) endpoint you can include to
any [**Kubernetes**](https://github.com/GoogleCloudPlatform/kubernetes) pod. It relies on
[**etcd**](https://github.com/coreos/etcd) for synchronization, leader election and
persistence. You can either decide to leverage the interal cluster used by
Kubernetes or run your own.

### What does it do ?

Kontrol implements a simple distributed control loop allowing you to react to any change
within your pod ensemble and trigger your own callback logic. Changes include for instance
scaling events, unexpected pod or node failures or updates to what each pod reports.

### Documentation

The [**Sphinx**](http://sphinx-doc.org/) materials can be found under docs/. Just go in there
and build for your favorite target, for instance:

```
$ cd docs
$ make html
```

The docs will be written to _docs/_build/html_. This is all Sphinx based and you have many
options and knobs to tweak should you want to customize the output.

### Support

Contact olivierp@unity3d.com for more information about this project.