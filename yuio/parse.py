# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Everything to do with parsing user input.

Use provided classes to construct parsers and add validation::

    >>> # Parses a string that matches the given regex.
    >>> ident = Regex(Str(), r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    >>> # Parses a non-empty list of strings.
    >>> idents = LenGe(List(ident), 1)

Pass a parser to other yuio functions::

    >>> yuio.io.ask('List of modules to reformat', parser=idents) # doctest: +SKIP

Or parse strings yourself::

    >>> idents.parse('sys os enum dataclasses')
    ['sys', 'os', 'enum', 'dataclasses']

Build a parser from type hints::

    >>> from_type_hint(list[int] | None)
    Optional(List(Int))


Parser basics
-------------

All parsers are derived from the same base class :class:`Parser`,
which describes parsing API.

.. autoclass:: Parser

    .. automethod:: parse

    .. automethod:: parse_many

    .. automethod:: supports_parse_many

    .. automethod:: parse_config

.. autoclass:: ParsingError
    :members:


Value parsers
-------------

.. autoclass:: Str

.. autoclass:: Int

.. autoclass:: Float

.. autoclass:: Bool

.. autoclass:: Enum

.. autoclass:: Decimal

.. autoclass:: Fraction

.. autoclass:: DateTime

.. autoclass:: Date

.. autoclass:: Time

.. autoclass:: TimeDelta

.. autoclass:: Seconds

.. autoclass:: Json

.. autoclass:: List

.. autoclass:: Set

.. autoclass:: FrozenSet

.. autoclass:: Dict

.. autoclass:: Tuple

.. autoclass:: Optional

.. autoclass:: Union

.. autoclass:: Path

.. autoclass:: NonExistentPath

.. autoclass:: ExistingPath

.. autoclass:: File

.. autoclass:: Dir

.. autoclass:: GitRepo

.. autoclass:: Secret


.. _validating-parsers:

Validators
----------

.. autoclass:: Regex

.. autoclass:: Bound

.. autoclass:: Gt

.. autoclass:: Ge

.. autoclass:: Lt

.. autoclass:: Le

.. autoclass:: LenBound

.. autoclass:: LenGt

.. autoclass:: LenGe

.. autoclass:: LenLt

.. autoclass:: LenLe

.. autoclass:: OneOf


Auxiliary parsers
-----------------

.. autoclass:: Map

.. autoclass:: Apply

.. autoclass:: Lower

.. autoclass:: Upper

.. autoclass:: CaseFold

.. autoclass:: Strip

.. autoclass:: WithMeta


Deriving parsers from type hints
--------------------------------

There is a way to automatically derive basic parsers from type hints
(used by :mod:`yuio.config`):

.. autofunction:: from_type_hint


.. _partial parsers:

Partial parsers
---------------

Sometimes it's not convenient to provide a parser for a complex type when
all we need is to make a small adjustment to a part of the type. For example:

.. invisible-code-block: python

    from yuio.config import Config, field

.. code-block:: python

    class AppConfig(Config):
        max_line_width: int | str = field(
            default="default",
            parser=Union(
                Gt(Int(), 0),
                OneOf(Str(), ["default", "unlimited", "keep"]),
            ),
        )

.. invisible-code-block: python

    AppConfig()

Instead, we can use :obj:`typing.Annotated` to attach validating parsers directly
to type hints:

.. code-block:: python

    from typing import Annotated


    class AppConfig(Config):
        max_line_width: (
            Annotated[int, Gt(0)]
            | Annotated[str, OneOf(["default", "unlimited", "keep"])]
        ) = "default"

.. invisible-code-block: python

    AppConfig()

Notice that we didn't specify inner parsers for :class:`Gt` and :class:`OneOf`.
This is because their internal parsers are derived from type hint, so we only care
about their settings.

Parsers created in such a way are called "partial". You can't use a partial parser
on its own because it doesn't have full information about the object's type.
You can only use partial parsers in type hints::

    >>> partial_parser = List(delimiter=",")
    >>> partial_parser.parse_with_ctx("1,2,3")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    TypeError: List requires an inner parser
    ...


Other parser methods
--------------------

:class:`Parser` defines some more methods and attributes.
They're rarely used because Yuio handles everything they do itself.
However, you can still use them in case you need to.

.. autoclass:: Parser
    :noindex:

    .. autoattribute:: __wrapped_parser__

    .. automethod:: parse_with_ctx

    .. automethod:: parse_many_with_ctx

    .. automethod:: parse_config_with_ctx

    .. automethod:: get_nargs

    .. automethod:: check_type

    .. automethod:: assert_type

    .. automethod:: describe

    .. automethod:: describe_or_def

    .. automethod:: describe_many

    .. automethod:: describe_value

    .. automethod:: options

    .. automethod:: completer

    .. automethod:: widget

    .. automethod:: to_json_schema

    .. automethod:: to_json_value

    .. automethod:: is_secret


Building your own parser
------------------------

.. _parser hierarchy:

Understanding parser hierarchy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The topmost class in the parser hierarchy is :class:`PartialParser`. It provides
abstract methods to deal with `partial parsers`_. The primary parser interface,
:class:`Parser`, is derived from it. Below :class:`Parser`, there are several
abstract classes that provide boilerplate implementations for common use cases.

.. raw:: html

    <p>
    <pre class="mermaid">
    ---
    config:
        class:
            hideEmptyMembersBox: true
    ---
    classDiagram

    class PartialParser
    click PartialParser href "#yuio.parse.PartialParser" "yuio.parse.PartialParser"

    class Parser
    click Parser href "#yuio.parse.Parser" "yuio.parse.Parser"
    PartialParser <|-- Parser

    class ValueParser
    click ValueParser href "#yuio.parse.ValueParser" "yuio.parse.ValueParser"
    Parser <|-- ValueParser

    class WrappingParser
    click WrappingParser href "#yuio.parse.WrappingParser" "yuio.parse.WrappingParser"
    Parser <|-- WrappingParser

    class MappingParser
    click MappingParser href "#yuio.parse.MappingParser" "yuio.parse.MappingParser"
    WrappingParser <|-- MappingParser

    class Map
    click Map href "#yuio.parse.Map" "yuio.parse.Map"
    MappingParser <|-- Map

    class Apply
    click Apply href "#yuio.parse.Apply" "yuio.parse.Apply"
    MappingParser <|-- Apply

    class ValidatingParser
    click ValidatingParser href "#yuio.parse.ValidatingParser" "yuio.parse.ValidatingParser"
    Apply <|-- ValidatingParser

    class CollectionParser
    click CollectionParser href "#yuio.parse.CollectionParser" "yuio.parse.CollectionParser"
    ValueParser <|-- CollectionParser
    WrappingParser <|-- CollectionParser
    </pre>
    </p>

The reason for separation of :class:`PartialParser` and :class:`Parser`
is better type checking. We want to prevent users from making a mistake of providing
a partial parser to a function that expect a fully initialized parser. For example,
consider this code:

.. skip: next

.. code-block:: python

    yuio.io.ask("Enter some names", parser=List())

This will fail because :class:`~List` needs an inner parser to function.

To annotate this behavior, we provide type hints for ``__new__`` methods
on each parser. When an inner parser is given, ``__new__`` is annotated as
returning an instance of :class:`Parser`. When inner parser is omitted,
``__new__`` is annotated as returning an instance of :class:`PartialParser`:

.. skip: next

.. code-block:: python

    from typing import TYPE_CHECKING, Any, Generic, overload

    class List(..., Generic[T]):
        if TYPE_CHECKING:
            @overload
            def __new__(cls, delimiter: str | None = None) -> PartialParser:
                ...
            @overload
            def __new__(cls, inner: Parser[T], delimiter: str | None = None) -> PartialParser:
                ...
            def __new__(cls, *args, **kwargs) -> Any:
                ...

With these type hints, our example will fail to type check: :func:`yuio.io.ask`
expects a :class:`Parser`, but ``List.__new__`` returns a :class:`PartialParser`.

Unfortunately, this means that all parsers derived from :class:`WrappingParser`
must provide appropriate type hints for their ``__new__`` method.

.. autoclass:: PartialParser
    :members:


Parsing contexts
~~~~~~~~~~~~~~~~

To track location of errors, parsers work with parsing context:
:class:`StrParsingContext` for parsing raw strings, and :class:`ConfigParsingContext`
for parsing configs.

When raising a :class:`ParsingError`, pass context to it so that we can show error
location to the user.

.. autoclass:: StrParsingContext
    :members:

.. autoclass:: ConfigParsingContext
    :members:


Base classes
~~~~~~~~~~~~

.. autoclass:: ValueParser

.. autoclass:: WrappingParser

    .. autoattribute:: _inner

    .. autoattribute:: _inner_raw

.. autoclass:: MappingParser

.. autoclass:: ValidatingParser

    .. autoattribute:: __wrapped_parser__
        :noindex:

    .. automethod:: _validate

.. autoclass:: CollectionParser

    .. autoattribute:: _allow_completing_duplicates


Adding type hint conversions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can register a converter so that :func:`from_type_hint` can derive custom
parsers from type hints:

.. autofunction:: register_type_hint_conversion(cb: Cb) -> Cb

When implementing a callback, you might need to specify a delimiter
for a collection parser. Use :func:`suggest_delim_for_type_hint_conversion`:

.. autofunction:: suggest_delim_for_type_hint_conversion


Re-imports
----------

.. type:: JsonValue
    :no-index:

    Alias of :obj:`yuio.json_schema.JsonValue`.

.. type:: SecretString
    :no-index:

    Alias of :obj:`yuio.secret.SecretString`.

.. type:: SecretValue
    :no-index:

    Alias of :obj:`yuio.secret.SecretValue`.

"""

from __future__ import annotations

import abc
import argparse
import contextlib
import dataclasses
import datetime
import decimal
import enum
import fractions
import functools
import json
import pathlib
import re
import threading
import traceback
from copy import copy as _copy

import yuio
import yuio.color
import yuio.complete
import yuio.json_schema
import yuio.string
import yuio.widget
from yuio.json_schema import JsonValue
from yuio.secret import SecretString, SecretValue
from yuio.util import find_docs as _find_docs
from yuio.util import to_dash_case as _to_dash_case

import typing
import yuio._typing_ext as _tx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "Apply",
    "Bool",
    "Bound",
    "CaseFold",
    "CollectionParser",
    "ConfigParsingContext",
    "Date",
    "DateTime",
    "Decimal",
    "Dict",
    "Dir",
    "Enum",
    "ExistingPath",
    "File",
    "Float",
    "Fraction",
    "FrozenSet",
    "Ge",
    "GitRepo",
    "Gt",
    "Int",
    "Json",
    "JsonValue",
    "Le",
    "LenBound",
    "LenGe",
    "LenGt",
    "LenLe",
    "LenLt",
    "List",
    "Lower",
    "Lt",
    "Map",
    "MappingParser",
    "NonExistentPath",
    "OneOf",
    "Optional",
    "Parser",
    "ParsingError",
    "PartialParser",
    "Path",
    "Regex",
    "Seconds",
    "Secret",
    "SecretString",
    "SecretValue",
    "Set",
    "Str",
    "StrParsingContext",
    "Strip",
    "Time",
    "TimeDelta",
    "Tuple",
    "Union",
    "Upper",
    "ValidatingParser",
    "ValueParser",
    "WithMeta",
    "WrappingParser",
    "from_type_hint",
    "register_type_hint_conversion",
    "suggest_delim_for_type_hint_conversion",
]

T_co = _t.TypeVar("T_co", covariant=True)
T = _t.TypeVar("T")
U = _t.TypeVar("U")
K = _t.TypeVar("K")
V = _t.TypeVar("V")
C = _t.TypeVar("C", bound=_t.Collection[object])
C2 = _t.TypeVar("C2", bound=_t.Collection[object])
Sz = _t.TypeVar("Sz", bound=_t.Sized)
Cmp = _t.TypeVar("Cmp", bound=_tx.SupportsLt[_t.Any])
E = _t.TypeVar("E", bound=enum.Enum)
TU = _t.TypeVar("TU", bound=tuple[object, ...])
P = _t.TypeVar("P", bound="Parser[_t.Any]")
Params = _t.ParamSpec("Params")


class ParsingError(yuio.PrettyException, ValueError, argparse.ArgumentTypeError):
    """PrettyException(msg: typing.LiteralString, /, *args: typing.Any, ctx: ConfigParsingContext | StrParsingContext | None = None, fallback_msg: typing.LiteralString | None = None, **kwargs)
    PrettyException(msg: str, /, *, ctx: ConfigParsingContext | StrParsingContext | None = None, fallback_msg: typing.LiteralString | None = None, **kwargs)

    Raised when parsing or validation fails.

    :param msg:
        message to format. Can be a literal string or any other colorable object.

        If it's given as a literal string, additional arguments for ``%``-formatting
        may be given. Otherwise, giving additional arguments will cause
        a :class:`TypeError`.
    :param args:
        arguments for ``%``-formatting the message.
    :param fallback_msg:
        fallback message that's guaranteed not to include representation of the faulty
        value, will replace `msg` when parsing secret values.

        .. warning::

            This parameter must not include contents of the faulty value. It is typed
            as :class:`~typing.LiteralString` as a deterrent; if you need string
            interpolation, create an instance of :class:`ParsingError` and set
            :attr:`~ParsingError.fallback_msg` directly.
    :param ctx:
        current error context that will be used to set :attr:`~ParsingError.raw`,
        :attr:`~ParsingError.pos`, and other attributes.
    :param kwargs:
        other keyword arguments set :attr:`~ParsingError.raw`,
        :attr:`~ParsingError.pos`, :attr:`~ParsingError.n_arg`,
        :attr:`~ParsingError.path`.

    """

    @_t.overload
    def __init__(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        fallback_msg: _t.LiteralString | None = None,
        ctx: ConfigParsingContext | StrParsingContext | None = None,
        raw: str | None = None,
        pos: tuple[int, int] | None = None,
        n_arg: int | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
    ): ...
    @_t.overload
    def __init__(
        self,
        msg: yuio.string.ToColorable | None | yuio.Missing = yuio.MISSING,
        /,
        *,
        fallback_msg: _t.LiteralString | None = None,
        ctx: ConfigParsingContext | StrParsingContext | None = None,
        raw: str | None = None,
        pos: tuple[int, int] | None = None,
        n_arg: int | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
    ): ...
    def __init__(
        self,
        *args,
        fallback_msg: _t.LiteralString | None = None,
        ctx: ConfigParsingContext | StrParsingContext | None = None,
        raw: str | None = None,
        pos: tuple[int, int] | None = None,
        n_arg: int | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
    ):
        super().__init__(*args)

        if ctx:
            if isinstance(ctx, ConfigParsingContext):
                path = path if path is not None else ctx.make_path()
            else:
                raw = raw if raw is not None else ctx.content
                pos = pos if pos is not None else (ctx.start, ctx.end)
                n_arg = n_arg if n_arg is not None else ctx.n_arg

        self.fallback_msg: yuio.string.Colorable | None = fallback_msg
        """
        This message will be used if error occurred while parsing a secret value.

        .. warning::

            This colorable must not include contents of the faulty value.

        """

        self.raw: str | None = raw
        """
        For errors that happened when parsing a string, this attribute contains the
        original string.

        """

        self.pos: tuple[int, int] | None = pos
        """
        For errors that happened when parsing a string, this attribute contains
        position in the original string in which this error has occurred (start
        and end indices).

        """

        self.n_arg: int | None = n_arg
        """
        For errors that happened in :meth:`~Parser.parse_many`, this attribute contains
        index of the string in which this error has occurred.

        """

        self.path: list[tuple[_t.Any, str | None]] | None = path
        """
        For errors that happened in :meth:`~Parser.parse_config_with_ctx`, this attribute
        contains path to the value in which this error has occurred.

        """

    @classmethod
    def type_mismatch(
        cls,
        value: _t.Any,
        /,
        *expected: type | str,
        ctx: ConfigParsingContext | StrParsingContext | None = None,
        raw: str | None = None,
        pos: tuple[int, int] | None = None,
        n_arg: int | None = None,
        path: list[tuple[_t.Any, str | None]] | None = None,
    ):
        """type_mismatch(value: _t.Any, /, *expected: type | str, **kwargs)

        Make an error with a standard message "expected type X, got type Y".

        :param value:
            value of an unexpected type.
        :param expected:
            expected types. Each argument can be a type or a string that describes
            a type.
        :param kwargs:
            keyword arguments will be passed to constructor.
        :example:
            ::

                >>> raise ParsingError.type_mismatch(10, str)
                Traceback (most recent call last):
                ...
                yuio.parse.ParsingError: Expected str, got int: 10

        """

        err = cls(
            "Expected %s, got `%s`: `%r`",
            yuio.string.Or(map(yuio.string.TypeRepr, expected)),
            yuio.string.TypeRepr(type(value)),
            value,
            ctx=ctx,
            raw=raw,
            pos=pos,
            n_arg=n_arg,
            path=path,
        )
        err.fallback_msg = yuio.string.Format(
            "Expected %s, got `%s`",
            yuio.string.Or(map(yuio.string.TypeRepr, expected)),
            yuio.string.TypeRepr(type(value)),
        )

        return err

    def set_ctx(self, ctx: ConfigParsingContext | StrParsingContext):
        if isinstance(ctx, ConfigParsingContext):
            self.path = ctx.make_path()
        else:
            self.raw = ctx.content
            self.pos = (ctx.start, ctx.end)
            self.n_arg = ctx.n_arg

    def to_colorable(self) -> yuio.string.Colorable:
        colorable = super().to_colorable()
        if self.path:
            colorable = yuio.string.Format(
                "In `%s`:\n%s",
                _PathRenderer(self.path),
                yuio.string.Indent(colorable),
            )
        if self.pos and self.raw and self.pos != (0, len(self.raw)):
            raw, pos = _repr_and_adjust_pos(self.raw, self.pos)
            colorable = yuio.string.Stack(
                _CodeRenderer(raw, pos),
                colorable,
            )
        return colorable


class PartialParser(abc.ABC):
    """
    An interface of a partial parser.

    """

    def __init__(self):
        self.__orig_traceback = traceback.extract_stack()
        while self.__orig_traceback and self.__orig_traceback[-1].filename.endswith(
            "yuio/parse.py"
        ):
            self.__orig_traceback.pop()
        super().__init__()

    def _get_orig_traceback(self) -> traceback.StackSummary:
        """
        Get stack summary for the place where this partial parser was created.

        """

        return self.__orig_traceback  # pragma: no cover

    @contextlib.contextmanager
    def _patch_stack_summary(self):
        """
        Attach original traceback to any exception that's raised
        within this context manager.

        """

        try:
            yield
        except Exception as e:
            stack_summary_text = "Traceback (most recent call last):\n" + "".join(
                self.__orig_traceback.format()
            )
            e.args = (
                f"{e}\n\nThe above error happened because of "
                f"this type hint:\n\n{stack_summary_text}",
            )
            setattr(e, "__yuio_stack_summary_text__", stack_summary_text)
            raise e

    @abc.abstractmethod
    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        """
        Apply this partial parser.

        When Yuio checks type annotations, it derives a parser for the given type hint,
        and the applies all partial parsers to it.

        For example, given this type hint:

        .. invisible-code-block: python

            from typing import Annotated

        .. code-block:: python

            field: Annotated[str, Map(str.lower)]

        Yuio will first infer parser for string (:class:`Str`), then it will pass
        this parser to ``Map.wrap``.

        :param parser:
            a parser instance that was created by inspecting type hints
            and previous annotations.
        :returns:
            a result of upgrading this parser from partial to full. This method
            usually returns copy of `self`.
        :raises:
            :class:`TypeError` if this parser can't be wrapped. Specifically, this
            method should raise a :class:`TypeError` for any non-partial parser.

        """

        return _copy(self)  # pyright: ignore[reportReturnType]


class Parser(PartialParser, _t.Generic[T_co]):
    """
    Base class for parsers.

    """

    # Original type hint from which this parser was derived.
    __typehint: _t.Any = None

    __wrapped_parser__: Parser[object] | None = None
    """
    An attribute for unwrapping parsers that validate or map results
    of other parsers.

    """

    @_t.final
    def parse(self, value: str, /) -> T_co:
        """
        Parse user input, raise :class:`ParsingError` on failure.

        :param value:
            value to parse.
        :returns:
            a parsed and processed value.
        :raises:
            :class:`ParsingError`.

        """

        return self.parse_with_ctx(StrParsingContext(value))

    @abc.abstractmethod
    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T_co:
        """
        Actual implementation of :meth:`~Parser.parse`, receives parsing context instead
        of a raw string.

        :param ctx:
            value to parse, wrapped into a parsing context.
        :returns:
            a parsed and processed value.
        :raises:
            :class:`ParsingError`.

        """

        raise NotImplementedError()

    def parse_many(self, value: _t.Sequence[str], /) -> T_co:
        """
        For collection parsers, parse and validate collection
        by parsing its items one-by-one.

        :param value:
            collection of values to parse.
        :returns:
            each value parsed and assembled into the target collection.
        :raises:
            :class:`ParsingError`. Also raises :class:`RuntimeError` if trying to call
            this method on a parser that doesn't supports parsing collections
            of objects.
        :example:
            ::

                >>> # Let's say we're parsing a set of ints.
                >>> parser = Set(Int())

                >>> # And the user enters collection items one-by-one.
                >>> user_input = ['1', '2', '3']

                >>> # We can parse collection from its items:
                >>> parser.parse_many(user_input)
                {1, 2, 3}

        """

        return self.parse_many_with_ctx(
            [StrParsingContext(item, n_arg=i) for i, item in enumerate(value)]
        )

    @abc.abstractmethod
    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> T_co:
        """
        Actual implementation of :meth:`~Parser.parse_many`, receives parsing contexts
        instead of a raw strings.

        :param ctxs:
            values to parse, wrapped into a parsing contexts.
        :returns:
            a parsed and processed value.
        :raises:
            :class:`ParsingError`.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def supports_parse_many(self) -> bool:
        """
        Return :data:`True` if this parser returns a collection
        and so supports :meth:`~Parser.parse_many`.

        :returns:
            :data:`True` if :meth:`~Parser.parse_many` is safe to call.

        """

        raise NotImplementedError()

    @_t.final
    def parse_config(self, value: object, /) -> T_co:
        """
        Parse value from a config, raise :class:`ParsingError` on failure.

        This method accepts python values that would result from
        parsing json, yaml, and similar formats.

        :param value:
            config value to parse.
        :returns:
            verified and processed config value.
        :raises:
            :class:`ParsingError`.
        :example:
            ::

                >>> # Let's say we're parsing a set of ints.
                >>> parser = Set(Int())

                >>> # And we're loading it from json.
                >>> import json
                >>> user_config = json.loads('[1, 2, 3]')

                >>> # We can process parsed json:
                >>> parser.parse_config(user_config)
                {1, 2, 3}

        """

        return self.parse_config_with_ctx(ConfigParsingContext(value))

    @abc.abstractmethod
    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T_co:
        """
        Actual implementation of :meth:`~Parser.parse_config`, receives parsing context
        instead of a raw value.

        :param ctx:
            config value to parse, wrapped into a parsing contexts.
        :returns:
            verified and processed config value.
        :raises:
            :class:`ParsingError`.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def get_nargs(self) -> _t.Literal["+", "*"] | int:
        """
        Generate ``nargs`` for argparse.

        :returns:
            `nargs` as defined by argparse. If :meth:`~Parser.supports_parse_many`
            returns :data:`True`, value should be ``"+"`` or an integer. Otherwise,
            value should be ``1``.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def check_type(self, value: object, /) -> _t.TypeGuard[T_co]:
        """
        Check whether the parser can handle a particular value in its
        :meth:`~Parser.describe_value` and other methods.

        This function is used to raise :class:`TypeError`\\ s in function that accept
        unknown values. Parsers like :class:`Union` rely on :class:`TypeError`\\ s
        to dispatch values to correct sub-parsers.

        .. note::

            For performance reasons, this method should not inspect contents
            of containers, only their type (otherwise some methods turn from linear
            to quadratic).

            This also means that validating and mapping parsers
            can always return :data:`True`.

        :param value:
            value that needs a type check.
        :returns:
            :data:`True` if the value matches the type of this parser.

        """

        raise NotImplementedError()

    def assert_type(self, value: object, /) -> _t.TypeGuard[T_co]:
        """
        Call :meth:`~Parser.check_type` and raise a :class:`TypeError`
        if it returns :data:`False`.

        This method always returns :data:`True` or throws an error, but type checkers
        don't know this. Use ``assert parser.assert_type(value)`` so that they
        understand that type of the `value` has narrowed.

        :param value:
            value that needs a type check.
        :returns:
            always returns :data:`True`.
        :raises:
            :class:`TypeError`.

        """

        if not self.check_type(value):
            raise TypeError(
                f"parser {self} can't handle value of type {_tx.type_repr(type(value))}"
            )
        return True

    @abc.abstractmethod
    def describe(self) -> str | None:
        """
        Return a human-readable description of an expected input.

        Used to describe expected input in widgets.

        :returns:
            human-readable description of an expected input. Can return :data:`None`
            for simple values that don't need a special description.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def describe_or_def(self) -> str:
        """
        Like :py:meth:`~Parser.describe`, but guaranteed to return something.

        Used to describe expected input in CLI help.

        :returns:
            human-readable description of an expected input.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def describe_many(self) -> str | tuple[str, ...]:
        """
        Return a human-readable description of a container element.

        Used to describe expected input in CLI help.

        :returns:
            human-readable description of expected inputs. If the value is a string,
            then it describes an individual member of a collection. The the value
            is a tuple, then each of the tuple's element describes an expected value
            at the corresponding position.
        :raises:
            :class:`RuntimeError` if trying to call this method on a parser
            that doesn't supports parsing collections of objects.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def describe_value(self, value: object, /) -> str:
        """
        Return a human-readable description of the given value.

        Used in error messages, and to describe returned input in widgets.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        Call :meth:`~Parser.assert_type` to check for this case.

        :param value:
            value that needs a description.
        :returns:
            description of a value in the format that this parser would expect to see
            in a CLI argument or an environment variable.
        :raises:
            :class:`TypeError` if the given value is not of type
            that this parser produces.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def options(self) -> _t.Collection[yuio.widget.Option[T_co]] | None:
        """
        Return options for a :class:`~yuio.widget.Multiselect` widget.

        This function can be implemented for parsers that return a fixed set
        of pre-defined values, like :class:`Enum` or :class:`OneOf`.
        Collection parsers may use this data to improve their widgets.
        For example, the :class:`Set` parser will use
        a :class:`~yuio.widget.Multiselect` widget.

        :returns:
            a full list of options that will be passed to
            a :class:`~yuio.widget.Multiselect` widget, or :data:`None`
            if the set of possible values is not known.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def completer(self) -> yuio.complete.Completer | None:
        """
        Return a completer for values of this parser.

        This function is used when assembling autocompletion functions for shells,
        and when reading values from user via :func:`yuio.io.ask`.

        :returns:
            a completer that will be used with CLI arguments or widgets.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T_co | yuio.Missing]:
        """
        Return a widget for reading values of this parser.

        This function is used when reading values from user via :func:`yuio.io.ask`.

        The returned widget must produce values of type ``T``. If `default` is given,
        and the user input is empty, the widget must produce
        the :data:`~yuio.MISSING` constant (*not* the default constant).
        This is because the default value might be of any type
        (for example :data:`None`), and validating parsers should not check it.

        Validating parsers must wrap the widget they got from
        :attr:`__wrapped_parser__` into :class:`~yuio.widget.Map`
        or :class:`~yuio.widget.Apply` in order to validate widget's results.

        :param default:
            default value that will be used if widget returns :data:`~yuio.MISSING`.
        :param input_description:
            a string describing what input is expected.
        :param default_description:
            a string describing default value.
        :returns:
            a widget that will be used to ask user for values. The widget can choose
            to use :func:`~Parser.completer` or :func:`~Parser.options`, or implement
            some custom logic.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        """
        Create a JSON schema object based on this parser.

        The purpose of this method is to make schemas for use in IDEs, i.e. to provide
        autocompletion or simple error checking. The returned schema is not guaranteed
        to reflect all constraints added to the parser. For example, :class:`OneOf`
        and :class:`Regex` parsers will not affect the generated schema.

        :param ctx:
            context for building a schema.
        :returns:
            a JSON schema that describes structure of values expected by this parser.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        """
        Convert given value to a representation suitable for JSON serialization.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        Call :meth:`~Parser.assert_type` to check for this case.

        :returns:
            a value converted to JSON-serializable representation.
        :raises:
            :class:`TypeError` if the given value is not of type
            that this parser produces.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def is_secret(self) -> bool:
        """
        Indicates that input functions should use secret input,
        i.e. :func:`~getpass.getpass` or :class:`yuio.widget.SecretInput`.

        """

        raise NotImplementedError()

    def __repr__(self):
        return self.__class__.__name__


class ValueParser(Parser[T], PartialParser, _t.Generic[T]):
    """
    Base implementation for a parser that returns a single value.

    Implements all method, except for :meth:`~Parser.parse_with_ctx`,
    :meth:`~Parser.parse_config_with_ctx`, :meth:`~Parser.to_json_schema`,
    and :meth:`~Parser.to_json_value`.

    :param ty:
        type of the produced value, used in :meth:`~Parser.check_type`.
    :example:
        .. invisible-code-block: python

            from dataclasses import dataclass
            @dataclass
            class MyType:
                data: str

        .. code-block:: python

            class MyTypeParser(ValueParser[MyType]):
                def __init__(self):
                    super().__init__(MyType)

                def parse_with_ctx(self, ctx: StrParsingContext, /) -> MyType:
                    return MyType(ctx.value)

                def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> MyType:
                    if not isinstance(ctx.value, str):
                        raise ParsingError.type_mismatch(value, str, ctx=ctx)
                    return MyType(ctx.value)

                def to_json_schema(
                    self, ctx: yuio.json_schema.JsonSchemaContext, /
                ) -> yuio.json_schema.JsonSchemaType:
                    return yuio.json_schema.String()

                def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
                    assert self.assert_type(value)
                    return value.data

        ::

            >>> MyTypeParser().parse('pancake')
            MyType(data='pancake')

    """

    def __init__(self, ty: type[T], /, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._value_type = ty
        """
        Type of the produced value, used in :meth:`~Parser.check_type`.

        """

    def wrap(self: P, parser: Parser[_t.Any]) -> P:
        typehint = getattr(parser, "_Parser__typehint", None)
        if typehint is None:
            with self._patch_stack_summary():
                raise TypeError(
                    f"annotating a type with {self} will override"
                    " all previous annotations. Make sure that"
                    f" {self} is the first annotation in"
                    " your type hint.\n\n"
                    "Example:\n"
                    "  Incorrect: Str() overrides effects of Map()\n"
                    "    field: typing.Annotated[str, Map(fn=str.lower), Str()]\n"
                    "                                                    ^^^^^\n"
                    "  Correct: Str() is applied first, then Map()\n"
                    "    field: typing.Annotated[str, Str(), Map(fn=str.lower)]\n"
                    "                                 ^^^^^"
                )
        if not isinstance(self, parser.__class__):
            with self._patch_stack_summary():
                raise TypeError(
                    f"annotating {_tx.type_repr(typehint)} with {self.__class__.__name__}"
                    " conflicts with default parser for this type, which is"
                    f" {parser.__class__.__name__}.\n\n"
                    "Example:\n"
                    "  Incorrect: Path() can't be used to annotate `str`\n"
                    "    field: typing.Annotated[str, Path(extensions=[...])]\n"
                    "                                 ^^^^^^^^^^^^^^^^^^^^^^\n"
                    "  Correct: using Path() to annotate `pathlib.Path`\n"
                    "    field: typing.Annotated[pathlib.Path, Path(extensions=[...])]\n"
                    "                                          ^^^^^^^^^^^^^^^^^^^^^^"
                )
        return super().wrap(parser)  # pyright: ignore[reportReturnType]

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> T:
        raise RuntimeError("unable to parse multiple values")

    def supports_parse_many(self) -> bool:
        return False

    def get_nargs(self) -> _t.Literal["+", "*"] | int:
        return 1

    def check_type(self, value: object, /) -> _t.TypeGuard[T]:
        return isinstance(value, self._value_type)

    def describe(self) -> str | None:
        return None

    def describe_or_def(self) -> str:
        return self.describe() or f"<{_to_dash_case(self.__class__.__name__)}>"

    def describe_many(self) -> str | tuple[str, ...]:
        return self.describe_or_def()

    def describe_value(self, value: object, /) -> str:
        assert self.assert_type(value)
        return str(value) or "<empty>"

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        return None

    def completer(self) -> yuio.complete.Completer | None:
        return None

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        completer = self.completer()
        return _WidgetResultMapper(
            self,
            input_description,
            default,
            (
                yuio.widget.InputWithCompletion(
                    completer,
                    placeholder=default_description or "",
                )
                if completer is not None
                else yuio.widget.Input(
                    placeholder=default_description or "",
                )
            ),
        )

    def is_secret(self) -> bool:
        return False


class WrappingParser(Parser[T], _t.Generic[T, U]):
    """
    A base for a parser that wraps another parser and alters its output.

    This base simplifies dealing with partial parsers.

    The :attr:`~WrappingParser._inner` attribute is whatever internal state you need
    to store. When it is :data:`None`, the parser is considered partial. That is,
    you can't use such a parser to actually parse anything, but you can
    use it in a type annotation. When it is not :data:`None`, the parser is considered
    non partial. You can use it to parse things, but you can't use it
    in a type annotation.

    .. warning::

        All descendants of this class must include appropriate type hints
        for their ``__new__`` method, otherwise type annotations from this base
        will shadow implementation's ``__init__`` signature.

        See section on `parser hierarchy`_ for details.

    :param inner:
        inner data or :data:`None`.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: U, /) -> WrappingParser[T, U]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: U | None, /, *args, **kwargs):
        self.__inner = inner
        super().__init__(*args, **kwargs)

    @property
    def _inner(self) -> U:
        """
        Internal resource wrapped by this parser.

        :raises:
            Accessing it when the parser is in a partial state triggers an error
            and warns user that they didn't provide an inner parser.

            Setting a new value when the parser is not in a partial state triggers
            an error and warns user that they shouldn't provide an inner parser
            in type annotations.

        """

        if self.__inner is None:
            with self._patch_stack_summary():
                raise TypeError(f"{self.__class__.__name__} requires an inner parser")
        return self.__inner

    @_inner.setter
    def _inner(self, inner: U):
        if self.__inner is not None:
            with self._patch_stack_summary():
                raise TypeError(
                    f"don't provide inner parser when using {self.__class__.__name__}"
                    " with type annotations. The inner parser will be derived automatically"
                    "from type hint.\n\n"
                    "Example:\n"
                    "  Incorrect: List() has an inner parser\n"
                    "    field: typing.Annotated[list[str], List(Str(), delimiter=';')]\n"
                    "                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^\n"
                    "  Correct: inner parser for List() derived from type hint\n"
                    "    field: typing.Annotated[list[str], List(delimiter=';')]\n"
                    "                                       ^^^^^^^^^^^^^^^^^^^"
                )
        self.__inner = inner

    @property
    def _inner_raw(self) -> U | None:
        """
        Unchecked access to the wrapped resource.

        """

        return self.__inner


