Interacting with user
=====================

    Everything about :mod:`yuio.io` and Yuio's interactive capabilities.


Printing messages
-----------------

Yuio offers a :mod:`logging`-like functions to print messages:

.. tab-set::
    :sync-group: formatting-method

    .. tab-item:: Printf-style formatting
        :sync: printf

        .. literalinclude:: /../../examples/docs/io_printing.py
            :language: python

    .. tab-item:: Template strings
        :sync: template

        .. literalinclude:: /../../examples/docs/io_printing_t.py
            :language: python

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_printing.py"
    Enter
    Sleep 6s

These functions accept format strings that can have :ref:`color tags <color-tags>`
and backticks:

.. tab-set::
    :sync-group: formatting-method

    .. tab-item:: Printf-style formatting
        :sync: printf

        .. literalinclude:: /../../examples/docs/io_colors.py
            :language: python
            :lines: 4-
            :dedent:

        .. code-annotations::

            1.  See full list of tags in :ref:`yuio.theme <common-tags>`.

    .. tab-item:: Template strings
        :sync: template

        .. literalinclude:: /../../examples/docs/io_colors_t.py
            :language: python
            :lines: 4-
            :dedent:

        .. code-annotations::

            1.  See full list of tags in :ref:`yuio.theme <common-tags>`.


Pretty-printing Python objects
------------------------------

Yuio supports `rich repr protocol`__, which enables you to pretty-print
Python objects. Pretty-printing is controlled through format flags for ``%r``
and ``%s``, as well as through formatting flags for template strings:

__ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

.. tab-set::
    :sync-group: formatting-method

    .. tab-item:: Printf-style formatting
        :sync: printf

        -   ``#`` enables colors in repr (i.e. ``%#r``);
        -   ``+`` splits repr into multiple lines (i.e. ``%+r``, ``%#+r``).

        .. literalinclude:: /../../examples/docs/io_repr.py
            :language: python
            :emphasize-lines: 13

    .. tab-item:: Template strings
        :sync: template

        -   ``#`` enables colors in repr (i.e. ``{var:#}``);
        -   ``+`` splits repr into multiple lines (i.e. ``{var:+}``, ``{var:#+}``);
        -   these flags work when you format strings or :ref:`colorable objects <pretty-protocol>`:
            you'll have to explicitly convert objects of other types to strings
            by specifying conversion operator, i.e. ``{var!r:#}``.

        .. literalinclude:: /../../examples/docs/io_repr_t.py
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

.. tab-set::
    :sync-group: formatting-method

    .. tab-item:: Printf-style formatting
        :sync: printf

        .. literalinclude:: /../../examples/docs/io_join.py
            :language: python
            :lines: 6-11
            :dedent:

        .. code-annotations::

            1.  You can pass multiple color tags in the same string, just separate
                them with spaces.

    .. tab-item:: Template strings
        :sync: template

        .. literalinclude:: /../../examples/docs/io_join_t.py
            :language: python
            :lines: 6-10
            :dedent:

        .. code-annotations::

            1.  You can pass multiple color tags in the same string, just separate
                them with spaces.

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/io_join.py"
    Enter
    Sleep 6s


RST and Markdown
----------------

Yuio also supports basic RST and Markdown formatting. It's mostly used for generating
CLI help, but you can print messages with it as well:

.. tab-set::
    :sync-group: docs-lang

    .. tab-item:: RST
        :sync: rst

        .. literalinclude:: /../../examples/docs/io_rst.py
            :language: python
            :lines: 6-26
            :dedent:

        .. vhs-inline::
            :scale: 40%

            Source "docs/source/_tapes/_config.tape"
            Type "python examples/docs/io_rst.py 2>&1 | less -R"
            Enter
            Sleep 1s
            Down@1s 6
            Sleep 4s

    .. tab-item:: Markdown
        :sync: markdown

        .. literalinclude:: /../../examples/docs/io_markdown.py
            :language: python
            :lines: 6-24
            :dedent:

        .. vhs-inline::
            :scale: 40%

            Source "docs/source/_tapes/_config.tape"
            Type "python examples/docs/io_markdown.py 2>&1 | less -R"
            Enter
            Sleep 1s
            Down@1s 6
            Sleep 4s


Highlighting code
-----------------

Yuio supports simple :doc:`code highlighting <../../internals/hl>`:

.. literalinclude:: /../../examples/docs/io_hl.py
    :language: python
    :lines: 6-15
    :dedent:

.. code-annotations::

    1.  See full list of supported languages in :mod:`yuio.hl`.

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

.. code-annotations::

    1.  We use :class:`~enum.Enum` so that Yuio knows which values to expect.
        It will change input widget accordingly.
    2.  :func:`~yuio.io.ask` accepts type parameter which determines its result.
        Default is :class:`str`.

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

And if the job can report its progress, we can even show a progressbar:

.. literalinclude:: /../../examples/docs/io_progress.py
    :language: python
    :lines: 9-14
    :dedent:

.. code-annotations::

    1.  :class:`~yuio.io.Task` has lots of helper methods on it.

        For example, this code can be simplified using
        :meth:`Task.iter() <yuio.io.Task.iter>` instead of :func:`enumerate`.

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

.. code-annotations::

    1.  All lines that start with this marker will be removed after editing.


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
