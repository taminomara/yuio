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
for example in flags in argparse, or in :func:`~yuio.log.ask` method
from :mod:`yuio.log`.


Base parser
-----------

.. autoclass:: Parser

   .. automethod:: parse

   .. automethod:: parse_config

   .. automethod:: validate

   .. automethod:: describe

   .. automethod:: describe_value


Value parsers
-------------

.. autoclass:: Str

.. autoclass:: StrLower

.. autoclass:: StrUpper

.. autoclass:: Int

.. autoclass:: Float

.. autoclass:: Bool

.. autoclass:: Enum


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

.. autoclass:: OneOf

"""

import abc
import enum
import pathlib
import typing as _t


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

    def __call__(self, value: str) -> T:
        """Parse and verify user input, raise :class:`ValueError` on failure.

        """

        parsed = self.parse(value)
        self.validate(parsed)
        return parsed

    @abc.abstractmethod
    def parse(self, value: str) -> T:
        """Parse user input, raise :class:`ValueError` on failure.

        """

    @abc.abstractmethod
    def parse_config(self, value: _t.Any) -> T:
        """Parse value from a config, raise :class:`ValueError` on failure.

        This method accepts python values, i.e. when parsing a json config.

        """

    @abc.abstractmethod
    def validate(self, value: T):
        """Verify parsed value, raise :class:`ValueError` on failure.

        """

    def describe(self) -> _t.Optional[str]:
        """Return a human-readable description of an expected input.

        """

        return None

    def describe_value(self, value: T) -> _t.Optional[str]:
        """Return a human-readable description of a given value.

        """

        return None


class Str(Parser[str]):
    """Parser for str values.

    Applies a `modifier` to the value, if one is given.

    """

    def __init__(self, modifier: _t.Optional[_t.Callable[[str], str]] = None):
        super().__init__()

        self._modifier = modifier

    def parse(self, value: str) -> str:
        if self._modifier is not None:
            return self._modifier(value)
        else:
            return value

    def parse_config(self, value: _t.Any) -> str:
        if not isinstance(value, str):
            raise ValueError('expected a string')
        if self._modifier is not None:
            return self._modifier(value)
        else:
            return value

    def validate(self, value: str):
        pass


class StrLower(Str):
    """Parser for str values that converts them to lowercase.

    """

    def __init__(self):
        super().__init__(str.lower)


class StrUpper(Str):
    """Parser for str values that converts them to uppercase.

    """

    def __init__(self):
        super().__init__(str.upper)


class Int(Parser[int]):
    """Parser for int values.

    """

    def parse(self, value: str) -> int:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f'could not parse value {value!r} as an int')

    def parse_config(self, value: _t.Any) -> int:
        if isinstance(value, float):
            if value != int(value):
                raise ValueError('expected an int, got a float instead')
            value = int(value)
        if not isinstance(value, int):
            raise ValueError('expected an int')
        return value

    def validate(self, value: int):
        pass


class Float(Parser[float]):
    """Parser for float values.

    """

    def parse(self, value: str) -> float:
        try:
            return float(value)
        except ValueError:
            raise ValueError(f'could not parse value {value!r} as a float')

    def parse_config(self, value: _t.Any) -> float:
        if not isinstance(value, (float, int)):
            raise ValueError('expected a float')
        return value

    def validate(self, value: float):
        pass


class Bool(Parser[bool]):
    """Parser for bool values, such as `'yes'` or `'no'`.

    """

    def parse(self, value: str) -> bool:
        value = value.lower()

        if value in ('y', 'yes', 'true', '1'):
            return True
        elif value in ('n', 'no', 'false', '0'):
            return False
        else:
            raise ValueError(f'could not parse value {value!r},'
                             f' enter either \'yes\' or \'no\'')

    def parse_config(self, value: _t.Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError('expected a bool')
        return value

    def validate(self, value: bool):
        pass

    def describe(self) -> _t.Optional[str]:
        return 'yes/no'

    def describe_value(self, value: bool) -> _t.Optional[str]:
        return 'yes' if value else 'no'


class Enum(Parser[E]):
    """Parser for enums, as defined in the standard :mod:`enum` module.

    """

    def __init__(self, enum_type: _t.Type[E]):
        super().__init__()

        self._enum_type: _t.Type[E] = enum_type

    def parse(self, value: str) -> E:
        try:
            return self._enum_type[value.upper()]
        except KeyError:
            enum_values = ', '.join(e.name for e in self._enum_type)
            raise ValueError(
                f'could not parse value {value!r}'
                f' as {self._enum_type.__name__},'
                f' should be one of {enum_values}')

    def parse_config(self, value: _t.Any) -> E:
        if not isinstance(value, str):
            raise ValueError('expected a string')
        return self.parse(value)

    def validate(self, value: E):
        pass

    def describe(self) -> _t.Optional[str]:
        desc = '/'.join(e.name for e in self._enum_type)
        if len(desc) < 80:
            return desc
        else:
            return None

    def describe_value(self, value: E) -> _t.Optional[str]:
        return value.name


class Path(Parser[pathlib.Path]):
    """Parse a file system path, return a :class:`pathlib.Path`.

    """

    def __init__(self, extensions: _t.Optional[_t.Collection[str]] = None):
        """Init the class.

        :param extensions: list of allowed file extensions.

        """

        super().__init__()

        self._extensions = extensions

    def parse(self, value: str) -> pathlib.Path:
        return pathlib.Path(value).expanduser().resolve()

    def parse_config(self, value: _t.Any) -> pathlib.Path:
        if not isinstance(value, str):
            raise ValueError('expected a string')
        return self.parse(value)

    def validate(self, value: pathlib.Path):
        if self._extensions is not None:
            if not any(value.name.endswith(ext) for ext in self._extensions):
                exts = ', '.join(self._extensions)
                raise ValueError(f'{value} should have extension {exts}')

    def describe(self) -> _t.Optional[str]:
        if self._extensions is not None:
            return '/'.join(self._extensions)
        else:
            return None


class NonExistentPath(Path):
    """Parse a file system path and verify that it doesn't exist.

    """

    def validate(self, value: pathlib.Path):
        super().validate(value)

        if value.exists():
            raise ValueError(f'{value} already exist')


class ExistingPath(Path):
    """Parse a file system path and verify that it exists.

    """

    def validate(self, value: pathlib.Path):
        super().validate(value)

        if not value.exists():
            raise ValueError(f'{value} doesn\'t exist')


class File(ExistingPath):
    """Parse path to a file.

    """

    def validate(self, value: pathlib.Path):
        super().validate(value)

        if not value.is_file():
            raise ValueError(f'{value} is not a file')


class Dir(ExistingPath):
    """Parse path to a directory.

    """

    def __init__(self):
        # Disallow passing `extensions`.
        super().__init__()

    def validate(self, value: pathlib.Path):
        super().validate(value)

        if not value.is_dir():
            raise ValueError(f'{value} is not a directory')


class GitRepo(Dir):
    """Parse path to a git repository.

    This parser just checks that the given directory has
    a subdirectory named ``.git``.

    """

    def validate(self, value: pathlib.Path):
        super().validate(value)

        if not value.joinpath('.git').is_dir():
            raise ValueError(f'{value} is not a git repository')

        return value


class Bound(Parser[C]):
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

    def parse(self, value: str) -> C:
        return self._inner.parse(value)

    def parse_config(self, value: _t.Any) -> C:
        return self._inner.parse_config(value)

    def validate(self, value: C):
        self._inner.validate(value)

        if self._lower is not None:
            if self._lower_inclusive and value < self._lower:
                raise ValueError(
                    f'value should be greater or equal to {self._lower},'
                    f' got {value} instead')
            elif not self._lower_inclusive and value <= self._lower:
                raise ValueError(
                    f'value should be greater than {self._lower},'
                    f' got {value} instead')

        if self._upper is not None:
            if self._upper_inclusive and value > self._upper:
                raise ValueError(
                    f'value should be lesser or equal to {self._upper},'
                    f' got {value} instead')
            elif not self._upper_inclusive and value >= self._upper:
                raise ValueError(
                    f'value should be lesser than {self._upper},'
                    f' got {value} instead')


class OneOf(Parser[T]):
    """Check if the parsed value is one of the given set of values.

    """

    def __init__(self, inner: Parser[T], values: _t.Collection[T]):
        super().__init__()

        self._inner = inner
        self._allowed_values = values

    def parse(self, value: str) -> T:
        return self._inner.parse(value)

    def parse_config(self, value: _t.Any) -> T:
        return self._inner.parse_config(value)

    def validate(self, value: T):
        self._inner.validate(value)

        if value not in self._allowed_values:
            values = ', '.join(map(str, self._allowed_values))
            raise ValueError(
                f'could not parse value {value!r},'
                f' should be one of {values}')

    def describe(self) -> _t.Optional[str]:
        desc = '/'.join(str(e) for e in self._allowed_values)
        if len(desc) < 80:
            return desc
        else:
            return super().describe()
