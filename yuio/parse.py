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

   .. automethod:: lower_bound

   .. automethod:: lower_bound_inclusive

   .. automethod:: upper_bound

   .. automethod:: upper_bound_inclusive

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
import enum
import pathlib
import re
import typing as _t


_TO_DASH_CASE_RE = re.compile(
    r'(?<!^)((?=[A-Z]([^A-Z]|$))|(?<=\d)(?=[A-Z])|(?<!\d)(?=\d))'
)


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
T1 = _t.TypeVar('T1')
T2 = _t.TypeVar('T2')
T3 = _t.TypeVar('T3')
T4 = _t.TypeVar('T4')
T5 = _t.TypeVar('T5')
T6 = _t.TypeVar('T6')
T7 = _t.TypeVar('T7')
T8 = _t.TypeVar('T8')
T9 = _t.TypeVar('T9')
T10 = _t.TypeVar('T10')


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

    def __call__(self, value: str, /) -> T:
        """Parse and verify user input, raise :class:`ParsingError` on failure.

        """

        parsed = self.parse(value)
        self.validate(parsed)
        return parsed

    @abc.abstractmethod
    def parse(self, value: str, /) -> T:
        """Parse user input, raise :class:`ParsingError` on failure.

        Don't forget to call :meth:`Parser.validate` after parsing a value.

        """

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        """Parse a list of user inputs by sending them to an inner parser
        one-by-one, and then uniting parsed values into a collection.

        Used with argparse for actions with ``nargs`` set
        to allow multiple values.

        """

        raise ParsingError('unable to parse multiple values')

    def supports_parse_many(self) -> bool:
        """Returns true if this parser returns a collection
        and so supports :meth:`~Parser.parse_many`.

        """

        return False

    @abc.abstractmethod
    def parse_config(self, value: _t.Any, /) -> T:
        """Parse value from a config, raise :class:`ParsingError` on failure.

        This method accepts python values, i.e. when parsing a json config.

        Don't forget to call :meth:`Parser.validate` after parsing a value.

        """

    @abc.abstractmethod
    def validate(self, value: T, /):
        """Verify parsed value, raise :class:`ParsingError` on failure.

        """

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
            or _TO_DASH_CASE_RE.sub('-', self.__class__.__name__).lower()
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
            or _TO_DASH_CASE_RE.sub('-', self.__class__.__name__).lower()
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


class Str(Parser[str]):
    """Parser for str values.

    Applies a `modifiers` to the value, in order they are given.

    """

    _Self = _t.TypeVar('_Self', bound='Str')

    def __init__(self, *modifiers: _t.Callable[[str], str]):
        super().__init__()

        self._modifiers = list(modifiers)

    def parse(self, value: str, /) -> str:
        for modifier in self._modifiers:
            value = modifier(value)
        return value

    def parse_config(self, value: _t.Any, /) -> str:
        if not isinstance(value, str):
            raise ParsingError('expected a string')
        for modifier in self._modifiers:
            value = modifier(value)
        return value

    def validate(self, value: str, /):
        pass

    def lower(self: _Self) -> _Self:
        """Applies :meth:`str.lower` to all parsed strings.

        """

        self._modifiers.append(str.lower)
        return self

    def upper(self: _Self) -> _Self:
        """Applies :meth:`str.upper` to all parsed strings.

        """

        self._modifiers.append(str.upper)
        return self

    def strip(self: _Self, char: _t.Optional[str] = None, /) -> _Self:
        """Applies :meth:`str.strip` to all parsed strings.

        """

        self._modifiers.append(lambda s: s.strip(char))
        return self

    def lstrip(self: _Self, char: _t.Optional[str] = None, /) -> _Self:
        """Applies :meth:`str.lstrip` to all parsed strings.

        """

        self._modifiers.append(lambda s: s.lstrip(char))
        return self

    def rstrip(self: _Self, char: _t.Optional[str] = None, /) -> _Self:
        """Applies :meth:`str.rstrip` to all parsed strings.

        """

        self._modifiers.append(lambda s: s.rstrip(char))
        return self


class Int(Parser[int]):
    """Parser for int values.

    """

    def parse(self, value: str, /) -> int:
        try:
            return int(value.strip())
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as an int')

    def parse_config(self, value: _t.Any, /) -> int:
        if isinstance(value, float):
            if value != int(value):
                raise ParsingError('expected an int, got a float instead')
            value = int(value)
        if not isinstance(value, int):
            raise ParsingError('expected an int')
        return value

    def validate(self, value: int, /):
        pass


class Float(Parser[float]):
    """Parser for float values.

    """

    def parse(self, value: str, /) -> float:
        try:
            return float(value.strip())
        except ValueError:
            raise ParsingError(f'could not parse value {value!r} as a float')

    def parse_config(self, value: _t.Any, /) -> float:
        if not isinstance(value, (float, int)):
            raise ParsingError('expected a float')
        return value

    def validate(self, value: float, /):
        pass


