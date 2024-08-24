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
    >>> ident = Str().regex(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

    >>> # Parses a non-empty list of strings.
    >>> idents = List(ident).len_ge(1)

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


Building a parser
-----------------

:class:`Parser` includes several convenience methods that make
building complex verification easier.

.. class:: Parser
   :noindex:

   .. automethod:: bound

   .. automethod:: gt

   .. automethod:: ge

   .. automethod:: lt

   .. automethod:: le

   .. automethod:: len_bound

   .. automethod:: len_between

   .. automethod:: len_gt

   .. automethod:: len_ge

   .. automethod:: len_lt

   .. automethod:: len_le

   .. automethod:: len_eq

   .. automethod:: one_of


Value parsers
-------------

.. autoclass:: Str

   .. automethod:: lower

   .. automethod:: upper

   .. automethod:: strip

   .. automethod:: lstrip

   .. automethod:: rstrip

   .. automethod:: regex

.. autoclass:: Int

.. autoclass:: Float

.. autoclass:: Bool

.. autoclass:: Enum

.. autoclass:: Decimal

.. autoclass:: Fraction

.. autoclass:: List

.. autoclass:: Set

.. autoclass:: FrozenSet

.. autoclass:: Dict

.. autoclass:: Tuple(*parsers: Parser[...], delimiter: typing.Optional[str] = None)


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

.. autoclass:: Bound

.. autoclass:: LenBound

.. autoclass:: OneOf


Functional parsers
------------------

.. autoclass:: Map

.. autoclass:: Apply


Deriving parsers from type hints
--------------------------------

There is a way to automatically derive basic parsers from type hints
(used by :mod:`yuio.config`):

.. autofunction:: from_type_hint

To extend capabilities of the automatic converter,
you can register your own types and parsers:

.. autofunction:: register_type_hint_conversion

When implementing a callback, you might need to specify a delimiter
for a collection parser. Use :func:`suggest_delim_for_type_hint_conversion`:

.. autofunction:: suggest_delim_for_type_hint_conversion


Other parser methods
--------------------

:class:`Parser` defines some more methods and attributes.
You don't usually need because Yuio handles everything they do itself.
However, you can still use them in case you need to.

.. autoclass:: Parser
   :noindex:

   .. autoattribute:: __wrapped_parser__

   .. automethod:: get_nargs

   .. automethod:: describe

   .. automethod:: describe_or_def

   .. automethod:: describe_many

   .. automethod:: describe_many_or_def

   .. automethod:: describe_value

   .. automethod:: describe_value_or_def

   .. automethod:: completer

   .. automethod:: widget


Building your own parser
------------------------

To implement your parser, you can subclass :class:`Parser`
and implement all abstract methods yourself.

We, however, recommend using the following classes
to speed up the process and avoid common bugs:

.. autoclass:: ValueParser

.. autoclass:: ValidatingParser

  .. autoattribute:: __wrapped_parser__
     :noindex:

  .. automethod:: _validate

.. autoclass:: CollectionParser

   .. autoattribute:: _allow_completing_duplicates

"""

import abc
import argparse
import datetime
import decimal
import enum
import fractions
import pathlib
import re
import threading
from yuio import _t

import yuio
import yuio.complete
import yuio.widget

T = _t.TypeVar("T")
U = _t.TypeVar("U")
T_co = _t.TypeVar("T_co", covariant=True)
K = _t.TypeVar("K")
V = _t.TypeVar("V")
C = _t.TypeVar("C", bound=_t.Collection[object])
C2 = _t.TypeVar("C2", bound=_t.Collection[object])
Sz = _t.TypeVar("Sz", bound=_t.Sized)
Cmp = _t.TypeVar("Cmp", bound=yuio.SupportsLt[_t.Any])
E = _t.TypeVar("E", bound=enum.Enum)
TU = _t.TypeVar("TU", bound=_t.Tuple[object, ...])


class ParsingError(ValueError, argparse.ArgumentTypeError):
    """Raised when parsing or validation fails.

    This exception is derived from both :class:`ValueError`
    and :class:`argparse.ArgumentTypeError` to ensure that error messages
    are displayed nicely with argparse, and handled correctly in other places.

    """


class Parser(_t.Generic[T_co], abc.ABC):
    """Base class for parsers.

    """

    #: An attribute for unwrapping parsers that validate or map results
    #: of other parsers.
    __wrapped_parser__: _t.Optional["Parser[object]"] = None

    @abc.abstractmethod
    def parse(self, value: str, /) -> T_co:
        """Parse user input, raise :class:`ParsingError` on failure."""

    @abc.abstractmethod
    def parse_many(self, value: _t.Sequence[str], /) -> T_co:
        """For collection parsers, parse and validate collection
        by parsing its items one-by-one.

        Example:

        >>> # Let's say we're parsing a set of ints.
        >>> parser = Set(Int())
        >>>
        >>> # And the user enters collection items one-by-one.
        >>> user_input = ['1', '2', '3']
        >>>
        >>> # We can parse collection from its items:
        >>> parser.parse_many(user_input)
        {1, 2, 3}

        """

    @abc.abstractmethod
    def supports_parse_many(self) -> bool:
        """Return true if this parser returns a collection
        and so supports :meth:`~Parser.parse_many`.

        """

    @abc.abstractmethod
    def parse_config(self, value: object, /) -> T_co:
        """Parse value from a config, raise :class:`ParsingError` on failure.

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

        """

    @abc.abstractmethod
    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        """Generate `nargs` for argparse."""

    @abc.abstractmethod
    def describe(self) -> _t.Optional[str]:
        """Return a human-readable description of an expected input."""

    @abc.abstractmethod
    def describe_or_def(self) -> str:
        """Like :py:meth:`~Parser.describe`, but guaranteed to return something."""

    @abc.abstractmethod
    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        """Return a human-readable description of a container element.

        Used with :meth:`~Parser.parse_many`.

        """

    @abc.abstractmethod
    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        """Like :py:meth:`~Parser.describe_many`, but guaranteed to return something."""

    @abc.abstractmethod
    def describe_value(self, value: object, /) -> _t.Optional[str]:
        """Return a human-readable description of the given value.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        In this case, you can return :data:`None`.

        """

    @abc.abstractmethod
    def describe_value_or_def(self, value: object, /) -> str:
        """Like :py:meth:`~Parser.describe_value`, but guaranteed to return something.

        Note that, since parser's type parameter is covariant, this function is not
        guaranteed to receive a value of the same type that this parser produces.
        In this case, you can return ``str(value) or "<empty>"``.

        """

    @abc.abstractmethod
    def completer(self) -> yuio.complete.Completer:
        """Return a completer for values of this parser.

        This function is used when assembling autocompletion functions for shells,
        and when reading values from user via :func:`yuio.io.ask`.

        """

    @abc.abstractmethod
    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[T_co, yuio.Missing]]:
        """Return a widget for reading values of this parser.

        This function is used when reading values from user via :func:`yuio.io.ask`.

        The returned widget must produce values of type `T`. If `default` is given,
        and the user input is empty (or, in case of `choice` widgets, if the user
        chooses the default), the widget must produce
        the :data:`~yuio.MISSING` constant (*not* the default constant).

        Validating parsers must wrap the widget they got from
        :func:`__wrapped_parser__` into :class:`~yuio.widget.Map`
        or :class:`~yuio.widget.Apply` in order to validate widget's results.

        """

    def bound(
        self: "Parser[Cmp]",
        *,
        lower: _t.Optional[Cmp] = None,
        lower_inclusive: _t.Optional[Cmp] = None,
        upper: _t.Optional[Cmp] = None,
        upper_inclusive: _t.Optional[Cmp] = None,
    ) -> "Bound[Cmp]":
        """Check that value is upper- or lower-bound by some constraints.

        Example::

            >>> # Int in range `0 < x <= 1`:
            >>> Int().bound(lower=0, upper_inclusive=1)
            Bound(Int, 0 < x <= 1)

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

        """

        return Bound(
            self,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
        )

    def gt(self: "Parser[Cmp]", bound: Cmp, /) -> "Bound[Cmp]":
        """Check that value is greater than the given bound.

        See :meth:`~Parser.bound` for more info.

        """

        return self.bound(lower=bound)

    def ge(self: "Parser[Cmp]", bound: Cmp, /) -> "Bound[Cmp]":
        """Check that value is greater than or equal to the given bound.

        See :meth:`~Parser.bound` for more info.

        """

        return self.bound(lower_inclusive=bound)

    def lt(self: "Parser[Cmp]", bound: Cmp, /) -> "Bound[Cmp]":
        """Check that value is lesser than the given bound.

        See :meth:`~Parser.bound` for more info.

        """

        return self.bound(upper=bound)

    def le(self: "Parser[Cmp]", bound: Cmp, /) -> "Bound[Cmp]":
        """Check that value is lesser than or equal to the given bound.

        See :meth:`~Parser.bound` for more info.

        """

        return self.bound(upper_inclusive=bound)

    def len_bound(
        self: "Parser[Sz]",
        *,
        lower: _t.Optional[int] = None,
        lower_inclusive: _t.Optional[int] = None,
        upper: _t.Optional[int] = None,
        upper_inclusive: _t.Optional[int] = None,
    ) -> "LenBound[Sz]":
        """Check that length of a value is upper- or lower-bound by some constraints.

        The signature is the same as of the :meth:`~Parser.bound` method.

        Example::

            >>> # List of up to five ints:
            >>> List(Int()).len_bound(upper_inclusive=5)
            LenBound(List(Int), len <= 5)

        """

        return LenBound(
            self,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
        )

    @_t.overload
    def len_between(self: "Parser[Sz]", upper: int, /) -> "LenBound[Sz]":
        ...

    @_t.overload
    def len_between(self: "Parser[Sz]", lower: int, upper: int, /) -> "LenBound[Sz]":
        ...

    def len_between(self: "Parser[Sz]", *args: int) -> "LenBound[Sz]":
        """Check that length of the value is within the given range.

        Example::

            >>> # List of up to five ints:
            >>> List(Int()).len_between(6)
            LenBound(List(Int), len < 6)

            >>> # List of one, two, or three ints:
            >>> List(Int()).len_between(1, 4)
            LenBound(List(Int), 1 <= len < 4)

        See :meth:`~Parser.len_bound` for more info.

        :param lower:
            lower length bound, inclusive.
        :param upper:
            upper length bound, not inclusive.

        """

        if len(args) == 1:
            lower, upper = None, args[0]
        elif len(args) == 2:
            lower, upper = args
        else:
            raise TypeError(f"len_between() takes 1 or 2 arguments ({len(args)} given)")
        return self.len_bound(lower_inclusive=lower, upper=upper)

    def len_gt(self: "Parser[Sz]", bound: int, /) -> "LenBound[Sz]":
        """Check that length of the value is greater than the given bound.

        See :meth:`~Parser.len_bound` for more info.

        """

        return self.len_bound(lower=bound)

    def len_ge(self: "Parser[Sz]", bound: int, /) -> "LenBound[Sz]":
        """Check that length of the value is greater than or equal to the given bound.

        See :meth:`~Parser.len_bound` for more info.

        """

        return self.len_bound(lower_inclusive=bound)

    def len_lt(self: "Parser[Sz]", bound: int, /) -> "LenBound[Sz]":
        """Check that length of the value is lesser than the given bound.

        See :meth:`~Parser.len_bound` for more info.

        """

        return self.len_bound(upper=bound)

    def len_le(self: "Parser[Sz]", bound: int, /) -> "LenBound[Sz]":
        """Check that length of the value is lesser than or equal to the given bound.

        See :meth:`~Parser.len_bound` for more info.

        """

        return self.len_bound(upper_inclusive=bound)

    def len_eq(self: "Parser[Sz]", bound: int, /) -> "LenBound[Sz]":
        """Check that length of the value is equal to the given bound.

        See :meth:`~Parser.len_bound` for more info.

        """

        return self.len_bound(lower_inclusive=bound, upper_inclusive=bound)

    def one_of(self: "Parser[T]", values: _t.Collection[T], /) -> "OneOf[T]":
        """Check that the parsed value is one of the given set of values.

        Example::

            >>> # Accepts only strings 'A', 'B', or 'C':
            >>> Str().one_of(['A', 'B', 'C'])
            OneOf(Str)

        """

        return OneOf(self, values)

    def __repr__(self):
        return self.__class__.__name__


class ValueParser(Parser[T], _t.Generic[T]):
    """Base implementation for a parser that returns a single value.

    Implements all method, except for :meth:`~Parser.parse`
    and :meth:`~Parser.parse_config`.

    ..
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class MyType:
        ...     value: int

    Example::

        >>> class MyTypeParser(ValueParser[MyType]):
        ...     def parse(self, value: str, /) -> MyType:
        ...         return self.parse_config(value)
        ...
        ...     def parse_config(self, value: object, /) -> MyType:
        ...         if not isinstance(value, str):
        ...             raise ParsingError(f'expected a string, got {value!r}')
        ...         return MyType(value)

        >>> MyTypeParser().parse('data')
        MyType(value='data')

    """

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        raise RuntimeError("unable to parse multiple values")

    def supports_parse_many(self) -> bool:
        return False

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        return None

    def describe(self) -> _t.Optional[str]:
        return None

    def describe_or_def(self) -> str:
        return self.describe() or yuio.to_dash_case(self.__class__.__name__)

    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        return self.describe()

    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        return self.describe_many() or yuio.to_dash_case(self.__class__.__name__)

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        return None

    def describe_value_or_def(self, value: object, /) -> str:
        return self.describe_value(value) or str(value) or "<empty>"

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.Empty()

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[T, yuio.Missing]]:
        completer = self.completer()
        return _map_widget_result(
            self,
            default,
            yuio.widget.InputWithCompletion(
                completer,
                placeholder=f" default: {default_description}"
                if default_description
                else "",
            ),
        )


class ValidatingParser(Parser[T], _t.Generic[T]):
    """Base implementation for a parser that validates result of another parser.

    This class wraps another parser and passes all method calls to it.
    All parsed values are additionally passed to :meth:`~ValidatingParser._validate`.

    Example::

        >>> class IsLower(ValidatingParser[str]):
        ...     def _validate(self, value: str, /):
        ...         if not value.islower():
        ...             raise ParsingError('value should be lowercase')

        >>> IsLower(Str()).parse('Not lowercase!')
        Traceback (most recent call last):
        ...
        yuio.parse.ParsingError: value should be lowercase

    """

    def __init__(self, inner: Parser[T]):
        self.__wrapped_parser__: Parser[T] = inner  # type: ignore

    def parse(self, value: str, /) -> T:
        parsed = self.__wrapped_parser__.parse(value)
        self._validate(parsed)
        return parsed

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        parsed = self.__wrapped_parser__.parse_many(value)
        self._validate(parsed)
        return parsed

    def supports_parse_many(self) -> bool:
        return self.__wrapped_parser__.supports_parse_many()

    def parse_config(self, value: object, /) -> T:
        parsed = self.__wrapped_parser__.parse_config(value)
        self._validate(parsed)
        return parsed

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        return self.__wrapped_parser__.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self.__wrapped_parser__.describe()

    def describe_or_def(self) -> str:
        return self.__wrapped_parser__.describe_or_def()

    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        return self.__wrapped_parser__.describe_many()

    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        return self.__wrapped_parser__.describe_many_or_def()

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        return self.__wrapped_parser__.describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        return self.__wrapped_parser__.describe_value_or_def(value)

    def completer(self) -> yuio.complete.Completer:
        return self.__wrapped_parser__.completer()

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[T, yuio.Missing]]:
        return yuio.widget.Apply(
            self.__wrapped_parser__.widget(default, default_description),
            lambda v: self._validate(v) if v is not yuio.MISSING else None,
        )

    @abc.abstractmethod
    def _validate(self, value: T, /):
        """Implementation of value validation.

        Should raise :class:`ParsingError` if validation fails.

        """

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__wrapped_parser__!r})"


class Str(ValueParser[str]):
    """Parser for str values.

    Applies `modifiers` to the value, in order they are given.

    Example::

        >>> parser = Str().strip().lower()
        >>> parser.parse('  SOME STRING  ')
        'some string'

    """

    def __init__(self, *modifiers: _t.Callable[[str], str]):
        self.__modifiers = list(modifiers)

    def parse(self, value: str, /) -> str:
        for modifier in self.__modifiers:
            value = modifier(value)
        return value

    def parse_config(self, value: object, /) -> str:
        if not isinstance(value, str):
            raise ParsingError("expected a string")
        for modifier in self.__modifiers:
            value = modifier(value)
        return value

    def lower(self) -> "Str":
        """Return a parser that applies :meth:`str.lower` to all parsed strings."""

        return Str(*self.__modifiers, str.lower)

    def upper(self) -> "Str":
        """Return a parser that applies :meth:`str.upper` to all parsed strings."""

        return Str(*self.__modifiers, str.upper)

    def strip(self, char: _t.Optional[str] = None, /) -> "Str":
        """Return a parser that applies :meth:`str.strip` to all parsed strings."""

        return Str(*self.__modifiers, lambda s: s.strip(char))

    def lstrip(self, char: _t.Optional[str] = None, /) -> "Str":
        """Return a parser that applies :meth:`str.lstrip` to all parsed strings."""

        return Str(*self.__modifiers, lambda s: s.lstrip(char))

    def rstrip(self, char: _t.Optional[str] = None, /) -> "Str":
        """Return a parser that applies :meth:`str.rstrip` to all parsed strings."""

        return Str(*self.__modifiers, lambda s: s.rstrip(char))

    def regex(
        self, regex: _t.Union[str, re.Pattern[str]], /, group: _t.Union[int, str] = 0
    ) -> "Str":
        """Return a parser that matches the parsed string with the given regular expression.

        If regex has capturing groups, parser can return contents of a group.

        """

        if isinstance(regex, re.Pattern):
            compiled = regex
        else:
            compiled = re.compile(regex)

        def mapper(value: str) -> str:
            if (match := compiled.match(value)) is None:
                raise ParsingError(f"value should match regex '{compiled.pattern}'")
            return match.group(group)

        return Str(*self.__modifiers, mapper)


class Int(ValueParser[int]):
    """Parser for int values."""

    def parse(self, value: str, /) -> int:
        try:
            return int(value.strip())
        except ValueError:
            raise ParsingError(f"could not parse value {value!r} as an int") from None

    def parse_config(self, value: object, /) -> int:
        if isinstance(value, float):
            if value != int(value):
                raise ParsingError("expected an int, got a float instead")
            value = int(value)
        if not isinstance(value, int):
            raise ParsingError("expected an int")
        return value


class Float(ValueParser[float]):
    """Parser for float values."""

    def parse(self, value: str, /) -> float:
        try:
            return float(value.strip())
        except ValueError:
            raise ParsingError(f"could not parse value {value!r} as a float") from None

    def parse_config(self, value: object, /) -> float:
        if not isinstance(value, (float, int)):
            raise ParsingError("expected a float")
        return value


class Bool(ValueParser[bool]):
    """Parser for bool values, such as `'yes'` or `'no'`."""

    def parse(self, value: str, /) -> bool:
        value = value.strip().lower()

        if value in ("y", "yes", "true", "1"):
            return True
        elif value in ("n", "no", "false", "0"):
            return False
        else:
            raise ParsingError(
                f"could not parse value {value!r}," f" enter either 'yes' or 'no'"
            )

    def parse_config(self, value: object, /) -> bool:
        if not isinstance(value, bool):
            raise ParsingError("expected a bool")
        return value

    def describe(self) -> _t.Optional[str]:
        return "yes|no"

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        if not isinstance(value, bool):
            return None
        return "yes" if value else "no"

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.Choice(
            [
                yuio.complete.Option("no"),
                yuio.complete.Option("yes"),
            ]
        )

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[bool, yuio.Missing]]:
        options: _t.List[yuio.widget.Option[_t.Union[bool, yuio.Missing]]] = [
            yuio.widget.Option(False, "no"),
            yuio.widget.Option(True, "yes"),
        ]

        if default is yuio.MISSING:
            default_index = 0
        elif isinstance(default, bool):
            default_index = int(default)
        else:
            options.append(yuio.widget.Option(yuio.MISSING, default_description))
            default_index = 2

        return yuio.widget.Choice(options, default_index=default_index)


class Enum(ValueParser[E], _t.Generic[E]):
    """
    Parser for enums, as defined in the standard :mod:`enum` module.

    """

    def __init__(self, enum_type: _t.Type[E], /, *, by_name: bool = False):
        self.__enum_type: _t.Type[E] = enum_type
        self.__getter: _t.Callable[[E], object] = (
            (lambda e: e.name) if by_name else (lambda e: e.value)
        )

    def parse(self, value: str, /) -> E:
        cf_value = value.strip().casefold()

        candidates: _t.List[E] = []
        for item in self.__enum_type:
            if self.__getter(item) == value:
                return item
            elif str(self.__getter(item)).casefold().startswith(cf_value):
                candidates.append(item)

        if len(candidates) == 1:
            return candidates[0]
        elif len(candidates) > 1:
            enum_values = ", ".join(str(self.__getter(e)) for e in self.__enum_type)
            raise ParsingError(
                f"could not parse value {value!r}"
                f" as {self.__enum_type.__name__},"
                f" possible candidates are {enum_values}"
            )
        else:
            enum_values = ", ".join(str(self.__getter(e)) for e in self.__enum_type)
            raise ParsingError(
                f"could not parse value {value!r}"
                f" as {self.__enum_type.__name__},"
                f" should be one of {enum_values}"
            )

    def parse_config(self, value: object, /) -> E:
        if not isinstance(value, str):
            raise ParsingError("expected a string")

        result = self.parse(value)

        if self.__getter(result) != value:
            raise ParsingError(
                f"could not parse value {value!r}"
                f" as {self.__enum_type.__name__},"
                f" did you mean {self.__getter(result)}?"
            )

        return result

    def describe(self) -> _t.Optional[str]:
        desc = "|".join(str(self.__getter(e)) for e in self.__enum_type)
        return desc

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        if not isinstance(value, self.__enum_type):
            return None
        return str(self.__getter(value))

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.Choice(
            [yuio.complete.Option(str(self.__getter(e))) for e in self.__enum_type]
        )

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[E, yuio.Missing]]:
        options: _t.List[yuio.widget.Option[_t.Union[E, yuio.Missing]]] = [
            yuio.widget.Option(e, str(self.__getter(e))) for e in self.__enum_type
        ]

        if default is yuio.MISSING:
            default_index = 0
        elif isinstance(default, self.__enum_type):
            default_index = list(self.__enum_type).index(default)
        else:
            options.insert(0, yuio.widget.Option(yuio.MISSING, default_description))
            default_index = 0

        return yuio.widget.FilterableChoice(options, default_index=default_index)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__enum_type!r})"


class Decimal(ValueParser[decimal.Decimal]):
    """Parser for :class:`decimal.Decimal`."""

    def parse(self, value: str, /) -> decimal.Decimal:
        return self.parse_config(value)

    def parse_config(self, value: object, /) -> decimal.Decimal:
        if not isinstance(value, (int, float, str, decimal.Decimal)):
            raise ParsingError("expected an int, float, or string")
        try:
            return decimal.Decimal(value)
        except decimal.DecimalException:
            raise ParsingError(
                f"could not parse value {value!r} as a decimal number"
            ) from None


class Fraction(ValueParser[fractions.Fraction]):
    """Parser for :class:`fractions.Fraction`."""

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
                    f"could not parse value {value[0]}/{value[1]} as a fraction"
                ) from None
        if isinstance(value, (int, float, str, decimal.Decimal, fractions.Fraction)):
            try:
                return fractions.Fraction(value)
            except (ValueError, ZeroDivisionError):
                raise ParsingError(
                    f"could not parse value {value!r} as a fraction"
                ) from None
        raise ParsingError(
            "expected an int, float, fraction string, or a tuple of two ints"
        )


class Optional(Parser[_t.Optional[T]], _t.Generic[T]):
    """Parser for optional values.

    Allows handling `None`s when parsing config.

    """

    __wrapped_parser__: Parser[T]

    def __init__(self, inner: Parser[T]):
        self.__wrapped_parser__ = inner  # type: ignore

    def parse(self, value: str, /) -> _t.Optional[T]:
        return self.__wrapped_parser__.parse(value)

    def parse_many(self, value: _t.Sequence[str], /) -> _t.Optional[T]:
        return self.__wrapped_parser__.parse_many(value)

    def supports_parse_many(self) -> bool:
        return self.__wrapped_parser__.supports_parse_many()

    def parse_config(self, value: object, /) -> _t.Optional[T]:
        if value is None:
            return None
        return self.__wrapped_parser__.parse_config(value)

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        return self.__wrapped_parser__.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self.__wrapped_parser__.describe()

    def describe_or_def(self) -> str:
        return self.__wrapped_parser__.describe_or_def()

    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        return self.__wrapped_parser__.describe_many()

    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        return self.__wrapped_parser__.describe_many_or_def()

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        if value is None:
            return "<none>"
        return self.__wrapped_parser__.describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        if value is None:
            return "<none>"
        return self.__wrapped_parser__.describe_value_or_def(value)

    def completer(self) -> yuio.complete.Completer:
        return self.__wrapped_parser__.completer()

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[T, yuio.Missing]]:
        return self.__wrapped_parser__.widget(default, default_description)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.__wrapped_parser__!r})"


class CollectionParser(Parser[C], _t.Generic[C, T]):
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

    ..
        >>> from typing import Iterable, Generic

    .. code-block::

        >>> class DoubleList(CollectionParser[list[T], T], Generic[T]):
        ...     def __init__(self, inner: Parser[T], /, *, delimiter: str | None = None):
        ...         super().__init__(inner, list, self._ctor, delimiter=delimiter)
        ...
        ...     @staticmethod
        ...     def _ctor(values: Iterable[T]) -> list[T]:
        ...         return [x for value in values for x in [value, value]]

        >>> DoubleList(Int()).parse('1 2 3 4')
        [1, 1, 2, 2, 3, 3, 4, 4]

    """

    #: If set to false, autocompletion will not suggest item duplicates.
    _allow_completing_duplicates: _t.ClassVar[bool] = True

    def __init__(
        self,
        inner: Parser[T],
        ty: _t.Type[C],
        ctor: _t.Callable[[_t.Iterable[T]], C],
        /,
        *,
        iter: _t.Callable[[C], _t.Iterable[T]] = iter,
        config_type: _t.Type[C2] = list,
        config_type_iter: _t.Callable[[C2], _t.Iterable[T]] = iter,
        delimiter: _t.Optional[str] = None,
    ):
        if delimiter == "":
            raise ValueError("empty delimiter")

        #: See class parameters for more details.
        self._inner = inner
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

    def parse(self, value: str, /) -> C:
        return self.parse_many(value.split(self._delimiter))

    def parse_many(self, value: _t.Sequence[str], /) -> C:
        return self._ctor(self._inner.parse(item) for item in value)

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: object, /) -> C:
        if not isinstance(value, self._config_type):
            raise ParsingError(f"expected a {self._config_type.__name__}")

        return self._ctor(
            self._inner.parse_config(item) for item in self._config_type_iter(value)
        )

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        return "*"

    def describe(self) -> _t.Optional[str]:
        return self.describe_or_def()

    def describe_or_def(self) -> str:
        delimiter = self._delimiter or " "
        value = self._inner.describe_or_def()

        return f"{value}[{delimiter}{value}[{delimiter}...]]"

    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        return self._inner.describe()

    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        return self._inner.describe_or_def()

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        return self.describe_value_or_def(value)

    def describe_value_or_def(self, value: object, /) -> str:
        if not isinstance(value, self._ty):
            return str(value) or "<empty>"
        return (self._delimiter or " ").join(
            self._inner.describe_value_or_def(item) for item in self._iter(value)
        )

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.List(
            self._inner.completer(),
            delimiter=self._delimiter,
            allow_duplicates=self._allow_completing_duplicates,
        )

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[C, yuio.Missing]]:
        return _map_widget_result(
            self,
            default,
            yuio.widget.InputWithCompletion(
                self.completer(),
                placeholder=f" default: {default_description}"
                if default_description
                else "",
            ),
        )

    def __repr__(self):
        return f"{self.__class__.__name__}({self._inner!r})"


