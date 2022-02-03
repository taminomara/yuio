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


class _Placeholder:
    def __init__(self, what: str):
        self._what = what

    def __bool__(self):
        return False

    def __repr__(self):
        return f'<{self._what}>'


_MISSING = _Placeholder('value is missing')
_DISABLED = _Placeholder('option is disabled')


def disabled() -> _t.Any:
    """Placeholder indicating that some field's functionality is disabled.

    Example::

        class AppConfig(Config):
            app_version: str = field(env=disabled())

    """

    return _DISABLED


@dataclass
class _Field:
    default: _t.Any = _MISSING
    parser: _t.Optional[yuio.parse.Parser] = None
    help: _t.Optional[str] = None
    env: _t.Optional[str] = None
    flag: _t.Optional[_t.Union[str, _t.List[str]]] = None
    dest: _t.Optional[str] = None


def field(
    default: _t.Any = _MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser] = None,
    help: _t.Optional[str] = None,
    env: _t.Optional[str] = None,
    flag: _t.Optional[_t.Union[str, _t.List[str]]] = None,
) -> _t.Any:
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

    return _Field(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flag=flag
    )


class _ConfigMeta(type):
    def __init__(cls, *args, **kwargs):
        type.__init__(cls, *args, **kwargs)

        annotations = {}

        for base in reversed(cls.__mro__):
            if hasattr(base, '__annotations__'):
                annotations.update(getattr(base, '__annotations__'))

        if hasattr(cls, '__annotations__'):
            annotations.update(getattr(cls, '__annotations__'))

        fields = {}

        for name, ty in annotations.items():
            if name.startswith('_'):
                continue

            value = getattr(cls, name, _MISSING)
            if isinstance(value, _Field):
                field = value
            else:
                field = _Field(default=value)
            setattr(cls, name, field.default)

            if field.parser is None:
                try:
                    field.parser = yuio.parse.Parser.from_type_hint(ty)
                except TypeError:
                    raise TypeError(
                        f'can\'t derive parser for {cls.__qualname__}.{name}')

            if field.env is None:
                field.env = name.upper()

            if field.flag is None:
                field.flag = '--' + name.replace('_', '-')

            field.dest = cls.__qualname__.replace('.', '__') + '__' + name

            fields[name] = field

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

            if field.env and field.env in os.environ:
                fields[name] = field.parser(os.environ[field.env])

        return cls(**fields)

    @classmethod
    def load_from_args(cls: _t.Type[_Self], args: argparse.Namespace) -> _Self:
        """Load config from parsed command line arguments.

        This method assumes that arguments parser was configured
        with :meth:`Config.setup_parser`.

        Use :meth:`Config.update` to merge several loaded configs into one.

        """

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
    def setup_parser(cls, parser: argparse.ArgumentParser):
        """Add fields from this config as flags to an argparse parser.

        """

        for name, field in cls._fields.items():
            if field.flag is _DISABLED:
                continue

            flag = field.flag
            if not isinstance(flag, list):
                flag = [flag]

            metavar = field.parser.describe()
            if metavar:
                metavar = '{' + metavar + '}'
            else:
                metavar = '<' + name.replace('_', '-') + '>'

            parser.add_argument(
                *flag,
                type=field.parser,
                default=_MISSING,
                help=field.help or 'not documented',
                metavar=metavar,
                dest=field.dest
            )

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if value is _MISSING:
            raise AttributeError(f'{item} is not configured')
        else:
            return value

    def __repr__(self):
        field_reprs = []
        for name in self._fields:
            # We don't want to show missing values or default values,
            # so we only show those that appear in our __dict__.
            value = self.__dict__.get(name, _MISSING)
            if value is not _MISSING:
                field_reprs.append(f'{name}={value!r}')
        return f'{self.__class__.__name__}({", ".join(field_reprs)})'
