# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides base functionality to build CLI interfaces.

Creating and running an app
---------------------------

Yuio's CLI applications have functional interface. Decorate main function
with the :func:`app` decorator, and use :meth:`App.run` method to start it:

.. code-block:: python

    # Let's define an app with one flag and one positional argument.
    @app
    def main(
        #: help message for `arg`
        arg: str = positional(),
        #: help message for `--flag`
        flag: int = 0
    ):
        \"""this command does a thing\"""
        yuio.io.info("flag=%r, arg=%r", flag, arg)

    if __name__ == "__main__":
        # We can now use `main.run` to parse arguments and invoke `main`.
        # Notice that `run` does not return anything. Instead, it terminates
        # python process with an appropriate exit code.
        main.run("--flag 10 foobar!".split())

Function's arguments will become program's flags and positionals, and function's
docstring will become app's :attr:`~App.description`.

Help messages for the flags are parsed from line comments
right above the field definition (comments must start with ``#:``).
They are all formatted using Markdown or RST depending on :attr:`App.doc_format`.

Parsers for CLI argument values are derived from type hints.
Use the `parser` parameter of the :func:`field` function to override them.

Arguments with bool parsers and parsers that support
:meth:`parsing collections <yuio.parse.Parser.supports_parse_many>`
are handled to provide better CLI experience:

.. invisible-code-block: python

    import pathlib

.. code-block:: python

    @app
    def main(
        # Will create flags `--verbose` and `--no-verbose`.
        # Since default is `False`, `--no-verbose` will be hidden from help
        # to reduce clutter.
        verbose: bool = False,
        # Will create a flag with `nargs=*`: `--inputs path1 path2 ...`
        inputs: list[pathlib.Path] = [],
    ): ...

.. autofunction:: app

.. autoclass:: App

    .. automethod:: run

    .. method:: wrapped(...)

        The original callable what was wrapped by :func:`app`.


Configuring CLI arguments
-------------------------

Names and types of arguments are determined by names and types of the app function's
arguments. You can use the :func:`field` function to override them:

.. autofunction:: field

.. autofunction:: inline

.. autofunction:: positional


Using configs in CLI
--------------------

You can use :class:`~yuio.config.Config` as a type of an app function's parameter.
This will make all of config fields into flags as well. By default, Yuio will use
parameter name as a prefix for all fields in the config; you can override it
with :func:`field` or :func:`inline`:

.. code-block:: python

    class KillCmdConfig(yuio.config.Config):
        signal: int
        pid: int = field(flags=["-p", "--pid"])


    @app
    def main(
        kill_cmd: KillCmdConfig,  # [1]_
        kill_cmd_2: KillCmdConfig = field(flags="--kill"),  # [2]_
        kill_cmd_3: KillCmdConfig = field(flags=""),  # [3]_
    ): ...

.. code-annotations::

    1.  ``kill_cmd.signal`` will be loaded from :flag:`--kill-cmd-signal`.
    2.  ``copy_cmd_2.signal`` will be loaded from :flag:`--kill-signal`.
    3.  ``kill_cmd_3.signal`` will be loaded from :flag:`--signal`.

.. note::

    Positional arguments are not allowed in configs,
    only in apps.


App settings
------------

You can override default usage and help messages as well as control some of the app's
help formatting using its arguments:

.. class:: App
    :noindex:

    .. autoattribute:: prog

    .. autoattribute:: usage

    .. autoattribute:: description

    .. autoattribute:: help

    .. autoattribute:: epilog

    .. autoattribute:: allow_abbrev

    .. autoattribute:: subcommand_required

    .. autoattribute:: setup_logging

    .. autoattribute:: theme

    .. autoattribute:: version

    .. autoattribute:: bug_report

    .. autoattribute:: is_dev_mode

    .. autoattribute:: doc_format


Creating sub-commands
---------------------

You can create multiple sub-commands for the main function
using the :meth:`App.subcommand` method:

.. code-block:: python

    @app
    def main(): ...


    @main.subcommand
    def do_stuff(): ...

There is no limit to how deep you can nest subcommands, but for usability reasons
we suggest not exceeding level of sub-sub-commands (:flag:`git stash push`, anyone?)

When user invokes a subcommand, the ``main()`` function is called first,
then subcommand. In the above example, invoking our app with subcommand ``push``
will cause ``main()`` to be called first, then ``push()``.

This behavior is useful when you have some global configuration flags
attached to the ``main()`` command. See the `example app`_ for details.

.. _example app: https://github.com/taminomara/yuio/blob/main/examples/app

.. class:: App
    :noindex:

    .. automethod:: subcommand


.. _sub-commands-more:

Controlling how sub-commands are invoked
----------------------------------------

By default, if a command has sub-commands, the user is required to provide
a sub-command. This behavior can be disabled by setting :attr:`App.subcommand_required`
to :data:`False`.

When this happens, we need to understand whether a subcommand was invoked or not.
To determine this, you can accept a special parameter called `_command_info`
of type :class:`CommandInfo`. It will contain info about the current function,
including its name and subcommand:

.. code-block:: python

    @app
    def main(_command_info: CommandInfo):
        if _command_info.subcommand is not None:
            # A subcommand was invoked.
            ...

You can call the subcommand on your own by using ``_command_info.subcommand``
as a callable:

.. code-block:: python

    @app
    def main(_command_info: CommandInfo):
        if _command_info.subcommand is not None and ...:
            _command_info.subcommand()  # manually invoking a subcommand

If you wish to disable calling the subcommand, you can return :data:`False`
from the main function:

.. code-block:: python

    @app
    def main(_command_info: CommandInfo):
        ...
        # Subcommand will not be invoked.
        return False

.. autoclass:: CommandInfo
   :members:


.. _flags-with-multiple-values:

Handling options with multiple values
-------------------------------------

When you create an option with a container type, Yuio enables passing its values
by specifying multiple arguments. For example:

.. code-block:: python

    @yuio.app.app
    def main(list: list[int]):
        print(list)

Here, you can pass values to :flag:`--list` as separate arguments:

.. code-block:: console

    $ app --list 1 2 3
    [1, 2, 3]

If you specify value for :flag:`--list` inline, it will be handled as
a delimiter-separated list:

.. code-block:: console

    $ app --list='1 2 3'
    [1, 2, 3]

This allows resolving ambiguities between flags and positional arguments:

.. code-block:: console

    $ app --list='1 2 3' subcommand

Technically, :flag:`--list 1 2 3` causes Yuio to invoke
``list_parser.parse_many(["1", "2", "3"])``, while :flag:`--list='1 2 3'` causes Yuio
to invoke ``list_parser.parse("1 2 3")``.


.. _flags-with-optional-values:

Handling flags with optional values
-----------------------------------

When designing a CLI, one important question is how to handle flags with optional
values, if at all. There are several things to consider:

1.  Does a flag have clear and predictable behavior when its value is not specified?

    For boolean flags the default behavior is obvious: :flag:`--use-gpu` will enable
    GPU, i.e. it is equivalent to :flag:`--use-gpu=true`.

    For flags that accept non-boolean values, though, things get messier. What will
    a flag like :flag:`--n-threads` do? Will it calculate number of threads based on
    available CPU cores? Will it use some default value?

    In these cases, it is usually better to require a sentinel value:
    :flag:`--n-threads=auto`.

2.  Where should flag's value go, it it's provided?

    We can only allow passing value inline, i.e. :flag:`--use-gpu=true`. Or we can
    greedily take the following argument as flag's value, i.e. :flag:`--use-gpu true`.

    The later approach has a significant downside: we don't know
    whether the next argument was intended for the flag or for a free-standing option.

    For example:

    .. code-block:: console

        $ my-renderer --color true  # is `true` meant for `--color`,
        $                           # or is it a subcommand for `my-renderer`?

Here's how Yuio handles this dilemma:

1.  High level API does not allow creating flags with optional values.

    To create one, you have to make a custom implementation of :class:`yuio.cli.Option`
    and set its :attr:`~yuio.cli.Option.allow_no_args` to :data:`True`. This will
    correspond to the greedy approach.

    .. note::

        Positionals with defaults are treated as optional because they don't
        create ambiguities.

2.  Boolean flags allow specifying value inline, but not as a separate argument.

3.  Yuio does not allow passing inline values to short boolean flags
    without adding an equals sign. For example, :flag:`-ftrue` will not work,
    while :flag:`-f=true` will.

    This is done to enable grouping short flags: :flag:`ls -laH` should be parsed
    as :flag:`ls -l -a -H`, not as :flag:`ls -l=aH`.

4.  On lower levels of API, Yuio allows precise control over this behavior
    by setting :attr:`Option.nargs <yuio.cli.Option.nargs>`,
    :attr:`Option.allow_no_args <yuio.cli.Option.allow_no_args>`,
    :attr:`Option.allow_inline_arg <yuio.cli.Option.allow_inline_arg>`,
    and :attr:`Option.allow_implicit_inline_arg <yuio.cli.Option.allow_implicit_inline_arg>`.


.. _custom-cli-options:

Creating custom CLI options
---------------------------

You can override default behavior and presentation of a CLI option by passing
custom `option_ctor` to :func:`field`. Furthermore, you can create your own
implementation of :class:`yuio.cli.Option` to further fine-tune how an option
is parsed, presented in CLI help, etc.

.. autofunction:: bool_option

.. autofunction:: parse_one_option

.. autofunction:: parse_many_option

.. autofunction:: store_const_option

.. autofunction:: count_option

.. autofunction:: store_true_option

.. autofunction:: store_false_option

.. type:: OptionCtor
    :canonical: typing.Callable[[OptionSettings], yuio.cli.Option[T]]

    CLI option constructor. Takes a single positional argument
    of type :class:`OptionSettings`, and returns an instance
    of :class:`yuio.cli.Option`.

.. autoclass:: OptionSettings
    :members:


Re-imports
----------

.. type:: HelpGroup
    :no-index:

    Alias of :obj:`yuio.cli.HelpGroup`.

.. type:: MutuallyExclusiveGroup
    :no-index:

    Alias of :obj:`yuio.cli.MutuallyExclusiveGroup`.

.. data:: MISC_GROUP
    :no-index:

    Alias of :obj:`yuio.cli.MISC_GROUP`.

.. data:: OPTS_GROUP
    :no-index:

    Alias of :obj:`yuio.cli.OPTS_GROUP`.

.. data:: SUBCOMMANDS_GROUP
    :no-index:

    Alias of :obj:`yuio.cli.SUBCOMMANDS_GROUP`.

"""