class MappingParser(WrappingParser[T, Parser[U]], _t.Generic[T, U]):
    """
    This is base abstraction for :class:`Map` and :class:`Optional`.
    Forwards all calls to the inner parser, except for :meth:`~Parser.parse_with_ctx`,
    :meth:`~Parser.parse_many_with_ctx`, :meth:`~Parser.parse_config_with_ctx`,
    :meth:`~Parser.options`, :meth:`~Parser.check_type`,
    :meth:`~Parser.describe_value`, :meth:`~Parser.widget`,
    and :meth:`~Parser.to_json_value`.

    :param inner:
        mapped parser or :data:`None`.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[U], /) -> MappingParser[T, U]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: Parser[U] | None, /):
        super().__init__(inner)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner = parser  # pyright: ignore[reportAttributeAccessIssue]
        return result

    def supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def get_nargs(self) -> _t.Literal["+", "*"] | int:
        return self._inner.get_nargs()

    def describe(self) -> str | None:
        return self._inner.describe()

    def describe_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_many(self) -> str | tuple[str, ...]:
        return self._inner.describe_many()

    def completer(self) -> yuio.complete.Completer | None:
        return self._inner.completer()

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return self._inner.to_json_schema(ctx)

    def is_secret(self) -> bool:
        return self._inner.is_secret()

    def __repr__(self):
        return f"{self.__class__.__name__}({self._inner_raw!r})"

    @property
    def __wrapped_parser__(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._inner_raw


class Map(MappingParser[T, U], _t.Generic[T, U]):
    """Map(inner: Parser[U], fn: typing.Callable[[U], T], rev: typing.Callable[[T | object], U] | None = None, /)

    A wrapper that maps result of the given parser using the given function.

    :param inner:
        a parser whose result will be mapped.
    :param fn:
        a function to convert a result.
    :param rev:
        a function used to un-map a value.

        This function is used in :meth:`Parser.describe_value`
        and :meth:`Parser.to_json_value` to convert parsed value back
        to its original state.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        In this case, you should raise a :class:`TypeError`.
    :example:
        ..
            >>> import math

        ::

            >>> parser = yuio.parse.Map(
            ...     yuio.parse.Int(),
            ...     lambda x: 2 ** x,
            ...     lambda x: int(math.log2(x)),
            ... )
            >>> parser.parse("10")
            1024
            >>> parser.describe_value(1024)
            '10'

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], fn: _t.Callable[[T], T], /) -> Map[T, T]: ...

        @_t.overload
        def __new__(cls, fn: _t.Callable[[T], T], /) -> PartialParser: ...

        @_t.overload
        def __new__(
            cls,
            inner: Parser[U],
            fn: _t.Callable[[U], T],
            rev: _t.Callable[[T | object], U],
            /,
        ) -> Map[T, T]: ...

        @_t.overload
        def __new__(
            cls, fn: _t.Callable[[U], T], rev: _t.Callable[[T | object], U], /
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, *args):
        inner: Parser[U] | None = None
        fn: _t.Callable[[U], T]
        rev: _t.Callable[[T | object], U] | None = None
        if len(args) == 1:
            (fn,) = args
        elif len(args) == 2 and isinstance(args[0], Parser):
            inner, fn = args
        elif len(args) == 2:
            fn, rev = args
        elif len(args) == 3:
            inner, fn, rev = args
        else:
            raise TypeError(
                f"expected between 1 and 2 positional arguments, got {len(args)}"
            )

        self._fn = fn
        self._rev = rev
        super().__init__(inner)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T:
        res = self._inner.parse_with_ctx(ctx)
        try:
            return self._fn(res)
        except ParsingError as e:
            e.set_ctx(ctx)
            raise

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> T:
        return self._fn(self._inner.parse_many_with_ctx(ctxs))

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T:
        res = self._inner.parse_config_with_ctx(ctx)
        try:
            return self._fn(res)
        except ParsingError as e:
            e.set_ctx(ctx)
            raise

    def check_type(self, value: object, /) -> _t.TypeGuard[T]:
        return True

    def describe_value(self, value: object, /) -> str:
        if self._rev:
            value = self._rev(value)
        return self._inner.describe_value(value)

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        options = self._inner.options()
        if options is not None:
            return [
                _t.cast(
                    yuio.widget.Option[T],
                    dataclasses.replace(option, value=self._fn(option.value)),
                )
                for option in options
            ]
        else:
            return None

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        return yuio.widget.Map(
            self._inner.widget(default, input_description, default_description),
            lambda v: self._fn(v) if v is not yuio.MISSING else yuio.MISSING,
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        if self._rev:
            value = self._rev(value)
        return self._inner.to_json_value(value)


@_t.overload
def Lower(inner: Parser[str], /) -> Parser[str]: ...
@_t.overload
def Lower() -> PartialParser: ...
def Lower(*args) -> _t.Any:
    """Lower(inner: Parser[str], /)

    Applies :meth:`str.lower` to the result of a string parser.

    :param inner:
        a parser whose result will be mapped.

    """

    return Map(*args, str.lower)  # pyright: ignore[reportCallIssue]


@_t.overload
def Upper(inner: Parser[str], /) -> Parser[str]: ...
@_t.overload
def Upper() -> PartialParser: ...
def Upper(*args) -> _t.Any:
    """Upper(inner: Parser[str], /)

    Applies :meth:`str.upper` to the result of a string parser.

    :param inner:
        a parser whose result will be mapped.

    """

    return Map(*args, str.upper)  # pyright: ignore[reportCallIssue]


@_t.overload
def CaseFold(inner: Parser[str], /) -> Parser[str]: ...
@_t.overload
def CaseFold() -> PartialParser: ...
def CaseFold(*args) -> _t.Any:
    """CaseFold(inner: Parser[str], /)

    Applies :meth:`str.casefold` to the result of a string parser.

    :param inner:
        a parser whose result will be mapped.

    """

    return Map(*args, str.casefold)  # pyright: ignore[reportCallIssue]


@_t.overload
def Strip(inner: Parser[str], /) -> Parser[str]: ...
@_t.overload
def Strip() -> PartialParser: ...
def Strip(*args) -> _t.Any:
    """Strip(inner: Parser[str], /)

    Applies :meth:`str.strip` to the result of a string parser.

    :param inner:
        a parser whose result will be mapped.

    """

    return Map(*args, str.strip)  # pyright: ignore[reportCallIssue]


@_t.overload
def Regex(
    inner: Parser[str],
    regex: str | _tx.StrRePattern,
    /,
    *,
    group: int | str = 0,
) -> Parser[str]: ...
@_t.overload
def Regex(
    regex: str | _tx.StrRePattern, /, *, group: int | str = 0
) -> PartialParser: ...
def Regex(*args, group: int | str = 0) -> _t.Any:
    """Regex(inner: Parser[str], regex: str | re.Pattern[str], /, *, group: int | str = 0)

    Matches the parsed string with the given regular expression.

    If regex has capturing groups, parser can return contents of a group.

    :param regex:
        regular expression for matching.
    :param group:
        name or index of a capturing group that should be used to get the final
        parsed value.

    """

    inner: Parser[str] | None
    regex: str | _tx.StrRePattern
    if len(args) == 1:
        inner, regex = None, args[0]
    elif len(args) == 2:
        inner, regex = args
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")

    if isinstance(regex, re.Pattern):
        compiled = regex
    else:
        compiled = re.compile(regex)

    def mapper(value: str) -> str:
        if (match := compiled.match(value)) is None:
            raise ParsingError(
                "Value doesn't match regex `%s`: `%r`",
                compiled.pattern,
                value,
                fallback_msg="Incorrect value format",
            )
        return match.group(group)

    return Map(inner, mapper)  # type: ignore


class Apply(MappingParser[T, T], _t.Generic[T]):
    """Apply(inner: Parser[T], fn: typing.Callable[[T], None], /)

    A wrapper that applies the given function to the result of a wrapped parser.

    :param inner:
        a parser used to extract and validate a value.
    :param fn:
        a function that will be called after parsing a value.
    :example:
        ::

            >>> # Run `Int` parser, then print its output before returning.
            >>> print_output = Apply(Int(), lambda x: print(f"Value is {x}"))
            >>> result = print_output.parse("10")
            Value is 10
            >>> result
            10

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls, inner: Parser[T], fn: _t.Callable[[T], None], /
        ) -> Apply[T]: ...

        @_t.overload
        def __new__(cls, fn: _t.Callable[[T], None], /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, *args):
        inner: Parser[T] | None
        fn: _t.Callable[[T], None]
        if len(args) == 1:
            inner, fn = None, args[0]
        elif len(args) == 2:
            inner, fn = args
        else:
            raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")

        self._fn = fn
        super().__init__(inner)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T:
        result = self._inner.parse_with_ctx(ctx)
        try:
            self._fn(result)
        except ParsingError as e:
            e.set_ctx(ctx)
            raise
        return result

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> T:
        result = self._inner.parse_many_with_ctx(ctxs)
        self._fn(result)
        return result

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T:
        result = self._inner.parse_config_with_ctx(ctx)
        try:
            self._fn(result)
        except ParsingError as e:
            e.set_ctx(ctx)
            raise
        return result

    def check_type(self, value: object, /) -> _t.TypeGuard[T]:
        return True

    def describe_value(self, value: object, /) -> str:
        return self._inner.describe_value(value)

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        return self._inner.options()

    def completer(self) -> yuio.complete.Completer | None:
        return self._inner.completer()

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        return yuio.widget.Apply(
            self._inner.widget(default, input_description, default_description),
            lambda v: self._fn(v) if v is not yuio.MISSING else None,
        )

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return self._inner.to_json_schema(ctx)

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        return self._inner.to_json_value(value)


class ValidatingParser(Apply[T], _t.Generic[T]):
    """
    Base implementation for a parser that validates result of another parser.

    This class wraps another parser and passes all method calls to it.
    All parsed values are additionally passed to :meth:`~ValidatingParser._validate`.

    :param inner:
        a parser which output will be validated.
    :example:
        .. code-block:: python

            class IsLower(ValidatingParser[str]):
                def _validate(self, value: str, /):
                    if not value.islower():
                        raise ParsingError(
                            "Value should be lowercase: `%r`",
                            value,
                            fallback_msg="Value should be lowercase",
                        )

        ::

            >>> IsLower(Str()).parse("Not lowercase!")
            Traceback (most recent call last):
            ...
            yuio.parse.ParsingError: Value should be lowercase: 'Not lowercase!'

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], /) -> ValidatingParser[T]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: Parser[T] | None = None, /):
        super().__init__(inner, self._validate)

    @abc.abstractmethod
    def _validate(self, value: T, /):
        """
        Implementation of value validation.

        :param value:
            value which needs validating.
        :raises:
            should raise :class:`ParsingError` if validation fails.

        """

        raise NotImplementedError()


