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
        #: Trained model to execute.
        model: pathlib.Path

        #: Input data for the model.
        data: pathlib.Path

        #: Enable or disable gpu.
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
and :func:`yuio.app.inline` functions (also available from :mod:`yuio.config`):

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
        #: Number of threads to use.
        threads: int

        #: Enable or disable gpu.
        use_gpu: bool = True


    class AppConfig(Config):
        #: Executor parameters.
        executor: ExecutorConfig

        #: Trained model to execute.
        model: pathlib.Path

To initialise a nested config, pass either an instance of if
or a dict with its variables to the config's constructor:

.. code-block:: python

    # The following lines are equivalent:
    config = AppConfig(executor=ExecutorConfig(threads=16))
    config = AppConfig(executor={"threads": 16})
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
        pid: int = field(env="PROCESS_ID")

In nested configs, environment variable names are prefixed with name
of a field that contains the nested config:

.. code-block:: python

    class BigConfig(Config):
        # `kill_cmd.signal` will be loaded from `KILL_CMD_SIGNAL`.
        kill_cmd: KillCmdConfig

        # `kill_cmd_2.signal` will be loaded from `KILL_SIGNAL`.
        kill_cmd_2: KillCmdConfig = field(env="KILL")

        # `kill_cmd_3.signal` will be loaded from `SIGNAL`.
        kill_cmd_3: KillCmdConfig = field(env="")

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
    config = BigConfig.load_from_env("MY_APP")


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


    config = AppConfig.load_from_json_file("~/.my_app_cfg.json")

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


Re-imports
----------


.. function:: field
    :no-index:

    Alias of :obj:`yuio.app.field`

.. function:: inline
    :no-index:

    Alias of :obj:`yuio.app.inline`

.. function:: positional
    :no-index:

    Alias of :obj:`yuio.app.positional`

.. function:: bool_option
    :no-index:

    Alias of :obj:`yuio.app.bool_option`

.. function:: count_option
    :no-index:

    Alias of :obj:`yuio.app.count_option`

.. function:: parse_many_option
    :no-index:

    Alias of :obj:`yuio.app.parse_many_option`

.. function:: parse_one_option
    :no-index:

    Alias of :obj:`yuio.app.parse_one_option`

.. function:: store_const_option
    :no-index:

    Alias of :obj:`yuio.app.store_const_option`

.. function:: store_false_option
    :no-index:

    Alias of :obj:`yuio.app.store_false_option`

.. function:: store_true_option
    :no-index:

    Alias of :obj:`yuio.app.store_true_option`

.. type:: HelpGroup
    :no-index:

    Alias of :obj:`yuio.cli.HelpGroup`.

.. type:: MutuallyExclusiveGroup
    :no-index:

    Alias of :obj:`yuio.cli.MutuallyExclusiveGroup`.

.. type:: OptionCtor
    :no-index:

    Alias of :obj:`yuio.app.OptionCtor`.

.. type:: OptionSettings
    :no-index:

    Alias of :obj:`yuio.app.OptionSettings`.

.. data:: MISC_GROUP
    :no-index:

    Alias of :obj:`yuio.cli.MISC_GROUP`.

.. data:: OPTS_GROUP
    :no-index:

    Alias of :obj:`yuio.cli.OPTS_GROUP`.

.. data:: SUBCOMMANDS_GROUP
    :no-index:

    Alias of :obj:`yuio.cli.SUBCOMMANDS_GROUP`.

"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import textwrap
import types
from dataclasses import dataclass

import yuio
import yuio.cli
import yuio.complete
import yuio.json_schema
import yuio.parse
import yuio.string
from yuio.cli import (
    MISC_GROUP,
    OPTS_GROUP,
    SUBCOMMANDS_GROUP,
    HelpGroup,
    MutuallyExclusiveGroup,
)
from yuio.util import find_docs as _find_docs

import yuio._typing_ext as _tx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "MISC_GROUP",
    "OPTS_GROUP",
    "SUBCOMMANDS_GROUP",
    "Config",
    "HelpGroup",
    "MutuallyExclusiveGroup",
    "OptionCtor",
    "OptionSettings",
    "bool_option",
    "collect_option",
    "count_option",
    "field",
    "inline",
    "parse_many_option",
    "parse_one_option",
    "positional",
    "store_const_option",
    "store_false_option",
    "store_true_option",
]

T = _t.TypeVar("T")
Cfg = _t.TypeVar("Cfg", bound="Config")


