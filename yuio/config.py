# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides base a class for configs that can be loaded from
files, environment variables or command line arguments.


Creating and loading configs
----------------------------

Derive your config from the :class:`Config` base class. Inside of its body,
define config fields using type annotations. This is similar to how you
create dataclasses::

    class AppConfig(Config):
        app_version: str
        deployment_strategy: str = 'ROLLING'

:class:`Config` defines `__init__` that takes keyword arguments for defined
fields, as well as some constructors that load config from environment
variables, files, and so on.

Upon creation, all fields that aren't explicitly initialized and don't have
defaults are considered missing. Accessing them
will raise :class:`AttributeError`.

Here's an example of loading our config from command line arguments
and environment variables::

    # Load config from env.
    config = AppConfig.load_from_env()

    # Parse arguments and update our config.
    config.update(AppConfig.load_from_args())

.. autoclass:: Config
   :members:


Advanced field configuration
----------------------------

By default, :class:`Config` infers names for env variables and flags,
appropriate parsers, and other things from field's name and type hint.
If you need to override them, theres the :func:`field` function::

    class AppConfig(Config):
        app_version: str = field(
            default='HEAD',
            help='git tag or commit hash at which a new version is built.',
        )
        deployment_strategy: str = field(
            default='ROLLING',
            help='strategy that will be used to deploy new pods.',
            parser=yuio.parse.OneOf(
                yuio.parse.Str().upper(),
                ['ROLLING', 'READONLY', 'DOWNTIME']
            )

.. autofunction:: field

.. autofunction:: disabled

"""

import argparse
import json
import os
import typing as _t
from dataclasses import dataclass

import yuio.parse


T = _t.TypeVar('T')


class _Placeholder:
    def __init__(self, what: str):
        self._what = what

    def __bool__(self):
        return False

    def __repr__(self):
        return f'<{self._what}>'


_MISSING: _t.Any = _Placeholder('value is missing')
_DISABLED: _t.Any = _Placeholder('option is disabled')


def disabled() -> _t.Any:
    """Placeholder indicating that some field's functionality is disabled.

    Example::

        class AppConfig(Config):
            app_version: str = field(env=disabled())

    """

    return _DISABLED


@dataclass(frozen=True)
class _FieldSettings:
    default: _t.Any = _MISSING
    parser: _t.Optional[yuio.parse.Parser] = None
    help: _t.Optional[str] = None
    env: _t.Optional[str] = None
    flags: _t.Optional[_t.Union[str, _t.List[str]]] = None
    required: bool = False

    def _update_defaults(self, qualname, name, ty) -> '_Field':
        is_subconfig = isinstance(ty, type) and issubclass(ty, Config)

        help = self.help
        if help is None:
            help = ''

        env = self.env
        if env is None:
            env = name.upper()

        flags = self.flags
        if flags is None:
            flags = '--' + name.replace('_', '-')
        if not isinstance(flags, list):
            flags = [flags]
        if not flags:
            raise TypeError(
                f'{qualname}.{name} should have at least one flag')
        for flag in flags:
            if flag and not flag.startswith('-'):
                raise TypeError(
                    f'{qualname}.{name}: positional arguments '
                    f'are not supported')
            if not flag and not is_subconfig:
                raise TypeError(
                    f'{qualname}.{name} got an empty flag')

        default = self.default

        parser = self.parser

        required = self.required

        if is_subconfig:
            if default is not _MISSING:
                raise TypeError(
                    f'{qualname}.{name} cannot have defaults')

            if parser is not None:
                raise TypeError(
                    f'{qualname}.{name} cannot have parsers')

            if len(flags) > 1:
                raise TypeError(
                    f'{qualname}.{name} cannot have multiple flags')

            if flags[0] and not flags[0].startswith('--'):
                raise TypeError(
                    f'{qualname}.{name} cannot have a short flag ')

            if required:
                raise TypeError(
                    f'{qualname}.{name} cannot be required')
        elif parser is None:
            try:
                parser = yuio.parse.Parser.from_type_hint(ty)
            except TypeError:
                raise TypeError(
                    f'can\'t derive parser for {qualname}.{name}')

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
    env: str
    flags: _t.List[str]
    is_subconfig: bool
    ty: _t.Type
    required: bool


@_t.overload
def field(
    *,
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str]]] = None,
    required: bool = False,
) -> _t.Any: pass


@_t.overload
def field(
    default: T = _MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str]]] = None,
    required: bool = False,
) -> T: pass


def field(
    default: T = _MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str]]] = None,
    required: bool = False,
) -> T:
    """Field descriptor, used for additional configuration of fields.

    This is similar to what :func:`dataclasses.field` does.

    :param default:
        default value for config field, used if field is missing from config.
    :param parser:
        parser that will be used to parse env vars, configs and CLI arguments.
        By default, it's inferred from type hint.
    :param help:
        help message that will be used in CLI argument description.
    :param env:
        name of environment variable that will be used for this field.
        By default, it's inferred from field name.
        Set to :func:`disabled` to disable parsing from environment variable.
    :param flags:
        name of a CLI flag (or a list of names) that will be used
        for this field. By default, it's inferred from field name.
        Set to :func:`disabled` to disable parsing from command line arguments.
    :param required:
        set this argument to be required when configuring CLI parser.

    """

    return _t.cast(_t.Any, _FieldSettings(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flags=flags,
        required=required,
    ))


class _ConfigMeta(type):
    def __init__(cls, name, bases, namespace):
        super().__init__(name, bases, namespace)

        fields = {}

        for base in reversed(cls.__mro__):
            if hasattr(base, '_fields'):
                fields.update(getattr(base, '_fields'))

        for name, ty in cls.__annotations__.items():
            if name.startswith('_'):
                continue

            value = namespace.get(name, _MISSING)
            if isinstance(value, _FieldSettings):
                field = value
            else:
                field = _FieldSettings(default=value)
            setattr(cls, name, field.default)

            fields[name] = field._update_defaults(cls.__qualname__, name, ty)

        cls._fields = fields


def _parse_collection_action(parser: yuio.parse.Parser):
    class Action(argparse.Action):
        def __call__(self, _, namespace, values, option_string=None):
            assert values is not None and not isinstance(values, str)

            setattr(namespace, self.dest, parser.parse_many(values))

    return Action


class Config(metaclass=_ConfigMeta):
    """Base class for configs.

    """

    _Self = _t.TypeVar('_Self', bound='Config')

    # Value is generated by metaclass.
    _fields: _t.Dict[str, _Field]

    def __init__(self, *args, **kwargs):
        for name, field in self._fields.items():
            if field.is_subconfig:
                setattr(self, name, field.ty())

        for arg in args:
            self.update(arg)

        self.update(kwargs)

    def update(self: _Self, other: _t.Union[_t.Dict[str, _t.Any], _Self]):
        """Update fields in this config with fields from another config.

        This function is similar to :meth:`dict.update`.

        """

        if isinstance(other, Config):
            other = other.__dict__
        elif isinstance(other, dict):
            other = other.copy()
        else:
            raise TypeError('expected a dict or a config class')

        for name, field in self._fields.items():
            if name in other:
                if field.is_subconfig:
                    getattr(self, name).update(other[name])
                elif other[name] is not _MISSING:
                    setattr(self, name, other[name])
                other.pop(name)

        if other:
            unknown_fields = ', '.join(other)
            raise TypeError(f'unknown field(s): {unknown_fields}')

    @classmethod
    def load_from_env(cls: _t.Type[_Self]) -> _Self:
        """Load config from environment variables.

        Use :meth:`Config.update` to merge several loaded configs into one.

        """

        return cls._load_from_env('')

    @classmethod
    def _load_from_env(cls: _t.Type[_Self], prefix) -> _Self:
        fields = {}

        for name, field in cls._fields.items():
            if field.env is _DISABLED:
                continue

            env = prefix + field.env

            if field.is_subconfig:
                fields[name] = field.ty._load_from_env(env + '__')
            elif env in os.environ:
                assert field.parser is not None
                fields[name] = field.parser(os.environ[env])

        return cls(**fields)

    @classmethod
    def load_from_args(
        cls: _t.Type[_Self],
        args: _t.Optional[_t.List[str]] = None
    ) -> _Self:
        """Parse the given args and load config from them.

        If args are not given, will parse :data:`sys.argv`.

        """

        return cls.load_from_namespace(cls.setup_parser().parse_args(args))

    @classmethod
    def load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace
    ) -> _Self:
        """Load config from parsed command line arguments.

        This method assumes that arguments parser was configured
        with :meth:`Config.setup_parser`.

        Use :meth:`Config.update` to merge several loaded configs into one.

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
            if field.flags is _DISABLED:
                continue

            dest = prefix + name

            if field.is_subconfig:
                fields[name] = field.ty._load_from_namespace(
                    namespace, dest + '.')
            elif hasattr(namespace, dest):
                fields[name] = getattr(namespace, dest)

        return cls(**fields)

    @classmethod
    def load_from_config(
        cls: _t.Type[_Self],
        config: _t.Any,
        ignore_unknown_fields: bool = False
    ) -> _Self:
        """Load config from parsed config file.

        This method takes a dict with arbitrary values that resulted from
        parsing type-rich configs such as ``.yaml`` or ``.json``.

        For example::

            with open('conf.yml') as file:
                config = Config.load_from_config(yaml.load(file))

        Use :meth:`Config.update` to merge several loaded configs into one.

        """

        if not isinstance(config, dict):
            raise TypeError('config should be a dict')

        fields = {}

        if not ignore_unknown_fields:
            for name in config:
                if name not in cls._fields:
                    raise ValueError(f'unknown config field {name}')

        for name, field in cls._fields.items():
            if name in config:
                if field.is_subconfig:
                    fields[name] = field.ty.load_from_config(
                        config[name],
                        ignore_unknown_fields
                    )
                else:
                    assert field.parser is not None
                    value = field.parser.parse_config(config[name])
                    field.parser.validate(value)
                    fields[name] = value

        return cls(**fields)

    @classmethod
    def load_from_json(
        cls,
        path: str,
        ignore_unknown_fields: bool = False
    ):
        """Load config from a ``.json`` file.

        """

        with open(path, 'r') as file:
            try:
                loaded = json.load(file)
            except json.JSONDecodeError as e:
                raise ValueError(f'invalid config {path}: {e}')

        return cls.load_from_config(loaded, ignore_unknown_fields)

    @classmethod
    def setup_parser(
        cls,
        parser: _t.Optional[argparse.ArgumentParser] = None
    ) -> argparse.ArgumentParser:
        """Add fields from this config as flags to an argparse parser.

        If parser is not given, will create one.

        """

        if parser is None:
            parser = argparse.ArgumentParser()

        cls._setup_parser(parser, parser, '', cls.__qualname__ + ':')

        return parser

    @classmethod
    def _setup_parser(
        cls,
        group: argparse.ArgumentParser,
        parser: argparse.ArgumentParser,
        prefix: str,
        dest_prefix: str,
    ):
        for name, field in cls._fields.items():
            if field.flags is _DISABLED:
                continue

            dest = dest_prefix + name

            flags = [prefix + flag for flag in field.flags]

            if field.is_subconfig:
                group = _t.cast(_t.Any, parser.add_argument_group(
                    field.help.rstrip('.') or name))
                field.ty._setup_parser(
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

                for flag in flags:
                    pos = flag.rfind('--')
                    if flag.startswith('--') and pos >= 0:
                        flag_neg = flag[:pos] + '--no-' + flag[pos + 2:]
                        mutex_group.add_argument(
                            flag_neg,
                            default=_MISSING,
                            help=f'set {flag} to be `false`',
                            dest=dest,
                            action='store_false',
                        )
                        break

                mutex_group.add_argument(
                    *flags,
                    type=field.parser,
                    default=_MISSING,
                    help=field.help or 'not documented',
                    metavar=metavar,
                    dest=dest,
                    nargs='?',
                    const=True,
                )
            elif field.parser.supports_parse_many():
                group.add_argument(
                    *flags,
                    default=_MISSING,
                    help=field.help or 'not documented',
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
                    default=_MISSING,
                    help=field.help or 'not documented',
                    metavar=metavar,
                    dest=dest,
                    required=field.required,
                )

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if value is _MISSING:
            raise AttributeError(f'{item} is not configured')
        else:
            return value

    def __repr__(self):
        return self._repr('')

    def _repr(self, prefix):
        field_reprs = []
        for name in self._fields:
            value = getattr(self, name, _MISSING)
            if value is not _MISSING:
                if isinstance(value, Config):
                    value_repr = value._repr(prefix + '  ')
                else:
                    value_repr = repr(value)
                field_reprs.append(f'{prefix}  {name}={value_repr}')
        if field_reprs:
            field_desc = ",\n".join(field_reprs)
            return f'{self.__class__.__name__}(\n{field_desc}\n{prefix})'