from __future__ import annotations

import dataclasses
import functools
import inspect
import json
import logging
import pathlib
import sys
import types
from dataclasses import dataclass

import yuio
import yuio.cli
import yuio.complete
import yuio.config
import yuio.dbg
import yuio.doc
import yuio.io
import yuio.parse
import yuio.string
import yuio.term
import yuio.theme
import yuio.util
from yuio.cli import (
    MISC_GROUP,
    OPTS_GROUP,
    SUBCOMMANDS_GROUP,
    HelpGroup,
    MutuallyExclusiveGroup,
)
from yuio.config import (
    OptionCtor,
    OptionSettings,
    bool_option,
    collect_option,
    count_option,
    field,
    inline,
    parse_many_option,
    parse_one_option,
    positional,
    store_const_option,
    store_false_option,
    store_true_option,
)
from yuio.util import find_docs as _find_docs
from yuio.util import to_dash_case as _to_dash_case

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "MISC_GROUP",
    "OPTS_GROUP",
    "SUBCOMMANDS_GROUP",
    "App",
    "AppError",
    "CommandInfo",
    "HelpGroup",
    "MutuallyExclusiveGroup",
    "OptionCtor",
    "OptionSettings",
    "app",
    "bool_option",
    "collect_option",
    "count_option",
    "field",
    "inline",
    "parse_many_option",
    "parse_one_option",
    "positional",
    "store_const_option",
    "store_false_option",
    "store_true_option",
]

