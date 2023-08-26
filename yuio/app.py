# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module expands on :mod:`yuio.config` to build CLI apps!

Creating and running an app
---------------------------

App arguments
-------------

App help
--------

Creating sub-commands
---------------------

Controlling how sub-commands are invoked
----------------------------------------

.. autoclass:: App
   :members:

"""


import abc
import argparse
import dataclasses
import inspect
import logging
import math
import os
import re
import shutil
import string
import sys
import textwrap
import types
import typing as _t
from dataclasses import dataclass
import functools

import yuio
import yuio.config
import yuio.io
import yuio.parse
import yuio.term
from yuio.config import field, inline, positional


Command: _t.TypeAlias = _t.Callable[..., None]


@_t.overload
def app(
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
) -> _t.Callable[["Command"], 'App']: ...


@_t.overload
def app(
    command: "Command",
    /,
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
) -> 'App': ...


def app(
    command: _t.Optional["Command"] = None,
    /,
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
):
    """

    """

    def registrar(command: "Command", /) -> App:
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


class App:
    @dataclass(frozen=True)
    class SubCommand:
        """Data about an invoked subcommand.

        """

        #: Name of the invoked subcommand.
        #:
        #: If subcommand was invoked by alias,
        #: this will contains the primary command name.
        name: str

        #: Subcommand of this command that was invoked.
        #:
        #: If this command has no subcommands, or subcommand was not invoked,
        #: this will be empty.
        subcommand: _t.Optional["App.SubCommand"]

        # Internal, do not use.
        _config: _t.Any

        def __call__(self):
            """Execute this subcommand.

            """

            if self._config is not None:
                should_invoke_subcommand = self._config._run(self.subcommand)
                if should_invoke_subcommand is None:
                    should_invoke_subcommand = True
            else:
                should_invoke_subcommand = True

            if should_invoke_subcommand and self.subcommand is not None:
                self.subcommand()

    @dataclass(frozen=True)
    class _SubApp:
        app: 'App'
        name: str
        aliases: _t.Optional[_t.List[str]] = None
        is_primary: bool = False

    def __init__(
        self,
        command: "Command",
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
        #:     usage = """
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

        if not description and command is not None:
            description = command.__doc__

        #: Text that is shown before CLI flags help, usually contains
        #: short description of the program or subcommand.
        #:
        #: By default, inferred from command's description.
        #:
        #: See `description <https://docs.python.org/3/library/argparse.html#description>`_.
        self.description: _t.Optional[str] = description

        if not help and description:
            lines = description.split('\n\n', 1)
            help = lines[0].rstrip('.')

        #: Short help message that is shown when listing subcommands.
        #:
        #: See `help <https://docs.python.org/3/library/argparse.html#help>`_.
        self.help: _t.Optional[str] = help

        #: Text that is shown after CLI flags help.
        #:
        #: See `epilog <https://docs.python.org/3/library/argparse.html#epilog>`_.
        self.epilog: _t.Optional[str] = epilog

        #: Allow abbreviating CLI flags if that doesn't create ambiguity.
        #:
        #: Enabled by default.
        #:
        #: See `allow_abbrev <https://docs.python.org/3/library/argparse.html#allow-abbrev>`_.
        self.allow_abbrev: bool = True

        #: Require the user to provide a subcommand for this command.
        #:
        #: If this command doesn't have any subcommands, this option is ignored.
        #:
        #: Enabled by default.
        self.subcommand_required: bool = True

        self._sub_apps: _t.Dict[str, 'App._SubApp'] = {}

        if callable(command):
            self._config_type = _command_from_callable(command)
        else:
            raise TypeError(f'expected a function, got {command}')

        functools.update_wrapper(
            self,  # type: ignore
            command,
            assigned=('__module__', '__name__', '__qualname__', '__doc__'),
            updated=()
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
    ) -> _t.Callable[["Command"], 'App']: ...

    @_t.overload
    def subcommand(
        self,
        cb: "Command",
        /,
        *,
        name: _t.Optional[str] = None,
        aliases: _t.Optional[_t.List[str]] = None,
        prog: _t.Optional[str] = None,
        usage: _t.Optional[str] = None,
        help: _t.Optional[str] = None,
        description: _t.Optional[str] = None,
        epilog: _t.Optional[str] = None,
    ) -> 'App': ...

    def subcommand(
        self,
        cb_or_name: _t.Union[str, "Command", None] = None,
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

        """

        if isinstance(cb_or_name, str):
            cb = None
            name = cb_or_name
        else:
            cb = cb_or_name

        def registrar(cb: "Command", /) -> App:
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
            self._sub_apps[main_name] = App._SubApp(app, main_name, aliases, is_primary=True)
            if aliases:
                alias_app = App._SubApp(app, main_name)
                self._sub_apps.update({alias: alias_app for alias in aliases})

            return app

        if cb is None:
            return registrar
        else:
            return registrar(cb)

    def run(self, args: _t.Optional[_t.List[str]] = None) -> _t.NoReturn:
        """Parse arguments and run the application.

        If no `args` are given, parse :data:`sys.argv`.

        This function does not return.

        """

        logging.basicConfig()

        parser = self._setup_arg_parser()
        try:
            command = self._load_from_namespace(parser.parse_args(args))
            command()
            exit(0)
        except (argparse.ArgumentTypeError, argparse.ArgumentError) as e:
            parser.error(str(e))
        except Exception as e:
            yuio.io.error_with_tb('Error: %s', e)
            exit(1)

    def _load_from_namespace(self, namespace: argparse.Namespace) -> 'App.SubCommand':
        return self.__load_from_namespace(namespace, 'app')

    def __load_from_namespace(self, namespace: argparse.Namespace, ns_prefix: str) -> 'App.SubCommand':
        config = self._config_type._load_from_namespace(namespace, ns_prefix=ns_prefix)
        subcommand = None

        if ns_prefix + '@subcommand' in namespace:
            name = getattr(namespace, ns_prefix + '@subcommand')
            sub_app = self._sub_apps[name]
            subcommand = dataclasses.replace(sub_app.app.__load_from_namespace(
                namespace, f'{ns_prefix}/{sub_app.name}'
            ), name=sub_app.name)

        return App.SubCommand('', subcommand, _config=config)

    def _setup_arg_parser(self) -> argparse.ArgumentParser:
        prog = self.prog
        if not prog:
            prog = os.path.basename(sys.argv[0])

        parser = argparse.ArgumentParser(
            prog=self.prog,
            usage=self.usage,
            description=self.description,
            epilog=self.epilog,
            allow_abbrev=self.allow_abbrev,
            formatter_class=_HelpFormatter,  # type: ignore
        )

        self.__setup_arg_parser(parser, 'app', prog)

        aux = parser.add_argument_group("auxiliary options")
        color = aux.add_mutually_exclusive_group()
        color.add_argument(
            '--force-color',
            help='force-enable colored output',
            action='store_true',  # Note: `yuio.term` inspects `sys.argv` on its own
        )
        color.add_argument(
            '--force-no-color',
            help='force-disable colored output',
            action='store_true',  # Note: `yuio.term` inspects `sys.argv` on its own
        )

        return parser

    def __setup_arg_parser(self, parser: argparse.ArgumentParser, ns_prefix: str, prog: str):
        self._config_type._setup_arg_parser(parser, ns_prefix=ns_prefix)

        if self._sub_apps:
            subparsers = parser.add_subparsers(
                required=self.subcommand_required,
                dest=ns_prefix + '@subcommand',
                metavar='<subcommand>'
            )

            for name, sub_app in self._sub_apps.items():
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

                sub_app.app.__setup_arg_parser(
                    parser, ns_prefix=f'{ns_prefix}/{name}', prog=sub_prog
                )


def _command_from_callable(cb: "Command") -> _t.Type[yuio.config.Config]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    accepts_subcommand = False

    try:
        docs = yuio._find_docs(cb)
    except Exception:
        yuio._logger.exception(
            'Unable to get documentation for %s',
            cb.__qualname__,
        )
        docs = {}

    for name, param in sig.parameters.items():
        if param.kind not in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            raise TypeError(
                'positional-only and variadic arguments are not supported'
            )

        if name.startswith('_'):
            if name == '_subcommand':
                accepts_subcommand = True
                continue
            else:
                raise TypeError(f'unknown special param {name}')

        if param.default is not param.empty:
            field = param.default
        else:
            field = yuio.config.positional()
        if not isinstance(field, yuio.config._FieldSettings):
            field = yuio.config.field(field)
        if field.default is yuio.MISSING:
            field = dataclasses.replace(field, required=True)
        if name in docs:
            field = dataclasses.replace(field, help=docs[name])

        if param.annotation is param.empty:
            raise TypeError(f'param {name} requires type annotation')

        dct[name] = field
        annotations[name] = param.annotation

    dct['_run'] = _command_from_callable_run_impl(
        cb, list(annotations.keys()), accepts_subcommand
    )
    dct['__annotations__'] = annotations
    dct['__module__'] = getattr(cb, '__module__', None)
    dct['__doc__'] = getattr(cb, '__doc__', None)

    return types.new_class(
        cb.__name__,
        (yuio.config.Config,),
        {'_allow_positionals': True},
        exec_body=lambda ns: ns.update(dct)
    )


def _command_from_callable_run_impl(cb: "Command", params: _t.List[str], accepts_subcommand):
    def run(self, subcommand):
        kw = {name: getattr(self, name) for name in params}
        if accepts_subcommand:
            kw['_subcommand'] = subcommand
        return cb(**kw)
    return run


_MAX_ARGS_COLUMN_WIDTH = 24


@dataclass(frozen=True, **yuio._with_slots())
class _HelpHeading:
    """Section heading for help message.

    """

    indent: int
    text: yuio.term.ColorizedString

    def format(self, out: yuio.term.ColorizedString, width: int, args_column_width: int, theme: yuio.term.Theme):
        indent = yuio.term.ColorizedString([theme.get_color("cli/plain_text"), "  " * self.indent])
        for line in self.text.wrap(width, first_line_indent=indent, continuation_indent=indent):
            out += line
            out += "\n"


@dataclass(frozen=True, **yuio._with_slots())
class _HelpText:
    """Help section with help message.

    Help messages are parsed from markdown-like language.

    """

    indent: int
    text: str

    class _Node(abc.ABC):
        """Base AST node for the parsed help text.

        """

        @abc.abstractmethod
        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            raise NotImplementedError()

    @dataclass(**yuio._with_slots())
    class _Heading(_Node):
        """Heading AST node.

        """

        heading: str

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            heading_decoration = theme.colorize(
                theme.msg_decorations.get("group", ""),
                default_color="cli/section/decoration",
            )
            if heading_decoration:
                heading_decoration += " "
            heading = theme.colorize(
                self.heading,
                default_color="cli/section",
                parse_cli_flags_in_backticks=True,
            )
            for line in heading.wrap(
                width,
                first_line_indent=first_line_indent,
                continuation_indent=continuation_indent
            ):
                out += line
                out += "\n"

    @dataclass(**yuio._with_slots())
    class _Container(_Node):
        """Base AST node for containers, i.e. nodes that contain lines of text.

        These lines can be displayed directly like in code blocks,
        wrapped like in paragraphs, or parsed for nested content
        like in list items or quotes.

        """

        lines: _t.List[str] = dataclasses.field(default_factory=list)

    @dataclass(**yuio._with_slots(), kw_only=True)
    class _Paragraph(_Container):
        """Paragraph AST node.

        """

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            text = self.lines[0] + "\n" + textwrap.dedent("\n".join(self.lines[1:]))
            c_text = theme.colorize(
                text,
                default_color="cli/plain_text",
                parse_cli_flags_in_backticks=True,
            )
            for line in c_text.wrap(
                width,
                preserve_newlines=False,
                first_line_indent=first_line_indent,
                continuation_indent=continuation_indent
            ):
                out += line
                out += "\n"

    @dataclass(**yuio._with_slots(), kw_only=True)
    class _ListItem(_Container):
        """AST node for a single bullet list item.

        """

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            _HelpText._format(
                "\n".join(self.lines),
                out,
                width,
                first_line_indent + [theme.get_color("cli/list/decoration"), "•   "],
                continuation_indent + [theme.get_color("cli/list/decoration"), "    "],
                theme
            )

    @dataclass(**yuio._with_slots(), kw_only=True)
    class _NumberedListItem(_Container):
        """AST node for a single numbered list item.

        """

        number: int

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
            *,
            justify: int = 2,
        ):
            number = f"{self.number}."

            _HelpText._format(
                "\n".join(self.lines),
                out,
                width,
                first_line_indent + [theme.get_color("cli/list/decoration"), f"{number:<{justify}}  "],
                continuation_indent + [theme.get_color("cli/list/decoration"), " " * justify + "  "],
                theme
            )

    @dataclass(**yuio._with_slots(), kw_only=True)
    class _Quote(_Container):
        """Quote AST node.

        """

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            _HelpText._format(
                "\n".join(self.lines),
                out,
                width,
                first_line_indent + [theme.get_color("cli/list/decoration"), ">   "],
                continuation_indent + [theme.get_color("cli/list/decoration"), ">   "],
                theme
            )

    @dataclass(**yuio._with_slots(), kw_only=True)
    class _Code(_Container):
        """Code AST node.

        """

        syntax: str

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            code = theme.highlight_code(
                "\n".join(self.lines),
                self.syntax,
                default_color="cli/code_block/text",
            )

            for line in code.wrap(
                width,
                break_on_hyphens=False,
                preserve_spaces=True,
                preserve_newlines=True,
                first_line_indent=first_line_indent + [theme.get_color("cli/code_block/decoration"), " " * 8],
                continuation_indent=continuation_indent + [theme.get_color("cli/code_block/decoration"), " " * 8],
            ):
                out += line
                out += "\n"

    @dataclass(**yuio._with_slots())
    class _List(_Node):
        """AST node that holds bullet list items.

        """

        items: _t.List["_HelpText._ListItem"] = dataclasses.field(default_factory=list)

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            sep = False
            indent = first_line_indent
            for item in self.items:
                if sep:
                    out += continuation_indent
                    out += theme.get_color("cli/plain_text")
                    out += "\n"
                item.format(
                    out,
                    width,
                    indent,
                    continuation_indent,
                    theme,
                )
                sep = True
                indent = continuation_indent

    @dataclass(**yuio._with_slots())
    class _NumberedList(_Node):
        """AST node that holds numbered list items.

        """

        items: _t.List["_HelpText._NumberedListItem"] = dataclasses.field(default_factory=list)

        def format(
            self,
            out: yuio.term.ColorizedString,
            width: int,
            first_line_indent: yuio.term.ColorizedString,
            continuation_indent: yuio.term.ColorizedString,
            theme: yuio.term.Theme,
        ):
            if not self.items:
                return
            justify = max(2, math.ceil(math.log10(max(item.number for item in self.items))))
            sep = False
            indent = first_line_indent
            for item in self.items:
                if sep:
                    out += continuation_indent
                    out += theme.get_color("cli/plain_text")
                    out += "\n"
                item.format(
                    out,
                    width,
                    indent,
                    continuation_indent,
                    theme,
                    justify=justify,
                )
                sep = True
                indent = continuation_indent

    @staticmethod
    def _parse_text(text: str, allow_headings: bool) -> _t.Iterable["_HelpText._Node"]:
        first_line, *rest = text.split('\n', 1)
        text = first_line + ('\n' + textwrap.dedent(rest[0]) if rest else '')
        text = text.strip()

        result: _t.List["_HelpText._Node"] = []

        NONE, BLOCK, CODE, PARAGRAPH = 1, 2, 3, 4
        state = NONE
        continuation_indent = ""

        empty_lines = 1

        for line in text.splitlines():
            if not line:
                empty_lines += 1

            if state == BLOCK:
                if line and not line.startswith(continuation_indent):
                    state = NONE
                    continuation_indent = ""
                    # Go to `NONE` state and parse this line as usual.
                else:
                    assert result and isinstance(result[-1], _HelpText._Container)
                    result[-1].lines.append(line[len(continuation_indent):])
                    continue

            if state == PARAGRAPH:
                if not line or not line.startswith(continuation_indent):
                    state = NONE
                    continuation_indent = ""
                    # Go to `NONE` state and parse this line as usual.
                else:
                    assert result and isinstance(result[-1], _HelpText._Paragraph)
                    result[-1].lines.append(line[len(continuation_indent):])
                    continue

            if state == CODE:
                if line == continuation_indent + "```" or (line and not line.startswith(continuation_indent)):
                    state = NONE
                    continuation_indent = ""
                    continue
                else:
                    assert result and isinstance(result[-1], _HelpText._Code)
                    result[-1].lines.append(line[len(continuation_indent):])
                    continue

            if state == NONE:
                line_indent = len(line) - len(line.lstrip())
                line = line[line_indent:]

                if not line:
                    pass  # do nothing
                elif line_indent == 0 and line.endswith(":") and empty_lines and allow_headings:
                    result.append(_HelpText._Heading(line))
                elif line.startswith("```"):
                    result.append(_HelpText._Code(syntax=line[3:].strip()))
                    state = CODE
                    continuation_indent = " " * line_indent
                elif line.startswith("- ") or line.startswith("* "):
                    result.append(_HelpText._ListItem([line[2:]]))
                    state = BLOCK
                    continuation_indent = " " * line_indent + "  "
                elif match := re.match(r"^(\d+)[.:)] ", line):
                    result.append(_HelpText._NumberedListItem([line[2:]], number=int(match.group(1))))
                    state = BLOCK
                    continuation_indent = " " * line_indent + "  "
                elif line.startswith(">"):
                    result.append(_HelpText._Quote([line[2:]]))
                    state = BLOCK
                    continuation_indent = " " * line_indent + ">"
                else:
                    result.append(_HelpText._Paragraph([line]))
                    state = PARAGRAPH
                    continuation_indent = " " * line_indent

            if line:
                empty_lines = 0

        # Group consecutive list items.
        grouped_result = []
        prev_container: _t.Union[None, _HelpText._List, _HelpText._NumberedList] = None
        for node in result:
            if isinstance(node, _HelpText._ListItem):
                if not isinstance(prev_container, _HelpText._List):
                    prev_container = _HelpText._List([node])
                    grouped_result.append(prev_container)
                else:
                    prev_container.items.append(node)
            elif isinstance(node, _HelpText._NumberedListItem):
                if not isinstance(prev_container, _HelpText._NumberedList):
                    prev_container = _HelpText._NumberedList([node])
                    grouped_result.append(prev_container)
                else:
                    node.number = prev_container.items[-1].number + 1
                    prev_container.items.append(node)
            else:
                grouped_result.append(node)
                prev_container = None

        return grouped_result

    @staticmethod
    def _format(
        text: str,
        out: yuio.term.ColorizedString,
        width: int,
        first_line_indent: yuio.term.ColorizedString,
        continuation_indent: yuio.term.ColorizedString,
        theme: yuio.term.Theme,
        *,
        allow_headings: bool = False,
    ):
        indent = first_line_indent
        section_indent = continuation_indent + [theme.get_color("cli/plain_text"), "  "]

        is_heading = True
        is_section = False
        for node in _HelpText._parse_text(text, allow_headings):
            if not is_heading:
                out += continuation_indent
                out += theme.get_color("cli/plain_text")
                out += "\n"
            if isinstance(node, _HelpText._Heading):
                is_heading = True
                is_section = True
            else:
                is_heading = False

            node.format(
                out,
                width,
                section_indent if (is_section and not is_heading) else indent,
                section_indent if (is_section and not is_heading) else continuation_indent,
                theme,
            )

            indent = continuation_indent

    def format(self,
        out: yuio.term.ColorizedString,
        width: int,
        args_column_width: int,
        theme: yuio.term.Theme
    ):
        self._format(
            self.text,
            out,
            width,
            yuio.term.ColorizedString([theme.get_color("cli/plain_text"), "  " * self.indent]),
            yuio.term.ColorizedString([theme.get_color("cli/plain_text"), "  " * self.indent]),
            theme,
            allow_headings=True,
        )


@dataclass(frozen=True, **yuio._with_slots())
class _HelpArg:
    indent: int
    args: yuio.term.ColorizedString
    help: str

    def format(self, out: yuio.term.ColorizedString, width: int, args_column_width: int, theme: yuio.term.Theme):
        indent = yuio.term.ColorizedString([theme.get_color("cli/plain_text"), "  " * self.indent])
        args = indent + self.args

        if not self.help:
            out += args
            out += "\n"
            return

        continuation_indent = indent + " " * (args_column_width + 2 - indent.width)
        if args.width > args_column_width:
            out += args
            out += "\n"
            first_line_indent = continuation_indent
        else:
            first_line_indent = args + [theme.get_color("cli/plain_text"), " " * (args_column_width + 2 - args.width)]
        _HelpText._format(
            self.help,
            out,
            width,
            first_line_indent,
            continuation_indent,
            theme,
            allow_headings=False,
        )

@dataclass(frozen=True, **yuio._with_slots())
class _HelpUsage:
    prefix: yuio.term.ColorizedString
    usage_override: yuio.term.ColorizedString
    usage: yuio.term.ColorizedString
    optionals: _t.List[yuio.term.ColorizedString]
    positionals: _t.List[yuio.term.ColorizedString]

    def format(self, out: yuio.term.ColorizedString, width: int, args_column_width: int, theme: yuio.term.Theme):
        out += theme.get_color("cli/plain_text")
        needs_space = False

        if self.usage_override:
            for line in self.usage_override.wrap(
                width,
                preserve_spaces=True,
                preserve_newlines=True,
                break_on_hyphens=False,
                first_line_indent=self.prefix,
                continuation_indent=" " * self.prefix.width,
            ):
                out += line
                out += "\n"
            return

        cur_width = 0

        if self.prefix:
            out += self.prefix
            cur_width += self.prefix.width
            needs_space = True

        if self.usage:
            out += self.usage
            cur_width += self.usage.width
            needs_space = True

        for arr in [self.optionals, self.positionals]:
            total_optionals_width = sum(elem.width for elem in arr) + len(arr) - 1
            if (
                cur_width + total_optionals_width + needs_space > width
                and self.prefix.width + total_optionals_width <= width
            ):
                needs_space = False
                out += theme.get_color("cli/plain_text")
                out += "\n" + " " * self.prefix.width
                cur_width = self.prefix.width
            for elem in arr:
                if needs_space and cur_width + 1 + elem.width > width:
                    needs_space = False
                    out += theme.get_color("cli/plain_text")
                    out += "\n" + " " * self.prefix.width
                    cur_width = self.prefix.width
                if needs_space:
                    out += theme.get_color("cli/plain_text")
                    out += " "
                    cur_width += 1
                out += elem
                cur_width += elem.width
                needs_space = True
        out += theme.get_color("cli/plain_text")
        out += "\n"


class _HelpFormatter(object):
    def __init__(self, prog: str):
        self._prog = prog
        self._term = yuio.io.get_term()
        self._theme = yuio.io.get_theme()
        self._indent = 0
        self._sections: _t.List[_t.Union[_HelpHeading, _HelpText, _HelpArg, _HelpUsage]] = []

    def start_section(self, heading: _t.Optional[str]):
        if heading:
            if not heading.endswith(":"):
                heading += ":"
            c_heading = self._theme.colorize(
                heading,
                default_color="cli/section",
                parse_cli_flags_in_backticks=True,
            )
            self._sections.append(_HelpHeading(self._indent, c_heading))
        self._indent += 1

    def end_section(self):
        self._indent -= 1

    def add_text(self, text):
        if text is not argparse.SUPPRESS and text:
            self._sections.append(_HelpText(self._indent, text))

    def add_usage(self, usage, actions: _t.Iterable[argparse.Action], groups, prefix=None):
        if usage is argparse.SUPPRESS:
            return

        if prefix is not None:
            c_prefix = self._theme.colorize(
                prefix,
                default_color="cli/section",
                parse_cli_flags_in_backticks=True,
            )
        else:
            c_prefix = yuio.term.ColorizedString([self._theme.get_color("cli/section"), "usage: "])

        c_optionals: _t.List[yuio.term.ColorizedString] = []
        c_positionals: _t.List[yuio.term.ColorizedString] = []

        c_usage = yuio.term.ColorizedString()
        c_usage_override = yuio.term.ColorizedString()
        if usage is not None:
            first_line, *rest = usage.split('\n', 1)
            usage = first_line + ('\n' + textwrap.dedent(rest[0]) if rest else '')
            usage = usage.strip()
            c_usage_override = self._theme.highlight_code(
                usage,
                "sh-usage",
                default_color="cli/plain_text",
            ) % dict(prog=self._prog)
        else:
            c_usage = yuio.term.ColorizedString([
                self._theme.get_color("cli/prog"),
                str(self._prog)
            ])

            optionals: _t.List[_t.Union[argparse.Action, argparse._MutuallyExclusiveGroup]] = []
            positionals: _t.List[_t.Union[argparse.Action, argparse._MutuallyExclusiveGroup]] = []
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
                                c_elem += self._theme.get_color("cli/plain_text")
                                c_elem += "(" if elem.required else "["
                            self._format_action_short(action, c_elem, in_group=True)
                            if i + 1 < len(elem._group_actions):
                                c_elem += self._theme.get_color("cli/plain_text")
                                c_elem += " |"
                            else:
                                c_elem += self._theme.get_color("cli/plain_text")
                                c_elem += ")" if elem.required else "]"
                            res.append(c_elem)

        self._sections.append(_HelpUsage(
            c_prefix,
            c_usage_override,
            c_usage,
            c_optionals,
            c_positionals,
        ))

    def add_argument(self, action: argparse.Action):
        if action.help is not argparse.SUPPRESS:
            c_usage = yuio.term.ColorizedString()
            sep = False
            if not action.option_strings:
                self._format_action_metavar(action, 0, c_usage)
            for option_string in action.option_strings:
                if sep:
                    c_usage += self._theme.get_color("cli/plain_text")
                    c_usage += ", "
                c_usage += self._theme.get_color("cli/flag")
                c_usage += option_string
                if action.nargs != 0:
                    c_usage += self._theme.get_color("cli/plain_text")
                    c_usage += " "
                self._format_action_metavar_expl(action, c_usage)
                sep = True

            self._sections.append(_HelpArg(
                self._indent,
                c_usage,
                action.help or "",
            ))

            try:
                get_subactions = action._get_subactions  # type: ignore
            except AttributeError:
                pass
            else:
                self._indent += 1
                self.add_arguments(get_subactions())
                self._indent -= 1

    def add_arguments(self, actions):
        for action in actions:
            self.add_argument(action)

    def format_help(self) -> str:
        width = max(min(shutil.get_terminal_size().columns, 90), 30)
        args_column_width = max(
            [
                item.args.width + item.indent * 2
                for item in self._sections
                if isinstance(item, _HelpArg)
                if item.args.width + item.indent * 2 <= _MAX_ARGS_COLUMN_WIDTH
            ] or [0]
        )

        out = yuio.term.ColorizedString()
        for i, section in enumerate(self._sections):
            if (
                isinstance(section, _HelpHeading)
                and (
                    i + 1 == len(self._sections)
                    or isinstance(self._sections[i + 1], _HelpHeading)
                )
            ):
                # Skip empty sections.
                continue

            if i > 0 and (
                # Always add empty line before heading.
                isinstance(section, _HelpHeading)
                # Add empty line before this section if it's not following
                # a heading, and if it's not an arg following another arg.
                or (
                    not isinstance(self._sections[i - 1], _HelpHeading)
                    and not (
                        isinstance(section, _HelpArg)
                        and isinstance(self._sections[i - 1], _HelpArg)
                    )
                )
            ):
                out += self._theme.get_color("cli/plain_text")
                out += "\n"

            section.format(out, width, args_column_width, self._theme)

        out += yuio.term.Color.NONE

        return out.merge(self._term)

    def _format_action_short(self, action: argparse.Action, out: yuio.term.ColorizedString, in_group: bool = False):
        if not in_group and not action.required:
            out += self._theme.get_color("cli/plain_text")
            out += "["

        if action.option_strings:
            out += self._theme.get_color("cli/flag")
            out += action.format_usage()
            if action.nargs != 0:
                out += self._theme.get_color("cli/plain_text")
                out += " "

        self._format_action_metavar_expl(action, out)

        if not in_group and not action.required:
            out += self._theme.get_color("cli/plain_text")
            out += "]"

    def _format_action_metavar_expl(self, action: argparse.Action, out: yuio.term.ColorizedString):
        nargs = action.nargs if action.nargs is not None else 1

        if nargs == argparse.OPTIONAL:
            out += self._theme.get_color("cli/plain_text")
            out += "["

            self._format_action_metavar(action, 0, out)

            out += self._theme.get_color("cli/plain_text")
            out += "]"
        elif nargs == argparse.ZERO_OR_MORE:
            out += self._theme.get_color("cli/plain_text")
            out += "["

            self._format_action_metavar(action, 0, out)

            out += self._theme.get_color("cli/plain_text")
            out += " ...]"
        elif nargs == argparse.ONE_OR_MORE:
            self._format_action_metavar(action, 0, out)

            out += self._theme.get_color("cli/plain_text")
            out += " ["

            self._format_action_metavar(action, 1, out)

            out += self._theme.get_color("cli/plain_text")
            out += " ...]"
        elif nargs == argparse.REMAINDER:
            out += self._theme.get_color("cli/plain_text")
            out += "..."
        elif nargs == argparse.PARSER:
            self._format_action_metavar(action, 1, out)

            out += self._theme.get_color("cli/plain_text")
            out += " ..."
        elif isinstance(nargs, int):
            sep = False
            for i in range(nargs):
                if sep:
                    out += self._theme.get_color("cli/plain_text")
                    out += " "
                self._format_action_metavar(action, i, out)
                sep = True

    def _format_action_metavar(self, action: argparse.Action, n: int, out: yuio.term.ColorizedString):
        metavar_t = action.metavar
        if not metavar_t and action.option_strings:
            metavar_t = f"<{action.option_strings[0]}>"
        if not metavar_t:
            metavar_t = "<value>"
        if isinstance(metavar_t, tuple):
            metavar = metavar_t[n] if n < len(metavar_t) else metavar_t[-1]
        else:
            metavar = metavar_t

        cli_color = self._theme.get_color("cli/plain_text")
        metavar_color = self._theme.get_color("cli/metavar")
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