@dataclass(frozen=True, slots=True)
class _FieldSettings:
    default: _t.Any
    parser: yuio.parse.Parser[_t.Any] | None = None
    env: str | yuio.Disabled | None = None
    flags: str | list[str] | yuio.Positional | yuio.Disabled | None = None
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING
    required: bool | None = None
    merge: _t.Callable[[_t.Any, _t.Any], _t.Any] | None = None
    mutex_group: MutuallyExclusiveGroup | None = None
    option_ctor: _t.Callable[[OptionSettings], yuio.cli.Option[_t.Any]] | None = None
    help: str | yuio.Disabled | None = None
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing = yuio.MISSING
    metavar: str | None = None
    usage: yuio.Collapse | bool | None = None
    default_desc: str | None = None
    show_if_inherited: bool | None = None

    def _update_defaults(
        self,
        qualname: str,
        name: str,
        ty_with_extras: _t.Any,
        parsed_help: str | None,
        allow_positionals: bool,
        cut_help: bool,
    ) -> _Field:
        ty = ty_with_extras
        while _t.get_origin(ty) is _t.Annotated:
            ty = _t.get_args(ty)[0]
        is_subconfig = isinstance(ty, type) and issubclass(ty, Config)

        env: str | yuio.Disabled
        if self.env is not None:
            env = self.env
        else:
            env = name.upper()
        if env == "" and not is_subconfig:
            raise TypeError(f"{qualname} got an empty env variable name")

        flags: list[str] | yuio.Positional | yuio.Disabled
        if self.flags is yuio.DISABLED:
            flags = self.flags
        elif self.flags is yuio.POSITIONAL:
            if not allow_positionals:
                raise TypeError(
                    f"{qualname}: positional arguments are not allowed in configs"
                )
            if is_subconfig:
                raise TypeError(
                    f"error in {qualname}: nested configs can't be positional"
                )
            flags = self.flags
        elif self.flags is None:
            flags = ["--" + name.replace("_", "-")]
        else:
            if isinstance(self.flags, str):
                if "," in self.flags:
                    flags = [
                        norm_flag
                        for flag in self.flags.split(",")
                        if (norm_flag := flag.strip())
                    ]
                else:
                    flags = self.flags.split()
                if not flags:
                    flags = [""]
            else:
                flags = self.flags

            if is_subconfig:
                if not flags:
                    raise TypeError(
                        f"error in {qualname}: nested configs should have exactly one flag; "
                        "to disable prefixing, pass an empty string as a flag"
                    )
                if len(flags) > 1:
                    raise TypeError(
                        f"error in {qualname}: nested configs can't have multiple flags"
                    )
                if flags[0]:
                    if not flags[0].startswith("--"):
                        raise TypeError(
                            f"error in {qualname}: nested configs can't have a short flag"
                        )
                    try:
                        yuio.cli._check_flag(flags[0])
                    except TypeError as e:
                        raise TypeError(f"error in {qualname}: {e}") from None
            else:
                if not flags:
                    raise TypeError(f"{qualname} should have at least one flag")
                for flag in flags:
                    try:
                        yuio.cli._check_flag(flag)
                    except TypeError as e:
                        raise TypeError(f"error in {qualname}: {e}") from None

        default = self.default
        if is_subconfig and default is not yuio.MISSING:
            raise TypeError(f"error in {qualname}: nested configs can't have defaults")

        parser = self.parser
        if is_subconfig and parser is not None:
            raise TypeError(f"error in {qualname}: nested configs can't have parsers")
        elif not is_subconfig and parser is None:
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
                default is None or _tx.is_union(origin) and types.NoneType in args
            )
            if is_optional and not yuio.parse._is_optional_parser(parser):
                parser = yuio.parse.Optional(parser)
            completer = self.completer
            metavar = self.metavar
            if not metavar and flags is yuio.POSITIONAL:
                metavar = f"<{name.replace('_', '-')}>"
            if completer is not None or metavar is not None:
                parser = yuio.parse.WithMeta(parser, desc=metavar, completer=completer)

        required = self.required
        if is_subconfig and required:
            raise TypeError(f"error in {qualname}: nested configs can't be required")
        if required is None:
            if is_subconfig:
                required = False
            elif allow_positionals:
                required = default is yuio.MISSING
            else:
                required = False

        merge = self.merge
        if is_subconfig and merge is not None:
            raise TypeError(
                f"error in {qualname}: nested configs can't have merge function"
            )

        mutex_group = self.mutex_group
        if is_subconfig and mutex_group is not None:
            raise TypeError(
                f"error in {qualname}: nested configs can't be a part "
                "of a mutually exclusive group"
            )
        if flags is yuio.POSITIONAL and mutex_group is not None:
            raise TypeError(
                f"error in {qualname}: positional arguments can't appear in mutually exclusive groups"
            )

        option_ctor = self.option_ctor
        if option_ctor is not None and is_subconfig:
            raise TypeError(
                f"error in {qualname}: nested configs can't have option constructors"
            )

        help: str | yuio.Disabled
        if self.help is not None:
            help = self.help
            full_help = help or ""
        elif parsed_help is not None:
            help = full_help = parsed_help
            if cut_help and (index := help.find("\n\n")) != -1:
                help = help[:index]
        else:
            help = full_help = ""

        help_group = self.help_group
        if help_group is yuio.COLLAPSE and not is_subconfig:
            raise TypeError(
                f"error in {qualname}: help_group=yuio.COLLAPSE only allowed for nested configs"
            )

        usage = self.usage

        default_desc = self.default_desc

        show_if_inherited = self.show_if_inherited

        return _Field(
            name=name,
            qualname=qualname,
            default=default,
            parser=parser,
            env=env,
            flags=flags,
            is_subconfig=is_subconfig,
            ty=ty,
            required=required,
            merge=merge,
            mutex_group=mutex_group,
            option_ctor=option_ctor,
            help=help,
            full_help=full_help,
            help_group=help_group,
            usage=usage,
            default_desc=default_desc,
            show_if_inherited=show_if_inherited,
        )


@dataclass(frozen=True, slots=True)
class _Field:
    name: str
    qualname: str
    default: _t.Any
    parser: yuio.parse.Parser[_t.Any] | None
    env: str | yuio.Disabled
    flags: list[str] | yuio.Positional | yuio.Disabled
    is_subconfig: bool
    ty: type
    required: bool
    merge: _t.Callable[[_t.Any, _t.Any], _t.Any] | None
    mutex_group: MutuallyExclusiveGroup | None
    option_ctor: _t.Callable[[OptionSettings], yuio.cli.Option[_t.Any]] | None
    help: str | yuio.Disabled
    full_help: str
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing
    usage: yuio.Collapse | bool | None
    default_desc: str | None
    show_if_inherited: bool | None


