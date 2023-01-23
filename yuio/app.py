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
import re
import textwrap
import types
import typing as _t
from dataclasses import dataclass

import yuio.config
import yuio.io
import yuio.parse
from yuio._utils import MISSING


@dataclass
class _SubApp:
    app: 'App'
    name: str
    aliases: _t.Optional[_t.List[str]] = None
    is_primary: bool = False


class App:
    def __init__(
        self,
        command: _t.Optional[_t.Union[_t.Callable[..., None], _t.Type['Command']]] = None,
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

        self.command: _t.Type[Command]
        if command is None:
            self.command = Command
        elif isinstance(command, type) and issubclass(command, Command):
            self.command = command
        elif callable(command):
            self.command = _command_from_callable(command)
        else:
            raise TypeError(
                f'expected yuio.app.Command or function, got {command}')

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
    ) -> _t.Callable[[_t.Union[_t.Callable[..., None], _t.Type['Command']]], 'App']:
        pass

    @_t.overload
    def subcommand(
        self,
        cb: _t.Union[_t.Callable[..., None], _t.Type['Command']],
        /,
    ) -> 'App':
        pass

    def subcommand(
        self,
        cb_or_name: _t.Union[str, _t.Callable[..., None], _t.Type['Command'], None] = None,
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

        def registrar(cb):
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

    def _load_from_namespace(self, namespace: argparse.Namespace) -> 'Command':
        return self.__load_from_namespace(namespace, 'app')

    def __load_from_namespace(self, namespace: argparse.Namespace, ns_prefix: str) -> 'Command':
        command = self.command.load_from_namespace(namespace, ns_prefix=ns_prefix)

        if ns_prefix + '@subcommand' in namespace:
            name = getattr(namespace, ns_prefix + '@subcommand')
            sub_app = self._sub_apps[name]
            command._subcommand = sub_app.app.__load_from_namespace(
                namespace, f'{ns_prefix}/{sub_app.name}'
            )

        return command

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
        self.command.setup_arg_parser(parser, ns_prefix=ns_prefix)

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


class Command(yuio.config.Config):
    _Self = _t.TypeVar('_Self', bound='Command')

    _subcommand: _t.Optional['Command'] = None

    def run(self):
        pass

    def __call__(self):
        self.run()
        if self._subcommand is not None:
            self._subcommand()


def _command_from_callable(cb: _t.Callable[..., None]) -> _t.Type[Command]:
    sig = inspect.signature(cb)

    dct = {}
    annotations = {}

    for name, param in sig.parameters.items():
        if param.kind not in (param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY):
            raise TypeError(
                'positional-only and variadic arguments are not supported'
            )

        if param.default is not param.empty:
            field = param.default
        else:
            field = yuio.config.field()
        if not isinstance(field, yuio.config._FieldSettings):
            field = yuio.config.field(field)
        if field.default is MISSING:
            field = dataclasses.replace(field, required=True)

        dct[name] = field
        annotations[name] = param.annotation

    dct['run'] = _command_from_callable_run_impl(cb, list(annotations.keys()))
    dct['__annotations__'] = annotations

    return types.new_class(
        f'FnCommand__{cb.__name__}',
        (Command,),
        exec_body=lambda ns: ns.update(dct)
    )


def _command_from_callable_run_impl(cb: _t.Callable[..., None], params: _t.List[str]):
    def run(self):
        cb(**{name: getattr(self, name) for name in params})
    return run


class _HelpFormatter(argparse.HelpFormatter):
    def format_help(self):
        help = super().format_help().strip('\n')
        help = re.sub(r'^usage:', '<c:cli-section>usage:</c>', help)
        help = re.sub(r':</c>:\n', r':</c>\n', help, flags=re.MULTILINE)
        help = re.sub(r'(?<=\W)(-[a-zA-Z0-9]|--[a-zA-Z0-9-_]+)\b', r'<c:cli-flag>\g<0></c>', help, flags=re.MULTILINE)
        help = re.sub(r'\[default: .*?]\n', r'<c:cli-default>\g<0></c>', help, flags=re.MULTILINE)
        help = help.replace('\n  <subcommand>\n', '\n')
        return yuio.io._HANDLER_IMPL._colorize(help, yuio.io.Color()) + '\n'

    def start_section(self, heading: _t.Optional[str]):
        heading = f'<c:cli-section>{heading}:</c>'
        super().start_section(heading)

    def _iter_indented_subactions(self, action):
        try:
            return action._get_subactions()
        except AttributeError:
            return []
