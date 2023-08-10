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


import argparse
import dataclasses
import inspect
import logging
import os
import re
import string
import sys
import textwrap
import types
import typing as _t
from dataclasses import dataclass
import functools

import yuio._utils
import yuio.config
import yuio.io
import yuio.parse
import yuio.term
from yuio.config import DISABLED, MISSING, POSITIONAL, Disabled, Missing, Positional
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
        """

        :param command:
        :param prog:
        :param usage:
        :param help:
        :param description:
        :param epilog:

        """

        #: Program or subcommand display name.
        #:
        #: By default, inferred from :data:`sys.argv` and subcommand names.
        #:
        #: See `prog <https://docs.python.org/3/library/argparse.html#prog>`_.
        self.prog: _t.Optional[str] = prog

        #: Program or subcommand usage description.
        #:
        #: By default, generated from CLI flags by argparse.
        #:
        #: See `usage <https://docs.python.org/3/library/argparse.html#usage>`_.
        self.usage: _t.Optional[str] = usage

        if not description and command is not None:
            description = command.__doc__

        #: Text that is shown before CLI flags help.
        #:
        #: By default, inferred from command's documentation.
        #:
        #: See `description <https://docs.python.org/3/library/argparse.html#description>`_.
        #:
        #: Error for github to display: :ref:`foobar`.
        self.description: _t.Optional[str] = description

        if not help and description:
            lines = description.split('\n\n', 1)
            help = lines[0].replace('\n', ' ').rstrip('.')

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

            main_name = name or yuio._utils.to_dash_case(cb.__name__)
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

        If arguments are not given, parse :data:`sys.argv`.

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
            formatter_class=_HelpFormatterV2,
        )

        self.__setup_arg_parser(parser, 'app', prog)

        return parser

    def __setup_arg_parser(self, parser: argparse.ArgumentParser, ns_prefix: str, prog: str):
        self._config_type._setup_arg_parser(parser, ns_prefix=ns_prefix)

        if self._sub_apps:
            subparsers = parser.add_subparsers(
                title='subcommands',
                required=self.subcommand_required,
                dest=ns_prefix + '@subcommand',
                metavar='<subcommand>'
            )

            for name, sub_app in self._sub_apps.items():
                if not sub_app.is_primary:
                    continue

                parser = subparsers.add_parser(
                    name,
                    aliases=sub_app.aliases or [],
                    prog=prog,
                    help=sub_app.app.help,
                    description=sub_app.app.description,
                    epilog=sub_app.app.epilog,
                    allow_abbrev=self.allow_abbrev,
                    formatter_class=_HelpFormatterV2,
                )

                sub_app.app.__setup_arg_parser(
                    parser, ns_prefix=f'{ns_prefix}/{name}', prog=f"{prog} {name}"
                )


def _command_from_callable(cb: "Command") -> _t.Type[yuio.config.Config]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    accepts_subcommand = False

    try:
        docs = yuio._utils.find_docs(cb)
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
        if field.default is MISSING:
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


# class _HelpFormatter(argparse.HelpFormatter):
#     def format_help(self):
#         help = super().format_help().strip('\n')
#         help = re.sub(r'^usage:', '<c:cli/section>usage:</c>', help)
#         help = re.sub(r'\n\n(\S.*?:)\n(  |\n|\Z)', r'\n\n<c:cli/section>\1</c>\n\2', help, flags=re.MULTILINE)
#         help = re.sub(r'(?<=\W)(-[a-zA-Z0-9]|--[a-zA-Z0-9-_]+)\b', r'<c:cli/flag>\1</c>', help, flags=re.MULTILINE)
#         help = re.sub(r'\[(default:\s*)(.*?)]$', r'<c:cli/default>[\1<c:cli/default/code>\2</c>]</c>', help, flags=re.MULTILINE)
#         help = re.sub(r'(`+)(.*?)\1', r'<c:code>\2</c>', help, flags=re.MULTILINE)
#         help = help.replace('\n  <subcommand>\n', '\n')

#         theme = yuio.io.get_theme()
#         term = yuio.io.get_term()
#         return theme.colorize(help + "\n", default_color="cli").merge(term)

#     def _iter_indented_subactions(self, action):
#         try:
#             return getattr(action, '_get_subactions')()
#         except AttributeError:
#             return []

