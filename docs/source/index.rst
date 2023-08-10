Yuio
====

Yuio is a lightweight python library for building simple human-friendly CLIs.

Unlike bigger tools like `click`_ or `cleo`_, Yuio is small, simple, has no dependencies, and relies
on standard python libraries such as :mod:`logging` and :mod:`argparse`.

.. _click: https://click.palletsprojects.com/
.. _cleo: https://cleo.readthedocs.io/en/latest/


.. vhs:: _tapes/widget_help.tape
   :alt: Demonstration of `InputWithCompletion` widget.
   :scale: 40%


Features
--------

- Easy to setup CLI apps::

    @yuio.app.app
    def main(inputs: list[pathlib.Path]):
        ...

    main.run()

- Colored output with inline tags built on top of the :mod:`logging` module::

    yuio.io.info('<c:bold>Yuio</c>: a user-friendly io library!')

- Status indication with progress bars::

    with yuio.io.Task('Loading sources') as task:
        for source in task.iter(sources):
            ...

- User interactions and input parsing::

    answer = yuio.io.ask('What\'s your favorite treat?', default='waffles')

- Tools to edit things in an external editor::

    text = '''

    // Please enter the commit message for your changes.
    // Lines starting with "//" will be ignored,
    // and an empty message aborts the commit.
    '''
    text = yuio.io.edit(text, comment_marker='//')

- Tools to run commands::

    yuio.exec.sh('ping 127.0.0.1 -c 5 1>&2')

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


Examples
--------

See examples at `taminomara/yuio`_.

.. _taminomara/yuio: https://github.com/taminomara/yuio/blob/main/examples/


Contents
--------

.. toctree::
   :maxdepth: 1

   io
   parse
   config
   app
   exec
   git
   complete
   term
   widget
