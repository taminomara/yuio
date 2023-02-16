# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides several parsers that convert (usually user-provided)
strings to python objects, or check user input, and throw
:class:`ValueError` in case of any issue.

All parsers are descendants of the :class:`Parser` class.
On the surface, they are just callables that take a string and return a python
object. That is, you can use them in any place that expects such callable,
for example in flags in argparse, or in :func:`~yuio.io.ask` method
from :mod:`yuio.io`.

When parsing fails, we raise :class:`ParsingError`.


Base parser
-----------

.. autoclass:: Parser
   :members:

.. autoclass:: ParsingError


Value parsers
-------------

.. autoclass:: Str

.. autoclass:: Int

.. autoclass:: Float

.. autoclass:: Bool

.. autoclass:: Enum

.. autoclass:: List

.. autoclass:: Set

.. autoclass:: FrozenSet

.. autoclass:: Dict

.. autoclass:: Pair

.. autoclass:: Tuple


File system path parsers
------------------------

.. autoclass:: Path

.. autoclass:: NonExistentPath

.. autoclass:: ExistingPath

.. autoclass:: File

.. autoclass:: Dir

.. autoclass:: GitRepo


Validators
----------

.. autoclass:: Bound

.. autoclass:: BoundLen

.. autoclass:: OneOf

.. autoclass:: Regex


Deriving parsers from type hints
--------------------------------

There is a way to automatically derive basic parsers from type hints
(used by :mod:`yuio.config`). To extend capabilities of the automatic converter,
you can register your own types and parsers:

.. autofunction:: from_type_hint

.. autofunction:: register_type_hint_conversion

