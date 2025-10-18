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


Value parsers
-------------

.. autoclass:: Str

.. autoclass:: Int

.. autoclass:: Float

.. autoclass:: Bool

.. autoclass:: Enum(enum_type: typing.Type[E], /, *, by_name: bool = False)

.. autoclass:: Decimal

.. autoclass:: Fraction

.. autoclass:: Json(inner: Parser[T] | None = None, /)

.. autoclass:: List(inner: Parser[T], /, *, delimiter: str | None = None)

.. autoclass:: Set(inner: Parser[T], /, *, delimiter: str | None = None)

.. autoclass:: FrozenSet(inner: Parser[T], /, *, delimiter: str | None = None)

.. autoclass:: Dict(key: Parser[K], value: Parser[V], /, *, delimiter: str | None = None, pair_delimiter: str = ":")

.. autoclass:: Tuple(*parsers: Parser[T], delimiter: str | None = None)

.. autoclass:: Optional(inner: Parser[T], /)

.. autoclass:: Union(*parsers: Parser[T])


File path parsers
-----------------

.. autoclass:: Path

.. autoclass:: NonExistentPath

.. autoclass:: ExistingPath

.. autoclass:: File

.. autoclass:: Dir

.. autoclass:: GitRepo


Validators
----------

.. autoclass:: Regex(inner: Parser[str], regex: str | re.Pattern[str], /, *, group: int | str = 0)

.. autoclass:: Bound(inner: Parser[Cmp], /, *, lower: Cmp | None = None, lower_inclusive: Cmp | None = None, upper: Cmp | None = None, upper_inclusive: Cmp | None = None)

.. autoclass:: Gt(inner: Parser[Cmp], bound: Cmp, /)

.. autoclass:: Ge(inner: Parser[Cmp], bound: Cmp, /)

.. autoclass:: Lt(inner: Parser[Cmp], bound: Cmp, /)

.. autoclass:: Le(inner: Parser[Cmp], bound: Cmp, /)

.. autoclass:: LenBound(inner: Parser[Sz], /, *, lower: int | None = None, lower_inclusive: int | None = None, upper: int | None = None, upper_inclusive: int | None = None)

.. autoclass:: LenGt(inner: Parser[Sz], bound: int, /)

.. autoclass:: LenGe(inner: Parser[Sz], bound: int, /)

.. autoclass:: LenLt(inner: Parser[Sz], bound: int, /)

.. autoclass:: LenLe(inner: Parser[Sz], bound: int, /)

.. autoclass:: OneOf(inner: Parser[T], values: typing.Collection[T], /)


Auxiliary parsers
-----------------

.. autoclass:: Map(inner: Parser[U], fn: typing.Callable[[U], T], rev: typing.Callable[[T | object], U] | None = None, /)

.. autoclass:: Apply(inner: Parser[T], fn: typing.Callable[[T], None], /)

.. autoclass:: Lower(inner: Parser[T], /)

.. autoclass:: Upper(inner: Parser[T], /)

.. autoclass:: CaseFold(inner: Parser[T], /)

.. autoclass:: Strip(inner: Parser[T], /)

.. autoclass:: WithDesc(inner: Parser[T], desc: str /)


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

Instead, we can use :class:`typing.Annotated` to attach validating parsers directly
to type hints:

