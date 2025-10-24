Hello, World
============

Basics of CLI apps and printing things to output.


Your first Yuio app
-------------------

Let's begin by setting up a very simple CLI app:

.. literalinclude:: hello_world_code/first_yuio_app.py
    :language: python


This is it! You now have a CLI app that greets you. Main function's parameters
become CLI arguments, and their type hints are used to parse arguments. Let's run it:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m hello_world_code.first_yuio_app --greeting 'my friend'"
    Enter
    Sleep 6s


Printing something colorful
---------------------------

We want colors, so it's time to switch from bare :func:`print` to :mod:`yuio.io`:

.. literalinclude:: hello_world_code/something_colorful.py
    :language: python
    :lines: 1-7
    :emphasize-lines: 2,6,7

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m hello_world_code.something_colorful"
    Enter
    Sleep 6s

Tada, now our greeting is ✨colorful✨! Yuio parses :ref:`color tags <color-tags>`
and backticks in messages. Here's the list of color tags available from the box:

-  ``code``, ``note``, ``path``: highlights,
-  ``bold``, ``b``, ``dim``, ``d``: font style,
-  ``normal``, ``black``, ``red``, ``green``, ``yellow``, ``blue``,
   ``magenta``, ``cyan``, ``white``: colors.

You can add more with :doc:`themes </internals/theme>`.


Flags and positional arguments
------------------------------

This is good, but we want a shorter flag for ``--greeting``. And we'd like to add
an option to output the greeting to a file.

Well, :func:`yuio.app.field` and :func:`yuio.app.positional` got you there:

.. literalinclude:: hello_world_code/flags.py
    :language: python
    :lines: 1-13
    :emphasize-lines: 1,7,8

We've added a short flag for ``--greeting`` using :func:`yuio.app.field`.
We've also added an optional positional argument for output file
using :func:`yuio.app.positional`.

Note that we use :class:`pathlib.Path` instead of :class:`str`.
This will tell Yuio that we're expecting a path, so the library
will handle it accordingly.


Adding help for CLI arguments
-----------------------------

Finally, let's add some help messages to document our CLI options:

.. literalinclude:: hello_world_code/help.py
    :language: python
    :lines: 5-13
    :emphasize-lines: 3,5,8

Yuio parses comments of your python files, so help messages
can be just markdown docstrings!

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m hello_world_code.help -h | less -R"
    Enter
    Sleep 6s

You can read about which markdown features Yuio supports
in the documentation for :mod:`yuio.md`.