@_t.overload
def field(
    *,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    env: str | yuio.Disabled | None = None,
    flags: str | list[str] | yuio.Positional | yuio.Disabled | None = None,
    required: bool | None = None,
    mutex_group: MutuallyExclusiveGroup | None = None,
    help: str | yuio.Disabled | None = None,
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing = yuio.MISSING,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
    show_if_inherited: bool | None = None,
) -> _t.Any: ...
@_t.overload
def field(
    *,
    default: None,
    parser: yuio.parse.Parser[T] | None = None,
    env: str | yuio.Disabled | None = None,
    flags: str | list[str] | yuio.Positional | yuio.Disabled | None = None,
    required: bool | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    merge: _t.Callable[[T, T], T] | None = None,
    mutex_group: MutuallyExclusiveGroup | None = None,
    option_ctor: OptionCtor[T] | None = None,
    help: str | yuio.Disabled | None = None,
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing = yuio.MISSING,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
    show_if_inherited: bool | None = None,
) -> T | None: ...
@_t.overload
def field(
    *,
    default: T | yuio.Missing = yuio.MISSING,
    parser: yuio.parse.Parser[T] | None = None,
    env: str | yuio.Disabled | None = None,
    flags: str | list[str] | yuio.Positional | yuio.Disabled | None = None,
    required: bool | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    merge: _t.Callable[[T, T], T] | None = None,
    mutex_group: MutuallyExclusiveGroup | None = None,
    option_ctor: OptionCtor[T] | None = None,
    help: str | yuio.Disabled | None = None,
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing = yuio.MISSING,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
    show_if_inherited: bool | None = None,
) -> T: ...
def field(
    *,
    default: _t.Any = yuio.MISSING,
    parser: yuio.parse.Parser[_t.Any] | None = None,
    env: str | yuio.Disabled | None = None,
    flags: str | list[str] | yuio.Positional | yuio.Disabled | None = None,
    required: bool | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    merge: _t.Callable[[_t.Any, _t.Any], _t.Any] | None = None,
    mutex_group: MutuallyExclusiveGroup | None = None,
    option_ctor: _t.Callable[..., _t.Any] | None = None,
    help: str | yuio.Disabled | None = None,
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing = yuio.MISSING,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
    show_if_inherited: bool | None = None,
) -> _t.Any:
    """
    Field descriptor, used for additional configuration of CLI options
    and config fields.

    :param default:
        default value for the field or CLI option.
    :param parser:
        parser that will be used to parse config values and CLI options.
    :param env:
        specifies name of environment variable that will be used if loading config
        from environment.

        Pass :data:`~yuio.DISABLED` to disable loading this field form environment.

        In sub-config fields, controls prefix for all environment variables within
        this sub-config; pass an empty string to disable prefixing.
    :param flags:
        list of names (or a single name) of CLI flags that will be used for this field.

        In configs, pass :data:`~yuio.DISABLED` to disable loading this field form CLI arguments.

        In apps, pass :data:`~yuio.POSITIONAL` to make this argument positional.

        In sub-config fields, controls prefix for all flags withing this sub-config;
        pass an empty string to disable prefixing.
    :param completer:
        completer that will be used for autocompletion in CLI. Using this option
        is equivalent to overriding `completer` with :class:`yuio.parse.WithMeta`.
    :param merge:
        defines how values of this field are merged when configs are updated.
    :param mutex_group:
        defines mutually exclusive group for this field.
    :param option_ctor:
        this parameter is similar to :mod:`argparse`\\ 's ``action``: it allows
        overriding logic for handling CLI arguments by providing a custom
        :class:`~yuio.cli.Option` implementation.

        `option_ctor` should be a callable which takes a single positional argument
        of type :class:`~yuio.app.OptionSettings`, and returns an instance
        of :class:`yuio.cli.Option`.
    :param help:
        help message that will be used in CLI option description,
        formatted using RST or Markdown
        (see :attr:`App.doc_format <yuio.app.App.doc_format>`).

        Pass :data:`yuio.DISABLED` to remove this field from CLI help.
    :param help_group:
        overrides group in which this field will be placed when generating CLI help
        message.

        Pass :class:`yuio.COLLAPSE` to create a collapsed group.
    :param metavar:
        value description that will be used for CLI help messages. Using this option
        is equivalent to overriding `desc` with :class:`yuio.parse.WithMeta`.
    :param usage:
        controls how this field renders in CLI usage section.

        Pass :data:`False` to remove this field from usage.

        Pass :class:`yuio.COLLAPSE` to omit this field and add a single string
        ``<options>`` instead.

        Setting `usage` on sub-config fields overrides default `usage` for all
        fields within this sub-config.
    :param default_desc:
        overrides description for default value in CLI help message.

        Pass an empty string to hide default value.
    :param show_if_inherited:
        for fields with flags, enables showing this field in CLI help message
        for subcommands.
    :returns:
        a magic object that will be replaced with field's default value once a new
        config class is created.
    :example:
        In apps:

        .. invisible-code-block: python

            import yuio.app

        .. code-block:: python

            @yuio.app.app
            def main(
                # Will be loaded from `--input`.
                input: pathlib.Path | None = None,
                # Will be loaded from `-o` or `--output`.
                output: pathlib.Path | None = field(
                    default=None, flags=["-o", "--output"]
                ),
            ): ...

        In configs:

        .. code-block:: python

            class AppConfig(Config):
                model: pathlib.Path | None = field(
                    default=None,
                    help="trained model to execute",
                )

    """

    return _FieldSettings(
        default=default,
        parser=parser,
        env=env,
        flags=flags,
        completer=completer,
        required=required,
        merge=merge,
        mutex_group=mutex_group,
        option_ctor=option_ctor,
        help=help,
        help_group=help_group,
        metavar=metavar,
        usage=usage,
        default_desc=default_desc,
        show_if_inherited=show_if_inherited,
    )