C = _t.TypeVar("C", bound=_t.Callable[..., None | bool])
C2 = _t.TypeVar("C2", bound=_t.Callable[..., None | bool])


class AppError(yuio.PrettyException, Exception):
    """
    An error that you can throw from an app to finish its execution without printing
    a traceback.

    """


@_t.overload
def app(
    *,
    prog: str | None = None,
    usage: str | None = None,
    description: str | None = None,
    epilog: str | None = None,
    version: str | None = None,
    bug_report: yuio.dbg.ReportSettings | bool = False,
    is_dev_mode: bool | None = None,
    doc_format: _t.Literal["md", "rst"] | yuio.doc.DocParser | None = None,
) -> _t.Callable[[C], App[C]]: ...
@_t.overload
def app(
    command: C,
    /,
    *,
    prog: str | None = None,
    usage: str | None = None,
    description: str | None = None,
    epilog: str | None = None,
    version: str | None = None,
    bug_report: yuio.dbg.ReportSettings | bool = False,
    is_dev_mode: bool | None = None,
    doc_format: _t.Literal["md", "rst"] | yuio.doc.DocParser | None = None,
) -> App[C]: ...
def app(
    command: _t.Callable[..., None | bool] | None = None,
    /,
    *,
    prog: str | None = None,
    usage: str | None = None,
    description: str | None = None,
    epilog: str | None = None,
    allow_abbrev: bool = False,
    subcommand_required: bool = True,
    setup_logging: bool = True,
    theme: (
        yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
    ) = None,
    version: str | None = None,
    bug_report: yuio.dbg.ReportSettings | bool = False,
    is_dev_mode: bool | None = None,
    doc_format: _t.Literal["md", "rst"] | yuio.doc.DocParser | None = None,
) -> _t.Any:
    """
    Create an application.

    This is a decorator that's supposed to be used on the main method
    of the application. This decorator returns an :class:`App` object.

    :param command:
        the main function of the application.
    :param prog:
        overrides program's name, see :attr:`App.prog`.
    :param usage:
        overrides program's usage description, see :attr:`App.usage`.
    :param description:
        overrides program's description, see :attr:`App.description`.
    :param epilog:
        overrides program's epilog, see :attr:`App.epilog`.
    :param allow_abbrev:
        whether to allow abbreviating unambiguous flags, see :attr:`App.allow_abbrev`.
    :param subcommand_required:
        whether this app requires a subcommand,
        see :attr:`App.subcommand_required`.
    :param setup_logging:
        whether to perform basic logging setup on startup,
        see :attr:`App.setup_logging`.
    :param theme:
        overrides theme that will be used when setting up :mod:`yuio.io`,
        see :attr:`App.theme`.
    :param version:
        program's version, will be displayed using the :flag:`--version` flag.
    :param bug_report:
        settings for automated bug report generation. If present,
        adds the :flag:`--bug-report` flag.
    :param is_dev_mode:
        enables additional logging, see :attr:`App.is_dev_mode`.
    :param doc_format:
        overrides program's documentation format, see :attr:`App.doc_format`.
    :returns:
        an :class:`App` object that wraps the original function.

    """

    def registrar(command: C, /) -> App[C]:
        return App(
            command,
            prog=prog,
            usage=usage,
            description=description,
            epilog=epilog,
            allow_abbrev=allow_abbrev,
            subcommand_required=subcommand_required,
            setup_logging=setup_logging,
            theme=theme,
            version=version,
            bug_report=bug_report,
            is_dev_mode=is_dev_mode,
            doc_format=doc_format,
        )

    if command is None:
        return registrar
    else:
        return registrar(command)