class Str(ValueParser[str]):
    """
    Parser for str values.

    """

    def __init__(self):
        super().__init__(str)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> str:
        return str(ctx.value)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> str:
        if not isinstance(ctx.value, str):
            raise ParsingError.type_mismatch(ctx.value, str, ctx=ctx)
        return str(ctx.value)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.String()

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return value


class Int(ValueParser[int]):
    """
    Parser for int values.

    """

    def __init__(self):
        super().__init__(int)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> int:
        ctx = ctx.strip_if_non_space()
        try:
            value = ctx.value.casefold()
            if value.startswith("-"):
                neg = True
                value = value[1:].lstrip()
            else:
                neg = False
            if value.startswith("0x"):
                base = 16
                value = value[2:]
            elif value.startswith("0o"):
                base = 8
                value = value[2:]
            elif value.startswith("0b"):
                base = 2
                value = value[2:]
            else:
                base = 10
            if value[:1] in "-\n\t\r\v\b ":
                raise ValueError()
            res = int(value, base=base)
            if neg:
                res = -res
            return res
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `int`",
                ctx.value,
                ctx=ctx,
                fallback_msg="Can't parse value as `int`",
            ) from None

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> int:
        value = ctx.value
        if isinstance(value, float):
            if value != int(value):  # pyright: ignore[reportUnnecessaryComparison]
                raise ParsingError.type_mismatch(value, int, ctx=ctx)
            value = int(value)
        if not isinstance(value, int):
            raise ParsingError.type_mismatch(value, int, ctx=ctx)
        return value

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Integer()

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return value


class Float(ValueParser[float]):
    """
    Parser for float values.

    """

    def __init__(self):
        super().__init__(float)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> float:
        ctx = ctx.strip_if_non_space()
        try:
            return float(ctx.value)
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `float`",
                ctx.value,
                ctx=ctx,
                fallback_msg="Can't parse value as `float`",
            ) from None

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> float:
        value = ctx.value
        if not isinstance(value, (float, int)):
            raise ParsingError.type_mismatch(value, float, ctx=ctx)
        return value

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Number()

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return value


