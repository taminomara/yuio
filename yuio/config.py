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
define config fields using type annotations, just like :mod:`dataclasses`:

.. code-block:: python

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
    config = AppConfig.load_from_json_file("~/.my_app_cfg.json")

    # Update config with values from env.
    config.update(AppConfig.load_from_env())


Config base class
-----------------

.. autoclass:: Config


Advanced field configuration
----------------------------

By default, :class:`Config` infers names for env variables and flags,
appropriate parsers, and other things from field's name, type hint, and comments.

If you need to override them, you can use :func:`yuio.app.field`
and :func:`yuio.app.inline` functions (also available from ``yuio.config.field``
and ``yuio.config.inline``):

.. code-block:: python

    class AppConfig(Config):
        model: pathlib.Path | None = field(
            default=None,
            help="trained model to execute",
        )


Nesting configs
---------------

You can nest configs to achieve modularity:

.. code-block:: python

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
or a dict with its variables to the config's constructor:

.. code-block:: python

    # The following lines are equivalent:
    config = AppConfig(executor=ExecutorConfig(threads=16))
    config = AppConfig(executor={'threads': 16})
    # ...although type checkers will complain about dict =(


Parsing environment variables
-----------------------------

You can load config from environment through :meth:`~Config.load_from_env`.

Names of environment variables are just capitalized field names.
Use the :func:`yuio.app.field` function to override them:

.. code-block:: python

    class KillCmdConfig(Config):
        # Will be loaded from `SIGNAL`.
        signal: int

        # Will be loaded from `PROCESS_ID`.
        pid: int = field(env='PROCESS_ID')

In nested configs, environment variable names are prefixed with name
of a field that contains the nested config:

.. code-block:: python

    class BigConfig(Config):
        # `kill_cmd.signal` will be loaded from `KILL_CMD_SIGNAL`.
        kill_cmd: KillCmdConfig

        # `kill_cmd_2.signal` will be loaded from `KILL_SIGNAL`.
        kill_cmd_2: KillCmdConfig = field(env='KILL')

        # `kill_cmd_3.signal` will be loaded from `SIGNAL`.
        kill_cmd_3: KillCmdConfig = field(env='')

You can also disable loading a field from an environment altogether:

.. code-block:: python

    class KillCmdConfig(Config):
        # Will not be loaded from env.
        pid: int = field(env=yuio.DISABLED)

To prefix all variable names with some string, pass the `prefix` parameter
to the :meth:`~Config.load_from_env` function:

.. code-block:: python

    # config.kill_cmd.field will be loaded
    # from `MY_APP_KILL_CMD_SIGNAL`
    config = BigConfig.load_from_env('MY_APP')


Parsing config files
--------------------

You can load config from structured config files,
such as `json`, `yaml` or `toml`:

.. skip: next

.. code-block:: python

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


Additional config validation
----------------------------

If you have invariants that can't be captured with type system,
you can override :meth:`~Config.validate_config`. This method will be called
every time you load a config from file, arguments or environment:

.. code-block:: python

    class DocGenConfig(Config):
        categories: list[str] = ["quickstart", "api_reference"]
        category_names: dict[str, str] = {"deep_dive": "Deep Dive"}

        def validate_config(self):
            for category in self.category_names:
                if category not in self.categories:
                    raise yuio.parse.ParsingError(f"unknown category {category}")


Merging configs
---------------

Configs are specially designed to be merge-able. The basic pattern is to create
an empty config instance, then :meth:`~Config.update` it with every config source:

.. skip: next

.. code-block:: python

    config = AppConfig()
    config.update(AppConfig.load_from_json_file("~/.my_app_cfg.json"))
    config.update(AppConfig.load_from_env())
    # ...and so on.

The :meth:`~Config.update` function ignores default values, and only overrides
keys that were actually configured.

If you need a more complex update behavior, you can add a merge function for a field:

.. code-block:: python

    class AppConfig(Config):
        plugins: list[str] = field(
            default=[],
            merge=lambda left, right: [*left, *right],
        )

Here, whenever we :meth:`~Config.update` ``AppConfig``, ``plugins`` from both instances
will be concatenated.

