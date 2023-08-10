# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides a base class for configs that can be loaded from
files, environment variables or command line arguments (via :mod:`yuio.app`).

Derive your config from the :class:`Config` base class. Inside of its body,
define config fields using type annotations,
just like :mod:`dataclasses`::

    class AppConfig(Config):
        #: trained model to execute
        model: pathlib.Path

        #: input data for the model
        data: pathlib.Path

        #: enable or disable gpu
        use_gpu: bool = True

Then use config's constructors and the :meth:`~Config.update` method
to load it from various sources::

    # Load config from a file.
    config = config.load_from_json_file('~/.my_app_cfg.json')

    # Update config with values from env.
    config.update(AppConfig.load_from_env())


Config base class
-----------------

.. autoclass:: Config
   :members:


Advanced field configuration
----------------------------

By default, :class:`Config` infers names for env variables and flags,
appropriate parsers, and other things from field's name, type hint, and comments.

If you need to override them, theres the :func:`field` function:

.. autofunction:: field

.. autodata:: DISABLED

.. autodata:: MISSING

.. autodata:: POSITIONAL

There are also a few helpers:

.. autofunction:: inline

.. autofunction:: positional


Nesting configs
---------------

You can nest configs to achieve modularity::

    class ExecutorConfig(Config):
        #: number of threads to use
        threads: int

        #: enable or disable gpu
        use_gpu: bool = True

    class AppConfig(Config):
        #: executor parameters
        executor: ExecutorConfig

        #: trained model to execute
        model: pathlib.Path

To initialise a nested config, pass either an instance of if
or a dict with its variables to the config's constructor::

    # The following lines are equivalent:
    config = AppConfig(executor={'threads': 16})
    config = AppConfig(executor=ExecutorConfig(threads=16))


Parsing environment variables
-----------------------------

You can load config from environment through :meth:`~Config.load_from_env`.

Names of environment variables are just capitalized field names.
Use the :func:`field` function to override them::

    class KillCmdConfig(Config):
        # Will be loaded from `SIGNAL`.
        signal: int

        # Will be loaded from `PROCESS_ID`.
        pid: int = field(env='PROCESS_ID')

In nested configs, environment variable names are prefixed with name
of a field that contains the nested config::

    class BigConfig(Config):
        # `kill_cmd.signal` will be loaded from `KILL_CMD_SIGNAL`.
        kill_cmd: KillCmdConfig

        # `copy_cmd_2.signal` will be loaded from `KILL_SIGNAL`.
        kill_cmd_2: KillCmdConfig = field(env='KILL')

        # `kill_cmd_3.signal` will be loaded from `SIGNAL`.
        kill_cmd_3: KillCmdConfig = field(env='')

You can also disable loading a field from an environment altogether::

    class Config(Config):
        # Will not be loaded from env.
        pid: int = field(env=DISABLED)

To prefix all variable names with some string, pass the `prefix` parameter
to the :meth:`~Config.load_from_env` function::

    # config.kill_cmd.field will be loaded
    # from `MY_APP_KILL_CMD_SIGNAL`
    config = BigConfig.load_from_env('MY_APP')


Parsing config files
--------------------

You can load config from structured config files,
such as `json`, `yaml` or `toml`::

    class ExecutorConfig(Config):
        threads: int
        use_gpu: bool = True

    class AppConfig(Config):
        executor: ExecutorConfig
        model: pathlib.Path

    config = AppConfig.load_from_json_file('~/.my_app_cfg.json')

In this example, contents of the above config would be:

.. code-block:: json

    {
        "executor": {
            "threads": 16,
            "use_gpu": true
        },
        "model": "/path/to/model"
    }

Note that, unlike with environment variables,
there is no way to inline nested configs.


Parsing CLI arguments
---------------------

:mod:`yuio.app` allows you to parse configs from CLI arguments.

Flag names are derived from field names.
Use the :func:`field` function to override them::

    class KillCmdConfig(Config):
        # Will be loaded from `--signal`.
        signal: int

        # Will be loaded from `-p` or `--pid`.
        pid: int = field(flags=['-p', '--pid'])

In nested configs, flags are prefixed with name
of a field that contains the nested config::

    class BigConfig(Config):
        # `kill_cmd.signal` will be loaded from `--kill-cmd-signal`.
        kill_cmd: KillCmdConfig

        # `copy_cmd_2.signal` will be loaded from `--kill-signal`.
        kill_cmd_2: KillCmdConfig = field(flags='--kill')

        # `kill_cmd_3.signal` will be loaded from `--signal`.
        kill_cmd_3: KillCmdConfig = field(flags='')