class Bool(Parser[bool]):
    """Parser for bool values, such as `'yes'` or `'no'`.

    """

    def parse(self, value: str, /) -> bool:
        value = value.strip().lower()

        if value in ('y', 'yes', 'true', '1'):
            return True
        elif value in ('n', 'no', 'false', '0'):
            return False
        else:
            raise ParsingError(f'could not parse value {value!r},'
                               f' enter either \'yes\' or \'no\'')

    def parse_config(self, value: _t.Any, /) -> bool:
        if not isinstance(value, bool):
            raise ParsingError('expected a bool')
        return value

    def validate(self, value: bool, /):
        pass

    def describe(self) -> _t.Optional[str]:
        return 'yes|no'

    def describe_value(self, value: bool, /) -> _t.Optional[str]:
        return 'yes' if value else 'no'


class Enum(Parser[E]):
    """Parser for enums, as defined in the standard :mod:`enum` module.

    """

    def __init__(self, enum_type: _t.Type[E]):
        super().__init__()

        self._enum_type: _t.Type[E] = enum_type

    def parse(self, value: str, /) -> E:
        try:
            return self._enum_type[value.strip().upper()]
        except KeyError:
            enum_values = ', '.join(e.name for e in self._enum_type)
            raise ParsingError(
                f'could not parse value {value!r}'
                f' as {self._enum_type.__name__},'
                f' should be one of {enum_values}')

    def parse_config(self, value: _t.Any, /) -> E:
        if not isinstance(value, str):
            raise ParsingError('expected a string')
        return self.parse(value)

    def validate(self, value: E, /):
        pass

    def describe(self) -> _t.Optional[str]:
        desc = '|'.join(e.name for e in self._enum_type)
        return desc

    def describe_value(self, value: E, /) -> _t.Optional[str]:
        return value.name


class Optional(Parser[_t.Optional[T]]):
    """Parser for optional values.

    Interprets empty strings as `None`s.

    """

    def __init__(self, inner: Parser[T]):
        super().__init__()

        self._inner: Parser[T] = inner

    def parse(self, value: str, /) -> _t.Optional[T]:
        if not value:
            return None
        return self._inner.parse(value)

    def parse_many(self, value: _t.Sequence[str], /) -> _t.Optional[T]:
        return self._inner.parse_many(value)

    def supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def parse_config(self, value: _t.Any, /) -> _t.Optional[T]:
        if value is None:
            return None
        return self._inner.parse_config(value)

    def validate(self, value: _t.Optional[T], /):
        if value is not None:
            self._inner.validate(value)

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe_many()

    def describe_value(self, value: _t.Optional[T], /) -> _t.Optional[str]:
        if value is None:
            return '<none>'
        return self._inner.describe_value(value)


class List(Parser[_t.List[T]]):
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

    def parse(self, value: str, /) -> _t.List[T]:
        return self.parse_many(value.split(self._delimiter))

    def parse_many(self, value: _t.Sequence[str], /) -> _t.List[T]:
        return [
            self._inner.parse(item)
            for item in value
        ]

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: _t.Any, /) -> _t.List[T]:
        if not isinstance(value, list):
            raise ParsingError('expected a list')

        return [
            self._inner.parse_config(item)
            for item in value
        ]

    def validate(self, value: _t.List[T], /):
        for item in value:
            self._inner.validate(item)

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


class Set(Parser[_t.Set[T]]):
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

    def parse(self, value: str, /) -> _t.Set[T]:
        return {
            self._inner.parse(item)
            for item in
            value.split(self._delimiter)
        }

    def parse_many(self, value: _t.Sequence[str], /) -> _t.Set[T]:
        return {
            self._inner.parse(item)
            for item in value
        }

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: _t.Any, /) -> _t.Set[T]:
        if not isinstance(value, list):
            raise ParsingError('expected a list')

        return {
            self._inner.parse_config(item)
            for item in value
        }

    def validate(self, value: _t.Set[T], /):
        for item in value:
            self._inner.validate(item)

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


class FrozenSet(Parser[_t.FrozenSet[T]]):
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

    def parse(self, value: str, /) -> _t.FrozenSet[T]:
        return frozenset({
            self._inner.parse(item)
            for item in
            value.split(self._delimiter)
        })

    def parse_many(self, value: _t.Sequence[str], /) -> _t.FrozenSet[T]:
        return frozenset({
            self._inner.parse(item)
            for item in value
        })

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: _t.Any, /) -> _t.FrozenSet[T]:
        if not isinstance(value, list):
            raise ParsingError('expected a list')

        return frozenset({
            self._inner.parse_config(item)
            for item in value
        })

    def validate(self, value: _t.FrozenSet[T], /):
        for item in value:
            self._inner.validate(item)

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


