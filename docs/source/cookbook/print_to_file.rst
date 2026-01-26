.. _cookbook-print-to-file:

Print formatted text to file
============================

    Printing formatted text to file or terminal while respecting terminal width
    or other settings.

While working with CLIs, it is important to separate user-facing messages from
program's output.

For most use cases, this is easy: user-facing messages go to :mod:`yuio.io`, which
sends them to ``stderr``, while program output goes to :func:`print`
or :data:`sys.stdout`.

This way, users can redirect ``stdout`` to a file while still seeing ``stderr``
in their terminal.

Complications arise when we want to print formatted content as program's output:
we have to face several scenarios:

1.  User wants to see program's output in the terminal:

    .. code-block:: console

        $ app

    In this case, we want to format it according to the terminal's capabilities.

2.  User piped program's output to a pager:

    .. code-block:: console

        $ app | less -R

    In this case, we'd also like to format it according to the terminal's capabilities.
    However, we can't know output's destination: will it end up in a terminal,
    some text processing utility, or a file?

3.  User redirected output to a file:

    .. code-block:: console

        $ app > output.txt

    From our app's perspective, this case looks exactly like case #2: all we know is
    that output is redirected, but we don't know where it goes.

4.  Our program has a distinct option for specifying output:

    .. code-block:: console

        $ app -o output.txt

    In this case, we need to format output for a file, choosing reasonable text width
    and other settings.

Here's how Yuio handles these scenarios, and how we can control its default behavior.

.. invisible-code-block: python

    import yuio.io


Case 1: output goes to a terminal
---------------------------------

In this case, we can use :mod:`yuio.io` to send output to ``stdout``:

.. code-block:: python

    result = ...
    yuio.io.info(result, to_stdout=True)

Here, ``result`` will be automatically formatted according
to terminal's capabilities.


Cases 2 and 3: output is redirected
-----------------------------------

When user redirects program's output, Yuio assumes that it goes to a file. Colors are
disabled, and formatting width is set to
:attr:`Theme.fallback_width <yuio.theme.Theme.fallback_width>`.

If user wants to treat output as a terminal, they can enable colors by setting
environment variable ``FORCE_COLOR`` or giving flag :flag:`--color`:

.. code-block:: console

    $ app --color | less -R


Case 4: dedicated option for output file
----------------------------------------

If our program has a distinct option for specifying output, we need to set up
:class:`~yuio.io.MessageChannel` in order to format output.

Here's how we can do this:

.. literalinclude:: /../../examples/cookbook/print_to_file.py
    :language: python
