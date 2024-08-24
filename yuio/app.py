# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module expands on :mod:`yuio.config` to build CLI apps.

Creating and running an app
---------------------------

Yuio's CLI applications have functional interface. Decorate main function
with the :func:`app` decorator, and use :meth:`App.run` method to start it::

    >>> # Let's define an app with one flag and one positional argument.
    ... @app
    ... def main(
    ...     #: help message for `arg`.
    ...     arg: str = positional(),
    ...     #: help message for `--flag`.
    ...     flag: int = 0
    ... ):
    ...     \"\"\"this command does a thing.\"\"\"
    ...     yuio.io.info("flag=%r, arg=%r", flag, arg)

    >>> # We can now use `main.run` to parse arguments and invoke `main`.
    ... # Notice that `run` does not return anything. Instead, it terminates
    ... # python process with an appropriate exit code.
    ... main.run("--flag 10 foobar!".split()) # doctest: +SKIP
    flag=10 arg='foobar!'

..
    >>> try:
    ...     main.run()
    ... except SystemExit as e:
    ...     print(e)

Function's arguments will become program's flags and positionals, and function's
docstring will become app's :attr:`~App.description`.

.. autofunction:: app

.. autoclass:: App

   .. automethod:: run


Configuring flags and options
-----------------------------

Main function parameters, much like :class:`~yuio.config.Config` fields,
can be configured. Their names and type hints are used to derive default values,
which can be overridden by the :func:`field` function. They can also contain other
configs, essentially allowing you to nest CLI flags.

.. autofunction:: field
   :noindex:

.. autodata:: yuio.DISABLED
   :noindex:

.. autodata:: yuio.MISSING
   :noindex:

.. autodata:: yuio.POSITIONAL
   :noindex:

There are also a few helpers that are specific to the :mod:`yuio.app` module:

.. autofunction:: inline
   :noindex:

.. autofunction:: positional

Flag names are derived from field names.
Use the :func:`field` function to override them::

    @app
    def main(
        # Will be loaded from `--input`.
        input: pathlib.Path | None = None,

        # Will be loaded from `-o` or `--output`.
        output: pathlib.Path | None = field(None, flags=['-p', '--pid'])
    ):
        ...

In nested configs, flags are prefixed with name
of a field that contains the nested config::

    class KillCmdConfig(Config):
        # Will be loaded from `--signal`.
        signal: int

        # Will be loaded from `-p` or `--pid`.
        pid: int = field(flags=['-p', '--pid'])

    @app
    def main(
        # `kill_cmd.signal` will be loaded from `--kill-cmd-signal`.
        kill_cmd: KillCmdConfig,

        # `copy_cmd_2.signal` will be loaded from `--kill-signal`.
        kill_cmd_2: KillCmdConfig = field(flags='--kill'),

        # `kill_cmd_3.signal` will be loaded from `--signal`.
        kill_cmd_3: KillCmdConfig = field(flags=''),
    ):
        ...

.. note::

   Positional arguments are not allowed in configs,
   only in apps.