class Dict(Parser[_t.Dict[K, V]]):
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
        delimiter: _t.Optional[str] = None,
        pair_delimiter: str = ':'
    ):
        super().__init__()

        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

        self._inner = Pair(key, value, pair_delimiter)

    def parse(self, value: str, /) -> _t.Dict[K, V]:
        return self.parse_many(value.split(self._delimiter))

    def parse_many(self, value: _t.Sequence[str], /) -> _t.Dict[K, V]:
        return dict(self._inner.parse(item) for item in value)

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: _t.Any, /) -> _t.Dict[K, V]:
        if not isinstance(value, dict):
            raise ParsingError('expected a dict')

        return dict(self._inner.parse_config(item) for item in value)

    def validate(self, value: _t.Dict[K, V], /):
        for item in value.items():
            self._inner.validate(item)

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


class Pair(Parser[_t.Tuple[K, V]]):
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
        delimiter: _t.Optional[str] = ':'
    ):
        super().__init__()

        self._key = key
        self._value = value
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def parse(self, value: str, /) -> _t.Tuple[K, V]:
        kv = value.split(self._delimiter, maxsplit=1)
        if len(kv) != 2:
            raise ParsingError('could not parse a key-value pair')

        return (
            self._key.parse(kv[0]),
            self._value.parse(kv[1]),
        )

    def parse_config(self, value: _t.Any, /) -> _t.Tuple[K, V]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ParsingError('expected a tuple of two elements')

        return (
            self._key.parse_config(value[0]),
            self._value.parse_config(value[1]),
        )

    def validate(self, value: _t.Tuple[K, V], /):
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


class Tuple(Parser[TU]):
    """Parser for tuples of fixed lengths.

    :param parsers:
        parsers for each tuple element.
    :param delimiter:
        delimiter that will be passed to :py:meth:`str.split`.

    """

    def __init__(self, *parsers: Parser[_t.Any], delimiter: _t.Optional[str] = None):
        super().__init__()

        if len(parsers) == 0:
            raise ValueError('empty tuple')
        self._parsers = parsers
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def parse(self, value: str, /) -> TU:
        items = value.split(self._delimiter, maxsplit=len(self._parsers) - 1)
        return self.parse_many(items)

    def parse_many(self, value: _t.Sequence[str], /) -> TU:
        if len(value) != len(self._parsers):
            raise ParsingError('could not parse a tuple')

        return _t.cast(TU, tuple(
            parser.parse(item) for parser, item in zip(self._parsers, value)
        ))

    def supports_parse_many(self) -> bool:
        return True

    def parse_config(self, value: _t.Any, /) -> TU:
        if not isinstance(value, (list, tuple)):
            raise ParsingError('expected a list or a tuple')
        elif len(value) != len(self._parsers):
            raise ParsingError(f'expected {len(self._parsers)} element(s)')

        return _t.cast(TU, tuple(
            parser.parse_config(item)
            for parser, item in zip(self._parsers, value)
        ))

    def validate(self, value: TU, /):
        for parser, item in zip(self._parsers, _t.cast(tuple, value)):
            parser.validate(item)

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
            for parser, item in zip(self._parsers, _t.cast(tuple, value))
        ]

        return delimiter.join(desc)


class Path(Parser[pathlib.Path]):
    """Parse a file system path, return a :class:`pathlib.Path`.

    :param extensions: list of allowed file extensions.

    """

    def __init__(self, extensions: _t.Optional[_t.Collection[str]] = None):
        super().__init__()

        self._extensions = extensions

    def parse(self, value: str, /) -> pathlib.Path:
        return pathlib.Path(value).expanduser().resolve()

    def parse_config(self, value: _t.Any, /) -> pathlib.Path:
        if not isinstance(value, str):
            raise ParsingError('expected a string')
        return self.parse(value)

    def validate(self, value: pathlib.Path, /):
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

    def validate(self, value: pathlib.Path, /):
        super().validate(value)

        if value.exists():
            raise ParsingError(f'{value} already exist')


class ExistingPath(Path):
    """Parse a file system path and verify that it exists.

    """

    def validate(self, value: pathlib.Path, /):
        super().validate(value)

        if not value.exists():
            raise ParsingError(f'{value} doesn\'t exist')


class File(ExistingPath):
    """Parse path to a file.

    """

    def validate(self, value: pathlib.Path, /):
        super().validate(value)

        if not value.is_file():
            raise ParsingError(f'{value} is not a file')


class Dir(ExistingPath):
    """Parse path to a directory.

    """

    def __init__(self):
        # Disallow passing `extensions`.
        super().__init__()

    def validate(self, value: pathlib.Path, /):
        super().validate(value)

        if not value.is_dir():
            raise ParsingError(f'{value} is not a directory')