"""

import abc
import argparse
import datetime
import enum
import pathlib
import re
import typing as _t

import yuio._utils


class _Comparable(_t.Protocol):
    @abc.abstractmethod
    def __lt__(self, other, /) -> bool: ...

    @abc.abstractmethod
    def __gt__(self, other, /) -> bool: ...

    @abc.abstractmethod
    def __le__(self, other, /) -> bool: ...

    @abc.abstractmethod
    def __ge__(self, other, /) -> bool: ...

    @abc.abstractmethod
    def __eq__(self, other, /) -> bool: ...


T = _t.TypeVar('T')
K = _t.TypeVar('K')
V = _t.TypeVar('V')
Sz = _t.TypeVar('Sz', bound=_t.Sized)
Cmp = _t.TypeVar('Cmp', bound=_Comparable)
E = _t.TypeVar('E', bound=enum.Enum)
TU = _t.TypeVar('TU', bound=tuple)


class ParsingError(ValueError, argparse.ArgumentTypeError):
    """Raised when parsing or validation fails.

    This exception is derived from both :class:`ValueError`
    and :class:`argparse.ArgumentTypeError` to ensure that error messages
    are displayed nicely with argparse, and handled correctly in other places.

    """


class Parser(_t.Generic[T], abc.ABC):
    """Base class for parsers.

    """

    def __init__(self):
        # For some reason PyCharm incorrectly derives some types without
        # this `__init__`. You can check with the following code:
        #
        # ```
        # def interact(msg: str, p: Parser[T]) -> T:
        #     return p(msg)
        #
        # val = interact('10', Int())  # type for `val` is not derived
        # ```
        pass

    @abc.abstractmethod
    def _parse(self, value: str, /) -> T:
        """Implementation of :meth:`~Parser.parse`.

        """

    @abc.abstractmethod
    def _parse_config(self, value: _t.Any, /) -> T:
        """Implementation of :meth:`~Parser.parse_config`.

        """

    def _parse_many(self, value: _t.Sequence[str], /) -> T:
        """Implementation of :meth:`~Parser.parse_many`.

        """

        raise RuntimeError('unable to parse multiple values')

    @abc.abstractmethod
    def _validate(self, value: T, /):
        """Implementation of :meth:`~Parser.validate`.

        """

    def _supports_parse_many(self) -> bool:
        """Implementation of :meth:`~Parser.supports_parse_many`.

        """

        return False

    def _supports_parse_optional(self) -> bool:
        """Implementation of :meth:`~Parser.supports_parse_optional`.

        """

        return False

    def _get_nargs(self) -> _t.Union[str, int, None]:
        """Implementation of :meth:`~Parser.get_nargs`.

        """

        return None

    @_t.final
    def __call__(self, value: str, /) -> T:
        return self.parse(value)

    @_t.final
    def parse(self, value: str, /) -> T:
        """Parse and validate user input,
        raise :class:`ParsingError` on failure.

        """

        parsed = self._parse(value)
        self._validate(parsed)
        return parsed

    @_t.final
    def parse_config(self, value: _t.Any, /) -> T:
        """Parse and validate value from a config,
        raise :class:`ParsingError` on failure.

        This method accepts python values, i.e. when parsing a json config.

        """

        parsed = self._parse_config(value)
        self._validate(parsed)
        return parsed

    @_t.final
    def parse_many(self, value: _t.Sequence[str], /) -> T:
        """Parse a list of user inputs by parsing them and uniting
        parsed values into a collection.

        """

        parsed = self._parse_many(value)
        self._validate(parsed)
        return parsed

    @_t.final
    def validate(self, value: T, /):
        """Verify parsed value, raise :class:`ParsingError` on failure.

        """

        self._validate(value)

    @_t.final
    def supports_parse_many(self) -> bool:
        """Return true if this parser returns a collection
        and so supports :meth:`~Parser.parse_many`.

        """

        return self._supports_parse_many()

    @_t.final
    def supports_parse_optional(self) -> bool:
        """Return true if this parser can handle optional values.

        """

        return self._supports_parse_optional()

    @_t.final
    def get_nargs(self) -> _t.Union[str, int, None]:
        """Generate `nargs` for argparse.

        """

        return self._get_nargs()

    def describe(self) -> _t.Optional[str]:
        """Return a human-readable description of an expected input.

        """

        return None

    def describe_or_def(self) -> str:
        """Like :py:meth:`~Parser.describe`,
        but guaranteed to return something.

        """

        return (
            self.describe()
            or yuio._utils.to_dash_case(self.__class__.__name__)
        )

    def describe_many(self) -> _t.Optional[str]:
        """Return a human-readable description of a container element.

        Used with :meth:`~Parser.parse_many`, when the outermost container
        is parsed in :mod:`argparse`.

        """

        return self.describe()

    def describe_many_or_def(self) -> str:
        """Like :py:meth:`~Parser.describe_many`,
        but guaranteed to return something.

        """

        return (
            self.describe_many()
            or yuio._utils.to_dash_case(self.__class__.__name__)
        )

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        """Return a human-readable description of a given value.

        """

        return None

    def describe_value_or_def(self, value: T, /) -> str:
        """Like :py:meth:`~Parser.describe_value`,
        but guaranteed to return something.

        """

        return self.describe_value(value) or str(value)

    @_t.final
    def bound(
        self: 'Parser[Cmp]',
        *,
        lower: _t.Optional[Cmp] = None,
        lower_inclusive: _t.Optional[Cmp] = None,
        upper: _t.Optional[Cmp] = None,
        upper_inclusive: _t.Optional[Cmp] = None
    ) -> 'Bound[Cmp]':
        """Check that value is upper- or lower-bound by some constraints.

        See :class:`Bound` for more info.

        """

        return Bound(
            self,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
        )

    @_t.final
    def gt(self: 'Parser[Cmp]', bound: Cmp, /) -> 'Bound[Cmp]':
        """Check that value is greater then the given bound.

        See :class:`Bound` for more info.

        """

        return self.bound(lower=bound)

    @_t.final
    def ge(self: 'Parser[Cmp]', bound: Cmp, /) -> 'Bound[Cmp]':
        """Check that value is greater then or equal to the given bound.

        See :class:`Bound` for more info.

        """

        return self.bound(lower_inclusive=bound)

    @_t.final
    def lt(self: 'Parser[Cmp]', bound: Cmp, /) -> 'Bound[Cmp]':
        """Check that value is lesser then the given bound.

        See :class:`Bound` for more info.

        """

        return self.bound(upper=bound)

    @_t.final
    def le(self: 'Parser[Cmp]', bound: Cmp, /) -> 'Bound[Cmp]':
        """Check that value is lesser then or equal to the given bound.

        See :class:`Bound` for more info.

        """

        return self.bound(upper_inclusive=bound)

    @_t.final
    def len_bound(
        self: 'Parser[Sz]',
        *,
        lower: _t.Optional[int] = None,
        lower_inclusive: _t.Optional[int] = None,
        upper: _t.Optional[int] = None,
        upper_inclusive: _t.Optional[int] = None
    ) -> 'LenBound[Sz]':
        """Check that length of a value is upper- or lower-bound
        by some constraints.

        See :class:`BoundLen` for more info.

        """

        return LenBound(
            self,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
        )

    @_t.final
    def len_gt(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is greater then
        the given bound.

        See :class:`Bound` for more info.

        """

        return self.len_bound(lower=bound)

    @_t.final
    def len_ge(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is greater then or equal to
        the given bound.

        See :class:`Bound` for more info.

        """

        return self.len_bound(lower_inclusive=bound)

    @_t.final
    def len_lt(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is lesser then
        the given bound.

        See :class:`Bound` for more info.

        """

        return self.len_bound(upper=bound)

    @_t.final
    def len_le(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is lesser then or equal to
        the given bound.

        See :class:`Bound` for more info.

        """

        return self.len_bound(upper_inclusive=bound)

    @_t.final
    def len_eq(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is equal to
        the given bound.

        See :class:`Bound` for more info.

        """

        return self.len_bound(lower_inclusive=bound, upper_inclusive=bound)

    @_t.final
    def one_of(
        self: 'Parser[T]',
        values: _t.Collection[T],
        /
    ) -> 'OneOf[T]':
        """Check that the parsed value is one of the given set of values.

        See :class:`OneOf` for more info.

        """

        return OneOf(self, values)

    @_t.final
    def optional(self) -> 'Optional[T]':
        """Enable parsing optional values.

        """

        return Optional(self)


class Str(Parser[str]):
    """Parser for str values.

    Applies a `modifiers` to the value, in order they are given.

    """

    def __init__(self, *modifiers: _t.Callable[[str], str]):
        super().__init__()

        self._modifiers = list(modifiers)

    def _parse(self, value: str, /) -> str:
        for modifier in self._modifiers:
            value = modifier(value)
        return value

    def _parse_config(self, value: _t.Any, /) -> str:
        if not isinstance(value, str):
            raise ParsingError('expected a string')
        for modifier in self._modifiers:
            value = modifier(value)
        return value

    def _validate(self, value: str, /):
        pass

    def lower(self) -> 'Str':
        """Applies :meth:`str.lower` to all parsed strings.

        """

        return Str(*self._modifiers, str.lower)

    def upper(self) -> 'Str':
        """Applies :meth:`str.upper` to all parsed strings.

        """

        return Str(*self._modifiers, str.upper)

    def strip(self, char: _t.Optional[str] = None, /) -> 'Str':
        """Applies :meth:`str.strip` to all parsed strings.

        """

        return Str(*self._modifiers, lambda s: s.strip(char))

    def lstrip(self, char: _t.Optional[str] = None, /) -> 'Str':
        """Applies :meth:`str.lstrip` to all parsed strings.

        """

        return Str(*self._modifiers, lambda s: s.lstrip(char))

    def rstrip(self, char: _t.Optional[str] = None, /) -> 'Str':
        """Applies :meth:`str.rstrip` to all parsed strings.

        """

        return Str(*self._modifiers, lambda s: s.rstrip(char))

    def regex(self, regex: _t.Union[str, re.Pattern], /) -> 'Str':
        """Checks that the parsed string matches the given regular expression.

        """

        if isinstance(regex, str):
            compiled = re.compile(regex)
        else:
            compiled = regex

        def mapper(value: str) -> str:
            if compiled.match(value) is None:
                raise ParsingError(
                    f'value should match regex \'{compiled.pattern}\'')
            return value

        return Str(*self._modifiers, mapper)


class Int(Parser[int]):
    """Parser for int values.

    """

    def _parse(self, value: str, /) -> int:
        try:
            return int(value.strip())
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as an int')

    def _parse_config(self, value: _t.Any, /) -> int:
        if isinstance(value, float):
            if value != int(value):
                raise ParsingError('expected an int, got a float instead')
            value = int(value)
        if not isinstance(value, int):
            raise ParsingError('expected an int')
        return value

    def _validate(self, value: int, /):
        pass


class Float(Parser[float]):
    """Parser for float values.

    """

    def _parse(self, value: str, /) -> float:
        try:
            return float(value.strip())
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as a float')

    def _parse_config(self, value: _t.Any, /) -> float:
        if not isinstance(value, (float, int)):
            raise ParsingError('expected a float')
        return value

    def _validate(self, value: float, /):
        pass


class Bool(Parser[bool]):
    """Parser for bool values, such as `'yes'` or `'no'`.

    """

    def _parse(self, value: str, /) -> bool:
        value = value.strip().lower()

        if value in ('y', 'yes', 'true', '1'):
            return True
        elif value in ('n', 'no', 'false', '0'):
            return False
        else:
            raise ParsingError(f'could not parse value {value!r},'
                               f' enter either \'yes\' or \'no\'')

    def _parse_config(self, value: _t.Any, /) -> bool:
        if not isinstance(value, bool):
            raise ParsingError('expected a bool')
        return value

    def _validate(self, value: bool, /):
        pass

    def describe(self) -> _t.Optional[str]:
        return 'yes|no'

    def describe_value(self, value: bool, /) -> _t.Optional[str]:
        return 'yes' if value else 'no'


class Enum(Parser[E], _t.Generic[E]):
    """Parser for enums, as defined in the standard :mod:`enum` module.

    """

    def __init__(self, enum_type: _t.Type[E], /):
        super().__init__()

        self._enum_type: _t.Type[E] = enum_type

    def _parse(self, value: str, /) -> E:
        try:
            return self._enum_type[value.strip().upper()]
        except KeyError:
            enum_values = ', '.join(e.name for e in self._enum_type)
            raise ParsingError(
                f'could not parse value {value!r}'
                f' as {self._enum_type.__name__},'
                f' should be one of {enum_values}')

    def _parse_config(self, value: _t.Any, /) -> E:
        if not isinstance(value, str):
            raise ParsingError('expected a string')
        return self.parse(value)

    def _validate(self, value: E, /):
        pass

    def describe(self) -> _t.Optional[str]:
        desc = '|'.join(e.name for e in self._enum_type)
        return desc

    def describe_value(self, value: E, /) -> _t.Optional[str]:
        return value.name


class Optional(Parser[_t.Optional[T]], _t.Generic[T]):
    """Parser for optional values.

    Interprets empty strings as `None`s.

    """

    def __init__(self, inner: Parser[T], /):
        super().__init__()

        self._inner: Parser[T] = inner

    def _parse(self, value: str, /) -> _t.Optional[T]:
        return self._inner.parse(value)

    def _parse_many(self, value: _t.Sequence[str], /) -> _t.Optional[T]:
        return self._inner.parse_many(value)

    def _parse_config(self, value: _t.Any, /) -> _t.Optional[T]:
        if value is None:
            return None
        return self._inner.parse_config(value)

    def _validate(self, value: _t.Optional[T], /):
        if value is not None:
            self._inner.validate(value)

    def _supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def _supports_parse_optional(self) -> bool:
        return True

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return self._inner.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe_many()

    def describe_value(self, value: _t.Optional[T], /) -> _t.Optional[str]:
        if value is None:
            return '<none>'
        return self._inner.describe_value(value)


class List(Parser[_t.List[T]], _t.Generic[T]):
    """Parser for lists.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse list items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__()

        self._inner: Parser[T] = inner
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def _parse(self, value: str, /) -> _t.List[T]:
        return self.parse_many(value.split(self._delimiter))

    def _parse_many(self, value: _t.Sequence[str], /) -> _t.List[T]:
        return [
            self._inner.parse(item)
            for item in value
        ]

    def _parse_config(self, value: _t.Any, /) -> _t.List[T]:
        if not isinstance(value, list):
            raise ParsingError('expected a list')

        return [
            self._inner.parse_config(item)
            for item in value
        ]

    def _validate(self, value: _t.List[T], /):
        for item in value:
            self._inner.validate(item)

    def _supports_parse_many(self) -> bool:
        return True

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return '*'

    def describe(self) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        value = self._inner.describe_or_def()

        return f'{value}[{delimiter}{value}[{delimiter}...]]'

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_value(self, value: _t.List[T], /) -> _t.Optional[str]:
        return (self._delimiter or ' ').join(
            self._inner.describe_value_or_def(item) for item in value
        )


class Set(Parser[_t.Set[T]], _t.Generic[T]):
    """Parser for sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__()

        self._inner: Parser[T] = inner
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def _parse(self, value: str, /) -> _t.Set[T]:
        return {
            self._inner.parse(item)
            for item in
            value.split(self._delimiter)
        }

    def _parse_many(self, value: _t.Sequence[str], /) -> _t.Set[T]:
        return {
            self._inner.parse(item)
            for item in value
        }

    def _parse_config(self, value: _t.Any, /) -> _t.Set[T]:
        if not isinstance(value, list):
            raise ParsingError('expected a list')

        return {
            self._inner.parse_config(item)
            for item in value
        }

    def _validate(self, value: _t.Set[T], /):
        for item in value:
            self._inner.validate(item)

    def _supports_parse_many(self) -> bool:
        return True

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return '*'

    def describe(self) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        value = self._inner.describe_or_def()

        return f'{value}[{delimiter}{value}[{delimiter}...]]'

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_value(self, value: _t.Set[T], /) -> _t.Optional[str]:
        return (self._delimiter or ' ').join(
            self._inner.describe_value_or_def(item) for item in value
        )


class FrozenSet(Parser[_t.FrozenSet[T]], _t.Generic[T]):
    """Parser for frozen sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__()

        self._inner: Parser[T] = inner
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def _parse(self, value: str, /) -> _t.FrozenSet[T]:
        return frozenset({
            self._inner.parse(item)
            for item in
            value.split(self._delimiter)
        })

    def _parse_many(self, value: _t.Sequence[str], /) -> _t.FrozenSet[T]:
        return frozenset({
            self._inner.parse(item)
            for item in value
        })

    def _parse_config(self, value: _t.Any, /) -> _t.FrozenSet[T]:
        if not isinstance(value, list):
            raise ParsingError('expected a list')

        return frozenset({
            self._inner.parse_config(item)
            for item in value
        })

    def _validate(self, value: _t.FrozenSet[T], /):
        for item in value:
            self._inner.validate(item)

    def _supports_parse_many(self) -> bool:
        return True

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return '*'

    def describe(self) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        value = self._inner.describe_or_def()

        return f'{value}[{delimiter}{value}[{delimiter}...]]'

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_value(self, value: _t.FrozenSet[T], /) -> _t.Optional[str]:
        return (self._delimiter or ' ').join(
            self._inner.describe_value_or_def(item) for item in value
        )


class Dict(Parser[_t.Dict[K, V]], _t.Generic[K, V]):
    """Parser for dicts.

    Will split a string by the given delimiter, and parse each item
    using a :py:class:`Pair` parser.

    :param key:
        inner parser that will be used to parse dict keys.
    :param value:
        inner parser that will be used to parse dict values.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.
    :param pair_delimiter:
        delimiter that will be used to split key-value elements.

    """

    def __init__(
        self,
        key: Parser[K],
        value: Parser[V],
        /,
        *,
        delimiter: _t.Optional[str] = None,
        pair_delimiter: str = ':'
    ):
        super().__init__()

        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

        self._inner = Pair(key, value, delimiter=pair_delimiter)

    def _parse(self, value: str, /) -> _t.Dict[K, V]:
        return self.parse_many(value.split(self._delimiter))

    def _parse_many(self, value: _t.Sequence[str], /) -> _t.Dict[K, V]:
        return dict(self._inner.parse(item) for item in value)

    def _parse_config(self, value: _t.Any, /) -> _t.Dict[K, V]:
        if not isinstance(value, dict):
            raise ParsingError('expected a dict')

        return dict(self._inner.parse_config(item) for item in value)

    def _validate(self, value: _t.Dict[K, V], /):
        for item in value.items():
            self._inner.validate(item)

    def _supports_parse_many(self) -> bool:
        return True

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return '*'

    def describe(self) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        value = self._inner.describe_or_def()

        return f'{value}[{delimiter}{value}[{delimiter}...]]'

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_value(self, value: _t.Dict[K, V], /) -> _t.Optional[str]:
        return (self._delimiter or ' ').join(
            self._inner.describe_value_or_def(item) for item in value.items()
        )


class Pair(Parser[_t.Tuple[K, V]], _t.Generic[K, V]):
    """Parser for key-value pairs.

    :param key:
        inner parser that will be used to parse the first element of the pair.
    :param value:
        inner parser that will be used to parse the second element of the pair.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(
        self,
        key: Parser[K],
        value: Parser[V],
        /,
        *,
        delimiter: _t.Optional[str] = ':'
    ):
        super().__init__()

        self._key = key
        self._value = value
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def _parse(self, value: str, /) -> _t.Tuple[K, V]:
        kv = value.split(self._delimiter, maxsplit=1)
        if len(kv) != 2:
            raise ParsingError('could not parse a key-value pair')

        return (
            self._key.parse(kv[0]),
            self._value.parse(kv[1]),
        )

    def _parse_config(self, value: _t.Any, /) -> _t.Tuple[K, V]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ParsingError('expected a tuple of two elements')

        return (
            self._key.parse_config(value[0]),
            self._value.parse_config(value[1]),
        )

    def _validate(self, value: _t.Tuple[K, V], /):
        self._key.validate(value[0])
        self._value.validate(value[1])

    def describe(self) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        key = self._key.describe_or_def()
        value = self._value.describe_or_def()

        return f'{key}{delimiter}{value}'

    def describe_value(self, value: _t.Tuple[K, V], /) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        key_d = self._key.describe_value_or_def(value[0])
        value_d = self._value.describe_value_or_def(value[1])

        return f'{key_d}{delimiter}{value_d}'


class Tuple(Parser[TU], _t.Generic[TU]):
    """Parser for tuples of fixed lengths.

    :param parsers:
        parsers for each tuple element.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(
        self,
        *parsers: Parser[_t.Any],
        delimiter: _t.Optional[str] = None
    ):
        super().__init__()

        if len(parsers) == 0:
            raise ValueError('empty tuple')
        self._parsers = parsers
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def _parse(self, value: str, /) -> TU:
        items = value.split(self._delimiter, maxsplit=len(self._parsers) - 1)
        return self.parse_many(items)

    def _parse_many(self, value: _t.Sequence[str], /) -> TU:
        if len(value) != len(self._parsers):
            raise ParsingError(f'expected {len(self._parsers)} element(s)')

        return _t.cast(TU, tuple(
            parser.parse(item) for parser, item in zip(self._parsers, value)
        ))

    def _parse_config(self, value: _t.Any, /) -> TU:
        if not isinstance(value, (list, tuple)):
            raise ParsingError('expected a list or a tuple')
        elif len(value) != len(self._parsers):
            raise ParsingError(f'expected {len(self._parsers)} element(s)')

        return _t.cast(TU, tuple(
            parser.parse_config(item)
            for parser, item in zip(self._parsers, value)
        ))

    def _validate(self, value: TU, /):
        for parser, item in zip(self._parsers, value):
            parser.validate(item)

    def _supports_parse_many(self) -> bool:
        return True

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return len(self._parsers)

    def describe(self) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        desc = [parser.describe_or_def() for parser in self._parsers]

        return delimiter.join(desc)

    def describe_many(self) -> _t.Optional[str]:
        return None

    def describe_value(self, value: TU, /) -> _t.Optional[str]:
        delimiter = self._delimiter or ' '
        desc = [
            parser.describe_value_or_def(item)
            for parser, item in zip(self._parsers, value)
        ]

        return delimiter.join(desc)


class DateTime(Parser[datetime.datetime]):
    """Parse a datetime in ISO ('YYYY-MM-DD HH:MM:SS') format.

    """

    def _parse(self, value: str, /) -> datetime.datetime:
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as a datetime')

    def _parse_config(self, value: _t.Any, /) -> datetime.datetime:
        if isinstance(value, datetime.datetime):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f'expected a datetime')

    def _validate(self, value: datetime.datetime, /):
        pass


class Date(Parser[datetime.date]):
    """Parse a date in ISO ('YYYY-MM-DD') format.

    """

    def _parse(self, value: str, /) -> datetime.date:
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as a date')

    def _parse_config(self, value: _t.Any, /) -> datetime.date:
        if isinstance(value, datetime.datetime):
            return value.date()
        elif isinstance(value, datetime.date):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f'expected a date')

    def _validate(self, value: datetime.date, /):
        pass


class Time(Parser[datetime.time]):
    """Parse a date in ISO ('HH:MM:SS') format.

    """

    def _parse(self, value: str, /) -> datetime.time:
        try:
            return datetime.time.fromisoformat(value)
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as a time')

    def _parse_config(self, value: _t.Any, /) -> datetime.time:
        if isinstance(value, datetime.datetime):
            return value.time()
        elif isinstance(value, datetime.time):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f'expected a time')

    def _validate(self, value: datetime.time, /):
        pass


class TimeDelta(Parser[datetime.timedelta]):
    """Parse a time delta.

    """

    _UNITS_MAP = (
        ('days', ('d', 'day', 'days')),
        ('seconds', ('s', 'sec', 'secs', 'second', 'seconds')),
        ('microseconds', ('us', 'u', 'micro', 'micros', 'microsecond', 'microseconds')),
        ('milliseconds', ('ms', 'l', 'milli', 'millis', 'millisecond', 'milliseconds')),
        ('minutes', ('m', 'min', 'mins', 'minute', 'minutes')),
        ('hours', ('h', 'hr', 'hrs', 'hour', 'hours')),
        ('weeks', ('w', 'week', 'weeks')),
    )

    _UNITS = {unit: name for name, units in _UNITS_MAP for unit in units}

    _TIMEDELTA_RE = re.compile(
        r'^'
        r'(?:([+-]?)\s*((?:\d+\s*[a-z]+\s*)+))?'
        r'(?:([+-]?)\s*(\d\d:\d\d(?::\d\d(?:\.\d{3}\d{3}?)?)?))?'
        r'$',
        re.IGNORECASE,
    )

    _COMPONENT_RE = re.compile(
        r'(\d+)\s*([a-z]+)\s*'
    )

    def _parse(self, value: str, /) -> datetime.timedelta:
        value = value.strip()

        if not value:
            raise ParsingError('got an empty timedelta')

        if match := self._TIMEDELTA_RE.match(value):
            c_sign_s, components_s, t_sign_s, time_s = match.groups()
        else:
            raise ParsingError(
                f'could not parse value {value!r} as a timedelta'
            )

        c_sign_s = -1 if c_sign_s == '-' else 1
        t_sign_s = -1 if t_sign_s == '-' else 1

        kwargs = {u: 0 for u, _ in self._UNITS_MAP}

        if components_s:
            for (num, unit) in self._COMPONENT_RE.findall(components_s):
                if unit_key := self._UNITS.get(unit.lower()):
                    kwargs[unit_key] += int(num)
                else:
                    raise ParsingError(
                        f'could not parse value {value!r} as a timedelta: '
                        f'unknown unit {unit!r}'
                    )

        timedelta = c_sign_s * datetime.timedelta(**kwargs)

        if time_s:
            time = datetime.time.fromisoformat(time_s)
            timedelta += t_sign_s * datetime.timedelta(
                hours=time.hour,
                minutes=time.minute,
                seconds=time.second,
                microseconds=time.microsecond
            )

        return timedelta

    def _parse_config(self, value: _t.Any, /) -> datetime.timedelta:
        if isinstance(value, datetime.timedelta):
            return value
        elif isinstance(value, str):
            return self.parse(value)
        else:
            raise ParsingError(f'expected a timedelta')

    def _validate(self, value: datetime.timedelta, /):
        pass


class Path(Parser[pathlib.Path]):
    """Parse a file system path, return a :class:`pathlib.Path`.

    :param extensions: list of allowed file extensions.

    """

    def __init__(
        self,
        extensions: _t.Optional[_t.Collection[str]] = None,
    ):
        super().__init__()

        self._extensions = extensions

    def _parse(self, value: str, /) -> pathlib.Path:
        return pathlib.Path(value).expanduser().resolve()

    def _parse_config(self, value: _t.Any, /) -> pathlib.Path:
        if not isinstance(value, str):
            raise ParsingError('expected a string')
        return self.parse(value)

    def _validate(self, value: pathlib.Path, /):
        if self._extensions is not None:
            if not any(value.name.endswith(ext) for ext in self._extensions):
                exts = ', '.join(self._extensions)
                raise ParsingError(f'{value} should have extension {exts}')

    def describe(self) -> _t.Optional[str]:
        if self._extensions is not None:
            return '|'.join('*' + e for e in self._extensions)
        else:
            return None


class NonExistentPath(Path):
    """Parse a file system path and verify that it doesn't exist.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if value.exists():
            raise ParsingError(f'{value} already exist')


class ExistingPath(Path):
    """Parse a file system path and verify that it exists.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.exists():
            raise ParsingError(f'{value} doesn\'t exist')


class File(ExistingPath):
    """Parse path to a file.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_file():
            raise ParsingError(f'{value} is not a file')


class Dir(ExistingPath):
    """Parse path to a directory.

    """

    def __init__(self):
        # Disallow passing `extensions`.
        super().__init__()

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.is_dir():
            raise ParsingError(f'{value} is not a directory')


class GitRepo(Dir):
    """Parse path to a git repository.

    This parser just checks that the given directory has
    a subdirectory named ``.git``.

    """

    def _validate(self, value: pathlib.Path, /):
        super()._validate(value)

        if not value.joinpath('.git').is_dir():
            raise ParsingError(f'{value} is not a git repository')

        return value


class _BoundImpl(Parser[T], _t.Generic[T, Cmp]):
    _Self = _t.TypeVar('_Self', bound='_BoundImpl')

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
        super().__init__()

        self._inner: Parser[T] = inner

        self._lower: _t.Optional[Cmp] = None
        self._lower_inclusive: bool = True
        self._upper: _t.Optional[Cmp] = None
        self._upper_inclusive: bool = True

        if lower is not None and lower_inclusive is not None:
            raise TypeError(
                'lower and lower_inclusive cannot be given at the same time')
        elif lower is not None:
            self._lower = lower
            self._lower_inclusive = False
        elif lower_inclusive is not None:
            self._lower = lower_inclusive
            self._lower_inclusive = True

        if upper is not None and upper_inclusive is not None:
            raise TypeError(
                'upper and upper_inclusive cannot be given at the same time')
        elif upper is not None:
            self._upper = upper
            self._upper_inclusive = False
        elif upper_inclusive is not None:
            self._upper = upper_inclusive
            self._upper_inclusive = True

        self._mapper = mapper
        self._desc = desc

    def _parse(self, value: str, /) -> T:
        return self._inner.parse(value)

    def _parse_many(self, value: _t.Sequence[str], /) -> T:
        return self._inner.parse_many(value)

    def _parse_config(self, value: _t.Any, /) -> T:
        return self._inner.parse_config(value)

    def _validate(self, value: T, /):
        self._inner.validate(value)

        mapped = self._mapper(value)

        if self._lower is not None:
            if self._lower_inclusive and mapped < self._lower:
                raise ParsingError(
                    f'{self._desc} should be greater or equal to {self._lower},'
                    f' got {value} instead')
            elif not self._lower_inclusive and mapped <= self._lower:
                raise ParsingError(
                    f'{self._desc} should be greater than {self._lower},'
                    f' got {value} instead')

        if self._upper is not None:
            if self._upper_inclusive and mapped > self._upper:
                raise ParsingError(
                    f'{self._desc} should be lesser or equal to {self._upper},'
                    f' got {value} instead')
            elif not self._upper_inclusive and mapped >= self._upper:
                raise ParsingError(
                    f'{self._desc} should be lesser than {self._upper},'
                    f' got {value} instead')

    def _supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def _supports_parse_optional(self) -> bool:
        return self._inner.supports_parse_optional()

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return self._inner.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe_many()

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        return self._inner.describe_value(value)


class Bound(_BoundImpl[Cmp, Cmp], _t.Generic[Cmp]):
    """Check that value is upper- or lower-bound by some constraints.

    :param inner:
        inner parser that will be used to actually parse a value before
        checking its bounds.
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

    def __init__(
        self,
        inner: Parser[Cmp],
        /,
        *,
        lower: _t.Optional[Cmp] = None,
        lower_inclusive: _t.Optional[Cmp] = None,
        upper: _t.Optional[Cmp] = None,
        upper_inclusive: _t.Optional[Cmp] = None
    ):
        super().__init__(
            inner,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
            mapper=lambda x: x,
            desc='value'
        )


class LenBound(_BoundImpl[Sz, int], _t.Generic[Sz]):
    """Check that length of a value is upper- or lower-bound by some constraints.

    The interface is exactly like one of the :class:`Bound` parser.

    """

    def __init__(
        self,
        inner: Parser[Sz],
        /,
        *,
        lower: _t.Optional[int] = None,
        lower_inclusive: _t.Optional[int] = None,
        upper: _t.Optional[int] = None,
        upper_inclusive: _t.Optional[int] = None
    ):
        super().__init__(
            inner,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
            mapper=len,
            desc='length of a value'
        )

    def _get_nargs(self) -> _t.Union[str, int, None]:
        if not self._inner.supports_parse_many():
            # somebody bound len of a string?
            return self._inner.get_nargs()

        lower = self._lower
        if lower is not None and not self._lower_inclusive:
            lower += 1
        upper = self._upper
        if upper is not None and not self._upper_inclusive:
            upper -= 1

        if lower == upper:
            return lower
        elif lower is not None and lower > 0:
            return '+'
        else:
            return '*'


class OneOf(Parser[T], _t.Generic[T]):
    """Check that the parsed value is one of the given set of values.

    """

    def __init__(self, inner: Parser[T], values: _t.Collection[T], /):
        super().__init__()

        self._inner: Parser[T] = inner
        self._allowed_values = values

    def _parse(self, value: str, /) -> T:
        return self._inner.parse(value)

    def _parse_many(self, value: _t.Sequence[str], /) -> T:
        return self._inner.parse_many(value)

    def _parse_config(self, value: _t.Any, /) -> T:
        return self._inner.parse_config(value)

    def _validate(self, value: T, /):
        self._inner.validate(value)

        if value not in self._allowed_values:
            values = ', '.join(map(str, self._allowed_values))
            raise ParsingError(
                f'could not parse value {value!r},'
                f' should be one of {values}')

    def _supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def _supports_parse_optional(self) -> bool:
        return self._inner.supports_parse_optional()

    def _get_nargs(self) -> _t.Union[str, int, None]:
        return self._inner.get_nargs()

    def describe(self) -> _t.Optional[str]:
        desc = '|'.join(self.describe_value_or_def(e) for e in self._allowed_values)
        if len(desc) < 80:
            return desc
        else:
            return super().describe()

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        return self._inner.describe_value(value)


_FromTypeHintCallback = _t.Callable[
    [_t.Type, _t.Optional[_t.Any], _t.Tuple[_t.Any, ...]],
    _t.Optional['Parser[_t.Any]']
]

_FROM_TYPE_HINT_CALLBACKS: _t.List[_FromTypeHintCallback] = []


def from_type_hint(ty: _t.Type[T], /) -> 'Parser[T]':
    """Create parser from a type hint.

    """

    if isinstance(ty, str) or isinstance(ty, _t.ForwardRef):
        raise TypeError(f'forward references are not supported here: {ty}')

    origin = _t.get_origin(ty)
    args = _t.get_args(ty)

    for cb in _FROM_TYPE_HINT_CALLBACKS:
        p = cb(ty, origin, args)
        if p is not None:
            return p

    raise TypeError(f'unsupported type {ty}')


def register_type_hint_conversion(
    cb: _FromTypeHintCallback
) -> _FromTypeHintCallback:
    """Register a new converter from typehint to a parser.

    This function takes a callback that accepts three positional arguments:

    - a type hint,
    - a type hint's origin (as defined by :func:`typing.get_origin`),
    - a type hint's args (as defined by :func:`typing.get_args`).

    The callback should return a parser if it can, or `None` otherwise.

    All registered callbacks are tried in the same order
    as the were registered.

    This function can be used as a decorator.

    """

    _FROM_TYPE_HINT_CALLBACKS.append(cb)
    return cb


register_type_hint_conversion(
    lambda ty, origin, args:
        Optional(from_type_hint(args[1 - args.index(type(None))]))
        if origin is _t.Union and len(args) == 2 and type(None) in args
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Str()
        if ty is str
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Int()
        if ty is int
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Float()
        if ty is float
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Bool()
        if ty is bool
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Enum(ty)
        if isinstance(ty, type) and issubclass(ty, enum.Enum)
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        List(from_type_hint(args[0]))
        if origin is list
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Set(from_type_hint(args[0]))
        if origin is set
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        FrozenSet(from_type_hint(args[0]))
        if origin is frozenset
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Dict(from_type_hint(args[0]), from_type_hint(args[1]))
        if origin is dict
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Tuple(*map(from_type_hint, args))
        if origin is tuple and ... not in args
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
        Path()
        if isinstance(ty, type) and issubclass(ty, pathlib.PurePath)
        else None
)
register_type_hint_conversion(
    lambda ty, origin, args:
    DateTime()
    if origin is datetime.datetime
    else None
)

register_type_hint_conversion(
    lambda ty, origin, args:
    Date()
    if origin is datetime.date
    else None
)

register_type_hint_conversion(
    lambda ty, origin, args:
    Time()
    if origin is datetime.time
    else None
)

register_type_hint_conversion(
    lambda ty, origin, args:
    TimeDelta()
    if origin is datetime.timedelta
    else None
)
