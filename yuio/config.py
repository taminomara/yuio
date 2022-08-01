# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides a base class for configs that can be loaded from
files, environment variables or command line arguments.


Creating and loading configs
----------------------------

Derive your config from the :class:`Config` base class. Inside of its body,
define config fields using type annotations, just like dataclasses::

    class AppConfig(Config):
        #: trained model to execute
        model: pathlib.Path

        #: input data for the model
        data: pathlib.Path

        #: enable or disable gpu (default is enable)
        use_gpu: bool = True

*Field names* are used to parse CLI arguments,
configs and environment variables; *type hints* are used to derive
:mod:`parsers <yuio.parse>`; *field comments* used as help messages
for CLI arguments (only ``#:``-style comments are supported).

:class:`Config` defines `__init__` that takes keyword arguments
for fields. It also defines some constructors that load config from environment
variables, files, and so on.

Upon creation, all fields that aren't explicitly initialized and don't have
defaults are considered missing. Accessing them
will raise :class:`AttributeError`.

Here's an example of loading our config from a file, command line arguments
and environment variables::

    # Load config from a file.
    # If file doesn't exist, return an empty config.
    config = config.load_from_json_file(
        '~/.my_app_cfg.json',
        ignore_missing_file=True
    )

    # Update config with values from env.
    config.update(AppConfig.load_from_env())

    # Update config with values from command line arguments.
    config.update(AppConfig.load_from_args())

You can nest configs one into another. Nested configs are loaded recursively.

.. autoclass:: Config
   :members:


Advanced field configuration
----------------------------

By default, :class:`Config` infers names for env variables and flags,
appropriate parsers, and other things from field's name and type hint.

If you need to override them, theres the :func:`field` function:

.. autofunction:: field

.. autofunction:: disabled

"""

import argparse
import os
import pathlib
import re
import logging
import enum
import typing as _t
from dataclasses import dataclass

import yuio.parse


T = _t.TypeVar('T')


class _Placeholders(enum.Enum):
    DISABLED = '<disabled>'
    MISSING = '<missing>'

    def __repr__(self):
        return self.value


#: Type of a :func:`disabled` placeholder.
Disabled = _t.Literal[_Placeholders.DISABLED]


def disabled() -> Disabled:
    """Placeholder indicating that some field's functionality is disabled.

    """

    return _Placeholders.DISABLED


@dataclass(frozen=True)
class _FieldSettings:
    default: _t.Any = _Placeholders.MISSING
    parser: _t.Optional[yuio.parse.Parser] = None
    help: _t.Optional[str] = None
    env: _t.Optional[_t.Union[str, Disabled]] = None
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None
    required: bool = False

    def _update_defaults(
        self,
        qualname: str,
        name: str,
        ty: _t.Any,
        parsed_help: _t.Optional[str],
    ) -> '_Field':
        is_subconfig = isinstance(ty, type) and issubclass(ty, Config)

        help: str
        if self.help is not None:
            help = self.help
        elif parsed_help is not None:
            help = parsed_help
        else:
            help = ''

        env: _t.Union[str, Disabled]
        if self.env is not None:
            env = self.env
        else:
            env = name.upper()
        if env == '' and not is_subconfig:
            raise TypeError(
                f'{qualname} got an empty env variable name')

        flags: _t.Union[_t.List[str], Disabled]
        if self.flags is _Placeholders.DISABLED:
            flags = _Placeholders.DISABLED
        elif self.flags is None:
            flags = ['--' + name.replace('_', '-')]
        elif isinstance(self.flags, str):
            flags = [self.flags]
        else:
            if not self.flags:
                raise TypeError(
                    f'{qualname} should have at least one flag')
            flags = self.flags
        if flags is not _Placeholders.DISABLED:
            for flag in flags:
                if flag and not flag.startswith('-'):
                    raise TypeError(
                        f'{qualname}: positional arguments '
                        f'are not supported')
                if not flag and not is_subconfig:
                    raise TypeError(
                        f'{qualname} got an empty flag')

        default = self.default

        parser = self.parser

        required = self.required

        if is_subconfig:
            if default is not _Placeholders.MISSING:
                raise TypeError(
                    f'{qualname} cannot have defaults')

            if parser is not None:
                raise TypeError(
                    f'{qualname} cannot have parsers')

            if flags is not _Placeholders.DISABLED:
                if len(flags) > 1:
                    raise TypeError(
                        f'{qualname} cannot have multiple flags')

                if flags[0] and not flags[0].startswith('--'):
                    raise TypeError(
                        f'{qualname} cannot have a short flag ')

            if required:
                raise TypeError(
                    f'{qualname} cannot be required')
        elif parser is None:
            try:
                parser = yuio.parse.from_type_hint(ty)
            except TypeError:
                raise TypeError(
                    f'can\'t derive parser for {qualname}')

        return _Field(
            default,
            parser,
            help,
            env,
            flags,
            is_subconfig,
            ty,
            required
        )


@dataclass(frozen=True)
class _Field:
    default: _t.Any
    parser: _t.Optional[yuio.parse.Parser]
    help: str
    env: _t.Union[str, Disabled]
    flags: _t.Union[_t.List[str], Disabled]
    is_subconfig: bool
    ty: _t.Type
    required: bool


@_t.overload
def field(
    *,
    help: _t.Optional[str] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
    required: bool = False,
) -> _t.Any: pass


@_t.overload
def field(
    default: _t.Union[T, _t.Literal[_Placeholders.MISSING]] = _Placeholders.MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[str] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
    required: bool = False,
) -> T: pass


def field(
    default: _t.Any = _Placeholders.MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[str] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
    required: bool = False,
) -> T:
    """Field descriptor, used for additional configuration of fields.

    :param default:
        default value for config field, used if field is missing from config.
    :param parser:
        parser that will be used to parse env vars, configs and CLI arguments.
    :param help:
        help message that will be used in CLI argument description.
        By default, this message is inferred from field's comments.
        See :meth:`~Config.load_from_args` for more info.
    :param env:
        name of environment variable that will be used for this field.
        See :meth:`~Config.load_from_env` for more info.
    :param flags:
        name of a CLI flag (or a list of names) that will be used
        for this field.
        See :meth:`~Config.load_from_args` for more info.
    :param required:
        set this argument to be required when configuring CLI parser.
        See :meth:`~Config.load_from_args` for more info.

    """

    return _t.cast(_t.Any, _FieldSettings(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flags=flags,
        required=required,
    ))


def _parse_collection_action(parser: yuio.parse.Parser):
    class Action(argparse.Action):
        def __call__(self, _, namespace, values, option_string=None):
            assert values is not None and not isinstance(values, str)

            setattr(namespace, self.dest, parser.parse_many(values))

    return Action


class Config:
    """Base class for configs.

    """

    _Self = _t.TypeVar('_Self', bound='Config')

    # Value is generated by __init_subclass__.
    _fields: _t.Dict[str, _Field]

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        try:
            docs = cls._find_docs()
        except Exception:
            logging.getLogger('yuio.internal').exception(
                'unable to get documentation for class %s',
                cls.__qualname__,
            )
            docs = {}

        fields = {}

        for base in reversed(cls.__mro__):
            if hasattr(base, '_fields'):
                fields.update(getattr(base, '_fields'))

        for name, ty in cls.__annotations__.items():
            if name.startswith('_'):
                continue

            value = cls.__dict__.get(name, _Placeholders.MISSING)
            if isinstance(value, _FieldSettings):
                field = value
            else:
                field = _FieldSettings(default=value)
            setattr(cls, name, field.default)

            fields[name] = field._update_defaults(
                f'{cls.__qualname__}.{name}', name, ty, docs.get(name))

        cls._fields = fields

    _COMMENT_RE = re.compile(r'^\s*#: ?(.*)\r?\n?$')

    @classmethod
    def _find_docs(cls) -> _t.Dict[str, str]:
        # based on code from Sphinx

        import inspect
        import ast

        if '<locals>' in cls.__qualname__:
            # This will not work as expected!
            raise OSError('source code not available')

        sourcelines, _ = inspect.getsourcelines(cls)

        docs = {}

        node = ast.parse(''.join(sourcelines))
        assert isinstance(node, ast.Module)
        assert len(node.body) == 1
        cdef = node.body[0]
        assert isinstance(cdef, ast.ClassDef)

        for stmt in cdef.body:
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and not stmt.target.id.startswith('_')
            ):
                comment_lines = []
                for before_line in sourcelines[stmt.lineno - 2::-1]:
                    if match := cls._COMMENT_RE.match(before_line):
                        comment_lines.append(match.group(1))
                    else:
                        break

                if comment_lines:
                    docs[stmt.target.id] = ' '.join(reversed(comment_lines))

        return docs

    def __init__(self, *args, **kwargs):
        for name, field in self._fields.items():
            if field.is_subconfig:
                setattr(self, name, field.ty())

        for arg in args:
            self.update(arg)

        self.update(kwargs)

    def update(self: _Self, other: _t.Union[_t.Dict[str, _t.Any], _Self], /):
        """Update fields in this config with fields from another config.

        This function is similar to :meth:`dict.update`.

        Nested configs are updated recursively.

        """

        if not other:
            return

        if isinstance(other, Config):
            ns = other.__dict__
        elif isinstance(other, dict):
            ns = other
            for name in ns:
                if name not in self._fields:
                    raise TypeError(f'unknown field: {name}')
        else:
            raise TypeError('expected a dict or a config class')

        for name, field in self._fields.items():
            if name in ns:
                if field.is_subconfig:
                    getattr(self, name).update(ns[name])
                elif ns[name] is not _Placeholders.MISSING:
                    setattr(self, name, ns[name])

    @classmethod
    def load_from_env(cls: _t.Type[_Self], prefix: str = '') -> _Self:
        """Load config from environment variables.

        Names of environment variables are just capitalized field names.
        Use the :func:`field` function to override them::

            class Config(yuio.config.Config):
                # Will be loaded from `SIGNAL`
                signal: int

                # Will be loaded from `PROCESS_ID`
                pid: int = yuio.config.field(env='PROCESS_ID')

        In nested configs, environment variable names are prefixed with name
        of a field that contains the nested config::

            class BigConfig(yuio.config.Config):
                # `kill_cmd.signal` will be loaded from `KILL_CMD_SIGNAL`
                kill_cmd: Config

                # `copy_cmd_2.signal` will be loaded from `KILL_SIGNAL`
                kill_cmd_2: Config = yuio.config.field(env='KILL')

                # `kill_cmd_3.signal` will be loaded from `SIGNAL`
                kill_cmd_3: Config = yuio.config.field(env='')

        You can also disable loading a field from an environment altogether::

            class Config(yuio.config.Config):
                # Will not be loaded from env
                pid: int = yuio.config.field(env=yuio.config.disabled())

        :param prefix:
            Add this prefix to all environment variable names
            before loading::

                # config.kill_cmd.field will be loaded
                # from `MY_APP_KILL_CMD_SIGNAL`
                config = BigConfig.load_from_env('MY_APP')

        """

        if prefix:
            prefix += '_'

        fields = {}

        for name, field in cls._fields.items():
            if field.env is _Placeholders.DISABLED:
                continue

            env = prefix + field.env

            if field.is_subconfig:
                fields[name] = field.ty.load_from_env(prefix=env)
            elif env in os.environ:
                assert field.parser is not None
                fields[name] = field.parser(os.environ[env])

        return cls(**fields)

    @classmethod
    def load_from_args(
        cls: _t.Type[_Self],
        args: _t.Optional[_t.List[str]] = None,
        /
    ) -> _Self:
        """Parse the given args and load config from them.

        If args are not given, will parse :data:`sys.argv`.

        Flag names are derived from field names;
        in nested configs, flags are prefixed with name
        of a field that contains the nested config.
        Use the :func:`field` function to override them::

            class Config(yuio.config.Config):
                # Will be loaded from `--signal`
                signal: int

                # Will be loaded from `-p` or `--pid`
                pid: int = yuio.config.field(flags=['-p', '--pid'])

            class BigConfig(yuio.config.Config):
                # `kill_cmd.signal` will be loaded from `--kill-cmd-signal`
                kill_cmd: Config

                # `copy_cmd_2.signal` will be loaded from `--kill-signal`
                kill_cmd_2: Config = yuio.config.field(flags='--kill')

                # `kill_cmd_3.signal` will be loaded from `--signal`
                kill_cmd_3: Config = yuio.config.field(flags='')

        You can also disable loading a field from CLI flags::

            class Config(yuio.config.Config):
                # Will not be loaded from args
                pid: int = yuio.config.field(flags=yuio.config.disabled())

        Help messages for the flags are parsed from the field comments.
        The :func:`field` function allows overriding them.

        If you need to make some flags required, use the `required` parameter
        of the :func:`field` function. It will only affect CLI parsing.

        Parsers for CLI argument values are derived from type hints.
        Use the `parser` parameter of the :func:`field` function
        to override them.

        Arguments with bool parsers and parsers that support
        :meth:`parsing collections <yuio.parse.Parser.supports_parse_many>`
        are handled to provide better CLI experience::

            class Config(yuio.config.Config):
                # Will create flags `--verbose` and `--no-verbose`.
                verbose: bool = True

                # Will create a flag with `nargs=*`: `--inputs path1 path2 ...`
                inputs: List[Path]

        """

        return cls.load_from_namespace(cls.setup_arg_parser().parse_args(args))

    @classmethod
    def load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace,
        /
    ) -> _Self:
        """Load config from parsed command line arguments.

        This method assumes that arguments parser was configured
        with :meth:`Config.setup_arg_parser`.

        """

        return cls._load_from_namespace(namespace, cls.__qualname__ + ':')

    @classmethod
    def _load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace,
        prefix: str
    ) -> _Self:

        fields = {}

        for name, field in cls._fields.items():
            if field.flags is _Placeholders.DISABLED:
                continue

            dest = prefix + name

            if field.is_subconfig:
                fields[name] = field.ty._load_from_namespace(
                    namespace, dest + '.')
            elif hasattr(namespace, dest):
                fields[name] = getattr(namespace, dest)

        return cls(**fields)

    @classmethod
    def setup_arg_parser(
        cls,
        parser: _t.Optional[argparse.ArgumentParser] = None,
        /
    ) -> argparse.ArgumentParser:
        """Add fields from this config as flags to an argument parser.

        If parser is not given, will create one.

        """

        if parser is None:
            parser = argparse.ArgumentParser()

        cls._setup_arg_parser(parser, parser, '', cls.__qualname__ + ':')

        return parser

    @classmethod
    def _setup_arg_parser(
        cls,
        group: argparse.ArgumentParser,
        parser: argparse.ArgumentParser,
        prefix: str,
        dest_prefix: str,
    ):
        if prefix:
            prefix += '-'

        for name, field in cls._fields.items():
            if field.flags is _Placeholders.DISABLED:
                continue

            dest = dest_prefix + name

            if prefix:
                flags = [prefix + flag.lstrip('-') for flag in field.flags]
            else:
                flags = field.flags

            if field.is_subconfig:
                group = _t.cast(_t.Any, parser.add_argument_group(
                    field.help.rstrip('.') or name))
                field.ty._setup_arg_parser(
                    group, parser, flags[0], dest + '.')
                continue

            assert field.parser is not None

            if field.parser.supports_parse_many():
                metavar = field.parser.describe_many()
            else:
                metavar = field.parser.describe()
            if metavar:
                metavar = '{' + metavar + '}'
            else:
                metavar = '<' + name.replace('_', '-') + '>'

            if isinstance(field.parser, yuio.parse.Bool):
                mutex_group = group.add_mutually_exclusive_group(
                    required=field.required)

                for flag in field.flags:
                    if flag.startswith('--'):
                        flag_pos = (prefix or "--") + flag[2:]
                        flag_neg = (prefix or '--') + 'no-' + flag[2:]
                        mutex_group.add_argument(
                            flag_neg,
                            default=_Placeholders.MISSING,
                            help=f'set {flag_pos} to `false`',
                            dest=dest,
                            action='store_false',
                        )
                        break

                mutex_group.add_argument(
                    *flags,
                    type=field.parser,
                    default=_Placeholders.MISSING,
                    help=field.help,
                    metavar=metavar,
                    dest=dest,
                    nargs='?',
                    const=True,
                )
            elif field.parser.supports_parse_many():
                group.add_argument(
                    *flags,
                    default=_Placeholders.MISSING,
                    help=field.help,
                    metavar=metavar,
                    dest=dest,
                    required=field.required,
                    nargs='*',
                    action=_parse_collection_action(field.parser),
                )
            else:
                group.add_argument(
                    *flags,
                    type=field.parser,
                    default=_Placeholders.MISSING,
                    help=field.help,
                    metavar=metavar,
                    dest=dest,
                    required=field.required,
                )

    @classmethod
    def load_from_parsed_file(
        cls: _t.Type[_Self],
        parsed: dict,
        /,
        *,
        ignore_unknown_fields: bool = False
    ) -> _Self:
        """Load config from parsed config file.

        This method takes a dict with arbitrary values that resulted from
        parsing type-rich configs such as ``.yaml`` or ``.json``.

        For example::

            with open('conf.yaml') as file:
                config = Config.load_from_parsed_file(yaml.load(file))

        """

        return cls._load_from_parsed_file(parsed, ignore_unknown_fields, '')

    @classmethod
    def _load_from_parsed_file(
        cls: _t.Type[_Self],
        parsed: dict,
        ignore_unknown_fields: bool = False,
        field_prefix: str = '',
    ) -> _Self:

        if not isinstance(parsed, dict):
            raise TypeError('config should be a dict')

        fields = {}

        if not ignore_unknown_fields:
            for name in parsed:
                if name not in cls._fields:
                    raise ValueError(
                        f'unknown config field {field_prefix}{name}')

        for name, field in cls._fields.items():
            if name in parsed:
                if field.is_subconfig:
                    fields[name] = field.ty._load_from_parsed_file(
                        parsed[name],
                        ignore_unknown_fields,
                        field_prefix=name + '.'
                    )
                else:
                    assert field.parser is not None
                    try:
                        value = field.parser.parse_config(parsed[name])
                        field.parser.validate(value)
                    except yuio.parse.ParsingError as e:
                        raise yuio.parse.ParsingError(
                            f'can\'t parse {field_prefix}{name}: {e}')
                    fields[name] = value

        return cls(**fields)

    @classmethod
    def load_from_json_file(
        cls: _t.Type[_Self],
        path: _t.Union[str, pathlib.Path],
        /,
        *,
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _Self:
        """Load config from a ``.json`` file.

        """

        import json

        return cls._load_from_file(
            path, json.loads, ignore_unknown_fields, ignore_missing_file)

    @classmethod
    def load_from_yaml_file(
        cls: _t.Type[_Self],
        path: _t.Union[str, pathlib.Path],
        /,
        *,
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _Self:
        """Load config from a ``.yaml`` file.

        This requires `PyYaml <https://pypi.org/project/PyYAML/>`_ package
        to be installed.

        """

        try:
            import yaml
        except ImportError:
            raise ImportError('PyYaml is not available')

        return cls._load_from_file(
            path, yaml.safe_load, ignore_unknown_fields, ignore_missing_file)

    @classmethod
    def load_from_toml_file(
        cls: _t.Type[_Self],
        path: _t.Union[str, pathlib.Path],
        /,
        *,
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _Self:
        """Load config from a ``.toml`` file.

        This requires `toml <https://pypi.org/project/toml/>`_ package
        to be installed.

        """

        try:
            import toml
        except ImportError:
            raise ImportError('toml is not available')

        return cls._load_from_file(
            path, toml.loads, ignore_unknown_fields, ignore_missing_file)

    @classmethod
    def _load_from_file(
        cls: _t.Type[_Self],
        path: _t.Union[str, pathlib.Path],
        parser: _t.Callable[[str], _t.Any],
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _Self:
        if ignore_missing_file and not os.path.exists(path):
            return cls()

        try:
            with open(path, 'r') as file:
                loaded = parser(file.read())
        except Exception as e:
            raise ValueError(f'invalid config {path}: {e}')

        return cls.load_from_parsed_file(
            loaded, ignore_unknown_fields=ignore_unknown_fields)

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if value is _Placeholders.MISSING:
            raise AttributeError(f'{item} is not configured')
        else:
            return value

    def __repr__(self):
        return self._repr('')

    def _repr(self, prefix):
        field_reprs = []
        for name in self._fields:
            value = getattr(self, name, _Placeholders.MISSING)
            if isinstance(value, Config):
                value_repr = value._repr(prefix + '  ')
            else:
                value_repr = repr(value)
            field_reprs.append(f'{prefix}  {name}={value_repr}')
        if field_reprs:
            field_desc = ",\n".join(field_reprs)
            return f'{self.__class__.__name__}(\n{field_desc}\n{prefix})'
