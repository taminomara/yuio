Command line interfaces
========================

    Exploring Yuio apps and CLI interfaces.


Creating and using apps
-----------------------

Yuio provides a decorator that turns functions into CLI applications:
:func:`yuio.app.app`. Function parameters become application's CLI arguments;
you can configure them the same way as you configure config fields:

.. code-block:: python

    import yuio.app

    @yuio.app.app
    def main(
        #: who are we greeting?
        greeting: str = yuio.app.field(
            default="world",
            flags=["-g", "--greeting"],
            metavar="<name>",
        )
    ):
        print(f"Hello, {greeting}!")

Decorated functions should only have named arguments; ``*args`` and ``**kwargs``
are not supported.

We can run the app with method :meth:`~yuio.app.App.run`:

.. code-block:: python

    if __name__ == "__main__":
        main.run()

:meth:`~yuio.app.App.run` sets up Yuio and logging, parses CLI arguments, and invokes
the main function.

We can invoke the original main function using :meth:`~yuio.app.App.wrapped`:

.. code-block:: python

    main.wrapped(greeting="sunshine")


Positional arguments
--------------------

By default, all CLI arguments become flags. You can turn them into positionals
by using :func:`yuio.app.positional`:

.. code-block:: python
    :emphasize-lines: 4

    @yuio.app.app
    def main(
        #: who are we greeting?
        greeting: str = yuio.app.positional(metavar="<name>")
    ):
        print(f"Hello, {greeting}!")


Mutually exclusive arguments
----------------------------

Sometimes you need to ensure that only one of several arguments can be passed.
For this, create a :class:`yuio.app.MutuallyExclusiveGroup` and pass it to
all such arguments:

.. code-block:: python
    :emphasize-lines: 1,6-8

    GROUP = yuio.app.MutuallyExclusiveGroup()

    @yuio.app.app
    def main(
        release: str,
        alpha: bool = yuio.app.field(default=False, group=GROUP),
        beta: bool = yuio.app.field(default=False, group=GROUP),
        rc: bool = yuio.app.field(default=False, group=GROUP),
    ):
        ...


Argument sections
-----------------

You can use :class:`yuio.config.Config` described in the previous chapter to group
CLI arguments into sections:

.. literalinclude:: cli_code/config.py
    :language: python
    :lines: 1-19
    :emphasize-lines: 6,15

Notice that we use :func:`yuio.app.inline` to inline config field names
without prefixing them with ``--executor-config-...``.

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m cli_code.config -h"
    Enter
    Sleep 6s


Subcommands
-----------

We can easily build apps with multiple subcommands
by using :meth:`yuio.app.App.subcommand`:

.. literalinclude:: cli_code/subcommands.py
    :language: python
    :lines: 5-18
    :emphasize-lines: 5,10


App settings
------------

We can further customize our app and subcommands using the decorator's arguments
or directly setting app properties.

For example, let's add aliases for subcommands,
and also an epilog section to our app's help:

.. literalinclude:: cli_code/settings.py
    :language: python
    :lines: 5-35
    :emphasize-lines: 5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,27

This will result in the following help message:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m cli_code.settings -h"
    Enter
    Sleep 6s


Autocompletion
--------------

Yuio can generate autocompletion for Bash, Fish, Zsh, and PowerShell.
It installs completions automatically, without any need to pipe shell scripts
into specific files. Just run your app with ``--completions`` flag:

.. code-block:: console

    $ ./app --completions

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config.tape"
    Hide
    Type "cd examples/apps && mkdir -p ./.vhs_tmp && export XDG_DATA_HOME=./.vhs_tmp/.local/share/ XDG_CACHE_HOME=./.vhs_tmp/.cache/ XDG_CONFIG_HOME=./.vhs_tmp/.config/ ZDOTDIR=./.vhs_tmp/ && touch ./.vhs_tmp/.zshrc && clear"
    Enter
    Show
    Type "./app --completions"
    Enter
    Wait
    Sleep 6s
    Hide
    Type "clear"
    Enter
    Type "zsh -li"
    Enter
    Type "clear"
    Enter
    Wait
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
    Sleep 6s
    Hide
    Type "rm -rf ./.vhs_tmp"
    Enter