def inline(
    help: str | yuio.Disabled | None = None,
    help_group: HelpGroup | yuio.Collapse | None | yuio.Missing = yuio.MISSING,
    usage: yuio.Collapse | bool | None = None,
    show_if_inherited: bool | None = None,
) -> _t.Any:
    """
    A shortcut for inlining nested configs.

    Equivalent to calling :func:`~yuio.app.field` with `env` and `flags`
    set to an empty string.

    """

    return field(
        env="",
        flags="",
        help=help,
        help_group=help_group,
        usage=usage,
        show_if_inherited=show_if_inherited,
    )


@_t.overload
def positional(
    *,
    env: str | yuio.Disabled | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    help: str | yuio.Disabled | None = None,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
) -> _t.Any: ...
@_t.overload
def positional(
    *,
    default: None,
    parser: yuio.parse.Parser[T] | None = None,
    env: str | yuio.Disabled | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    help: str | yuio.Disabled | None = None,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
) -> T | None: ...
@_t.overload
def positional(
    *,
    default: T | yuio.Missing = yuio.MISSING,
    parser: yuio.parse.Parser[T] | None = None,
    env: str | yuio.Disabled | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    help: str | yuio.Disabled | None = None,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
) -> T: ...
def positional(
    *,
    default: _t.Any = yuio.MISSING,
    parser: yuio.parse.Parser[_t.Any] | None = None,
    env: str | yuio.Disabled | None = None,
    completer: yuio.complete.Completer | None | yuio.Missing = yuio.MISSING,
    help: str | yuio.Disabled | None = None,
    metavar: str | None = None,
    usage: yuio.Collapse | bool | None = None,
    default_desc: str | None = None,
) -> _t.Any:
    """
    A shortcut for adding a positional argument.

    Equivalent to calling :func:`field` with `flags` set to :data:`~yuio.POSITIONAL`.

    """

    return field(
        default=default,
        parser=parser,
        env=env,
        flags=yuio.POSITIONAL,
        completer=completer,
        help=help,
        metavar=metavar,
        usage=usage,
        default_desc=default_desc,
    )


