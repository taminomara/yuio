Advanced apps
=============

Exploring Yuio apps deeper.


Grouping flags
--------------

You can use :class:`yuio.config.Config` to group flags into groups.
We will discuss configs in the next chapter, meanwhile here's the example
of what you can do:

.. literalinclude:: code/3_1_config.py
   :language: python
   :linenos:
   :lines: 1-19
   :emphasize-lines: 6,15

Notice that we use :func:`yuio.app.inline` to inline flags from config
without prefixing them with ``--executor-config-...``.


Subcommands
-----------

We can easily build apps with multiple subcommands
by using :meth:`yuio.app.App.subcommand`:

.. literalinclude:: code/3_2_subcommands.py
   :language: python
   :linenos:
   :lines: 5-18
   :emphasize-lines: 5,10


App settings
------------

We can further customize our app and subcommands using the decorator's arguments
or directly setting app properties.

For example, let's add aliases for subcommands,
and also an epilog section to our app's help:

.. literalinclude:: code/3_3_settings.py
   :language: python
   :linenos:
   :lines: 5-35
   :emphasize-lines: 5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,27

This will result in the following help message:

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 3_3_settings.py -h | less -R"
   Enter
   Sleep 1s
   Down@250ms 4
   Sleep 1s
   Down@250ms 5
   Sleep 6s


Logging
-------

The app will automatically perform a basic logging configuration on startup.
The logging level will depend on how many ``-v`` flags are given,
from ``WARNING`` to ``DEBUG``:

.. literalinclude:: code/3_4_logging.py
   :language: python
   :linenos:

This is how verbose output will look like:

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 3_4_logging.py -vv"
   Enter
   Sleep 6s

If you want to configure logging yourself, set :attr:`yuio.app.App.setup_logging`
to :data:`False`, and use :class:`yuio.io.Handler` to send logs to :data:`~sys.stderr`:

.. literalinclude:: code/3_5_logging_manual.py
   :language: python
   :linenos:
   :emphasize-lines: 9,10,11,12,17


Customizing argument parsing
----------------------------

Yuio guesses how to parse input parameters by inspecting their type hints.
To override its default guess, you can supply a :class:`~yuio.parse.Parser`
to :func:`yuio.app.field`.

For example, let's make yuio parse an argument as JSON, then validate its internal
structure:

.. literalinclude:: code/3_6_parsers.py
   :language: python
   :linenos:
   :lines: 1-11
   :emphasize-lines: 2,8


Autocompletion
--------------

Yuio can generate autocompletion for Bash, Fish and Zsh. It installs completions
automatically, without any need to pipe shell scripts into specific files.
Just run your app with ``--completions`` flag:

.. code-block:: console

   $ ./app --completions

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config.tape"
   Hide
   Type "cd examples && mkdir -p ./.vhs_tmp && export XDG_DATA_HOME=./.vhs_tmp/.local/share/ XDG_CACHE_HOME=./.vhs_tmp/.cache/ XDG_CONFIG_HOME=./.vhs_tmp/.config/ ZDOTDIR=./.vhs_tmp/ && clear"
   Enter
   Show
   Type "./app --completions"
   Enter
   Sleep 4s
   Hide
   Type ". ./.vhs_tmp/.local/share/fish/vendor_completions.d/app.fish && clear"
   Enter
   Show
   Type "./app --"
   Sleep 250ms
   Tab
   Sleep 1s
   Type "v"
   Sleep 250ms
   Tab
   Sleep 500ms
   Type "r"
   Sleep 250ms
   Tab
   Sleep 500ms
   Type "a"
   Sleep 100ms
   Type " b"
   Enter
   Sleep 4s
   Hide
   Type "rm -rf ./.vhs_tmp"
   Enter
   Show
