Hello, World
============

    Basics of CLI apps and printing things to output.


Your first Yuio app
-------------------

Let's begin by setting up a very simple CLI app:

.. literalinclude:: /../../examples/docs/hw_first_yuio_app.py
    :language: python

.. code-annotations::

    1.  :func:`~yuio.app.app` accepts useful settings in its constructor.
    2.  Function arguments become CLI flags.
    3.  :meth:`~yuio.app.App.run` parses CLI arguments and invokes ``main``.


This is it! You now have a CLI app that greets you. Let's run it:

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/hw_first_yuio_app.py \"
    Enter
    Tab
    Type "--greeting 'my friend'"
    Enter
    Sleep 6s


Printing something colorful
---------------------------

We want colors, so it's time to switch from bare :func:`print` to :mod:`yuio.io`:

.. literalinclude:: /../../examples/docs/hw_something_colorful.py
    :language: python
    :lines: 1-7

.. code-annotations::

    1.  :mod:`yuio.io` has everything for interacting with users.
    2.  ``<c ...>`` is a color tag. Read about its syntax
        in :ref:`yuio.io <color-tags>`, see full list of tags in
        :ref:`yuio.theme <common-tags>`.
    3.  Backticks work like in Markdown.

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/hw_something_colorful.py"
    Enter
    Sleep 6s

Tada, now our greeting is ✨colorful✨!


Flags and positional arguments
------------------------------

Let's add a shorter flag for :flag:`--greeting`, and add an option to output
the greeting to a file:

.. literalinclude:: /../../examples/docs/hw_flags.py
    :language: python
    :lines: 1-13

.. code-annotations::

    1.  We use :class:`pathlib.Path` instead of :class:`str`. This tells Yuio
        that you expect a file path, which affects autocompletion.
    2.  :func:`yuio.app.field` allows customizing settings for app arguments
        and config fields.
    3.  :func:`yuio.app.positional` is a convenience shortcut
        for :func:`yuio.app.field`.


Adding help for CLI arguments
-----------------------------

Finally, let's add some help messages to document our CLI options:

.. literalinclude:: /../../examples/docs/hw_help.py
    :language: python
    :lines: 5-16

.. code-annotations::

    1.  Default format is RST, but you can use Markdown instead.
    2.  Help for individual parameters can be added with documentation comments.
    3.  Function's docstring becomes the main help message.

Yuio parses comments of your python files, so help messages
can be just RST or Markdown docstrings!

.. vhs-inline::
    :scale: 40%

    Set FontSize 20
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/hw_help.py --help 2>&1 | less -R"
    Enter
    Sleep 1s
    Down@1s 6
    Sleep 4s