class List(CollectionParser[_t.List[T], T], _t.Generic[T]):
    """Parser for lists.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse list items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__(inner, list, list, delimiter=delimiter)


class Set(CollectionParser[_t.Set[T], T], _t.Generic[T]):
    """Parser for sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    _allow_completing_duplicates = False

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__(inner, set, set, delimiter=delimiter)


class FrozenSet(CollectionParser[_t.FrozenSet[T], T], _t.Generic[T]):
    """Parser for frozen sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    _allow_completing_duplicates = False

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__(inner, frozenset, frozenset, delimiter=delimiter)


class Dict(CollectionParser[_t.Dict[K, V], _t.Tuple[K, V]], _t.Generic[K, V]):
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

    _allow_completing_duplicates = False

    def __init__(
        self,
        key: Parser[K],
        value: Parser[V],
        /,
        *,
        delimiter: _t.Optional[str] = None,
        pair_delimiter: str = ":",
    ):
        inner: Parser[_t.Tuple[K, V]] = Tuple(key, value, delimiter=pair_delimiter)

        super().__init__(
            inner,
            dict,
            dict,
            iter=dict.items,
            config_type=dict,
            config_type_iter=dict.items,
            delimiter=delimiter,
        )


class Tuple(Parser[TU], _t.Generic[TU]):
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
            p1: Parser[T1],
            /,
            *,
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1]]":
            ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            /,
            *,
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2]]":
            ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            /,
            *,
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3]]":
            ...

        @_t.overload
        def __new__(
            cls,
            p1: Parser[T1],
            p2: Parser[T2],
            p3: Parser[T3],
            p4: Parser[T4],
            /,
            *,
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4]]":
            ...

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
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4, T5]]":
            ...

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
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6]]":
            ...

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
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7]]":
            ...

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
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7, T8]]":
            ...

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
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]]":
            ...

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
            delimiter: _t.Optional[str] = None,
        ) -> "Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9, T10]]":
            ...

        @_t.overload
        def __new__(
            cls, *parsers: Parser[_t.Any], delimiter: _t.Optional[str] = None
        ) -> "Tuple[_t.Tuple[_t.Any, ...]]":
            ...

        def __new__(
            cls, *parsers: Parser[_t.Any], delimiter: _t.Optional[str] = None
        ) -> "Tuple[_t.Tuple[_t.Any, ...]]":
            ...

    def __init__(  # pyright:ignore[reportInconsistentConstructor]
        #            FIXME: This is a bug in pyright,
        #            see https://github.com/microsoft/pyright/issues/8372.
        #            We can remove as soon as pylance is updated.
        self,
        *parsers: Parser[object],
        delimiter: _t.Optional[str] = None,
    ):
        if len(parsers) == 0:
            raise ValueError("empty tuple")
        self.__parsers = parsers
        if delimiter == "":
            raise ValueError("empty delimiter")
        self.__delimiter = delimiter

    def parse(self, value: str, /) -> TU:
        items = value.split(self.__delimiter, maxsplit=len(self.__parsers) - 1)
        return self.parse_many(items)

    def parse_many(self, value: _t.Sequence[str], /) -> TU:
        if len(value) != len(self.__parsers):
            raise ParsingError(f"expected {len(self.__parsers)} element(s)")

        return _t.cast(
            TU,
            tuple(parser.parse(item) for parser, item in zip(self.__parsers, value)),
        )

    def parse_config(self, value: object, /) -> TU:
        if not isinstance(value, (list, tuple)):
            raise ParsingError("expected a list or a tuple")
        elif len(value) != len(self.__parsers):
            raise ParsingError(f"expected {len(self.__parsers)} element(s)")

        return _t.cast(
            TU,
            tuple(
                parser.parse_config(item) for parser, item in zip(self.__parsers, value)
            ),
        )

    def supports_parse_many(self) -> bool:
        return True

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        return len(self.__parsers)

    def describe(self) -> _t.Optional[str]:
        return self.describe_or_def()

    def describe_or_def(self) -> str:
        delimiter = self.__delimiter or " "
        desc = [parser.describe_or_def() for parser in self.__parsers]

        return delimiter.join(desc)

    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        return tuple(parser.describe() or "value" for parser in self.__parsers)

    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        return tuple(parser.describe_or_def() for parser in self.__parsers)

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        if not isinstance(value, tuple):
            return None

        return self.describe_value_or_def(value)

    def describe_value_or_def(self, value: object, /) -> str:
        if not isinstance(value, tuple):
            return str(value) or "<empty>"

        delimiter = self.__delimiter or " "
        desc = [
            parser.describe_value_or_def(item)
            for parser, item in zip(self.__parsers, value)
        ]

        return delimiter.join(desc)

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.Tuple(
            *[parser.completer() for parser in self.__parsers],
            delimiter=self.__delimiter,
        )

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[TU, yuio.Missing]]:
        completer = self.completer()

        return _map_widget_result(
            self,
            default,
            yuio.widget.InputWithCompletion(
                completer,
                placeholder=f" default: {default_description}"
                if default_description
                else "",
            ),
        )

    def __repr__(self):
        parsers = ", ".join(repr(parser) for parser in self.__parsers)
        return f"{self.__class__.__name__}({parsers})"


class DateTime(ValueParser[datetime.datetime]):
    """Parse a datetime in ISO ('YYYY-MM-DD HH:MM:SS') format."""

    def parse(self, value: str, /) -> datetime.datetime:
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            raise ParsingError(
                f"could not parse value {value!r} as a datetime"
            ) from None

    def parse_config(self, value: object, /) -> datetime.datetime:
        if isinstance(value, datetime.datetime):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected a datetime")


class Date(ValueParser[datetime.date]):
    """Parse a date in ISO ('YYYY-MM-DD') format."""

    def parse(self, value: str, /) -> datetime.date:
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            raise ParsingError(f"could not parse value {value!r} as a date") from None

    def parse_config(self, value: object, /) -> datetime.date:
        if isinstance(value, datetime.datetime):
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected a date")


class Time(ValueParser[datetime.time]):
    """Parse a date in ISO ('HH:MM:SS') format."""

    def parse(self, value: str, /) -> datetime.time:
        try:
            return datetime.time.fromisoformat(value)
        except ValueError:
            raise ParsingError(f"could not parse value {value!r} as a time") from None

    def parse_config(self, value: object, /) -> datetime.time:
        if isinstance(value, datetime.datetime):
            return value.time()
        elif isinstance(value, datetime.time):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected a time")


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
    r"^"
    r"(?:([+-]?)\s*((?:\d+\s*[a-z]+\s*)+))?"
    r"(?:([+-]?)\s*(\d\d:\d\d(?::\d\d(?:\.\d{3}\d{3}?)?)?))?"
    r"$",
    re.IGNORECASE,
)

_COMPONENT_RE = re.compile(r"(\d+)\s*([a-z]+)\s*")


class TimeDelta(ValueParser[datetime.timedelta]):
    """Parse a time delta."""

    def parse(self, value: str, /) -> datetime.timedelta:
        value = value.strip()

        if not value:
            raise ParsingError("got an empty timedelta")

        if match := _TIMEDELTA_RE.match(value):
            c_sign_s, components_s, t_sign_s, time_s = match.groups()
        else:
            raise ParsingError(f"could not parse value {value!r} as a timedelta")

        c_sign_s = -1 if c_sign_s == "-" else 1
        t_sign_s = -1 if t_sign_s == "-" else 1

        kwargs = {u: 0 for u, _ in _UNITS_MAP}

        if components_s:
            for num, unit in _COMPONENT_RE.findall(components_s):
                if unit_key := _UNITS.get(unit.lower()):
                    kwargs[unit_key] += int(num)
                else:
                    raise ParsingError(
                        f"could not parse value {value!r} as a timedelta: "
                        f"unknown unit {unit!r}"
                    )

        timedelta = c_sign_s * datetime.timedelta(**kwargs)

        if time_s:
            time = datetime.time.fromisoformat(time_s)
            timedelta += t_sign_s * datetime.timedelta(
                hours=time.hour,
                minutes=time.minute,
                seconds=time.second,
                microseconds=time.microsecond,
            )

        return timedelta

    def parse_config(self, value: object, /) -> datetime.timedelta:
        if isinstance(value, datetime.timedelta):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f"expected a timedelta")


class Path(ValueParser[pathlib.Path]):
    """Parse a file system path, return a :class:`pathlib.Path`.

    :param extensions: list of allowed file extensions.

    """

    def __init__(
        self,
        extensions: _t.Union[str, _t.Collection[str], None] = None,
    ):
        self.__extensions = [extensions] if isinstance(extensions, str) else extensions

    def parse(self, value: str, /) -> pathlib.Path:
        path = pathlib.Path(value).expanduser().resolve()
        self._validate(path)
        return path

    def parse_config(self, value: object, /) -> pathlib.Path:
        if not isinstance(value, str):
            raise ParsingError("expected a string")
        return self.parse(value)

    def describe(self) -> _t.Optional[str]:
        if self.__extensions is not None:
            return "|".join("*" + e for e in self.__extensions)
        else:
            return None

    def _validate(self, value: pathlib.Path, /):
        if self.__extensions is not None:
            if not any(value.name.endswith(ext) for ext in self.__extensions):
                exts = ", ".join(self.__extensions)
                raise ParsingError(f"{value} should have extension {exts}")

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.File(extensions=self.__extensions)


class NonExistentPath(Path):
    """Parse a file system path and verify that it doesn't exist."""

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if value.exists():
            raise ParsingError(f"{value} already exist")