#     def _expand_help(self, action):
#         return self._get_help_string(action)

#     def _fill_text(self, text, width, indent):
#         text = text.replace('\t', '  ')
#         first_line, *rest = text.split('\n', 1)
#         text = first_line + ('\n' + textwrap.dedent(rest[0]) if rest else '')
#         text = text.strip()

#         filled_lines = []

#         for paragraph in re.split(r'\n\s*\n', text, re.MULTILINE):
#             if not paragraph:
#                 continue

#             lines = paragraph.split('\n')

#             if filled_lines:
#                 filled_lines.append('')

#             if (
#                 re.match(r'^[^\v\s][^\v]*:\v*$', lines[0])
#                 and (len(lines) == 1 or lines[1].startswith('  '))
#             ):
#                 # First line is a section's heading
#                 filled_lines.append(lines[0])
#                 lines.pop(0)

#             common_indent = min(
#                 len(line) - len(line.lstrip()) for line in lines
#             )

#             if common_indent >= 4:
#                 filled_lines.extend(line.rstrip('\v') for line in lines)
#             else:
#                 lines_to_fill = ['']
#                 for line in lines:
#                     if lines_to_fill[-1]:
#                         lines_to_fill[-1] += ' '
#                     if line.endswith('\v'):
#                         lines_to_fill[-1] += line[common_indent:-1]
#                         lines_to_fill.append('')
#                     else:
#                         lines_to_fill[-1] += line[common_indent:]
#                 filled_lines.extend(
#                     textwrap.fill(
#                         line,
#                         width=width,
#                         initial_indent=indent + ' ' * common_indent,
#                         subsequent_indent=indent + ' ' * common_indent,
#                     )
#                     for line in lines_to_fill if line
#                 )

#         return '\n'.join(filled_lines)


_MAX_ARGS_COLUMN_WIDTH = 25


