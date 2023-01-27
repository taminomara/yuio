# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3
"""
This module expands on :mod:`yuio.config` to build CLI apps.

"""
import argparse
import dataclasses
import inspect
import logging
import re
import textwrap
import types
import typing as _t
from dataclasses import dataclass

import yuio.config
import yuio.io
import yuio.parse
from yuio._utils import MISSING


Command = _t.Callable[..., None]


@dataclass(frozen=True)
class _SubApp:
    app: 'App'
    name: str
    aliases: _t.Optional[_t.List[str]] = None
    is_primary: bool = False


@_t.overload
def app(
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
) -> _t.Callable[[Command], 'App']:
    pass


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
) -> 'App':
    pass


def app(
    command: _t.Optional[Command] = None,
    /,
    *,
    prog: _t.Optional[str] = None,
    usage: _t.Optional[str] = None,
    help: _t.Optional[str] = None,
    description: _t.Optional[str] = None,
    epilog: _t.Optional[str] = None,
):
    def registrar(command: Command) -> App:
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
        subcommand: _t.Optional['App.SubCommand']

        # Internal, do not use
        _data: _t.Any

        def __call__(self):
            """Execute this subcommand.

            """

            if self._data is not None:
                should_invoke_subcommand = self._data._run(self.subcommand)
                if should_invoke_subcommand is None:
                    should_invoke_subcommand = True
            else:
                should_invoke_subcommand = True

            if should_invoke_subcommand and self.subcommand is not None:
                self.subcommand()

    def __init__(
        self,
        command: _t.Optional[Command] = None,
        prog: _t.Optional[str] = None,
        usage: _t.Optional[str] = None,
        help: _t.Optional[str] = None,
        description: _t.Optional[str] = None,
        epilog: _t.Optional[str] = None,
    ):
        self.prog: _t.Optional[str] = prog
        self.usage: _t.Optional[str] = usage

        if not description and command is not None:
            description = command.__doc__

        if description:
            description = textwrap.dedent(description.strip())

        self.description: _t.Optional[str] = description

        if not help and description:
            lines = description.split('\n\n', 1)
            help = lines[0].replace('\n', ' ').rstrip('.')

        self.help: _t.Optional[str] = help

        if epilog:
            epilog = textwrap.dedent(epilog.strip())

        self.epilog: _t.Optional[str] = epilog

        self.prefix_chars: str = '-'
        self.allow_abbrev: bool = True
        self.subcommand_required: bool = True

        self._sub_apps: _t.Dict[str, _SubApp] = {}

        if command is None:
            self._config_type: _t.Type[yuio.config.Config] = yuio.config.Config
        elif callable(command):
            self._config_type = _command_from_callable(command)
        else:
            raise TypeError(
                f'expected a function, got {command}')

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
    ) -> _t.Callable[[Command], 'App']:
        pass

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
    ) -> 'App':
        pass

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
        if isinstance(cb_or_name, str):
            cb = None
            name = cb_or_name
        else:
            cb = cb_or_name

        def registrar(cb: Command) -> App:
            app = App(
                prog=prog,
                usage=usage,
                help=help,
                description=description,
                epilog=epilog,
                command=cb
            )

            app.prefix_chars = self.prefix_chars
            app.allow_abbrev = self.allow_abbrev

            main_name = name or yuio._utils.to_dash_case(cb.__name__)
            self._sub_apps[main_name] = _SubApp(app, main_name, aliases, is_primary=True)
            alias_app = _SubApp(app, main_name)
            if aliases:
                self._sub_apps.update({alias: alias_app for alias in aliases})

            return app

        if cb is None:
            return registrar
        else:
            return registrar(cb)

    def run(self, args: _t.Optional[_t.List[str]] = None):
        parser = self._setup_arg_parser()
        try:
            command = self._load_from_namespace(parser.parse_args(args))
            command()
        except argparse.ArgumentTypeError as e:
            parser.error(str(e))
        except Exception as e:
            yuio.io.exception('<c:failure>Error: %s</c>', e)
            exit(1)

    def _load_from_namespace(self, namespace: argparse.Namespace) -> 'App.SubCommand':
        return self.__load_from_namespace(namespace, 'app')

    def __load_from_namespace(self, namespace: argparse.Namespace, ns_prefix: str) -> 'App.SubCommand':
        data = self._config_type.load_from_namespace(namespace, ns_prefix=ns_prefix)
        subcommand = None

        if ns_prefix + '@subcommand' in namespace:
            name = getattr(namespace, ns_prefix + '@subcommand')
            sub_app = self._sub_apps[name]
            subcommand = dataclasses.replace(sub_app.app.__load_from_namespace(
                namespace, f'{ns_prefix}/{sub_app.name}'
            ), name=sub_app.name)

        return App.SubCommand('', subcommand, _data=data)

    def _setup_arg_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog=self.prog,
            usage=self.usage,
            description=self.description,
            epilog=self.epilog,
            prefix_chars=self.prefix_chars,
            allow_abbrev=self.allow_abbrev,
            formatter_class=_HelpFormatter,
        )

        self.__setup_arg_parser(parser, 'app')

        return parser

    def __setup_arg_parser(self, parser: argparse.ArgumentParser, ns_prefix: str):
        self._config_type.setup_arg_parser(parser, ns_prefix=ns_prefix)

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
                    help=sub_app.app.help,
                    description=sub_app.app.description,
                    epilog=sub_app.app.epilog,
                    prefix_chars=self.prefix_chars,
                    allow_abbrev=self.allow_abbrev,
                    formatter_class=_HelpFormatter,
                )

                sub_app.app.__setup_arg_parser(
                    parser, ns_prefix=f'{ns_prefix}/{name}'
                )


def _command_from_callable(cb: Command) -> _t.Type[yuio.config.Config]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    accepts_subcommand = False

    try:
        docs = yuio._utils.find_docs(cb)
    except Exception:
        logging.getLogger('yuio.internal').exception(
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
            field = yuio.config.field()
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
        exec_body=lambda ns: ns.update(dct)
    )


def _command_from_callable_run_impl(cb: Command, params: _t.List[str], accepts_subcommand):
    def run(self, subcommand):
        kw = {name: getattr(self, name) for name in params}
        if accepts_subcommand:
            kw['_subcommand'] = subcommand
        return cb(**kw)
    return run


class _HelpFormatter(argparse.HelpFormatter):
    def format_help(self):
        help = super().format_help().strip('\n')
        help = re.sub(r'^usage:', '<c:cli-section>usage:</c>', help)
        help = re.sub(r':@@section</c>:$', r':</c>\n', help, flags=re.MULTILINE)
        help = re.sub(r'(?<=\W)(-[a-zA-Z0-9]|--[a-zA-Z0-9-_]+)\b', r'<c:cli-flag>\g<0></c>', help, flags=re.MULTILINE)
        help = re.sub(r'\[default: (.*?)]$', r'<c:cli-default>[default: <c:code>\1</c>]</c>', help, flags=re.MULTILINE)
        help = help.replace('\n  <subcommand>\n', '\n')
        return yuio.io._HANDLER_IMPL._colorize(help, yuio.io.Color()) + '\n'

    def start_section(self, heading: _t.Optional[str]):
        heading = f'<c:cli-section>{heading}:@@section</c>'
        super().start_section(heading)

    def _iter_indented_subactions(self, action):
        try:
            return action._get_subactions()
        except AttributeError:
            return []