@_t.final
@dataclass(frozen=True, eq=False, match_args=False, slots=True)
class CommandInfo:
    """
    Data about the invoked command.

    """

    name: str
    """
    Name of the current command.

    If it was invoked by alias,
    this will contains the primary command name.

    For the main function, the name will be set to ``"__main__"``.

    """

    # Internal, do not use.
    _config: _t.Any = dataclasses.field(repr=False)
    _executed: bool = dataclasses.field(default=False, repr=False)
    _subcommand: CommandInfo | None | yuio.Missing = dataclasses.field(
        default=yuio.MISSING, repr=False
    )

    @property
    def subcommand(self) -> CommandInfo | None:
        """
        Subcommand of this command, if one was given.

        """

        if self._subcommand is yuio.MISSING:
            if self._config._subcommand is None:
                subcommand = None
            else:
                subcommand = CommandInfo(
                    self._config._subcommand, self._config._subcommand_ns.config
                )
            object.__setattr__(self, "_subcommand", subcommand)
        return self._subcommand  # pyright: ignore[reportReturnType]

    def __call__(self) -> _t.Literal[False]:
        """
        Execute this command.

        """

        if self._executed:
            return False
        object.__setattr__(self, "_executed", True)

        should_invoke_subcommand = self._config._run(self)
        if should_invoke_subcommand is None:
            should_invoke_subcommand = True

        if should_invoke_subcommand and self.subcommand is not None:
            self.subcommand()

        return False


