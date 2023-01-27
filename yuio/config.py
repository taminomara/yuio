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

    # Update config with values from command line arguments.
    config.update(AppConfig.load_from_args())

.. autoclass:: Config
   :members:


Advanced field configuration
----------------------------

By default, :class:`Config` infers names for env variables and flags,
appropriate parsers, and other things from field's name and type hint.

If you need to override them, theres the :func:`field` function:

.. autofunction:: field

.. autofunction:: disabled


Parsing environment variables
-----------------------------

You can load config from environment through :meth:`~Config.load_from_env`.

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

To prefix all variable names with some string, pass the `prefix` parameter
to the :meth:`~Config.load_from_env` function::

        # config.kill_cmd.field will be loaded
        # from `MY_APP_KILL_CMD_SIGNAL`
        config = BigConfig.load_from_env('MY_APP')


Parsing CLI arguments
---------------------

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

import argparse
import os
import pathlib
import re
import logging
import textwrap
import typing as _t
from dataclasses import dataclass

import yuio.parse
from yuio._utils import DISABLED as _DISABLED, MISSING as _MISSING, Disabled as _Disabled, Missing as _Missing


T = _t.TypeVar('T')


#: Type of a :func:`disabled` placeholder.
Disabled = _Disabled


def disabled() -> Disabled:
    """Placeholder indicating that some field's functionality is disabled.

    """

    return _DISABLED


@dataclass(frozen=True)
class _FieldSettings:
    default: _t.Any = _MISSING
    parser: _t.Optional[yuio.parse.Parser] = None
    help: _t.Optional[_t.Union[str, Disabled]] = None
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

        help: _t.Union[str, Disabled]
        if self.help is not None:
            help = self.help
        elif parsed_help is not None:
            help = parsed_help
        elif is_subconfig and ty.__doc__:
            help = textwrap.dedent(ty.__doc__.strip())
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
        if self.flags is _DISABLED:
            flags = _DISABLED
        elif self.flags is None:
            flags = ['--' + name.replace('_', '-')]
        elif isinstance(self.flags, str):
            flags = [self.flags]
        else:
            if not self.flags:
                raise TypeError(
                    f'{qualname} should have at least one flag')
            flags = self.flags
        if flags is not _DISABLED:
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
            if default is not _MISSING:
                raise TypeError(
                    f'{qualname} cannot have defaults')

            if parser is not None:
                raise TypeError(
                    f'{qualname} cannot have parsers')

            if flags is not _DISABLED:
                if len(flags) > 1:
                    raise TypeError(
                        f'{qualname} cannot have multiple flags')

                if flags[0] and not flags[0].startswith('--'):
                    raise TypeError(
                        f'{qualname} cannot have a short flag ')
        elif parser is None:
            try:
                parser = yuio.parse.from_type_hint(ty)
            except TypeError as e:
                raise TypeError(
                    f'can\'t derive parser for {qualname}: {e}') from None

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
    help: _t.Union[str, Disabled]
    env: _t.Union[str, Disabled]
    flags: _t.Union[_t.List[str], Disabled]
    is_subconfig: bool
    ty: _t.Type
    required: bool


@_t.overload
def field(
    *,
    help: _t.Optional[_t.Union[str, Disabled]] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
) -> _t.Any: pass


@_t.overload
def field(
    default: _t.Union[T, _Missing] = _MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[_t.Union[str, Disabled]] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
) -> T: pass


@_t.overload
def field(
    default: None,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[_t.Union[str, Disabled]] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
) -> _t.Optional[T]: pass


def field(
    default: _t.Any = _MISSING,
    *,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Optional[_t.Union[str, Disabled]] = None,
    env: _t.Optional[_t.Union[str, Disabled]] = None,
    flags: _t.Optional[_t.Union[str, _t.List[str], Disabled]] = None,
) -> _t.Any:
    """Field descriptor, used for additional configuration of fields.

    :param default:
        default value for config field, used if field is missing from config.
    :param parser:
        parser that will be used to parse env vars, configs and CLI arguments.
    :param help:
        help message that will be used in CLI argument description.
    :param env:
        name of environment variable that will be used for this field.
    :param flags:
        list of names of CLI flags that will be used for this field.

    """

    return _FieldSettings(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flags=flags,
    )


def inline(
    help: _t.Optional[_t.Union[str, Disabled]] = None,
) -> _t.Any:
    """A shortcut for inlining nested configs.

    Equivalent to calling :func:`field` with ``env`` and ``flags``
    set to an empty string.

    """

    return field(help, env='', flags='')