class ExistingPath(Path):
    """Parse a file system path and verify that it exists."""

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.exists():
            raise ParsingError(f"{value} doesn't exist")


class File(ExistingPath):
    """Parse path to a file."""

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_file():
            raise ParsingError(f"{value} is not a file")


class Dir(ExistingPath):
    """Parse path to a directory."""

    def __init__(self):
        # Disallow passing `extensions`.
        super().__init__()

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_dir():
            raise ParsingError(f"{value} is not a directory")

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.Dir()


class GitRepo(Dir):
    """Parse path to a git repository.

    This parser just checks that the given directory has
    a subdirectory named ``.git``.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.joinpath(".git").is_dir():
            raise ParsingError(f"{value} is not a git repository")


class _BoundImpl(ValidatingParser[T], _t.Generic[T, Cmp]):
    _Self = _t.TypeVar("_Self", bound="_BoundImpl[_t.Any, _t.Any]")

    def __init__(
        self,
        inner: Parser[T],
        /,
        *,
        lower: _t.Optional[Cmp] = None,
        lower_inclusive: _t.Optional[Cmp] = None,
        upper: _t.Optional[Cmp] = None,
        upper_inclusive: _t.Optional[Cmp] = None,
        mapper: _t.Callable[[T], Cmp],
        desc: str,
    ):
        super().__init__(inner)

        self.__lower_bound: _t.Optional[Cmp] = None
        self.__lower_bound_is_inclusive: bool = True
        self.__upper_bound: _t.Optional[Cmp] = None
        self.__upper_bound_is_inclusive: bool = True

        if lower is not None and lower_inclusive is not None:
            raise TypeError(
                "lower and lower_inclusive cannot be given at the same time"
            )
        elif lower is not None:
            self.__lower_bound = lower
            self.__lower_bound_is_inclusive = False
        elif lower_inclusive is not None:
            self.__lower_bound = lower_inclusive
            self.__lower_bound_is_inclusive = True

        if upper is not None and upper_inclusive is not None:
            raise TypeError(
                "upper and upper_inclusive cannot be given at the same time"
            )
        elif upper is not None:
            self.__upper_bound = upper
            self.__upper_bound_is_inclusive = False
        elif upper_inclusive is not None:
            self.__upper_bound = upper_inclusive
            self.__upper_bound_is_inclusive = True

        self.__mapper = mapper
        self.__desc = desc

    def _validate(self, value: T, /):
        mapped = self.__mapper(value)

        if self.__lower_bound is not None:
            if self.__lower_bound_is_inclusive and mapped < self.__lower_bound:
                raise ParsingError(
                    f"{self.__desc} should be greater or equal to {self.__lower_bound},"
                    f" got {value} instead"
                )
            elif not self.__lower_bound_is_inclusive and not self.__lower_bound < mapped:
                raise ParsingError(
                    f"{self.__desc} should be greater than {self.__lower_bound},"
                    f" got {value} instead"
                )

        if self.__upper_bound is not None:
            if self.__upper_bound_is_inclusive and self.__upper_bound < mapped:
                raise ParsingError(
                    f"{self.__desc} should be lesser or equal to {self.__upper_bound},"
                    f" got {value} instead"
                )
            elif not self.__upper_bound_is_inclusive and not mapped < self.__upper_bound:
                raise ParsingError(
                    f"{self.__desc} should be lesser than {self.__upper_bound},"
                    f" got {value} instead"
                )

    def __repr__(self):
        desc = ""
        if self.__lower_bound is not None:
            desc += repr(self.__lower_bound)
            desc += " <= " if self.__lower_bound_is_inclusive else " < "
        mapper_name = getattr(self.__mapper, "__name__")
        if mapper_name and mapper_name != "<lambda>":
            desc += mapper_name
        else:
            desc += "x"
        if self.__upper_bound is not None:
            desc += " <= " if self.__upper_bound_is_inclusive else " < "
            desc += repr(self.__upper_bound)
        return f"{self.__class__.__name__}({self.__wrapped_parser__!r}, {desc})"


class Bound(_BoundImpl[Cmp, Cmp], _t.Generic[Cmp]):
    """Check that value is upper- or lower-bound by some constraints.

    See :meth:`Parser.bound` for more info.

    """

    def __init__(
        self,
        inner: Parser[Cmp],
        /,
        *,
        lower: _t.Optional[Cmp] = None,
        lower_inclusive: _t.Optional[Cmp] = None,
        upper: _t.Optional[Cmp] = None,
        upper_inclusive: _t.Optional[Cmp] = None,
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


class LenBound(_BoundImpl[Sz, int], _t.Generic[Sz]):
    """Check that length of a value is upper- or lower-bound by some constraints.

    See :meth:`Parser.len_bound` for more info.

    """

    def __init__(
        self,
        inner: Parser[Sz],
        /,
        *,
        lower: _t.Optional[int] = None,
        lower_inclusive: _t.Optional[int] = None,
        upper: _t.Optional[int] = None,
        upper_inclusive: _t.Optional[int] = None,
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

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        if not self.__wrapped_parser__.supports_parse_many():
            # somebody bound len of a string?
            return self.__wrapped_parser__.get_nargs()

        lower = self.__lower_bound
        if lower is not None and not self.__lower_bound_is_inclusive:
            lower += 1
        upper = self.__upper_bound
        if upper is not None and not self.__upper_bound_is_inclusive:
            upper -= 1

        if lower == upper:
            return lower
        elif lower is not None and lower > 0:
            return "+"
        else:
            return "*"


class OneOf(ValidatingParser[T], _t.Generic[T]):
    """Check that the parsed value is one of the given set of values.

    See :meth:`Parser.one_of` for more info.

    """

    def __init__(self, inner: Parser[T], values: _t.Collection[T], /):
        super().__init__(inner)

        self.__allowed_values = values

    def _validate(self, value: T, /):
        if value not in self.__allowed_values:
            values = ", ".join(map(str, self.__allowed_values))
            raise ParsingError(
                f"could not parse value {value!r}," f" should be one of {values}"
            )

    def describe(self) -> _t.Optional[str]:
        desc = "|".join(self.describe_value_or_def(e) for e in self.__allowed_values)
        if len(desc) < 80:
            return desc
        else:
            return super().describe()

    def describe_or_def(self) -> str:
        return self.describe() or super().describe_or_def()

    def completer(self) -> yuio.complete.Completer:
        return yuio.complete.Choice(
            [
                yuio.complete.Option(self.describe_value_or_def(e))
                for e in self.__allowed_values
            ]
        )

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[T, yuio.Missing]]:
        allowed_values = list(self.__allowed_values)

        options: _t.List[yuio.widget.Option[_t.Union[T, yuio.Missing]]] = [
            yuio.widget.Option(e, self.__wrapped_parser__.describe_value_or_def(e))
            for e in allowed_values
        ]

        if default is yuio.MISSING:
            default_index = 0
        elif default in allowed_values:
            default_index = list(allowed_values).index(default)  # type: ignore
        else:
            options.insert(0, yuio.widget.Option(yuio.MISSING, default_description))
            default_index = 0

        return yuio.widget.FilterableChoice(options, default_index=default_index)


class Map(Parser[T], _t.Generic[T]):
    """A wrapper that maps result of the given parser using the given function.

    Example::

        >>> # Run `Int` parser, then square the result.
        >>> int_parser = Map(Int(), lambda x: x ** 2)
        >>> int_parser.parse("8")
        64

    """

    def __init__(self, inner: Parser[U], fn: _t.Callable[[U], T], /):
        self.__inner = inner
        self.__fn = fn

    def parse(self, value: str, /) -> T:
        return self.__fn(self.__inner.parse(value))

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        return self.__fn(self.__inner.parse_many(value))

    def supports_parse_many(self) -> bool:
        return self.__inner.supports_parse_many()

    def parse_config(self, value: object, /) -> T:
        return self.__fn(self.__inner.parse_config(value))

    def get_nargs(self) -> _t.Union[_t.Literal["-", "+", "*", "?"], int, None]:
        return self.__inner.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self.__inner.describe()

    def describe_or_def(self) -> str:
        return self.__inner.describe_or_def()

    def describe_many(self) -> _t.Union[str, _t.Tuple[str, ...], None]:
        return self.__inner.describe_many()

    def describe_many_or_def(self) -> _t.Union[str, _t.Tuple[str, ...]]:
        return self.__inner.describe_many_or_def()

    def describe_value(self, value: object, /) -> _t.Optional[str]:
        return self.__inner.describe_value(value)

    def describe_value_or_def(self, value: object, /) -> str:
        return self.__inner.describe_value_or_def(value)

    def completer(self) -> yuio.complete.Completer:
        return self.__inner.completer()

    def widget(
        self, default: _t.Union[object, yuio.Missing], default_description: str, /
    ) -> yuio.widget.Widget[_t.Union[T, yuio.Missing]]:
        mapper = lambda v: self.__fn(v) if v is not yuio.MISSING else yuio.MISSING
        return yuio.widget.Map(
            self.__inner.widget(default, default_description),
            mapper,
        )


class Apply(Map[T], _t.Generic[T]):
    """A wrapper that applies the given function to the result of a wrapped widget.

    Example::

        >>> # Run `Int` parser, then print its output before returning.
        >>> print_output = Apply(Int(), print)
        >>> result = print_output.parse("10")
        10
        >>> result
        10

    """

    def __init__(self, inner: Parser[T], fn: _t.Callable[[T], None], /):
        def mapper(x: T) -> T:
            fn(x)
            return x

        super().__init__(inner, mapper)


def _map_widget_result(
    parser: Parser[T],
    default: _t.Union[object, yuio.Missing],
    widget: yuio.widget.Widget[str],
) -> yuio.widget.Widget[_t.Union[T, yuio.Missing]]:
    def mapper(s: str) -> _t.Union[T, yuio.Missing]:
        if not s and default is not yuio.MISSING:
            return yuio.MISSING
        elif not s:
            raise ParsingError("Input is required.")
        else:
            return parser.parse(s)

    return yuio.widget.Map(widget, mapper)


_FromTypeHintCallback: _t.TypeAlias = _t.Callable[
    [type, _t.Optional[type], _t.Tuple[object, ...]], _t.Optional[Parser[object]]
]


_FROM_TYPE_HINT_CALLBACKS: _t.List[_t.Tuple["_FromTypeHintCallback", bool]] = []
_FROM_TYPE_HINT_DELIM_SUGGESTIONS: _t.List[_t.Optional[str]] = [
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
def from_type_hint(ty: _t.Type[T], /) -> "Parser[T]":
    ...


@_t.overload
def from_type_hint(ty: object, /) -> "Parser[object]":
    ...


def from_type_hint(ty: _t.Any, /) -> "Parser[_t.Any]":
    """Create parser from a type hint.

    Example::

        >>> from_type_hint(list[int] | None)
        Optional(List(Int))

    """

    if isinstance(ty, str) or isinstance(ty, _t.ForwardRef):
        raise TypeError(f"forward references are not supported here: {ty}")

    origin = _t.get_origin(ty)
    args = _t.get_args(ty)

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

    raise TypeError(f"unsupported type {ty}")


@_t.overload
def register_type_hint_conversion(
    cb: "_FromTypeHintCallback",
    /,
    *,
    uses_delim: bool = False,
) -> "_FromTypeHintCallback":
    ...


@_t.overload
def register_type_hint_conversion(
    *,
    uses_delim: bool = False,
) -> "_t.Callable[[_FromTypeHintCallback], _FromTypeHintCallback]":
    ...


def register_type_hint_conversion(
    cb: "_t.Optional[_FromTypeHintCallback]" = None,
    /,
    *,
    uses_delim: bool = False,
) -> _t.Union[
    _FromTypeHintCallback, _t.Callable[[_FromTypeHintCallback], _FromTypeHintCallback]
]:
    """Register a new converter from typehint to a parser.

    This function takes a callback that accepts three positional arguments:

    - a type hint,
    - a type hint's origin (as defined by :func:`typing.get_origin`),
    - a type hint's args (as defined by :func:`typing.get_args`).

    The callback should return a parser if it can, or `None` otherwise.

    All registered callbacks are tried in the same order
    as the were registered.

    If ``uses_delim`` is true, callback can use
    :func:`suggest_delim_for_type_hint_conversion`.

    This function can be used as a decorator.

    ..
        >>> class MyType: ...
        >>> class MyTypeParser(ValueParser[MyType]):
        ...     def parse(self, value: str, /) -> MyType: ...
        ...     def parse_config(self, value: object, /) -> MyType: ...

    Example::

        >>> @register_type_hint_conversion
        ... def my_type_conversion(ty, origin, args):
        ...     if ty is MyType:
        ...         return MyTypeParser()
        ...     else:
        ...         return None

        >>> from_type_hint(MyType)
        MyTypeParser

    ..
        >>> del _FROM_TYPE_HINT_CALLBACKS[-1]

    """

    def registrar(cb: _FromTypeHintCallback):
        _FROM_TYPE_HINT_CALLBACKS.append((cb, uses_delim))
        return cb

    return registrar(cb) if cb is not None else registrar


def suggest_delim_for_type_hint_conversion() -> _t.Optional[str]:
    """
    Suggests a delimiter for use in type hint converters.

    When creating a parser for a collection of items based on a type hint,
    it is important to use different delimiters for nested collections.
    This function can suggest such a delimiter based on the current type hint's depth.

    ..
        >>> class MyCollection(list, _t.Generic[T]): ...
        >>> class MyCollectionParser(CollectionParser[MyCollection[T], T], _t.Generic[T]):
        ...     def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        ...         super().__init__(inner, MyCollection, MyCollection, delimiter=delimiter)

    Example::

        >>> @register_type_hint_conversion(uses_delim=True)
        ... def my_collection_conversion(ty, origin, args):
        ...     if origin is MyCollection:
        ...         return MyCollectionParser(
        ...             from_type_hint(args[0]),
        ...             delimiter=suggest_delim_for_type_hint_conversion(),
        ...         )
        ...     else:
        ...         return None

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