class Bool(ValueParser[bool]):
    """
    Parser for bool values, such as ``"yes"`` or ``"no"``.

    """

    def __init__(self):
        super().__init__(bool)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> bool:
        ctx = ctx.strip_if_non_space()
        value = ctx.value.casefold()
        if value in ("y", "yes", "true", "1"):
            return True
        elif value in ("n", "no", "false", "0"):
            return False
        else:
            raise ParsingError(
                "Can't parse `%r` as `bool`, should be `yes`, `no`, `true`, or `false`",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `bool`",
            )

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> bool:
        value = ctx.value
        if not isinstance(value, bool):
            raise ParsingError.type_mismatch(value, bool, ctx=ctx)
        return value

    def describe(self) -> str | None:
        return "{yes|no}"

    def describe_value(self, value: object, /) -> str:
        assert self.assert_type(value)
        return "yes" if value else "no"

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Choice(
            [
                yuio.complete.Option("true"),
                yuio.complete.Option("false"),
            ]
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[bool | yuio.Missing]:
        options: list[yuio.widget.Option[bool | yuio.Missing]] = [
            yuio.widget.Option(False, "no"),
            yuio.widget.Option(True, "yes"),
        ]

        if default is yuio.MISSING:
            default_index = 0
        elif isinstance(default, bool):
            default_index = int(default)
        else:
            options.append(
                yuio.widget.Option(yuio.MISSING, default_description or str(default))
            )
            default_index = 2

        return yuio.widget.Choice(options, default_index=default_index)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Boolean()

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return value


class Enum(WrappingParser[E, type[E]], ValueParser[E], _t.Generic[E]):
    """Enum(enum_type: typing.Type[E], /, *, by_name: bool | None = None, to_dash_case: bool | None = None, doc_inline: bool = False)

    Parser for enums, as defined in the standard :mod:`enum` module.

    :param enum_type:
        enum class that will be used to parse and extract values.
    :param by_name:
        if :data:`True`, the parser will use enumerator names, instead of
        their values, to match the input.

        If not given, Yuio will search for :data:`__yuio_by_name__` attribute on the
        given enum class to infer value for this option.
    :param to_dash_case:
        convert enum names/values to dash case.

        If not given, Yuio will search for :data:`__yuio_to_dash_case__` attribute on the
        given enum class to infer value for this option.
    :param doc_inline:
        inline this enum in json schema and in documentation.

        Useful for small enums that don't warrant a separate section in documentation.

        If not given, Yuio will search for :data:`__yuio_doc_inline__` attribute on the
        given enum class to infer value for this option.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls,
            inner: type[E],
            /,
            *,
            by_name: bool | None = None,
            to_dash_case: bool | None = None,
            doc_inline: bool | None = None,
        ) -> Enum[E]: ...

        @_t.overload
        def __new__(
            cls,
            /,
            *,
            by_name: bool | None = None,
            to_dash_case: bool | None = None,
            doc_inline: bool | None = None,
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        enum_type: type[E] | None = None,
        /,
        *,
        by_name: bool | None = None,
        to_dash_case: bool | None = None,
        doc_inline: bool | None = None,
    ):
        self._by_name = by_name
        self._to_dash_case = to_dash_case
        self._doc_inline = doc_inline
        super().__init__(enum_type, enum_type)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        result._value_type = parser._inner  # type: ignore
        return result

    @functools.cached_property
    def _getter(self) -> _t.Callable[[E], str]:
        by_name = self._by_name
        if by_name is None:
            by_name = getattr(self._inner, "__yuio_by_name__", False)
        to_dash_case = self._to_dash_case
        if to_dash_case is None:
            to_dash_case = getattr(self._inner, "__yuio_to_dash_case__", False)

        items = {}
        for e in self._inner:
            if by_name:
                name = e.name
            else:
                name = str(e.value)
            if to_dash_case:
                name = _to_dash_case(name)
            items[e] = name
        return lambda e: items[e]

    @functools.cached_property
    def _docs(self) -> dict[str, str]:
        docs = _find_docs(self._inner).copy()
        for key, text in docs.items():
            if (index := text.find("\n\n")) != -1:
                docs[key] = text[:index]
        return docs

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> E:
        ctx = ctx.strip_if_non_space()
        return self._parse(ctx.value, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> E:
        value = ctx.value

        if isinstance(value, self._inner):
            return value

        if not isinstance(value, str):
            raise ParsingError.type_mismatch(value, str, ctx=ctx)

        result = self._parse(value, ctx)

        if self._getter(result) != value:
            raise ParsingError(
                "Can't parse `%r` as `%s`, did you mean `%s`?",
                value,
                self._inner.__name__,
                self._getter(result),
                ctx=ctx,
            )

        return result

    def _parse(self, value: str, ctx: ConfigParsingContext | StrParsingContext):
        cf_value = value.strip().casefold()

        candidates: list[E] = []
        for item in self._inner:
            if self._getter(item) == value:
                return item
            elif (self._getter(item)).casefold().startswith(cf_value):
                candidates.append(item)

        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            enum_values = tuple(self._getter(e) for e in candidates)
            raise ParsingError(
                "Can't parse `%r` as `%s`, possible candidates are %s",
                value,
                self._inner.__name__,
                yuio.string.Or(enum_values),
                ctx=ctx,
            )
        else:
            enum_values = tuple(self._getter(e) for e in self._inner)
            raise ParsingError(
                "Can't parse `%r` as `%s`, should be %s",
                value,
                self._inner.__name__,
                yuio.string.Or(enum_values),
                ctx=ctx,
            )

    def describe(self) -> str | None:
        desc = "|".join(self._getter(e) for e in self._inner)
        if len(self._inner) > 1:
            desc = f"{{{desc}}}"
        return desc

    def describe_many(self) -> str | tuple[str, ...]:
        return self.describe_or_def()

    def describe_value(self, value: object, /) -> str:
        assert self.assert_type(value)
        return str(self._getter(value))

    def options(self) -> _t.Collection[yuio.widget.Option[E]]:
        docs = self._docs
        options = []
        for e in self._inner:
            comment = docs.get(e.name)
            if comment:
                lines = comment.splitlines()
                if not lines:
                    comment = None
                elif len(lines) == 1:
                    comment = str(lines[0])
                else:
                    comment = str(lines[0]) + ("..." if lines[1] else "")
            options.append(
                yuio.widget.Option(e, display_text=self._getter(e), comment=comment)
            )
        return options

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Choice(
            [
                yuio.complete.Option(option.display_text, comment=option.comment)
                for option in self.options()
            ]
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[E | yuio.Missing]:
        options: list[yuio.widget.Option[E | yuio.Missing]] = list(self.options())

        if default is yuio.MISSING:
            default_index = 0
        elif isinstance(default, self._inner):
            default_index = list(self._inner).index(default)
        else:
            options.insert(
                0, yuio.widget.Option(yuio.MISSING, default_description or str(default))
            )
            default_index = 0

        return yuio.widget.Choice(options, default_index=default_index)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        items = [self._getter(e) for e in self._inner]
        docs = self._docs

        descriptions = [docs.get(e.name) for e in self._inner]
        if not any(descriptions):
            descriptions = None

        by_name = self._by_name
        if by_name is None:
            by_name = getattr(self._inner, "__yuio_by_name__", False)
        to_dash_case = self._to_dash_case
        if to_dash_case is None:
            to_dash_case = getattr(self._inner, "__yuio_to_dash_case__", False)
        doc_inline = self._doc_inline
        if doc_inline is None:
            doc_inline = getattr(self._inner, "__yuio_doc_inline__", False)

        if doc_inline:
            return yuio.json_schema.Enum(items, descriptions)
        else:
            return ctx.add_type(
                Enum._TyWrapper(self._inner, by_name, to_dash_case),
                _tx.type_repr(self._inner),
                lambda: yuio.json_schema.Meta(
                    yuio.json_schema.Enum(items, descriptions),
                    title=self._inner.__name__,
                    description=self._inner.__doc__,
                ),
            )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return self._getter(value)

    def __repr__(self):
        if self._inner_raw is not None:
            return f"{self.__class__.__name__}({self._inner_raw!r})"
        else:
            return self.__class__.__name__

    @dataclasses.dataclass(unsafe_hash=True, match_args=False, slots=True)
    class _TyWrapper:
        inner: type
        by_name: bool
        to_dash_case: bool


class Decimal(ValueParser[decimal.Decimal]):
    """
    Parser for :class:`decimal.Decimal`.

    """

    def __init__(self):
        super().__init__(decimal.Decimal)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> decimal.Decimal:
        ctx = ctx.strip_if_non_space()
        try:
            return decimal.Decimal(ctx.value)
        except (ArithmeticError, ValueError, TypeError):
            raise ParsingError(
                "Can't parse `%r` as `decimal`",
                ctx.value,
                ctx=ctx,
                fallback_msg="Can't parse value as `decimal`",
            ) from None

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> decimal.Decimal:
        value = ctx.value
        if not isinstance(value, (int, float, str, decimal.Decimal)):
            raise ParsingError.type_mismatch(value, int, float, str, ctx=ctx)
        try:
            return decimal.Decimal(value)
        except (ArithmeticError, ValueError, TypeError):
            raise ParsingError(
                "Can't parse `%r` as `decimal`",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `decimal`",
            ) from None

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            decimal.Decimal,
            "Decimal",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.OneOf(
                    [
                        yuio.json_schema.Number(),
                        yuio.json_schema.String(
                            pattern=r"(?i)^[+-]?((\d+\.\d*|\.?\d+)(e[+-]?\d+)?|inf(inity)?|(nan|snan)\d*)$"
                        ),
                    ]
                ),
                title="Decimal",
                description="Decimal fixed-point and floating-point number.",
            ),
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


class Fraction(ValueParser[fractions.Fraction]):
    """
    Parser for :class:`fractions.Fraction`.

    """

    def __init__(self):
        super().__init__(fractions.Fraction)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> fractions.Fraction:
        ctx = ctx.strip_if_non_space()
        try:
            return fractions.Fraction(ctx.value)
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `fraction`",
                ctx.value,
                ctx=ctx,
                fallback_msg="Can't parse value as `fraction`",
            ) from None
        except ZeroDivisionError:
            raise ParsingError(
                "Can't parse `%r` as `fraction`, division by zero",
                ctx.value,
                ctx=ctx,
                fallback_msg="Can't parse value as `fraction`",
            ) from None

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> fractions.Fraction:
        value = ctx.value
        if (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(isinstance(v, (float, int)) for v in value)
        ):
            try:
                return fractions.Fraction(*value)
            except (ValueError, TypeError):
                raise ParsingError(
                    "Can't parse `%s/%s` as `fraction`",
                    value[0],
                    value[1],
                    ctx=ctx,
                    fallback_msg="Can't parse value as `fraction`",
                ) from None
            except ZeroDivisionError:
                raise ParsingError(
                    "Can't parse `%s/%s` as `fraction`, division by zero",
                    value[0],
                    value[1],
                    ctx=ctx,
                    fallback_msg="Can't parse value as `fraction`",
                ) from None
        if isinstance(value, (int, float, str, decimal.Decimal, fractions.Fraction)):
            try:
                return fractions.Fraction(value)
            except (ValueError, TypeError):
                raise ParsingError(
                    "Can't parse `%r` as `fraction`",
                    value,
                    ctx=ctx,
                    fallback_msg="Can't parse value as `fraction`",
                ) from None
            except ZeroDivisionError:
                raise ParsingError(
                    "Can't parse `%r` as `fraction`, division by zero",
                    value,
                    ctx=ctx,
                    fallback_msg="Can't parse value as `fraction`",
                ) from None
        raise ParsingError.type_mismatch(
            value, int, float, str, "a tuple of two ints", ctx=ctx
        )

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            fractions.Fraction,
            "Fraction",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.OneOf(
                    [
                        yuio.json_schema.Number(),
                        yuio.json_schema.String(
                            pattern=r"(?i)^[+-]?(\d+(\/\d+)?|(\d+\.\d*|\.?\d+)(e[+-]?\d+)?|inf(inity)?|nan)$"
                        ),
                        yuio.json_schema.Tuple(
                            [yuio.json_schema.Number(), yuio.json_schema.Number()]
                        ),
                    ]
                ),
                title="Fraction",
                description="A rational number.",
            ),
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


class Json(WrappingParser[T, Parser[T]], ValueParser[T], _t.Generic[T]):
    """Json(inner: Parser[T] | None = None, /)

    A parser that tries to parse value as JSON.

    This parser will load JSON strings into python objects.
    If `inner` parser is given, :class:`Json` will validate parsing results
    by calling :meth:`~Parser.parse_config_with_ctx` on the inner parser.

    :param inner:
        a parser used to convert and validate contents of json.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], /) -> Json[T]: ...

        @_t.overload
        def __new__(cls, /) -> Json[yuio.json_schema.JsonValue]: ...

        def __new__(cls, inner: Parser[T] | None = None, /) -> Json[_t.Any]: ...

    def __init__(
        self,
        inner: Parser[T] | None = None,
        /,
    ):
        super().__init__(inner, object)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = _copy(self)
        result._inner = parser
        return result

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T:
        ctx = ctx.strip_if_non_space()
        try:
            config_value: JsonValue = json.loads(ctx.value)
        except json.JSONDecodeError as e:
            raise ParsingError(
                "Can't parse `%r` as `JsonValue`:\n%s",
                ctx.value,
                yuio.string.Indent(e),
                ctx=ctx,
                fallback_msg="Can't parse value as `JsonValue`",
            ) from None
        try:
            return self.parse_config_with_ctx(ConfigParsingContext(config_value))
        except ParsingError as e:
            raise ParsingError(
                "Error in parsed json value:\n%s",
                yuio.string.Indent(e),
                ctx=ctx,
                fallback_msg="Error in parsed json value",
            ) from None

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T:
        if self._inner_raw is not None:
            return self._inner_raw.parse_config_with_ctx(ctx)
        else:
            return _t.cast(T, ctx.value)

    def check_type(self, value: object, /) -> _t.TypeGuard[T]:
        return True

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        if self._inner_raw is not None:
            return self._inner_raw.to_json_schema(ctx)
        else:
            return yuio.json_schema.Any()

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        if self._inner_raw is not None:
            return self._inner_raw.to_json_value(value)
        return value  # type: ignore

    def __repr__(self):
        if self._inner_raw is not None:
            return f"{self.__class__.__name__}({self._inner_raw!r})"
        else:
            return super().__repr__()


class DateTime(ValueParser[datetime.datetime]):
    """
    Parse a datetime in ISO ('YYYY-MM-DD HH:MM:SS') format.

    """

    def __init__(self):
        super().__init__(datetime.datetime)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> datetime.datetime:
        ctx = ctx.strip_if_non_space()
        return self._parse(ctx.value, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> datetime.datetime:
        value = ctx.value
        if isinstance(value, datetime.datetime):
            return value
        elif isinstance(value, str):
            return self._parse(value, ctx)
        else:
            raise ParsingError.type_mismatch(value, str, ctx=ctx)

    @staticmethod
    def _parse(value: str, ctx: ConfigParsingContext | StrParsingContext):
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `datetime`",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `datetime`",
            ) from None

    def describe(self) -> str | None:
        return "YYYY-MM-DD[ HH:MM:SS]"

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            datetime.datetime,
            "DateTime",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.String(
                    pattern=(
                        r"^"
                        r"("
                        r"\d{4}-W\d{2}(-\d)?"
                        r"|\d{4}-\d{2}-\d{2}"
                        r"|\d{4}W\d{2}\d?"
                        r"|\d{4}\d{2}\d{2}"
                        r")"
                        r"("
                        r"[T ]"
                        r"\d{2}(:\d{2}(:\d{2}(.\d{3}(\d{3})?)?)?)?"
                        r"([+-]\d{2}(:\d{2}(:\d{2}(.\d{3}(\d{3})?)?)?)?|Z)?"
                        r")?"
                        r"$"
                    )
                ),
                title="DateTime",
                description="ISO 8601 datetime.",
            ),
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


class Date(ValueParser[datetime.date]):
    """
    Parse a date in ISO ('YYYY-MM-DD') format.

    """

    def __init__(self):
        super().__init__(datetime.date)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> datetime.date:
        ctx = ctx.strip_if_non_space()
        return self._parse(ctx.value, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> datetime.date:
        value = ctx.value
        if isinstance(value, datetime.datetime):
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        elif isinstance(value, str):
            return self._parse(value, ctx)
        else:
            raise ParsingError.type_mismatch(value, str, ctx=ctx)

    @staticmethod
    def _parse(value: str, ctx: ConfigParsingContext | StrParsingContext):
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `date`",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `date`",
            ) from None

    def describe(self) -> str | None:
        return "YYYY-MM-DD"

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            datetime.date,
            "Date",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.String(
                    pattern=(
                        r"^"
                        r"("
                        r"\d{4}-W\d{2}(-\d)?"
                        r"|\d{4}-\d{2}-\d{2}"
                        r"|\d{4}W\d{2}\d?"
                        r"|\d{4}\d{2}\d{2}"
                        r")"
                        r"$"
                    )
                ),
                title="Date",
                description="ISO 8601 date.",
            ),
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


class Time(ValueParser[datetime.time]):
    """
    Parse a time in ISO ('HH:MM:SS') format.

    """

    def __init__(self):
        super().__init__(datetime.time)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> datetime.time:
        ctx = ctx.strip_if_non_space()
        return self._parse(ctx.value, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> datetime.time:
        value = ctx.value
        if isinstance(value, datetime.datetime):
            return value.time()
        elif isinstance(value, datetime.time):
            return value
        elif isinstance(value, str):
            return self._parse(value, ctx)
        else:
            raise ParsingError.type_mismatch(value, str, ctx=ctx)

    @staticmethod
    def _parse(value: str, ctx: ConfigParsingContext | StrParsingContext):
        try:
            return datetime.time.fromisoformat(value)
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `time`",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `time`",
            ) from None

    def describe(self) -> str | None:
        return "HH:MM:SS"

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            datetime.time,
            "Time",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.String(
                    pattern=(
                        r"^"
                        r"\d{2}(:\d{2}(:\d{2}(.\d{3}(\d{3})?)?)?)?"
                        r"([+-]\d{2}(:\d{2}(:\d{2}(.\d{3}(\d{3})?)?)?)?|Z)?"
                        r"$"
                    )
                ),
                title="Time",
                description="ISO 8601 time.",
            ),
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


_UNITS_MAP = (
    ("days", ("d", "day", "days")),
    ("seconds", ("s", "sec", "secs", "second", "seconds")),
    ("microseconds", ("us", "u", "micro", "micros", "microsecond", "microseconds")),
    ("milliseconds", ("ms", "l", "milli", "millis", "millisecond", "milliseconds")),
    ("minutes", ("m", "min", "mins", "minute", "minutes")),
    ("hours", ("h", "hr", "hrs", "hour", "hours")),
    ("weeks", ("w", "week", "weeks")),
)

_UNITS = {unit: name for name, units in _UNITS_MAP for unit in units}

_TIMEDELTA_RE = re.compile(
    r"""
        # General format: -1 day, -01:00:00.000000
        ^
        (?:([+-]?)\s*((?:\d+\s*[a-z]+\s*)+))?
        (?:,\s*)?
        (?:([+-]?)\s*(\d+):(\d?\d)(?::(\d?\d)(?:\.(?:(\d\d\d)(\d\d\d)?))?)?)?
        $
    """,
    re.VERBOSE | re.IGNORECASE,
)

_COMPONENT_RE = re.compile(r"(\d+)\s*([a-z]+)\s*")


class TimeDelta(ValueParser[datetime.timedelta]):
    """
    Parse a time delta.

    """

    def __init__(self):
        super().__init__(datetime.timedelta)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> datetime.timedelta:
        ctx = ctx.strip_if_non_space()
        return self._parse(ctx.value, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> datetime.timedelta:
        value = ctx.value
        if isinstance(value, datetime.timedelta):
            return value
        elif isinstance(value, str):
            return self._parse(value, ctx)
        else:
            raise ParsingError.type_mismatch(value, str, ctx=ctx)

    @staticmethod
    def _parse(value: str, ctx: ConfigParsingContext | StrParsingContext):
        value = value.strip()

        if not value:
            raise ParsingError("Got an empty `timedelta`", ctx=ctx)
        if value.endswith(","):
            raise ParsingError(
                "Can't parse `%r` as `timedelta`, trailing comma is not allowed",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `timedelta`",
            )
        if value.startswith(","):
            raise ParsingError(
                "Can't parse `%r` as `timedelta`, leading comma is not allowed",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `timedelta`",
            )

        if match := _TIMEDELTA_RE.match(value):
            (
                c_sign_s,
                components_s,
                t_sign_s,
                hour,
                minute,
                second,
                millisecond,
                microsecond,
            ) = match.groups()
        else:
            raise ParsingError(
                "Can't parse `%r` as `timedelta`",
                value,
                ctx=ctx,
                fallback_msg="Can't parse value as `timedelta`",
            )

        c_sign_s = -1 if c_sign_s == "-" else 1
        t_sign_s = -1 if t_sign_s == "-" else 1

        kwargs = {u: 0 for u, _ in _UNITS_MAP}

        if components_s:
            for num, unit in _COMPONENT_RE.findall(components_s):
                if unit_key := _UNITS.get(unit.lower()):
                    kwargs[unit_key] += int(num)
                else:
                    raise ParsingError(
                        "Can't parse `%r` as `timedelta`, unknown unit `%r`",
                        value,
                        unit,
                        ctx=ctx,
                        fallback_msg="Can't parse value as `timedelta`",
                    )

        timedelta = c_sign_s * datetime.timedelta(**kwargs)

        timedelta += t_sign_s * datetime.timedelta(
            hours=int(hour or "0"),
            minutes=int(minute or "0"),
            seconds=int(second or "0"),
            milliseconds=int(millisecond or "0"),
            microseconds=int(microsecond or "0"),
        )

        return timedelta

    def describe(self) -> str | None:
        return "[+|-]HH:MM:SS"

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            datetime.timedelta,
            "TimeDelta",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.String(
                    # save yourself some trouble, paste this into https://regexper.com/
                    pattern=(
                        r"^(([+-]?\s*(\d+\s*(d|day|days|s|sec|secs|second|seconds"
                        r"|us|u|micro|micros|microsecond|microseconds|ms|l|milli|"
                        r"millis|millisecond|milliseconds|m|min|mins|minute|minutes"
                        r"|h|hr|hrs|hour|hours|w|week|weeks)\s*)+)(,\s*)?"
                        r"([+-]?\s*\d+:\d?\d(:\d?\d(\.\d\d\d(\d\d\d)?)?)?)"
                        r"|([+-]?\s*\d+:\d?\d(:\d?\d(\.\d\d\d(\d\d\d)?)?)?)"
                        r"|([+-]?\s*(\d+\s*(d|day|days|s|sec|secs|second|seconds"
                        r"|us|u|micro|micros|microsecond|microseconds|ms|l|milli"
                        r"|millis|millisecond|milliseconds|m|min|mins|minute|minutes"
                        r"|h|hr|hrs|hour|hours|w|week|weeks)\s*)+))$"
                    )
                ),
                title="Time delta. General format: '[+-] [M weeks] [N days] [+-]HH:MM:SS'",
                description=".",
            ),
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