.. warning::

    Merge function shouldn't mutate its arguments.
    It should produce a new value instead.

.. warning::

    Merge function will not be called for default value. It's advisable to keep the
    default value empty, and add the actual default to the initial empty config:

    .. skip: next

    .. code-block:: python

        config = AppConfig(plugins=["markdown", "rst"])
        config.update(...)

"""

import argparse
import json
import os
import pathlib
import textwrap
from dataclasses import dataclass

import yuio
import yuio.complete
import yuio.parse
from yuio import _typing as _t

T = _t.TypeVar("T")
Cfg = _t.TypeVar("Cfg", bound="Config")


@dataclass(frozen=True)
class _FieldSettings:
    default: _t.Any
    parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None
    help: _t.Union[str, yuio.Disabled, None] = None
    env: _t.Union[str, yuio.Disabled, None] = None
    flags: _t.Union[str, _t.List[str], yuio.Positional, yuio.Disabled, None] = None
    completer: _t.Optional[yuio.complete.Completer] = None
    required: bool = False
    merge: _t.Optional[_t.Callable[[_t.Any, _t.Any], _t.Any]] = None

    def _update_defaults(
        self,
        qualname: str,
        name: str,
        ty_with_extras: _t.Any,
        parsed_help: _t.Optional[str],
        allow_positionals: bool,
    ) -> "_Field":
        ty = ty_with_extras
        while _t.get_origin(ty) is _t.Annotated:
            ty = _t.get_args(ty)[0]
        is_subconfig = isinstance(ty, type) and issubclass(ty, Config)

        help: _t.Union[str, yuio.Disabled]
        if self.help is not None:
            help = self.help
        elif parsed_help is not None:
            help = parsed_help
        elif is_subconfig and ty.__doc__:
            help = ty.__doc__
        else:
            help = ""
        if help == argparse.SUPPRESS:
            help = yuio.DISABLED

        env: _t.Union[str, yuio.Disabled]
        if self.env is not None:
            env = self.env
        else:
            env = name.upper()
        if env == "" and not is_subconfig:
            raise TypeError(f"{qualname} got an empty env variable name")

        flags: _t.Union[_t.List[str], yuio.Positional, yuio.Disabled]
        if self.flags is yuio.DISABLED or self.flags is yuio.POSITIONAL:
            flags = self.flags
            if not allow_positionals and flags is yuio.POSITIONAL:
                raise TypeError(
                    f"{qualname}: positional arguments are not allowed in configs"
                )
        elif self.flags is None:
            flags = ["--" + name.replace("_", "-")]
        elif isinstance(self.flags, str):
            flags = [self.flags]
        else:
            if not self.flags:
                raise TypeError(f"{qualname} should have at least one flag")
            flags = self.flags
        if flags is not yuio.DISABLED and flags is not yuio.POSITIONAL:
            for flag in flags:
                if flag and not flag.startswith("-"):
                    raise TypeError(f"{qualname}: flag should start with a dash")
                if not flag and not is_subconfig:
                    raise TypeError(f"{qualname} got an empty flag")

        default = self.default

        parser = self.parser

        required = self.required

        if is_subconfig:
            if default is not yuio.MISSING:
                raise TypeError(
                    f"error in {qualname}: nested configs can't have defaults"
                )

            if parser is not None:
                raise TypeError(
                    f"error in {qualname}: nested configs can't have parsers"
                )

            if flags is not yuio.DISABLED:
                if flags is yuio.POSITIONAL:
                    raise TypeError(
                        f"error in {qualname}: nested configs can't be positional"
                    )
                if len(flags) > 1:
                    raise TypeError(
                        f"error in {qualname}: nested configs can't have multiple flags"
                    )
                if flags[0] and not flags[0].startswith("--"):
                    raise TypeError(
                        f"error in {qualname}: nested configs can't have a short flag"
                    )
        elif parser is None:
            try:
                parser = yuio.parse.from_type_hint(ty_with_extras)
            except TypeError as e:
                raise TypeError(
                    f"can't derive parser for {qualname}:\n"
                    + textwrap.indent(str(e), "  ")
                ) from None

        if parser is not None:
            origin = _t.get_origin(ty)
            args = _t.get_args(ty)

            is_optional = (
                default is None
                or _t.is_union(origin)
                and len(args) == 2
                and type(None) in args
            )

            if is_optional and not yuio.parse._is_optional_parser(parser):
                parser = yuio.parse.Optional(parser)

            if (
                flags is yuio.POSITIONAL
                and default is not yuio.MISSING
                and parser.supports_parse_many()
            ):
                raise TypeError(
                    f"{qualname}: positional multi-value arguments can't have defaults"
                )

        completer = self.completer

        merge = self.merge

        if is_subconfig and merge is not yuio.MISSING:
            if default is not yuio.MISSING:
                raise TypeError(f"error in {qualname}: nested configs can't have merge")

        return _Field(
            default,
            parser,
            help,
            env,
            flags,
            completer,
            is_subconfig,
            ty,
            required,
            merge,
        )


@dataclass(frozen=True)
class _Field:
    default: _t.Any
    parser: _t.Optional[yuio.parse.Parser[_t.Any]]
    help: _t.Union[str, yuio.Disabled]
    env: _t.Union[str, yuio.Disabled]
    flags: _t.Union[_t.List[str], yuio.Positional, yuio.Disabled]
    completer: _t.Optional[yuio.complete.Completer]
    is_subconfig: bool
    ty: type
    required: bool
    merge: _t.Optional[_t.Callable[[_t.Any, _t.Any], _t.Any]]


@_t.overload
def field(
    *,
    completer: _t.Optional[yuio.complete.Completer] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    flags: _t.Union[str, _t.List[str], yuio.Positional, yuio.Disabled, None] = None,
) -> _t.Any: ...


@_t.overload
def field(
    *,
    default: None,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    flags: _t.Union[str, _t.List[str], yuio.Positional, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
    merge: _t.Optional[_t.Callable[[T, T], T]] = None,
) -> _t.Optional[T]: ...


@_t.overload
def field(
    *,
    default: _t.Union[T, yuio.Missing] = yuio.MISSING,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    flags: _t.Union[str, _t.List[str], yuio.Positional, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
    merge: _t.Optional[_t.Callable[[T, T], T]] = None,
) -> T: ...


def field(
    *,
    default: _t.Any = yuio.MISSING,
    parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    flags: _t.Union[str, _t.List[str], yuio.Positional, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
    merge: _t.Optional[_t.Callable[[T, T], T]] = None,
) -> _t.Any:
    """Field descriptor, used for additional configuration of flags and config fields.

    In apps::

        @app
        def main(
            # Will be loaded from `--input`.
            input: pathlib.Path | None = None,

            # Will be loaded from `-o` or `--output`.
            output: pathlib.Path | None = field(default=None, flags=['-p', '--pid'])
        ):
            ...

    In configs::

        class AppConfig(Config):
            model: pathlib.Path | None = field(
                default=None,
                help="trained model to execute",
            )

    :param default:
        default value for the field or CLI argument.
    :param parser:
        parser that will be used to parse and CLI arguments.
    :param help:
        Help message that will be used in CLI argument description.

        Pass :data:`~yuio.DISABLED` to remove this field from CLI help.

        By default, help message is inferred from comments right above the field
        definition (comments must start with ``#:``).

        Help messages are formatted using Markdown (see :mod:`yuio.md`).
    :param env:
        In configs, specifies name of environment variable that will be used
        if loading config from environment variable.

        Pass :data:`~yuio.DISABLED` to disable loading this field form environment variable.

        Pass an empty string to disable prefixing nested config variables.
    :param flags:
        List of names (or a single name) of CLI flags that will be used for this field.

        In configs, pass :data:`~yuio.DISABLED` to disable loading this field form CLI arguments.

        In apps, pass :data:`~yuio.POSITIONAL` to make this argument positional.

        Pass an empty string to disable prefixing nested config flags.
    :param completer:
        completer that will be used for autocompletion in CLI.
    :param merge:
        defines how values of this field are merged when configs are updated.

    """

    return _FieldSettings(
        default=default,
        completer=completer,
        parser=parser,
        help=help,
        env=env,
        flags=flags,
        merge=merge,
    )


def inline(
    help: _t.Union[str, yuio.Disabled, None] = None,
) -> _t.Any:
    """A shortcut for inlining nested configs.

    Equivalent to calling :func:`~yuio.app.field` with ``env`` and ``flags``
    set to an empty string.

    """

    return field(help=help, env="", flags="")


@_t.overload
def positional(
    *,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
) -> _t.Any: ...


@_t.overload
def positional(
    *,
    default: None,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
) -> _t.Optional[T]: ...


@_t.overload
def positional(
    *,
    default: _t.Union[T, yuio.Missing] = yuio.MISSING,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
) -> T: ...


def positional(
    *,
    default: _t.Any = yuio.MISSING,
    parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None,
    help: _t.Union[str, yuio.Disabled, None] = None,
    env: _t.Union[str, yuio.Disabled, None] = None,
    completer: _t.Optional[yuio.complete.Completer] = None,
) -> _t.Any:
    """A shortcut for adding a positional argument.

    Equivalent to calling :func:`field` with ``flags`` set to :data:`~yuio.POSITIONAL`.

    """

    return field(
        default=default,
        parser=parser,
        help=help,
        env=env,
        flags=yuio.POSITIONAL,
        completer=completer,
    )


def _action(
    field: _Field,
    parse_many: bool,
):
    class Action(argparse.Action):
        @staticmethod
        def get_parser():
            return field.parser

        @staticmethod
        def get_completer():
            return field.completer

        @staticmethod
        def get_merge():
            return field.merge

        def __call__(self, _, namespace, values, option_string=None):
            try:
                if parse_many:
                    if values is yuio.MISSING:
                        values = []
                    assert values is not None and not isinstance(values, str)
                    assert field.parser
                    parsed = field.parser.parse_many(values)
                else:
                    if values is yuio.MISSING:
                        return
                    assert isinstance(values, str)
                    assert field.parser
                    parsed = field.parser.parse(values)
            except argparse.ArgumentTypeError as e:
                raise argparse.ArgumentError(self, str(e))
            # Note: merge will be executed in `namespace.__setattr__`,
            # see `yuio.app._Namespace`.
            setattr(namespace, self.dest, parsed)

    return Action


@_t.dataclass_transform(
    eq_default=False,
    order_default=False,
    kw_only_default=True,
    frozen_default=False,
    field_specifiers=(field, inline, positional),
)
class Config:
    """Base class for configs.

    Pass keyword args to set fields, or pass another config to copy it::

        Config(config1, config2, ..., field1=value1, ...)

    Upon creation, all fields that aren't explicitly initialized
    and don't have defaults are considered missing.
    Accessing them will raise :class:`AttributeError`.

    .. automethod:: update

    .. automethod:: load_from_env

    .. automethod:: load_from_json_file

    .. automethod:: load_from_yaml_file

    .. automethod:: load_from_toml_file

    .. automethod:: load_from_parsed_file

    .. automethod:: validate_config

    """

    _Self = _t.TypeVar("_Self", bound="Config")

    # Value is generated lazily by `__get_fields`.
    __allow_positionals: _t.ClassVar[bool] = False
    __fields: _t.ClassVar[_t.Optional[_t.Dict[str, _Field]]]

    @classmethod
    def __get_fields(cls) -> _t.Dict[str, _Field]:
        if cls.__fields is not None:
            return cls.__fields

        try:
            docs = yuio._find_docs(cls)
        except Exception:
            yuio._logger.exception(
                "unable to get documentation for class %s",
                cls.__qualname__,
            )
            docs = {}

        fields = {}
        defaults = {}

        for base in reversed(cls.__mro__):
            if base is not cls and hasattr(base, "_Config__get_fields"):
                fields.update(getattr(base, "_Config__get_fields")())

        try:
            types = _t.get_type_hints(cls, include_extras=True)
        except NameError as e:
            if "<locals>" in cls.__qualname__:
                raise NameError(
                    f"{e}. "
                    f"Note: forward references do not work inside functions "
                    f"(see https://github.com/python/typing/issues/797)"
                ) from None
            raise

        for name in cls.__annotations__:
            if name.startswith("_"):
                continue

            value = cls.__dict__.get(name, yuio.MISSING)
            if isinstance(value, _FieldSettings):
                field = value
            else:
                field = _FieldSettings(default=value)

            defaults[name] = field.default
            fields[name] = field._update_defaults(
                f"{cls.__qualname__}.{name}",
                name,
                types[name],
                docs.get(name),
                cls.__allow_positionals,
            )

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

    def __init__(self: _Self, *args: _Self, **kwargs):
        for name, field in self.__get_fields().items():
            if field.is_subconfig:
                setattr(self, name, field.ty())

        for arg in args:
            self.update(arg)

        self.update(kwargs)

    def update(self: _Self, other: _t.Union[_Self, _t.Dict[str, _t.Any]], /):
        """Update fields in this config with fields from another config.

        This function is similar to :meth:`dict.update`.

        Nested configs are updated recursively.

        :param other:
            data for update.

        """

        if not other:
            return

        if isinstance(other, Config):
            if (
                self.__class__ not in other.__class__.__mro__
                and other.__class__ not in self.__class__.__mro__
            ):
                raise TypeError("updating from an incompatible config")
            ns = other.__dict__
        elif isinstance(other, dict):
            ns = other
            for name in ns:
                if name not in self.__get_fields():
                    raise TypeError(f"unknown field: {name}")
        else:
            raise TypeError("expected a dict or a config class")

        for name, field in self.__get_fields().items():
            if name in ns:
                if field.is_subconfig:
                    getattr(self, name).update(ns[name])
                elif ns[name] is not yuio.MISSING:
                    if field.merge is not None and name in self.__dict__:
                        setattr(self, name, field.merge(getattr(self, name), ns[name]))
                    else:
                        setattr(self, name, ns[name])

    @classmethod
    def load_from_env(cls: _t.Type[_Self], prefix: str = "") -> _Self:
        """
        Load config from environment variables.

        :param prefix:
            if given, names of all environment variables will be prefixed with
            this string and an underscore.

        """

        try:
            result = cls.__load_from_env(prefix)
            result.validate_config()
            return result
        except yuio.parse.ParsingError as e:
            raise yuio.parse.ParsingError(
                f"failed to load config from environment variables:\n"
                + textwrap.indent(str(e), "  ")
            ) from None

    @classmethod
    def __load_from_env(cls: _t.Type[_Self], prefix: str = "") -> _Self:

        fields = {}

        for name, field in cls.__get_fields().items():
            if field.env is yuio.DISABLED:
                continue

            if prefix and field.env:
                env = f"{prefix}_{field.env}"
            else:
                env = f"{prefix}{field.env}"

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
        ns_prefix: str = "",
    ) -> _Self:
        result = cls.__load_from_namespace(namespace, ns_prefix + ":")
        result.validate_config()
        return result

    @classmethod
    def __load_from_namespace(
        cls: _t.Type[_Self], namespace: argparse.Namespace, prefix: str
    ) -> _Self:
        fields = {}

        for name, field in cls.__get_fields().items():
            if field.flags is yuio.DISABLED:
                continue

            dest = prefix + name

            if field.is_subconfig:
                fields[name] = field.ty.__load_from_namespace(namespace, dest + ".")
            elif hasattr(namespace, dest):
                fields[name] = getattr(namespace, dest)

        return cls(**fields)

    @classmethod
    def _setup_arg_parser(
        cls,
        parser: argparse.ArgumentParser,
        /,
        *,
        group: _t.Optional[argparse.ArgumentParser] = None,
        ns_prefix: str = "",
    ):
        group = group or parser
        cls.__setup_arg_parser(group, parser, "", ns_prefix + ":", False)

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
            prefix += "-"

        for name, field in cls.__get_fields().items():
            if field.flags is yuio.DISABLED:
                continue

            dest = dest_prefix + name

            if suppress_help or field.help is yuio.DISABLED:
                help = argparse.SUPPRESS
                current_suppress_help = True
            else:
                help = field.help
                current_suppress_help = False

            flags: _t.Union[_t.List[str], yuio.Positional]
            if prefix and field.flags is not yuio.POSITIONAL:
                flags = [prefix + flag.lstrip("-") for flag in field.flags]
            else:
                flags = field.flags

            if field.is_subconfig:
                assert flags is not yuio.POSITIONAL
                if current_suppress_help:
                    subgroup = group
                else:
                    lines = help.split("\n\n", 1)
                    title = lines[0].replace("\n", " ").rstrip(".") or name
                    desc = textwrap.dedent(lines[1]) if len(lines) > 1 else None
                    subgroup = parser.add_argument_group(title, desc)
                field.ty.__setup_arg_parser(
                    subgroup, parser, flags[0], dest + ".", current_suppress_help
                )
                continue
            else:
                assert field.parser is not None

            parse_many = field.parser.supports_parse_many()

            action = _action(field, parse_many)

            if flags is yuio.POSITIONAL:
                metavar = f"<{name.replace('_', '-')}>"
            elif parse_many:
                metavar = field.parser.describe_many_or_def()
            else:
                metavar = field.parser.describe_or_def()

            nargs = field.parser.get_nargs()
            if (
                flags is yuio.POSITIONAL
                and field.default is not yuio.MISSING
                and nargs is None
            ):
                nargs = "?"
            nargs_kw: _t.Any = {"nargs": nargs} if nargs is not None else {}

            if flags is yuio.POSITIONAL:
                group.add_argument(
                    dest,
                    default=yuio.MISSING,
                    help=help,
                    metavar=metavar,
                    action=action,
                    **nargs_kw,
                )
            elif isinstance(field.parser, yuio.parse.Bool):
                mutex_group = group.add_mutually_exclusive_group(
                    required=field.required
                )

                mutex_group.add_argument(
                    *flags,
                    default=yuio.MISSING,
                    help=help,
                    dest=dest,
                    action="store_true",
                )

                assert field.flags is not yuio.POSITIONAL
                for flag in field.flags:
                    if flag.startswith("--"):
                        flag_neg = (prefix or "--") + "no-" + flag[2:]
                        if current_suppress_help:
                            help = argparse.SUPPRESS
                        else:
                            help = f'disable <c hl/flag:sh-usage>{(prefix or "--") + flag[2:]}</c>'
                        mutex_group.add_argument(
                            flag_neg,
                            default=yuio.MISSING,
                            help=help,
                            dest=dest,
                            action="store_false",
                        )
                        break
            else:
                group.add_argument(
                    *flags,
                    default=yuio.MISSING,
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
        """
        Load config from a ``.json`` file.

        :param path:
            path of the config file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param ignore_missing_file:
            if :data:`True`, silently ignore a file missing error. This is useful
            when loading a config from a home directory.

        """

        return cls.__load_from_file(
            path, json.loads, ignore_unknown_fields, ignore_missing_file
        )

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

        :param path:
            path of the config file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param ignore_missing_file:
            if :data:`True`, silently ignore a file missing error. This is useful
            when loading a config from a home directory.

        """

        try:
            import yaml
        except ImportError:
            raise ImportError("PyYaml is not available")

        return cls.__load_from_file(
            path, yaml.safe_load, ignore_unknown_fields, ignore_missing_file
        )

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

        :param path:
            path of the config file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param ignore_missing_file:
            if :data:`True`, silently ignore a file missing error. This is useful
            when loading a config from a home directory.

        """

        try:
            import toml
        except ImportError:
            try:
                import tomllib as toml
            except ImportError:
                raise ImportError("toml is not available")

        return cls.__load_from_file(
            path, toml.loads, ignore_unknown_fields, ignore_missing_file
        )

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
            with open(path, "r") as file:
                loaded = file_parser(file.read())
        except Exception as e:
            raise yuio.parse.ParsingError(
                f"invalid config {path}:\n" + textwrap.indent(str(e), "  ")
            ) from None

        return cls.load_from_parsed_file(
            loaded, ignore_unknown_fields=ignore_unknown_fields, path=path
        )

    @classmethod
    def load_from_parsed_file(
        cls: _t.Type[_Self],
        parsed: _t.Dict[str, object],
        /,
        *,
        ignore_unknown_fields: bool = False,
        path: _t.Union[str, pathlib.Path, None] = None,
    ) -> _Self:
        """Load config from parsed config file.

        This method takes a dict with arbitrary values that you'd get from
        parsing type-rich configs such as ``yaml`` or ``json``.

        For example::

            with open('conf.yaml') as file:
                config = Config.load_from_parsed_file(yaml.load(file))

        :param parsed:
            data from parsed file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param path:
            path of the original file, used for error reporting.

        """

        try:
            result = cls.__load_from_parsed_file(parsed, ignore_unknown_fields, "")
            result.validate_config()
            return result
        except yuio.parse.ParsingError as e:
            if path is None:
                raise
            else:
                raise yuio.parse.ParsingError(
                    f"invalid config {path}:\n" + textwrap.indent(str(e), "  ")
                ) from None

    @classmethod
    def __load_from_parsed_file(
        cls: _t.Type[_Self],
        parsed: _t.Dict[str, object],
        ignore_unknown_fields: bool = False,
        field_prefix: str = "",
    ) -> _Self:
        if not isinstance(parsed, dict):
            raise TypeError("config should be a dict")

        fields = {}

        if not ignore_unknown_fields:
            for name in parsed:
                if name not in cls.__get_fields():
                    raise yuio.parse.ParsingError(f"unknown field {field_prefix}{name}")

        for name, field in cls.__get_fields().items():
            if name in parsed:
                if field.is_subconfig:
                    fields[name] = field.ty.__load_from_parsed_file(
                        parsed[name], ignore_unknown_fields, field_prefix=name + "."
                    )
                else:
                    assert field.parser is not None
                    try:
                        value = field.parser.parse_config(parsed[name])
                    except yuio.parse.ParsingError as e:
                        raise yuio.parse.ParsingError(
                            f"can't parse {field_prefix}{name}:\n"
                            + textwrap.indent(str(e), "  ")
                        ) from None
                    fields[name] = value

        return cls(**fields)

    def __getattribute(self, item):
        value = super().__getattribute__(item)
        if value is yuio.MISSING:
            raise AttributeError(f"{item} is not configured")
        else:
            return value

    # A dirty hack to hide __getattribute__ from type checkers.
    locals()["__getattribute__"] = __getattribute

    def __repr__(self):
        return self.__repr(0)

    def __repr(self, indent):
        field_reprs = []
        prefix = " " * indent
        for name in self.__get_fields():
            value = getattr(self, name, yuio.MISSING)
            if isinstance(value, Config):
                value_repr = value.__repr(indent + 2)
            else:
                value_repr = repr(value)
            field_reprs.append(f"{prefix}  {name}={value_repr}")
        if field_reprs:
            field_desc = ",\n".join(field_reprs)
            return f"{self.__class__.__name__}(\n{field_desc}\n{prefix})"
        else:
            return f"{self.__class__.__name__}()"

    def validate_config(self):
        """
        Perform config validation.

        This function is called every time a config is loaded from CLI arguments,
        file, or environment variables. It should check that config is correct,
        and raise :class:`yuio.parse.ParsingError` if it's not.

        """


Config.__init_subclass__()


class ConfigParser(yuio.parse.ValueParser[Cfg], _t.Generic[Cfg]):
    if _t.TYPE_CHECKING:

        def __new__(cls, config: _t.Type[Cfg]) -> "ConfigParser[Cfg]": ...

    def __init__(self, config: _t.Type[Cfg]):
        self.__config = config
        super().__init__()

    def parse(self, value: str) -> Cfg:
        try:
            config_value = json.loads(value)
        except json.JSONDecodeError as e:
            raise yuio.parse.ParsingError(
                f"unable to decode JSON:\n" + textwrap.indent(str(e), "  ")
            ) from None
        return self.parse_config(config_value)

    def parse_config(self, value: object) -> Cfg:
        if isinstance(value, dict):
            return self.__config.load_from_parsed_file(value)
        else:
            raise yuio.parse.ParsingError(
                f"expected a dict, got {type(value).__name__} instead"
            )


yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: (
        ConfigParser(ty) if isinstance(ty, type) and issubclass(ty, Config) else None
    )
)