class App(_t.Generic[C]):
    """
    A class that encapsulates app settings and logic for running it.

    It is better to create instances of this class using the :func:`app` decorator,
    as it provides means to decorate the main function and specify all of the app's
    parameters.

    """

    def __init__(
        self,
        command: C,
        /,
        *,
        prog: str | None = None,
        usage: str | None = None,
        help: str | yuio.Disabled | None = None,
        description: str | None = None,
        epilog: str | None = None,
        allow_abbrev: bool = False,
        subcommand_required: bool = True,
        setup_logging: bool = True,
        theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = None,
        version: str | None = None,
        bug_report: yuio.dbg.ReportSettings | bool = False,
        is_dev_mode: bool | None = None,
        doc_format: _t.Literal["md", "rst"] | yuio.doc.DocParser | None = None,
    ):
        self.prog: str | None = prog
        """
        Program or subcommand's primary name.

        For main app, this controls its display name and generation of shell completion
        scripts.

        For subcommands, this is always equal to subcommand's main name.

        By default, inferred from :data:`sys.argv` and subcommand name.

        """

        self.usage: str | None = usage
        """
        Program or subcommand synapsis.

        This string will be processed using the to ``bash`` syntax,
        and then it will be ``%``-formatted with a single keyword argument ``prog``.
        If command supports multiple signatures, each of them should be listed
        on a separate string. For example::

            @app
            def main(): ...

            main.usage = \"""
            %(prog)s [-q] [-f] [-m] [<branch>]
            %(prog)s [-q] [-f] [-m] --detach [<branch>]
            %(prog)s [-q] [-f] [-m] [--detach] <commit>
            ...
            \"""

        By default, usage is generated from CLI flags.

        """

        if description is None and command.__doc__:
            description = yuio.util.dedent(command.__doc__).removesuffix("\n")
        if description is None:
            description = ""

        self.description: str = description
        """
        Text that is shown before CLI flags help, usually contains
        short description of the program or subcommand.

        The text should be formatted using Markdown or RST,
        depending on :attr:`~App.doc_format`. For example:

        .. code-block:: python

           @yuio.app.app(doc_format="md")
           def main(): ...

           main.description = \"""
           This command does a thing.

           # Different ways to do a thing

           This command can apply multiple algorithms to achieve
           a necessary state in which a thing can be done. This includes:

           - randomly turning the screen on and off;

           - banging a head on a table;

           - fiddling with your PCs power cord.

           By default, the best algorithm is determined automatically.
           However, you can hint a preferred algorithm via the `--hint-algo` flag.

           \"""

        By default, inferred from command's docstring.

        """

        if help is None and description:
            help = description
            if (index := help.find("\n\n")) != -1:
                help = help[:index]
        elif help is None:
            help = ""

        self.help: str | yuio.Disabled = help
        """
        Short help message that is shown when listing subcommands.

        By default, uses first paragraph of description.

        """

        self.epilog: str | None = epilog
        """
        Text that is shown after the main portion of the help message.

        The text should be formatted using Markdown or RST,
        depending on :attr:`~App.doc_format`.

        """

        self.allow_abbrev: bool = allow_abbrev
        """
        Allow abbreviating CLI flags if that doesn't create ambiguity.

        Disabled by default.

        """

        self.subcommand_required: bool = subcommand_required
        """
        Require the user to provide a subcommand for this command.

        If this command doesn't have any subcommands, this option is ignored.

        Enabled by default.

        """

        self.setup_logging: bool = setup_logging
        """
        If :data:`True`, the app will call :func:`logging.basicConfig` during
        its initialization. Disable this if you want to customize
        logging initialization.

        Disabling this option also removes the :flag:`--verbose` flag form the CLI.

        """

        self.theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = theme
        """
        A custom theme that will be passed to :func:`yuio.io.setup`
        on application startup.

        """

        self.version: str | None = version
        """
        If not :data:`None`, add :flag:`--version` flag to the CLI.

        """

        self.bug_report: yuio.dbg.ReportSettings | bool = bug_report
        """
        If not :data:`False`, add :flag:`--bug-report` flag to the CLI.

        This flag automatically collects data about environment and prints it
        in a format suitable for adding to a bug report.

        """

        self.is_dev_mode: bool | None = is_dev_mode
        """
        If :data:`True`, this will enable :func:`logging.captureWarnings`
        and configure internal Yuio logging to show warnings.

        By default, dev mode is detected by checking if :attr:`~App.version`
        contains substring ``"dev"``.

        .. note::

            You can always enable full debug logging by setting environment
            variable ``YUIO_DEBUG``.

            If enabled, full log will be saved to ``YUIO_DEBUG_FILE``.

        """

        self.doc_format: _t.Literal["md", "rst"] | yuio.doc.DocParser = (
            doc_format or "rst"
        )
        """
        Format or parser that will be used to interpret documentation.

        """

        self._ordered_subcommands: list[App[_t.Any]] = []
        self._subcommands: dict[str, App[_t.Any]] = {}
        self._parent: App[_t.Any] | None = None
        self._aliases: list[str] | None = None

        if callable(command):
            self._config_type = _command_from_callable(command)
        else:
            raise TypeError(f"expected a function, got {command}")

        functools.update_wrapper(
            self,  # type: ignore
            command,
            assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            updated=(),
        )

        self._command = command

        @functools.wraps(command)
        def wrapped_command(*args, **kwargs):
            if args:
                names = self._config_type.__annotations__
                if len(args) > len(names):
                    s = "" if len(names) == 1 else "s"
                    raise TypeError(
                        f"expected at most {len(names)} positional argument{s}, got {len(args)}"
                    )
                for arg, name in zip(args, names):
                    if name in kwargs:
                        raise TypeError(f"argument {name} was given twice")
                    kwargs[name] = arg
            return CommandInfo("__raw__", self._config_type(**kwargs), False)()

        self.wrapped: C = wrapped_command  # type: ignore
        """
        The original callable what was wrapped by :func:`app`.

        """

    @_t.overload
    def subcommand(
        self,
        /,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        usage: str | None = None,
        help: str | yuio.Disabled | None = None,
        description: str | None = None,
        epilog: str | None = None,
    ) -> _t.Callable[[C2], App[C2]]: ...

    @_t.overload
    def subcommand(
        self,
        cb: C2,
        /,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        usage: str | None = None,
        help: str | yuio.Disabled | None = None,
        description: str | None = None,
        epilog: str | None = None,
    ) -> App[C2]: ...

    def subcommand(
        self,
        cb: _t.Callable[..., None | bool] | None = None,
        /,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        usage: str | None = None,
        help: str | yuio.Disabled | None = None,
        description: str | None = None,
        epilog: str | None = None,
        subcommand_required: bool = True,
    ) -> _t.Any:
        """
        Register a subcommand for the given app.

        This method can be used as a decorator, similar to the :func:`app` function.

        :param name:
            allows overriding subcommand's name.
        :param aliases:
            allows adding alias names for subcommand.
        :param usage:
            overrides subcommand's usage description, see :attr:`App.usage`.
        :param help:
            overrides subcommand's short help, see :attr:`App.help`.
            pass :data:`~yuio.DISABLED` to hide this subcommand in CLI help message.
        :param description:
            overrides subcommand's description, see :attr:`App.description`.
        :param epilog:
            overrides subcommand's epilog, see :attr:`App.epilog`.
        :param subcommand_required:
            whether this subcommand requires another subcommand,
            see :attr:`App.subcommand_required`.
        :returns:
            a new :class:`App` object for a subcommand.

        """

        def registrar(cb: C2, /) -> App[C2]:
            main_name = name or _to_dash_case(cb.__name__)
            app = App(
                cb,
                prog=main_name,
                usage=usage,
                help=help,
                description=description,
                epilog=epilog,
                subcommand_required=subcommand_required,
            )
            app._parent = self
            app._aliases = aliases

            self._ordered_subcommands.append(app)
            self._subcommands[main_name] = app
            if aliases:
                self._subcommands.update({alias: app for alias in aliases})

            return app

        if cb is None:
            return registrar
        else:
            return registrar(cb)

    def run(self, args: list[str] | None = None) -> _t.NoReturn:
        """
        Parse arguments, set up :mod:`yuio.io` and :mod:`logging`,
        and run the application.

        :param args:
            command line arguments. If none are given,
            use arguments from :data:`sys.argv`.
        :returns:
            this method does not return, it exits the program instead.

        """

        if args is None:
            args = sys.argv[1:]

        if "--yuio-custom-completer--" in args:
            index = args.index("--yuio-custom-completer--")
            _run_custom_completer(
                self._make_cli_command(root=True), args[index + 1], args[index + 2]
            )
            sys.exit(0)

        if "--yuio-bug-report--" in args:
            from yuio.dbg import print_report

            print_report(settings=self.bug_report, app=self)
            sys.exit(0)

        yuio.io.setup(theme=self.theme, wrap_stdio=True)

        try:
            if self.is_dev_mode is None:
                self.is_dev_mode = (
                    self.version is not None and "dev" in self.version.casefold()
                )
            if self.is_dev_mode:
                yuio.enable_internal_logging(add_handler=True)

            help_parser = self._make_help_parser()

            cli_command = self._make_cli_command(root=True)
            namespace = yuio.cli.CliParser(
                cli_command, help_parser=help_parser, allow_abbrev=self.allow_abbrev
            ).parse(args)

            if self.setup_logging:
                logging_level = {
                    0: logging.WARNING,
                    1: logging.INFO,
                    2: logging.DEBUG,
                }.get(namespace["_verbose"], logging.DEBUG)
                logging.basicConfig(handlers=[yuio.io.Handler()], level=logging_level)

            command = CommandInfo("__main__", _config=namespace.config)
            command()
            sys.exit(0)
        except yuio.cli.ArgumentError as e:
            yuio.io.raw(e, add_newline=True)
            sys.exit(1)
        except (AppError, yuio.cli.ArgumentError, yuio.parse.ParsingError) as e:
            yuio.io.failure(e)
            sys.exit(1)
        except KeyboardInterrupt:
            yuio.io.failure("Received Keyboard Interrupt, stopping now")
            sys.exit(130)
        except Exception as e:
            yuio.io.failure_with_tb("Error: %s", e)
            sys.exit(3)
        finally:
            yuio.io.restore_streams()

    def _make_help_parser(self):
        if self.doc_format == "md":
            from yuio.md import MdParser

            return MdParser()
        elif self.doc_format == "rst":
            from yuio.rst import RstParser

            return RstParser()
        else:
            return self.doc_format

    def _make_cli_command(self, root: bool = False):
        options = self._config_type._build_options()

        if root:
            options.append(yuio.cli.HelpOption())
            if self.version:
                options.append(yuio.cli.VersionOption(version=self.version))
            if self.setup_logging:
                options.append(
                    yuio.cli.CountOption(
                        flags=["-v", "--verbose"],
                        usage=yuio.COLLAPSE,
                        help="Increase output verbosity.",
                        help_group=yuio.cli.MISC_GROUP,
                        show_if_inherited=False,
                        dest="_verbose",
                    )
                )
            if self.bug_report:
                options.append(yuio.cli.BugReportOption(app=self))
            options.append(yuio.cli.CompletionOption())
            options.append(_ColorOption())

        subcommands = {}
        subcommand_for_app = {}
        for name, sub_app in self._subcommands.items():
            if sub_app not in subcommand_for_app:
                subcommand_for_app[sub_app] = sub_app._make_cli_command()
            subcommands[name] = subcommand_for_app[sub_app]

        return yuio.cli.Command(
            name=self.prog or pathlib.Path(sys.argv[0]).stem,
            desc=self.description or "",
            help=self.help,
            epilog=self.epilog or "",
            usage=yuio.util.dedent(self.usage or ""),
            options=options,
            subcommands=subcommands,
            subcommand_required=self.subcommand_required,
            ns_ctor=lambda: yuio.cli.ConfigNamespace(self._config_type()),
            dest="_subcommand",
            ns_dest="_subcommand_ns",
        )


