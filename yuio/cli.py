# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Low-level interface to CLI parser.

Yuio's primary interface for building CLIs is :mod:`yuio.app`; this is low-level module
that actually parses arguments. Because of this, :mod:`yuio.cli` doesn't expose
a convenient interface for building CLIs. Instead, it exposes a set of classes
that describe an interface; :mod:`yuio.app` and :mod:`yuio.config` compose these
classes and pass them to :class:`CliParser`.

This module is inspired by :mod:`argparse`, but there are differences:

-   all flags should start with ``-``, other symbols are not supported (at least
    for now);

-   unlike :mod:`argparse`, this module doesn't rely on partial parsing and sub-parses.
    Instead, it operates like a regular state machine, and any unmatched flags
    or arguments are reported right away;

-   it uses nested namespaces, one namespace per subcommand. When a subcommand
    is encountered, a new namespace is created and assigned to the corresponding
    :attr:`~Option.dest` in the parent namespace;

-   namespaces are abstracted away by the :class:`Namespace` protocol, which has an
    interface similar to :class:`dict`;

-   options from base command can be specified after a subcommand argument, unless
    subcommand shadows them. This is possible because we don't do partial parsing.

    For example, consider this program:

    .. code-block:: python

        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-v", "--verbose", action="count")
        subparsers = parser.add_subparsers()
        subcommand = subparsers.add_parser("subcommand")

    Argparse will not recognize :flag:`--verbose` if it's specified
    after :flag:`subcommand`, but :mod:`yuio.cli` handles this just fine:

    .. code-block:: console

        $ prog subcommand --verbose

-   there's no distinction between ``nargs=None`` and ``nargs=1``; however, there is
    a distinction between argument being specified inline or not. This allows us to
    supply arguments for options with ``nargs=0``.

    See :ref:`flags-with-optional-values` for details;

-   the above point also allows us to disambiguate positional arguments
    and arguments with ``nargs="*"``:

    .. code-block:: console

        $ prog --array='a b c' subcommand

    See :ref:`flags-with-multiple-values` for details;

-   this parser tracks information about argument positions and offsets, allowing
    it to display rich error messages;

-   we expose more knobs to tweak help formatting; see functions on :class:`Option`
    for details.


Commands and sub-commands
-------------------------

.. autoclass:: Command
    :members:


Flags and positionals
---------------------

.. autoclass:: Option
    :members:

.. autoclass:: ValueOption
    :members:

.. autoclass:: ParserOption
    :members:

.. autoclass:: BoolOption
    :members:

.. autoclass:: ParseOneOption
    :members:

.. autoclass:: ParseManyOption
    :members:

.. autoclass:: StoreConstOption
    :members:

.. autoclass:: StoreFalseOption
    :members:

.. autoclass:: StoreTrueOption
    :members:

.. autoclass:: CountOption
    :members:

.. autoclass:: VersionOption
    :members:

.. autoclass:: HelpOption
    :members:


Namespace
---------

.. autoclass:: Namespace

    .. automethod:: __getitem__

    .. automethod:: __setitem__

    .. automethod:: __contains__

.. autoclass:: ConfigNamespace
    :members:


CLI parser
----------

.. autoclass:: CliParser
    :members:

.. autoclass:: Argument
    :members:

.. autoclass:: Flag
    :members:

.. autoclass:: ArgumentError
    :members:

.. type:: NArgs
    :canonical: int | typing.Literal["+"]

    Type alias for :attr:`~Option.nargs`.

    .. note::

        ``"*"`` from argparse is equivalent to ``nargs="+"`` with ``allow_no_args=True``;
        ``"?"`` from argparse is equivalent to ``nargs=1`` with ``allow_no_args=True``.


Option grouping
---------------

.. autoclass:: MutuallyExclusiveGroup
    :members:

.. autoclass:: HelpGroup
    :members:

.. autodata:: ARGS_GROUP

.. autodata:: SUBCOMMANDS_GROUP

.. autodata:: OPTS_GROUP

.. autodata:: MISC_GROUP