class GitRepo(Dir):
    """Parse path to a git repository.

    This parser just checks that the given directory has
    a subdirectory named ``.git``.

    """

    def validate(self, value: pathlib.Path, /):
        super().validate(value)

        if not value.joinpath('.git').is_dir():
            raise ParsingError(f'{value} is not a git repository')

        return value


class _BoundImpl(Parser[T], _t.Generic[T, Cmp]):
    _Self = _t.TypeVar('_Self', bound='_BoundImpl')

    def __init__(
        self,
        inner: Parser[T],
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
            self.lower_bound(lower)
        elif lower_inclusive is not None:
            self.lower_bound_inclusive(lower_inclusive)

        if upper is not None and upper_inclusive is not None:
            raise TypeError(
                'upper and upper_inclusive cannot be given at the same time')
        elif upper is not None:
            self.upper_bound(upper)
        elif upper_inclusive is not None:
            self.upper_bound_inclusive(upper_inclusive)

        self._mapper = mapper
        self._desc = desc

    def lower_bound(self: _Self, lower: Cmp, /) -> _Self:
        """Set lower bound so we require that `value > lower`.

        """

        self._lower = lower
        self._lower_inclusive = False
        return self

    def lower_bound_inclusive(self: _Self, lower: Cmp, /) -> _Self:
        """Set lower bound so we require that `value >= lower`.

        """

        self._lower = lower
        self._lower_inclusive = True
        return self

    def upper_bound(self: _Self, upper: Cmp, /) -> _Self:
        """Set upper bound so we require that `value < upper`.

        """

        self._upper = upper
        self._upper_inclusive = False
        return self

    def upper_bound_inclusive(self: _Self, upper: Cmp, /) -> _Self:
        """Set upper bound so we require that `value <= upper`.

        """

        self._upper = upper
        self._upper_inclusive = True
        return self

    def parse(self, value: str, /) -> T:
        return self._inner.parse(value)

    def parse_many(self, value: _t.Sequence[str], /) -> T:
        return self._inner.parse_many(value)

    def supports_parse_many(self) -> bool:
        return self._inner.supports_parse_many()

    def parse_config(self, value: _t.Any, /) -> T:
        return self._inner.parse_config(value)

    def validate(self, value: T, /):
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

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_many(self) -> _t.Optional[str]:
        return self._inner.describe_many()

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        return self._inner.describe_value(value)


class Bound(_BoundImpl[Cmp, Cmp]):
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


class BoundLen(_BoundImpl[Sz, int]):
    """Check that length of a value is upper- or lower-bound by some constraints.

    The interface is exactly like one of the :class:`Bound` parser.

    """

    def __init__(
        self,
        inner: Parser[Sz],
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


class OneOf(Parser[T]):
    """Check if the parsed value is one of the given set of values.

    """

    def __init__(self, inner: Parser[T], values: _t.Collection[T]):
        super().__init__()

        self._inner: Parser[T] = inner
        self._allowed_values = values

    def parse(self, value: str, /) -> T:
        return self._inner.parse(value)

    def parse_config(self, value: _t.Any, /) -> T:
        return self._inner.parse_config(value)

    def validate(self, value: T, /):
        self._inner.validate(value)

        if value not in self._allowed_values:
            values = ', '.join(map(str, self._allowed_values))
            raise ParsingError(
                f'could not parse value {value!r},'
                f' should be one of {values}')

    def describe(self) -> _t.Optional[str]:
        desc = '|'.join(str(e) for e in self._allowed_values)
        if len(desc) < 80:
            return desc
        else:
            return super().describe()

    def describe_value(self, value: T, /) -> _t.Optional[str]:
        return self._inner.describe_value(value)


class Regex(Parser[str]):
    """Check if the parsed value matches the given regular expression.

    """

    def __init__(self, inner: Parser[str], regex: _t.Union[str, re.Pattern]):
        super().__init__()

        if isinstance(regex, str):
            regex = re.compile(regex)

        self._inner: Parser[str] = inner
        self._regex = regex

    def parse(self, value: str, /) -> str:
        return self._inner.parse(value)

    def parse_config(self, value: _t.Any, /) -> str:
        return self._inner.parse_config(value)

    def validate(self, value: str, /):
        self._inner.validate(value)

        if self._regex.match(value) is None:
            raise ParsingError(
                f'value should match regex \'{self._regex.pattern}\'')

    def describe(self) -> _t.Optional[str]:
        return self._inner.describe()

    def describe_value(self, value: str, /) -> _t.Optional[str]:
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
        raise TypeError(f'forward references are not supported: {ty}')

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
    from_type_hint(ty.__supertype__)
    if getattr(ty, '__module__') == 'typing' and hasattr(ty, '__supertype__')
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
