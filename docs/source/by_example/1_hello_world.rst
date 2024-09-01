Hello, World
============

Basics of CLI apps and printing things to output.


Your first Yuio app
-------------------

Let's begin by setting up a very simple CLI app:

.. literalinclude:: code/1_1_first_yuio_app.py
   :language: python
   :linenos:


This is it! You now have a CLI app that greets you. Main function's parameters
become flags, and their type hints are used to parse arguments. Let's run it:

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 1_1_first_yuio_app.py --greeting 'my friend'"
   Enter
   Sleep 6s

That was simple. What else is there in our app?

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 1_1_first_yuio_app.py -h | less -R"
   Enter
   Sleep 6s

Well, that's a bunch of stuff you get out of the box! We will return to it later.


Printing something colorful
---------------------------

We want colors, so it's time to switch from bare :func:`print` to :mod:`yuio.io`:

.. literalinclude:: code/1_2_something_colorful.py
   :language: python
   :linenos:
   :lines: 1-6
   :emphasize-lines: 2,6

Tada, now our greeting is ✨colorful✨! Yuio parses markdown-style backticks
in messages, and colors them as code:

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 1_2_something_colorful.py"
   Enter
   Sleep 6s

If you want more control over formatting, though, you can use color tags:

.. literalinclude:: code/1_3_something_colorful.py
   :language: python
   :linenos:
   :lines: 4-6
   :emphasize-lines: 3

Now our message is bold, and green. By the way, Yuio has other color tags,
for example ``<c note>`` can be used for emphasis.


Flags and positional arguments
------------------------------

This is good, but we want a shorter flag for ``--greeting``. And we'd like to add
an option to output the greeting to a file.

Well, :func:`yuio.app.field` and :func:`yuio.app.positional` got you there:

.. literalinclude:: code/1_4_flags.py
   :language: python
   :linenos:
   :lines: 1-13
   :emphasize-lines: 1,7,8

We've added a short flag for ``--greeting`` using :func:`yuio.app.field`.
We've also added an optional positional argument for output file
using :func:`yuio.app.positional`.

Note that we use :class:`pathlib.Path` instead of :class:`str`.
This will tell Yuio that we're expecting a path, so the library
will handle it accordingly.


Adding help for CLI flags
-------------------------

Finally, let's add some help messages to document our CLI options:

.. literalinclude:: code/1_5_help.py
   :language: python
   :linenos:
   :lines: 5-16
   :emphasize-lines: 3,5,8

Yuio parses comments of your python files, so help messages can be just docstrings!

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 1_5_help.py -h | less -R"
   Enter
   Sleep 6s