def _command_from_callable(
    cb: _t.Callable[..., None | bool],
) -> type[yuio.config.Config]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    accepts_command_info = False

    try:
        docs = _find_docs(cb)
    except Exception:
        yuio._logger.warning(
            "unable to get documentation for %s.%s",
            cb.__module__,
            cb.__qualname__,
        )
        docs = {}

    for name, param in sig.parameters.items():
        if param.kind not in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            raise TypeError("positional-only and variadic arguments are not supported")

        if name.startswith("_"):
            if name == "_command_info":
                accepts_command_info = True
                continue
            else:
                raise TypeError(f"unknown special param {name}")

        if param.default is not param.empty:
            field = param.default
        else:
            field = yuio.MISSING
        if not isinstance(field, yuio.config._FieldSettings):
            field = _t.cast(
                yuio.config._FieldSettings, yuio.config.field(default=field)
            )

        if param.annotation is param.empty:
            raise TypeError(f"param {name} requires type annotation")

        dct[name] = field
        annotations[name] = param.annotation

    dct["_run"] = _command_from_callable_run_impl(
        cb, list(annotations.keys()), accepts_command_info
    )
    dct["_color"] = None
    dct["_verbose"] = 0
    dct["_subcommand"] = None
    dct["_subcommand_ns"] = None
    dct["__annotations__"] = annotations
    dct["__module__"] = getattr(cb, "__module__", None)
    dct["__doc__"] = getattr(cb, "__doc__", None)
    dct["__yuio_pre_parsed_docs__"] = docs

    return types.new_class(
        cb.__name__,
        (yuio.config.Config,),
        {"_allow_positionals": True},
        exec_body=lambda ns: ns.update(dct),
    )


