# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Everything to do with parsing user input.

Use provided classes to construct parsers and add validation::

    # Parses a non-empty list of strings.
    parser = yuio.parse.List(yuio.parse.Str()).len_ge(1)

Pass a parser to other yuio functions::

    mods = yuio.io.ask('List of modules to reformat', parser=parser)

Or parse strings yourself::

    mods = parser.parse('sys os enum dataclasses')


Using a parser
--------------

..

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

.. autoclass:: Parser

   .. automethod:: parse

   .. automethod:: parse_many

   .. automethod:: supports_parse_many

   .. automethod:: parse_config

   .. automethod:: get_nargs

   .. automethod:: describe

   .. automethod:: describe_or_def

   .. automethod:: describe_many

   .. automethod:: describe_many_or_def

   .. automethod:: describe_value

   .. automethod:: describe_value_or_def

   .. automethod:: _parse

   .. automethod:: _parse_many

   .. automethod:: _supports_parse_many

   .. automethod:: _parse_config

   .. automethod:: _validate

   .. automethod:: _get_nargs


.. autoclass:: ParsingError


Value parsers
-------------

.. autoclass:: Str
   :members:

.. autoclass:: Int

.. autoclass:: Float

.. autoclass:: Bool

.. autoclass:: Enum

.. autoclass:: List

.. autoclass:: Set

.. autoclass:: FrozenSet

.. autoclass:: Dict

.. autoclass:: Pair

.. autoclass:: Tuple(*parsers: Parser[typing.Any], delimiter: typing.Optional[str] = None)


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

.. autoclass:: LenBound

.. autoclass:: OneOf


Deriving parsers from type hints
--------------------------------

There is a way to automatically derive basic parsers from type hints
(used by :mod:`yuio.config`):

.. autofunction:: from_type_hint