class Seconds(TimeDelta):
    """
    Parse a float and convert it to a time delta as a number of seconds.

    """

    @staticmethod
    def _parse(value: str, ctx: ConfigParsingContext | StrParsingContext):
        try:
            seconds = float(value)
        except ValueError:
            raise ParsingError(
                "Can't parse `%r` as `<seconds>`",
                ctx.value,
                ctx=ctx,
                fallback_msg="Can't parse value as `<seconds>`",
            ) from None
        return datetime.timedelta(seconds=seconds)

    def describe(self) -> str | None:
        return "<seconds>"

    def describe_or_def(self) -> str:
        return "<seconds>"

    def describe_many(self) -> str | tuple[str, ...]:
        return "<seconds>"

    def describe_value(self, value: object) -> str:
        assert self.assert_type(value)
        return str(value.total_seconds())

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Meta(yuio.json_schema.Number(), description="seconds")

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return value.total_seconds()


class Path(ValueParser[pathlib.Path]):
    """
    Parse a file system path, return a :class:`pathlib.Path`.

    :param extensions:
        list of allowed file extensions, including preceding dots.

    """

    def __init__(
        self,
        /,
        *,
        extensions: str | _t.Collection[str] | None = None,
    ):
        self._extensions = [extensions] if isinstance(extensions, str) else extensions
        super().__init__(pathlib.Path)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> pathlib.Path:
        ctx = ctx.strip_if_non_space()
        return self._parse(ctx.value, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> pathlib.Path:
        value = ctx.value
        if not isinstance(value, str):
            raise ParsingError.type_mismatch(value, str, ctx=ctx)
        return self._parse(value, ctx)

    def _parse(self, value: str, ctx: ConfigParsingContext | StrParsingContext):
        res = pathlib.Path(value).expanduser().resolve().absolute()
        try:
            self._validate(res)
        except ParsingError as e:
            e.set_ctx(ctx)
            raise
        return res

    def describe(self) -> str | None:
        if self._extensions is not None:
            desc = "|".join(f"<*{e}>" for e in self._extensions)
            if len(self._extensions) > 1:
                desc = f"{{{desc}}}"
            return desc
        else:
            return super().describe()

    def _validate(self, value: pathlib.Path, /):
        if self._extensions is not None and not any(
            value.name.endswith(ext) for ext in self._extensions
        ):
            raise ParsingError(
                "<c path>%s</c> should have extension %s",
                value,
                yuio.string.Or(self._extensions),
            )

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.File(extensions=self._extensions)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.String()

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return str(value)


class NonExistentPath(Path):
    """
    Parse a file system path and verify that it doesn't exist.

    :param extensions:
        list of allowed file extensions, including preceding dots.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if value.exists():
            raise ParsingError("<c path>%s</c> already exists", value)


class ExistingPath(Path):
    """
    Parse a file system path and verify that it exists.

    :param extensions:
        list of allowed file extensions, including preceding dots.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.exists():
            raise ParsingError("<c path>%s</c> doesn't exist", value)


class File(ExistingPath):
    """
    Parse a file system path and verify that it points to a regular file.

    :param extensions:
        list of allowed file extensions, including preceding dots.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_file():
            raise ParsingError("<c path>%s</c> is not a file", value)


class Dir(ExistingPath):
    """
    Parse a file system path and verify that it points to a directory.

    """

    def __init__(self):
        # Disallow passing `extensions`.
        super().__init__()

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_dir():
            raise ParsingError("<c path>%s</c> is not a directory", value)

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Dir()


class GitRepo(Dir):
    """
    Parse a file system path and verify that it points to a git repository.

    This parser just checks that the given directory has
    a subdirectory named ``.git``.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.joinpath(".git").is_dir():
            raise ParsingError("<c path>%s</c> is not a git repository root", value)


class Secret(Map[SecretValue[T], T], _t.Generic[T]):
    """Secret(inner: Parser[U], /)

    Wraps result of the inner parser into :class:`~yuio.secret.SecretValue`
    and ensures that :func:`yuio.io.ask` doesn't show value as user enters it.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], /) -> Secret[T]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: Parser[U] | None = None, /):
        super().__init__(inner, SecretValue, lambda x: x.data)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> SecretValue[T]:
        with self._replace_error():
            return super().parse_with_ctx(ctx)

    def parse_many_with_ctx(
        self, ctxs: _t.Sequence[StrParsingContext], /
    ) -> SecretValue[T]:
        with self._replace_error():
            return super().parse_many_with_ctx(ctxs)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> SecretValue[T]:
        with self._replace_error():
            return super().parse_config_with_ctx(ctx)

    @staticmethod
    @contextlib.contextmanager
    def _replace_error():
        try:
            yield
        except ParsingError as e:
            # Error messages can contain secret value, hide them.
            raise ParsingError(
                yuio.string.Printable(
                    e.fallback_msg or "Error when parsing secret data"
                ),
                pos=e.pos,
                path=e.path,
                n_arg=e.n_arg,
                # Omit raw value.
            ) from None

    def describe_value(self, value: object, /) -> str:
        return "***"

    def completer(self) -> yuio.complete.Completer | None:
        return None

    def options(self) -> _t.Collection[yuio.widget.Option[SecretValue[T]]] | None:
        return None

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[SecretValue[T] | yuio.Missing]:
        return _secret_widget(self, default, input_description, default_description)

    def is_secret(self) -> bool:
        return True


class CollectionParser(
    WrappingParser[C, Parser[T]], ValueParser[C], PartialParser, _t.Generic[C, T]
):
    """CollectionParser(inner: Parser[T] | None, /, **kwargs)

    A base class for implementing collection parsing. It will split a string
    by the given delimiter, parse each item using a subparser, and then pass
    the result to the given constructor.

    :param inner:
        parser that will be used to parse collection items.
    :param ty:
        type of the collection that this parser returns.
    :param ctor:
        factory of instances of the collection that this parser returns.
        It should take an iterable of parsed items, and return a collection.
    :param iter:
        a function that is used to get an iterator from a collection.
        This defaults to :func:`iter`, but sometimes it may be different.
        For example, :class:`Dict` is implemented as a collection of pairs,
        and its `iter` is :meth:`dict.items`.
    :param config_type:
        type of a collection that we expect to find when parsing a config.
        This will usually be a list.
    :param config_type_iter:
        a function that is used to get an iterator from a config value.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    The above parameters are exposed via protected attributes:
    ``self._inner``, ``self._ty``, etc.

    For example, let's implement a :class:`list` parser
    that repeats each element twice:

    .. code-block:: python

        from typing import Iterable, Generic


        class DoubleList(CollectionParser[list[T], T], Generic[T]):
            def __init__(self, inner: Parser[T], /, *, delimiter: str | None = None):
                super().__init__(inner, ty=list, ctor=self._ctor, delimiter=delimiter)

            @staticmethod
            def _ctor(values: Iterable[T]) -> list[T]:
                return [x for value in values for x in [value, value]]

            def to_json_schema(
                self, ctx: yuio.json_schema.JsonSchemaContext, /
            ) -> yuio.json_schema.JsonSchemaType:
                return {"type": "array", "items": self._inner.to_json_schema(ctx)}

            def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
                assert self.assert_type(value)
                return [self._inner.to_json_value(item) for item in value[::2]]

    ::

        >>> parser = DoubleList(Int())
        >>> parser.parse("1 2 3")
        [1, 1, 2, 2, 3, 3]
        >>> parser.to_json_value([1, 1, 2, 2, 3, 3])
        [1, 2, 3]

    """

    _allow_completing_duplicates: typing.ClassVar[bool] = True
    """
    If set to :data:`False`, autocompletion will not suggest item duplicates.

    """

    def __init__(
        self,
        inner: Parser[T] | None,
        /,
        *,
        ty: type[C],
        ctor: _t.Callable[[_t.Iterable[T]], C],
        iter: _t.Callable[[C], _t.Iterable[T]] = iter,
        config_type: type[C2] | tuple[type[C2], ...] = list,
        config_type_iter: _t.Callable[[C2], _t.Iterable[T]] = iter,
        delimiter: str | None = None,
    ):
        if delimiter == "":
            raise ValueError("empty delimiter")

        #: See class parameters for more details.
        self._ty = ty
        self._ctor = ctor
        self._iter = iter
        self._config_type = config_type
        self._config_type_iter = config_type_iter
        self._delimiter = delimiter

        super().__init__(inner, ty)

    def wrap(self: P, parser: Parser[_t.Any]) -> P:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        return result

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> C:
        return self._ctor(
            self._inner.parse_with_ctx(item) for item in ctx.split(self._delimiter)
        )

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> C:
        return self._ctor(self._inner.parse_with_ctx(item) for item in ctxs)

    def supports_parse_many(self) -> bool:
        return True

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> C:
        value = ctx.value
        if not isinstance(value, self._config_type):
            expected = self._config_type
            if not isinstance(expected, tuple):
                expected = (expected,)
            raise ParsingError.type_mismatch(value, *expected, ctx=ctx)

        return self._ctor(
            self._inner.parse_config_with_ctx(ctx.descend(item, i))
            for i, item in enumerate(self._config_type_iter(value))
        )

    def get_nargs(self) -> _t.Literal["+", "*"] | int:
        return "*"

    def describe(self) -> str | None:
        delimiter = self._delimiter or " "
        value = self._inner.describe_or_def()

        return f"{value}[{delimiter}{value}[{delimiter}...]]"

    def describe_many(self) -> str | tuple[str, ...]:
        return self._inner.describe_or_def()

    def describe_value(self, value: object, /) -> str:
        assert self.assert_type(value)

        return (self._delimiter or " ").join(
            self._inner.describe_value(item) for item in self._iter(value)
        )

    def options(self) -> _t.Collection[yuio.widget.Option[C]] | None:
        return None

    def completer(self) -> yuio.complete.Completer | None:
        completer = self._inner.completer()
        return (
            yuio.complete.List(
                completer,
                delimiter=self._delimiter,
                allow_duplicates=self._allow_completing_duplicates,
            )
            if completer is not None
            else None
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[C | yuio.Missing]:
        completer = self.completer()
        return _WidgetResultMapper(
            self,
            input_description,
            default,
            (
                yuio.widget.InputWithCompletion(
                    completer,
                    placeholder=default_description or "",
                )
                if completer is not None
                else yuio.widget.Input(
                    placeholder=default_description or "",
                )
            ),
        )

    def is_secret(self) -> bool:
        return self._inner.is_secret()

    def __repr__(self):
        if self._inner_raw is not None:
            return f"{self.__class__.__name__}({self._inner_raw!r})"
        else:
            return self.__class__.__name__


class List(CollectionParser[list[T], T], _t.Generic[T]):
    """List(inner: Parser[T], /, *, delimiter: str | None = None)

    Parser for lists.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse list items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls, inner: Parser[T], /, *, delimiter: str | None = None
        ) -> List[T]: ...

        @_t.overload
        def __new__(cls, /, *, delimiter: str | None = None) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        inner: Parser[T] | None = None,
        /,
        *,
        delimiter: str | None = None,
    ):
        super().__init__(inner, ty=list, ctor=list, delimiter=delimiter)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Array(self._inner.to_json_schema(ctx))

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return [self._inner.to_json_value(item) for item in value]