"""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import functools
import re
import sys
import warnings
from dataclasses import dataclass

import yuio
import yuio.complete
import yuio.doc
import yuio.hl
import yuio.parse
import yuio.string
from yuio.string import ColorizedString as _ColorizedString
from yuio.util import _UNPRINTABLE_TRANS
from yuio.util import commonprefix as _commonprefix

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

if TYPE_CHECKING:
    import yuio.app
    import yuio.config
    import yuio.dbg

__all__ = [
    "ARGS_GROUP",
    "MISC_GROUP",
    "OPTS_GROUP",
    "SUBCOMMANDS_GROUP",
    "Argument",
    "ArgumentError",
    "BoolOption",
    "BugReportOption",
    "CliParser",
    "CliWarning",
    "CollectOption",
    "Command",
    "CompletionOption",
    "ConfigNamespace",
    "CountOption",
    "Flag",
    "HelpGroup",
    "HelpOption",
    "MutuallyExclusiveGroup",
    "NArgs",
    "Namespace",
    "Option",
    "ParseManyOption",
    "ParseOneOption",
    "ParserOption",
    "StoreConstOption",
    "StoreFalseOption",
    "StoreTrueOption",
    "ValueOption",
    "VersionOption",
]

T = _t.TypeVar("T")
T_cov = _t.TypeVar("T_cov", covariant=True)

_SHORT_FLAG_RE = r"^-[a-zA-Z0-9]$"
_LONG_FLAG_RE = r"^--[a-zA-Z0-9_+/.-]+$"

_NUM_RE = r"""(?x)
    ^
    [+-]?
    (?:
      (?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?
      |0[bB][01]+
      |0[oO][0-7]+
      |0[xX][0-9a-fA-F]+
    )
    $
"""

NArgs: _t.TypeAlias = int | _t.Literal["+"]
"""
Type alias for nargs.

.. note::

    ``"*"`` from argparse is equivalent to ``nargs="+"`` with ``allow_no_args=True``;
    ``"?"`` from argparse is equivalent to ``nargs=1`` with ``allow_no_args=True``.

"""

NamespaceT = _t.TypeVar("NamespaceT", bound="Namespace")
ConfigT = _t.TypeVar("ConfigT", bound="yuio.config.Config")


class CliWarning(yuio.YuioWarning):
    pass


@dataclass(frozen=True, slots=True)
class Argument:
    """
    Represents a CLI argument, or its part.

    For positionals, this will contain the entire argument. For inline values,
    this will contain value substring and its position relative to the full
    value.

    :example:
        Consider the following command arguments:

        .. code-block:: text

            --arg=value

        Argument ``"value"`` will be represented as:

        .. code-block:: python

            Argument(value="value", index=0, pos=6, flag="--arg", metavar=...)

    """

    value: str
    """
    Contents of the argument.

    """

    index: int
    """
    Index of this argument in the array that was passed to :meth:`CliParser.parse`.

    Note that this array does not include executable name, so indexes are shifted
    relative to :data:`sys.argv`.

    """

    pos: int
    """
    Position of the :attr:`~Argument.value` relative to the original argument string.

    """

    metavar: str
    """
    Meta variable for this argument.

    """

    flag: Flag | None
    """
    If this argument belongs to a flag, this attribute will contain flag's name.

    """

    def __str__(self) -> str:
        return self.metavar

    def __colorized_str__(self, ctx: yuio.string.ReprContext) -> _ColorizedString:
        return _ColorizedString(
            ctx.get_color("msg/text:code/sh-usage hl/flag:sh-usage"),
            self.metavar,
        )


@dataclass(frozen=True, slots=True)
class Flag:
    value: str
    """
    Name of the flag.

    """

    index: int
    """
    Index of this flag in the array that was passed to :meth:`CliParser.parse`.

    Note that this array does not include executable name, so indexes are shifted
    relative to :data:`sys.argv`.

    """

    def __str__(self) -> str:
        return self.value

    def __colorized_str__(self, ctx: yuio.string.ReprContext) -> _ColorizedString:
        return _ColorizedString(
            ctx.get_color("msg/text:code/sh-usage hl/flag:sh-usage"),
            self.value,
        )


class ArgumentError(yuio.PrettyException, ValueError):
    """
    Error that happened during argument parsing.

    """

    @_t.overload
    def __init__(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        flag: Flag | None = None,
        arguments: Argument | list[Argument] | None = None,
        n_arg: int | None = None,
        pos: tuple[int, int] | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
        option: Option[_t.Any] | None = None,
    ): ...
    @_t.overload
    def __init__(
        self,
        msg: yuio.string.Colorable | None = None,
        /,
        *,
        flag: Flag | None = None,
        arguments: Argument | list[Argument] | None = None,
        n_arg: int | None = None,
        pos: tuple[int, int] | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
        option: Option[_t.Any] | None = None,
    ): ...
    def __init__(
        self,
        *args,
        flag: Flag | None = None,
        arguments: Argument | list[Argument] | None = None,
        n_arg: int | None = None,
        pos: tuple[int, int] | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
        option: Option[_t.Any] | None = None,
    ):
        super().__init__(*args)

        self.flag: Flag | None = flag
        """
        Flag that caused this error. Can be :data:`None` if error is caused
        by a positional argument.

        """

        self.arguments: Argument | list[Argument] | None = arguments
        """
        Arguments that caused this error.

        This can be a single argument, or multiple arguments. In the later case,
        :attr:`~yuio.parse.ParsingError.n_arg` should correspond to the argument
        that failed to parse. If :attr:`~yuio.parse.ParsingError.n_arg`
        is :data:`None`, then all arguments are treated as faulty.

        .. note::

            Don't confuse :attr:`~ArgumentError.arguments` and :attr:`~BaseException.args`:
            the latter contains formatting arguments and is defined
            in the :class:`BaseException` class.

        """

        self.pos: tuple[int, int] | None = pos
        """
        Position in the original string in which this error has occurred (start
        and end indices).

        If :attr:`~ArgumentError.n_arg` is set, and :attr:`~ArgumentError.arguments`
        is given as a list, then this position is relative to the argument
        at index :attr:`~ArgumentError.n_arg`.

        If :attr:`~ArgumentError.arguments` is given as a single argument (not a list),
        then this position is relative to that argument.

        Otherwise, position is ignored.

        """

        self.n_arg: int | None = n_arg
        """
        Index of the argument that caused the error.

        """

        self.path: list[tuple[_t.Any, str | None]] | None = path
        """
        Same as in :attr:`ParsingError.path <yuio.parse.ParsingError.path>`.
        Can be present if parser uses :meth:`~yuio.parse.Parser.parse_config`
        for validation.

        """

        self.option: Option[_t.Any] | None = option
        """
        Option which caused failure.

        """

        self.commandline: list[str] | None = None
        self.prog: str | None = None
        self.subcommands: list[str] | None = None
        self.help_parser: yuio.doc.DocParser | None = None

    @classmethod
    def from_parsing_error(
        cls,
        e: yuio.parse.ParsingError,
        /,
        *,
        flag: Flag | None = None,
        arguments: Argument | list[Argument] | None = None,
        option: Option[_t.Any] | None = None,
    ):
        """
        Convert parsing error to argument error.

        """

        return cls(
            *e.args,
            flag=flag,
            arguments=arguments,
            n_arg=e.n_arg,
            pos=e.pos,
            path=e.path,
            option=option,
        )

    def to_colorable(self) -> yuio.string.Colorable:
        colorable = yuio.string.WithBaseColor(
            super().to_colorable(),
            base_color="msg/text:error",
        )

        msg = []
        args = []
        sep = False

        if self.flag and self.flag.value:
            msg.append("in flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>")
            args.append(self.flag.value)
            sep = True

        argument = None
        if isinstance(self.arguments, list):
            if self.n_arg is not None and self.n_arg < len(self.arguments):
                argument = self.arguments[self.n_arg]
        else:
            argument = self.arguments

        if argument and argument.metavar:
            if sep:
                msg.append(", ")
            msg.append("in <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>")
            args.append(argument.metavar)

        if self.path:
            if sep:
                msg.append(", ")
            msg.append("in <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>")
            args.append(yuio.parse._PathRenderer(self.path))

        if sep:
            msg.insert(0, "Error ")
            msg.append(":")

            colorable = yuio.string.Stack(
                yuio.string.WithBaseColor(
                    yuio.string.Format("".join(msg), *args),
                    base_color="msg/text:failure",
                ),
                yuio.string.Indent(colorable),
            )
        else:
            colorable = yuio.string.WithBaseColor(
                colorable,
                base_color="msg/text:failure",
            )

        if commandline := self._make_commandline():
            colorable = yuio.string.Stack(
                commandline,
                colorable,
            )

        if usage := self._make_usage():
            colorable = yuio.string.Stack(
                colorable,
                usage,
            )

        return colorable

    def _make_commandline(self):
        if not self.prog or not self.commandline:
            return None

        argument = None
        if isinstance(self.arguments, list):
            if self.n_arg is not None and self.n_arg < len(self.arguments):
                argument = self.arguments[self.n_arg]
        else:
            argument = self.arguments

        if argument:
            arg_index = argument.index
            arg_pos = (argument.pos, argument.pos + len(argument.value))
            if self.pos:
                arg_pos = (
                    arg_pos[0] + self.pos[0],
                    min(arg_pos[1], arg_pos[0] + self.pos[1]),
                )
        elif self.flag:
            arg_index = self.flag.index
            arg_pos = (0, len(self.commandline[arg_index]))
        else:
            return None

        text = self.prog
        text += " "
        text += " ".join(_quote(arg) for arg in self.commandline[:arg_index])
        if arg_index > 0:
            text += " "

        center, pos = _quote_and_adjust_pos(self.commandline[arg_index], arg_pos)
        pos = (pos[0] + len(text), pos[1] + len(text))

        text += center
        text += " "
        text += " ".join(_quote(arg) for arg in self.commandline[arg_index + 1 :])

        if text:
            return yuio.parse._CodeRenderer(text, pos, as_cli=True)
        else:
            return None

    def _make_usage(self):
        if not self.option or not self.option.help or not self.help_parser:
            return None
        else:
            return _ShortUsageFormatter(self.help_parser, self.subcommands, self.option)


class Namespace(_t.Protocol):
    """
    Protocol for namespace implementations.

    """

    @abc.abstractmethod
    def __getitem__(self, key: str, /) -> _t.Any: ...

    @abc.abstractmethod
    def __setitem__(self, key: str, value: _t.Any, /): ...

    @abc.abstractmethod
    def __contains__(self, key: str, /) -> bool: ...


@yuio.string.repr_from_rich
class ConfigNamespace(Namespace, _t.Generic[ConfigT]):
    """
    Wrapper that makes :class:`~yuio.config.Config` instances behave like namespaces.

    """

    def __init__(self, config: ConfigT) -> None:
        self.__config = config

    @property
    def config(self) -> ConfigT:
        """
        Wrapped config instance.

        """

        return self.__config

    def __getitem__(self, key: str) -> _t.Any:
        root, key = self.__split_key(key)
        try:
            return getattr(root, key)
        except AttributeError as e:
            raise KeyError(str(e)) from None

    def __setitem__(self, key: str, value: _t.Any):
        root, key = self.__split_key(key)
        try:
            return setattr(root, key, value)
        except AttributeError as e:
            raise KeyError(str(e)) from None

    def __contains__(self, key: str):
        root, key = self.__split_key(key)
        return key in root.__dict__

    def __split_key(self, key: str) -> tuple[yuio.config.Config, str]:
        root = self.__config
        *parents, key = key.split(".")
        for parent in parents:
            root = getattr(root, parent)
        return root, key

    def __rich_repr__(self):
        yield None, self.__config


@dataclass(eq=False)
class HelpGroup:
    """
    Group of flags in CLI help.

    """

    title: str
    """
    Title for this group.

    """

    help: str | yuio.Disabled = dataclasses.field(default="", kw_only=True)
    """
    Help message for an option.

    """

    collapse: bool = dataclasses.field(default=False, kw_only=True)
    """
    Hide options from this group in CLI help, but show group's title and help.

    """

    _slug: str | None = dataclasses.field(default=None, kw_only=True)


ARGS_GROUP = HelpGroup("Arguments")
"""
Help group for positional arguments.

"""

SUBCOMMANDS_GROUP = HelpGroup("Subcommands")
"""
Help group for subcommands.

"""

OPTS_GROUP = HelpGroup("Options")
"""
Help group for flags.

"""

MISC_GROUP = HelpGroup("Misc options")
"""
Help group for misc flags such as :flag:`--help` or :flag:`--version`.

"""


@dataclass(kw_only=True, eq=False)
class MutuallyExclusiveGroup:
    """
    A sentinel for creating mutually exclusive groups.

    Pass an instance of this class all :func:`~yuio.app.field`\\ s that should
    be mutually exclusive.

    """

    required: bool = False
    """
    Require that one of the mutually exclusive options is always given.

    """


@dataclass(eq=False, kw_only=True)
class Option(abc.ABC, _t.Generic[T_cov]):
    """
    Base class for a CLI option.

    """

    flags: list[str] | yuio.Positional
    """
    Flags corresponding to this option. Positional options have flags set to
    :data:`yuio.POSITIONAL`.

    """

    allow_inline_arg: bool
    """
    Whether to allow specifying argument inline (i.e. :flag:`--foo=bar`).

    Inline arguments are handled separately from normal arguments,
    and :attr:`~Option.nargs` setting does not affect them.

    Positional options can't take inline arguments, so this attribute has
    no effect on them.

    """

    allow_implicit_inline_arg: bool
    """
    Whether to allow specifying argument inline with short flags without equals sign
    (i.e. :flag:`-fValue`).

    Inline arguments are handled separately from normal arguments,
    and :attr:`~Option.nargs` setting does not affect them.

    Positional options can't take inline arguments, so this attribute has
    no effect on them.

    """

    nargs: NArgs
    """
    How many arguments this option takes.

    """

    allow_no_args: bool
    """
    Whether to allow passing no arguments even if :attr:`~Option.nargs` requires some.

    """

    required: bool
    """
    Makes this option required. The parsing will fail if this option is not
    encountered among CLI arguments.

    Note that positional arguments are always parsed; if no positionals are given,
    all positional options are processed with zero arguments, at which point they'll
    fail :attr:`~Option.nargs` check. Thus, :attr:`~Option.required` has no effect
    on positionals.

    """

    metavar: str | tuple[str, ...]
    """
    Option's meta variable, used for displaying help messages.

    If :attr:`~Option.nargs` is an integer, this can be a tuple of strings,
    one for each argument. If :attr:`~Option.nargs` is zero, this can be an empty
    tuple.

    """

    mutex_group: None | MutuallyExclusiveGroup
    """
    Mutually exclusive group for this option. Positional options can't have
    mutex groups.

    """

    usage: yuio.Collapse | bool
    """
    Specifies whether this option should be displayed in CLI usage. Positional options
    are always displayed, regardless of this setting.

    """

    help: str | yuio.Disabled
    """
    Help message for an option.

    """

    help_group: HelpGroup | None
    """
    Group for this flag, default is :data:`OPTS_GROUP` for flags and :data:`ARGS_GROUP`
    for positionals. Positionals are flags are never mixed together; if they appear
    in the same group, the group title will be repeated twice.

    """

    default_desc: str | None
    """
    Overrides description of default value.

    """

    show_if_inherited: bool
    """
    Force-show this flag if it's inherited from parent command. Positionals can't be
    inherited because subcommand argument always goes last.

    """

    allow_abbrev: bool
    """
    Allow abbreviation for this option.

    """

    dest: str
    """
    Key where to store parsed argument.

    """

    @abc.abstractmethod
    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        """
        Process this argument.

        This method is called every time an option is encountered
        on the command line. It should parse option's args and merge them
        with previous values, if there are any.

        When option's arguments are passed separately (i.e. :flag:`--opt arg1 arg2 ...`),
        `args` is given as a list. List's length is checked against
        :attr:`~Option.nargs` before this method is called.

        When option's arguments are passed as an inline value (i.e. :flag:`--long=arg`
        or :flag:`-Sarg`), the `args` is given as a string. :attr:`~Option.nargs`
        are not checked in this case, giving you an opportunity to handle inline option
        however you like.

        :param cli_parser:
            CLI parser instance that's doing the parsing. Not to be confused with
            :class:`yuio.parse.Parser`.
        :param flag:
            flag that set this option. This will be set to :data:`None`
            for positional arguments.
        :param arguments:
            option arguments, see above.
        :param ns:
            namespace where parsed arguments should be stored.
        :raises:
            :class:`ArgumentError`, :class:`~yuio.parse.ParsingError`.

        """

    def post_process(
        self,
        cli_parser: CliParser[Namespace],
        arguments: list[Argument],
        ns: Namespace,
    ):
        """
        Called once at the end of parsing to post-process all arguments.

        :param cli_parser:
            CLI parser instance that's doing the parsing. Not to be confused with
            :class:`yuio.parse.Parser`.
        :param arguments:
            option arguments that were ever passed to this option.
        :param ns:
            namespace where parsed arguments should be stored.
        :raises:
            :class:`ArgumentError`, :class:`~yuio.parse.ParsingError`.

        """

    @functools.cached_property
    def short_flags(self) -> list[str] | None:
        if self.flags is yuio.POSITIONAL:
            return None
        else:
            return [flag for flag in self.flags if _is_short(flag)]

    @functools.cached_property
    def long_flags(self) -> list[str] | None:
        if self.flags is yuio.POSITIONAL:
            return None
        else:
            return [flag for flag in self.flags if not _is_short(flag)]

    @functools.cached_property
    def primary_short_flag(self) -> str | None:
        """
        Short flag that will be displayed in CLI help.

        """

        if short_flags := self.short_flags:
            return short_flags[0]
        else:
            return None

    @functools.cached_property
    def primary_long_flags(self) -> list[str] | None:
        """
        Long flags that will be displayed in CLI help.

        """

        if long_flags := self.long_flags:
            return [long_flags[0]]
        else:
            return None

    def format_usage(
        self,
        ctx: yuio.string.ReprContext,
        /,
    ) -> tuple[_ColorizedString, bool]:
        """
        Allows customizing how this option looks in CLI usage.

        :param ctx:
            repr context for formatting help.
        :returns:
            a string that will be used to represent this option in program's
            usage section.

        """

        can_group = False
        res = _ColorizedString()
        if self.flags is not yuio.POSITIONAL and self.flags:
            flag = self.primary_short_flag
            if flag:
                can_group = True
            elif self.primary_long_flags:
                flag = self.primary_long_flags[0]
            else:
                flag = self.flags[0]
            res.append_color(ctx.get_color("hl/flag:sh-usage"))
            res.append_str(flag)
        if metavar := self.format_metavar(ctx):
            res.append_colorized_str(metavar)
            can_group = False
        return res, can_group

    def format_metavar(
        self,
        ctx: yuio.string.ReprContext,
        /,
    ) -> _ColorizedString:
        """
        Allows customizing how this option looks in CLI help.

        :param ctx:
            repr context for formatting help.
        :returns:
            a string that will be appended to the list of option's flags
            to format an entry for this option in CLI help message.

        """

        res = _ColorizedString()

        if not self.nargs:
            return res

        res.append_color(ctx.get_color("hl/punct:sh-usage"))
        if self.flags:
            res.append_str(" ")

        if self.nargs == "+":
            if self.allow_no_args:
                res.append_str("[")
            res.append_colorized_str(_format_metavar(self.nth_metavar(0), ctx))
            if self.allow_no_args:
                res.append_str(" ...]")
            else:
                res.append_str(" [")
                res.append_colorized_str(_format_metavar(self.nth_metavar(0), ctx))
                res.append_str(" ...]")
        elif isinstance(self.nargs, int) and self.nargs:
            if self.allow_no_args:
                res.append_str("[")
            sep = False
            for i in range(self.nargs):
                if sep:
                    res.append_str(" ")
                res.append_colorized_str(_format_metavar(self.nth_metavar(i), ctx))
                sep = True
            if self.allow_no_args:
                res.append_str("]")

        return res

    def format_help_tail(
        self, ctx: yuio.string.ReprContext, /, *, all: bool = False
    ) -> _ColorizedString:
        """
        Format additional content that will be added to the end of the help message,
        such as aliases, default value, etc.

        :param ctx:
            repr context for formatting help.
        :param all:
            whether :flag:`--help=all` was specified.
        :returns:
            a string that will be appended to the main help message.

        """

        base_color = ctx.get_color("msg/text:help/tail msg/text:code/sh-usage")

        res = _ColorizedString(base_color)

        if alias_flags := self.format_alias_flags(ctx, all=all):
            es = "" if len(alias_flags) == 1 else "es"
            res.append_str(f"Alias{es}: ")
            sep = False
            for alias_flag in alias_flags:
                if isinstance(alias_flag, tuple):
                    alias_flag = alias_flag[0]
                if sep:
                    res.append_str(", ")
                res.append_colorized_str(alias_flag.with_base_color(base_color))
                sep = True

        if default := self.format_default(ctx, all=all):
            if res:
                res.append_str("; ")
            res.append_str("Default: ")
            res.append_colorized_str(default.with_base_color(base_color))

        if res:
            res.append_str(".")

        return res

    def format_alias_flags(
        self, ctx: yuio.string.ReprContext, /, *, all: bool = False
    ) -> list[_ColorizedString | tuple[_ColorizedString, str]] | None:
        """
        Format alias flags that weren't included in :attr:`~Option.primary_short_flag`
        and :attr:`~Option.primary_long_flags`.

        :param ctx:
            repr context for formatting help.
        :param all:
            whether :flag:`--help=all` was specified.
        :returns:
            a list of strings, one per each alias.

        """

        if self.flags is yuio.POSITIONAL:
            return None
        primary_flags = set(self.primary_long_flags or [])
        if self.primary_short_flag:
            primary_flags.add(self.primary_short_flag)
        aliases: list[_ColorizedString | tuple[_ColorizedString, str]] = []
        flag_color = ctx.get_color("hl/flag:sh-usage")
        for flag in self.flags:
            if flag not in primary_flags:
                res = _ColorizedString()
                res.start_no_wrap()
                res.append_color(flag_color)
                res.append_str(flag)
                res.end_no_wrap()
                aliases.append(res)
        return aliases

    def format_default(
        self, ctx: yuio.string.ReprContext, /, *, all: bool = False
    ) -> _ColorizedString | None:
        """
        Format default value that will be included in the CLI help.

        :param ctx:
            repr context for formatting help.
        :param all:
            whether :flag:`--help=all` was specified.
        :returns:
            a string that will be appended to the main help message.

        """

        if self.default_desc is not None:
            return ctx.hl(self.default_desc).with_base_color(ctx.get_color("code"))

        return None

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return None, False

    def nth_metavar(self, n: int) -> str:
        """
        Get metavar for n-th argument for this option.

        """

        if not self.metavar:
            return "<argument>"
        if isinstance(self.metavar, tuple):
            if n >= len(self.metavar):
                return self.metavar[-1]
            else:
                return self.metavar[n]
        else:
            return self.metavar


@dataclass(eq=False, kw_only=True)
class ValueOption(Option[T], _t.Generic[T]):
    """
    Base class for options that parse arguments and assign them to namespace.

    This base handles assigning parsed value to the target destination and merging
    values if option is invoked multiple times. Call ``self.set(ns, value)`` from
    :meth:`Option.process` to set result of option processing.

    """

    merge: _t.Callable[[T, T], T] | None
    """
    Function to merge previous and new value.

    """

    default: object
    """
    Default value that will be used if this flag is not given.

    Used for formatting help, does not affect actual parsing.

    """

    def set(self, ns: Namespace, value: T):
        """
        Save new value. If :attr:`~ValueOption.merge` is given, automatically
        merge old and new value.

        """

        if self.merge and self.dest in ns:
            ns[self.dest] = self.merge(ns[self.dest], value)
        else:
            ns[self.dest] = value


@dataclass(eq=False, kw_only=True)
class ParserOption(ValueOption[T], _t.Generic[T]):
    """
    Base class for options that use :mod:`yuio.parse` to process arguments.

    """

    parser: yuio.parse.Parser[T]
    """
    A parser used to parse option's arguments.

    """

    def format_default(
        self, ctx: yuio.string.ReprContext, /, *, all: bool = False
    ) -> _ColorizedString | None:
        if self.default_desc is not None:
            return ctx.hl(self.default_desc).with_base_color(ctx.get_color("code"))

        if self.default is yuio.MISSING or self.default is None:
            return None

        try:
            return ctx.hl(self.parser.describe_value(self.default)).with_base_color(
                ctx.get_color("code")
            )
        except TypeError:
            return ctx.repr(self.default)


@dataclass(eq=False, kw_only=True)
class BoolOption(ParserOption[bool]):
    """
    An option that combines :class:`StoreTrueOption`, :class:`StoreFalseOption`,
    and :class:`ParseOneOption`.

    If any of the :attr:`~BoolOption.pos_flags` are given without arguments, it works like
    :class:`StoreTrueOption`.

    If any of the :attr:`~BoolOption.neg_flags` are given, it works like
    :class:`StoreFalseOption`.

    If any of the :attr:`~BoolOption.pos_flags` are given with an inline argument,
    the argument is parsed as a :class:`bool`.

    .. note::

        Bool option has :attr:`~Option.nargs` set to ``0``, so non-inline arguments
        (i.e. :flag:`--json false`) are not recognized. You should always use inline
        argument to set boolean flag's value (i.e. :flag:`--json=false`). This avoids
        ambiguity in cases like the following:

        .. code-block:: console

            $ prog --json subcommand  # Ok
            $ prog --json=true subcommand  # Ok
            $ prog --json true subcommand  # Not allowed

    :example:
        .. code-block:: python

            option = yuio.cli.BoolOption(
                pos_flags=["--json"],
                neg_flags=["--no-json"],
                dest=...,
            )

        .. code-block:: console

            $ prog --json  # Set `dest` to `True`
            $ prog --no-json  # Set `dest` to `False`
            $ prog --json=$value  # Set `dest` to parsed `$value`

    """

    pos_flags: list[str]
    """
    List of flag names that enable this boolean option. Should be non-empty.

    """

    neg_flags: list[str]
    """
    List of flag names that disable this boolean option.

    """

    def __init__(
        self,
        *,
        pos_flags: list[str],
        neg_flags: list[str],
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        parser: yuio.parse.Parser[bool] | None = None,
        merge: _t.Callable[[bool, bool], bool] | None = None,
        default: bool | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        self.pos_flags = pos_flags
        self.neg_flags = neg_flags

        super().__init__(
            flags=pos_flags + neg_flags,
            allow_inline_arg=True,
            allow_implicit_inline_arg=False,
            nargs=0,
            allow_no_args=True,
            required=required,
            metavar=(),
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=merge,
            default=default,
            parser=parser or yuio.parse.Bool(),
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        if flag and flag.value in self.neg_flags:
            if arguments:
                raise ArgumentError(
                    "This flag can't have arguments", flag=flag, arguments=arguments
                )
            value = False
        elif isinstance(arguments, Argument):
            value = self.parser.parse(arguments.value)
        else:
            value = True
        self.set(ns, value)

    @functools.cached_property
    def primary_short_flag(self):
        if self.flags is yuio.POSITIONAL:
            return None
        if self.default is True:
            flags = self.neg_flags
        else:
            flags = self.pos_flags
        for flag in flags:
            if _is_short(flag):
                return flag
        return None

    @functools.cached_property
    def primary_long_flags(self):
        flags = []
        if self.default is not True:
            for flag in self.pos_flags:
                if not _is_short(flag):
                    flags.append(flag)
                    break
        if self.default is not False:
            for flag in self.neg_flags:
                if not _is_short(flag):
                    flags.append(flag)
                    break
        return flags

    def format_alias_flags(
        self, ctx: yuio.string.ReprContext, *, all: bool = False
    ) -> list[_ColorizedString | tuple[_ColorizedString, str]] | None:
        if self.flags is yuio.POSITIONAL:
            return None

        primary_flags = set(self.primary_long_flags or [])
        if self.primary_short_flag:
            primary_flags.add(self.primary_short_flag)

        aliases: list[_ColorizedString | tuple[_ColorizedString, str]] = []
        flag_color = ctx.get_color("hl/flag:sh-usage")
        if all:
            alias_candidates = self.pos_flags + self.neg_flags
        else:
            alias_candidates = []
            if self.default is not True:
                alias_candidates += self.pos_flags
            if self.default is not False:
                alias_candidates += self.neg_flags
        for flag in alias_candidates:
            if flag not in primary_flags:
                res = _ColorizedString()
                res.start_no_wrap()
                res.append_color(flag_color)
                res.append_str(flag)
                res.end_no_wrap()
                aliases.append(res)
        if self.pos_flags and all:
            primary_pos_flag = self.pos_flags[0]
            for pos_flag in self.pos_flags:
                if not _is_short(pos_flag):
                    primary_pos_flag = pos_flag
                    break
            punct_color = ctx.get_color("hl/punct:sh-usage")
            metavar_color = ctx.get_color("hl/metavar:sh-usage")
            res = _ColorizedString()
            res.start_no_wrap()
            res.append_color(flag_color)
            res.append_str(primary_pos_flag)
            res.end_no_wrap()
            res.append_color(punct_color)
            res.append_str("={")
            res.append_color(metavar_color)
            res.append_str("true")
            res.append_color(punct_color)
            res.append_str("|")
            res.append_color(metavar_color)
            res.append_str("false")
            res.append_color(punct_color)
            res.append_str("}")
            aliases.append(res)
        return aliases

    def format_default(
        self, ctx: yuio.string.ReprContext, /, *, all: bool = False
    ) -> _ColorizedString | None:
        if self.default_desc is not None:
            return ctx.hl(self.default_desc).with_base_color(ctx.get_color("code"))

        return None

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return (
            yuio.complete.Choice(
                [
                    yuio.complete.Option("true"),
                    yuio.complete.Option("false"),
                ]
            ),
            False,
        )


@dataclass(eq=False, kw_only=True)
class ParseOneOption(ParserOption[T], _t.Generic[T]):
    """
    An option with a single argument that uses Yuio parser.

    """

    def __init__(
        self,
        *,
        flags: list[str] | yuio.Positional,
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        parser: yuio.parse.Parser[T],
        merge: _t.Callable[[T, T], T] | None = None,
        default: T | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        super().__init__(
            flags=flags,
            allow_inline_arg=True,
            allow_implicit_inline_arg=True,
            nargs=1,
            allow_no_args=default is not yuio.MISSING and flags is yuio.POSITIONAL,
            required=required,
            metavar=parser.describe_or_def(),
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=merge,
            default=default,
            parser=parser,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        if isinstance(arguments, list):
            if not arguments and self.allow_no_args:
                return  # Don't set value so that app falls back to default.
            arguments = arguments[0]
        try:
            self.set(ns, self.parser.parse(arguments.value))
        except yuio.parse.ParsingError as e:
            e.n_arg = 0
            raise

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return (self.parser.completer(), False)


@dataclass(eq=False, kw_only=True)
class ParseManyOption(ParserOption[T], _t.Generic[T]):
    """
    An option with multiple arguments that uses Yuio parser.

    """

    def __init__(
        self,
        *,
        flags: list[str] | yuio.Positional,
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        parser: yuio.parse.Parser[T],
        merge: _t.Callable[[T, T], T] | None = None,
        default: T | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        assert parser.supports_parse_many()

        nargs = parser.get_nargs()
        allow_no_args = default is not yuio.MISSING and flags is yuio.POSITIONAL
        if nargs == "*":
            nargs = "+"
            allow_no_args = True

        super().__init__(
            flags=flags,
            allow_inline_arg=True,
            allow_implicit_inline_arg=True,
            nargs=nargs,
            allow_no_args=allow_no_args,
            required=required,
            metavar=parser.describe_many(),
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=merge,
            default=default,
            parser=parser,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        if (
            not arguments
            and self.allow_no_args
            and self.default is not yuio.MISSING
            and self.flags is yuio.POSITIONAL
        ):
            return  # Don't set value so that app falls back to default.

        if isinstance(arguments, list):
            self.set(ns, self.parser.parse_many([arg.value for arg in arguments]))
        else:
            self.set(ns, self.parser.parse(arguments.value))

    def format_alias_flags(
        self, ctx: yuio.string.ReprContext, /, *, all: bool = False
    ) -> list[_ColorizedString | tuple[_ColorizedString, str]] | None:
        aliases = super().format_alias_flags(ctx, all=all) or []
        if all:
            flag = self.primary_short_flag
            if not flag and self.primary_long_flags:
                flag = self.primary_long_flags[0]
            if not flag and self.flags:
                flag = self.flags[0]
            if flag:
                res = _ColorizedString()
                res.start_no_wrap()
                res.append_color(ctx.get_color("hl/flag:sh-usage"))
                res.append_str(flag)
                res.end_no_wrap()
                res.append_color(ctx.get_color("hl/punct:sh-usage"))
                res.append_str("=")
                res.append_color(ctx.get_color("hl/str:sh-usage"))
                res.append_str("'")
                res.append_str(self.parser.describe_or_def())
                res.append_str("'")
                comment = (
                    "can be given as a single argument with delimiter-separated list."
                )
                aliases.append((res, comment))
        return aliases

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return (self.parser.completer(), True)


@dataclass(eq=False, kw_only=True)
class CollectOption(ParserOption[T], _t.Generic[T]):
    """
    An option with single argument that collects all of its instances and passes them
    to :meth:`Parser.parse_many <yuio.parse.Parser.parse_many>`.

    """

    def __init__(
        self,
        *,
        flags: list[str] | yuio.Positional,
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        parser: yuio.parse.Parser[T],
        merge: _t.Callable[[T, T], T] | None = None,
        default: T | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        assert parser.supports_parse_many()

        if flags is yuio.POSITIONAL:
            raise TypeError(
                "ParseManyOneByOneOption can't be used with positional arguments"
            )

        nargs = parser.get_nargs()
        if nargs not in ["*", "+"]:
            raise TypeError(
                "ParseManyOneByOneOption can't be used with parser "
                "that limits length of its collection"
            )

        super().__init__(
            flags=flags,
            allow_inline_arg=True,
            allow_implicit_inline_arg=True,
            nargs=1,
            allow_no_args=False,
            required=required,
            metavar=parser.describe_many(),
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=merge,
            default=default,
            parser=parser,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        pass

    def post_process(
        self,
        cli_parser: CliParser[Namespace],
        arguments: list[Argument],
        ns: Namespace,
    ):
        self.set(ns, self.parser.parse_many([arg.value for arg in arguments]))

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return (self.parser.completer(), True)


@dataclass(eq=False, kw_only=True)
class StoreConstOption(ValueOption[T], _t.Generic[T]):
    """
    An option with no arguments that stores a constant to namespace.

    """

    const: T
    """
    Constant that will be stored.

    """

    def __init__(
        self,
        *,
        flags: list[str],
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        merge: _t.Callable[[T, T], T] | None = None,
        default: T | yuio.Missing = yuio.MISSING,
        const: T,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        self.const = const

        super().__init__(
            flags=flags,
            allow_inline_arg=False,
            allow_implicit_inline_arg=False,
            nargs=0,
            allow_no_args=True,
            required=required,
            metavar=(),
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=merge,
            default=default,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        if self.merge and self.dest in ns:
            ns[self.dest] = self.merge(ns[self.dest], self.const)
        else:
            ns[self.dest] = self.const


@dataclass(eq=False, kw_only=True)
class CountOption(StoreConstOption[int]):
    """
    An option that counts number of its appearances on the command line.

    """

    def __init__(
        self,
        *,
        flags: list[str],
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        default: int | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        super().__init__(
            flags=flags,
            required=required,
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=lambda x, y: x + y,
            default=default,
            const=1,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )

    def format_metavar(self, ctx: yuio.string.ReprContext) -> _ColorizedString:
        return _ColorizedString((ctx.get_color("hl/flag:sh-usage"), "..."))


@dataclass(eq=False, kw_only=True)
class StoreTrueOption(StoreConstOption[bool]):
    """
    An option that stores :data:`True` to namespace.

    """

    def __init__(
        self,
        *,
        flags: list[str],
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        default: bool | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        super().__init__(
            flags=flags,
            required=required,
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=None,
            default=default,
            const=True,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )


@dataclass(eq=False, kw_only=True)
class StoreFalseOption(StoreConstOption[bool]):
    """
    An option that stores :data:`False` to namespace.

    """

    def __init__(
        self,
        *,
        flags: list[str],
        required: bool = False,
        mutex_group: None | MutuallyExclusiveGroup = None,
        usage: yuio.Collapse | bool = True,
        help: str | yuio.Disabled = "",
        help_group: HelpGroup | None = None,
        show_if_inherited: bool = False,
        dest: str,
        default: bool | yuio.Missing = yuio.MISSING,
        allow_abbrev: bool = True,
        default_desc: str | None = None,
    ):
        super().__init__(
            flags=flags,
            required=required,
            mutex_group=mutex_group,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=None,
            default=default,
            const=False,
            allow_abbrev=allow_abbrev,
            default_desc=default_desc,
        )


@dataclass(eq=False, kw_only=True)
class VersionOption(Option[_t.Never]):
    """
    An option that prints app's version and stops the program.

    """

    version: str
    """
    Version to print.

    """

    def __init__(
        self,
        *,
        version: str,
        flags: list[str] = ["-V", "--version"],
        usage: yuio.Collapse | bool = yuio.COLLAPSE,
        help: str | yuio.Disabled = "Print program version and exit.",
        help_group: HelpGroup | None = MISC_GROUP,
        allow_abbrev: bool = True,
    ):
        super().__init__(
            flags=flags,
            allow_inline_arg=False,
            allow_implicit_inline_arg=False,
            nargs=0,
            allow_no_args=True,
            required=False,
            metavar=(),
            mutex_group=None,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=False,
            allow_abbrev=allow_abbrev,
            dest="_version",
            default_desc=None,
        )

        self.version = version

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        import yuio.io

        if self.version:
            yuio.io.raw(self.version, add_newline=True, to_stdout=True)
        else:
            yuio.io.raw("<unknown version>", add_newline=True, to_stdout=True)
        sys.exit(0)


@dataclass(eq=False, kw_only=True)
class BugReportOption(Option[_t.Never]):
    """
    An option that prints bug report.

    """

    settings: yuio.dbg.ReportSettings | bool | None
    """
    Settings for bug report generation.

    """

    app: yuio.app.App[_t.Any] | None
    """
    Main app of the project, used to extract project's version and dependencies.

    """

    def __init__(
        self,
        *,
        settings: yuio.dbg.ReportSettings | bool | None = None,
        app: yuio.app.App[_t.Any] | None = None,
        flags: list[str] = ["--bug-report"],
        usage: yuio.Collapse | bool = yuio.COLLAPSE,
        help: str | yuio.Disabled = "Print environment data for bug report and exit.",
        help_group: HelpGroup | None = MISC_GROUP,
        allow_abbrev: bool = True,
    ):
        super().__init__(
            flags=flags,
            allow_inline_arg=False,
            allow_implicit_inline_arg=False,
            nargs=0,
            allow_no_args=True,
            required=False,
            metavar=(),
            mutex_group=None,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=False,
            allow_abbrev=allow_abbrev,
            dest="_bug_report",
            default_desc=None,
        )

        self.settings = settings
        self.app = app

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        import yuio.dbg

        yuio.dbg.print_report(settings=self.settings, app=self.app)
        sys.exit(0)


@dataclass(eq=False, kw_only=True)
class CompletionOption(Option[_t.Never]):
    """
    An option that installs autocompletion.

    """

    _SHELLS = [
        "all",
        "uninstall",
        "bash",
        "zsh",
        "fish",
        "pwsh",
    ]

    def __init__(
        self,
        *,
        flags: list[str] = ["--completions"],
        usage: yuio.Collapse | bool = yuio.COLLAPSE,
        help: str | yuio.Disabled | None = None,
        help_group: HelpGroup | None = MISC_GROUP,
        allow_abbrev: bool = True,
    ):
        if help is None:
            shells = yuio.string.Or(f"``{shell}``" for shell in self._SHELLS)
            help = (
                "Install or update autocompletion scripts and exit.\n\n"
                f"Supported shells: {shells}."
            )
        super().__init__(
            flags=flags,
            allow_inline_arg=True,
            allow_implicit_inline_arg=True,
            nargs=1,
            allow_no_args=True,
            required=False,
            metavar="<shell>",
            mutex_group=None,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=False,
            allow_abbrev=allow_abbrev,
            dest="_completions",
            default_desc=None,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        if isinstance(arguments, list):
            argument = arguments[0].value if arguments else "all"
        else:
            argument = arguments.value

        if argument not in self._SHELLS:
            raise ArgumentError(
                "Unknown shell `%r`, should be %s",
                argument,
                yuio.string.Or(self._SHELLS),
                flag=flag,
                arguments=arguments,
                n_arg=0,
            )

        root = cli_parser._root_command
        help_parser = cli_parser._help_parser

        if argument == "uninstall":
            compdata = ""
        else:
            serializer = yuio.complete._ProgramSerializer()
            self._dump(root, serializer, [], help_parser)
            compdata = serializer.dump()

        yuio.complete._write_completions(compdata, root.name, argument)

        sys.exit(0)

    def _dump(
        self,
        command: Command[_t.Any],
        serializer: yuio.complete._ProgramSerializer,
        parent_options: list[Option[_t.Any]],
        help_parser: yuio.doc.DocParser,
    ):
        seen_flags: set[str] = set()
        seen_options: list[Option[_t.Any]] = []

        # Add command's options, keep track of flags from the current command.
        for option in command.options:
            completer, is_many = option.get_completer()
            help = option.help
            if help is not yuio.DISABLED:
                ctx = yuio.string.ReprContext.make_dummy(is_unicode=False)
                ctx.width = 60
                parsed_help = _parse_option_help(option, help_parser, ctx)
                if parsed_help:
                    lines = _CliFormatter(help_parser, ctx).format(parsed_help)
                    if not lines:
                        help = ""
                    elif len(lines) == 1:
                        help = str(lines[0])
                    else:
                        help = str(lines[0]) + ("..." if lines[1] else "")
                else:
                    help = ""
            serializer.add_option(
                flags=option.flags,
                nargs=option.nargs,
                metavar=option.metavar,
                help=help,
                completer=completer,
                is_many=is_many,
            )
            if option.flags is not yuio.POSITIONAL:
                seen_flags |= seen_flags
                seen_options.append(option)

        # Add parent options if their flags were not shadowed.
        for option in parent_options:
            assert option.flags is not yuio.POSITIONAL

            flags = [flag for flag in option.flags if flag not in seen_flags]
            if not flags:
                continue

            completer, is_many = option.get_completer()
            help = option.help
            if help is not yuio.DISABLED and not option.show_if_inherited:
                # TODO: not sure if disabling help for inherited options is
                # the best approach here.
                help = yuio.DISABLED
            nargs = option.nargs
            if option.allow_no_args:
                if nargs == 1:
                    nargs = "?"
                elif nargs == "+":
                    nargs = "*"
            serializer.add_option(
                flags=flags,
                nargs=nargs,
                metavar=option.metavar,
                help=help,
                completer=completer,
                is_many=is_many,
            )

            seen_flags |= seen_flags
            seen_options.append(option)

        for name, subcommand in command.subcommands.items():
            subcommand_serializer = serializer.add_subcommand(
                name=name, is_alias=name != subcommand.name, help=subcommand.help
            )
            self._dump(subcommand, subcommand_serializer, seen_options, help_parser)

    def get_completer(self) -> tuple[yuio.complete.Completer | None, bool]:
        return (
            yuio.complete.Choice(
                [yuio.complete.Option(shell) for shell in self._SHELLS]
            ),
            False,
        )


@dataclass(eq=False, kw_only=True)
class HelpOption(Option[_t.Never]):
    """
    An option that prints help message and stops the program.

    """

    def __init__(
        self,
        *,
        flags: list[str] = ["-h", "--help"],
        usage: yuio.Collapse | bool = yuio.COLLAPSE,
        help: str | yuio.Disabled = "Print this message and exit.",
        help_group: HelpGroup | None = MISC_GROUP,
        allow_abbrev: bool = True,
    ):
        super().__init__(
            flags=flags,
            allow_inline_arg=True,
            allow_implicit_inline_arg=True,
            nargs=0,
            allow_no_args=True,
            required=False,
            metavar=(),
            mutex_group=None,
            usage=usage,
            help=help,
            help_group=help_group,
            show_if_inherited=True,
            allow_abbrev=allow_abbrev,
            dest="_help",
            default_desc=None,
        )

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        import yuio.io
        import yuio.string

        if isinstance(arguments, list):
            argument = arguments[0].value if arguments else ""
        else:
            argument = arguments.value

        if argument not in ("all", ""):
            raise ArgumentError(
                "Unknown help scope <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>, should be %s",
                argument,
                yuio.string.Or(
                    ["all"], color="msg/text:code/sh-usage hl/flag:sh-usage"
                ),
                flag=flag,
                arguments=arguments,
                n_arg=0,
            )

        formatter = _HelpFormatter(cli_parser._help_parser, all=argument == "all")
        inherited_options = []
        seen_inherited_options = set()
        for opt in cli_parser._inherited_options.values():
            if opt not in seen_inherited_options:
                seen_inherited_options.add(opt)
                inherited_options.append(opt)
        formatter.add_command(
            " ".join(cli_parser._current_path),
            cli_parser._current_command,
            list(inherited_options),
        )

        yuio.io.raw(formatter, add_newline=True, to_stdout=True)
        sys.exit(0)


@dataclass(kw_only=True, eq=False, match_args=False)
class Command(_t.Generic[NamespaceT]):
    """
    Data about CLI interface of a single command or subcommand.

    """

    name: str
    """
    Canonical name of this command.

    """

    desc: str
    """
    Long description for a command.

    """

    help: str | yuio.Disabled
    """
    Help message for this command, displayed when listing subcommands.

    """

    epilog: str
    """
    Long description printed after command help.

    """

    usage: str
    """
    Override for usage section of CLI help.

    """

    options: list[Option[_t.Any]]
    """
    Options for this command.

    """

    subcommands: dict[str, Command[Namespace]]
    """
    Last positional option can be a sub-command.

    This is a map from subcommand's name or alias to subcommand's implementation.

    """

    subcommand_required: bool
    """
    Whether subcommand is required or optional. If no :attr:`~Command.subcommands`
    are given, this attribute is ignored.

    """

    ns_ctor: _t.Callable[[], NamespaceT]
    """
    A constructor that will be called to create namespace for command's arguments.

    """

    dest: str
    """
    Where to save subcommand's name.

    """

    ns_dest: str
    """
    Where to save subcommand's namespace.

    """

    metavar: str = "<subcommand>"
    """
    Meta variable used for subcommand option.

    """


@dataclass(eq=False, kw_only=True)
class _SubCommandOption(ValueOption[str]):
    subcommands: dict[str, Command[Namespace]]
    """
    All subcommands.

    """

    ns_dest: str
    """
    Where to save subcommand's namespace.

    """

    ns_ctor: _t.Callable[[], Namespace]
    """
    A constructor that will be called to create namespace for subcommand's arguments.

    """

    def __init__(
        self,
        *,
        subcommands: dict[str, Command[Namespace]],
        subcommand_required: bool,
        ns_dest: str,
        ns_ctor: _t.Callable[[], Namespace],
        metavar: str = "<subcommand>",
        help_group: HelpGroup | None = SUBCOMMANDS_GROUP,
        show_if_inherited: bool = False,
        dest: str,
    ):
        subcommand_names = [
            f"``{name}``"
            for name, subcommand in subcommands.items()
            if name == subcommand.name and subcommand.help is not yuio.DISABLED
        ]
        help = f"Available subcommands: {yuio.string.Or(subcommand_names)}"

        super().__init__(
            flags=yuio.POSITIONAL,
            allow_inline_arg=False,
            allow_implicit_inline_arg=False,
            nargs=1,
            allow_no_args=not subcommand_required,
            required=False,
            metavar=metavar,
            mutex_group=None,
            usage=True,
            help=help,
            help_group=help_group,
            show_if_inherited=show_if_inherited,
            dest=dest,
            merge=None,
            default=yuio.MISSING,
            allow_abbrev=False,
            default_desc=None,
        )

        self.subcommands = subcommands
        self.ns_dest = ns_dest
        self.ns_ctor = ns_ctor

        assert self.dest
        assert self.ns_dest

    def process(
        self,
        cli_parser: CliParser[Namespace],
        flag: Flag | None,
        arguments: Argument | list[Argument],
        ns: Namespace,
    ):
        assert isinstance(arguments, list)
        if not arguments:
            return
        subcommand = self.subcommands.get(arguments[0].value)
        if subcommand is None:
            raise ArgumentError(
                "Unknown subcommand <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>, can be %s",
                arguments[0].value,
                yuio.string.Or(
                    (
                        name
                        for name, subcommand in self.subcommands.items()
                        if subcommand.help != yuio.DISABLED
                    ),
                    color="msg/text:code/sh-usage hl/flag:sh-usage",
                ),
                arguments=arguments,
            )
        ns[self.dest] = subcommand.name
        ns[self.ns_dest] = new_ns = subcommand.ns_ctor()
        cli_parser._load_command(subcommand, new_ns)


@dataclass(eq=False, match_args=False, slots=True)
class _BoundOption:
    wrapped: Option[_t.Any]
    ns: Namespace
    seen: bool = False

    @property
    def usage(self):
        return self.wrapped.usage

    @property
    def flags(self):
        return self.wrapped.flags

    @property
    def nargs(self):
        return self.wrapped.nargs

    @property
    def allow_no_args(self):
        return self.wrapped.allow_no_args

    @property
    def allow_inline_arg(self):
        return self.wrapped.allow_inline_arg

    @property
    def allow_implicit_inline_arg(self):
        return self.wrapped.allow_implicit_inline_arg

    @property
    def mutex_group(self):
        return self.wrapped.mutex_group

    @property
    def required(self):
        return self.wrapped.required

    @property
    def allow_abbrev(self):
        return self.wrapped.allow_abbrev

    def nth_metavar(self, n: int) -> str:
        return self.wrapped.nth_metavar(n)


class CliParser(_t.Generic[NamespaceT]):
    """
    CLI arguments parser.

    :param command:
        root command.
    :param allow_abbrev:
        allow abbreviating CLI flags if that doesn't create ambiguity.
    :param help_parser:
        help parser that will be used to parse and display help for options
        that've failed to parse.

    """

    def __init__(
        self,
        command: Command[NamespaceT],
        /,
        *,
        help_parser: yuio.doc.DocParser,
        allow_abbrev: bool,
    ):
        self._root_command = command
        self._allow_abbrev = allow_abbrev
        self._help_parser = help_parser

    def _load_command(self, command: Command[_t.Any], ns: Namespace):
        # All pending flags and positionals should've been flushed by now.
        assert self._current_flag is None
        assert self._current_positional == len(self._positionals)

        self._inherited_options.update(
            {flag: opt.wrapped for flag, opt in self._known_long_flags.items()}
        )
        self._inherited_options.update(
            {flag: opt.wrapped for flag, opt in self._known_short_flags.items()}
        )
        self._current_path.append(command.name)

        # Update known flags and positionals.
        self._positionals = []
        seen_flags: set[str] = set()
        for option in command.options:
            bound_option = _BoundOption(option, ns)
            if option.flags is yuio.POSITIONAL:
                if option.mutex_group is not None:
                    raise TypeError(
                        f"{option}: positional arguments can't appear "
                        "in mutually exclusive groups"
                    )
                if option.nargs == 0:
                    raise TypeError(
                        f"{option}: positional arguments can't nave nargs=0"
                    )
                self._positionals.append(bound_option)
            else:
                if option.mutex_group is not None:
                    self._mutex_groups.setdefault(option.mutex_group, []).append(option)
                if not option.flags:
                    raise TypeError(f"{option}: option has no flags")
                for flag in option.flags:
                    if flag in seen_flags:
                        raise TypeError(
                            f"got multiple options with the same flag {flag}"
                        )
                    seen_flags.add(flag)
                    self._inherited_options.pop(flag, None)
                    _check_flag(flag)
                    if _is_short(flag):
                        dest = self._known_short_flags
                    else:
                        dest = self._known_long_flags
                    if flag in dest:
                        warnings.warn(
                            f"flag {flag} from subcommand {command.name} shadows "
                            f"the same flag from command {self._current_command.name}",
                            CliWarning,
                        )
                        self._finalize_unused_flag(flag, dest[flag])
                    dest[flag] = bound_option
        if command.subcommands:
            self._positionals.append(_BoundOption(_make_subcommand(command), ns))
        self._current_command = command
        self._current_positional = 0

    def parse(self, args: list[str] | None = None) -> NamespaceT:
        """
        Parse arguments and invoke their actions.

        :param args:
            CLI arguments, not including the program name (i.e. the first argument).
            If :data:`None`, use :data:`sys.argv` instead.
        :returns:
            namespace with parsed arguments.
        :raises:
            :class:`ArgumentError`, :class:`~yuio.parse.ParsingError`.

        """

        if args is None:
            args = sys.argv[1:]

        try:
            return self._parse(args)
        except ArgumentError as e:
            e.commandline = args
            e.prog = self._root_command.name
            e.subcommands = self._current_path
            e.help_parser = self._help_parser
            raise

    def _parse(self, args: list[str]) -> NamespaceT:
        self._current_command = self._root_command
        self._current_path: list[str] = []
        self._inherited_options: dict[str, Option[_t.Any]] = {}

        self._seen_mutex_groups: dict[
            MutuallyExclusiveGroup, tuple[_BoundOption, Flag]
        ] = {}
        self._mutex_groups: dict[MutuallyExclusiveGroup, list[Option[_t.Any]]] = {}

        self._current_index = 0

        self._known_long_flags: dict[str, _BoundOption] = {}
        self._known_short_flags: dict[str, _BoundOption] = {}
        self._positionals: list[_BoundOption] = []
        self._current_positional: int = 0

        self._current_flag: tuple[_BoundOption, Flag] | None = None
        self._current_flag_args: list[Argument] = []
        self._current_positional_args: list[Argument] = []

        self._post_process: dict[
            _BoundOption, tuple[list[Argument], list[Flag | None]]
        ] = {}

        root_ns = self._root_command.ns_ctor()
        self._load_command(self._root_command, root_ns)

        allow_flags = True

        for i, arg in enumerate(args):
            self._current_index = i

            # Handle `--`.
            if arg == "--" and allow_flags:
                self._flush_flag()
                allow_flags = False
                continue

            # Check what we have here.
            if allow_flags:
                result = self._detect_flag(arg)
            else:
                result = None

            if result is None:
                # This not a flag. Can be an argument to a positional/flag option.
                self._handle_positional(arg)
            else:
                # This is a flag.
                options, inline_arg = result
                self._handle_flags(options, inline_arg)

        self._finalize()

        return root_ns

    def _finalize(self):
        self._flush_flag()

        for flag, option in self._known_long_flags.items():
            self._finalize_unused_flag(flag, option)
        for flag, option in self._known_short_flags.items():
            self._finalize_unused_flag(flag, option)
        while self._current_positional < len(self._positionals):
            self._flush_positional()
        for group, options in self._mutex_groups.items():
            if group.required and group not in self._seen_mutex_groups:
                raise ArgumentError(
                    "%s %s must be provided",
                    "Either" if len(options) > 1 else "Flag",
                    yuio.string.Or(
                        (option.flags[0] for option in options if option.flags),
                        color="msg/text:code/sh-usage hl/flag:sh-usage",
                    ),
                )
        for option, (arguments, flags) in self._post_process.items():
            try:
                option.wrapped.post_process(
                    _t.cast(CliParser[Namespace], self), arguments, option.ns
                )
            except ArgumentError as e:
                if e.arguments is None:
                    e.arguments = arguments
                if e.flag is None and e.n_arg is not None and 0 <= e.n_arg < len(flags):
                    e.flag = flags[e.n_arg]
                if e.option is None:
                    e.option = option.wrapped
                raise
            except yuio.parse.ParsingError as e:
                flag = None
                if e.n_arg is not None and 0 <= e.n_arg < len(flags):
                    flag = flags[e.n_arg]
                raise ArgumentError.from_parsing_error(
                    e, flag=flag, arguments=arguments, option=option.wrapped
                )

    def _finalize_unused_flag(self, flag: str, option: _BoundOption):
        if option.required and not option.seen:
            raise ArgumentError(
                "Missing required flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>",
                flag,
            )

    def _detect_flag(
        self, arg: str
    ) -> tuple[list[tuple[_BoundOption, Flag]], Argument | None] | None:
        if not arg.startswith("-") or len(arg) <= 1:
            # This is a positional.
            return None

        if arg.startswith("--"):
            # This is a long flag.
            return self._parse_long_flag(arg)
        else:
            return self._detect_short_flag(arg)

    def _parse_long_flag(
        self, arg: str
    ) -> tuple[list[tuple[_BoundOption, Flag]], Argument | None] | None:
        if "=" in arg:
            flag, inline_arg = arg.split("=", maxsplit=1)
        else:
            flag, inline_arg = arg, None
        flag = self._make_flag(flag)
        if long_opt := self._known_long_flags.get(flag.value):
            if inline_arg is not None:
                inline_arg = self._make_arg(
                    long_opt, inline_arg, len(flag.value) + 1, flag
                )
            return [(long_opt, flag)], inline_arg

        # Try as abbreviated long flags.
        candidates: list[str] = []
        if self._allow_abbrev:
            for candidate in self._known_long_flags:
                if candidate.startswith(flag.value):
                    candidates.append(candidate)
            if len(candidates) == 1:
                candidate = candidates[0]
                opt = self._known_long_flags[candidate]
                if not opt.allow_abbrev:
                    raise ArgumentError(
                        "Unknown flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>, did you mean %s?",
                        flag,
                        candidate,
                        flag=self._make_flag(""),
                    )
                flag = self._make_flag(candidate)
                if inline_arg is not None:
                    inline_arg = self._make_arg(
                        opt, inline_arg, len(flag.value) + 1, flag
                    )
                return [(opt, flag)], inline_arg

        if candidates:
            raise ArgumentError(
                "Unknown flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>, can be %s",
                flag,
                yuio.string.Or(
                    candidates, color="msg/text:code/sh-usage hl/flag:sh-usage"
                ),
                flag=self._make_flag(""),
            )
        else:
            raise ArgumentError(
                "Unknown flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>",
                flag,
                flag=self._make_flag(""),
            )

    def _detect_short_flag(
        self, arg: str
    ) -> tuple[list[tuple[_BoundOption, Flag]], Argument | None] | None:
        # Try detecting short flags first.
        short_opts: list[tuple[_BoundOption, Flag]] = []
        inline_arg = None
        inline_arg_pos = 0
        unknown_ch = None
        for i, ch in enumerate(arg[1:]):
            if ch == "=":
                # Short flag with explicit argument.
                inline_arg_pos = i + 2
                inline_arg = arg[inline_arg_pos:]
                break
            elif short_opts and (
                short_opts[-1][0].allow_implicit_inline_arg
                or short_opts[-1][0].nargs != 0
            ):
                # Short flag with implicit argument.
                inline_arg_pos = i + 1
                inline_arg = arg[inline_arg_pos:]
                break
            elif short_opt := self._known_short_flags.get("-" + ch):
                # Short flag, arguments may follow.
                short_opts.append((short_opt, self._make_flag("-" + ch)))
            else:
                # Unknown short flag. Will try parsing as abbreviated long flag next.
                unknown_ch = ch
                break
        if short_opts and not unknown_ch:
            if inline_arg is not None:
                inline_arg = self._make_arg(
                    short_opts[-1][0], inline_arg, inline_arg_pos, short_opts[-1][1]
                )
            return short_opts, inline_arg

        # Try as signed int.
        if re.match(_NUM_RE, arg):
            # This is a positional.
            return None

        if unknown_ch and len(arg) > 2:
            raise ArgumentError(
                "Unknown flag <c msg/text:code/sh-usage hl/flag:sh-usage>-%s</c> in argument <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>",
                unknown_ch,
                arg,
                flag=self._make_flag(""),
            )
        else:
            raise ArgumentError(
                "Unknown flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>",
                arg,
                flag=self._make_flag(""),
            )

    def _make_arg(
        self, opt: _BoundOption, arg: str, pos: int, flag: Flag | None = None
    ):
        return Argument(
            arg,
            index=self._current_index,
            pos=pos,
            metavar=opt.nth_metavar(0),
            flag=flag,
        )

    def _make_flag(self, arg: str):
        return Flag(arg, self._current_index)

    def _handle_positional(self, arg: str):
        if self._current_flag is not None:
            opt, flag = self._current_flag
            # This is an argument for a flag option.
            self._current_flag_args.append(
                Argument(
                    arg,
                    index=self._current_index,
                    pos=0,
                    metavar=opt.nth_metavar(len(self._current_flag_args)),
                    flag=flag,
                )
            )
            nargs = opt.nargs
            if isinstance(nargs, int) and len(self._current_flag_args) == nargs:
                self._flush_flag()  # This flag is full.
        else:
            # This is an argument for a positional option.
            if self._current_positional >= len(self._positionals):
                raise ArgumentError(
                    "Unexpected positional argument <c msg/text:code/sh-usage hl/flag:sh-usage>%r</c>",
                    arg,
                    arguments=Argument(
                        arg, index=self._current_index, pos=0, metavar="", flag=None
                    ),
                )
            current_positional = self._positionals[self._current_positional]
            self._current_positional_args.append(
                Argument(
                    arg,
                    index=self._current_index,
                    pos=0,
                    metavar=current_positional.nth_metavar(
                        len(self._current_positional_args)
                    ),
                    flag=None,
                )
            )
            nargs = current_positional.nargs
            if isinstance(nargs, int) and len(self._current_positional_args) == nargs:
                self._flush_positional()  # This positional is full.

    def _handle_flags(
        self, options: list[tuple[_BoundOption, Flag]], inline_arg: Argument | None
    ):
        # If we've seen another flag before this one, and we were waiting
        # for that flag's arguments, flush them now.
        self._flush_flag()

        # Handle short flags in multi-arg sequence, i.e. `-li` -> `-l -i`
        for opt, name in options[:-1]:
            self._eval_option(opt, name, [])

        # Handle the last short flag in multi-arg sequence.
        opt, name = options[-1]
        if inline_arg is not None:
            # Flag with an inline argument, i.e. `-Xfoo`/`-X=foo` -> `-X foo`
            self._eval_option(opt, name, inline_arg)
        else:
            self._push_flag(opt, name)

    def _flush_positional(self):
        if self._current_positional >= len(self._positionals):
            return
        opt, args = (
            self._positionals[self._current_positional],
            self._current_positional_args,
        )

        self._current_positional += 1
        self._current_positional_args = []

        self._eval_option(opt, None, args)

    def _flush_flag(self):
        if self._current_flag is None:
            return

        (opt, name), args = (self._current_flag, self._current_flag_args)

        self._current_flag = None
        self._current_flag_args = []

        self._eval_option(opt, name, args)

    def _push_flag(self, opt: _BoundOption, flag: Flag):
        assert self._current_flag is None

        if opt.nargs == 0:
            # Flag without arguments, handle it right now.
            self._eval_option(opt, flag, [])
        else:
            # Flag with possible arguments, save it. If we see a non-flag later,
            # it will be added to this flag's arguments.
            self._current_flag = (opt, flag)
            self._current_flag_args = []

    def _eval_option(
        self, opt: _BoundOption, flag: Flag | None, arguments: Argument | list[Argument]
    ):
        if opt.mutex_group is not None:
            if seen := self._seen_mutex_groups.get(opt.mutex_group):
                raise ArgumentError(
                    "Flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c> can't be given together with flag <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>",
                    flag or self._make_flag(opt.nth_metavar(0)),
                    seen[1],
                )
            self._seen_mutex_groups[opt.mutex_group] = (
                opt,
                flag or self._make_flag(opt.nth_metavar(0)),
            )

        if isinstance(arguments, list):
            _check_nargs(opt, flag, arguments)
        elif not opt.allow_inline_arg:
            raise ArgumentError(
                "This flag can't have arguments",
                flag=flag,
                arguments=arguments,
                option=opt.wrapped,
            )

        opt.seen = True
        try:
            opt.wrapped.process(
                _t.cast(CliParser[Namespace], self), flag, arguments, opt.ns
            )
        except ArgumentError as e:
            if e.flag is None:
                e.flag = flag
            if e.arguments is None:
                e.arguments = arguments
            if e.option is None:
                e.option = opt.wrapped
            raise
        except yuio.parse.ParsingError as e:
            raise ArgumentError.from_parsing_error(
                e, flag=flag, arguments=arguments, option=opt.wrapped
            )

        if not isinstance(arguments, list):
            arguments = [arguments]
        if opt not in self._post_process:
            self._post_process[opt] = ([], [])
        self._post_process[opt][0].extend(arguments)
        self._post_process[opt][1].extend([flag] * len(arguments))


def _check_flag(flag: str):
    if not flag.startswith("-"):
        raise TypeError(f"flag {flag!r} should start with `-`")
    if len(flag) == 2:
        if not re.match(_SHORT_FLAG_RE, flag):
            raise TypeError(f"invalid short flag {flag!r}")
    elif len(flag) == 1:
        raise TypeError(f"flag {flag!r} is too short")
    else:
        if not re.match(_LONG_FLAG_RE, flag):
            raise TypeError(f"invalid long flag {flag!r}")


def _is_short(flag: str):
    return flag.startswith("-") and len(flag) == 2 and flag != "--"


def _make_subcommand(command: Command[Namespace]):
    return _SubCommandOption(
        metavar=command.metavar,
        subcommands=command.subcommands,
        subcommand_required=command.subcommand_required,
        dest=command.dest,
        ns_dest=command.ns_dest,
        ns_ctor=command.ns_ctor,
    )


def _check_nargs(opt: _BoundOption, flag: Flag | None, args: list[Argument]):
    if not args and opt.allow_no_args:
        return
    match opt.nargs:
        case "+":
            if not args:
                if opt.flags is yuio.POSITIONAL:
                    raise ArgumentError(
                        "Missing required positional <c msg/text:code/sh-usage hl/flag:sh-usage>%s</c>",
                        opt.nth_metavar(0),
                        flag=flag,
                        option=opt.wrapped,
                    )
                else:
                    raise ArgumentError(
                        "Expected at least `1` argument, got `0`",
                        flag=flag,
                        option=opt.wrapped,
                    )
        case n:
            if len(args) < n and (opt.flags is yuio.POSITIONAL):
                s = "" if n - len(args) == 1 else "s"
                raise ArgumentError(
                    "Missing required positional%s %s",
                    s,
                    yuio.string.JoinStr(
                        [opt.nth_metavar(i) for i in range(len(args), n)],
                        color="msg/text:code/sh-usage hl/flag:sh-usage",
                    ),
                    flag=flag,
                    option=opt.wrapped,
                )
            elif len(args) != n:
                s = "" if n == 1 else "s"
                raise ArgumentError(
                    "Expected `%s` argument%s, got `%s`",
                    n,
                    s,
                    len(args),
                    flag=flag,
                    option=opt.wrapped,
                )


def _quote_and_adjust_pos(s: str, pos: tuple[int, int]):
    s = s.translate(_UNPRINTABLE_TRANS)

    if not s:
        return "''", (1, 1)
    elif not re.search(r"[^\w@%+=:,./-]", s, re.ASCII):
        return s, pos

    start, end = pos

    start_shift = 1 + s[:start].count("'") * 4
    end_shift = start_shift + s[start:end].count("'") * 4

    return "'" + s.replace("'", "'\"'\"'") + "'", (start + start_shift, end + end_shift)


def _quote(s: str):
    s = s.translate(_UNPRINTABLE_TRANS)

    if not s:
        return "''"
    elif not re.search(r"[^\w@%+=:,./-]", s, re.ASCII):
        return s
    else:
        return "'" + s.replace("'", "'\"'\"'") + "'"


class _HelpFormatter:
    def __init__(self, parser: yuio.doc.DocParser, all: bool = False) -> None:
        self.nodes: list[yuio.doc.AstBase] = []
        self.parser = parser
        self.all = all

    def add_command(
        self, prog: str, cmd: Command[Namespace], inherited: list[Option[_t.Any]], /
    ):
        self._add_usage(prog, cmd, inherited)
        if cmd.desc:
            self.nodes.extend(self.parser.parse(cmd.desc).items)
        self._add_options(cmd)
        self._add_subcommands(cmd)
        self._add_flags(cmd, inherited)
        if cmd.epilog:
            self.nodes.append(_ResetIndentation())
            self.nodes.extend(self.parser.parse(cmd.epilog).items)

    def __colorized_str__(self, ctx: yuio.string.ReprContext) -> _ColorizedString:
        return self.format(ctx)

    def format(self, ctx: yuio.string.ReprContext):
        res = _ColorizedString()
        lines = _CliFormatter(self.parser, ctx, all=self.all).format(
            yuio.doc.Document(items=self.nodes)
        )
        sep = False
        for line in lines:
            if sep:
                res.append_str("\n")
            res.append_colorized_str(line)
            sep = True
        return res

    def _add_usage(
        self, prog: str, cmd: Command[Namespace], inherited: list[Option[_t.Any]], /
    ):
        self.nodes.append(_Usage(prog=prog, cmd=cmd, inherited=inherited))

    def _add_options(self, cmd: Command[Namespace], /):
        groups: dict[HelpGroup, list[Option[_t.Any]]] = {}
        for opt in cmd.options:
            if opt.flags is not yuio.POSITIONAL:
                continue
            if opt.help is yuio.DISABLED:
                continue
            group = opt.help_group or ARGS_GROUP
            if group.help is yuio.DISABLED:
                continue
            if group not in groups:
                groups[group] = []
            groups[group].append(opt)
        for group, options in groups.items():
            assert group.help is not yuio.DISABLED
            self.nodes.append(
                yuio.doc.Heading(
                    items=self.parser.parse_paragraph(group.title), level=1
                )
            )
            if group.help:
                self.nodes.append(
                    yuio.doc.NoHeadings(items=self.parser.parse(group.help).items)
                )
            arg_group = _HelpArgGroup(items=[])
            for opt in options:
                assert opt.help is not yuio.DISABLED
                arg_group.items.append(_HelpArg(opt))
            self.nodes.append(arg_group)

    def _add_subcommands(self, cmd: Command[Namespace], /):
        subcommands: dict[Command[Namespace], list[str]] = {}
        for name, subcommand in cmd.subcommands.items():
            if subcommand.help is yuio.DISABLED:
                continue
            if subcommand not in subcommands:
                subcommands[subcommand] = [name]
            else:
                subcommands[subcommand].append(name)
        if not subcommands:
            return
        group = SUBCOMMANDS_GROUP
        self.nodes.append(
            yuio.doc.Heading(items=self.parser.parse_paragraph(group.title), level=1)
        )
        if group.help:
            self.nodes.append(
                yuio.doc.NoHeadings(items=self.parser.parse(group.help).items)
            )
        arg_group = _HelpArgGroup(items=[])
        for subcommand, names in subcommands.items():
            assert subcommand.help is not yuio.DISABLED
            arg_group.items.append(_HelpSubCommand(names, subcommand.help))
        self.nodes.append(arg_group)

    def _add_flags(self, cmd: Command[Namespace], inherited: list[Option[_t.Any]], /):
        groups: dict[
            HelpGroup, tuple[list[Option[_t.Any]], list[Option[_t.Any]], int]
        ] = {}
        for i, opt in enumerate(cmd.options + inherited):
            if not opt.flags:
                continue
            if opt.help is yuio.DISABLED:
                continue
            group = opt.help_group or OPTS_GROUP
            if group.help is yuio.DISABLED:
                continue
            is_inherited = i >= len(cmd.options)
            if group not in groups:
                groups[group] = ([], [], 0)
            if opt.required or (opt.mutex_group and opt.mutex_group.required):
                groups[group][0].append(opt)
            elif is_inherited and not opt.show_if_inherited and not self.all:
                required, optional, n_inherited = groups[group]
                groups[group] = required, optional, n_inherited + 1
            else:
                groups[group][1].append(opt)
        for group, (required, optional, n_inherited) in groups.items():
            assert group.help is not yuio.DISABLED

            if group.collapse and not self.all and not (required or optional):
                continue

            self.nodes.append(
                yuio.doc.Heading(
                    items=self.parser.parse_paragraph(group.title), level=1
                )
            )

            if group.collapse and not self.all:
                all_flags: set[str] = set()
                for opt in required or optional:
                    all_flags.update(opt.primary_long_flags or [])
                if len(all_flags) == 1:
                    prefix = all_flags.pop()
                else:
                    prefix = _commonprefix(all_flags)
                if not prefix:
                    prefix = "--*"
                elif prefix.endswith("-"):
                    prefix += "*"
                else:
                    prefix += "-*"
                help = yuio.doc.NoHeadings(items=self.parser.parse(group.help).items)
                self.nodes.append(
                    _CollapsedOpt(
                        flags=[prefix],
                        items=[help],
                    )
                )
                continue

            if group.help and (required or optional):
                self.nodes.append(
                    yuio.doc.NoHeadings(items=self.parser.parse(group.help).items)
                )
            arg_group = _HelpArgGroup(items=[])
            for opt in required:
                assert opt.help is not yuio.DISABLED
                arg_group.items.append(_HelpOpt(opt))
            for opt in optional:
                assert opt.help is not yuio.DISABLED
                arg_group.items.append(_HelpOpt(opt))
            if n_inherited > 0:
                arg_group.items.append(_InheritedOpts(n_inherited=n_inherited))
            self.nodes.append(arg_group)


def _format_metavar(metavar: str, ctx: yuio.string.ReprContext):
    punct_color = ctx.get_color("hl/punct:sh-usage")
    metavar_color = ctx.get_color("hl/metavar:sh-usage")

    res = _ColorizedString()
    is_punctuation = False
    for part in re.split(r"((?:[{}()[\]\\;!&|]|\s)+)", metavar):
        if is_punctuation:
            res.append_color(punct_color)
        else:
            res.append_color(metavar_color)
        res.append_str(part)
        is_punctuation = not is_punctuation

    return res


_ARGS_COLUMN_WIDTH = 26
_ARGS_COLUMN_WIDTH_NARROW = 8


class _CliFormatter(yuio.doc.Formatter):  # type: ignore
    def __init__(
        self,
        parser: yuio.doc.DocParser,
        ctx: yuio.string.ReprContext,
        /,
        *,
        all: bool = False,
    ):
        self.parser = parser
        self.all = all

        self._heading_indent = contextlib.ExitStack()
        self._args_column_width = (
            _ARGS_COLUMN_WIDTH if ctx.width >= 50 else _ARGS_COLUMN_WIDTH_NARROW
        )
        ctx.width = min(ctx.width, 80)

        super().__init__(ctx, allow_headings=True)

        self.base_color = self.ctx.get_color("msg/text:code/sh-usage")
        self.prog_color = self.base_color | self.ctx.get_color("hl/prog:sh-usage")
        self.punct_color = self.base_color | self.ctx.get_color("hl/punct:sh-usage")
        self.metavar_color = self.base_color | self.ctx.get_color("hl/metavar:sh-usage")
        self.flag_color = self.base_color | self.ctx.get_color("hl/flag:sh-usage")

    def _format_Heading(self, node: yuio.doc.Heading):
        if not self._allow_headings:
            with self._with_color("msg/text:paragraph"):
                self._format_Text(node)
            return

        if node.level == 1:
            self._heading_indent.close()

            raw_heading = "".join(map(str, node.items))
            if raw_heading and raw_heading[-1].isalnum():
                node.items.append(":")

        decoration = self.ctx.get_msg_decoration("heading/section")
        with (
            self._with_indent("msg/decoration:heading/section", decoration),
            self._with_color("msg/text:heading/section"),
        ):
            self._format_Text(node)

        if node.level == 1:
            self._heading_indent.enter_context(self._with_indent(None, "  "))
        elif self._separate_paragraphs:
            self._line(self._indent)

        self._is_first_line = True

    def _format_ResetIndentation(self, node: _ResetIndentation):
        self._heading_indent.close()
        self._is_first_line = True

    def _format_Usage(self, node: _Usage):
        if node.prefix:
            prefix = _ColorizedString(
                self.ctx.get_color("msg/text:heading/section"),
                node.prefix,
                self.base_color,
                " ",
            )
        else:
            prefix = _ColorizedString()

        usage = _ColorizedString()
        if node.cmd.usage:
            sh_usage_highlighter, sh_usage_syntax_name = yuio.hl.get_highlighter(
                "sh-usage"
            )

            usage = sh_usage_highlighter.highlight(
                node.cmd.usage.rstrip(),
                theme=self.ctx.theme,
                syntax=sh_usage_syntax_name,
            ).percent_format({"prog": node.prog}, self.ctx)
        else:
            usage = self._build_usage(node)

        with self._with_indent(None, prefix):
            self._line(
                usage.indent(
                    indent=self._indent,
                    continuation_indent=self._continuation_indent,
                )
            )

    def _build_usage(self, node: _Usage):
        flags_and_groups: list[
            Option[_t.Any] | tuple[MutuallyExclusiveGroup, list[Option[_t.Any]]]
        ] = []
        positionals: list[Option[_t.Any]] = []
        groups: dict[MutuallyExclusiveGroup, list[Option[_t.Any]]] = {}
        has_grouped_flags = False

        for i, opt in enumerate(node.cmd.options + node.inherited):
            is_inherited = i >= len(node.cmd.options)
            if is_inherited and (
                not opt.show_if_inherited or opt.flags is yuio.POSITIONAL
            ):
                continue
            if opt.help is yuio.DISABLED:
                continue
            if opt.help_group is not None and opt.help_group.help is yuio.DISABLED:
                continue
            if opt.flags is yuio.POSITIONAL:
                positionals.append(opt)
            elif opt.usage is yuio.COLLAPSE:
                has_grouped_flags = True
            elif not opt.usage:
                pass
            elif opt.mutex_group:
                if opt.mutex_group not in groups:
                    group_items = []
                    groups[opt.mutex_group] = group_items
                    flags_and_groups.append((opt.mutex_group, group_items))
                else:
                    group_items = groups[opt.mutex_group]
                group_items.append(opt)
            else:
                flags_and_groups.append(opt)

        res = _ColorizedString()
        res.append_color(self.prog_color)
        res.append_str(node.prog)

        if has_grouped_flags:
            res.append_color(self.base_color)
            res.append_str(" ")
            res.append_color(self.flag_color)
            res.append_str("<options>")

        res.append_color(self.base_color)

        in_opt_short_group = False
        for flag_or_group in flags_and_groups:
            match flag_or_group:
                case (group, flags):
                    res.append_color(self.base_color)
                    res.append_str(" ")
                    res.append_color(self.punct_color)
                    res.append_str("(" if group.required else "[")
                    sep = False
                    for flag in flags:
                        if sep:
                            res.append_str("|")
                        usage, _ = flag.format_usage(self.ctx)
                        res.append_colorized_str(usage.with_base_color(self.base_color))
                        sep = True
                    res.append_str(")" if group.required else "]")
                case flag:
                    usage, can_group = flag.format_usage(self.ctx)
                    if not flag.primary_short_flag or flag.nargs != 0 or flag.required:
                        can_group = False

                    if can_group:
                        if not in_opt_short_group:
                            res.append_color(self.base_color)
                            res.append_str(" ")
                            res.append_color(self.punct_color)
                            res.append_str("[")
                            res.append_color(self.flag_color)
                            res.append_str("-")
                            in_opt_short_group = True
                        letter = (flag.primary_short_flag or "")[1:]
                        res.append_str(letter)
                        continue

                    if in_opt_short_group:
                        res.append_color(self.punct_color)
                        res.append_str("]")
                        in_opt_short_group = False

                    res.append_color(self.base_color)
                    res.append_str(" ")

                    if not flag.required:
                        res.append_color(self.punct_color)
                        res.append_str("[")
                    res.append_colorized_str(usage.with_base_color(self.base_color))
                    if not flag.required:
                        res.append_color(self.punct_color)
                        res.append_str("]")

        if in_opt_short_group:
            res.append_color(self.punct_color)
            res.append_str("]")
            in_opt_short_group = False

        for positional in positionals:
            res.append_color(self.base_color)
            res.append_str(" ")
            res.append_colorized_str(
                positional.format_usage(self.ctx)[0].with_base_color(self.base_color)
            )

        if node.cmd.subcommands:
            res.append_str(" ")
            if not node.cmd.subcommand_required:
                res.append_color(self.punct_color)
                res.append_str("[")
            res.append_colorized_str(
                _format_metavar(node.cmd.metavar, self.ctx).with_base_color(
                    self.base_color
                )
            )
            res.append_color(self.base_color)
            res.append_str(" ")
            res.append_color(self.metavar_color)
            res.append_str("...")
            if not node.cmd.subcommand_required:
                res.append_color(self.punct_color)
                res.append_str("]")

        return res

    def _format_HelpOpt(self, node: _HelpOpt):
        lead = _ColorizedString()
        if node.arg.primary_short_flag:
            lead.append_color(self.flag_color)
            lead.append_str(node.arg.primary_short_flag)
            sep = True
        else:
            lead.append_color(self.base_color)
            lead.append_str("    ")
            sep = False
        for flag in node.arg.primary_long_flags or []:
            if sep:
                lead.append_color(self.punct_color)
                lead.append_str(", ")
            lead.append_color(self.flag_color)
            lead.append_str(flag)
            sep = True

        lead.append_colorized_str(
            node.arg.format_metavar(self.ctx).with_base_color(self.base_color)
        )

        help = _parse_option_help(node.arg, self.parser, self.ctx, all=self.all)

        if help is None:
            self._line(self._indent + lead)
            return

        if lead.width + 2 > self._args_column_width:
            self._line(self._indent + lead)
            indent_ctx = self._with_indent(None, " " * self._args_column_width)
        else:
            indent_ctx = self._with_indent(None, self._make_lead_padding(lead))

        with indent_ctx:
            self._format(help)

    def _format_HelpArg(self, node: _HelpArg):
        lead = _format_metavar(node.arg.nth_metavar(0), self.ctx).with_base_color(
            self.base_color
        )

        help = _parse_option_help(node.arg, self.parser, self.ctx, all=self.all)

        if help is None:
            self._line(self._indent + lead)
            return

        if lead.width + 2 > self._args_column_width:
            self._line(self._indent + lead)
            indent_ctx = self._with_indent(None, " " * self._args_column_width)
        else:
            indent_ctx = self._with_indent(None, self._make_lead_padding(lead))

        with indent_ctx:
            self._format(help)

    def _format_HelpSubCommand(self, node: _HelpSubCommand):
        lead = _ColorizedString()
        sep = False
        for name in node.names:
            if sep:
                lead.append_color(self.punct_color)
                lead.append_str(", ")
            lead.append_color(self.flag_color)
            lead.append_str(name)
            sep = True

        help = node.help

        if not help:
            self._line(self._indent + lead)
            return

        if lead.width + 2 > self._args_column_width:
            self._line(self._indent + lead)
            indent_ctx = self._with_indent(None, " " * self._args_column_width)
        else:
            indent_ctx = self._with_indent(None, self._make_lead_padding(lead))

        with indent_ctx:
            self._format(self.parser.parse(help))

    def _format_CollapsedOpt(self, node: _CollapsedOpt):
        if not node.flags:
            self._format_Container(node)
            return

        lead = _ColorizedString()
        sep = False
        for flag in node.flags:
            if sep:
                lead.append_color(self.punct_color)
                lead.append_str(", ")
            lead.append_color(self.flag_color)
            lead.append_str(flag)
            sep = True

        if lead.width + 2 > self._args_column_width:
            self._line(self._indent + lead)
            indent_ctx = self._with_indent(None, " " * self._args_column_width)
        else:
            indent_ctx = self._with_indent(None, self._make_lead_padding(lead))

        with indent_ctx:
            self._separate_paragraphs = False
            self._allow_headings = False
            self._format_Container(node)
            self._separate_paragraphs = True
            self._allow_headings = True

    def _format_InheritedOpts(self, node: _InheritedOpts):
        raw = _ColorizedString()
        s = "" if node.n_inherited == 1 else "s"
        raw.append_color(self.ctx.get_color("secondary_color"))
        raw.append_str(f"  +{node.n_inherited} global option{s}, --help=all to show")
        self._line(raw)

    def _format_HelpArgGroup(self, node: _HelpArgGroup):
        self._separate_paragraphs = False
        self._allow_headings = False
        self._format_Container(node)
        self._separate_paragraphs = True
        self._allow_headings = True

    def _make_lead_padding(self, lead: _ColorizedString):
        color = self.base_color
        return lead + color + " " * (self._args_column_width - lead.width)


@dataclass(eq=False, match_args=False, slots=True)
class _ResetIndentation(yuio.doc.AstBase):
    pass


@dataclass(eq=False, match_args=False, slots=True)
class _Usage(yuio.doc.AstBase):
    prog: str
    cmd: Command[Namespace]
    inherited: list[Option[_t.Any]]
    prefix: str = "Usage:"


@dataclass(eq=False, match_args=False, slots=True)
class _HelpOpt(yuio.doc.AstBase):
    arg: Option[_t.Any]


@dataclass(eq=False, match_args=False, slots=True)
class _CollapsedOpt(yuio.doc.Container[yuio.doc.AstBase]):
    flags: list[str]


@dataclass(eq=False, match_args=False, slots=True)
class _HelpArg(yuio.doc.AstBase):
    arg: Option[_t.Any]


@dataclass(eq=False, match_args=False, slots=True)
class _InheritedOpts(yuio.doc.AstBase):
    n_inherited: int


@dataclass(eq=False, match_args=False, slots=True)
class _HelpSubCommand(yuio.doc.AstBase):
    names: list[str]
    help: str | None


@dataclass(eq=False, match_args=False, slots=True)
class _HelpArgGroup(yuio.doc.Container[yuio.doc.AstBase]):
    pass


class _ShortUsageFormatter:
    def __init__(
        self,
        parser: yuio.doc.DocParser,
        subcommands: list[str] | None,
        option: Option[_t.Any],
    ):
        self.parser = parser
        self.subcommands = subcommands
        self.option = option

    def __colorized_str__(self, ctx: yuio.string.ReprContext) -> _ColorizedString:
        note_color = ctx.get_color("msg/text:error/note")
        heading_color = ctx.get_color("msg/text:heading/note")
        code_color = ctx.get_color("msg/text:code/sh-usage")
        punct_color = code_color | ctx.get_color("hl/punct:sh-usage")
        flag_color = code_color | ctx.get_color("hl/flag:sh-usage")

        res = _ColorizedString()
        res.append_color(heading_color)
        res.append_str("Help: ")

        if self.option.flags is not yuio.POSITIONAL:
            sep = False
            if self.option.primary_short_flag:
                res.append_color(flag_color)
                res.append_str(self.option.primary_short_flag)
                sep = True
            for flag in self.option.primary_long_flags or []:
                if sep:
                    res.append_color(punct_color)
                    res.append_str(", ")
                res.append_color(flag_color)
                res.append_str(flag)
                sep = True

        res.append_colorized_str(
            self.option.format_metavar(ctx).with_base_color(code_color)
        )

        res.append_color(heading_color)
        res.append_str("\n")
        res.append_color(note_color)

        if help := _parse_option_help(self.option, self.parser, ctx):
            with ctx.with_settings(width=ctx.width - 2):
                formatter = _CliFormatter(self.parser, ctx)
                sep = False
                for line in formatter.format(_HelpArgGroup(items=[help])):
                    if sep:
                        res.append_str("\n")
                    res.append_str("  ")
                    res.append_colorized_str(line.with_base_color(note_color))
                    sep = True

        return res


def _parse_option_help(
    option: Option[_t.Any],
    parser: yuio.doc.DocParser,
    ctx: yuio.string.ReprContext,
    /,
    *,
    all: bool = False,
) -> yuio.doc.AstBase | None:
    help = parser.parse(option.help or "")
    if help_tail := option.format_help_tail(ctx, all=all):
        help.items.append(yuio.doc.Raw(raw=help_tail))

    return help if help.items else None