Help messages for the flags are parsed from line comments
right above the field definition (comments must start with ``#:``).
This works for both functions and config classes.
The :func:`field` function allows overriding them. Help messages
are all formatted using the Markdown (see :mod:`yuio.md`).

Parsers for CLI argument values are derived from type hints.
Use the `parser` parameter of the :func:`field` function to override them.

Arguments with bool parsers and parsers that support
:meth:`parsing collections <yuio.parse.Parser.supports_parse_many>`
are handled to provide better CLI experience::

    @app
    def main(
        # Will create flags `--verbose` and `--no-verbose`.
        verbose: bool = True,

        # Will create a flag with `nargs=*`: `--inputs path1 path2 ...`
        inputs: list[Path],
    ):


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

   .. autoattribute:: setup_io

   .. autoattribute:: setup_logging


Creating sub-commands
---------------------

You can create multiple sub-commands for the main function,
using the :meth:`App.subcommand` method:

.. class:: App
   :noindex:

   .. automethod:: subcommand

For example::

    @app
    def main(): ...

    @main.subcommand
    def push(): ...

    @main.subcommand
    def pop(): ...

There is no limit to how deep you can nest subcommands, but for usability reasons
we suggest not exceeding level of sub-sub-commands (``git stash push``, anyone?)

When user invokes a subcommand, the ``main()`` function is called first,
then subcommand. In the above example, invoking our app with subcommand ``push``
will cause ``main()`` to be called first, then ``push()``.

This behavior is useful when you have some global configuration flags
attached to the ``main()`` command. See the `example app`_ for details.

.. _example app: https://github.com/taminomara/yuio/blob/main/examples/app


Controlling how sub-commands are invoked
----------------------------------------

By default, if a command has sub-commands, the user is required to provide
a sub-command. This behavior can be disabled by setting :attr:`App.subcommand_required`
to :data:`False`.

When this happens, we need to understand whether a subcommand was invoked or not.
To determine this, you can accept a special parameter called ``_command_info``
of type :class:`CommandInfo`. It will contain info about the current function,
including its name and subcommand::

    @app
    def main(_command_info: CommandInfo):
        if _command_info.subcommand is not None:
            # A subcommand was invoked.
            ...

.. autoclass:: CommandInfo

   .. autoattribute:: name

   .. autoattribute:: subcommand

You can call the subcommand on your own by using ``_command_info`` as a callable.
However, you must return :data:`False` from your function, this will prevent Yuio
from calling subcommand for a second time::

    @app
    def main(_command_info: CommandInfo):
        if _command_info.subcommand is not None and ...:
            _command_info()  # manually invoking a subcommand

        # Ensure that Yuio doesn't call a subcommand again.
        # This interface is similar to one of __exit__ functions,
        # where you return `True` to suppress an exception.
        return False

.. autoclass:: CommandInfo
   :noindex:

   .. automethod:: __call__

"""


import argparse
import contextlib
import dataclasses
import functools
import inspect
import logging
import os
import re
import string
import sys
import types
from yuio import _t
from dataclasses import dataclass

import yuio
import yuio.complete
import yuio.config
import yuio.exec
import yuio.io
import yuio.parse
import yuio.term
import yuio.md
from yuio.config import field, inline, positional

__all__ = [
    "field",
    "inline",
    "positional",
    "Command",
    "app",
    "App",
]

Command: _t.TypeAlias = _t.Callable[..., None]


@_t.overload
def app(
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
) -> _t.Callable[[Command], "App"]:
    ...


@_t.overload
def app(
    command: Command,
    /,
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
) -> "App":
    ...


def app(
    command: "_t.Optional[Command]" = None,
    /,
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
):
    """Create an application.

    This is a decorator that's supposed to be used on the main method
    of the application. This decorator returns an :class:`App` object.

    See :class:`App` for description of function's parameters.

    """

    def registrar(command: Command, /) -> App:
        return App(
            command,
            prog=prog,
            usage=usage,
            help=help,
            description=description,
            epilog=epilog,
        )

    if command is None:
        return registrar
    else:
        return registrar(command)


@dataclass(frozen=True)
class CommandInfo:
    """Data about the invoked command."""

    #: Name of the current command.
    #:
    #: If it was invoked by alias,
    #: this will contains the primary command name.
    #:
    #: For the main function, the name will be set to ``'__main__'``.
    name: str

    #: Subcommand of this command, if one was given.
    subcommand: "_t.Optional[CommandInfo]"

    # Internal, do not use.
    _config: _t.Any = dataclasses.field(repr=False)

    def __call__(self) -> _t.Literal[False]:
        """Execute this command.

        This function always returns :data:`False`, so you can call a subcommand
        and exit from a parent command in a single line::

            @app
            def main(_command_info: CommandInfo):
                if _command_info.subcommand is not None:
                    # Manually call a subcommand and return `False`:
                    return _command_info()

        """

        if self._config is not None:
            should_invoke_subcommand = self._config._run(self)
            if should_invoke_subcommand is None:
                should_invoke_subcommand = True
        else:
            should_invoke_subcommand = True

        if should_invoke_subcommand and self.subcommand is not None:
            self.subcommand()

        return False


class App:
    """A class that encapsulates app settings and logic for running it.

    It is better to create instances of this class using the :func:`app` decorator,
    as it provides means to decorate the main function and specify all of the app's
    parameters.

    """

    @dataclass(frozen=True)
    class _SubApp:
        app: "App"
        name: str
        aliases: _t.Optional[_t.List[str]] = None
        is_primary: bool = False

    def __init__(
        self,
        command: Command,
        /,
        *,
        prog: _t.Optional[str] = None,
        usage: _t.Optional[str] = None,
        help: _t.Optional[str] = None,
        description: _t.Optional[str] = None,
        epilog: _t.Optional[str] = None,
    ):
        #: Program or subcommand display name.
        #:
        #: By default, inferred from :data:`sys.argv` and subcommand names.
        #:
        #: See `prog <https://docs.python.org/3/library/argparse.html#prog>`_.
        self.prog: _t.Optional[str] = prog

        #: Program or subcommand synapsis.
        #:
        #: This string will be colorized according to `bash` syntax,
        #: and then it will be ``%``-formatted with a single keyword argument `prog`.
        #: If command supports multiple signatures, each of them should be listed
        #: on a separate string. For example::
        #:
        #:     @app
        #:     def main(): ...
        #:
        #:     main.usage = """
        #:     %(prog)s [-q] [-f] [-m] [<branch>]
        #:     %(prog)s [-q] [-f] [-m] --detach [<branch>]
        #:     %(prog)s [-q] [-f] [-m] [--detach] <commit>
        #:     ...
        #:     """
        #:
        #: By default, generated from CLI flags by argparse.
        #:
        #: See `usage <https://docs.python.org/3/library/argparse.html#usage>`_.
        self.usage: _t.Optional[str] = usage

        if not description and command.__doc__:
            description = command.__doc__

        #: Text that is shown before CLI flags help, usually contains
        #: short description of the program or subcommand.
        #:
        #: The text should be formatted using markdown. For example::
        #:
        #:     @app
        #:     def main(): ...
        #:
        #:     main.description = """
        #:     this command does a thing.
        #:
        #:     # different ways to do a thing
        #:
        #      this command can apply multiple algorithms to achieve
        #:     a necessary state in which a thing can be done. This includes:
        #:
        #:     - randomly turning the screen on and off;
        #:
        #:     - banging a head on a table;
        #:
        #:     - fiddling with your PCs power levels.
        #:
        #:     By default, the best algorithm is determined automatically.
        #:     However, you can hint a preferred algorithm via the `--hint-algo` flag.
        #:
        #:     """
        #:
        #: By default, inferred from command's description.
        #:
        #: See `description <https://docs.python.org/3/library/argparse.html#description>`_.
        self.description: _t.Optional[str] = description

        if not help and description:
            lines = description.split("\n\n", 1)
            help = lines[0].rstrip(".")

        #: Short help message that is shown when listing subcommands.
        #:
        #: See `help <https://docs.python.org/3/library/argparse.html#help>`_.
        self.help: _t.Optional[str] = help

        #: Text that is shown after the main portion of the help message.
        #:
        #: Text format is identical to the one for :attr:`~App.description`.
        #:
        #: See `epilog <https://docs.python.org/3/library/argparse.html#epilog>`_.
        self.epilog: _t.Optional[str] = epilog

        #: Allow abbreviating CLI flags if that doesn't create ambiguity.
        #:
        #: Disabled by default.
        #:
        #: See `allow_abbrev <https://docs.python.org/3/library/argparse.html#allow-abbrev>`_.
        self.allow_abbrev: bool = False

        #: Require the user to provide a subcommand for this command.
        #:
        #: If this command doesn't have any subcommands, this option is ignored.
        #:
        #: Enabled by default.
        self.subcommand_required: bool = True

        #: If :data:`True`, the app will call :func:`yuio.io.setup` during
        #: its initialization. Disable this if you want to customize initialization.
        self.setup_io: bool = True

        #: If :data:`True`, the app will call :func:`logging.basicConfig` during
        #: its initialization. Disable this if you want to customize initialization.
        #:
        #: Disabling this option also removes the ``--verbose`` flag form the CLI.
        self.setup_logging: bool = True

        self.__sub_apps: _t.Dict[str, "App._SubApp"] = {}

        if callable(command):
            self.__config_type = _command_from_callable(command)
        else:
            raise TypeError(f"expected a function, got {command}")

        functools.update_wrapper(
            self,  # type: ignore
            command,
            assigned=("__module__", "__name__", "__qualname__", "__doc__"),
            updated=(),
        )

    @_t.overload
    def subcommand(
        self,
        name: _t.Optional[str] = None,
        /,
        *,
        aliases: _t.Optional[_t.List[str]] = None,
        prog: _t.Optional[str] = None,
        usage: _t.Optional[str] = None,
        help: _t.Optional[str] = None,
        description: _t.Optional[str] = None,
        epilog: _t.Optional[str] = None,
    ) -> _t.Callable[[Command], "App"]:
        ...

    @_t.overload
    def subcommand(
        self,
        cb: Command,
        /,
        *,
        name: _t.Optional[str] = None,
        aliases: _t.Optional[_t.List[str]] = None,
        prog: _t.Optional[str] = None,
        usage: _t.Optional[str] = None,
        help: _t.Optional[str] = None,
        description: _t.Optional[str] = None,
        epilog: _t.Optional[str] = None,
    ) -> "App":
        ...

    def subcommand(
        self,
        cb_or_name: _t.Union[str, Command, None] = None,
        /,
        *,
        name: _t.Optional[str] = None,
        aliases: _t.Optional[_t.List[str]] = None,
        prog: _t.Optional[str] = None,
        usage: _t.Optional[str] = None,
        help: _t.Optional[str] = None,
        description: _t.Optional[str] = None,
        epilog: _t.Optional[str] = None,
    ):
        """Register a subcommand for the given app.

        This method can be used as a decorator, similar to the :func:`app` function.

        """

        if isinstance(cb_or_name, str):
            cb = None
            name = cb_or_name
        else:
            cb = cb_or_name

        def registrar(cb: Command, /) -> App:
            app = App(
                cb,
                prog=prog,
                usage=usage,
                help=help,
                description=description,
                epilog=epilog,
            )

            app.allow_abbrev = self.allow_abbrev

            main_name = name or yuio.to_dash_case(cb.__name__)
            self.__sub_apps[main_name] = App._SubApp(
                app, main_name, aliases, is_primary=True
            )
            if aliases:
                alias_app = App._SubApp(app, main_name)
                self.__sub_apps.update({alias: alias_app for alias in aliases})

            return app

        if cb is None:
            return registrar
        else:
            return registrar(cb)

    def run(self, args: _t.Optional[_t.List[str]] = None) -> _t.NoReturn:
        """Parse arguments, set up :mod:`yuio.io` and :mod:`logging`,
        and run the application.

        If no `args` are given, parse :data:`sys.argv`.

        """

        if args is None:
            args = sys.argv[1:]

        if "--yuio-custom-completer--" in args:
            index = args.index("--yuio-custom-completer--")
            yuio.complete._run_custom_completer(args[index + 1], args[index + 2])
            exit(0)

        parser = self.__setup_arg_parser()
        namespace = parser.parse_args(args)


        if self.setup_io:
            yuio.io.setup(query_theme=True)

        if self.setup_logging:
            verbosity_level = getattr(namespace, "verbosity_level", 0)
            logging_level = {0: logging.WARNING, 1: logging.INFO, 2: logging.DEBUG}.get(
                verbosity_level, logging.WARNING
            )
            logging.basicConfig(handlers=[yuio.io.Handler()], level=logging_level)

        try:
            command = self.__load_from_namespace(namespace)
            command()
            exit(0)
        except (argparse.ArgumentTypeError, argparse.ArgumentError) as e:
            parser.error(str(e))
        except Exception as e:
            yuio.io.error_with_tb("Error: %s", e)
            exit(1)

    def __load_from_namespace(self, namespace: argparse.Namespace) -> CommandInfo:
        return self.__load_from_namespace_impl(namespace, "app")

    def __load_from_namespace_impl(
        self, namespace: argparse.Namespace, ns_prefix: str
    ) -> CommandInfo:
        config = self.__config_type._load_from_namespace(namespace, ns_prefix=ns_prefix)
        subcommand = None

        if name := getattr(namespace, ns_prefix + "@subcommand", None):
            sub_app = self.__sub_apps[name]
            subcommand = dataclasses.replace(
                sub_app.app.__load_from_namespace_impl(
                    namespace, f"{ns_prefix}/{sub_app.name}"
                ),
                name=sub_app.name,
            )

        return CommandInfo("__main__", subcommand, _config=config)

    def __setup_arg_parser(
        self, parser: _t.Optional[argparse.ArgumentParser] = None
    ) -> argparse.ArgumentParser:
        prog = self.prog
        if not prog:
            prog = os.path.basename(sys.argv[0])

        parser = parser or argparse.ArgumentParser(
            prog=self.prog,
            usage=self.usage,
            description=self.description,
            epilog=self.epilog,
            allow_abbrev=self.allow_abbrev,
            formatter_class=_HelpFormatter,  # type: ignore
        )

        self.__setup_arg_parser_impl(parser, "app", prog)

        aux = parser.add_argument_group("auxiliary options")
        color = aux.add_mutually_exclusive_group()
        color.add_argument(
            "--force-color",
            help="force-enable colored output",
            action="store_true",  # Note: `yuio.term` inspects `sys.argv` on its own
        )
        color.add_argument(
            "--force-no-color",
            help="force-disable colored output",
            action="store_true",  # Note: `yuio.term` inspects `sys.argv` on its own
        )

        if self.setup_logging:
            aux.add_argument(
                "-v",
                "--verbose",
                help="increase output verbosity",
                action="count",
                dest="verbosity_level",
            )

        class CompletionsAction(argparse.Action):
            @staticmethod
            def get_parser() -> yuio.parse.Parser[str]:
                return yuio.parse.Str().lower().one_of(["all", "bash", "zsh", "fish"])

            def __init__(_self, *args, **kwargs):
                kwargs["metavar"] = _self.get_parser().describe_or_def()
                super().__init__(*args, **kwargs)

            def __call__(_self, parser, namespace, value, *args):
                self._App__write_completions(_self.get_parser().parse(value or "all"))  # type: ignore
                parser.exit()

        aux.add_argument(
            "--completions",
            help="generate autocompletion scripts and exit",
            nargs="?",
            action=CompletionsAction,
        )

        return parser

    def __setup_arg_parser_impl(
        self, parser: argparse.ArgumentParser, ns_prefix: str, prog: str
    ):
        self.__config_type._setup_arg_parser(parser, ns_prefix=ns_prefix)

        if self.__sub_apps:
            subparsers = parser.add_subparsers(
                required=self.subcommand_required,
                dest=ns_prefix + "@subcommand",
                metavar="<subcommand>",
            )

            for name, sub_app in self.__sub_apps.items():
                if not sub_app.is_primary:
                    continue

                sub_prog = f"{prog} {name}"

                parser = subparsers.add_parser(
                    name,
                    aliases=sub_app.aliases or [],
                    prog=sub_prog,
                    help=sub_app.app.help,
                    description=sub_app.app.description,
                    epilog=sub_app.app.epilog,
                    allow_abbrev=self.allow_abbrev,
                    formatter_class=_HelpFormatter,  # type: ignore
                )

                sub_app.app.__setup_arg_parser_impl(
                    parser, ns_prefix=f"{ns_prefix}/{name}", prog=sub_prog
                )

    def __get_completions(self) -> yuio.complete._CompleterSerializer:
        serializer = yuio.complete._CompleterSerializer()
        self.__setup_arg_parser(serializer.as_parser())
        return serializer

    def __write_completions(self, shell: str):
        self.__get_completions().write_completions(self.prog, shell)


class _NoReprConfig(yuio.config.Config):
    def __repr__(self):
        return "<move along, nothing to see here>"


def _command_from_callable(cb: Command) -> _t.Type[yuio.config.Config]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    accepts_command_info = False

    try:
        docs = yuio._find_docs(cb)
    except Exception:
        yuio._logger.exception(
            "Unable to get documentation for %s",
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
            field = _t.cast(yuio.config._FieldSettings, yuio.config.field(field))
        if field.default is yuio.MISSING:
            field = dataclasses.replace(field, required=True)
        if name in docs:
            field = dataclasses.replace(field, help=docs[name])

        if param.annotation is param.empty:
            raise TypeError(f"param {name} requires type annotation")

        dct[name] = field
        annotations[name] = param.annotation

    dct["_run"] = _command_from_callable_run_impl(
        cb, list(annotations.keys()), accepts_command_info
    )
    dct["__annotations__"] = annotations
    dct["__module__"] = getattr(cb, "__module__", None)
    dct["__doc__"] = getattr(cb, "__doc__", None)

    return types.new_class(
        cb.__name__,
        (_NoReprConfig,),
        {"_allow_positionals": True},
        exec_body=lambda ns: ns.update(dct),
    )


def _command_from_callable_run_impl(
    cb: Command, params: _t.List[str], accepts_command_info
):
    def run(self, command_info):
        kw = {name: getattr(self, name) for name in params}
        if accepts_command_info:
            kw["_command_info"] = command_info
        return cb(**kw)

    return run


_MAX_ARGS_COLUMN_WIDTH = 24


class _CliMdFormatter(yuio.md.MdFormatter):  # type: ignore
    def __init__(
        self,
        theme: yuio.term.Theme,
        *,
        width: _t.Optional[int] = None,
        allow_headings: bool = True,
    ):
        self._heading_indent = contextlib.ExitStack()
        self._args_column_width = _MAX_ARGS_COLUMN_WIDTH

        super().__init__(
            theme,
            width=width,
            allow_headings=allow_headings,
        )

    def colorize(
        self,
        s: str,
        /,
        *,
        default_color: _t.Union[yuio.term.Color, str] = yuio.term.Color.NONE,
    ):
        return yuio.md._colorize(
            self.theme,
            s,
            default_color=default_color,
            parse_cli_flags_in_backticks=True,
        )

    def _format_Heading(self, node: yuio.md.Heading):
        if node.level == 1:
            self._heading_indent.close()

            decoration = self.theme.msg_decorations.get("heading/section", "")
            with self._indent("msg/decoration:heading/section", decoration):
                self._format_Text(
                    node,
                    default_color=self.theme.get_color(f"msg/text:heading/section"),
                )

            self._heading_indent.enter_context(self._indent(None, "  "))

            self._is_first_line = True
        else:
            super()._format_Heading(node)

    def _format_Usage(self, node: "_Usage"):
        with self._indent(None, node.prefix):
            if node.usage_override:
                for line in node.usage_override.wrap(
                    self.width,
                    break_on_hyphens=False,
                    preserve_spaces=True,
                    preserve_newlines=True,
                    first_line_indent=self._first_line_indent,
                    continuation_indent=self._continuation_indent,
                ):
                    self._line(line)
                return

            line = yuio.term.ColorizedString(self._first_line_indent)
            cur_width = self._first_line_indent.width
            needs_space = False

            if node.usage:
                line += node.usage
                cur_width += node.usage.width
                needs_space = True

            for arr in [node.optionals, node.positionals]:
                total_options_width = sum(elem.width for elem in arr) + len(arr) - 1

                if (
                    cur_width + total_options_width + needs_space > self.width
                    and self._continuation_indent.width + total_options_width
                    <= self.width
                ):
                    self._line(line)
                    line = yuio.term.ColorizedString(self._first_line_indent)
                    cur_width = self._first_line_indent.width
                    needs_space = False

                for elem in arr:
                    if needs_space and cur_width + 1 + elem.width > self.width:
                        self._line(line)
                        line = yuio.term.ColorizedString(self._first_line_indent)
                        cur_width = self._first_line_indent.width
                        needs_space = False
                    if needs_space:
                        line += " "
                        cur_width += 1
                    line += elem
                    cur_width += elem.width
                    needs_space = True

            if line:
                self._line(line)

    def _format_HelpArg(self, node: "_HelpArg"):
        if node.help is None:
            self._line(self._first_line_indent + node.args)
            return

        if node.args.width > self._args_column_width:
            self._line(self._first_line_indent + node.indent + node.args)
            indent_ctx = self._indent(None, " " * self._args_column_width)
        else:
            indent_ctx = self._indent(
                None,
                node.indent
                + node.args
                + " " * (self._args_column_width - len(node.indent) - node.args.width),
            )

        with indent_ctx:
            if node.help:
                self._format(node.help)

    def _format_HelpArgGroup(self, node: "_HelpArgGroup"):
        for item in node.items:
            self._format(item)


@dataclass(**yuio._with_slots())
class _Usage(yuio.md.AstBase):
    prefix: yuio.term.ColorizedString
    usage_override: yuio.term.ColorizedString
    usage: yuio.term.ColorizedString
    optionals: _t.List[yuio.term.ColorizedString]
    positionals: _t.List[yuio.term.ColorizedString]


@dataclass(**yuio._with_slots())
class _HelpArg(yuio.md.AstBase):
    indent: str
    args: yuio.term.ColorizedString
    help: _t.Optional[yuio.md.AstBase]


@dataclass(**yuio._with_slots())
class _HelpArgGroup(yuio.md.Container[_HelpArg]):
    pass


class _HelpFormatter(object):
    def __init__(self, prog: str):
        self._prog = prog
        self._term = yuio.io.get_term()
        self._theme = yuio.io.get_theme()
        self._formatter = _CliMdFormatter(self._theme)
        self._nodes: _t.List[yuio.md.AstBase] = []
        self._args_column_width = 0

    def start_section(self, heading: _t.Optional[str]):
        if heading:
            if not heading.endswith(":"):
                heading += ":"
            self._nodes.append(yuio.md.Heading([heading], 1))

    def end_section(self):
        pass

    def add_text(self, text):
        if text is not argparse.SUPPRESS and text:
            self._nodes.append(self._formatter.parse(text))

    def add_usage(
        self, usage, actions: _t.Iterable[argparse.Action], groups, prefix=None
    ):
        if usage is argparse.SUPPRESS:
            return

        if prefix is not None:
            c_prefix = self._formatter.colorize(
                prefix,
                default_color="msg/text:heading/section",
            )
        else:
            c_prefix = yuio.term.ColorizedString(
                [self._theme.get_color("msg/text:heading/section"), "usage: "]
            )

        c_usage = yuio.term.ColorizedString()
        c_usage_override = yuio.term.ColorizedString()
        c_optionals: _t.List[yuio.term.ColorizedString] = []
        c_positionals: _t.List[yuio.term.ColorizedString] = []

        if usage is not None:
            usage = self._formatter._dedent(usage)
            sh_usage_highlighter = yuio.md.SyntaxHighlighter.get_highlighter("sh-usage")

            c_usage_override = sh_usage_highlighter.highlight(
                self._theme,
                usage,
            )
        else:
            c_usage = yuio.term.ColorizedString(
                [self._theme.get_color("hl/prog:sh-usage"), str(self._prog)]
            )

            optionals: _t.List[
                _t.Union[argparse.Action, argparse._MutuallyExclusiveGroup]
            ] = []
            positionals: _t.List[
                _t.Union[argparse.Action, argparse._MutuallyExclusiveGroup]
            ] = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)
            for group in groups:
                if len(group._group_actions) <= 1:
                    continue
                for arr in [optionals, positionals]:
                    try:
                        start = arr.index(group._group_actions[0])
                    except (ValueError, IndexError):
                        continue
                    else:
                        end = start + len(group._group_actions)
                        if arr[start:end] == group._group_actions:
                            arr[start:end] = [group]

            for res, arr in [(c_optionals, optionals), (c_positionals, positionals)]:
                for elem in arr:
                    if isinstance(elem, argparse.Action):
                        c_elem = yuio.term.ColorizedString()
                        self._format_action_short(elem, c_elem)
                        res.append(c_elem)
                    elif elem._group_actions:
                        for i, action in enumerate(elem._group_actions):
                            c_elem = yuio.term.ColorizedString()
                            if i == 0:
                                c_elem += self._theme.get_color(
                                    "msg/text:code/sh-usage"
                                )
                                c_elem += "(" if elem.required else "["
                            self._format_action_short(action, c_elem, in_group=True)
                            if i + 1 < len(elem._group_actions):
                                c_elem += self._theme.get_color(
                                    "msg/text:code/sh-usage"
                                )
                                c_elem += " |"
                            else:
                                c_elem += self._theme.get_color(
                                    "msg/text:code/sh-usage"
                                )
                                c_elem += ")" if elem.required else "]"
                            res.append(c_elem)

        self._nodes.append(
            _Usage(
                c_prefix,
                c_usage_override,
                c_usage,
                c_optionals,
                c_positionals,
            )
        )

    def add_argument(self, action: argparse.Action, indent: str = ""):
        if action.help is not argparse.SUPPRESS:
            c_usage = yuio.term.ColorizedString()
            sep = False
            if not action.option_strings:
                self._format_action_metavar(action, 0, c_usage)
            for option_string in action.option_strings:
                if sep:
                    c_usage += self._theme.get_color("msg/text:code/sh-usage")
                    c_usage += ", "
                c_usage += self._theme.get_color("hl/flag:sh-usage")
                c_usage += option_string
                if action.nargs != 0:
                    c_usage += self._theme.get_color("msg/text:code/sh-usage")
                    c_usage += " "
                self._format_action_metavar_expl(action, c_usage)
                sep = True

            if self._nodes and isinstance(self._nodes[-1], _HelpArgGroup):
                group = self._nodes[-1]
            else:
                group = _HelpArgGroup([])
                self._nodes.append(group)
            group.items.append(
                _HelpArg(
                    indent,
                    c_usage,
                    self._formatter.parse(action.help) if action.help else None,
                )
            )

            arg_width = len(indent) + c_usage.width + 2
            if arg_width <= _MAX_ARGS_COLUMN_WIDTH:
                self._args_column_width = max(self._args_column_width, arg_width)

            try:
                get_subactions = action._get_subactions  # type: ignore
            except AttributeError:
                pass
            else:
                self.add_arguments(get_subactions(), indent + "  ")

    def add_arguments(self, actions, indent: str = ""):
        for action in actions:
            self.add_argument(action, indent)

    def format_help(self) -> str:
        self._formatter._args_column_width = self._args_column_width
        return "".join(
            self._formatter.format_node(yuio.md.Document(self._nodes)).process_colors(
                self._term
            )
        )

    def _format_action_short(
        self,
        action: argparse.Action,
        out: yuio.term.ColorizedString,
        in_group: bool = False,
    ):
        if not in_group and not action.required:
            out += self._theme.get_color("msg/text:code/sh-usage")
            out += "["

        if action.option_strings:
            out += self._theme.get_color("hl/flag:sh-usage")
            out += action.option_strings[0]
            if action.nargs != 0:
                out += self._theme.get_color("msg/text:code/sh-usage")
                out += " "

        self._format_action_metavar_expl(action, out)

        if not in_group and not action.required:
            out += self._theme.get_color("msg/text:code/sh-usage")
            out += "]"

    def _format_action_metavar_expl(
        self, action: argparse.Action, out: yuio.term.ColorizedString
    ):
        nargs = action.nargs if action.nargs is not None else 1

        if nargs == argparse.OPTIONAL:
            out += self._theme.get_color("msg/text:code/sh-usage")
            out += "["

            self._format_action_metavar(action, 0, out)

            out += self._theme.get_color("msg/text:code/sh-usage")
            out += "]"
        elif nargs == argparse.ZERO_OR_MORE:
            out += self._theme.get_color("msg/text:code/sh-usage")
            out += "["

            self._format_action_metavar(action, 0, out)

            out += self._theme.get_color("msg/text:code/sh-usage")
            out += " ...]"
        elif nargs == argparse.ONE_OR_MORE:
            self._format_action_metavar(action, 0, out)

            out += self._theme.get_color("msg/text:code/sh-usage")
            out += " ["

            self._format_action_metavar(action, 1, out)

            out += self._theme.get_color("msg/text:code/sh-usage")
            out += " ...]"
        elif nargs == argparse.REMAINDER:
            out += self._theme.get_color("msg/text:code/sh-usage")
            out += "..."
        elif nargs == argparse.PARSER:
            self._format_action_metavar(action, 1, out)

            out += self._theme.get_color("msg/text:code/sh-usage")
            out += " ..."
        elif isinstance(nargs, int):
            sep = False
            for i in range(nargs):
                if sep:
                    out += self._theme.get_color("msg/text:code/sh-usage")
                    out += " "
                self._format_action_metavar(action, i, out)
                sep = True

    def _format_action_metavar(
        self, action: argparse.Action, n: int, out: yuio.term.ColorizedString
    ):
        metavar_t = action.metavar
        if not metavar_t and action.option_strings:
            metavar_t = f"<{action.option_strings[0]}>"
        if not metavar_t:
            metavar_t = "<value>"
        if isinstance(metavar_t, tuple):
            metavar = metavar_t[n] if n < len(metavar_t) else metavar_t[-1]
        else:
            metavar = metavar_t

        cli_color = self._theme.get_color("msg/text:code/sh-usage")
        metavar_color = self._theme.get_color("hl/metavar:sh-usage")
        cur_color = None
        is_punctuation = False
        for part in re.split(r"((?:[" + string.punctuation + r"]|\s)+)", metavar):
            if is_punctuation and cur_color is not cli_color:
                cur_color = cli_color
                out += cli_color
            elif not is_punctuation and cur_color is not metavar_color:
                cur_color = metavar_color
                out += metavar_color
            out += part
            is_punctuation = not is_punctuation

    def _format_args(self, *_):
        # argparse calls this method sometimes
        # to check if given metavar is valid or not (TODO!)
        pass
