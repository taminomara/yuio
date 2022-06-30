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

    # Create and setup parser.
    parser = argparse.ArgumentParser()
    AppConfig.setup_parser(parser)

    # Parse arguments, convert them to config,
    # and merge with config loaded from env.
    config.update(AppConfig.load_from_args(parser.parse_args()))

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
                yuio.parse.StrUpper(),
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
    flag: _t.Optional[_t.Union[str, _t.List[str]]] = None

    def _update_defaults(self, qualname, name, ty) -> '_Field':
        default = self.default

        parser = self.parser
        if parser is None:
            try:
                parser = yuio.parse.Parser.from_type_hint(ty)
            except TypeError:
                raise TypeError(
                    f'can\'t derive parser for {qualname}.{name}')

        help = self.help
        if help is None:
            help = 'not documented.'

        env = self.env
        if env is None:
            env = name.upper()

        flag = self.flag
        if flag is None:
            flag = '--' + name.replace('_', '-')
        if not isinstance(flag, list):
            flag = [flag]

        dest = qualname.replace('.', '__') + '__' + name

        return _Field(
            default,
            parser,
            help,
            env,
            flag,
            dest
        )


@dataclass(frozen=True)
class _Field:
    default: _t.Any
    parser: yuio.parse.Parser
    help: str
    env: str
    flag: _t.List[str]
    dest: str


@_t.overload
def field(
    *,
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flag: _t.Optional[_t.Union[str, _t.List[str]]] = None,
) -> _t.Any: pass


@_t.overload
def field(
    default: T = _MISSING,
    *,
    parser: yuio.parse.Parser[T],
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flag: _t.Optional[_t.Union[str, _t.List[str]]] = None,
) -> T: pass


def field(
    default: T = _MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flag: _t.Optional[_t.Union[str, _t.List[str]]] = None,
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
    :param flag:
        name of a CLI flag (or a list of names) that will be used
        for this field. By default, it's inferred from field name.
        Set to :func:`disabled` to disable parsing from command line arguments.

    """

    return _t.cast(_t.Any, _FieldSettings(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flag=flag
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


class Config(metaclass=_ConfigMeta):
    """Base class for configs.

    """

    _Self = _t.TypeVar('_Self', bound='Config')

    # Value is generated by metaclass.
    _fields: _t.ClassVar[_t.Dict[str, _Field]]

    def __init__(self, **kwargs):
        for name in self._fields:
            if name in kwargs:
                setattr(self, name, kwargs.pop(name))

        if kwargs:
            unknown_fields = ', '.join(kwargs)
            raise TypeError(f'unknown field(s): {unknown_fields}')

    def update(self: _Self, other: _Self):
        """Update fields in this config with fields from another config.

        This function is similar to :meth:`dict.update`.

        """

        for name in self._fields:
            if name in other.__dict__:
                setattr(self, name, getattr(other, name))

    @classmethod
    def load_from_env(cls: _t.Type[_Self]) -> _Self:
        """Load config from environment variables.

        Use :meth:`Config.update` to merge several loaded configs into one.

        """

        fields = {}

        for name, field in cls._fields.items():
            if field.env is _DISABLED:
                continue

            if field.env in os.environ:
                fields[name] = field.parser(os.environ[field.env])

        return cls(**fields)

    @classmethod
    def load_from_args(
        cls: _t.Type[_Self],
        args: _t.Optional[argparse.Namespace] = None
    ) -> _Self:
        """Load config from parsed command line arguments.

        This method assumes that arguments parser was configured
        with :meth:`Config.setup_parser`.

        Use :meth:`Config.update` to merge several loaded configs into one.

        If `args` is not given, will create a parser and parse arguments
        from :data:`sys.argv`.

        """

        if args is None:
            args = cls.setup_parser().parse_args()

        fields = {}

        for name, field in cls._fields.items():
            if field.flag is _DISABLED:
                continue

            value = getattr(args, field.dest, _MISSING)
            if value is not _MISSING:
                fields[name] = value

        return cls(**fields)

    @classmethod
    def load_from_config(
        cls: _t.Type[_Self],
        config: _t.Dict[str, _t.Any],
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

        fields = {}

        if not ignore_unknown_fields:
            for name in config:
                if name not in cls._fields:
                    raise ValueError(f'unknown config field {name}')

        for name, field in cls._fields.items():
            value = config.get(name, _MISSING)
            if value is not _MISSING:
                value = field.parser.parse_config(value)
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

        for name, field in cls._fields.items():
            if field.flag is _DISABLED:
                continue

            metavar = field.parser.describe()
            if metavar:
                metavar = '{' + metavar + '}'
            else:
                metavar = '<' + name.replace('_', '-') + '>'

            kwargs = {}

            if isinstance(field.parser, yuio.parse.Bool):
                kwargs['nargs'] = '?'
                kwargs['const'] = True

            parser.add_argument(
                *field.flag,
                type=field.parser,
                default=_MISSING,
                help=field.help,
                metavar=metavar,
                dest=field.dest,
                **kwargs
            )

        return parser

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if value is _MISSING:
            raise AttributeError(f'{item} is not configured')
        else:
            return value

    def __repr__(self):
        field_reprs = []
        for name in self._fields:
            value = getattr(self, name, _MISSING)
            if value is not _MISSING:
                field_reprs.append(f'{name}={value!r}')
        if field_reprs:
            field_desc = ",\n  ".join(field_reprs)
            return f'{self.__class__.__name__}(\n  {field_desc}\n)'