def _command_from_callable_run_impl(
    cb: _t.Callable[..., None | bool], params: list[str], accepts_command_info
):
    def run(self, command_info):
        kw = {name: getattr(self, name) for name in params}
        if accepts_command_info:
            kw["_command_info"] = command_info
        return cb(**kw)

    return run


def _run_custom_completer(command: yuio.cli.Command[_t.Any], raw_data: str, word: str):
    data = json.loads(raw_data)
    path: str = data["path"]
    flags: set[str] = set(data["flags"])
    index: int = data["index"]

    root = command
    for name in path.split("/"):
        if not name:
            continue
        if name not in command.subcommands:
            return
        root = command.subcommands[name]

    positional_index = 0
    for option in root.options:
        option_flags = option.flags
        if option_flags is yuio.POSITIONAL:
            option_flags = [str(positional_index)]
            positional_index += 1
        if flags.intersection(option_flags):
            completer, is_many = option.get_completer()
            break
    else:
        completer, is_many = None, False

    if completer:
        yuio.complete._run_completer_at_index(completer, is_many, index, word)


@dataclass(eq=False, kw_only=True)
class _ColorOption(yuio.cli.Option[_t.Never]):
    # `yuio.term` will scan `sys.argv` on its own, this option just checks format
    # and adds help entry.

    _ALLOWED_VALUES = (
        "y",
        "yes",
        "true",
        "1",
        "n",
        "no",
        "false",
        "0",
        "ansi",
        "ansi-256",
        "ansi-true",
    )

    _PUBLIC_VALUES = (
        ("true", "3-bit colors or higher"),
        ("false", "disable colors"),
        ("ansi", "force 3-bit colors"),
        ("ansi-256", "force 8-bit colors"),
        ("ansi-true", "force 24-bit colors"),
    )

    def __init__(self):
        super().__init__(
            flags=["--color", "--no-color"],
            allow_inline_arg=True,
            allow_implicit_inline_arg=True,
            nargs=0,
            allow_no_args=True,
            required=False,
            metavar=(),
            mutex_group=None,
            usage=yuio.COLLAPSE,
            help="Enable or disable ANSI colors.",
            help_group=yuio.cli.MISC_GROUP,
            show_if_inherited=False,
            allow_abbrev=False,
            dest="_color",
            default_desc=None,
        )

    def process(
        self,
        cli_parser: yuio.cli.CliParser[yuio.cli.Namespace],
        flag: yuio.cli.Flag | None,
        arguments: yuio.cli.Argument | list[yuio.cli.Argument],
        ns: yuio.cli.Namespace,
    ):
        if isinstance(arguments, yuio.cli.Argument):
            if flag and flag.value == "--no-color":
                raise yuio.cli.ArgumentError(
                    "This flag can't have arguments", flag=flag, arguments=arguments
                )
            if arguments.value.casefold() not in self._ALLOWED_VALUES:
                raise yuio.cli.ArgumentError(
                    "Can't parse `%r` as color, should be %s",
                    arguments.value,
                    yuio.string.Or(value for value, _ in self._PUBLIC_VALUES),
                    flag=flag,
                    arguments=arguments,
                )

    @functools.cached_property
    def primary_short_flag(self):
        return None

    @functools.cached_property
    def primary_long_flags(self):
        return ["--color", "--no-color"]

    def format_alias_flags(
        self,
        ctx: yuio.string.ReprContext,
        /,
        *,
        all: bool = False,
    ) -> (
        list[yuio.string.ColorizedString | tuple[yuio.string.ColorizedString, str]]
        | None
    ):
        if self.flags is yuio.POSITIONAL:
            return None

        primary_flags = set(self.primary_long_flags or [])
        if self.primary_short_flag:
            primary_flags.add(self.primary_short_flag)

        aliases: list[
            yuio.string.ColorizedString | tuple[yuio.string.ColorizedString, str]
        ] = []
        flag_color = ctx.get_color("hl/flag:sh-usage")
        punct_color = ctx.get_color("hl/punct:sh-usage")
        metavar_color = ctx.get_color("hl/metavar:sh-usage")
        res = yuio.string.ColorizedString()
        res.start_no_wrap()
        res.append_color(flag_color)
        res.append_str("--color")
        res.end_no_wrap()
        res.append_color(punct_color)
        res.append_str("={")
        sep = False
        for value, _ in self._PUBLIC_VALUES:
            if sep:
                res.append_color(punct_color)
                res.append_str("|")
            res.append_color(metavar_color)
            res.append_str(value)
            sep = True
        res.append_color(punct_color)
        res.append_str("}")
        aliases.append(res)
        return aliases

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return yuio.complete.Choice(
            [
                yuio.complete.Option(value, comment)
                for value, comment in self._PUBLIC_VALUES
            ]
        ), False