register_type_hint_conversion(
    lambda ty, origin, args: Optional(from_type_hint(args[1 - args.index(type(None))]))
    if _t.is_union(origin) and len(args) == 2 and type(None) in args
    else None
)
register_type_hint_conversion(lambda ty, origin, args: Str() if ty is str else None)
register_type_hint_conversion(lambda ty, origin, args: Int() if ty is int else None)
register_type_hint_conversion(lambda ty, origin, args: Float() if ty is float else None)
register_type_hint_conversion(lambda ty, origin, args: Bool() if ty is bool else None)
register_type_hint_conversion(
    lambda ty, origin, args: Enum(ty)
    if isinstance(ty, type) and issubclass(ty, enum.Enum)
    else None
)
register_type_hint_conversion(
    lambda ty, origin, args: Decimal() if ty is decimal.Decimal else None
)
register_type_hint_conversion(
    lambda ty, origin, args: Fraction() if ty is fractions.Fraction else None
)
register_type_hint_conversion(
    lambda ty, origin, args: List(
        from_type_hint(args[0]), delimiter=suggest_delim_for_type_hint_conversion()
    )
    if origin is list
    else None,
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: Set(
        from_type_hint(args[0]), delimiter=suggest_delim_for_type_hint_conversion()
    )
    if origin is set
    else None,
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: FrozenSet(
        from_type_hint(args[0]), delimiter=suggest_delim_for_type_hint_conversion()
    )
    if origin is frozenset
    else None,
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: Dict(
        from_type_hint(args[0]),
        from_type_hint(args[1]),
        delimiter=suggest_delim_for_type_hint_conversion(),
    )
    if origin is dict
    else None,
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: Tuple(
        *[from_type_hint(arg) for arg in args],
        delimiter=suggest_delim_for_type_hint_conversion(),
    )
    if origin is tuple and ... not in args
    else None,
    uses_delim=True,
)
register_type_hint_conversion(
    lambda ty, origin, args: Path() if ty is pathlib.Path else None
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


def _is_optional_parser(parser: _t.Optional[Parser[object]], /) -> bool:
    while parser is not None:
        if isinstance(parser, Optional):
            return True
        parser = parser.__wrapped_parser__
    return False
