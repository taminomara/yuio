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
        #: Who are we greeting?
        greeting: str = yuio.app.field(
            default="world",
            flags=["-g", "--greeting"],
            metavar="<name>",
        )
    ):
        print(f"Hello, {greeting}!")

Decorated functions should only have named arguments; `*args` and `**kwargs`
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
        #: Who are we greeting?
        greeting: str = yuio.app.positional(metavar="<name>")
    ):
        print(f"Hello, {greeting}!")


Mutually exclusive arguments
----------------------------

Sometimes you need to ensure that only one of several arguments can be passed.
For this, create a :class:`~yuio.cli.MutuallyExclusiveGroup` and pass it to all
such arguments:

.. code-block:: python
    :emphasize-lines: 1,6-8

    GROUP = yuio.app.MutuallyExclusiveGroup()

    @yuio.app.app
    def main(
        release: str,
        alpha: bool = yuio.app.field(default=False, mutex_group=GROUP),
        beta: bool = yuio.app.field(default=False, mutex_group=GROUP),
        rc: bool = yuio.app.field(default=False, mutex_group=GROUP),
    ):
        ...


Argument groups
---------------

You can use :class:`~yuio.config.Config` to group CLI arguments. This can help with
encapsulation and reduce code duplication:

.. literalinclude:: cli_code/config.py
    :language: python
    :lines: 1-19
    :emphasize-lines: 6,15

By default, Yuio will prefix all flags in the nested config with flag of config's
field. That is, ``ExecutorConfig.threads`` will be loaded from
:flag:`--executor-config-threads`.

You can override this prefix by passing `flag` to :func:`yuio.app.field`,
or disable prefixing by using :func:`yuio.app.inline`:

.. literalinclude:: cli_code/config_inline.py
    :language: python
    :lines: 11-18
    :emphasize-lines: 4


Splitting help into sections
----------------------------

Yuio automatically separates CLI options into sections when you use nested
:class:`~yuio.config.Config`\ s; config's help message becomes group's title:

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m cli_code.config_inline -h"
    Enter
    Sleep 6s

You can disable this behavior by setting `help` to an empty string:

.. literalinclude:: cli_code/config_no_group.py
    :language: python
    :lines: 11-17
    :emphasize-lines: 3

You can also assign groups for individual fields by passing
:class:`~yuio.cli.HelpGroup` to :func:`yuio.app.field`:

.. literalinclude:: cli_code/config_explicit_group.py
    :language: python
    :emphasize-lines: 4,11,16


Subcommands
-----------

We can easily build apps with multiple subcommands
by using :meth:`App.subcommand <yuio.app.App.subcommand>`:

.. literalinclude:: cli_code/subcommands.py
    :language: python
    :lines: 5-18
    :emphasize-lines: 5,10

When you run ``app backup ...``, ``main()`` will be called first, then ``backup()``.
This lets you run code that's needed for all sub-commands, such as loading configs.
See details in :ref:`sub-commands-more`.


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
into specific files. Just run your app with :flag:`--completions` flag:

.. code-block:: console

    $ ./app --completions

.. vhs-inline:
    :scale: 40%

    Source "docs/source/_tapes/_config.tape"
    Hide
    Type "cd examples && mkdir -p ./.vhs_tmp && export XDG_DATA_HOME=./.vhs_tmp/.local/share/ XDG_CACHE_HOME=./.vhs_tmp/.cache/ XDG_CONFIG_HOME=./.vhs_tmp/.config/ ZDOTDIR=./.vhs_tmp/ && touch ./.vhs_tmp/.zshrc && clear"
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
    Type "rb"
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


CLI options with custom behavior
--------------------------------

If default behavior doesn't meet your needs, you can provide your own option
implementation by passing `option_ctor` to :func:`yuio.app.field`. This will let you
manually configure option's parsing and help formatting:

.. code-block:: python

    @yuio.app.app
    def main(
        quiet: int = yuio.app.field(
            default=0,
            flags=["-q", "--quiet"],
            option_ctor=yuio.app.count_option(),
        )
    ):
        ...

.. seealso::

    See :ref:`custom-cli-options`, :class:`yuio.app.OptionCtor`,
    and :mod:`yuio.cli` for API reference.