class Set(CollectionParser[set[T], T], _t.Generic[T]):
    """Set(inner: Parser[T], /, *, delimiter: str | None = None)

    Parser for sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls, inner: Parser[T], /, *, delimiter: str | None = None
        ) -> Set[T]: ...

        @_t.overload
        def __new__(cls, /, *, delimiter: str | None = None) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    _allow_completing_duplicates = False

    def __init__(
        self,
        inner: Parser[T] | None = None,
        /,
        *,
        delimiter: str | None = None,
    ):
        super().__init__(inner, ty=set, ctor=set, delimiter=delimiter)

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[set[T] | yuio.Missing]:
        options = self._inner.options()
        if options is not None and len(options) <= 25:
            return yuio.widget.Map(yuio.widget.Multiselect(list(options)), set)
        else:
            return super().widget(default, input_description, default_description)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Array(
            self._inner.to_json_schema(ctx), unique_items=True
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return [self._inner.to_json_value(item) for item in value]


class FrozenSet(CollectionParser[frozenset[T], T], _t.Generic[T]):
    """FrozenSet(inner: Parser[T], /, *, delimiter: str | None = None)

    Parser for frozen sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls, inner: Parser[T], /, *, delimiter: str | None = None
        ) -> FrozenSet[T]: ...

        @_t.overload
        def __new__(cls, /, *, delimiter: str | None = None) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    _allow_completing_duplicates = False

    def __init__(
        self,
        inner: Parser[T] | None = None,
        /,
        *,
        delimiter: str | None = None,
    ):
        super().__init__(inner, ty=frozenset, ctor=frozenset, delimiter=delimiter)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Array(
            self._inner.to_json_schema(ctx), unique_items=True
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return [self._inner.to_json_value(item) for item in value]


class Dict(CollectionParser[dict[K, V], tuple[K, V]], _t.Generic[K, V]):
    """Dict(key: Parser[K], value: Parser[V], /, *, delimiter: str | None = None, pair_delimiter: str = ":")

    Parser for dicts.

    Will split a string by the given delimiter, and parse each item
    using a :py:class:`Tuple` parser.

    :param key:
        inner parser that will be used to parse dict keys.
    :param value:
        inner parser that will be used to parse dict values.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.
    :param pair_delimiter:
        delimiter that will be used to split key-value elements.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls,
            key: Parser[K],
            value: Parser[V],
            /,
            *,
            delimiter: str | None = None,
            pair_delimiter: str = ":",
        ) -> Dict[K, V]: ...

        @_t.overload
        def __new__(
            cls,
            /,
            *,
            delimiter: str | None = None,
            pair_delimiter: str = ":",
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    _allow_completing_duplicates = False

    def __init__(
        self,
        key: Parser[K] | None = None,
        value: Parser[V] | None = None,
        /,
        *,
        delimiter: str | None = None,
        pair_delimiter: str = ":",
    ):
        self._pair_delimiter = pair_delimiter
        super().__init__(
            (
                _DictElementParser(key, value, delimiter=pair_delimiter)
                if key and value
                else None
            ),
            ty=dict,
            ctor=dict,
            iter=dict.items,
            config_type=(dict, list),
            config_type_iter=self.__config_type_iter,
            delimiter=delimiter,
        )

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner._delimiter = self._pair_delimiter  # pyright: ignore[reportAttributeAccessIssue]
        return result

    @staticmethod
    def __config_type_iter(x) -> _t.Iterator[tuple[K, V]]:
        if isinstance(x, dict):
            return iter(x.items())
        else:
            return iter(x)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        key_schema = self._inner._inner[0].to_json_schema(ctx)  # type: ignore
        value_schema = self._inner._inner[1].to_json_schema(ctx)  # type: ignore
        return yuio.json_schema.Dict(key_schema, value_schema)

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        items = _t.cast(
            list[tuple[yuio.json_schema.JsonValue, yuio.json_schema.JsonValue]],
            [self._inner.to_json_value(item) for item in value.items()],
        )

        if all(isinstance(k, str) for k, _ in items):
            return dict(_t.cast(list[tuple[str, yuio.json_schema.JsonValue]], items))
        else:
            return items


class Tuple(
    WrappingParser[TU, tuple[Parser[object], ...]],
    ValueParser[TU],
    PartialParser,
    _t.Generic[TU],
):
    """Tuple(*parsers: Parser[...], delimiter: str | None = None)

    Parser for tuples of fixed lengths.

    :param parsers:
        parsers for each tuple element.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    # See the links below for an explanation of shy this is so ugly:
    # https://github.com/python/typing/discussions/1450
    # https://github.com/python/typing/issues/1216
    if TYPE_CHECKING:
        T1 = _t.TypeVar("T1")
        T2 = _t.TypeVar("T2")
        T3 = _t.TypeVar("T3")
        T4 = _t.TypeVar("T4")
        T5 = _t.TypeVar("T5")
        T6 = _t.TypeVar("T6")
        T7 = _t.TypeVar("T7")
        T8 = _t.TypeVar("T8")
        T9 = _t.TypeVar("T9")
        T10 = _t.TypeVar("T10")

        @_t.overload
        def __new__(
            cls,
            /,
            *,
            delimiter: str | None = None,
        ) -> PartialParser: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4, T5]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4, T5, T6]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4, T5, T6, T7]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4, T5, T6, T7, T8]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            p9: Parser[T9],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            p9: Parser[T9],
            p10: Parser[T10],
            /,
            *,
            delimiter: str | None = None,
        ) -> Tuple[tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            p9: Parser[T9],
            p10: Parser[T10],
            p11: Parser[object],
            *tail: Parser[object],
            delimiter: str | None = None,
        ) -> Tuple[tuple[_t.Any, ...]]: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        *parsers: Parser[_t.Any],
        delimiter: str | None = None,
    ):
        if delimiter == "":
            raise ValueError("empty delimiter")
        self._delimiter = delimiter
        super().__init__(parsers or None, tuple)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        return result

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> TU:
        items = list(ctx.split(self._delimiter, maxsplit=len(self._inner) - 1))

        if len(items) != len(self._inner):
            raise ParsingError(
                "Expected %s element%s, got %s: `%r`",
                len(self._inner),
                "" if len(self._inner) == 1 else "s",
                len(items),
                ctx.value,
                ctx=ctx,
            )

        return _t.cast(
            TU,
            tuple(
                parser.parse_with_ctx(item) for parser, item in zip(self._inner, items)
            ),
        )

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> TU:
        if len(ctxs) != len(self._inner):
            raise ParsingError(
                "Expected %s element%s, got %s: `%r`",
                len(self._inner),
                "" if len(self._inner) == 1 else "s",
                len(ctxs),
                ctxs,
            )

        return _t.cast(
            TU,
            tuple(
                parser.parse_with_ctx(item) for parser, item in zip(self._inner, ctxs)
            ),
        )

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> TU:
        value = ctx.value
        if not isinstance(value, (list, tuple)):
            raise ParsingError.type_mismatch(value, list, tuple, ctx=ctx)
        elif len(value) != len(self._inner):
            raise ParsingError(
                "Expected %s element%s, got %s: `%r`",
                len(self._inner),
                "" if len(self._inner) == 1 else "s",
                len(value),
                value,
            )

        return _t.cast(
            TU,
            tuple(
                parser.parse_config_with_ctx(ctx.descend(item, i))
                for i, (parser, item) in enumerate(zip(self._inner, value))
            ),
        )

    def supports_parse_many(self) -> bool:
        return True

    def get_nargs(self) -> _t.Literal["+", "*"] | int:
        return len(self._inner)

    def describe(self) -> str | None:
        delimiter = self._delimiter or " "
        desc = [parser.describe_or_def() for parser in self._inner]
        return delimiter.join(desc)

    def describe_many(self) -> str | tuple[str, ...]:
        return tuple(parser.describe_or_def() for parser in self._inner)

    def describe_value(self, value: object, /) -> str:
        assert self.assert_type(value)

        delimiter = self._delimiter or " "
        desc = [parser.describe_value(item) for parser, item in zip(self._inner, value)]

        return delimiter.join(desc)

    def options(self) -> _t.Collection[yuio.widget.Option[TU]] | None:
        return None

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Tuple(
            *[parser.completer() or yuio.complete.Empty() for parser in self._inner],
            delimiter=self._delimiter,
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[TU | yuio.Missing]:
        completer = self.completer()

        return _WidgetResultMapper(
            self,
            input_description,
            default,
            (
                yuio.widget.InputWithCompletion(
                    completer,
                    placeholder=default_description or "",
                )
                if completer is not None
                else yuio.widget.Input(
                    placeholder=default_description or "",
                )
            ),
        )

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.Tuple(
            [parser.to_json_schema(ctx) for parser in self._inner]
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return [parser.to_json_value(item) for parser, item in zip(self._inner, value)]

    def is_secret(self) -> bool:
        return any(parser.is_secret() for parser in self._inner)

    def __repr__(self):
        if self._inner_raw is not None:
            return f"{self.__class__.__name__}{self._inner_raw!r}"
        else:
            return self.__class__.__name__


class _DictElementParser(Tuple[tuple[K, V]], _t.Generic[K, V]):
    def __init__(self, k: Parser[K], v: Parser[V], delimiter: str | None = None):
        super().__init__(k, v, delimiter=delimiter)

    # def parse_with_ctx(self, ctx: StrParsingContext, /) -> tuple[K, V]:
    #     items = list(ctx.split(self._delimiter, maxsplit=len(self._inner) - 1))

    #     if len(items) != len(self._inner):
    #         raise ParsingError("Expected key-value pair, got `%r`", ctx.value)

    #     return _t.cast(
    #         tuple[K, V],
    #         tuple(parser.parse_with_ctx(item) for parser, item in zip(self._inner, items)),
    #     )

    # def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> tuple[K, V]:
    #     if len(value) != len(self._inner):
    #         with describe_context("element #%(key)r"):
    #             raise ParsingError(
    #                 "Expected key-value pair, got `%r`",
    #                 value,
    #             )

    #     k = describe_context("key of element #%(key)r", self._inner[0].parse, value[0])
    #     v = replace_context(k, self._inner[1].parse, value[1])

    #     return _t.cast(tuple[K, V], (k, v))

    # def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> tuple[K, V]:
    #     if not isinstance(value, (list, tuple)):
    #         with describe_context("element #%(key)r"):
    #             raise ParsingError.type_mismatch(value, list, tuple)
    #     elif len(value) != len(self._inner):
    #         with describe_context("element #%(key)r"):
    #             raise ParsingError(
    #                 "Expected key-value pair, got `%r`",
    #                 value,
    #             )

    #     k = describe_context(
    #         "key of element #%(key)r", self._inner[0].parse_config_with_ctx, value[0]
    #     )
    #     v = replace_context(k, self._inner[1].parse_config_with_ctx, value[1])

    #     return _t.cast(tuple[K, V], (k, v))


class Optional(MappingParser[T | None, T], _t.Generic[T]):
    """Optional(inner: Parser[T], /)

    Parser for optional values.

    Allows handling :data:`None`\\ s when parsing config. Does not change how strings
    are parsed, though.

    :param inner:
        a parser used to extract and validate contents of an optional.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], /) -> Optional[T]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: Parser[T] | None = None, /):
        super().__init__(inner)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T | None:
        return self._inner.parse_with_ctx(ctx)

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> T | None:
        return self._inner.parse_many_with_ctx(ctxs)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T | None:
        if ctx.value is None:
            return None
        return self._inner.parse_config_with_ctx(ctx)

    def check_type(self, value: object, /) -> _t.TypeGuard[T | None]:
        return True

    def describe_value(self, value: object, /) -> str:
        if value is None:
            return "<none>"
        return self._inner.describe_value(value)

    def options(self) -> _t.Collection[yuio.widget.Option[T | None]] | None:
        return self._inner.options()

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        return self._inner.widget(default, input_description, default_description)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.OneOf(
            [self._inner.to_json_schema(ctx), yuio.json_schema.Null()]
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        if value is None:
            return None
        else:
            return self._inner.to_json_value(value)


class Union(WrappingParser[T, tuple[Parser[T], ...]], ValueParser[T], _t.Generic[T]):
    """Union(*parsers: Parser[T])

    Tries several parsers and returns the first successful result.

    .. warning::

        Order of parsers matters. Since parsers are tried in the same order as they're
        given, make sure to put parsers that are likely to succeed at the end.

        For example, this parser will always return a string because :class:`Str`
        can't fail::

            >>> parser = Union(Str(), Int())  # Always returns a string!
            >>> parser.parse("10")
            '10'

        To fix this, put :class:`Str` at the end so that :class:`Int` is tried first::

            >>> parser = Union(Int(), Str())
            >>> parser.parse("10")
            10
            >>> parser.parse("not an int")
            'not an int'

    """

    # See the links below for an explanation of shy this is so ugly:
    # https://github.com/python/typing/discussions/1450
    # https://github.com/python/typing/issues/1216
    if TYPE_CHECKING:
        T1 = _t.TypeVar("T1")
        T2 = _t.TypeVar("T2")
        T3 = _t.TypeVar("T3")
        T4 = _t.TypeVar("T4")
        T5 = _t.TypeVar("T5")
        T6 = _t.TypeVar("T6")
        T7 = _t.TypeVar("T7")
        T8 = _t.TypeVar("T8")
        T9 = _t.TypeVar("T9")
        T10 = _t.TypeVar("T10")

        @_t.overload
        def __new__(
            cls,
            /,
        ) -> PartialParser: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            /,
        ) -> Union[T1]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            /,
        ) -> Union[T1 | T2]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            /,
        ) -> Union[T1 | T2 | T3]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            /,
        ) -> Union[T1 | T2 | T3 | T4]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            /,
        ) -> Union[T1 | T2 | T3 | T4 | T5]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            /,
        ) -> Union[T1 | T2 | T3 | T4 | T5 | T6]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            /,
        ) -> Union[T1 | T2 | T3 | T4 | T5 | T6 | T7]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            /,
        ) -> Union[T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            p9: Parser[T9],
            /,
        ) -> Union[T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            p9: Parser[T9],
            p10: Parser[T10],
            /,
        ) -> Union[T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 | T9 | T10]: ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            p5: Parser[T5],
            p6: Parser[T6],
            p7: Parser[T7],
            p8: Parser[T8],
            p9: Parser[T9],
            p10: Parser[T10],
            p11: Parser[object],
            *parsers: Parser[object],
        ) -> Union[object]: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, *parsers: Parser[_t.Any]):
        super().__init__(parsers or None, object)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        return result

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T:
        errors: list[tuple[Parser[object], ParsingError]] = []
        for parser in self._inner:
            try:
                return parser.parse_with_ctx(ctx)
            except ParsingError as e:
                errors.append((parser, e))
        raise self._make_error(errors, ctx)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T:
        errors: list[tuple[Parser[object], ParsingError]] = []
        for parser in self._inner:
            try:
                return parser.parse_config_with_ctx(ctx)
            except ParsingError as e:
                errors.append((parser, e))
        raise self._make_error(errors, ctx)

    def _make_error(
        self,
        errors: list[tuple[Parser[object], ParsingError]],
        ctx: StrParsingContext | ConfigParsingContext,
    ):
        msgs = []
        for parser, error in errors:
            error.raw = None
            error.pos = None
            msgs.append(
                yuio.string.Format(
                    "  Trying as `%s`:\n%s",
                    parser.describe_or_def(),
                    yuio.string.Indent(error, indent=4),
                )
            )
        return ParsingError(
            "Can't parse `%r`:\n%s", ctx.value, yuio.string.Stack(*msgs), ctx=ctx
        )

    def check_type(self, value: object, /) -> _t.TypeGuard[T]:
        return True

    def describe(self) -> str | None:
        if len(self._inner) > 1:

            def strip_curly_brackets(desc: str):
                if desc.startswith("{") and desc.endswith("}") and "|" in desc:
                    s = desc[1:-1]
                    if "{" not in s and "}" not in s:
                        return s
                return desc

            desc = "|".join(
                strip_curly_brackets(parser.describe_or_def()) for parser in self._inner
            )
            desc = f"{{{desc}}}"
        else:
            desc = "|".join(parser.describe_or_def() for parser in self._inner)
        return desc

    def describe_value(self, value: object, /) -> str:
        for parser in self._inner:
            try:
                return parser.describe_value(value)
            except TypeError:
                pass

        raise TypeError(
            f"parser {self} can't handle value of type {_tx.type_repr(type(value))}"
        )

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        result = []
        got_options = False
        for parser in self._inner:
            if options := parser.options():
                result.extend(options)
                got_options = True
        if got_options:
            return result
        else:
            return None

    def completer(self) -> yuio.complete.Completer | None:
        completers = []
        for parser in self._inner:
            if completer := parser.completer():
                completers.append((parser.describe(), completer))
        if not completers:
            return None
        elif len(completers) == 1:
            return completers[0][1]
        else:
            return yuio.complete.Alternative(completers)

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return yuio.json_schema.OneOf(
            [parser.to_json_schema(ctx) for parser in self._inner]
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        for parser in self._inner:
            try:
                return parser.to_json_value(value)
            except TypeError:
                pass

        raise TypeError(
            f"parser {self} can't handle value of type {_tx.type_repr(type(value))}"
        )

    def is_secret(self) -> bool:
        return any(parser.is_secret() for parser in self._inner)

    def __repr__(self):
        return f"{self.__class__.__name__}{self._inner_raw!r}"


class _BoundImpl(ValidatingParser[T], _t.Generic[T, Cmp]):
    def __init__(
        self,
        inner: Parser[T] | None,
        /,
        *,
        lower: Cmp | None = None,
        lower_inclusive: Cmp | None = None,
        upper: Cmp | None = None,
        upper_inclusive: Cmp | None = None,
        mapper: _t.Callable[[T], Cmp],
        desc: str,
    ):
        super().__init__(inner)

        self._lower_bound: Cmp | None = None
        self._lower_bound_is_inclusive: bool = True
        self._upper_bound: Cmp | None = None
        self._upper_bound_is_inclusive: bool = True

        if lower is not None and lower_inclusive is not None:
            raise TypeError(
                "lower and lower_inclusive cannot be given at the same time"
            )
        elif lower is not None:
            self._lower_bound = lower
            self._lower_bound_is_inclusive = False
        elif lower_inclusive is not None:
            self._lower_bound = lower_inclusive
            self._lower_bound_is_inclusive = True

        if upper is not None and upper_inclusive is not None:
            raise TypeError(
                "upper and upper_inclusive cannot be given at the same time"
            )
        elif upper is not None:
            self._upper_bound = upper
            self._upper_bound_is_inclusive = False
        elif upper_inclusive is not None:
            self._upper_bound = upper_inclusive
            self._upper_bound_is_inclusive = True

        self.__mapper = mapper
        self.__desc = desc

    def _validate(self, value: T, /):
        mapped = self.__mapper(value)

        if self._lower_bound is not None:
            if self._lower_bound_is_inclusive and mapped < self._lower_bound:
                raise ParsingError(
                    "%s should be greater than or equal to `%s`: `%r`",
                    self.__desc,
                    self._lower_bound,
                    value,
                )
            elif not self._lower_bound_is_inclusive and not self._lower_bound < mapped:
                raise ParsingError(
                    "%s should be greater than `%s`: `%r`",
                    self.__desc,
                    self._lower_bound,
                    value,
                )

        if self._upper_bound is not None:
            if self._upper_bound_is_inclusive and self._upper_bound < mapped:
                raise ParsingError(
                    "%s should be lesser than or equal to `%s`: `%r`",
                    self.__desc,
                    self._upper_bound,
                    value,
                )
            elif not self._upper_bound_is_inclusive and not mapped < self._upper_bound:
                raise ParsingError(
                    "%s should be lesser than `%s`: `%r`",
                    self.__desc,
                    self._upper_bound,
                    value,
                )

    def __repr__(self):
        desc = ""
        if self._lower_bound is not None:
            desc += repr(self._lower_bound)
            desc += " <= " if self._lower_bound_is_inclusive else " < "
        mapper_name = getattr(self.__mapper, "__name__")
        if mapper_name and mapper_name != "<lambda>":
            desc += mapper_name
        else:
            desc += "x"
        if self._upper_bound is not None:
            desc += " <= " if self._upper_bound_is_inclusive else " < "
            desc += repr(self._upper_bound)
        return f"{self.__class__.__name__}({self.__wrapped_parser__!r}, {desc})"


class Bound(_BoundImpl[Cmp, Cmp], _t.Generic[Cmp]):
    """Bound(inner: Parser[Cmp], /, *, lower: Cmp | None = None, lower_inclusive: Cmp | None = None, upper: Cmp | None = None, upper_inclusive: Cmp | None = None)

    Check that value is upper- or lower-bound by some constraints.

    :param inner:
        parser whose result will be validated.
    :param lower:
        set lower bound for value, so we require that ``value > lower``.
        Can't be given if `lower_inclusive` is also given.
    :param lower_inclusive:
        set lower bound for value, so we require that ``value >= lower``.
        Can't be given if `lower` is also given.
    :param upper:
        set upper bound for value, so we require that ``value < upper``.
        Can't be given if `upper_inclusive` is also given.
    :param upper_inclusive:
        set upper bound for value, so we require that ``value <= upper``.
        Can't be given if `upper` is also given.
    :example:
        ::

            >>> # Int in range `0 < x <= 1`:
            >>> Bound(Int(), lower=0, upper_inclusive=1)
            Bound(Int, 0 < x <= 1)

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls,
            inner: Parser[Cmp],
            /,
            *,
            lower: Cmp | None = None,
            lower_inclusive: Cmp | None = None,
            upper: Cmp | None = None,
            upper_inclusive: Cmp | None = None,
        ) -> Bound[Cmp]: ...

        @_t.overload
        def __new__(
            cls,
            *,
            lower: Cmp | None = None,
            lower_inclusive: Cmp | None = None,
            upper: Cmp | None = None,
            upper_inclusive: Cmp | None = None,
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        inner: Parser[Cmp] | None = None,
        /,
        *,
        lower: Cmp | None = None,
        lower_inclusive: Cmp | None = None,
        upper: Cmp | None = None,
        upper_inclusive: Cmp | None = None,
    ):
        super().__init__(
            inner,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
            mapper=lambda x: x,
            desc="Value",
        )

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        bound = {}
        if isinstance(self._lower_bound, (int, float)):
            bound[
                "minimum" if self._lower_bound_is_inclusive else "exclusiveMinimum"
            ] = self._lower_bound
        if isinstance(self._upper_bound, (int, float)):
            bound[
                "maximum" if self._upper_bound_is_inclusive else "exclusiveMaximum"
            ] = self._upper_bound
        if bound:
            return yuio.json_schema.AllOf(
                [super().to_json_schema(ctx), yuio.json_schema.Opaque(bound)]
            )
        else:
            return super().to_json_schema(ctx)


@_t.overload
def Gt(inner: Parser[Cmp], bound: Cmp, /) -> Bound[Cmp]: ...
@_t.overload
def Gt(bound: _tx.SupportsLt[_t.Any], /) -> PartialParser: ...
def Gt(*args) -> _t.Any:
    """Gt(inner: Parser[Cmp], bound: Cmp, /)

    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        lower bound for parsed values.

    """

    if len(args) == 1:
        return Bound(lower=args[0])
    elif len(args) == 2:
        return Bound(args[0], lower=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


@_t.overload
def Ge(inner: Parser[Cmp], bound: Cmp, /) -> Bound[Cmp]: ...
@_t.overload
def Ge(bound: _tx.SupportsLt[_t.Any], /) -> PartialParser: ...
def Ge(*args) -> _t.Any:
    """Ge(inner: Parser[Cmp], bound: Cmp, /)

    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        lower inclusive bound for parsed values.

    """

    if len(args) == 1:
        return Bound(lower_inclusive=args[0])
    elif len(args) == 2:
        return Bound(args[0], lower_inclusive=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


@_t.overload
def Lt(inner: Parser[Cmp], bound: Cmp, /) -> Bound[Cmp]: ...
@_t.overload
def Lt(bound: _tx.SupportsLt[_t.Any], /) -> PartialParser: ...
def Lt(*args) -> _t.Any:
    """Lt(inner: Parser[Cmp], bound: Cmp, /)

    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        upper bound for parsed values.

    """

    if len(args) == 1:
        return Bound(upper=args[0])
    elif len(args) == 2:
        return Bound(args[0], upper=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


@_t.overload
def Le(inner: Parser[Cmp], bound: Cmp, /) -> Bound[Cmp]: ...
@_t.overload
def Le(bound: _tx.SupportsLt[_t.Any], /) -> PartialParser: ...
def Le(*args) -> _t.Any:
    """Le(inner: Parser[Cmp], bound: Cmp, /)

    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        upper inclusive bound for parsed values.

    """

    if len(args) == 1:
        return Bound(upper_inclusive=args[0])
    elif len(args) == 2:
        return Bound(args[0], upper_inclusive=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


class LenBound(_BoundImpl[Sz, int], _t.Generic[Sz]):
    """LenBound(inner: Parser[Sz], /, *, lower: int | None = None, lower_inclusive: int | None = None, upper: int | None = None, upper_inclusive: int | None = None)

    Check that length of a value is upper- or lower-bound by some constraints.

    The signature is the same as of the :class:`Bound` class.

    :param inner:
        parser whose result will be validated.
    :param lower:
        set lower bound for value's length, so we require that ``len(value) > lower``.
        Can't be given if `lower_inclusive` is also given.
    :param lower_inclusive:
        set lower bound for value's length, so we require that ``len(value) >= lower``.
        Can't be given if `lower` is also given.
    :param upper:
        set upper bound for value's length, so we require that ``len(value) < upper``.
        Can't be given if `upper_inclusive` is also given.
    :param upper_inclusive:
        set upper bound for value's length, so we require that ``len(value) <= upper``.
        Can't be given if `upper` is also given.
    :example:
        ::

            >>> # List of up to five ints:
            >>> LenBound(List(Int()), upper_inclusive=5)
            LenBound(List(Int), len <= 5)

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls,
            inner: Parser[Sz],
            /,
            *,
            lower: int | None = None,
            lower_inclusive: int | None = None,
            upper: int | None = None,
            upper_inclusive: int | None = None,
        ) -> LenBound[Sz]: ...

        @_t.overload
        def __new__(
            cls,
            /,
            *,
            lower: int | None = None,
            lower_inclusive: int | None = None,
            upper: int | None = None,
            upper_inclusive: int | None = None,
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        inner: Parser[Sz] | None = None,
        /,
        *,
        lower: int | None = None,
        lower_inclusive: int | None = None,
        upper: int | None = None,
        upper_inclusive: int | None = None,
    ):
        super().__init__(
            inner,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
            mapper=len,
            desc="Length of value",
        )

    def get_nargs(self) -> _t.Literal["+", "*"] | int:
        if not self._inner.supports_parse_many():
            # somebody bound len of a string?
            return self._inner.get_nargs()

        lower = self._lower_bound
        if lower is not None and not self._lower_bound_is_inclusive:
            lower += 1
        upper = self._upper_bound
        if upper is not None and not self._upper_bound_is_inclusive:
            upper -= 1

        if lower == upper and lower is not None:
            return lower
        elif lower is not None and lower > 0:
            return "+"
        else:
            return "*"

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        bound = {}
        min_bound = self._lower_bound
        if not self._lower_bound_is_inclusive and min_bound is not None:
            min_bound -= 1
        if min_bound is not None:
            bound["minLength"] = bound["minItems"] = bound["minProperties"] = min_bound
        max_bound = self._upper_bound
        if not self._upper_bound_is_inclusive and max_bound is not None:
            max_bound += 1
        if max_bound is not None:
            bound["maxLength"] = bound["maxItems"] = bound["maxProperties"] = max_bound
        if bound:
            return yuio.json_schema.AllOf(
                [super().to_json_schema(ctx), yuio.json_schema.Opaque(bound)]
            )
        else:
            return super().to_json_schema(ctx)


@_t.overload
def LenGt(inner: Parser[Sz], bound: int, /) -> LenBound[Sz]: ...
@_t.overload
def LenGt(bound: int, /) -> PartialParser: ...
def LenGt(*args) -> _t.Any:
    """LenGt(inner: Parser[Sz], bound: int, /)

    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        lower bound for parsed values's length.

    """

    if len(args) == 1:
        return LenBound(lower=args[0])
    elif len(args) == 2:
        return LenBound(args[0], lower=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


@_t.overload
def LenGe(inner: Parser[Sz], bound: int, /) -> LenBound[Sz]: ...
@_t.overload
def LenGe(bound: int, /) -> PartialParser: ...
def LenGe(*args) -> _t.Any:
    """LenGe(inner: Parser[Sz], bound: int, /)

    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        lower inclusive bound for parsed values's length.

    """

    if len(args) == 1:
        return LenBound(lower_inclusive=args[0])
    elif len(args) == 2:
        return LenBound(args[0], lower_inclusive=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


@_t.overload
def LenLt(inner: Parser[Sz], bound: int, /) -> LenBound[Sz]: ...
@_t.overload
def LenLt(bound: int, /) -> PartialParser: ...
def LenLt(*args) -> _t.Any:
    """LenLt(inner: Parser[Sz], bound: int, /)

    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        upper bound for parsed values's length.

    """

    if len(args) == 1:
        return LenBound(upper=args[0])
    elif len(args) == 2:
        return LenBound(args[0], upper=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


@_t.overload
def LenLe(inner: Parser[Sz], bound: int, /) -> LenBound[Sz]: ...
@_t.overload
def LenLe(bound: int, /) -> PartialParser: ...
def LenLe(*args) -> _t.Any:
    """LenLe(inner: Parser[Sz], bound: int, /)

    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.
    :param bound:
        upper inclusive bound for parsed values's length.

    """

    if len(args) == 1:
        return LenBound(upper_inclusive=args[0])
    elif len(args) == 2:
        return LenBound(args[0], upper_inclusive=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


class OneOf(ValidatingParser[T], _t.Generic[T]):
    """OneOf(inner: Parser[T], values: typing.Collection[T], /)

    Check that the parsed value is one of the given set of values.

    :param inner:
        parser whose result will be validated.
    :param values:
        collection of allowed values.
    :example:
        ::

            >>> # Accepts only strings 'A', 'B', or 'C':
            >>> OneOf(Str(), ['A', 'B', 'C'])
            OneOf(Str)

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], values: _t.Collection[T], /) -> OneOf[T]: ...

        @_t.overload
        def __new__(cls, values: _t.Collection[T], /) -> PartialParser: ...

        def __new__(cls, *args) -> _t.Any: ...

    def __init__(self, *args):
        inner: Parser[T] | None
        values: _t.Collection[T]
        if len(args) == 1:
            inner, values = None, args[0]
        elif len(args) == 2:
            inner, values = args
        else:
            raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")

        super().__init__(inner)

        self._allowed_values = values

    def _validate(self, value: T, /):
        if value not in self._allowed_values:
            raise ParsingError(
                "Can't parse `%r`, should be %s",
                value,
                yuio.string.JoinRepr.or_(self._allowed_values),
            )

    def describe(self) -> str | None:
        desc = "|".join(self.describe_value(e) for e in self._allowed_values)
        if len(desc) < 80:
            if len(self._allowed_values) > 1:
                desc = f"{{{desc}}}"
            return desc
        else:
            return super().describe()

    def describe_or_def(self) -> str:
        desc = "|".join(self.describe_value(e) for e in self._allowed_values)
        if len(desc) < 80:
            if len(self._allowed_values) > 1:
                desc = f"{{{desc}}}"
            return desc
        else:
            return super().describe_or_def()

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        return [
            yuio.widget.Option(e, self.describe_value(e)) for e in self._allowed_values
        ]

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Choice(
            [yuio.complete.Option(self.describe_value(e)) for e in self._allowed_values]
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        allowed_values = list(self._allowed_values)

        options = _t.cast(list[yuio.widget.Option[T | yuio.Missing]], self.options())

        if default is yuio.MISSING:
            default_index = 0
        elif default in allowed_values:
            default_index = list(allowed_values).index(default)  # type: ignore
        else:
            options.insert(
                0, yuio.widget.Option(yuio.MISSING, default_description or str(default))
            )
            default_index = 0

        return yuio.widget.Choice(options, default_index=default_index)


class WithMeta(MappingParser[T, T], _t.Generic[T]):
    """WithMeta(inner: Parser[T], /, *, desc: str, completer: yuio.complete.Completer | None | ~yuio.MISSING = MISSING)

    Overrides inline help messages and other meta information of a wrapped parser.

    Inline help messages will show up as hints in autocompletion and widgets.

    :param inner:
        inner parser.
    :param desc:
        description override. This short string will be used in CLI, widgets, and
        completers to describe expected value.
    :param completer:
        completer override. Pass :data:`None` to disable completion.

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls,
            inner: Parser[T],
            /,
            *,
            desc: str | None = None,
            completer: yuio.complete.Completer | yuio.Missing | None = yuio.MISSING,
        ) -> MappingParser[T, T]: ...

        @_t.overload
        def __new__(
            cls,
            /,
            *,
            desc: str | None = None,
            completer: yuio.complete.Completer | yuio.Missing | None = yuio.MISSING,
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        *args,
        desc: str | None = None,
        completer: yuio.complete.Completer | yuio.Missing | None = yuio.MISSING,
    ):
        inner: Parser[T] | None
        if not args:
            inner = None
        elif len(args) == 1:
            inner = args[0]
        else:
            raise TypeError(f"expected at most 1 positional argument, got {len(args)}")

        self._desc = desc
        self._completer = completer
        super().__init__(inner)

    def check_type(self, value: object, /) -> _t.TypeGuard[T]:
        return True

    def describe(self) -> str | None:
        return self._desc or self._inner.describe()

    def describe_or_def(self) -> str:
        return self._desc or self._inner.describe_or_def()

    def describe_many(self) -> str | tuple[str, ...]:
        return self._desc or self._inner.describe_many()

    def describe_value(self, value: object, /) -> str:
        return self._inner.describe_value(value)

    def parse_with_ctx(self, ctx: StrParsingContext, /) -> T:
        return self._inner.parse_with_ctx(ctx)

    def parse_many_with_ctx(self, ctxs: _t.Sequence[StrParsingContext], /) -> T:
        return self._inner.parse_many_with_ctx(ctxs)

    def parse_config_with_ctx(self, ctx: ConfigParsingContext, /) -> T:
        return self._inner.parse_config_with_ctx(ctx)

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        return self._inner.options()

    def completer(self) -> yuio.complete.Completer | None:
        if self._completer is not yuio.MISSING:
            return self._completer  # type: ignore
        else:
            return self._inner.completer()

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        return self._inner.widget(default, input_description, default_description)

    def to_json_value(self, value: object) -> yuio.json_schema.JsonValue:
        return self._inner.to_json_value(value)


class _WidgetResultMapper(yuio.widget.Map[T | yuio.Missing, str]):
    def __init__(
        self,
        parser: Parser[T],
        input_description: str | None,
        default: object | yuio.Missing,
        widget: yuio.widget.Widget[str],
    ):
        self._parser = parser
        self._input_description = input_description
        self._default = default
        super().__init__(widget, self.mapper)

    def mapper(self, s: str) -> T | yuio.Missing:
        if not s and self._default is not yuio.MISSING:
            return yuio.MISSING
        elif not s:
            raise ParsingError("Input is required")
        try:
            return self._parser.parse_with_ctx(StrParsingContext(s))
        except ParsingError as e:
            if (
                isinstance(
                    self._inner, (yuio.widget.Input, yuio.widget.InputWithCompletion)
                )
                and e.pos
                and e.raw == self._inner.text
            ):
                if e.pos == (0, len(self._inner.text)):
                    # Don't highlight the entire text, it's not useful and creates
                    # visual noise.
                    self._inner.err_region = None
                else:
                    self._inner.err_region = e.pos
                e.raw = None
                e.pos = None
            raise

    @property
    def help_data(self):
        return super().help_data.with_action(
            group="Input Format",
            msg=self._input_description,
            prepend=True,
            prepend_group=True,
        )


def _secret_widget(
    parser: Parser[T],
    default: object | yuio.Missing,
    input_description: str | None,
    default_description: str | None,
    /,
) -> yuio.widget.Widget[T | yuio.Missing]:
    return _WidgetResultMapper(
        parser,
        input_description,
        default,
        (
            yuio.widget.SecretInput(
                placeholder=default_description or "",
            )
        ),
    )


class StrParsingContext:
    """StrParsingContext(content: str, /, *, n_arg: int | None = None)

    String parsing context tracks current position in the string.

    :param content:
        content to parse.
    :param n_arg:
        content index when using :meth:`~Parser.parse_many`.

    """

    def __init__(
        self,
        content: str,
        /,
        *,
        n_arg: int | None = None,
        _value: str | None = None,
        _start: int | None = None,
        _end: int | None = None,
    ):
        self.start: int = _start if _start is not None else 0
        """
        Start position of the value.

        """

        self.end: int = _end if _end is not None else self.start + len(content)
        """
        End position of the value.

        """

        self.content: str = content
        """
        Full content of the value that was passed to :meth:`Parser.parse`.

        """

        self.value: str = _value if _value is not None else content
        """
        Part of the :attr:`~StrParsingContext.content` that's currently being parsed.

        """

        self.n_arg: int | None = n_arg
        """
        For :meth:`~Parser.parse_many`, this attribute contains index of the value
        that is being parsed. For :meth:`~Parser.parse`, this is :data:`None`.

        """

    def split(
        self, delimiter: str | None = None, /, maxsplit: int = -1
    ) -> _t.Generator[StrParsingContext]:
        """
        Split current value by the given delimiter while keeping track of the current position.

        """

        if delimiter is None:
            yield from self._split_space(maxsplit=maxsplit)
            return

        dlen = len(delimiter)
        start = self.start
        for part in self.value.split(delimiter, maxsplit=maxsplit):
            yield StrParsingContext(
                self.content,
                _value=part,
                _start=start,
                _end=start + len(part),
                n_arg=self.n_arg,
            )
            start += len(part) + dlen

    def _split_space(self, maxsplit: int = -1) -> _t.Generator[StrParsingContext]:
        i = 0
        n_splits = 0
        is_space = True
        for part in re.split(r"(\s+)", self.value):
            is_space = not is_space
            if is_space:
                i += len(part)
                continue

            if not part:
                continue

            if maxsplit >= 0 and n_splits >= maxsplit:
                part = self.value[i:]
                yield StrParsingContext(
                    self.content,
                    _value=part,
                    _start=i,
                    _end=i + len(part),
                    n_arg=self.n_arg,
                )
                return
            else:
                yield StrParsingContext(
                    self.content,
                    _value=part,
                    _start=i,
                    _end=i + len(part),
                    n_arg=self.n_arg,
                )
                i += len(part)
                n_splits += 1

    def strip(self, chars: str | None = None, /) -> StrParsingContext:
        """
        Strip current value while keeping track of the current position.

        """

        l_stripped = self.value.lstrip(chars)
        start = self.start + (len(self.value) - len(l_stripped))
        stripped = l_stripped.rstrip(chars)
        return StrParsingContext(
            self.content,
            _value=stripped,
            _start=start,
            _end=start + len(stripped),
            n_arg=self.n_arg,
        )

    def strip_if_non_space(self) -> StrParsingContext:
        """
        Strip current value unless it entirely consists of spaces.

        """

        if not self.value or self.value.isspace():
            return self
        else:
            return self.strip()

    # If you need more methods, feel free to open an issue or send a PR!
    # For now, `split` and `split` is enough.


class ConfigParsingContext:
    """
    Config parsing context tracks path in the config, similar to JSON path.

    """

    def __init__(
        self,
        value: object,
        /,
        *,
        parent: ConfigParsingContext | None = None,
        key: _t.Any = None,
        desc: str | None = None,
    ):
        self.value: object = value
        """
        Config value to be validated and parsed.

        """

        self.parent: ConfigParsingContext | None = parent
        """
        Parent context.

        """

        self.key: _t.Any = key
        """
        Key that was accessed when we've descended from parent context to this one.

        Root context has key :data:`None`.

        """

        self.desc: str | None = desc
        """
        Additional description of the key.

        """

    def descend(
        self,
        value: _t.Any,
        key: _t.Any,
        desc: str | None = None,
    ) -> ConfigParsingContext:
        """
        Create a new context that adds a new key to the path.

        :param value:
            inner value that was derived from the current value by accessing it with
            the given `key`.
        :param key:
            key that we use to descend into the current value.

            For example, let's say we're parsing a list. We iterate over it and pass
            its elements to a sub-parser. Before calling a sub-parser, we need to
            make a new context for it. In this situation, we'll pass current element
            as `value`, and is index as `key`.
        :param desc:
            human-readable description for the new context. Will be colorized
            and ``%``-formatted with a single named argument `key`.

            This is useful when parsing structures that need something more complex than
            JSON path. For example, when parsing a key in a dictionary, it is helpful
            to set description to something like ``"key of element #%(key)r"``.
            This way, parsing errors will have a more clear message:

            .. code-block:: text

                Parsing error:
                  In key of element #2:
                    Expected str, got int: 10

        """

        return ConfigParsingContext(value, parent=self, key=key, desc=desc)

    def make_path(self) -> list[tuple[_t.Any, str | None]]:
        """
        Capture current path.

        :returns:
            a list of tuples. First element of each tuple is a key, second is
            an additional description.

        """

        path = []

        root = self
        while True:
            if root.parent is None:
                break
            else:
                path.append((root.key, root.desc))
                root = root.parent

        path.reverse()

        return path


class _PathRenderer:
    def __init__(self, path: list[tuple[_t.Any, str | None]]):
        self._path = path

    def __colorized_str__(
        self, ctx: yuio.string.ReprContext
    ) -> yuio.string.ColorizedString:
        code_color = ctx.theme.get_color("msg/text:code/repr hl:repr")
        punct_color = ctx.theme.get_color("msg/text:code/repr hl/punct:repr")

        msg = yuio.string.ColorizedString(code_color)
        msg.start_no_wrap()

        for i, (key, desc) in enumerate(self._path):
            if desc:
                desc = (
                    (yuio.string)
                    .colorize(desc, ctx=ctx)
                    .percent_format({"key": key}, ctx=ctx)
                )

                if i == len(self._path) - 1:
                    # Last key.
                    if msg:
                        msg.append_color(punct_color)
                        msg.append_str(", ")
                    msg.append_colorized_str(desc)
                else:
                    # Element in the middle.
                    if not msg:
                        msg.append_str("$")
                    msg.append_color(punct_color)
                    msg.append_str(".<")
                    msg.append_colorized_str(desc)
                    msg.append_str(">")
            elif isinstance(key, str) and re.match(r"^[a-zA-Z_][\w-]*$", key):
                # Key is identifier-like, use `x.key` notation.
                if not msg:
                    msg.append_str("$")
                msg.append_color(punct_color)
                msg.append_str(".")
                msg.append_color(code_color)
                msg.append_str(key)
            else:
                # Key is not identifier-like, use `x[key]` notation.
                if not msg:
                    msg.append_str("$")
                msg.append_color(punct_color)
                msg.append_str("[")
                msg.append_color(code_color)
                msg.append_str(repr(key))
                msg.append_color(punct_color)
                msg.append_str("]")

        msg.end_no_wrap()
        return msg


class _CodeRenderer:
    def __init__(self, code: str, pos: tuple[int, int], as_cli: bool = False):
        self._code = code
        self._pos = pos
        self._as_cli = as_cli

    def __colorized_str__(
        self, ctx: yuio.string.ReprContext
    ) -> yuio.string.ColorizedString:
        width = ctx.width - 2  # Account for indentation.

        if width < 10:  # 6 symbols for ellipsis and at least 2 wide chars.
            return yuio.string.ColorizedString()

        start, end = self._pos
        if end == start:
            end += 1

        left = self._code[:start]
        center = self._code[start:end]
        right = self._code[end:]

        l_width = yuio.string.line_width(left)
        c_width = yuio.string.line_width(center)
        r_width = yuio.string.line_width(right)

        available_width = width - (3 if left else 0) - 3
        if c_width > available_width:
            # Center can't fit: remove left and right side,
            # and trim as much center as needed.

            left = "..." if l_width > 3 else left
            l_width = len(left)

            right = ""
            r_width = 0

            new_c = ""
            c_width = 0

            for c in center:
                cw = yuio.string.line_width(c)
                if c_width + cw <= available_width:
                    new_c += c
                    c_width += cw
                else:
                    new_c += "..."
                    c_width += 3
                    break
            center = new_c

        if r_width > 3 and l_width + c_width + r_width > width:
            # Trim right side.
            new_r = ""
            r_width = 3
            for c in right:
                cw = yuio.string.line_width(c)
                if l_width + c_width + r_width + cw <= width:
                    new_r += c
                    r_width += cw
                else:
                    new_r += "..."
                    break
            right = new_r

        if l_width > 3 and l_width + c_width + r_width > width:
            # Trim left side.
            new_l = ""
            l_width = 3
            for c in left[::-1]:
                cw = yuio.string.line_width(c)
                if l_width + c_width + r_width + cw <= width:
                    new_l += c
                    l_width += cw
                else:
                    new_l += "..."
                    break
            left = new_l[::-1]

        if self._as_cli:
            punct_color = ctx.theme.get_color(
                "msg/text:code/sh-usage hl/punct:sh-usage"
            )
        else:
            punct_color = ctx.theme.get_color("msg/text:code/text hl/punct:text")

        res = yuio.string.ColorizedString()
        res.start_no_wrap()

        if self._as_cli:
            res.append_color(punct_color)
            res.append_str("$ ")
            res.append_colorized_str(
                ctx.str(
                    yuio.string.Hl(
                        left.replace("%", "%%") + "%s" + right.replace("%", "%%"),  # pyright: ignore[reportArgumentType]
                        yuio.string.WithBaseColor(
                            center, base_color="hl/error:sh-usage"
                        ),
                        syntax="sh-usage",
                    )
                )
            )
        else:
            text_color = ctx.theme.get_color("msg/text:code/text")
            res.append_color(punct_color)
            res.append_str("> ")
            res.append_color(text_color)
            res.append_str(left)
            res.append_color(text_color | ctx.theme.get_color("hl/error:text"))
            res.append_str(center)
            res.append_color(text_color)
            res.append_str(right)
        res.append_color(yuio.color.Color.NONE)
        res.append_str("\n")
        if self._as_cli:
            text_color = ctx.theme.get_color("msg/text:code/sh-usage")
            res.append_color(text_color | ctx.theme.get_color("hl/error:sh-usage"))
        else:
            text_color = ctx.theme.get_color("msg/text:code/text")
            res.append_color(text_color | ctx.theme.get_color("hl/error:text"))
        res.append_str("  ")
        res.append_str(" " * yuio.string.line_width(left))
        res.append_str("~" * yuio.string.line_width(center))

        res.end_no_wrap()

        return res


def _repr_and_adjust_pos(s: str, pos: tuple[int, int]):
    start, end = pos

    left = json.dumps(s[:start])[:-1]
    center = json.dumps(s[start:end])[1:-1]
    right = json.dumps(s[end:])[1:]

    return left + center + right, (len(left), len(left) + len(center))


_FromTypeHintCallback: _t.TypeAlias = _t.Callable[
    [type, type | None, tuple[object, ...]], Parser[object] | None
]


_FROM_TYPE_HINT_CALLBACKS: list[tuple[_FromTypeHintCallback, bool]] = []
_FROM_TYPE_HINT_DELIM_SUGGESTIONS: list[str | None] = [
    None,
    ",",
    "@",
    "/",
    "=",
]


class _FromTypeHintDepth(threading.local):
    def __init__(self):
        self.depth: int = 0
        self.uses_delim = False


_FROM_TYPE_HINT_DEPTH: _FromTypeHintDepth = _FromTypeHintDepth()


@_t.overload
def from_type_hint(ty: type[T], /) -> Parser[T]: ...
@_t.overload
def from_type_hint(ty: object, /) -> Parser[object]: ...
def from_type_hint(ty: _t.Any, /) -> Parser[object]:
    """from_type_hint(ty: type[T], /) -> Parser[T]

    Create parser from a type hint.

    :param ty:
        a type hint.

        This type hint should not contain strings or forward references. Make sure
        they're resolved before passing it to this function.
    :returns:
        a parser instance created from type hint.
    :raises:
        :class:`TypeError` if type hint contains forward references or types
        that don't have associated parsers.
    :example:
        ::

            >>> from_type_hint(list[int] | None)
            Optional(List(Int))

    """

    result = _from_type_hint(ty)
    setattr(result, "_Parser__typehint", ty)
    return result


def _from_type_hint(ty: _t.Any, /) -> Parser[object]:
    if isinstance(ty, (str, _t.ForwardRef)):
        raise TypeError(f"forward references are not supported here: {ty}")

    origin = _t.get_origin(ty)
    args = _t.get_args(ty)

    if origin is _t.Annotated:
        p = from_type_hint(args[0])
        for arg in args[1:]:
            if isinstance(arg, PartialParser):
                p = arg.wrap(p)
        return p

    for cb, uses_delim in _FROM_TYPE_HINT_CALLBACKS:
        prev_uses_delim = _FROM_TYPE_HINT_DEPTH.uses_delim
        _FROM_TYPE_HINT_DEPTH.uses_delim = uses_delim
        _FROM_TYPE_HINT_DEPTH.depth += uses_delim
        try:
            p = cb(ty, origin, args)
            if p is not None:
                return p
        finally:
            _FROM_TYPE_HINT_DEPTH.uses_delim = prev_uses_delim
            _FROM_TYPE_HINT_DEPTH.depth -= uses_delim

    if _tx.is_union(origin):
        if is_optional := (type(None) in args):
            args = list(args)
            args.remove(type(None))
        if len(args) == 1:
            p = from_type_hint(args[0])
        else:
            p = Union(*[from_type_hint(arg) for arg in args])
        if is_optional:
            p = Optional(p)
        return p
    else:
        raise TypeError(f"unsupported type {_tx.type_repr(ty)}")


@_t.overload
def register_type_hint_conversion(
    cb: _FromTypeHintCallback,
    /,
    *,
    uses_delim: bool = False,
) -> _FromTypeHintCallback: ...
@_t.overload
def register_type_hint_conversion(
    *,
    uses_delim: bool = False,
) -> _t.Callable[[_FromTypeHintCallback], _FromTypeHintCallback]: ...
def register_type_hint_conversion(
    cb: _FromTypeHintCallback | None = None,
    /,
    *,
    uses_delim: bool = False,
) -> (
    _FromTypeHintCallback | _t.Callable[[_FromTypeHintCallback], _FromTypeHintCallback]
):
    """
    Register a new converter from a type hint to a parser.

    This function takes a callback that accepts three positional arguments:

    - a type hint,
    - a type hint's origin (as defined by :func:`typing.get_origin`),
    - a type hint's args (as defined by :func:`typing.get_args`).

    The callback should return a parser if it can, or :data:`None` otherwise.

    All registered callbacks are tried in the same order
    as they were registered.

    If `uses_delim` is :data:`True`, callback can use
    :func:`suggest_delim_for_type_hint_conversion`.

    This function can be used as a decorator.

    :param cb:
        a function that should inspect a type hint and possibly return a parser.
    :param uses_delim:
        indicates that callback will use
        :func:`suggest_delim_for_type_hint_conversion`.
    :example:
        .. invisible-code-block: python

            class MyType: ...
            class MyTypeParser(ValueParser[MyType]):
                def __init__(self): super().__init__(MyType)
                def parse_with_ctx(self, ctx: StrParsingContext, /): ...
                def parse_config_with_ctx(self, value, /): ...
                def to_json_schema(self, ctx, /): ...
                def to_json_value(self, value, /): ...

        .. code-block:: python

            @register_type_hint_conversion
            def my_type_conversion(ty, origin, args):
                if ty is MyType:
                    return MyTypeParser()
                else:
                    return None

        ::

            >>> from_type_hint(MyType)
            MyTypeParser

        .. invisible-code-block: python

            del _FROM_TYPE_HINT_CALLBACKS[-1]

    """

    def registrar(cb: _FromTypeHintCallback):
        _FROM_TYPE_HINT_CALLBACKS.append((cb, uses_delim))
        return cb

    return registrar(cb) if cb is not None else registrar


def suggest_delim_for_type_hint_conversion() -> str | None:
    """
    Suggests a delimiter for use in type hint converters.

    When creating a parser for a collection of items based on a type hint,
    it is important to use different delimiters for nested collections.
    This function can suggest such a delimiter based on the current type hint's depth.

    .. invisible-code-block: python

        class MyCollection(list, _t.Generic[T]): ...
        class MyCollectionParser(CollectionParser[MyCollection[T], T], _t.Generic[T]):
            def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
                super().__init__(inner, ty=MyCollection, ctor=MyCollection, delimiter=delimiter)
            def to_json_schema(self, ctx, /): ...
            def to_json_value(self, value, /): ...

    :raises:
        :class:`RuntimeError` if called from a type converter that
        didn't set `uses_delim` to :data:`True`.
    :example:
        .. code-block:: python

            @register_type_hint_conversion(uses_delim=True)
            def my_collection_conversion(ty, origin, args):
                if origin is MyCollection:
                    return MyCollectionParser(
                        from_type_hint(args[0]),
                        delimiter=suggest_delim_for_type_hint_conversion(),
                    )
                else:
                    return None

        ::

            >>> parser = from_type_hint(MyCollection[MyCollection[str]])
            >>> parser
            MyCollectionParser(MyCollectionParser(Str))
            >>> # First delimiter is `None`, meaning split by whitespace:
            >>> parser._delimiter is None
            True
            >>> # Second delimiter is `","`:
            >>> parser._inner._delimiter == ","
            True

        ..
            >>> del _FROM_TYPE_HINT_CALLBACKS[-1]

    """

    if not _FROM_TYPE_HINT_DEPTH.uses_delim:
        raise RuntimeError(
            "looking up delimiters is not available in this callback; did you forget"
            " to pass `uses_delim=True` when registering this callback?"
        )

    depth = _FROM_TYPE_HINT_DEPTH.depth - 1
    if depth < len(_FROM_TYPE_HINT_DELIM_SUGGESTIONS):
        return _FROM_TYPE_HINT_DELIM_SUGGESTIONS[depth]
    else:
        return None


register_type_hint_conversion(lambda ty, origin, args: Str() if ty is str else None)
register_type_hint_conversion(lambda ty, origin, args: Int() if ty is int else None)
register_type_hint_conversion(lambda ty, origin, args: Float() if ty is float else None)
register_type_hint_conversion(lambda ty, origin, args: Bool() if ty is bool else None)
register_type_hint_conversion(
    lambda ty, origin, args: (
        Enum(ty) if isinstance(ty, type) and issubclass(ty, enum.Enum) else None
    )
)
register_type_hint_conversion(
    lambda ty, origin, args: Decimal() if ty is decimal.Decimal else None
)
register_type_hint_conversion(
    lambda ty, origin, args: Fraction() if ty is fractions.Fraction else None
)
register_type_hint_conversion(
    lambda ty, origin, args: (
        List(
            from_type_hint(args[0]), delimiter=suggest_delim_for_type_hint_conversion()
        )
        if origin is list
        else None
    ),
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: (
        Set(from_type_hint(args[0]), delimiter=suggest_delim_for_type_hint_conversion())
        if origin is set
        else None
    ),
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: (
        FrozenSet(
            from_type_hint(args[0]), delimiter=suggest_delim_for_type_hint_conversion()
        )
        if origin is frozenset
        else None
    ),
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: (
        Dict(
            from_type_hint(args[0]),
            from_type_hint(args[1]),
            delimiter=suggest_delim_for_type_hint_conversion(),
        )
        if origin is dict
        else None
    ),
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: (
        Tuple(
            *[from_type_hint(arg) for arg in args],
            delimiter=suggest_delim_for_type_hint_conversion(),
        )
        if origin is tuple and ... not in args
        else None
    ),
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: Path() if ty is pathlib.Path else None
)
register_type_hint_conversion(
    lambda ty, origin, args: Json() if ty is yuio.json_schema.JsonValue else None
)
register_type_hint_conversion(
    lambda ty, origin, args: DateTime() if ty is datetime.datetime else None
)
register_type_hint_conversion(
    lambda ty, origin, args: Date() if ty is datetime.date else None
)
register_type_hint_conversion(
    lambda ty, origin, args: Time() if ty is datetime.time else None
)
register_type_hint_conversion(
    lambda ty, origin, args: TimeDelta() if ty is datetime.timedelta else None
)


@register_type_hint_conversion
def __secret(ty, origin, args):
    if ty is SecretValue:
        raise TypeError("yuio.secret.SecretValue requires type arguments")
    if origin is SecretValue:
        if len(args) == 1:
            return Secret(from_type_hint(args[0]))
        else:  # pragma: no cover
            raise TypeError(
                f"yuio.secret.SecretValue requires 1 type argument, got {len(args)}"
            )
    return None


def _is_optional_parser(parser: Parser[_t.Any] | None, /) -> bool:
    while parser is not None:
        if isinstance(parser, Optional):
            return True
        parser = parser.__wrapped_parser__
    return False


def _is_bool_parser(parser: Parser[_t.Any] | None, /) -> bool:
    while parser is not None:
        if isinstance(parser, Bool):
            return True
        parser = parser.__wrapped_parser__
    return False