def _parse_collection_action(parser: yuio.parse.Parser):
    class Action(argparse.Action):
        def __call__(self, _, namespace, values, option_string=None):
            assert values is not None and not isinstance(values, str)

            parsed = parser.parse_many(values)
            parser.validate(parsed)
            setattr(namespace, self.dest, parsed)

    return Action


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
    __fields: _t.ClassVar[_t.Optional[_t.Dict[str, _Field]]] = None

    @classmethod
    def __get_fields(cls) -> _t.Dict[str, _Field]:
        if cls.__fields is not None:
            return cls.__fields

        try:
            docs = yuio._utils.find_docs(cls)
        except Exception:
            logging.getLogger('yuio.internal').exception(
                'unable to get documentation for class %s',
                cls.__qualname__,
            )
            docs = {}

        fields = {}

        for base in reversed(cls.__mro__):
            if base is not cls and hasattr(base, '_Config__get_fields'):
                fields.update(getattr(base, '_Config__get_fields')())

        try:
            types = _t.get_type_hints(cls)
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

            value = cls.__dict__.get(name, _MISSING)
            if isinstance(value, _FieldSettings):
                field = value
            else:
                field = _FieldSettings(default=value)
            setattr(cls, name, field.default)

            fields[name] = field._update_defaults(
                f'{cls.__qualname__}.{name}', name, types[name], docs.get(name))

        cls.__fields = fields

        return fields

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.__fields = None

    __COMMENT_RE = re.compile(r'^\s*#: ?(.*)\r?\n?$')

    @classmethod
    def __find_docs(cls) -> _t.Dict[str, str]:
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
                    if match := cls.__COMMENT_RE.match(before_line):
                        comment_lines.append(match.group(1))
                    else:
                        break

                if comment_lines:
                    docs[stmt.target.id] = '\n'.join(reversed(comment_lines))

        return docs

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
                elif ns[name] is not _MISSING:
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
            if field.env is _DISABLED:
                continue

            if prefix and field.env:
                env = f'{prefix}_{field.env}'
            else:
                env = f'{prefix}{field.env}'

            if field.is_subconfig:
                fields[name] = field.ty.load_from_env(prefix=env)
            elif env in os.environ:
                assert field.parser is not None
                fields[name] = field.parser(os.environ[env])

        return cls(**fields)

    @classmethod
    def load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace,
        /,
        *,
        ns_prefix: str = '',
    ) -> _Self:
        """Load config from parsed command line arguments.

        This method assumes that arguments parser was configured
        with :meth:`Config.setup_arg_parser`.

        """

        return cls.__load_from_namespace(namespace, ns_prefix + ':')

    @classmethod
    def __load_from_namespace(
        cls: _t.Type[_Self],
        namespace: argparse.Namespace,
        prefix: str
    ) -> _Self:

        fields = {}

        for name, field in cls.__get_fields().items():
            if field.flags is _DISABLED:
                continue

            dest = prefix + name

            if field.is_subconfig:
                fields[name] = field.ty.__load_from_namespace(
                    namespace, dest + '.')
            elif hasattr(namespace, dest):
                fields[name] = getattr(namespace, dest)

        return cls(**fields)

    @classmethod
    def setup_arg_parser(
        cls,
        parser: argparse.ArgumentParser,
        /,
        *,
        ns_prefix: str = '',
    ):
        """Add fields from this config to the given arguments parser.

        :param ns_prefix:
            add this prefix to ``dest``s of all argparse actions.

        """

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
            if field.flags is _DISABLED:
                continue

            dest = dest_prefix + name

            if suppress_help or field.help is _DISABLED:
                help = argparse.SUPPRESS
                current_suppress_help = True
            else:
                help = field.help
                current_suppress_help = False
                if field.default is not _MISSING:
                    assert field.parser is not None
                    default = field.parser.describe_value_or_def(field.default)
                    help += f' [default: {default}]'

            if prefix:
                flags = [prefix + flag.lstrip('-') for flag in field.flags]
            else:
                flags = field.flags

            if field.is_subconfig:
                if current_suppress_help:
                    subgroup = group
                else:
                    lines = help.split('\n\n', 1)
                    title = lines[0].replace('\n', ' ').rstrip('.') or name
                    desc = lines[1] if len(lines) > 1 else None
                    subgroup = parser.add_argument_group(
                        title, desc)  # type: ignore
                field.ty.__setup_arg_parser(
                    subgroup, parser, flags[0], dest + '.', current_suppress_help)
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

                mutex_group.add_argument(
                    *flags,
                    type=field.parser,
                    default=_MISSING,
                    help=help,
                    metavar=metavar,
                    dest=dest,
                    nargs='?',
                    const=True,
                )

                for flag in field.flags:
                    if flag.startswith('--'):
                        flag_neg = (prefix or '--') + 'no-' + flag[2:]
                        if current_suppress_help:
                            help = argparse.SUPPRESS
                        else:
                            help = f'set {(prefix or "--") + flag[2:]} to `no`'
                        mutex_group.add_argument(
                            flag_neg,
                            default=_MISSING,
                            help=help,
                            dest=dest,
                            action='store_false',
                        )
                        break
            elif field.parser.supports_parse_many():
                group.add_argument(
                    *flags,
                    default=_MISSING,
                    help=help,
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
                    help=help,
                    metavar=metavar,
                    dest=dest,
                    required=field.required,
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
            import yaml
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

        This requires `toml <https://pypi.org/project/toml/>`_ package
        to be installed.

        """

        try:
            import toml
        except ImportError:
            raise ImportError('toml is not available')

        return cls.__load_from_file(
            path, toml.loads, ignore_unknown_fields, ignore_missing_file)

    @classmethod
    def __load_from_file(
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

        This method takes a dict with arbitrary values that resulted from
        parsing type-rich configs such as ``.yaml`` or ``.json``.

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
                        field.parser.validate(value)
                    except yuio.parse.ParsingError as e:
                        raise yuio.parse.ParsingError(
                            f'can\'t parse {field_prefix}{name}: {e}') from None
                    fields[name] = value

        return cls(**fields)

    def __getattribute__(self, item):
        value = super().__getattribute__(item)
        if value is _MISSING:
            raise AttributeError(f'{item} is not configured')
        else:
            return value

    def __repr__(self):
        return self.__repr(0)

    def __repr(self, indent):
        field_reprs = []
        prefix = ' ' * indent
        for name in self.__get_fields():
            value = getattr(self, name, _MISSING)
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
