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
        arg: str,  # [1]_
        /,
        *,
        #: help message for `--flag`
        flag: int = 0  # [2]_
    ):
        \"""this command does a thing\"""
        yuio.io.info("flag=%r, arg=%r", flag, arg)

    if __name__ == "__main__":
        # We can now use `main.run` to parse arguments and invoke `main`.
        # Notice that `run` does not return anything. Instead, it terminates
        # python process with an appropriate exit code.
        main.run("--flag 10 foobar!".split())

.. code-annotations::

    1.  Positional-only arguments become positional CLI options.
    2.  Other arguments become CLI flags.

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

    .. autoattribute:: subcommand_required

    .. autoattribute:: allow_abbrev

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

    .. automethod:: lazy_subcommand


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
from typing import ClassVar as _ClassVar

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
    "SubcommandRegistrar",
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
CB = _t.TypeVar("CB", bound="App[_t.Any]")


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
            subcommand_required=subcommand_required,
            allow_abbrev=allow_abbrev,
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
class CommandInfo:
    """
    Data about the invoked command.

    """

    def __init__(
        self,
        name: str,
        command: App[_t.Any],
        namespace: yuio.cli.ConfigNamespace["_CommandConfig"],
    ):
        self.name = name
        """
        Name of the current command.

        If it was invoked by alias,
        this will contains the primary command name.

        For the main function, the name will be set to ``"__main__"``.

        """

        self.__namespace = namespace
        self.__command = command
        self.__subcommand: CommandInfo | None | yuio.Missing = yuio.MISSING
        self.__executed: bool = False

    @property
    def subcommand(self) -> CommandInfo | None:
        """
        Subcommand of this command, if one was given.

        """

        if self.__subcommand is yuio.MISSING:
            self.__subcommand = self.__command._get_subcommand(self.__namespace)
        return self.__subcommand

    def __call__(self) -> _t.Literal[False]:
        """
        Execute this command.

        """

        if self.__executed:
            return False
        self.__executed = True

        should_invoke_subcommand = self.__command._invoke(self.__namespace, self)
        if should_invoke_subcommand is None:
            should_invoke_subcommand = True

        if should_invoke_subcommand and self.subcommand is not None:
            self.subcommand()

        return False


@dataclass(eq=False, match_args=False, slots=True)
class _SubcommandData:
    names: list[str]
    help: str | yuio.Disabled | None
    command: App[_t.Any] | _Lazy

    def load(self) -> App[_t.Any]:
        if isinstance(self.command, _Lazy):
            self.command = self.command.load()
        return self.command

    def make_cli_command(self):
        return self.load()._make_cli_command(self.name, self.help)

    @property
    def name(self):
        return self.names[0]


class SubcommandRegistrar(_t.Protocol):
    """
    Type for a callback returned from :meth:`App.subcommand`.

    """

    @_t.overload
    def __call__(self, cb: C, /) -> App[C]: ...
    @_t.overload
    def __call__(self, cb: CB, /) -> CB: ...
    def __call__(self, cb, /) -> _t.Any: ...


@dataclass(frozen=True, eq=False, match_args=False, slots=True)
class _Lazy:
    path: str

    def load(self) -> App[_t.Any]:
        import importlib

        path = self.path
        if ":" in path:
            mod, _, path = path.partition(":")
            path_parts = path.split(".")

            try:
                root = importlib.import_module(mod)
            except ImportError as e:
                raise ImportError(f"failed to import lazy subcommand {self.path}: {e}")
        else:
            path_parts = path.split(".")

            i = len(path_parts)
            while i > 0:
                try:
                    root = importlib.import_module(".".join(path_parts[:i]))
                    path_parts = path_parts[i:]
                except ImportError:
                    pass
                else:
                    break
                i -= 1
            else:
                raise ImportError(f"failed to import lazy subcommand {self.path}")

        for name in path_parts:
            try:
                root = getattr(root, name)
            except AttributeError as e:
                raise AttributeError(
                    f"failed to import lazy subcommand {self.path}: {e}"
                )

        if not isinstance(root, App):
            root = App(root)  # type: ignore

        return root


@_t.final
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
        subcommand_required: bool = True,
        allow_abbrev: bool = False,
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
        Program's primary name.

        For main app, this attribute controls its display name and generation
        of shell completion scripts.

        For subcommands, this attribute is ignored.

        By default, inferred from :data:`sys.argv`.

        """

        self.usage: str = yuio.util.dedent(usage) if usage else ""
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

        self.epilog: str = epilog or ""
        """
        Text that is shown after the main portion of the help message.

        The text should be formatted using Markdown or RST,
        depending on :attr:`~App.doc_format`.

        """

        self.subcommand_required: bool = subcommand_required
        """
        Require the user to provide a subcommand for this command.

        If this command doesn't have any subcommands, this option is ignored.

        Enabled by default.

        """

        self.allow_abbrev: bool = allow_abbrev
        """
        Allow abbreviating CLI flags if that doesn't create ambiguity.

        Disabled by default.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self.setup_logging: bool = setup_logging
        """
        If :data:`True`, the app will call :func:`logging.basicConfig` during
        its initialization. Disable this if you want to customize
        logging initialization.

        Disabling this option also removes the :flag:`--verbose` flag form the CLI.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self.theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = theme
        """
        A custom theme that will be passed to :func:`yuio.io.setup`
        on application startup.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self.version: str | None = version
        """
        If not :data:`None`, add :flag:`--version` flag to the CLI.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self.bug_report: yuio.dbg.ReportSettings | bool = bug_report
        """
        If not :data:`False`, add :flag:`--bug-report` flag to the CLI.

        This flag automatically collects data about environment and prints it
        in a format suitable for adding to a bug report.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self.is_dev_mode: bool | None = is_dev_mode
        """
        If :data:`True`, this will enable :func:`logging.captureWarnings`
        and configure internal Yuio logging to show warnings.

        By default, dev mode is detected by checking if :attr:`~App.version`
        contains substring ``"dev"``.

        .. tip::

            You can always enable full debug logging by setting environment
            variable ``YUIO_DEBUG``.

            If enabled, full log will be saved to ``YUIO_DEBUG_FILE``.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self.doc_format: _t.Literal["md", "rst"] | yuio.doc.DocParser = (
            doc_format or "rst"
        )
        """
        Format or parser that will be used to interpret documentation.

        .. note::

            This attribute should be set in the root app; it is ignored in subcommands.

        """

        self._subcommands: dict[str, _SubcommandData] = {}

        if callable(command):
            self._config_type, self._callback = _command_from_callable(command)
        else:
            raise TypeError(f"expected a function, got {command}")

        functools.update_wrapper(
            self,  # type: ignore
            command,
            assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            updated=(),
        )

        @functools.wraps(command)
        def wrapped_command(*args, **kwargs):
            a_params: list[str] = getattr(self._config_type, "_a_params")
            a_kw_params: list[str] = getattr(self._config_type, "_a_kw_params")
            var_a_param: str | None = getattr(self._config_type, "_var_a_param")
            kw_params: list[str] = getattr(self._config_type, "_kw_params")

            i = 0

            for name in a_params:
                if name in kwargs:
                    raise TypeError(
                        f"positional-only argument {name} was given as keyword argument"
                    )
                if i < len(args):
                    kwargs[name] = args[i]
                    i += 1

            for name in a_kw_params:
                if i >= len(args):
                    break
                if name in kwargs:
                    raise TypeError(f"argument {name} was given twice")
                kwargs[name] = args[i]
                i += 1

            if var_a_param:
                if var_a_param in kwargs:
                    raise TypeError(f"unexpected argument {var_a_param}")
                kwargs[var_a_param] = args[i:]
                i = len(args)
            elif i < len(args):
                s = "" if i == 1 else "s"
                raise TypeError(
                    f"expected at most {i} positional argument{s}, got {len(args)}"
                )

            kwargs.pop("_command_info", None)

            config = self._config_type(**kwargs)

            for name in a_params + a_kw_params + kw_params:
                if not hasattr(config, name) and name != "_command_info":
                    raise TypeError(f"missing required argument {name}")

            namespace = yuio.cli.ConfigNamespace(config)

            return CommandInfo("__main__", self, namespace)()

        self.__wrapped__ = _t.cast(C, wrapped_command)

    @property
    def wrapped(self) -> C:
        """
        The original callable what was wrapped by :func:`app`.

        """

        return self.__wrapped__

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
    ) -> SubcommandRegistrar: ...
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
    @_t.overload
    def subcommand(
        self,
        cb: CB,
        /,
        *,
        name: str | None = None,
        aliases: list[str] | None = None,
        help: str | yuio.Disabled | None = None,
    ) -> CB: ...
    def subcommand(
        self,
        cb: _t.Callable[..., None | bool] | App[_t.Any] | None = None,
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

        def registrar(cb, /) -> App[_t.Any]:
            if not isinstance(cb, App):
                cb = App(
                    cb,
                    usage=usage,
                    help=help,
                    description=description,
                    epilog=epilog,
                    subcommand_required=subcommand_required,
                )

            names = [name or _to_dash_case(cb.wrapped.__name__), *(aliases or [])]
            subcommand_data = _SubcommandData(names, help, cb)
            self._add_subcommand(subcommand_data)

            return cb

        if cb is None:
            return registrar
        else:
            return registrar(cb)

    def lazy_subcommand(
        self,
        path: str,
        name: str,
        /,
        *,
        aliases: list[str] | None = None,
        help: str | yuio.Disabled | None = None,
    ):
        """
        Add a subcommand for this app that will be imported and loaded on demand.

        :param path:
            dot-separated path to a command or command's main function.

            As a hint, module can be separated from the rest of the path with
            a semicolon, i.e. ``"module.submodule:class.method"``.
        :param name:
            subcommand's primary name.
        :param aliases:
            allows adding alias names for subcommand.
        :param help:
            allows specifying subcommand's help. If given, generating CLI help for
            base command will not require importing subcommand.
        :example:
            In module ``my_app.commands.run``:

            .. code-block:: python

                import yuio.app


                @yuio.app.app
                def command(): ...

            In module ``my_app.main``:

            .. code-block:: python

                import yuio.app


                @yuio.app.app
                def main(): ...


                main.lazy_subcommand("my_app.commands.run:command", "run")

        """

        subcommand_data = _SubcommandData([name, *(aliases or [])], help, _Lazy(path))
        self._add_subcommand(subcommand_data)

    def _add_subcommand(self, subcommand_data: _SubcommandData):
        for nam in subcommand_data.names:
            if nam in self._subcommands:
                subcommand = self._subcommands[nam].load()
                raise ValueError(
                    f"{self.__class__.__module__}.{self.__class__.__name__}: "
                    f"subcommand {nam!r} already registered in "
                    f"{subcommand.__class__.__module__}.{subcommand.__class__.__name__}"
                )
        self._subcommands.update(dict.fromkeys(subcommand_data.names, subcommand_data))

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

        prog = self.prog or pathlib.Path(sys.argv[0]).stem

        if "--yuio-custom-completer--" in args:
            index = args.index("--yuio-custom-completer--")
            _run_custom_completer(
                self._make_cli_command(prog, is_root=True),
                args[index + 1],
                args[index + 2],
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

            cli_command = self._make_cli_command(prog, is_root=True)
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

            CommandInfo("__main__", self, namespace)()
            sys.exit(0)
        except yuio.cli.ArgumentError as e:
            yuio.io.raw(e, add_newline=True, wrap=True)
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

    def _make_cli_command(
        self, name: str, help: str | yuio.Disabled | None = None, is_root: bool = False
    ):
        options: list[yuio.cli.Option[_t.Any]] = self._config_type._build_options()

        if is_root:
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

        subcommands: dict[
            str, yuio.cli.Command[_t.Any] | yuio.cli.LazyCommand[_t.Any]
        ] = {}
        for subcommand_name, subcommand_data in self._subcommands.items():
            if subcommand_data.name not in subcommands:
                subcommands[subcommand_data.name] = yuio.cli.LazyCommand(
                    help=subcommand_data.help,
                    loader=subcommand_data.make_cli_command,
                )
            subcommands[subcommand_name] = subcommands[subcommand_data.name]

        if help is None:
            help = self.help

        return yuio.cli.Command(
            name=name,
            desc=self.description,
            help=help,
            epilog=self.epilog,
            usage=self.usage,
            options=options,
            subcommands=subcommands,
            subcommand_required=self.subcommand_required,
            ns_ctor=self._create_ns,
            dest="_subcommand",
            ns_dest="_subcommand_ns",
        )

    def _create_ns(self):
        return yuio.cli.ConfigNamespace(self._config_type())

    def _invoke(
        self,
        namespace: yuio.cli.ConfigNamespace["_CommandConfig"],
        command_info: CommandInfo,
    ) -> bool | None:
        return self._callback(namespace.config, command_info)

    def _get_subcommand(
        self, namespace: yuio.cli.ConfigNamespace["_CommandConfig"]
    ) -> CommandInfo | None:
        config = namespace.config
        if config._subcommand is None:
            return None
        else:
            subcommand_ns = config._subcommand_ns
            subcommand_data = self._subcommands[config._subcommand]

            assert subcommand_ns is not None

            return CommandInfo(
                subcommand_data.name, subcommand_data.load(), subcommand_ns
            )


class _CommandConfig(yuio.config.Config):
    _a_params: _ClassVar[list[str]]
    _var_a_param: _ClassVar[str | None]
    _a_kw_params: _ClassVar[list[str]]
    _kw_params: _ClassVar[list[str]]
    _subcommand: str | None = None
    _subcommand_ns: yuio.cli.ConfigNamespace[_CommandConfig] | None = None


def _command_from_callable(
    cb: _t.Callable[..., None | bool],
) -> tuple[
    type[_CommandConfig],
    _t.Callable[[_CommandConfig, CommandInfo], bool | None],
]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    try:
        docs = _find_docs(cb)
    except Exception:
        yuio._logger.warning(
            "unable to get documentation for %s.%s",
            cb.__module__,
            cb.__qualname__,
        )
        docs = {}

    dct["_a_params"] = a_params = []
    dct["_var_a_param"] = var_a_param = None
    dct["_a_kw_params"] = a_kw_params = []
    dct["_kw_params"] = kw_params = []

    for name, param in sig.parameters.items():
        if param.kind is param.VAR_KEYWORD:
            raise TypeError("variadic keyword parameters are not supported")

        is_special = False
        if name.startswith("_"):
            is_special = True
            if name != "_command_info":
                raise TypeError(f"unknown special parameter {name}")
            if param.kind is param.VAR_POSITIONAL:
                raise TypeError(f"special parameter {name} can't be variadic")

        if param.default is not param.empty:
            field = param.default
        else:
            field = yuio.MISSING
        if not isinstance(field, yuio.config._FieldSettings):
            field = _t.cast(
                yuio.config._FieldSettings, yuio.config.field(default=field)
            )

        annotation = param.annotation
        if annotation is param.empty and not is_special:
            raise TypeError(f"parameter {name} requires type annotation")

        match param.kind:
            case param.POSITIONAL_ONLY:
                if field.flags is None:
                    field = dataclasses.replace(field, flags=yuio.POSITIONAL)
                a_params.append(name)
            case param.VAR_POSITIONAL:
                if field.flags is None:
                    field = dataclasses.replace(field, flags=yuio.POSITIONAL)
                annotation = list[annotation]
                dct["_var_a_param"] = var_a_param = name
            case param.POSITIONAL_OR_KEYWORD:
                a_kw_params.append(name)
            case param.KEYWORD_ONLY:
                kw_params.append(name)

        if not is_special:
            dct[name] = field
            annotations[name] = annotation

    dct["_color"] = None
    dct["_verbose"] = 0
    dct["_subcommand"] = None
    dct["_subcommand_ns"] = None
    dct["__annotations__"] = annotations
    dct["__module__"] = getattr(cb, "__module__", None)
    dct["__doc__"] = getattr(cb, "__doc__", None)
    dct["__yuio_pre_parsed_docs__"] = docs

    config = types.new_class(
        cb.__name__,
        (_CommandConfig,),
        {"_allow_positionals": True},
        exec_body=lambda ns: ns.update(dct),
    )
    callback = _command_from_callable_run_impl(
        cb, a_params + a_kw_params, var_a_param, kw_params
    )

    return config, callback


def _command_from_callable_run_impl(
    cb: _t.Callable[..., None | bool],
    a_params: list[str],
    var_a_param: str | None,
    kw_params: list[str],
):
    def run(config: _CommandConfig, command_info: CommandInfo):
        def get(name: str) -> _t.Any:
            return command_info if name == "_command_info" else getattr(config, name)

        args = [get(name) for name in a_params]
        if var_a_param is not None:
            args.extend(get(var_a_param))
        kwargs = {name: get(name) for name in kw_params}
        return cb(*args, **kwargs)

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
        root = command.subcommands[name].load()

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
