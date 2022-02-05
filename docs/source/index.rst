Yuio
====

Yuio is a lightweight python library for building simple human-friendly CLIs.

Unlike bigger tools like `click`_ or `cleo`_, Yuio is small, simple, has no dependencies, and relies
on standard python libraries such as :mod:`logging` and :mod:`argparse`.

It is ideal for things like automation scripts, utilities for CI, or any other small tools.
Without dependencies, it is easy to use in places where you either don't or don't want to have
access to dependency management systems. Just copy-paste its source files into your project,
and be done with it.

Yuio is MyPy-friendly!

.. _click: https://click.palletsprojects.com/
.. _cleo: https://cleo.readthedocs.io/en/latest/

----

.. image:: _static/yuio_small.png

----

Features
--------

- Colored output with inline tags built on top of the :mod:`logging` module::

    yuio.io.setup()
    yuio.io.info('<c:bold>Yuio</c>: a user-friendly io library!')

- Status indication with progress bars::

    with yuio.io.Task('Loading sources') as task:
        for i, source in enumerate(sources):
            source.load()
            task.progress(float(i) / len(sources))

- User interactions and input parsing::

    answer = yuio.io.ask(
        'Do you want a choco bar?',
        parser=yuio.parse.Bool(),
        default=True,
    )

- Tools to edit things in an external editor::

    text = (
        '\n'
        '\n'
        '// Please enter the commit message for your changes.\n'
        '// Lines starting with "//" will be ignored,\n'
        '// and an empty message aborts the commit.\n'
    )
    text = yuio.edit.edit(text, comment_marker='//')

- Interactions with git::

   repo = yuio.git.Repo('.')
   status = repo.status()
   yuio.io.info(
       'At branch <c:code>%s</c>, commit <c:code>%s</c>',
       status.branch, status.commit
   )


Requirements
------------

The only requirement is ``python >= 3.8``.


Installation
------------

Install ``yuio`` with pip:

.. code-block:: sh

    pip3 install yuio

Or just copy-paste the ``yuio`` directory to somewhere in the ``PYTHONPATH`` of your project.


Use cases
---------

- `Example`_: a script that cuts Yuio's releases.

.. _Example: https://github.com/taminomara/yuio/blob/main/examples/release.py


Contents
--------

.. toctree::
   :maxdepth: 2

   io
   parse
   config
   git
