Installation
============

With Pip
--------

You can install Yuio from Pip as usual:

.. code-block:: console

    $ pip install yuio


Using Wheels
------------

Sometimes you need to run code in an environment that doesn't have pip. In this case,
you can use a wheel file:

1.  Download a ``.whl`` file from PyPi__.
2.  Add downloaded file to :data:`sys.path` and import Yuio as usual:

    .. code-block:: python

        import sys
        sys.path.insert(0, "yuio-2.0.0-py3-none-any.whl")

        import yuio

        ...

__ https://pypi.org/project/yuio/#files
