Yuio
====

Yuio is everything you'll ever need to write a good CLI, deps-free.

Forget searching for *that one progressbar library*,
figuring out how to keep loading configs DRY,
or having headaches because autocompletion was just an afterthought.
Yuio got you.

.. vhs:: _tapes/demo.tape
   :alt: Demonstration of yuio capabilities.
   :scale: 50%


.. invisible-code-block: python

   import io
   import pathlib
   import sys
   import yuio.app
   import yuio.term

   yuio.io.setup(term=yuio.term.Term(io.StringIO()))


Features
--------

- Easy to setup CLI apps with autocompletion out of the box:

  .. code-block:: python

     @yuio.app.app
     def main(
         #: input files for the program.
         inputs: list[pathlib.Path] = yuio.app.positional(),
     ):
         ...

     if __name__ == "__main__":
         main.run()

- Colored output with inline tags and markdown:

  .. code-block:: python

     yuio.io.info('<c bold>Yuio</c>: a user-friendly io library!')

- Status indication with progress bars that don't break your console:

  .. invisible-code-block: python

     sources = []

  .. code-block:: python

     with yuio.io.Task('Loading sources') as task:
         for source in task.iter(sources):
             ...

- User interactions, input parsing and simple widgets:

  .. code-block:: python

     answer = yuio.io.ask("What's your favorite treat?", default="waffles")

- And many more!


Requirements
------------

The only requirement is ``python >= 3.8``.


Installation
------------

Install ``yuio`` with pip:

.. code-block:: console

   $ pip install yuio

Or just copy-paste the ``yuio`` directory to somewhere in the ``PYTHONPATH`` of your project.


Examples
--------

See examples at `taminomara/yuio`_.

.. _taminomara/yuio: https://github.com/taminomara/yuio/blob/main/examples/


Contents
--------

.. toctree::
   :maxdepth: 2

   by_example/index
   main_features/index
   internals/index