You can also disable loading a field from CLI flags::

    class KillCmdConfig(Config):
        # Will not be loaded from args.
        pid: int = field(flags=DISABLED)

.. note::

   Positional arguments are not allowed in configs,
   only in apps and subcommands.

Help messages for the flags are parsed from line comments
right above the field definition (comments must start with ``#:``).
The :func:`field` function allows overriding them.

Parsers for CLI argument values are derived from type hints.
Use the `parser` parameter of the :func:`field` function to override them.

Arguments with bool parsers and parsers that support
:meth:`parsing collections <yuio.parse.Parser.supports_parse_many>`
are handled to provide better CLI experience::

    class Config(Config):
        # Will create flags `--verbose` and `--no-verbose`.
        verbose: bool = True

        # Will create a flag with `nargs=*`: `--inputs path1 path2 ...`
        inputs: List[Path]

"""

import argparse
import logging
import os
import pathlib
import enum
import typing as _t
from dataclasses import dataclass

import yuio._utils
import yuio.parse


T = _t.TypeVar('T')


class _Placeholders(enum.Enum):
    DISABLED = '<disabled>'
    MISSING = '<missing>'
    POSITIONAL = '<positional>'

    def __repr__(self):
        return self.value


#: Type of the :data:`DISABLED` placeholder.
Disabled: _t.TypeAlias = _t.Literal[_Placeholders.DISABLED]
#: Indicates that some functionality is disabled.
DISABLED: "Disabled" = _Placeholders.DISABLED

#: Type of the :data:`MISSING` placeholder.
Missing: _t.TypeAlias = _t.Literal[_Placeholders.MISSING]
#: Indicates that some value is missing.
MISSING: "Missing" = _Placeholders.MISSING

#: Type of the :data:`POSITIONAL` placeholder.
Positional: _t.TypeAlias = _t.Literal[_Placeholders.POSITIONAL]
#: Used with :func:`field` to enable positional arguments.
POSITIONAL: "Positional" = _Placeholders.POSITIONAL


@dataclass(frozen=True)
class _FieldSettings:
    default: _t.Any
    parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None
    help: _t.Union[str, "Disabled", None] = None
    env: _t.Union[str, "Disabled", None] = None
    flags: _t.Union[str, _t.List[str], "Disabled", "Positional", None] = None
    required: bool = False

    def _update_defaults(
        self,
        qualname: str,
        name: str,
        ty_with_extras: _t.Any,
        parsed_help: _t.Optional[str],
        allow_positionals: bool,
    ) -> '_Field':
        ty = ty_with_extras
        while _t.get_origin(ty) is _t.Annotated:
            ty = _t.get_args(ty)[0]
        is_subconfig = isinstance(ty, type) and issubclass(ty, Config)

        help: _t.Union[str, "Disabled"]
        if self.help is not None:
            help = self.help
        elif parsed_help is not None:
            help = parsed_help
        elif is_subconfig and ty.__doc__:
            help = ty.__doc__
        else:
            help = ''
        if help == argparse.SUPPRESS:
            help = DISABLED

        env: _t.Union[str, "Disabled"]
        if self.env is not None:
            env = self.env
        else:
            env = name.upper()
        if env == '' and not is_subconfig:
            raise TypeError(
                f'{qualname} got an empty env variable name')

        flags: _t.Union[_t.List[str], "Disabled", "Positional"]
        if self.flags is DISABLED or self.flags is POSITIONAL:
            flags = self.flags
            if not allow_positionals and flags is POSITIONAL:
                raise TypeError(
                    f'{qualname}: positional arguments are not allowed in configs')
        elif self.flags is None:
            flags = ['--' + name.replace('_', '-')]
        elif isinstance(self.flags, str):
            flags = [self.flags]
        else:
            if not self.flags:
                raise TypeError(
                    f'{qualname} should have at least one flag')
            flags = self.flags
        if flags is not DISABLED and flags is not POSITIONAL:
            for flag in flags:
                if flag and not flag.startswith('-'):
                    raise TypeError(
                        f'{qualname}: flag should start with a dash')
                if not flag and not is_subconfig:
                    raise TypeError(
                        f'{qualname} got an empty flag')

        default = self.default

        parser = self.parser

        required = self.required

        if is_subconfig:
            if default is not MISSING:
                raise TypeError(
                    f'{qualname} cannot have defaults')

            if parser is not None:
                raise TypeError(
                    f'{qualname} cannot have parsers')

            if flags is not DISABLED:
                if flags is POSITIONAL:
                    raise TypeError(
                        f'{qualname} cannot be positional')
                if len(flags) > 1:
                    raise TypeError(
                        f'{qualname} cannot have multiple flags')
                if flags[0] and not flags[0].startswith('--'):
                    raise TypeError(
                        f'{qualname} cannot have a short flag')
        elif parser is None:
            try:
                parser = yuio.parse.from_type_hint(ty_with_extras)
            except TypeError as e:
                raise TypeError(
                    f'can\'t derive parser for {qualname}: {e}') from None

        if parser is not None:
            origin = _t.get_origin(ty)
            args = _t.get_args(ty)

            is_optional = (
                default is None
                or origin is _t.Union and len(args) == 2 and type(None) in args
            )

            if is_optional and not isinstance(parser, yuio.parse.Optional):
                parser = yuio.parse.Optional(parser)

            if flags is POSITIONAL and default is not MISSING and parser.supports_parse_many():
                raise TypeError(
                    f'{qualname}: positional multi-value arguments can\'t have defaults')

        return _Field(
            default,
            parser,
            help,
            env,
            flags,
            is_subconfig,
            ty,
            required,
        )


@dataclass(frozen=True)
class _Field:
    default: _t.Any
    parser: _t.Optional[yuio.parse.Parser[_t.Any]]
    help: _t.Union[str, "Disabled"]
    env: _t.Union[str, "Disabled"]
    flags: _t.Union[_t.List[str], "Disabled", "Positional"]
    is_subconfig: bool
    ty: _t.Type
    required: bool


@_t.overload
def field(
    *,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
    flags: _t.Union[str, _t.List[str], "Positional", "Disabled", None] = None,
) -> _t.Any: ...


@_t.overload
def field(
    default: _t.Union[T, "Missing"] = MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
    flags: _t.Union[str, _t.List[str], "Positional", "Disabled", None] = None,
) -> T: ...


@_t.overload
def field(
    default: None,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
    flags: _t.Union[str, _t.List[str], "Positional", "Disabled", None] = None,
) -> _t.Optional[T]: ...


def field(
    default: _t.Any = MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
    flags: _t.Union[str, _t.List[str], "Disabled", "Positional", None] = None,
) -> _t.Any:
    """Field descriptor, used for additional configuration of fields.

    :param default:
        default value for config field, used if field is missing from config.
    :param parser:
        parser that will be used to parse env vars, configs and CLI arguments.
    :param help:
        Help message that will be used in CLI argument description.

        Pass :data:`DISABLED` to remove this field from CLI help.

        By default, help message is inferred from comments right above the field
        definition (comments must start with ``#:``).
    :param env:
        Name of environment variable that will be used for this field.

        Pass :data:`DISABLED` to disable loading this field form environment variable.

        Pass an empty string to disable prefixing nested config variables.
    :param flags:
        List of names (or a single name) of CLI flags that will be used for this field.

        Pass :data:`DISABLED` to disable loading this field form CLI arguments.

        Pass :data:`POSITIONAL` to make this argument positional (only in apps and subcommands).

        Pass an empty string to disable prefixing nested config flags.

        See :mod:`yuio.app` for details.

    """

    return _FieldSettings(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flags=flags,
    )


def inline(
    help: _t.Union[str, "Disabled", None] = None,
) -> _t.Any:
    """A shortcut for inlining nested configs.

    Equivalent to calling :func:`field` with ``env`` and ``flags`` set to an empty string.

    """

    return field(help=help, env='', flags='')


@_t.overload
def positional(
    *,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
) -> _t.Any: ...


@_t.overload
def positional(
    default: _t.Union[T, "Missing"] = MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
) -> T: ...


@_t.overload
def positional(
    default: None,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
) -> _t.Optional[T]: ...


def positional(
    default: _t.Any = MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None,
    help: _t.Union[str, "Disabled", None] = None,
    env: _t.Union[str, "Disabled", None] = None,
) -> _t.Any:
    """A shortcut for adding a positional argument.

    Equivalent to calling :func:`field` with ``flags`` set to :data:`POSITIONAL`.

    """

    return field(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flags=POSITIONAL,
    )


def _action(parser: yuio.parse.Parser, parse_many: bool):
    class Action(argparse.Action):
        def __call__(self, _, namespace, values, option_string=None):
            try:
                if parse_many:
                    if values is MISSING:
                        values = []
                    assert values is not None and not isinstance(values, str)
                    parsed = parser.parse_many(values)
                else:
                    if values is MISSING:
                        return
                    assert isinstance(values, str)
                    parsed = parser.parse(values)
            except argparse.ArgumentTypeError as e:
                raise argparse.ArgumentError(self, str(e))
            setattr(namespace, self.dest, parsed)

    return Action


class _VerboseAction(argparse.Action):
    def __call__(self, _, namespace, values, option_string=None):
        count = (getattr(namespace, self.dest, 0) or 0) + 1
        setattr(namespace, self.dest, count)

        # TODO!

        # import yuio.io
        # yuio.io.setup(debug_output=True)

        pass


class Config:
    """Base class for configs.

    Pass keyword args to set fields, or pass another config to copy it::

        Config(config1, config2, ..., field1=value1, ...)

    Upon creation, all fields that aren't explicitly initialized
    and don't have defaults are considered missing.
    Accessing them will raise :class:`AttributeError`.

    """

    _Self = _t.TypeVar('_Self', bound='Config')

    # Value is generated lazily by `__get_fields`.
    __allow_positionals: _t.ClassVar[bool] = False
    __fields: _t.ClassVar[_t.Optional[_t.Dict[str, _Field]]] = None

    @classmethod
    def __get_fields(cls) -> _t.Dict[str, _Field]:
        if cls.__fields is not None:
            return cls.__fields

        try:
            docs = yuio._utils.find_docs(cls)
        except Exception:
            yuio._logger.exception(
                'unable to get documentation for class %s',
                cls.__qualname__,
            )
            docs = {}

        fields = {}
        defaults = {}

        for base in reversed(cls.__mro__):
            if base is not cls and hasattr(base, '_Config__get_fields'):
                fields.update(getattr(base, '_Config__get_fields')())

        try:
            types = _t.get_type_hints(cls, include_extras=True)
        except NameError as e:
            if '<locals>' in cls.__qualname__:
                raise NameError(
                    f'{e}. '
                    f'Note: forward references do not work inside functions '
                    f'(see https://github.com/python/typing/issues/797)'
                ) from None
            raise

        for name in cls.__annotations__:
            if name.startswith('_'):
                continue

            value = cls.__dict__.get(name, MISSING)
            if isinstance(value, _FieldSettings):
                field = value
            else:
                field = _FieldSettings(default=value)

            defaults[name] = field.default
            fields[name] = field._update_defaults(
                f'{cls.__qualname__}.{name}', name, types[name], docs.get(name), cls.__allow_positionals)

        # We don't want to set any attributes on cls if any `_update_defaults` has
        # raised an exception. For this reason, we defer setting defaults
        # until all fields were processed.
        for name, default in defaults.items():
            setattr(cls, name, default)
        cls.__fields = fields

        return fields

    def __init_subclass__(cls, _allow_positionals=None, **kwargs):
        super().__init_subclass__(**kwargs)

        if _allow_positionals is not None:
            cls.__allow_positionals = _allow_positionals
        cls.__fields = None

    def __init__(self, *args, **kwargs):
        for name, field in self.__get_fields().items():
            if field.is_subconfig:
                setattr(self, name, field.ty())

        for arg in args:
            self.update(arg)

        self.update(kwargs)

    def update(
        self: _Self,
        other: _t.Union[_t.Dict[str, _t.Any], _Self],
        /
    ):
        """Update fields in this config with fields from another config.

        This function is similar to :meth:`dict.update`.

        Nested configs are updated recursively.

        """

        if not other:
            return

        if isinstance(other, Config):
            if (
                self.__class__ not in other.__class__.__mro__
                and other.__class__ not in self.__class__.__mro__
            ):
                raise TypeError('updating from an incompatible config')
            ns = other.__dict__
        elif isinstance(other, dict):
            ns = other
            for name in ns:
                if name not in self.__get_fields():
                    raise TypeError(f'unknown field: {name}')
        else:
            raise TypeError('expected a dict or a config class')

        for name, field in self.__get_fields().items():
            if name in ns:
                if field.is_subconfig:
                    getattr(self, name).update(ns[name])
                elif ns[name] is not MISSING:
                    setattr(self, name, ns[name])

    @classmethod
    def load_from_env(
        cls: _t.Type[_Self],
        prefix: str = ''
    ) -> _Self:
        """Load config from environment variables.

        """

        fields = {}

        for name, field in cls.__get_fields().items():
            if field.env is DISABLED:
                continue

            if prefix and field.env:
                env = f'{prefix}_{field.env}'
            else:
                env = f'{prefix}{field.env}'

            if field.is_subconfig:
                fields[name] = field.ty.load_from_env(prefix=env)
            elif env in os.environ:
                assert field.parser is not None
                fields[name] = field.parser.parse(os.environ[env])

        return cls(**fields)

    @classmethod
    def _load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace,
        /,
        *,
        ns_prefix: str = '',
    ) -> _Self:
        return cls.__load_from_namespace(namespace, ns_prefix + ':')

    @classmethod
    def __load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace,
        prefix: str
    ) -> _Self:

        fields = {}

        for name, field in cls.__get_fields().items():
            if field.flags is DISABLED:
                continue

            dest = prefix + name

            if field.is_subconfig:
                fields[name] = field.ty.__load_from_namespace(
                    namespace, dest + '.')
            elif hasattr(namespace, dest):
                fields[name] = getattr(namespace, dest)

        return cls(**fields)

    @classmethod
    def _setup_arg_parser(
        cls,
        parser: argparse.ArgumentParser,
        /,
        *,
        ns_prefix: str = '',
    ):
        parser.add_argument(
            '-v', '--verbose',
            help='increase verbosity of output',
            action=_VerboseAction,
            nargs=0,
        )

        # Note: `yuio.term` will search for these flags in `sys.argv` on its own,
        # our job is simply to accept them. This is done to avoid situations when
        # `yuio.io` gets used before parsing arguments.
        color = parser.add_mutually_exclusive_group()
        color.add_argument(
            '--force-color',
            help='force-enable colored output',
            action='store_true',
        )
        color.add_argument(
            '--force-no-color',
            help='force-disable colored output',
            action='store_true',
        )

        cls.__setup_arg_parser(parser, parser, '', ns_prefix + ':', False)

    @classmethod
    def __setup_arg_parser(
        cls,
        group: argparse.ArgumentParser,
        parser: argparse.ArgumentParser,
        prefix: str,
        dest_prefix: str,
        suppress_help: bool,
    ):
        if prefix:
            prefix += '-'

        for name, field in cls.__get_fields().items():
            if field.flags is DISABLED:
                continue

            dest = dest_prefix + name

            if suppress_help or field.help is DISABLED:
                help = argparse.SUPPRESS
                current_suppress_help = True
            else:
                help = field.help
                current_suppress_help = False
                if field.default is not MISSING:
                    assert field.parser is not None
                    if isinstance(field.parser, yuio.parse.Bool):
                        default_desc = 'enabled' if field.default else 'disabled'
                    else:
                        default_desc = field.parser.describe_value_or_def(field.default)
                    help += f' [default: {default_desc}]'

            flags: _t.Union[_t.List[str], "Positional"]
            if prefix and field.flags is not POSITIONAL:
                flags = [prefix + flag.lstrip('-') for flag in field.flags]
            else:
                flags = field.flags

            if field.is_subconfig:
                assert flags is not POSITIONAL
                if current_suppress_help:
                    subgroup = group
                else:
                    lines = help.split('\n\n', 1)
                    title = lines[0].replace('\n', ' ').rstrip('.') or name
                    desc = lines[1] if len(lines) > 1 else None
                    subgroup = parser.add_argument_group(title, desc)
                field.ty.__setup_arg_parser(
                    subgroup, parser, flags[0], dest + '.', current_suppress_help)
                continue
            else:
                assert field.parser is not None

            parse_many = field.parser.supports_parse_many()

            action = _action(field.parser, parse_many)

            if flags is POSITIONAL:
                metavar = '<' + name.replace('_', '-') + '>'
            elif parse_many:
                metavar = field.parser.describe_many_or_def()
                if isinstance(metavar, tuple):
                    metavar = tuple("{" + v + "}" for v in metavar)
                else:
                    metavar = "{" + metavar + "}"
            else:
                metavar = '{' + field.parser.describe_or_def() + '}'

            nargs = field.parser.get_nargs()
            if flags is POSITIONAL and field.default is not MISSING and nargs is None:
                nargs = '?'
            nargs_kw: _t.Any = {'nargs': nargs} if nargs is not None else {}

            if flags is POSITIONAL:
                group.add_argument(
                    dest,
                    default=MISSING,
                    help=help,
                    metavar=metavar,
                    action=action,
                    **nargs_kw,
                )
            elif isinstance(field.parser, yuio.parse.Bool):
                mutex_group = group.add_mutually_exclusive_group(
                    required=field.required)

                mutex_group.add_argument(
                    *flags,
                    default=MISSING,
                    help=help,
                    dest=dest,
                    action='store_true',
                )

                assert field.flags is not POSITIONAL
                for flag in field.flags:
                    if flag.startswith('--'):
                        flag_neg = (prefix or '--') + 'no-' + flag[2:]
                        if current_suppress_help:
                            help = argparse.SUPPRESS
                        else:
                            help = f'disable {(prefix or "--") + flag[2:]}'
                        mutex_group.add_argument(
                            flag_neg,
                            default=MISSING,
                            help=help,
                            dest=dest,
                            action='store_false',
                        )
                        break
            else:
                group.add_argument(
                    *flags,
                    default=MISSING,
                    help=help,
                    metavar=metavar,
                    required=field.required,
                    dest=dest,
                    action=action,
                    **nargs_kw,
                )

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

        return cls.__load_from_file(
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
            import yaml  # type: ignore
        except ImportError:
            raise ImportError('PyYaml is not available')

        return cls.__load_from_file(
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

        This requires
        `tomllib <https://docs.python.org/3/library/tomllib.html>`_ or
        `toml <https://pypi.org/project/toml/>`_ package
        to be installed.

        """

        try:
            import toml  # type: ignore
        except ImportError:
            try:
                import tomllib as toml  # type: ignore
            except ImportError:
                raise ImportError('toml is not available')

        return cls.__load_from_file(
            path, toml.loads, ignore_unknown_fields, ignore_missing_file)

    @classmethod
    def __load_from_file(
        cls: _t.Type[_Self],
        path: _t.Union[str, pathlib.Path],
        file_parser: _t.Callable[[str], _t.Any],
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _Self:
        if ignore_missing_file and not os.path.exists(path):
            return cls()

        try:
            with open(path, 'r') as file:
                loaded = file_parser(file.read())
        except Exception as e:
            raise yuio.parse.ParsingError(f'invalid config {path}: {e}') from None

        try:
            return cls.load_from_parsed_file(
                loaded, ignore_unknown_fields=ignore_unknown_fields)
        except yuio.parse.ParsingError as e:
            raise yuio.parse.ParsingError(f'invalid config {path}: {e}') from None

    @classmethod
    def load_from_parsed_file(
        cls: _t.Type[_Self],
        parsed: dict,
        /,
        *,
        ignore_unknown_fields: bool = False
    ) -> _Self:
        """Load config from parsed config file.

        This method takes a dict with arbitrary values that you'd get from
        parsing type-rich configs such as `yaml` or `json`.

        For example::

            with open('conf.yaml') as file:
                config = Config.load_from_parsed_file(yaml.load(file))

        """

        return cls.__load_from_parsed_file(parsed, ignore_unknown_fields, '')

    @classmethod
    def __load_from_parsed_file(
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
                if name not in cls.__get_fields():
                    raise yuio.parse.ParsingError(
                        f'unknown field {field_prefix}{name}')

        for name, field in cls.__get_fields().items():
            if name in parsed:
                if field.is_subconfig:
                    fields[name] = field.ty.__load_from_parsed_file(
                        parsed[name],
                        ignore_unknown_fields,
                        field_prefix=name + '.'
                    )
                else:
                    assert field.parser is not None
                    try:
                        value = field.parser.parse_config(parsed[name])
                    except yuio.parse.ParsingError as e:
                        raise yuio.parse.ParsingError(
                            f'can\'t parse {field_prefix}{name}: {e}') from None
                    fields[name] = value

        return cls(**fields)

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if value is MISSING:
            raise AttributeError(f'{item} is not configured')
        else:
            return value

    def __repr__(self):
        return self.__repr(0)

    def __repr(self, indent):
        field_reprs = []
        prefix = ' ' * indent
        for name in self.__get_fields():
            value = getattr(self, name, MISSING)
            if isinstance(value, Config):
                value_repr = value.__repr(indent + 2)
            else:
                value_repr = repr(value)
            field_reprs.append(f'{prefix}  {name}={value_repr}')
        if field_reprs:
            field_desc = ",\n".join(field_reprs)
            return f'{self.__class__.__name__}(\n{field_desc}\n{prefix})'
        else:
            return f'{self.__class__.__name__}()'