class _HelpFormatterV2(object):
    @dataclass(frozen=True, slots=True)
    class _Text:
        args: _t.Optional[yuio.term.ColorizedString]
        text: _t.Optional[yuio.term.ColorizedString]

    @dataclass(frozen=True, slots=True)
    class _Section:
        indent: int
        heading: _t.Optional[yuio.term.ColorizedString] = None
        items: _t.List["_HelpFormatterV2._Text"] = dataclasses.field(default_factory=list)

        def format(self, out: yuio.term.ColorizedString, term_width: int):
            if self.heading:
                out += "  " * (self.indent - 1)
                out += self.heading
                out += "\n"

            for item in self.items:
                indent = self.indent
                if item.args:
                    out += "  " * indent
                    out += item.args
                    out += "\n"
                    indent += 1
                if item.text:
                    for line in item.text.wrap(term_width - 2 * indent):
                        out += "  " * indent
                        out += line
                        out += "\n"

            # args_column_width = max(
            #     min(item.args_column_width, _MAX_ARGS_COLUMN_WIDTH)
            #     for item in self.items
            # )


    def __init__(self, prog: str):
        self._prog = prog
        self._term = yuio.io.get_term()
        self._theme = yuio.io.get_theme()
        self._indent = 0
        self._sections = [_HelpFormatterV2._Section(0)]

    def start_section(self, heading: _t.Optional[str]):
        c_heading = self._theme.colorize(heading, default_color="cli/section") if heading else None
        self._indent += 1
        self._sections.append(_HelpFormatterV2._Section(self._indent, c_heading))

    def end_section(self):
        self._indent -= 1
        self._sections.append(_HelpFormatterV2._Section(self._indent, None))

    def add_text(self, text):
        if text is not argparse.SUPPRESS and text is not None:
            pass

    def add_usage(self, usage, actions, groups, prefix=None):
        if usage is argparse.SUPPRESS:
            return

        if prefix is None:
            prefix = 'usage: '
        c_prefix = self._theme.colorize(prefix, default_color="cli/section")

        if usage is not None:
            c_usage = self._theme.colorize(usage) % dict(prog=self._prog)
        else:
            c_usage = self._theme.colorize("%(prog)s") % dict(prog=self._prog)

            optionals = []
            positionals = []
            for action in actions:
                if action.option_strings:
                    optionals.append(action)
                else:
                    positionals.append(action)
            actions = optionals + positionals
            inserts = [' '] * len(actions) + ['']
            action_is_in_group = [False] * len(actions)
            group: argparse._MutuallyExclusiveGroup
            for group in groups:
                try:
                    start = actions.index(group._group_actions[0])
                except (ValueError, IndexError):
                    continue
                else:
                    end = start + len(group._group_actions)
                    if actions[start:end] == group._group_actions:
                        inserts[start] += '(' if group.required else '['
                        inserts[start + 1:end] = [' | '] * (end - start - 1)
                        inserts[end] = (')' if group.required else ']') + inserts[end]
                        action_is_in_group[start:end] = [True] * len(group._group_actions)

            for insert, action, in_group in zip(inserts, actions, action_is_in_group):
                c_usage += self._theme.get_color("cli")
                c_usage += insert
                self._format_action_short(action, c_usage, in_group=in_group)
            if inserts[-1]:
                c_usage += self._theme.get_color("cli")
                c_usage += inserts[-1]

        self._sections[-1].items.append(_HelpFormatterV2._Text(None, c_prefix + c_usage))

    def add_argument(self, action: argparse.Action):
        if action.help is not argparse.SUPPRESS:
            c_usage = yuio.term.ColorizedString()
            sep = False
            for option_string in action.option_strings:
                if sep:
                    c_usage += self._theme.get_color("cli")
                    c_usage += ", "
                c_usage += self._theme.get_color("cli/flag")
                c_usage += option_string
                if action.nargs != 0:
                    c_usage += self._theme.get_color("cli")
                    c_usage += " "
                self._format_action_metavar_expl(action, c_usage)
                sep = True

            self._sections[-1].items.append(
                _HelpFormatterV2._Text(
                    c_usage,
                    self._theme.colorize(action.help) if action.help else None)
            )

            try:
                get_subactions = action._get_subactions
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
        out = yuio.term.ColorizedString()
        need_sep = False
        for section in self._sections:
            if not section.items:
                continue
            if section.heading and need_sep:
                out += "\n"
            section.format(out, 100)
            need_sep = True
        out += yuio.term.Color.NONE
        return out.merge(self._term)

    def _format_action_short(self, action: argparse.Action, out: yuio.term.ColorizedString, in_group: bool = False):
        out += self._theme.get_color("cli")
        if not in_group and not action.required:
            out += "["

        if action.option_strings:
            out += self._theme.get_color("cli/flag")
            out += action.format_usage()
            if action.nargs != 0:
                out += self._theme.get_color("cli")
                out += " "

        self._format_action_metavar_expl(action, out)

        if not in_group and not action.required:
            out += self._theme.get_color("cli")
            out += "]"

    def _format_action_metavar_expl(self, action: argparse.Action, out: yuio.term.ColorizedString):
        nargs = action.nargs if action.nargs is not None else 1

        if nargs == argparse.OPTIONAL:
            out += "["
            self._format_action_metavar(action, 0, out)
            out += self._theme.get_color("cli")
            out += "]"
        elif nargs == argparse.ZERO_OR_MORE:
            out += "["
            self._format_action_metavar(action, 0, out)
            out += self._theme.get_color("cli")
            out += " ...]"
        elif nargs == argparse.ONE_OR_MORE:
            self._format_action_metavar(action, 0, out)
            out += self._theme.get_color("cli")
            out += " ["
            self._format_action_metavar(action, 1, out)
            out += self._theme.get_color("cli")
            out += " ...]"
        elif nargs == argparse.REMAINDER:
            out += "..."
        elif nargs == argparse.PARSER:
            self._format_action_metavar(action, 1, out)
            out += self._theme.get_color("cli")
            out += " ..."
        elif isinstance(nargs, int):
            sep = False
            for i in range(nargs):
                if sep:
                    out += self._theme.get_color("cli")
                    out += " "
                self._format_action_metavar(action, i, out)
                sep = True

    def _format_action_metavar(self, action: argparse.Action, n: int, out: yuio.term.ColorizedString):
        metavar_t = action.metavar or f"<{action.option_strings[0]}>"
        if isinstance(metavar_t, tuple):
            metavar = metavar_t[n] if n < len(metavar_t) else metavar_t[-1]
        else:
            metavar = metavar_t

        cli_color = self._theme.get_color("cli")
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
        pass  # a workaround for argparse's shitty code