To extend capabilities of the automatic converter,
you can register your own types and parsers:

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
U = _t.TypeVar('U')
K = _t.TypeVar('K')
V = _t.TypeVar('V')
C = _t.TypeVar('C', bound=_t.Collection)
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
    def _parse_many(self, value: _t.Sequence[str], /) -> T:
        """Implementation of :meth:`~Parser.parse_many`.

        """

    @abc.abstractmethod
    def _supports_parse_many(self) -> bool:
        """Implementation of :meth:`~Parser.supports_parse_many`.

        """

    @abc.abstractmethod
    def _parse_config(self, value: _t.Any, /) -> T:
        """Implementation of :meth:`~Parser.parse_config`.

        """

    @abc.abstractmethod
    def _validate(self, value: T, /):
        """Validation for parsed value.

        """

    @_t.final
    def parse(self, value: str, /) -> T:
        """Parse and validate user input,
        raise :class:`ParsingError` on failure.

        """

        parsed = self._parse(value)
        self._validate(parsed)
        return parsed

    @_t.final
    def parse_many(self, value: _t.Sequence[str], /) -> T:
        """For collection parsers, parse and validate collection
        by parsing its items one-by-one.

        Example::

            # Let's say we're parsing a set of ints...
            parser = Set(Int())

            # And the user enters collection items one-by-one.
            user_input = ['1', '2', '3']

            # We can parse collection from its items:
            result = parser.parse_many(user_input)

        """

        parsed = self._parse_many(value)
        self._validate(parsed)
        return parsed

    @_t.final
    def supports_parse_many(self) -> bool:
        """Return true if this parser returns a collection
        and so supports :meth:`~Parser.parse_many`.

        """

        return self._supports_parse_many()

    @_t.final
    def parse_config(self, value: _t.Any, /) -> T:
        """Parse and validate value from a config,
        raise :class:`ParsingError` on failure.

        This method accepts python values.
        Use it to parse json configs and similar.

        """

        parsed = self._parse_config(value)
        self._validate(parsed)
        return parsed

    @abc.abstractmethod
    def get_nargs(self) -> _t.Union[str, int, None]:
        """Generate `nargs` for argparse.

        """

    @abc.abstractmethod
    def describe(self) -> _t.Optional[str]:
        """Return a human-readable description of an expected input.

        """

        return None

    @abc.abstractmethod
    def describe_or_def(self) -> str:
        """Like :py:meth:`~Parser.describe`,
        but guaranteed to return something.

        """

    @abc.abstractmethod
    def describe_many(self) -> _t.Optional[str]:
        """Return a human-readable description of a container element.

        Used with :meth:`~Parser.parse_many`.

        """

    @abc.abstractmethod
    def describe_many_or_def(self) -> str:
        """Like :py:meth:`~Parser.describe_many`,
        but guaranteed to return something.

        """

    @abc.abstractmethod
    def describe_value(self, value: T, /) -> _t.Optional[str]:
        """Return a human-readable description of a given value.

        """

    @abc.abstractmethod
    def describe_value_or_def(self, value: T, /) -> str:
        """Like :py:meth:`~Parser.describe_value`,
        but guaranteed to return something.

        """

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

        See :class:`LenBound` for more info.

        """

        return LenBound(
            self,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive,
        )


    @_t.overload
    def len_between(self: 'Parser[Sz]', upper: int, /) -> 'LenBound[Sz]': ...

    @_t.overload
    def len_between(self: 'Parser[Sz]', lower: int, upper: int, /) -> 'LenBound[Sz]': ...

    @_t.final
    def len_between(self: 'Parser[Sz]', *args: int) -> 'LenBound[Sz]':
        """Check that length of the value is within the given range.

        See :class:`LenBound` for more info.
        
        """
        
        if len(args) == 1:
            lower, upper = None, args[0]
        elif len(args) == 2:
            lower, upper = args
        else:
            raise TypeError(f'len_between() takes 1 or 2 arguments ({len(args)} given)')
        return self.len_bound(lower_inclusive=lower, upper=upper)

    @_t.final
    def len_gt(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is greater then
        the given bound.

        See :class:`LenBound` for more info.

        """

        return self.len_bound(lower=bound)

    @_t.final
    def len_ge(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is greater then or equal to
        the given bound.

        See :class:`LenBound` for more info.

        """

        return self.len_bound(lower_inclusive=bound)

    @_t.final
    def len_lt(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is lesser then
        the given bound.

        See :class:`LenBound` for more info.

        """

        return self.len_bound(upper=bound)

    @_t.final
    def len_le(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is lesser then or equal to
        the given bound.

        See :class:`LenBound` for more info.

        """

        return self.len_bound(upper_inclusive=bound)

    @_t.final
    def len_eq(self: 'Parser[Sz]', bound: int, /) -> 'LenBound[Sz]':
        """Check that length of the value is equal to
        the given bound.

        See :class:`LenBound` for more info.

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


class _ValueParser(Parser[T], _t.Generic[T]):
    """Base implementation for a parser that returns a single value.
    
    """
    
    @_t.final
    def _parse_many(self, value: _t.Sequence[str], /) -> T:
        raise RuntimeError('unable to parse multiple values')

    @_t.final
    def _supports_parse_many(self) -> bool:
        return False

    @_t.final
    def get_nargs(self) -> _t.Union[str, int, None]:
        return None

    def describe(self) -> _t.Optional[str]:
        return None

    def describe_or_def(self) -> str:
        return (
            self.describe()
            or yuio._utils.to_dash_case(self.__class__.__name__)
        )

    def describe_many(self) -> _t.Optional[str]:
        return self.describe()

    def describe_many_or_def(self) -> str:
        return (
            self.describe_many()
            or yuio._utils.to_dash_case(self.__class__.__name__)
        )

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        return None

    def describe_value_or_def(self, value: T, /) -> str:
        return self.describe_value(value) or str(value)


class _WrappingParser(Parser[T], _t.Generic[T, U]):
    """Base implementation for a parser that wraps another parser.

    :tparam T: return type of the parser.
    :tparam U: return type of the wrapped parser.
    
    """

    def __init__(self, inner: Parser[U]):
        super().__init__()

        self._inner = inner


class _SimpleWrappingParser(_WrappingParser[T, T], _t.Generic[T]):
    def _parse(self, value: str, /) -> T:
        return self._inner.parse(value)

    def _parse_many(self, value: _t.Sequence[str], /) -> T:
        return self._inner.parse_many(value)

    def _supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def _parse_config(self, value: _t.Any, /) -> T:
        return self._inner.parse_config(value)

    def _validate(self, value: T, /):
        self._inner._validate(value)

    def get_nargs(self) -> _t.Union[str, int, None]:
        return self._inner.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe_many()

    def describe_many_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        return self._inner.describe_value(value)

    def describe_value_or_def(self, value: T, /) -> str:
        return self._inner.describe_value_or_def(value)


class Str(_ValueParser[str]):
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

    # def regex(self, regex: _t.Union[str, re.Pattern], /, group: _t.Union[int, str] = 0) -> 'Str':
    #     """Matches the parsed string with the given regular expression,
    #     can return a group of .

    #     """

    #     if isinstance(regex, re.Pattern):
    #         compiled = regex
    #     else:
    #         compiled = re.compile(regex)

    #     def mapper(value: str) -> str:
    #         if (match := compiled.match(value)) is None:
    #             raise ParsingError(
    #                 f'value should match regex \'{compiled.pattern}\'')
    #         return match.group(group)

    #     return Str(*self._modifiers, mapper)


class Int(_ValueParser[int]):
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


class Float(_ValueParser[float]):
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


class Bool(_ValueParser[bool]):
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


class Enum(_ValueParser[E], _t.Generic[E]):
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


class Optional(_WrappingParser[_t.Optional[T], T], _t.Generic[T]):
    """Parser for optional values.

    Interprets empty strings as `None`s.

    """

    def _parse(self, value: str, /) -> _t.Optional[T]:
        return self._inner.parse(value)

    def _parse_many(self, value: _t.Sequence[str], /) -> _t.Optional[T]:
        return self._inner.parse_many(value)

    def _supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def _parse_config(self, value: _t.Any, /) -> _t.Optional[T]:
        if value is None:
            return None
        return self._inner.parse_config(value)

    def _validate(self, value: _t.Optional[T], /):
        if value is not None:
            self._inner._validate(value)

    def get_nargs(self) -> _t.Union[str, int, None]:
        return self._inner.get_nargs()

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe_many()

    def describe_many_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_value(self, value: _t.Optional[T], /) -> _t.Optional[str]:
        if value is None:
            return '<none>'
        return self._inner.describe_value(value)

    def describe_value_or_def(self, value: _t.Optional[T], /) -> _t.Optional[str]:
        if value is None:
            return '<none>'
        return self._inner.describe_value_or_def(value)


class _Collection(_WrappingParser[C, T], _t.Generic[C, T]):
    def __init__(
        self,
        inner: Parser[T],
        ctor: _t.Callable[[_t.Iterable[T]], C],
        /,
        *,
        config_type: type = list,
        config_type_iter: _t.Callable[[C], _t.Iterable[T]] = iter,
        delimiter: _t.Optional[str] = None
    ):
        super().__init__(inner)

        self._ctor = ctor
        self._config_type = config_type
        self._config_type_iter = config_type_iter
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def _parse(self, value: str, /) -> C:
        return self.parse_many(value.split(self._delimiter))

    def _parse_many(self, value: _t.Sequence[str], /) -> C:
        return self._ctor(
            self._inner.parse(item)
            for item in value
        )

    def _supports_parse_many(self) -> bool:
        return True

    def _parse_config(self, value: _t.Any, /) -> C:
        if not isinstance(value, self._config_type):
            raise ParsingError(f'expected a {self._config_type.__name__}')

        return self._ctor(
            self._inner.parse_config(item)
            for item in self._config_type_iter(value)
        )

    def _validate(self, value: C, /):
        for item in self._config_type_iter(value):
            self._inner._validate(item)

    def get_nargs(self) -> _t.Union[str, int, None]:
        return '*'

    def describe(self) -> _t.Optional[str]:
        return self.describe_or_def()

    def describe_or_def(self) -> str:
        delimiter = self._delimiter or ' '
        value = self._inner.describe_or_def()

        return f'{value}[{delimiter}{value}[{delimiter}...]]'

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_many_or_def(self) -> str:
        return self._inner.describe_or_def()

    def describe_value(self, value: C, /) -> _t.Optional[str]:
        return self.describe_value_or_def(value)

    def describe_value_or_def(self, value: C, /) -> str:
        return (self._delimiter or ' ').join(
            self._inner.describe_value_or_def(item)
            for item in self._config_type_iter(value)
        )


class List(_Collection[_t.List[T], T], _t.Generic[T]):
    """Parser for lists.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse list items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__(inner, list, delimiter=delimiter)


class Set(_Collection[_t.Set[T], T], _t.Generic[T]):
    """Parser for sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__(inner, set, delimiter=delimiter)


class FrozenSet(_Collection[_t.FrozenSet[T], T], _t.Generic[T]):
    """Parser for frozen sets.

    Will split a string by the given delimiter, and parse each item
    using a subparser.

    :param inner:
        inner parser that will be used to parse set items.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, inner: Parser[T], /, *, delimiter: _t.Optional[str] = None):
        super().__init__(inner, frozenset, delimiter=delimiter)


class Dict(_Collection[_t.Dict[K, V], _t.Tuple[K, V]], _t.Generic[K, V]):
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
        inner = Pair(key, value, delimiter=pair_delimiter)

        super().__init__(
            inner,
            dict,
            config_type=dict,
            config_type_iter=dict.items,
            delimiter=delimiter
        )


class Pair(_ValueParser[_t.Tuple[K, V]], _t.Generic[K, V]):
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
        self._key._validate(value[0])
        self._value._validate(value[1])

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

    T1 = _t.TypeVar('T1')
    T2 = _t.TypeVar('T2')
    T3 = _t.TypeVar('T3')
    T4 = _t.TypeVar('T4')
    T5 = _t.TypeVar('T5')
    T6 = _t.TypeVar('T6')
    T7 = _t.TypeVar('T7')
    T8 = _t.TypeVar('T8')
    T9 = _t.TypeVar('T9')

    @_t.overload
    def __new__(cls, p1: Parser[T1], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], p4: Parser[T4], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3, T4]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], p4: Parser[T4], p5: Parser[T5], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3, T4, T5]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], p4: Parser[T4], p5: Parser[T5], p6: Parser[T6], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], p4: Parser[T4], p5: Parser[T5], p6: Parser[T6], p7: Parser[T7], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], p4: Parser[T4], p5: Parser[T5], p6: Parser[T6], p7: Parser[T7], p8: Parser[T8], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7, T8]]': ...
    @_t.overload
    def __new__(cls, p1: Parser[T1], p2: Parser[T2], p3: Parser[T3], p4: Parser[T4], p5: Parser[T5], p6: Parser[T6], p7: Parser[T7], p8: Parser[T8], p9: Parser[T9], /, delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[T1, T2, T3, T4, T5, T6, T7, T8, T9]]': ...
    @_t.overload
    def __new__(cls, *parsers: Parser[_t.Any], delimiter: _t.Optional[str] = None) -> 'Tuple[_t.Tuple[_t.Any, ...]]': ...

    def __new__(cls, *args, **kwargs) -> _t.Any:
        return super().__new__(cls)

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
            parser._validate(item)

    def _supports_parse_many(self) -> bool:
        return True

    def get_nargs(self) -> _t.Union[str, int, None]:
        return len(self._parsers)

    def describe(self) -> _t.Optional[str]:
        return self.describe_or_def()
    
    def describe_or_def(self) -> str:
        delimiter = self._delimiter or ' '
        desc = [parser.describe_or_def() for parser in self._parsers]

        return delimiter.join(desc)

    def describe_many(self) -> _t.Optional[str]:
        descriptions = set(parser.describe() for parser in self._parsers)
        if len(descriptions) == 1:
            return descriptions.pop()
        else:
            return None

    def describe_many_or_def(self) -> str:
        descriptions = set(parser.describe_or_def() for parser in self._parsers)
        if len(descriptions) == 1:
            return descriptions.pop()
        else:
            return 'value'

    def describe_value(self, value: TU, /) -> _t.Optional[str]:
        return self.describe_value_or_def(value)

    def describe_value_or_def(self, value: TU, /) -> str:
        delimiter = self._delimiter or ' '
        desc = [
            parser.describe_value_or_def(item)
            for parser, item in zip(self._parsers, value)
        ]

        return delimiter.join(desc)


class DateTime(_ValueParser[datetime.datetime]):
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


class Date(_ValueParser[datetime.date]):
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


class Time(_ValueParser[datetime.time]):
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


class TimeDelta(_ValueParser[datetime.timedelta]):
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


class Path(_ValueParser[pathlib.Path]):
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


class _BoundImpl(_SimpleWrappingParser[T], _t.Generic[T, Cmp]):
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
        super().__init__(inner)

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

    def _validate(self, value: T, /):
        self._inner._validate(value)

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

    def get_nargs(self) -> _t.Union[str, int, None]:
        if not self._inner.supports_parse_many():
            # somebody bound len of a string?
            return self._inner.get_nargs()

        lower_inclusive = self._lower_inclusive
        if lower_inclusive is None and self._lower is not None:
            lower_inclusive = self._lower + 1
        upper_inclusive = self._upper_inclusive
        if upper_inclusive is None and self._upper is not None:
            upper_inclusive = self._upper - 1

        if lower_inclusive == upper_inclusive:
            return lower_inclusive
        elif lower_inclusive is not None and lower_inclusive > 0:
            return '+'
        else:
            return '*'


class OneOf(_SimpleWrappingParser[T], _t.Generic[T]):
    """Check that the parsed value is one of the given set of values.

    """

    def __init__(self, inner: Parser[T], values: _t.Collection[T], /):
        super().__init__(inner)

        self._allowed_values = values

    def _validate(self, value: T, /):
        self._inner._validate(value)

        if value not in self._allowed_values:
            values = ', '.join(map(str, self._allowed_values))
            raise ParsingError(
                f'could not parse value {value!r},'
                f' should be one of {values}')

    def describe(self) -> _t.Optional[str]:
        desc = '|'.join(self.describe_value_or_def(e) for e in self._allowed_values)
        if len(desc) < 80:
            return desc
        else:
            return super().describe()


# class Regex(Parser[str]):
#     def __init__(self, inner: Parser[str], regex: _t.Union[str, re.Pattern]):
#         super().__init__()

#         self._inner = inner
#         if not isinstance(regex, re.Pattern):
#             regex = re.compile(regex)
#         self._regex = regex
    



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