.. code-block:: python

    from typing import Annotated

    class AppConfig(Config):
        max_line_width: (
            Annotated[int, Gt(0)] | Annotated[str, OneOf(["default", "unlimited", "keep"])]
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
    >>> partial_parser.parse("1,2,3")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
    ...
    TypeError: List requires an inner parser
    ...


Other parser methods
--------------------

:class:`Parser` defines some more methods and attributes.
You don't usually need because Yuio handles everything they do itself.
However, you can still use them in case you need to.

.. autoclass:: Parser
    :noindex:

    .. autoattribute:: __wrapped_parser__

    .. automethod:: get_nargs

    .. automethod:: check_type

    .. automethod:: assert_type

    .. automethod:: describe

    .. automethod:: describe_or_def

    .. automethod:: describe_many

    .. automethod:: describe_many_or_def

    .. automethod:: describe_value

    .. automethod:: describe_value_or_def

    .. automethod:: options

    .. automethod:: completer

    .. automethod:: widget

    .. automethod:: to_json_schema

    .. automethod:: to_json_value


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

This will fail because ``List`` needs an inner parser to function.

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
            def __new__(cls, *args, **kwargs) -> _t.Any:
                ...

With these type hints, our example will fail to type check: :func:`yuio.io.ask`
expects a :class:`Parser`, but ``List.__new__`` returns a :class:`PartialParser`.

Unfortunately, this means that all parsers derived from :class:`WrappingParser`
must provide appropriate type hints for their ``__new__`` method.

.. autoclass:: PartialParser
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

.. autofunction:: register_type_hint_conversion

When implementing a callback, you might need to specify a delimiter
for a collection parser. Use :func:`suggest_delim_for_type_hint_conversion`:

.. autofunction:: suggest_delim_for_type_hint_conversion

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
import textwrap
import threading
import traceback
import types

import yuio
import yuio.complete
import yuio.json_schema
import yuio.widget
from yuio import _typing as _t

T_co = _t.TypeVar("T_co", covariant=True)
T = _t.TypeVar("T")
U = _t.TypeVar("U")
K = _t.TypeVar("K")
V = _t.TypeVar("V")
C = _t.TypeVar("C", bound=_t.Collection[object])
C2 = _t.TypeVar("C2", bound=_t.Collection[object])
Sz = _t.TypeVar("Sz", bound=_t.Sized)
Cmp = _t.TypeVar("Cmp", bound=yuio.SupportsLt[_t.Any])
E = _t.TypeVar("E", bound=enum.Enum)
TU = _t.TypeVar("TU", bound=tuple[object, ...])
P = _t.TypeVar("P", bound="Parser[_t.Any]")


class ParsingError(ValueError, argparse.ArgumentTypeError):
    """Raised when parsing or validation fails.

    This exception is derived from both :class:`ValueError`
    and :class:`argparse.ArgumentTypeError` to ensure that error messages
    are displayed nicely with argparse, and handled correctly in other places.

    """


class PartialParser(abc.ABC):
    """
    An interface of a partial parser.

    """

    def __init__(self) -> None:
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

        return self.__orig_traceback

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
        :return:
            a result of upgrading this parser from partial to full. This method
            usually returns ``self``.

        """


class Parser(PartialParser, _t.Generic[T_co]):
    """
    Base class for parsers.

    """

    # Original type hint from which this parser was derived.
    __typehint: _t.Any = None

    #: An attribute for unwrapping parsers that validate or map results
    #: of other parsers.
    __wrapped_parser__: Parser[object] | None = None

    @abc.abstractmethod
    def parse(self, value: str, /) -> T_co:
        """
        Parse user input, raise :class:`ParsingError` on failure.

        :param value:
            value to parse.

        """

    @abc.abstractmethod
    def parse_many(self, value: _t.Sequence[str], /) -> T_co:
        """
        For collection parsers, parse and validate collection
        by parsing its items one-by-one.

        Example::

            >>> # Let's say we're parsing a set of ints.
            >>> parser = Set(Int())

            >>> # And the user enters collection items one-by-one.
            >>> user_input = ['1', '2', '3']

            >>> # We can parse collection from its items:
            >>> parser.parse_many(user_input)
            {1, 2, 3}

        :param value:
            collection of values to parse.

        """

    @abc.abstractmethod
    def supports_parse_many(self) -> bool:
        """
        Return :data:`True` if this parser returns a collection
        and so supports :meth:`~Parser.parse_many`.

        """

    @abc.abstractmethod
    def parse_config(self, value: object, /) -> T_co:
        """
        Parse value from a config, raise :class:`ParsingError` on failure.

        This method accepts python values that would result from
        parsing json, yaml, and similar formats.

        Example::

            >>> # Let's say we're parsing a set of ints.
            >>> parser = Set(Int())

            >>> # And we're loading it from json.
            >>> import json
            >>> user_config = json.loads('[1, 2, 3]')

            >>> # We can process parsed json:
            >>> parser.parse_config(user_config)
            {1, 2, 3}

        :param value:
            config value to parse.

        """

    @abc.abstractmethod
    def get_nargs(self) -> _t.Literal["-", "+", "*", "?"] | int | None:
        """
        Generate `nargs` for argparse.

        """

    @abc.abstractmethod
    def check_type(self, value: object, /) -> _t.TypeGuard[T_co]:
        """
        Check whether the parser can handle a particular value in its
        :meth:`~Parser.describe_value` and other methods.

        This function is used in :class:`Union` to dispatch values to correct parsers.

        :param value:
            value that needs a type check.

        """

    def assert_type(self, value: object, /) -> _t.TypeGuard[T_co]:
        """
        Call :meth:`~Parser.check_type` and raise a :class:`TypeError`
        if it returns :data:`False`.

        This method always returns :data:`True` or throws an error, but type checkers
        don't know this. Use ``assert parser.assert_type(value)`` so that they
        understand that type of the ``value`` has narrowed.

        :param value:
            value that needs a type check.

        """

        if not self.check_type(value):
            raise TypeError(
                f"parser {self} can't handle value of type {_t.type_repr(type(value))}"
            )
        return True

    @abc.abstractmethod
    def describe(self) -> str | None:
        """
        Return a human-readable description of an expected input.

        """

    @abc.abstractmethod
    def describe_or_def(self) -> str:
        """
        Like :py:meth:`~Parser.describe`, but guaranteed to return something.

        """

    @abc.abstractmethod
    def describe_many(self) -> str | tuple[str, ...] | None:
        """
        Return a human-readable description of a container element.

        Used with :meth:`~Parser.parse_many`.

        """

    @abc.abstractmethod
    def describe_many_or_def(self) -> str | tuple[str, ...]:
        """
        Like :py:meth:`~Parser.describe_many`, but guaranteed to return something.

        """

    @abc.abstractmethod
    def describe_value(self, value: object, /) -> str | None:
        """
        Return a human-readable description of the given value.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        Call :meth:`~Parser.assert_type` to check for this case.

        :param value:
            value that needs a description.

        """

    @abc.abstractmethod
    def describe_value_or_def(self, value: object, /) -> str:
        """
        Like :py:meth:`~Parser.describe_value`, but guaranteed to return something.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        Call :meth:`~Parser.assert_type` to check for this case.

        :param value:
            value that needs a description.

        """

    @abc.abstractmethod
    def options(self) -> _t.Collection[yuio.widget.Option[T_co]] | None:
        """
        Return options for a :class:`~yuio.widget.Multiselect` widget.

        This function can be implemented for parsers that return a fixed set
        of pre-defined values, like :class:`Enum` or :class:`OneOf` widgets.
        Collection parsers may use this data to improve their widgets.
        For example, the :class:`Set` parser will use
        a :class:`~yuio.widget.Multiselect` widget.

        """

    @abc.abstractmethod
    def completer(self) -> yuio.complete.Completer | None:
        """
        Return a completer for values of this parser.

        This function is used when assembling autocompletion functions for shells,
        and when reading values from user via :func:`yuio.io.ask`.

        """

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

        The returned widget must produce values of type `T`. If `default` is given,
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

        """

    @abc.abstractmethod
    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        """
        Create a Json schema object based on this parser.

        The purpose of this method is to make schemas for use in IDEs, i.e. to provide
        autocompletion or simple error checking. The returned schema is not guaranteed
        to reflect all constraints added to the parser. For example, :class:`OneOf`
        and :class:`Regex` parsers will not affect the generated schema.

        :param ctx:
            context for building a schema.

        """

    @abc.abstractmethod
    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        """
        Convert given value to a representation suitable for JSON serialization.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        Call :meth:`~Parser.assert_type` to check for this case.

        """

    def __repr__(self):
        return self.__class__.__name__


class ValueParser(Parser[T], PartialParser, _t.Generic[T]):
    """
    Base implementation for a parser that returns a single value.

    Implements all method, except for :meth:`~Parser.parse`,
    :meth:`~Parser.parse_config`, :meth:`~Parser.to_json_schema`,
    and :meth:`~Parser.to_json_value`.

    :param ty:
        type of the produced value, used in :meth:`~Parser.check_type`.

    .. invisible-code-block: python

        from dataclasses import dataclass
        @dataclass
        class MyType:
            data: str

    Example:

    .. code-block:: python

        class MyTypeParser(ValueParser[MyType]):
            def __init__(self):
                super().__init__(MyType)

            def parse(self, value: str, /) -> MyType:
                return self.parse_config(value)

            def parse_config(self, value: object, /) -> MyType:
                if not isinstance(value, str):
                    raise ParsingError(f'expected a string, got {value!r}')
                return MyType(value)

            def to_json_schema(
                self, ctx: yuio.json_schema.JsonSchemaContext, /
            ) -> yuio.json_schema.JsonSchemaType:
                return yuio.json_schema.String()

            def to_json_value(
                self, value: object, /
            ) -> yuio.json_schema.JsonValue:
                assert self.assert_type(value)
                return value.data

    ::

        >>> MyTypeParser().parse('pancake')
        MyType(data='pancake')

    """

    def __init__(self, ty: type[T], /, *args, **kwargs) -> types.NoneType:
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
                    f"annotating {_t.type_repr(typehint)} with {self.__class__.__name__}"
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
        return self

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        raise RuntimeError("unable to parse multiple values")

    def supports_parse_many(self) -> bool:
        return False

    def get_nargs(self) -> _t.Literal["-", "+", "*", "?"] | int | None:
        return None

    def check_type(self, value: object) -> _t.TypeGuard[T]:
        return isinstance(value, self._value_type)

    def describe(self) -> str | None:
        return None

    def describe_or_def(self) -> str:
        return self.describe() or f"<{yuio.to_dash_case(self.__class__.__name__)}>"

    def describe_many(self) -> str | tuple[str, ...] | None:
        return self.describe()

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return self.describe_many() or f"<{yuio.to_dash_case(self.__class__.__name__)}>"

    def describe_value(self, value: object, /) -> str | None:
        assert self.assert_type(value)
        return None

    def describe_value_or_def(self, value: object, /) -> str:
        assert self.assert_type(value)
        return self.describe_value(value) or str(value) or "<empty>"

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

    if _t.TYPE_CHECKING:

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
    This is a base abstraction for :class:`Map` and :class:`Optional`.
    Forwards all calls to the inner parser, except for :meth:`~Parser.parse`,
    :meth:`~Parser.parse_many`, :meth:`~Parser.parse_config`,
    :meth:`~Parser.options`, :meth:`~Parser.check_type`,
    :meth:`~Parser.describe_value`, :meth:`~Parser.describe_value_or_def`,
    :meth:`~Parser.widget`, and :meth:`~Parser.to_json_value`.

    :param inner:
        mapped parser or :data:`None`.

    """

    if _t.TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[U], /) -> MappingParser[T, U]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: Parser[U] | None, /):
        super().__init__(inner)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        self._inner = parser
        return self

    def supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def get_nargs(self) -> _t.Literal["-", "+", "*", "?"] | int | None:
        return self._inner.get_nargs()

    def describe(self) -> str | None:
        return self._inner.describe()

    def describe_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_many(self) -> str | tuple[str, ...] | None:
        return self._inner.describe_many()

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return self._inner.describe_many_or_def()

    def completer(self) -> yuio.complete.Completer | None:
        return self._inner.completer()

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return self._inner.to_json_schema(ctx)

    def __repr__(self):
        return f"{self.__class__.__name__}({self._inner_raw!r})"

    @property
    def __wrapped_parser__(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        return self._inner_raw


class Map(MappingParser[T, U], _t.Generic[T, U]):
    """
    A wrapper that maps result of the given parser using the given function.

    Example::

        >>> # Run `Int` parser, then square the result.
        >>> int_parser = Map(Int(), lambda x: x ** 2)
        >>> int_parser.parse("8")
        64

    :param inner:
        a parser whose result will be mapped.
    :param fn:
        a function to convert a result.
    :param rev:
        a function used to un-map a value.

        This function should be present if mapping operation changes value's type
        or not idempotent. It is used in :meth:`Parser.describe_value`
        and :meth:`Parser.to_json_value` to convert parsed value back
        to its original state.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        In this case, you can raise a :class:`TypeError`.

    """

    if _t.TYPE_CHECKING:

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

        self.__fn = fn
        self.__rev = rev
        super().__init__(inner)

    def parse(self, value: str, /) -> T:
        return self.__fn(self._inner.parse(value))

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        return self.__fn(self._inner.parse_many(value))

    def parse_config(self, value: object, /) -> T:
        return self.__fn(self._inner.parse_config(value))

    def check_type(self, value: object) -> _t.TypeGuard[T]:
        if self.__rev:
            value = self.__rev(value)
        return self._inner.check_type(value)

    def describe_value(self, value: object, /) -> str | None:
        if self.__rev:
            value = self.__rev(value)
        return self._inner.describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        if self.__rev:
            value = self.__rev(value)
        return self._inner.describe_value_or_def(value)

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        options = self._inner.options()
        if options is not None:
            return [
                _t.cast(
                    yuio.widget.Option[T],
                    dataclasses.replace(option, value=self.__fn(option.value)),
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
            lambda v: self.__fn(v) if v is not yuio.MISSING else yuio.MISSING,
        )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        if self.__rev:
            value = self.__rev(value)
        return self._inner.to_json_value(value)


@_t.overload
def Lower(inner: Parser[str], /) -> Parser[str]: ...
@_t.overload
def Lower() -> PartialParser: ...


def Lower(*args) -> _t.Any:
    """
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
    """
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
    """
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
    """
    Applies :meth:`str.strip` to the result of a string parser.

    :param inner:
        a parser whose result will be mapped.

    """

    return Map(*args, str.strip)  # pyright: ignore[reportCallIssue]


@_t.overload
def Regex(
    inner: Parser[str],
    regex: str | _t.StrRePattern,
    /,
    *,
    group: int | str = 0,
) -> Parser[str]: ...
@_t.overload
def Regex(
    regex: str | _t.StrRePattern, /, *, group: int | str = 0
) -> PartialParser: ...


def Regex(*args, group: int | str = 0) -> _t.Any:
    """
    Matches the parsed string with the given regular expression.

    If regex has capturing groups, parser can return contents of a group.

    :param regex:
        regular expression for matching.
    :param group:
        mane of index of a capturing group that should be used to get the final
        parsed value.

    """

    inner: Parser[str] | None
    regex: str | _t.StrRePattern
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
            raise ParsingError(f"value should match regex '{compiled.pattern}'")
        return match.group(group)

    return Map(inner, mapper)  # type: ignore


class Apply(MappingParser[T, T], _t.Generic[T]):
    """A wrapper that applies the given function to the result of a wrapped widget.

    Example::

        >>> # Run `Int` parser, then print its output before returning.
        >>> print_output = Apply(Int(), print)
        >>> result = print_output.parse("10")
        10
        >>> result
        10

    :param inner:
        a parser used to extract and validate a value.
    :param fn:
        a function that will be called after parsing a value.

    """

    if _t.TYPE_CHECKING:

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

        self.__fn = fn
        super().__init__(inner)

    def parse(self, value: str, /) -> T:
        result = self._inner.parse(value)
        self.__fn(result)
        return result

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        result = self._inner.parse_many(value)
        self.__fn(result)
        return result

    def parse_config(self, value: object, /) -> T:
        result = self._inner.parse_config(value)
        self.__fn(result)
        return result

    def check_type(self, value: object) -> _t.TypeGuard[T]:
        return self._inner.check_type(value)

    def describe_value(self, value: object, /) -> str | None:
        return self._inner.describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        return self._inner.describe_value_or_def(value)

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
            lambda v: self.__fn(v) if v is not yuio.MISSING else None,
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

    Example:

    .. code-block:: python

        class IsLower(ValidatingParser[str]):
            def _validate(self, value: str, /):
                if not value.islower():
                    raise ParsingError('value should be lowercase')

    ::

        >>> IsLower(Str()).parse('Not lowercase!')
        Traceback (most recent call last):
        ...
        yuio.parse.ParsingError: value should be lowercase

    :param inner:
        a parser which output will be validated.

    """

    if _t.TYPE_CHECKING:

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

        Should raise :class:`ParsingError` if validation fails.

        :param value:
            value which needs validating.

        """


class Str(ValueParser[str]):
    """
    Parser for str values.

    """

    def __init__(self):
        super().__init__(str)

    def parse(self, value: str, /) -> str:
        return value

    def parse_config(self, value: object, /) -> str:
        if not isinstance(value, str):
            raise ParsingError(f"expected string, got {_t.type_repr(type(value))}")
        return value

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

    def parse(self, value: str, /) -> int:
        try:
            return int(value.strip())
        except ValueError:
            raise ParsingError(f"can't parse {value!r} as an int") from None

    def parse_config(self, value: object, /) -> int:
        if isinstance(value, float):
            if value != int(value):  # pyright: ignore[reportUnnecessaryComparison]
                raise ParsingError("expected int, got float")
            value = int(value)
        if not isinstance(value, int):
            raise ParsingError(f"expected int, got {_t.type_repr(type(value))}")
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

    def parse(self, value: str, /) -> float:
        try:
            return float(value.strip())
        except ValueError:
            raise ParsingError(f"can't parse {value!r} as a float") from None

    def parse_config(self, value: object, /) -> float:
        if not isinstance(value, (float, int)):
            raise ParsingError(f"expected float, got {_t.type_repr(type(value))}")
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

    def parse(self, value: str, /) -> bool:
        value = value.strip().lower()

        if value in ("y", "yes", "true", "1"):
            return True
        elif value in ("n", "no", "false", "0"):
            return False
        else:
            raise ParsingError(f"can't parse {value!r}, enter either 'yes' or 'no'")

    def parse_config(self, value: object, /) -> bool:
        if not isinstance(value, bool):
            raise ParsingError(f"expected bool, got {_t.type_repr(type(value))}")
        return value

    def describe(self) -> str | None:
        return "yes|no"

    def describe_value(self, value: object, /) -> str | None:
        return "yes" if value else "no"

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Choice(
            [
                yuio.complete.Option("no"),
                yuio.complete.Option("yes"),
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
    """
    Parser for enums, as defined in the standard :mod:`enum` module.

    :param enum_type:
        enum class that will be used to parse and extract values.
    :param by_name:
        if :data:`True`, the parser will use enumerator names, instead of
        their values, to match the input.
    :param doc_inline:
        inline this enum in json schema and in documentation.

    """

    if _t.TYPE_CHECKING:

        @_t.overload
        def __new__(
            cls,
            inner: type[E],
            /,
            *,
            by_name: bool = False,
            to_dash_case: bool = False,
            doc_inline: bool = False,
        ) -> Enum[E]: ...

        @_t.overload
        def __new__(
            cls,
            /,
            *,
            by_name: bool = False,
            to_dash_case: bool = False,
            doc_inline: bool = False,
        ) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(
        self,
        enum_type: type[E] | None = None,
        /,
        *,
        by_name: bool = False,
        to_dash_case: bool = False,
        doc_inline: bool = False,
    ):
        self.__by_name = by_name
        self.__to_dash_case = to_dash_case
        self.__doc_inline = doc_inline
        super().__init__(enum_type, enum_type)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        result._value_type = parser._inner  # type: ignore
        return result

    @functools.cached_property
    def __getter(self) -> _t.Callable[[E], str]:
        items = {}
        for e in self._inner:
            if self.__by_name:
                name = e.name
            else:
                name = str(e.value)
            if self.__to_dash_case:
                name = yuio.to_dash_case(name)
            items[e] = name
        return lambda e: items[e]

    def parse(self, value: str, /) -> E:
        cf_value = value.strip().casefold()

        candidates: list[E] = []
        for item in self._inner:
            if self.__getter(item) == value:
                return item
            elif (self.__getter(item)).casefold().startswith(cf_value):
                candidates.append(item)

        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            enum_values = ", ".join(self.__getter(e) for e in candidates)
            raise ParsingError(
                f"can't parse {value!r}"
                f" as {self._inner.__name__},"
                f" possible candidates are {enum_values}"
            )
        else:
            enum_values = ", ".join(self.__getter(e) for e in self._inner)
            raise ParsingError(
                f"can't parse {value!r}"
                f" as {self._inner.__name__},"
                f" should be one of {enum_values}"
            )

    def parse_config(self, value: object, /) -> E:
        if not isinstance(value, str):
            raise ParsingError(f"expected string, got {_t.type_repr(type(value))}")

        result = self.parse(value)

        if self.__getter(result) != value:
            raise ParsingError(
                f"can't parse {value!r}"
                f" as {self._inner.__name__},"
                f" did you mean {self.__getter(result)}?"
            )

        return result

    def describe_or_def(self) -> str:
        desc = "|".join(self.__getter(e) for e in self._inner)
        if len(self._inner) > 1:
            desc = f"{{{desc}}}"
        return desc

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return self.describe_or_def()

    def describe_value(self, value: object) -> str | None:
        assert self.assert_type(value)
        return super().describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        assert self.assert_type(value)
        return str(self.__getter(value))

    def options(self) -> _t.Collection[yuio.widget.Option[E]] | None:
        return [
            yuio.widget.Option(e, display_text=self.__getter(e)) for e in self._inner
        ]

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Choice(
            [yuio.complete.Option(self.__getter(e)) for e in self._inner]
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[E | yuio.Missing]:
        options: list[yuio.widget.Option[E | yuio.Missing]] = [
            yuio.widget.Option(e, self.__getter(e)) for e in self._inner
        ]

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
        if self.__doc_inline:
            return yuio.json_schema.Enum([self.__getter(e) for e in self._inner])
        else:
            return ctx.add_type(
                Enum._TyWrapper(self._inner, self.__by_name, self.__to_dash_case),
                _t.type_repr(self._inner),
                lambda: yuio.json_schema.Meta(
                    yuio.json_schema.Enum([self.__getter(e) for e in self._inner]),
                    title=self._inner.__name__,
                    description=self._inner.__doc__,
                ),
            )

    def to_json_value(self, value: object, /) -> yuio.json_schema.JsonValue:
        assert self.assert_type(value)
        return self.__getter(value)

    def __repr__(self):
        if self._inner_raw is not None:
            return f"{self.__class__.__name__}({self._inner_raw!r})"
        else:
            return self.__class__.__name__

    @dataclasses.dataclass(**yuio._with_slots(), unsafe_hash=True)
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

    def parse(self, value: str, /) -> decimal.Decimal:
        return self.parse_config(value)

    def parse_config(self, value: object, /) -> decimal.Decimal:
        if not isinstance(value, (int, float, str, decimal.Decimal)):
            raise ParsingError(
                f"expected int or float or string, got {_t.type_repr(type(value))}"
            )
        try:
            return decimal.Decimal(value)
        except (ArithmeticError, ValueError, TypeError):
            raise ParsingError(f"can't parse {value!r} as a decimal number") from None

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

    def parse(self, value: str, /) -> fractions.Fraction:
        return self.parse_config(value)

    def parse_config(self, value: object, /) -> fractions.Fraction:
        if (
            isinstance(value, (list, tuple))
            and len(value) == 2
            and all(isinstance(v, (float, int)) for v in value)
        ):
            try:
                return fractions.Fraction(*value)
            except (ValueError, ZeroDivisionError):
                raise ParsingError(
                    f"can't parse value {value[0]}/{value[1]} as a fraction"
                ) from None
        if isinstance(value, (int, float, str, decimal.Decimal, fractions.Fraction)):
            try:
                return fractions.Fraction(value)
            except (ValueError, ZeroDivisionError):
                raise ParsingError(f"can't parse {value!r} as a fraction") from None
        raise ParsingError(
            "expected int or float or fraction string "
            f"or a tuple of two ints, got {_t.type_repr(type(value))} instead"
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
    """
    A parser that tries to parse value as JSON.

    This parser will load JSON strings into python objects.
    If ``inner`` parser is given, :class:`Json` will validate parsing results
    by calling :meth:`~Parser.parse_config` on the inner parser.

    :param inner:
        a parser used to convert and validate contents of json.

    """

    if _t.TYPE_CHECKING:

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
        self._inner = parser
        return self

    def parse(self, value: str) -> T:
        try:
            config_value = json.loads(value)
        except json.JSONDecodeError as e:
            raise ParsingError(
                f"unable to decode JSON:\n" + textwrap.indent(str(e), "  ")
            ) from None
        return self.parse_config(config_value)

    def parse_config(self, value: object) -> T:
        if self._inner_raw is not None:
            return self._inner_raw.parse_config(value)
        else:
            return _t.cast(T, value)

    def check_type(self, value: object) -> _t.TypeGuard[T]:
        if self._inner_raw is not None:
            return self._inner_raw.check_type(value)
        else:
            return True  # xxx: make a better check

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
        return value

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

    def parse(self, value: str, /) -> datetime.datetime:
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            raise ParsingError(f"can't parse {value!r} as a datetime") from None

    def parse_config(self, value: object, /) -> datetime.datetime:
        if isinstance(value, datetime.datetime):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected str, got {_t.type_repr(type(value))}")

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

    def parse(self, value: str, /) -> datetime.date:
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            raise ParsingError(f"can't parse {value!r} as a date") from None

    def parse_config(self, value: object, /) -> datetime.date:
        if isinstance(value, datetime.datetime):
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected str, got {_t.type_repr(type(value))}")

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

    def parse(self, value: str, /) -> datetime.time:
        try:
            return datetime.time.fromisoformat(value)
        except ValueError:
            raise ParsingError(f"can't parse {value!r} as a time value") from None

    def parse_config(self, value: object, /) -> datetime.time:
        if isinstance(value, datetime.datetime):
            return value.time()
        elif isinstance(value, datetime.time):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected str, got {_t.type_repr(type(value))}")

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
        (?:([+-]?)\s*(\d?\d):(\d?\d)(?::(\d?\d)(?:\.(?:(\d\d\d)(\d\d\d)?))?)?)?
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

    def parse(self, value: str, /) -> datetime.timedelta:
        value = value.strip()

        if not value:
            raise ParsingError("got an empty timedelta")
        if value.endswith(","):
            raise ParsingError(
                f"can't parse {value!r} as a timedelta: trailing coma is not allowed"
            )
        if value.startswith(","):
            raise ParsingError(
                f"can't parse {value!r} as a timedelta: leading coma is not allowed"
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
            raise ParsingError(f"can't parse {value!r} as a timedelta")

        c_sign_s = -1 if c_sign_s == "-" else 1
        t_sign_s = -1 if t_sign_s == "-" else 1

        kwargs = {u: 0 for u, _ in _UNITS_MAP}

        if components_s:
            for num, unit in _COMPONENT_RE.findall(components_s):
                if unit_key := _UNITS.get(unit.lower()):
                    kwargs[unit_key] += int(num)
                else:
                    raise ParsingError(
                        f"can't parse {value!r} as a timedelta: "
                        f"unknown unit {unit!r}"
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

    def parse_config(self, value: object, /) -> datetime.timedelta:
        if isinstance(value, datetime.timedelta):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected str, got {_t.type_repr(type(value))}")

    def to_json_schema(
        self, ctx: yuio.json_schema.JsonSchemaContext, /
    ) -> yuio.json_schema.JsonSchemaType:
        return ctx.add_type(
            datetime.date,
            "TimeDelta",
            lambda: yuio.json_schema.Meta(
                yuio.json_schema.String(
                    # save yourself some trouble, paste this into https://regexper.com/
                    pattern=(
                        r"^(([+-]?\s*(\d+\s*(d|day|days|s|sec|secs|second|seconds"
                        r"|us|u|micro|micros|microsecond|microseconds|ms|l|milli|"
                        r"millis|millisecond|milliseconds|m|min|mins|minute|minutes"
                        r"|h|hr|hrs|hour|hours|w|week|weeks)\s*)+)(,\s*)?"
                        r"([+-]?\s*\d?\d:\d?\d(:\d?\d(\.\d\d\d(\d\d\d)?)?)?)"
                        r"|([+-]?\s*\d?\d:\d?\d(:\d?\d(\.\d\d\d(\d\d\d)?)?)?)"
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
        self.__extensions = [extensions] if isinstance(extensions, str) else extensions
        super().__init__(pathlib.Path)

    def parse(self, value: str, /) -> pathlib.Path:
        path = pathlib.Path(value).expanduser().resolve().absolute()
        self._validate(path)
        return path

    def parse_config(self, value: object, /) -> pathlib.Path:
        if not isinstance(value, str):
            raise ParsingError(f"expected string, got {_t.type_repr(type(value))}")
        return self.parse(value)

    def describe(self) -> str | None:
        if self.__extensions is not None:
            desc = "|".join(f"<*{e}>" for e in self.__extensions)
            if len(self.__extensions) > 1:
                desc = f"{{{desc}}}"
            return desc
        else:
            return None

    def _validate(self, value: pathlib.Path, /):
        if self.__extensions is not None:
            if not any(value.name.endswith(ext) for ext in self.__extensions):
                exts = ", ".join(self.__extensions)
                raise ParsingError(f"{value} should have extension {exts}")

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.File(extensions=self.__extensions)

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

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if value.exists():
            raise ParsingError(f"{value} already exists")


class ExistingPath(Path):
    """
    Parse a file system path and verify that it exists.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.exists():
            raise ParsingError(f"{value} doesn't exist")


class File(ExistingPath):
    """
    Parse a file system path and verify that it points to a regular file.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_file():
            raise ParsingError(f"{value} is not a file")


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
            raise ParsingError(f"{value} is not a directory")

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
            raise ParsingError(f"{value} is not a git repository")


class CollectionParser(
    WrappingParser[C, Parser[T]], ValueParser[C], PartialParser, _t.Generic[C, T]
):
    """
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
        and its ``iter`` is :meth:`dict.items`.
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

    .. code-block::

        from typing import Iterable, Generic

        class DoubleList(CollectionParser[list[T], T], Generic[T]):
            def __init__(self, inner: Parser[T], /, *, delimiter: str | None = None):
                super().__init__(inner, ty=list, ctor=self._ctor, delimiter=delimiter)

            @staticmethod
            def _ctor(values: Iterable[T]) -> list[T]:
                return [x for value in values for x in [value, value]]

            def to_json_schema(self, ctx: yuio.json_schema.JsonSchemaContext, /) -> yuio.json_schema.JsonSchemaType:
                return {"type": "array", "items": self._inner.to_json_schema(ctx)}

    """

    #: If set to :data:`False`, autocompletion will not suggest item duplicates.
    _allow_completing_duplicates: _t.ClassVar[bool] = True

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
        #: See class parameters for more details.
        self._ctor = ctor
        #: See class parameters for more details.
        self._iter = iter
        #: See class parameters for more details.
        self._config_type = config_type
        #: See class parameters for more details.
        self._config_type_iter = config_type_iter
        #: See class parameters for more details.
        self._delimiter = delimiter

        super().__init__(inner, ty)

    def wrap(self: P, parser: Parser[_t.Any]) -> P:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        return result

    def parse(self, value: str, /) -> C:
        return self.parse_many(value.split(self._delimiter))

    def parse_many(self, value: _t.Sequence[str], /) -> C:
        return self._ctor(self._inner.parse(item) for item in value)

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: object, /) -> C:
        if not isinstance(value, self._config_type):
            if isinstance(self._config_type, tuple):
                expected = " or ".join(ty.__name__ for ty in self._config_type)
            else:
                expected = self._config_type.__name__
            raise ParsingError(f"expected {expected}, got {_t.type_repr(type(value))}")

        return self._ctor(
            self._inner.parse_config(item) for item in self._config_type_iter(value)
        )

    def get_nargs(self) -> _t.Literal["-", "+", "*", "?"] | int | None:
        return "*"

    def describe(self) -> str | None:
        return self.describe_or_def()

    def describe_or_def(self) -> str:
        delimiter = self._delimiter or " "
        value = self._inner.describe_or_def()

        return f"{value}[{delimiter}{value}[{delimiter}...]]"

    def describe_many(self) -> str | tuple[str, ...] | None:
        return self._inner.describe()

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return self._inner.describe_or_def()

    def describe_value(self, value: object, /) -> str | None:
        return self.describe_value_or_def(value)

    def describe_value_or_def(self, value: object, /) -> str:
        assert self.assert_type(value)

        return (self._delimiter or " ").join(
            self._inner.describe_value_or_def(item) for item in self._iter(value)
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

    def __repr__(self):
        if self._inner_raw is not None:
            return f"{self.__class__.__name__}({self._inner_raw!r})"
        else:
            return self.__class__.__name__


class List(CollectionParser[list[T], T], _t.Generic[T]):
    """Parser for lists.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse list items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    if _t.TYPE_CHECKING:

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
    """Parser for sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    if _t.TYPE_CHECKING:

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
    """Parser for frozen sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    if _t.TYPE_CHECKING:

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
    """Parser for dicts.

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

    if _t.TYPE_CHECKING:

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
        self.__pair_delimiter = pair_delimiter
        super().__init__(
            Tuple(key, value, delimiter=pair_delimiter) if key and value else None,
            ty=dict,
            ctor=dict,
            iter=dict.items,
            config_type=(dict, list),
            config_type_iter=self.__config_type_iter,
            delimiter=delimiter,
        )

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        setattr(result._inner, "_Tuple__delimiter", self.__pair_delimiter)
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
    """Parser for tuples of fixed lengths.

    :param parsers:
        parsers for each tuple element.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    # Shitty hack to allow type inference in older pythons.
    if _t.TYPE_CHECKING:
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
        self.__delimiter = delimiter
        super().__init__(parsers or None, tuple)

    def wrap(self, parser: Parser[_t.Any]) -> Parser[_t.Any]:
        result = super().wrap(parser)
        result._inner = parser._inner  # type: ignore
        return result

    def parse(self, value: str, /) -> TU:
        items = value.split(self.__delimiter, maxsplit=len(self._inner) - 1)
        return self.parse_many(items)

    def parse_many(self, value: _t.Sequence[str], /) -> TU:
        if len(value) != len(self._inner):
            raise ParsingError(
                f"expected {len(self._inner)} element{'' if len(self._inner) == 1 else 's'}"
            )

        return _t.cast(
            TU,
            tuple(parser.parse(item) for parser, item in zip(self._inner, value)),
        )

    def parse_config(self, value: object, /) -> TU:
        if not isinstance(value, (list, tuple)):
            raise ParsingError(
                f"expected list or tuple, got {_t.type_repr(type(value))}"
            )
        elif len(value) != len(self._inner):
            raise ParsingError(
                f"expected {len(self._inner)} element{'' if len(self._inner) == 1 else 's'}"
            )

        return _t.cast(
            TU,
            tuple(
                parser.parse_config(item) for parser, item in zip(self._inner, value)
            ),
        )

    def supports_parse_many(self) -> bool:
        return True

    def get_nargs(self) -> _t.Literal["-", "+", "*", "?"] | int | None:
        return len(self._inner)

    def describe(self) -> str | None:
        return self.describe_or_def()

    def describe_or_def(self) -> str:
        delimiter = self.__delimiter or " "
        desc = [parser.describe_or_def() for parser in self._inner]
        return delimiter.join(desc)

    def describe_many(self) -> str | tuple[str, ...] | None:
        return self.describe_many_or_def()

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return tuple(parser.describe_or_def() for parser in self._inner)

    def describe_value(self, value: object, /) -> str | None:
        return self.describe_value_or_def(value)

    def describe_value_or_def(self, value: object, /) -> str:
        assert self.assert_type(value)

        delimiter = self.__delimiter or " "
        desc = [
            parser.describe_value_or_def(item)
            for parser, item in zip(self._inner, value)
        ]

        return delimiter.join(desc)

    def options(self) -> _t.Collection[yuio.widget.Option[TU]] | None:
        return None

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Tuple(
            *[parser.completer() or yuio.complete.Empty() for parser in self._inner],
            delimiter=self.__delimiter,
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

    def __repr__(self):
        return f"{self.__class__.__name__}{self._inner_raw!r}"


class Optional(MappingParser[T | None, T], _t.Generic[T]):
    """
    Parser for optional values.

    Allows handling :data:`None`\\ s when parsing config. Does not change how strings
    are parsed, though.

    :param inner:
        a parser used to extract and validate contents of an optional.

    """

    if _t.TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], /) -> Optional[T]: ...

        @_t.overload
        def __new__(cls, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, inner: Parser[T] | None = None, /):
        super().__init__(inner)

    def parse(self, value: str, /) -> T | None:
        return self._inner.parse(value)

    def parse_many(self, value: _t.Sequence[str], /) -> T | None:
        return self._inner.parse_many(value)

    def parse_config(self, value: object, /) -> T | None:
        if value is None:
            return None
        return self._inner.parse_config(value)

    def check_type(self, value: object) -> _t.TypeGuard[T | None]:
        if value is None:
            return True
        return self._inner.check_type(value)

    def describe_value(self, value: object, /) -> str | None:
        if value is None:
            return "<none>"
        return self._inner.describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        if value is None:
            return "<none>"
        return self._inner.describe_value_or_def(value)

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
    """
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

    # Shitty hack to allow type inference in older pythons.
    if _t.TYPE_CHECKING:
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

    def parse(self, value: str, /) -> T:
        errors = []
        for parser in self._inner:
            try:
                return parser.parse(value)
            except ParsingError as e:
                errors.append((parser, e))
        raise ParsingError(
            "\n".join(
                f"trying as {parser.describe_or_def()}:\n"
                + textwrap.indent(str(e), "  ")
                for parser, e in errors
            )
        )

    def parse_config(self, value: object, /) -> T:
        errors = []
        for parser in self._inner:
            try:
                return parser.parse_config(value)
            except ParsingError as e:
                errors.append((parser, e))
        raise ParsingError(
            "\n".join(
                f"trying as {parser.describe_or_def()}:\n"
                + textwrap.indent(str(e), "  ")
                for parser, e in errors
            )
        )

    def check_type(self, value: object) -> _t.TypeGuard[T]:
        return any(parser.check_type(value) for parser in self._inner)

    def describe(self) -> str | None:
        return self.describe_or_def()

    def describe_or_def(self) -> str:
        desc = f"|".join(parser.describe_or_def() for parser in self._inner)
        if len(self._inner) > 1:
            desc = f"{{{desc}}}"
        return desc

    def describe_value(self, value: object) -> str | None:
        for parser in self._inner:
            try:
                return parser.describe_value(value)
            except TypeError:
                pass

        raise TypeError(
            f"parser {self} can't handle value of type {_t.type_repr(type(value))}"
        )

    def describe_value_or_def(self, value: object) -> str:
        for parser in self._inner:
            try:
                return parser.describe_value_or_def(value)
            except TypeError:
                pass

        raise TypeError(
            f"parser {self} can't handle value of type {_t.type_repr(type(value))}"
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
                completers.append((parser.describe_or_def(), completer))
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
            f"parser {self} can't handle value of type {_t.type_repr(type(value))}"
        )

    def __repr__(self):
        return f"{self.__class__.__name__}{self._inner_raw!r}"


class _BoundImpl(ValidatingParser[T], _t.Generic[T, Cmp]):
    _Self = _t.TypeVar("_Self", bound="_BoundImpl[_t.Any, _t.Any]")

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
                    f"{self.__desc} should be greater or equal to {self._lower_bound},"
                    f" got {value} instead"
                )
            elif not self._lower_bound_is_inclusive and not self._lower_bound < mapped:
                raise ParsingError(
                    f"{self.__desc} should be greater than {self._lower_bound},"
                    f" got {value} instead"
                )

        if self._upper_bound is not None:
            if self._upper_bound_is_inclusive and self._upper_bound < mapped:
                raise ParsingError(
                    f"{self.__desc} should be lesser or equal to {self._upper_bound},"
                    f" got {value} instead"
                )
            elif not self._upper_bound_is_inclusive and not mapped < self._upper_bound:
                raise ParsingError(
                    f"{self.__desc} should be lesser than {self._upper_bound},"
                    f" got {value} instead"
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
    """
    Check that value is upper- or lower-bound by some constraints.

    Example::

        >>> # Int in range `0 < x <= 1`:
        >>> Bound(Int(), lower=0, upper_inclusive=1)
        Bound(Int, 0 < x <= 1)

    :param inner:
        parser whose result will be validated.
    :param lower:
        set lower bound for value, so we require that ``value > lower``.
        Can't be given if ``lower_inclusive`` is also given.
    :param lower_inclusive:
        set lower bound for value, so we require that ``value >= lower``.
        Can't be given if ``lower`` is also given.
    :param upper:
        set upper bound for value, so we require that ``value < upper``.
        Can't be given if ``upper_inclusive`` is also given.
    :param upper_inclusive:
        set upper bound for value, so we require that ``value <= upper``.
        Can't be given if ``upper`` is also given.

    """

    if _t.TYPE_CHECKING:

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
            desc="value",
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
def Gt(bound: yuio.SupportsLt[_t.Any], /) -> PartialParser: ...


def Gt(*args) -> _t.Any:
    """
    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.

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
def Ge(bound: yuio.SupportsLt[_t.Any], /) -> PartialParser: ...


def Ge(*args) -> _t.Any:
    """
    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.

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
def Lt(bound: yuio.SupportsLt[_t.Any], /) -> PartialParser: ...


def Lt(*args) -> _t.Any:
    """
    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.

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
def Le(bound: yuio.SupportsLt[_t.Any], /) -> PartialParser: ...


def Le(*args) -> _t.Any:
    """
    Alias for :class:`Bound`.

    :param inner:
        parser whose result will be validated.

    """

    if len(args) == 1:
        return Bound(upper_inclusive=args[0])
    elif len(args) == 2:
        return Bound(args[0], upper_inclusive=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


class LenBound(_BoundImpl[Sz, int], _t.Generic[Sz]):
    """Check that length of a value is upper- or lower-bound by some constraints.

    The signature is the same as of the :class:`Bound` class.

    Example::

        >>> # List of up to five ints:
        >>> LenBound(List(Int()), upper_inclusive=5)
        LenBound(List(Int), len <= 5)

    :param inner:
        parser whose result will be validated.
    :param lower:
        set lower bound for value's length, so we require that ``len(value) > lower``.
        Can't be given if ``lower_inclusive`` is also given.
    :param lower_inclusive:
        set lower bound for value's length, so we require that ``len(value) >= lower``.
        Can't be given if ``lower`` is also given.
    :param upper:
        set upper bound for value's length, so we require that ``len(value) < upper``.
        Can't be given if ``upper_inclusive`` is also given.
    :param upper_inclusive:
        set upper bound for value's length, so we require that ``len(value) <= upper``.
        Can't be given if ``upper`` is also given.

    """

    if _t.TYPE_CHECKING:

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
            desc="length of a value",
        )

    def get_nargs(self) -> _t.Literal["-", "+", "*", "?"] | int | None:
        if not self._inner.supports_parse_many():
            # somebody bound len of a string?
            return self._inner.get_nargs()

        lower = self._lower_bound
        if lower is not None and not self._lower_bound_is_inclusive:
            lower += 1
        upper = self._upper_bound
        if upper is not None and not self._upper_bound_is_inclusive:
            upper -= 1

        if lower == upper:
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
    """
    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.

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
    """
    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.

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
    """
    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.

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
    """
    Alias for :class:`LenBound`.

    :param inner:
        parser whose result will be validated.

    """

    if len(args) == 1:
        return LenBound(upper_inclusive=args[0])
    elif len(args) == 2:
        return LenBound(args[0], upper_inclusive=args[1])
    else:
        raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")


class OneOf(ValidatingParser[T], _t.Generic[T]):
    """
    Check that the parsed value is one of the given set of values.

    Example::

        >>> # Accepts only strings 'A', 'B', or 'C':
        >>> OneOf(Str(), ['A', 'B', 'C'])
        OneOf(Str)

    :param inner:
        parser whose result will be validated.
    :param values:
        collection of allowed values.

    """

    if _t.TYPE_CHECKING:

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

        self.__allowed_values = values

    def _validate(self, value: T, /):
        if value not in self.__allowed_values:
            values = ", ".join(map(repr, self.__allowed_values))
            raise ParsingError(f"can't parse {value!r}, should be one of {values}")

    def describe(self) -> str | None:
        desc = "|".join(self.describe_value_or_def(e) for e in self.__allowed_values)
        if len(desc) < 80:
            if len(self.__allowed_values) > 1:
                desc = f"{{{desc}}}"
            return desc
        else:
            return super().describe()

    def describe_or_def(self) -> str:
        return self.describe() or super().describe_or_def()

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        return [
            yuio.widget.Option(e, self.describe_value_or_def(e))
            for e in self.__allowed_values
        ]

    def completer(self) -> yuio.complete.Completer | None:
        return yuio.complete.Choice(
            [
                yuio.complete.Option(self.describe_value_or_def(e))
                for e in self.__allowed_values
            ]
        )

    def widget(
        self,
        default: object | yuio.Missing,
        input_description: str | None,
        default_description: str | None,
        /,
    ) -> yuio.widget.Widget[T | yuio.Missing]:
        allowed_values = list(self.__allowed_values)

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


class WithDesc(MappingParser[T, T], _t.Generic[T]):
    """
    Overrides inline help messages of a wrapped parser.

    Inline help messages will show up as hints in autocompletion and widgets.

    :param inner:
        inner parser.
    :param desc:
        description override.

    """

    if _t.TYPE_CHECKING:

        @_t.overload
        def __new__(cls, inner: Parser[T], desc: str, /) -> MappingParser[T, T]: ...

        @_t.overload
        def __new__(cls, desc: str, /) -> PartialParser: ...

        def __new__(cls, *args, **kwargs) -> _t.Any: ...

    def __init__(self, *args):
        inner: Parser[T] | None
        desc: str
        if len(args) == 1:
            inner, desc = None, args[0]
        elif len(args) == 2:
            inner, desc = args
        else:
            raise TypeError(f"expected 1 or 2 positional arguments, got {len(args)}")

        self.__desc = desc
        super().__init__(inner)

    def check_type(self, value: object) -> _t.TypeGuard[T]:
        return self._inner.check_type(value)

    def describe(self) -> str | None:
        return self.__desc or self._inner.describe()

    def describe_or_def(self) -> str:
        return self.__desc or self._inner.describe_or_def()

    def describe_many(self) -> str | tuple[str, ...] | None:
        return self.__desc or self._inner.describe_many()

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return self.__desc or self._inner.describe_many_or_def()

    def describe_value(self, value: object) -> str | None:
        return self._inner.describe_value(value)

    def describe_value_or_def(self, value: object) -> str:
        return self._inner.describe_value_or_def(value)

    def parse(self, value: str, /) -> T:
        return self._inner.parse(value)

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        return self._inner.parse_many(value)

    def parse_config(self, value: object, /) -> T:
        return self._inner.parse_config(value)

    def options(self) -> _t.Collection[yuio.widget.Option[T]] | None:
        return self._inner.options()

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
            raise ParsingError("input is required")
        else:
            return self._parser.parse(s)

    @property
    def help_data(self):
        return super().help_data.with_action(
            group="Input Format",
            msg=self._input_description,
            prepend=True,
            prepend_group=True,
        )


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
    """
    Create parser from a type hint.

    Example::

        >>> from_type_hint(list[int] | None)
        Optional(List(Int))

    :param ty:
        A type hint.

        This type hint should not contain strings or forward references. Make sure
        they're resolved before passing it to this function.

    """

    result = _from_type_hint(ty)
    setattr(result, "_Parser__typehint", ty)
    return result


def _from_type_hint(ty: _t.Any, /) -> Parser[object]:
    if isinstance(ty, str) or isinstance(ty, _t.ForwardRef):
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

    if _t.is_union(origin):
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
        raise TypeError(f"unsupported type {_t.type_repr(ty)}")


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

    If ``uses_delim`` is :data:`True`, callback can use
    :func:`suggest_delim_for_type_hint_conversion`.

    This function can be used as a decorator.

    .. invisible-code-block: python

        class MyType: ...
        class MyTypeParser(ValueParser[MyType]):
            def __init__(self): super().__init__(MyType)
            def parse(self, value: str, /): ...
            def parse_config(self, value, /): ...
            def to_json_schema(self, ctx, /): ...
            def to_json_value(self, value, /): ...

    Example:

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

    :param cb:
        a function that should inspect a type hint and possibly return a parser.
    :param uses_delim:
        indicates that callback will use
        :func:`suggest_delim_for_type_hint_conversion`.

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

    Example:

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
        >>> parser._delimiter is None
        True
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


def _str_ty_union_parser(ty, origin, args, target, parser):
    if ty is target:
        return parser()
    is_union = _t.is_union(origin)
    is_optional = is_union and types.NoneType in args
    if len(args) == 2 + is_optional and str in args and target in args:
        if is_optional:
            return Optional(parser())
        else:
            return parser()


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
    lambda ty, origin, args: _str_ty_union_parser(ty, origin, args, pathlib.Path, Path)
)
register_type_hint_conversion(
    lambda ty, origin, args: (Json() if ty is yuio.json_schema.JsonValue else None)
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
