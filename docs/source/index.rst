Yuio
====

This is a lightweight, no-dependency python module for building simple human-friendly CLIs
with python.

It is ideal for small things such as automation scripts, utilities for CI, or any other tools.
Without dependencies, it is easy to use it in places where you either don't or don't want to have
access to dependency management systems. Just copy-paste its source files into your project,
and be done with it.

.. _features:

Features
--------

- Colored output with inline tags built on top of the :mod:`logging` module::

    yuio.log.setup()
    yuio.log.info('<c:bold>Yuio</c>: a user-friendly io!')

- Status indication with progress bars::

    with yuio.log.Task('Loading sources') as task:
        for i, source in enumerate(sources):
            source.load()
            task.progress(float(i) / len(sources))

- User interactions and input parsing::

    answer = yuio.log.ask(
        'Do you want a choco bar?',
        parser=yuio.parse.Bool(),
        default=True,
    )

- More is coming!

Requirements
------------

The only requirement is ``python >= 3.8``.

Installation
------------

Install ``yuio`` with pip:

.. code-block:: sh

    pip3 install yuio

Contents
--------

.. toctree::
   :maxdepth: 2

   log
   parse
