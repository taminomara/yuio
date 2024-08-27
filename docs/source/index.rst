Yuio
====

Yuio is a lightweight python library for building simple human-friendly CLIs.

Unlike bigger tools like `click`_ or `cleo`_, Yuio is small, simple, has no dependencies, and relies
on standard python libraries such as :mod:`logging` and :mod:`argparse`.

.. _click: https://click.palletsprojects.com/
.. _cleo: https://cleo.readthedocs.io/en/latest/


.. vhs:: _tapes/demo.tape
   :alt: Demonstration of yuio capabilities.
   :scale: 50%


Features
--------

- Easy to setup CLI apps::

    @yuio.app.app
    def main(inputs: list[pathlib.Path]):
        ...

    if __name__ == "__main__":
        main.run()

- Colored output with inline tags::

    yuio.io.info('<c bold>Yuio</c>: a user-friendly io library!')

- Status indication with progress bars that don't break your console::

    with yuio.io.Task('Loading sources') as task:
        for source in task.iter(sources):
            ...

- User interactions, input parsing and simple widgets::

    answer = yuio.io.ask("What's your favorite treat?", default="waffles")
    want_now = yuio.io.ask[bool]("Do you want %s now?", answer)

- Tools to edit things in an external editor::

    text = '''

    // Please enter the commit message for your changes.
    // Lines starting with "//" will be ignored,
    // and an empty message aborts the commit.
    '''

    text = yuio.io.edit(text, comment_marker='//')

- Tools to run commands::

    yuio.exec.sh("ping 127.0.0.1 -c 5 1>&2")

- Interactions with git::

    repo = yuio.git.Repo(".")
    status = repo.status()
    yuio.io.info(
       'At branch `%s`, commit `%s`',
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

**Main functionality:**

.. toctree::
   :maxdepth: 2

   io
   parse
   config
   app
   exec
   git

**Lower-level details:**

.. toctree::
   :maxdepth: 2

   complete
   md
   term
   theme
   widget
