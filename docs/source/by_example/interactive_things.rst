Interacting with user
=====================

Everything about :mod:`yuio.io` and Yuio's interactive capabilities.


Printing messages
-----------------

Yuio offers a logging-like functions to print different sorts of messages:

.. literalinclude:: interactive_things_code/printing.py
    :language: python

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m interactive_things_code.printing"
    Enter
    Sleep 6s


Markdown and inline markup
--------------------------

If you need something even more complicated, you can use :func:`yuio.io.md` to print
formatted markdown:

.. literalinclude:: interactive_things_code/markdown.py
    :language: python
    :lines: 6-16
    :dedent:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m interactive_things_code.markdown"
    Enter
    Sleep 6s


Querying user input
-------------------

Last time we've built a simple CLI app that greets the user.
Now, let's make it interactive.

We'll start by querying the user's name, and if they want
a formal or an informal greeting:

.. literalinclude:: interactive_things_code/querying.py
    :language: python
    :lines: 1-16
    :emphasize-lines: 5,12,13

We've used :func:`yuio.io.ask` to get data from the user. It's like :func:`input`,
but automatically parses the user input, and can use different widgets based
on the expected value's type. That's why we've used :class:`~enum.Enum` instead
of a simple string:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m interactive_things_code.querying"
    Enter
    Sleep 1s
    Type "Indigo Montoya"
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

.. literalinclude:: interactive_things_code/task.py
    :language: python
    :emphasize-lines: 7

And if the job can report its progress, we can even show a progressbar:

.. literalinclude:: interactive_things_code/progress.py
    :language: python
    :emphasize-lines: 9,11,12

:class:`~yuio.io.Task` has lots of helper methods on it. For example, the above code
can be simplified using :meth:`yuio.io.Task.iter`: a function that automatically
updates progress as you iterate over a collection.

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m interactive_things_code.progress"
    Enter
    Sleep 12s


Opening an external editor
--------------------------

You know how when you run ``git commit``, it opens an editor and asks you to edit
a commit message? Yuio can do the same:

.. literalinclude:: interactive_things_code/edit.py
    :language: python
    :lines: 6-12
    :dedent:


Logging
-------

The app will automatically perform a basic logging configuration on startup.
The logging level will depend on how many ``-v`` flags are given,
from ``WARNING`` to ``DEBUG``:

.. literalinclude:: interactive_things_code/logging.py
    :language: python

This is how verbose output will look like:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m interactive_things_code.logging -vv"
    Enter
    Sleep 6s

If you want to configure logging yourself, set :attr:`yuio.app.App.setup_logging`
to :data:`False`, and use :class:`yuio.io.Handler` to send logs to :data:`~sys.stderr`:

.. literalinclude:: interactive_things_code/logging_manual.py
    :language: python
    :emphasize-lines: 9,10,11,12,17


Suspending output
-----------------

Sometimes you need to stop all output from your program. Most often this happens
when you want to hand IO control to a subprocess. :class:`yuio.io.SuspendOutput`
does just that:

.. literalinclude:: interactive_things_code/suspend.py
    :language: python
    :lines: 7-8
    :emphasize-lines: 2
    :dedent:

:class:`yuio.io.SuspendOutput` will disable all output, including prints
and writes to :data:`sys.stderr` and :data:`sys.stdout`. To bypass it,
use :func:`yuio.io.orig_stderr`, :func:`yuio.io.orig_stdout`, and methods
on the :class:`yuio.io.SuspendOutput` class.

Here's a more complicated example:

.. literalinclude:: interactive_things_code/suspend_complex.py
    :language: python
    :lines: 1-19
    :emphasize-lines: 13,15

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m interactive_things_code.suspend_complex"
    Enter
    Sleep 6s

.. note::

    :mod:`yuio.exec` provides a simple wrapper around :mod:`subprocess` that will
    log process' ``stderr``, and return process' ``stdout``.
