Interacting with user
=====================

    Everything about :mod:`yuio.io` and Yuio's interactive capabilities.


Printing messages
-----------------

Yuio offers a :mod:`logging`-like functions to print messages:

.. literalinclude:: /../../examples/docs/io_printing.py
    :language: python

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_printing.py"
    Enter
    Sleep 6s


Pretty-printing Python objects
------------------------------

Yuio supports `rich repr protocol`__, which enables you to pretty-print
Python objects. Pretty-printing is controlled through format flags for ``%r``
and ``%s``:

__ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

- ``#`` enables colors in repr (i.e. ``%#r``);
- ``+`` splits repr into multiple lines (i.e. ``%+r``, ``%#+r``).

.. literalinclude:: /../../examples/docs/io_repr.py
    :language: python
    :emphasize-lines: 13

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_repr.py"
    Enter
    Sleep 6s


``", ".join(map(repr, values))``
--------------------------------

You often need to print lists joined by some separator. Yuio provides
:class:`~yuio.string.JoinStr`, :class:`~yuio.string.JoinRepr`,
:class:`~yuio.string.And`, and :class:`~yuio.string.Or` to help with this task:

.. literalinclude:: /../../examples/docs/io_join.py
    :language: python
    :lines: 6-11
    :dedent:

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_join.py"
    Enter
    Sleep 6s

:class:`~yuio.string.JoinStr` will call :class:`str() <str>`
(:class:`~yuio.string.JoinRepr` calls :func:`repr`)
on collection values, then join them with the given separator.
Not only that, it will also highlight joined values (but not separators!) using
the given color tag (``code`` by default).


Markdown and inline markup
--------------------------

If you need something even more complex, you can use :func:`yuio.io.md` to print
formatted markdown:

.. literalinclude:: /../../examples/docs/io_markdown.py
    :language: python
    :lines: 6-16
    :dedent:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_markdown.py"
    Enter
    Sleep 6s


Highlighting code
-----------------

Yuio supports simple :ref:`code highlighting <highlighting-code>`:

.. literalinclude:: /../../examples/docs/io_hl.py
    :language: python
    :lines: 6-12
    :dedent:

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_hl.py"
    Enter
    Sleep 6s


Querying user input
-------------------

You can use :func:`yuio.io.ask` to get data from the user. It's like :func:`input`,
but automatically parses the user input, and can use different widgets based
on the expected value's type:

.. literalinclude:: /../../examples/docs/io_querying.py
    :language: python
    :lines: 1-16
    :emphasize-lines: 5,11-15

.. note::

    :func:`yuio.io.ask` is designed to interact with users, not to read data. It uses
    ``/dev/tty`` on Unix, and console API on Windows, so it will read from
    an actual TTY even if ``stdin`` is redirected.

    When designing your program, make sure that users have alternative means
    to provide values: use configs or CLI arguments, allow passing passwords
    via environment variables, etc.

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_querying.py"
    Enter
    Sleep 1s
    Type "Miku"
    Sleep 500ms
    Enter
    Sleep 500ms
    Down
    Sleep 500ms
    Enter
    Sleep 6s


Indicating progress
-------------------

Suppose you have some long-running job, and you want to indicate that it is running.
:class:`yuio.io.Task` to the rescue:

.. literalinclude:: /../../examples/docs/io_task.py
    :language: python
    :lines: 7-8
    :dedent:
    :emphasize-lines: 1

And if the job can report its progress, we can even show a progressbar:

.. literalinclude:: /../../examples/docs/io_progress.py
    :language: python
    :lines: 9-14
    :dedent:
    :emphasize-lines: 1,3-4

:class:`~yuio.io.Task` has lots of helper methods on it. For example, the above code
can be simplified using :meth:`Task.iter() <yuio.io.Task.iter>`: a function that automatically
updates progress as you iterate over a collection.

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_progress.py"
    Enter
    Sleep 12s


Opening an external editor
--------------------------

You know how when you run :flag:`git commit`, it opens an editor and asks you to edit
a commit message? Yuio can do the same:

.. literalinclude:: /../../examples/docs/io_edit.py
    :language: python
    :lines: 6-12
    :dedent:
    :emphasize-lines: 1-5


Logging
-------

The app will automatically perform a basic logging configuration on startup.
The logging level will depend on how many :flag:`-v` flags are given,
from ``WARNING`` to ``DEBUG``:

.. literalinclude:: /../../examples/docs/io_logging.py
    :language: python
    :emphasize-lines: 4,8-9

This is how verbose output will look like:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_logging.py -vv"
    Enter
    Sleep 6s

If you want to configure logging yourself, set :attr:`yuio.app.App.setup_logging`
to :data:`False`, and use :class:`yuio.io.Handler` to send logs to :data:`~sys.stderr`:

.. literalinclude:: /../../examples/docs/io_logging_manual.py
    :language: python
    :emphasize-lines: 9,10,11,12,17


Suspending output
-----------------

Sometimes you need to stop all output from your program. Most often this happens
when you want to hand IO control to a subprocess. :class:`yuio.io.SuspendOutput`
does just that:

.. literalinclude:: /../../examples/docs/io_suspend.py
    :language: python
    :lines: 7-8
    :emphasize-lines: 2
    :dedent:


.. tip::

    :mod:`yuio.exec` provides a simple wrapper around :mod:`subprocess` that will
    log process' ``stderr``, and return process' ``stdout``.


:class:`yuio.io.SuspendOutput` will disable all output, including prints
and writes to :data:`sys.stderr` and :data:`sys.stdout`. To bypass it,
use :func:`yuio.io.orig_stderr`, :func:`yuio.io.orig_stdout`, and methods
on the :class:`yuio.io.SuspendOutput` class.

Here's a more comprehensive example:

.. literalinclude:: /../../examples/docs/io_suspend_complex.py
    :language: python
    :lines: 1-19
    :emphasize-lines: 13,15

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_suspend_complex.py"
    Enter
    Sleep 6s
