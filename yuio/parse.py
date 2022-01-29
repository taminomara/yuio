# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""Parsing user input.

This module provides several parsers that convert (usually user-provided)
strings to python objects, or check user input, and throw `ValueError`s
in case of any issue.

All parsers are descendants of the `Parser` class. On the surface, they are
just callables that take a string and return a python object. That is, you
can use them in any place that expects such callable, for example
in flags in argparse, or in `ask` method from `yuio.log`.

"""

import abc
import enum
import typing as _t


__all__ = (
    'Parser',
    'Str',
    'Int',
    'Float',
    'Bool',
    'Enum',
    'File',
    'Dir',
    'GitRepo',
    'Bound',
    'OneOf',
    'Map',
    'Lower',
    'Upper',

    'parse_str',
    'parse_int',
    'parse_float',
    'parse_bool',
    'parse_enum',
    'parse_file',
    'parse_dir',
    'parse_git_repo',
)


class _Comparable(_t.Protocol):
    @abc.abstractmethod
    def __lt__(self, other) -> bool: ...

    @abc.abstractmethod
    def __gt__(self, other) -> bool: ...

    @abc.abstractmethod
    def __le__(self, other) -> bool: ...

    @abc.abstractmethod
    def __ge__(self, other) -> bool: ...

    @abc.abstractmethod
    def __eq__(self, other) -> bool: ...


T = _t.TypeVar('T')
C = _t.TypeVar('C', bound=_Comparable)
E = _t.TypeVar('E', bound=enum.Enum)


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
    def __call__(self, value: str) -> T:
        """Parse and verify user input, raise `ValueError` on failure.

        """

    def bound(
        self: 'Parser[C]',
        *,
        lower: _t.Optional[C] = None,
        lower_inclusive: _t.Optional[C] = None,
        upper: _t.Optional[C] = None,
        upper_inclusive: _t.Optional[C] = None
    ) -> 'Bound[C]':
        """Check that value is upper- or lower-bound by some constraints.

        See `Bound` for more info.

        """

        return Bound(
            self,
            lower=lower,
            lower_inclusive=lower_inclusive,
            upper=upper,
            upper_inclusive=upper_inclusive
        )

    def one_of(self, values: _t.Collection[T]) -> 'OneOf[T]':
        """Check if the parsed value is one of the given set of values.

        See `OneOf` for more info.

        """

        return OneOf(self, values)

    def map(self, mapper: _t.Callable[[str], str]) -> 'Map[T]':
        """Apply a callable to a string before passing it to another parser.

        See `Map` for more info.

        """

        return Map(self, mapper)

    def lower(self) -> 'Lower[T]':
        """Convert string to lowercase before passing it to another parser.

        See `Lower` for more info.

        """

        return Lower(self)

    def upper(self) -> 'Upper[T]':
        """Convert string to uppercase before passing it to another parser.

        See `Upper` for more info.

        """

        return Upper(self)

    def strip(self) -> 'Strip[T]':
        """Remove whitespaces from string ends before passing it to another parser.

        See `Strip` for more info.

        """

        return Strip(self)


class Str(Parser[str]):
    """Parser for str values (does nothing).

    """

    def __call__(self, value: str) -> str:
        return value


class Int(Parser[int]):
    """Parser for int values.

    """

    def __call__(self, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f'could not parse value {value!r} as int')


class Float(Parser[float]):
    """Parser for float values.

    """

    def __call__(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            raise ValueError(f'could not parse value {value!r} as float')


class Bool(Parser[bool]):
    """Parser for bool values, such as `'yes'` or `'no'`.

    """

    def __call__(self, value: str) -> bool:
        value = value.lower()

        if value in ('y', 'yes', 'true', '1'):
            return True
        elif value in ('n', 'no', 'false', '0'):
            return False
        else:
            raise ValueError(f'could not parse value {value!r},'
                             f' enter either \'yes\' or \'no\'')


class Enum(Parser[E]):
    """Parse an enum, as defined in the standard `enum` module.

    """

    def __init__(self, enum_type: _t.Type[E]):
        super().__init__()

        self._enum_type: _t.Type[E] = enum_type

    def __call__(self, value: str) -> E:
        try:
            return self._enum_type[value.upper()]
        except KeyError:
            enum_values = ', '.join(e.name for e in self._enum_type)
            raise ValueError(
                f'could not parse value {value!r}'
                f' as {self._enum_type.__name__},'
                f' should be one of {enum_values}')


class File(Parser[str]):
    """Check that the given string is a path to a file.

    """

    def __init__(self, extensions: _t.Optional[_t.Collection[str]] = None):
        """Init the class.

        :param extensions: list of allowed file extensions.

        """

        super().__init__()

        self._extensions = extensions

    def __call__(self, value: str) -> str:
        import os

        value = os.path.expanduser(value)
        value = os.path.abspath(value)

        if not os.path.exists(value):
            raise ValueError(f'{value} doesn\'t exist')
        if not os.path.isfile(value):
            raise ValueError(f'{value} is not a file')
        if self._extensions is not None:
            if not any(value.endswith(ext) for ext in self._extensions):
                exts = ', '.join(self._extensions)
                raise ValueError(f'{value} should have extension {exts}')

        return value


class Dir(Parser[str]):
    """Check that the given string is a path to a dir.

    """

    def __call__(self, value: str) -> str:
        import os

        value = os.path.expanduser(value)
        value = os.path.abspath(value)

        if not os.path.exists(value):
            raise ValueError(f'{value} doesn\'t exist')
        if not os.path.isdir(value):
            raise ValueError(f'{value} is not a directory')

        return value


class GitRepo(Dir):
    """Check that the given string is a path to a git repository.

    """

    def __call__(self, value: str) -> str:
        import os

        value = super().__call__(value)

        if not os.path.isdir(os.path.join(value, '.git')):
            raise ValueError(f'{value} is not a git repository')

        return value


class Bound(Parser[C]):
    """Check that value is upper- or lower-bound by some constraints.

    """

    _Self = _t.TypeVar('_Self', bound='Bound')

    _lower: _t.Optional[C] = None
    """Lower bound."""

    _lower_inclusive: bool = True
    """True if lower bound is inclusive."""

    _upper: _t.Optional[C] = None
    """Upper bound."""

    _upper_inclusive: bool = True
    """True if upper bound is inclusive."""

    def __init__(
        self,
        inner: Parser[C],
        *,
        lower: _t.Optional[C] = None,
        lower_inclusive: _t.Optional[C] = None,
        upper: _t.Optional[C] = None,
        upper_inclusive: _t.Optional[C] = None
    ):
        """Init the class.

        :param inner:
            inner parser that will be used to actually parse a value before
            checking its bounds.
        :param lower:
            set lower bound for value, so we require that `value > lower`.
            Can't be given if `lower_inclusive` is also given.
        :param lower_inclusive:
            set lower bound for value, so we require that `value >= lower`.
            Can't be given if `lower` is also given.
        :param upper:
            set upper bound for value, so we require that `value < upper`.
            Can't be given if `upper_inclusive` is also given.
        :param upper_inclusive:
            set upper bound for value, so we require that `value <= upper`.
            Can't be given if `upper` is also given.

        """

        super().__init__()

        self._inner: Parser[C] = inner

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

    def lower_bound(self: _Self, lower: C) -> _Self:
        """Set lower bound so we require that `value > lower`.

        """

        self._lower = lower
        self._lower_inclusive = False
        return self

    def lower_bound_inclusive(self: _Self, lower: C) -> _Self:
        """Set lower bound so we require that `value >= lower`.

        """

        self._lower = lower
        self._lower_inclusive = True
        return self

    def upper_bound(self: _Self, upper: C) -> _Self:
        """Set upper bound so we require that `value < upper`.

        """

        self._upper = upper
        self._upper_inclusive = False
        return self

    def upper_bound_inclusive(self: _Self, upper: C) -> _Self:
        """Set upper bound so we require that `value <= upper`.

        """

        self._upper = upper
        self._upper_inclusive = True
        return self

    def __call__(self, value: str) -> C:
        parsed = self._inner(value)

        if self._lower is not None:
            if self._lower_inclusive and parsed < self._lower:
                raise ValueError(
                    f'value should be greater or equal to {self._lower},'
                    f' got {parsed} instead')
            elif not self._lower_inclusive and parsed <= self._lower:
                raise ValueError(
                    f'value should be greater than {self._lower},'
                    f' got {parsed} instead')

        if self._upper is not None:
            if self._upper_inclusive and parsed > self._upper:
                raise ValueError(
                    f'value should be lesser or equal to {self._upper},'
                    f' got {parsed} instead')
            elif not self._upper_inclusive and parsed >= self._upper:
                raise ValueError(
                    f'value should be lesser than {self._upper},'
                    f' got {parsed} instead')

        return parsed


class OneOf(Parser[T]):
    """Check if the parsed value is one of the given set of values.

    """

    def __init__(self, inner: Parser[T], values: _t.Collection[T]):
        super().__init__()

        self._inner = inner
        self._allowed_values = values

    def __call__(self, value: str) -> T:
        parsed = self._inner(value)

        if parsed not in self._allowed_values:
            values = ', '.join(map(repr, self._allowed_values))
            raise ValueError(
                f'could not parse value {value!r},'
                f' should be one of {values}')

        return parsed


class Map(Parser[T]):
    """Apply a callable to a string before passing it to another parser.

    """

    def __init__(self, inner: Parser[T], mapper: _t.Callable[[str], str]):
        super().__init__()

        self._inner = inner
        self._mapper = mapper

    def __call__(self, value: str) -> T:
        return self._inner(self._mapper(value))


class Lower(Map[T]):
    """Convert string to lowercase before passing it to another parser.

    """

    def __init__(self, inner: Parser[T]):
        super().__init__(inner, str.lower)


class Upper(Map[T]):
    """Convert string to uppercase before passing it to another parser.

    """

    def __init__(self, inner: Parser[T]):
        super().__init__(inner, str.lower)


class Strip(Map[T]):
    """Remove whitespaces from string ends before passing it to another parser.

    """

    def __init__(self, inner: Parser[T]):
        super().__init__(inner, str.strip)


# Helper constructors


def parse_str() -> Str:
    """Parser for str values (does nothing).

    """

    return Str()


def parse_int() -> Int:
    """Parser for int values.

    """

    return Int()


def parse_float() -> Float:
    """Parser for float values.

    """

    return Float()


def parse_bool() -> Bool:
    """Parser for bool values, such as `'yes'` or `'no'`.

    """

    return Bool()


def parse_enum(enum_type: _t.Type[E]) -> Enum[E]:
    """Parse an enum, as defined in the standard `enum` module.

    """

    return Enum(enum_type)


def parse_file(extensions: _t.Optional[_t.Collection[str]] = None) -> File:
    """Check that the given string is a path to a file.

    """

    return File(extensions)


def parse_dir() -> Dir:
    """Check that the given string is a path to a dir.

    """

    return Dir()


def parse_git_repo() -> GitRepo:
    """Check that the given string is a path to a git repository.

    """

    return GitRepo()