@_t.dataclass_transform(
    eq_default=False,
    order_default=False,
    kw_only_default=True,
    frozen_default=False,
    field_specifiers=(field, inline, positional),
)
class Config:
    """
    Base class for configs.

    Pass keyword args to set fields, or pass another config to copy it::

        Config(config1, config2, ..., field1=value1, ...)

    Upon creation, all fields that aren't explicitly initialized
    and don't have defaults are considered missing.
    Accessing them will raise :class:`AttributeError`.

    .. note::

        Unlike dataclasses, Yuio does not provide an option to create new instances
        of default values upon config instantiation. This is done so that default
        values don't override non-default ones when you update one config from another.

    .. automethod:: update

    .. automethod:: load_from_env

    .. automethod:: load_from_json_file

    .. automethod:: load_from_yaml_file

    .. automethod:: load_from_toml_file

    .. automethod:: load_from_parsed_file

    .. automethod:: to_json_schema

    .. automethod:: to_json_value

    """

    @classmethod
    def __get_fields(cls) -> dict[str, _Field]:
        if cls.__fields is not None:
            return cls.__fields

        docs = getattr(cls, "__yuio_pre_parsed_docs__", None)
        if docs is None:
            try:
                docs = _find_docs(cls)
            except Exception:
                yuio._logger.warning(
                    "unable to get documentation for class %s.%s",
                    cls.__module__,
                    cls.__qualname__,
                )
                docs = {}

        fields = {}

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
            raise  # pragma: no cover

        cut_help = getattr(cls, "__yuio_short_help__", False)

        for name, field in cls.__gathered_fields.items():
            if not isinstance(field, _FieldSettings):
                field = _FieldSettings(default=field)

            fields[name] = field._update_defaults(
                f"{cls.__qualname__}.{name}",
                name,
                types[name],
                docs.get(name),
                cls.__allow_positionals,
                cut_help,
            )
        cls.__fields = fields

        return fields

    def __init_subclass__(cls, _allow_positionals=None, **kwargs):
        super().__init_subclass__(**kwargs)

        if _allow_positionals is not None:
            cls.__allow_positionals: bool = _allow_positionals
        cls.__fields: dict[str, _Field] | None = None

        cls.__gathered_fields: dict[str, _FieldSettings | _t.Any] = {}
        for name in cls.__annotations__:
            if not name.startswith("_"):
                cls.__gathered_fields[name] = cls.__dict__.get(name, yuio.MISSING)
        for name, value in cls.__dict__.items():
            if isinstance(value, _FieldSettings) and name not in cls.__gathered_fields:
                qualname = f"{cls.__qualname__}.{name}"
                raise TypeError(
                    f"error in {qualname}: field without annotations is not allowed"
                )
        for name, value in cls.__gathered_fields.items():
            if isinstance(value, _FieldSettings):
                value = value.default
            setattr(cls, name, value)

    def __init__(self, *args: _t.Self | dict[str, _t.Any], **kwargs):
        for name, field in self.__get_fields().items():
            if field.is_subconfig:
                setattr(self, name, field.ty())

        for arg in args:
            self.update(arg)

        self.update(kwargs)

    def update(self, other: _t.Self | dict[str, _t.Any], /):
        """
        Update fields in this config with fields from another config.

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
    def load_from_env(cls, prefix: str = "") -> _t.Self:
        """
        Load config from environment variables.

        :param prefix:
            if given, names of all environment variables will be prefixed with
            this string and an underscore.
        :returns:
            a parsed config.
        :raises:
            :class:`~yuio.parse.ParsingError`.

        """

        return cls.__load_from_env(prefix)

    @classmethod
    def __load_from_env(cls, prefix: str = "") -> _t.Self:
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
                try:
                    fields[name] = field.parser.parse(os.environ[env])
                except yuio.parse.ParsingError as e:
                    raise yuio.parse.ParsingError(
                        "Can't parse environment variable `%s`:\n%s",
                        env,
                        yuio.string.Indent(e),
                    ) from None

        return cls(**fields)

    @classmethod
    def _build_options(cls):
        return cls.__build_options("", "", None, True, False)

    @classmethod
    def __build_options(
        cls,
        prefix: str,
        dest_prefix: str,
        help_group: yuio.cli.HelpGroup | None,
        usage: yuio.Collapse | bool,
        show_if_inherited: bool,
    ) -> list[yuio.cli.Option[_t.Any]]:
        options: list[yuio.cli.Option[_t.Any]] = []

        if prefix:
            prefix += "-"

        for name, field in cls.__get_fields().items():
            if field.flags is yuio.DISABLED:
                continue

            dest = dest_prefix + name

            flags: list[str] | yuio.Positional
            if prefix and field.flags is not yuio.POSITIONAL:
                flags = [prefix + flag.lstrip("-") for flag in field.flags]
            else:
                flags = field.flags

            field_usage = field.usage
            if field_usage is None:
                field_usage = usage

            field_show_if_inherited = field.show_if_inherited
            if field_show_if_inherited is None:
                field_show_if_inherited = show_if_inherited

            if field.is_subconfig:
                assert flags is not yuio.POSITIONAL
                assert issubclass(field.ty, Config)
                if field.help is yuio.DISABLED:
                    subgroup = yuio.cli.HelpGroup("", help=yuio.DISABLED)
                elif field.help_group is yuio.MISSING:
                    if field.full_help:
                        lines = field.full_help.split("\n\n", 1)
                        title = lines[0].replace("\n", " ").rstrip(".").strip() or name
                        help = lines[1] if len(lines) > 1 else ""
                        subgroup = yuio.cli.HelpGroup(title=title, help=help)
                    else:
                        subgroup = help_group
                elif field.help_group is yuio.COLLAPSE:
                    if field.full_help:
                        lines = field.full_help.split("\n\n", 1)
                        title = lines[0].replace("\n", " ").rstrip(".").strip() or name
                        help = lines[1] if len(lines) > 1 else ""
                        subgroup = yuio.cli.HelpGroup(title=title, help=help)
                    else:
                        subgroup = yuio.cli.HelpGroup(title=field.name)
                    subgroup.collapse = True
                    subgroup._slug = field.name
                else:
                    subgroup = field.help_group
                options.extend(
                    field.ty.__build_options(
                        flags[0],
                        dest + ".",
                        subgroup,
                        field_usage,
                        field_show_if_inherited,
                    )
                )
                continue

            assert field.parser is not None

            option_ctor = field.option_ctor or _default_option
            option = option_ctor(
                OptionSettings(
                    name=name,
                    qualname=field.qualname,
                    parser=field.parser,
                    flags=flags,
                    required=field.required,
                    mutex_group=field.mutex_group,
                    usage=field_usage,
                    help=field.help,
                    help_group=field.help_group if field.help_group else help_group,
                    show_if_inherited=field_show_if_inherited,
                    merge=field.merge,
                    dest=dest,
                    default=field.default,
                    default_desc=field.default_desc,
                    long_flag_prefix=prefix or "--",
                )
            )
            options.append(option)

        return options

    def __getattribute(self, item):
        value = super().__getattribute__(item)
        if value is yuio.MISSING:
            raise AttributeError(f"{item} is not configured")
        else:
            return value

    # A dirty hack to hide `__getattribute__` from type checkers.
    locals()["__getattribute__"] = __getattribute

    def __repr__(self):
        field_reprs = ", ".join(
            f"{name}={getattr(self, name, yuio.MISSING)!r}"
            for name in self.__get_fields()
        )
        return f"{self.__class__.__name__}({field_reprs})"

    def __rich_repr__(self):
        for name in self.__get_fields():
            yield name, getattr(self, name, yuio.MISSING)

    def __copy__(self):
        return type(self)(self)

    def __deepcopy__(self, memo: dict[int, _t.Any] | None = None):
        return type(self)(copy.deepcopy(self.__dict__, memo))

    @classmethod
    def load_from_json_file(
        cls,
        path: str | pathlib.Path,
        /,
        *,
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _t.Self:
        """
        Load config from a ``.json`` file.

        :param path:
            path of the config file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param ignore_missing_file:
            if :data:`True`, silently ignore a missing file error. This is useful
            when loading a config from a home directory.
        :returns:
            a parsed config.
        :raises:
            :class:`~yuio.parse.ParsingError` if config parsing has failed
            or if config file doesn't exist.

        """

        return cls.__load_from_file(
            path, json.loads, ignore_unknown_fields, ignore_missing_file
        )

    @classmethod
    def load_from_yaml_file(
        cls,
        path: str | pathlib.Path,
        /,
        *,
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _t.Self:
        """
        Load config from a ``.yaml`` file.

        This requires `PyYaml <https://pypi.org/project/PyYAML/>`__ package
        to be installed.

        :param path:
            path of the config file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param ignore_missing_file:
            if :data:`True`, silently ignore a missing file error. This is useful
            when loading a config from a home directory.
        :returns:
            a parsed config.
        :raises:
            :class:`~yuio.parse.ParsingError` if config parsing has failed
            or if config file doesn't exist. Can raise :class:`ImportError`
            if ``PyYaml`` is not available.

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
        cls,
        path: str | pathlib.Path,
        /,
        *,
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _t.Self:
        """
        Load config from a ``.toml`` file.

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
            if :data:`True`, silently ignore a missing file error. This is useful
            when loading a config from a home directory.
        :returns:
            a parsed config.
        :raises:
            :class:`~yuio.parse.ParsingError` if config parsing has failed
            or if config file doesn't exist. Can raise :class:`ImportError`
            if ``toml`` is not available.

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
        cls,
        path: str | pathlib.Path,
        file_parser: _t.Callable[[str], _t.Any],
        ignore_unknown_fields: bool = False,
        ignore_missing_file: bool = False,
    ) -> _t.Self:
        path = pathlib.Path(path)

        if ignore_missing_file and (not path.exists() or not path.is_file()):
            return cls()

        try:
            loaded = file_parser(path.read_text())
        except Exception as e:
            raise yuio.parse.ParsingError(
                "Invalid config <c path>%s</c>:\n%s",
                path,
                yuio.string.Indent(e),
            ) from None

        return cls.load_from_parsed_file(
            loaded, ignore_unknown_fields=ignore_unknown_fields, path=path
        )

    @classmethod
    def load_from_parsed_file(
        cls,
        parsed: dict[str, object],
        /,
        *,
        ignore_unknown_fields: bool = False,
        path: str | pathlib.Path | None = None,
    ) -> _t.Self:
        """
        Load config from parsed config file.

        This method takes a dict with arbitrary values that you'd get from
        parsing type-rich configs such as ``yaml`` or ``json``.

        For example::

            with open("conf.yaml") as file:
                config = Config.load_from_parsed_file(yaml.load(file))

        :param parsed:
            data from parsed file.
        :param ignore_unknown_fields:
            if :data:`True`, this method will ignore fields that aren't listed
            in config class.
        :param path:
            path of the original file, used for error reporting.
        :returns:
            a parsed config.
        :raises:
            :class:`~yuio.parse.ParsingError`.

        """

        try:
            return cls.__load_from_parsed_file(
                yuio.parse.ConfigParsingContext(parsed), ignore_unknown_fields, ""
            )
        except yuio.parse.ParsingError as e:
            if path is None:
                raise
            else:
                raise yuio.parse.ParsingError(
                    "Invalid config <c path>%s</c>:\n%s",
                    path,
                    yuio.string.Indent(e),
                ) from None

    @classmethod
    def __load_from_parsed_file(
        cls,
        ctx: yuio.parse.ConfigParsingContext,
        ignore_unknown_fields: bool = False,
        field_prefix: str = "",
    ) -> _t.Self:
        value = ctx.value

        if not isinstance(value, dict):
            raise yuio.parse.ParsingError.type_mismatch(value, dict, ctx=ctx)

        fields = {}

        if not ignore_unknown_fields:
            for name in value:
                if name not in cls.__get_fields() and name != "$schema":
                    raise yuio.parse.ParsingError(
                        "Unknown field `%s`", f"{field_prefix}{name}"
                    )

        for name, field in cls.__get_fields().items():
            if name in value:
                if field.is_subconfig:
                    fields[name] = field.ty.__load_from_parsed_file(
                        ctx.descend(value[name], name),
                        ignore_unknown_fields,
                        field_prefix=name + ".",
                    )
                else:
                    assert field.parser is not None
                    fields[name] = field.parser.parse_config_with_ctx(
                        ctx.descend(value[name], name)
                    )

        return cls(**fields)

    @classmethod
    def to_json_schema(
        cls, ctx: yuio.json_schema.JsonSchemaContext
    ) -> yuio.json_schema.JsonSchemaType:
        """
        Create a JSON schema object based on this config.

        The purpose of this method is to make schemas for use in IDEs, i.e. to provide
        autocompletion or simple error checking. The returned schema is not guaranteed
        to reflect all constraints added to the parser.

        :param ctx:
            context for building a schema.
        :returns:
            a JSON schema that describes structure of this config.

        """

        return ctx.add_type(cls, _tx.type_repr(cls), lambda: cls.__to_json_schema(ctx))

    def to_json_value(
        self, *, include_defaults: bool = True
    ) -> yuio.json_schema.JsonValue:
        """
        Convert this config to a representation suitable for JSON serialization.

        :param include_defaults:
            if :data:`False`, default values will be skipped.
        :returns:
            a config converted to JSON-serializable representation.
        :raises:
            :class:`TypeError` if any of the config fields contain values that can't
            be converted to JSON by their respective parsers.

        """

        data = {}
        for name, field in self.__get_fields().items():
            if not include_defaults and name not in self.__dict__:
                continue
            if field.is_subconfig:
                value = getattr(self, name).to_json_value(
                    include_defaults=include_defaults
                )
                if value:
                    data[name] = value
            else:
                assert field.parser
                try:
                    value = getattr(self, name)
                except AttributeError:
                    pass
                else:
                    data[name] = field.parser.to_json_value(value)
        return data

    @classmethod
    def __to_json_schema(
        cls, ctx: yuio.json_schema.JsonSchemaContext
    ) -> yuio.json_schema.JsonSchemaType:
        properties: dict[str, yuio.json_schema.JsonSchemaType] = {}
        defaults = {}

        properties["$schema"] = yuio.json_schema.String()

        for name, field in cls.__get_fields().items():
            if field.is_subconfig:
                properties[name] = field.ty.to_json_schema(ctx)
            else:
                assert field.parser
                field_schema = field.parser.to_json_schema(ctx)
                if field.help and field.help is not yuio.DISABLED:
                    field_schema = yuio.json_schema.Meta(
                        field_schema, description=field.help
                    )
                properties[name] = field_schema
                if field.default is not yuio.MISSING:
                    try:
                        defaults[name] = field.parser.to_json_value(field.default)
                    except TypeError:
                        pass

        return yuio.json_schema.Meta(
            yuio.json_schema.Object(properties),
            title=cls.__name__,
            description=cls.__doc__,
            default=defaults,
        )


Config.__init_subclass__(_allow_positionals=False)


@dataclass(eq=False, kw_only=True)
class OptionSettings:
    """
    Settings for creating an :class:`~yuio.cli.Option` derived from field's type
    and configuration.

    """

    name: str | None
    """
    Name of config field or app parameter that caused creation of this option.

    """

    qualname: str | None
    """
    Fully qualified name of config field or app parameter that caused creation
    of this option. Useful for reporting errors.

    """

    default: _t.Any | yuio.Missing
    """
    See :attr:`yuio.cli.ValueOption.default`.

    """

    parser: yuio.parse.Parser[_t.Any]
    """
    Parser associated with this option.

    """

    flags: list[str] | yuio.Positional
    """
    See :attr:`yuio.cli.Option.flags`.

    """

    required: bool
    """
    See :attr:`yuio.cli.Option.required`.

    """

    merge: _t.Callable[[_t.Any, _t.Any], _t.Any] | None
    """
    See :attr:`yuio.cli.ValueOption.merge`.

    """

    mutex_group: None | MutuallyExclusiveGroup
    """
    See :attr:`yuio.cli.Option.mutex_group`.

    """

    dest: str
    """
    See :attr:`yuio.cli.Option.dest`. We don't provide any guarantees about `dest`\\ 's
    contents and recommend treating it as an opaque value.

    """

    help: str | yuio.Disabled
    """
    See :attr:`yuio.cli.Option.help`.

    """

    help_group: HelpGroup | None
    """
    See :attr:`yuio.cli.Option.help_group`.

    """

    usage: yuio.Collapse | bool
    """
    See :attr:`yuio.cli.Option.usage`.

    """

    default_desc: str | None
    """
    See :attr:`yuio.cli.Option.default_desc`.

    """

    show_if_inherited: bool
    """
    See :attr:`yuio.cli.Option.show_if_inherited`.

    """

    long_flag_prefix: str
    """
    This argument will contain prefix that was added to all :attr:`~OptionSettings.flags`.
    For apps and top level configs it will be ``"--"``, for nested configs it will
    include additional prefixes, for example ``"--nested-"``.

    """


OptionCtor: _t.TypeAlias = _t.Callable[[OptionSettings], yuio.cli.Option[T]]


def _default_option(s: OptionSettings):
    if s.flags is not yuio.POSITIONAL and yuio.parse._is_bool_parser(s.parser):
        return bool_option()(s)
    elif s.parser.supports_parse_many():
        return parse_many_option()(s)
    else:
        return parse_one_option()(s)


def bool_option(*, neg_flags: list[str] | None = None) -> OptionCtor[bool]:
    """
    Factory for :class:`yuio.cli.BoolOption`.

    :param neg_flags:
        additional set of flags that will set option's value to :data:`False`. If not
        given, a negative flag will be created by adding prefix ``no-`` to the first
        long flag of the option.
    :example:
        Boolean flag :flag:`--json` implicitly creates flag :flag:`--no-json`:

        .. code-block:: python
            :emphasize-lines: 5

            @yuio.app.app
            def main(
                json: bool = yuio.app.field(
                    default=False,
                    option_ctor=yuio.app.bool_option(),
                ),
            ): ...

        Boolean flag :flag:`--json` with explicitly provided flag
        :flag:`--disable-json`:

        .. code-block:: python
            :emphasize-lines: 5-7

            @yuio.app.app
            def main(
                json: bool = yuio.app.field(
                    default=False,
                    option_ctor=yuio.app.bool_option(
                        neg_flags=["--disable-json"],
                    ),
                ),
            ): ...

    """

    def ctor(s: OptionSettings, /):
        if s.flags is yuio.POSITIONAL:
            raise TypeError(f"error in {s.qualname}: BoolOption can't be positional")
        if neg_flags is None:
            _neg_flags = []
            for flag in s.flags:
                if not yuio.cli._is_short(flag) and flag.startswith(s.long_flag_prefix):
                    prefix = s.long_flag_prefix.strip("-")
                    if prefix:
                        prefix += "-"
                    suffix = flag[len(s.long_flag_prefix) :].removeprefix("-")
                    _neg_flags.append(f"--{prefix}no-{suffix}")
                    break
        elif s.long_flag_prefix == "--":
            _neg_flags = neg_flags
        else:
            _neg_flags = []
            for flag in neg_flags:
                _neg_flags.append(s.long_flag_prefix + flag.lstrip("-"))
        return yuio.cli.BoolOption(
            pos_flags=s.flags,
            neg_flags=_neg_flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            parser=s.parser,
            merge=s.merge,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor


def parse_one_option() -> OptionCtor[_t.Any]:
    """
    Factory for :class:`yuio.cli.ParseOneOption`.

    This option takes one argument and passes it
    to :meth:`Parser.parse() <yuio.parse.Parser.parse>`.

    :example:
        Forcing a field which can use :func:`parse_many_option`
        to use :func:`parse_one_option` instead.

        .. code-block:: python
            :emphasize-lines: 6

            @yuio.app.app
            def main(
                files: list[str] = yuio.app.field(
                    default=[],
                    parser=yuio.parse.List(yuio.parse.Int(), delimiter=","),
                    option_ctor=yuio.app.parse_one_option(),
                ),
            ): ...

        This will disable multi-argument syntax:

        .. code-block:: console

            $ prog --files a.txt,b.txt  # Ok
            $ prog --files a.txt b.txt  # Error: `--files` takes one argument.

    """

    def ctor(s: OptionSettings, /):
        return yuio.cli.ParseOneOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            parser=s.parser,
            merge=s.merge,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor


def parse_many_option() -> OptionCtor[_t.Any]:
    """
    Factory for :class:`yuio.cli.ParseManyOption`.

    This option takes multiple arguments and passes them
    to :meth:`Parser.parse_many() <yuio.parse.Parser.parse_many>`.

    """

    def ctor(s: OptionSettings, /):
        return yuio.cli.ParseManyOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            parser=s.parser,
            merge=s.merge,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor


def collect_option() -> OptionCtor[_t.Any]:
    """
    Factory for :class:`yuio.cli.ParseManyOption`.

    This option takes single argument; it collects all arguments across all uses
    of this option, and passes them
    to :meth:`Parser.parse_many() <yuio.parse.Parser.parse_many>`.

    :example:
        Forcing a field which can use :func:`parse_many_option`
        to collect arguments one-by-one.

        .. code-block:: python
            :emphasize-lines: 5

            @yuio.app.app
            def main(
                files: list[str] = yuio.app.field(
                    default=[],
                    option_ctor=yuio.app.collect_option(),
                    flags="--file",
                ),
            ): ...

        This will disable multi-argument syntax, but allow giving option multiple
        times without overriding previous value:

        .. code-block:: console

            $ prog --file a.txt --file b.txt  # Ok
            $ prog --files a.txt b.txt  # Error: `--file` takes one argument.

    """

    def ctor(s: OptionSettings, /):
        return yuio.cli.CollectOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            parser=s.parser,
            merge=s.merge,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor


def store_const_option(const: T) -> OptionCtor[T]:
    """
    Factory for :class:`yuio.cli.StoreConstOption`.

    This options takes no arguments. When it's encountered amongst CLI arguments,
    it writes `const` to the resulting config.

    """

    def ctor(s: OptionSettings, /):
        if s.flags is yuio.POSITIONAL:
            raise TypeError(
                f"error in {s.qualname}: StoreConstOption can't be positional"
            )

        return yuio.cli.StoreConstOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            merge=s.merge,
            default=s.default,
            default_desc=s.default_desc,
            const=const,
        )

    return ctor


def count_option() -> OptionCtor[int]:
    """
    Factory for :class:`yuio.cli.CountOption`.

    This option counts number of times it's encountered amongst CLI arguments.

    Equivalent to using :func:`store_const_option` with ``const=1``
    and ``merge=lambda a, b: a + b``.

    :example:

    .. code-block:: python

        @yuio.app.app
        def main(
            quiet: int = yuio.app.field(
                default=0,
                flags=["-q", "--quiet"],
                option_ctor=yuio.app.count_option(),
            ),
        ): ...

    .. code-block:: console

        prog -qq  # quiet=2

    """

    def ctor(s: OptionSettings, /):
        if s.flags is yuio.POSITIONAL:
            raise TypeError(f"error in {s.qualname}: CountOption can't be positional")

        return yuio.cli.CountOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor


def store_true_option() -> OptionCtor[bool]:
    """
    Factory for :class:`yuio.cli.StoreTrueOption`.

    Equivalent to using :func:`store_const_option` with ``const=True``.

    """

    def ctor(s: OptionSettings, /):
        if s.flags is yuio.POSITIONAL:
            raise TypeError(
                f"error in {s.qualname}: StoreTrueOption can't be positional"
            )

        return yuio.cli.StoreTrueOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor


def store_false_option() -> OptionCtor[bool]:
    """
    Factory for :class:`yuio.cli.StoreFalseOption`.

    Equivalent to using :func:`store_const_option` with ``const=False``.

    """

    def ctor(s: OptionSettings, /):
        if s.flags is yuio.POSITIONAL:
            raise TypeError(
                f"error in {s.qualname}: StoreFalseOption can't be positional"
            )

        return yuio.cli.StoreFalseOption(
            flags=s.flags,
            required=s.required,
            mutex_group=s.mutex_group,
            usage=s.usage,
            help=s.help,
            help_group=s.help_group,
            show_if_inherited=s.show_if_inherited,
            dest=s.dest,
            default=s.default,
            default_desc=s.default_desc,
        )

    return ctor
