# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Type annotations are unfortunately bulky. Yuio provides shortcuts for common annotated
types such as positive ints or non-empty containers.

.. type:: PosInt
    :canonical: typing.Annotated[int, ~yuio.parse.Gt(0)]

    Positive int.

.. type:: NonNegInt
    :canonical: typing.Annotated[int, ~yuio.parse.Ge(0)]

    Non-negative int.

.. type:: PosFloat
    :canonical: typing.Annotated[float, ~yuio.parse.Gt(0)]

    Positive float.

.. type:: NonNegFloat
    :canonical: typing.Annotated[float, ~yuio.parse.Ge(0)]

    Non-negative float.

.. type:: NonEmptyStr
    :canonical: typing.Annotated[str, ~yuio.parse.LenGt(0)]

    Non-empty string.

.. type:: NonEmptyList
    :canonical: typing.Annotated[list[T], ~yuio.parse.LenGt(0)]

    Non-empty list.

.. type:: NonEmptySet
    :canonical: typing.Annotated[set[T], ~yuio.parse.LenGt(0)]

    Non-empty set.

.. type:: NonEmptyFrozenSet
    :canonical: typing.Annotated[frozenset[T], ~yuio.parse.LenGt(0)]

    Non-empty frozenset.

.. type:: NonEmptyDict
    :canonical: typing.Annotated[dict[K, V], ~yuio.parse.LenGt(0)]

    Non-empty dict.

.. type:: Path
    :canonical: pathlib.Path

    Filepath.

.. type:: NonExistentPath
    :canonical: typing.Annotated[Path, ~yuio.parse.NonExistentPath]

    Filepath not pointing to an existing file or directory.

.. type:: ExistingPath
    :canonical: typing.Annotated[Path, ~yuio.parse.ExistingPath]

    Filepath pointing to an existing file or directory.

.. type:: File
    :canonical: typing.Annotated[Path, ~yuio.parse.File]

    Filepath pointing to an existing regular file.

.. type:: Dir
    :canonical: typing.Annotated[Path, ~yuio.parse.Dir]

    Filepath pointing to an existing directory.

.. type:: GitRepo
    :canonical: typing.Annotated[Path, ~yuio.parse.GitRepo]

    Filepath pointing to an existing directory that has ``.git`` sub-directory.

.. type:: TimeDelta
    :canonical: ~datetime.timedelta

    Time delta.

.. type:: PosTimeDelta
    :canonical: typing.Annotated[TimeDelta, ~yuio.parse.Gt(~datetime.timedelta(0))]

    Positive time delta.

.. type:: NonNegTimeDelta
    :canonical: typing.Annotated[TimeDelta, ~yuio.parse.Ge(~datetime.timedelta(0))]

    Non-negative time delta.

.. type:: Seconds
    :canonical: typing.Annotated[~datetime.timedelta, ~yuio.parse.Seconds()]

    Timedelta that's parsed from int as number of seconds.

.. type:: PosSeconds
    :canonical: typing.Annotated[Seconds, ~yuio.parse.Gt(~datetime.timedelta(0))]

    Positive number of seconds.

.. type:: NonNegSeconds
    :canonical: typing.Annotated[Seconds, ~yuio.parse.Ge(~datetime.timedelta(0))]

    Non-negative number of seconds.


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

import datetime
import pathlib

import yuio.parse
from yuio.json_schema import JsonValue
from yuio.secret import SecretString, SecretValue

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "Dir",
    "ExistingPath",
    "File",
    "GitRepo",
    "JsonValue",
    "NonEmptyDict",
    "NonEmptyFrozenSet",
    "NonEmptyList",
    "NonEmptySet",
    "NonEmptyStr",
    "NonExistentPath",
    "NonNegFloat",
    "NonNegInt",
    "NonNegSeconds",
    "NonNegTimeDelta",
    "Path",
    "PosFloat",
    "PosInt",
    "PosSeconds",
    "PosTimeDelta",
    "Seconds",
    "SecretString",
    "SecretValue",
    "TimeDelta",
]


T = _t.TypeVar("T")
K = _t.TypeVar("K")
V = _t.TypeVar("V")


PosInt: _t.TypeAlias = _t.Annotated[int, yuio.parse.Gt(0)]
"""
Positive int.

"""

NonNegInt: _t.TypeAlias = _t.Annotated[int, yuio.parse.Ge(0)]
"""
Non-negative int.

"""

PosFloat: _t.TypeAlias = _t.Annotated[float, yuio.parse.Gt(0)]
"""
Positive float.

"""

NonNegFloat: _t.TypeAlias = _t.Annotated[float, yuio.parse.Ge(0)]
"""
Non-negative float.

"""

NonEmptyStr: _t.TypeAlias = _t.Annotated[str, yuio.parse.LenGt(0)]
"""
Non-empty string.

"""

NonEmptyList: _t.TypeAlias = _t.Annotated[list[T], yuio.parse.LenGt(0)]
"""
Non-empty list.

"""

NonEmptySet: _t.TypeAlias = _t.Annotated[set[T], yuio.parse.LenGt(0)]
"""
Non-empty set.

"""

NonEmptyFrozenSet: _t.TypeAlias = _t.Annotated[frozenset[T], yuio.parse.LenGt(0)]
"""
Non-empty frozenset.

"""

NonEmptyDict: _t.TypeAlias = _t.Annotated[dict[K, V], yuio.parse.LenGt(0)]
"""
Non-empty dict.

"""

Path: _t.TypeAlias = pathlib.Path
"""
Filepath.

"""

NonExistentPath: _t.TypeAlias = _t.Annotated[Path, yuio.parse.NonExistentPath]
"""
Filepath not pointing to an existing file or directory.

"""

ExistingPath: _t.TypeAlias = _t.Annotated[Path, yuio.parse.ExistingPath]
"""
Filepath pointing to an existing file or directory.

"""

File: _t.TypeAlias = _t.Annotated[Path, yuio.parse.File]
"""
Filepath pointing to an existing regular file.

"""

Dir: _t.TypeAlias = _t.Annotated[Path, yuio.parse.Dir]
"""
Filepath pointing to an existing directory.

"""

GitRepo: _t.TypeAlias = _t.Annotated[Path, yuio.parse.GitRepo]
"""
Filepath pointing to an existing directory that has ``.git`` sub-directory.

"""

TimeDelta: _t.TypeAlias = datetime.timedelta
"""
Time delta.

"""

_TD_ZERO = datetime.timedelta()

PosTimeDelta: _t.TypeAlias = _t.Annotated[
    TimeDelta, yuio.parse.Gt(_TD_ZERO), yuio.parse.WithMeta(desc="HH:MM:SS")
]
"""
Positive time delta.

"""

NonNegTimeDelta: _t.TypeAlias = _t.Annotated[
    TimeDelta, yuio.parse.Ge(_TD_ZERO), yuio.parse.WithMeta(desc="HH:MM:SS")
]
"""
Non-negative time delta.

"""

Seconds: _t.TypeAlias = _t.Annotated[datetime.timedelta, yuio.parse.Seconds()]
"""
Timedelta that's parsed from int as number of seconds.

"""

PosSeconds: _t.TypeAlias = _t.Annotated[Seconds, yuio.parse.Gt(_TD_ZERO)]
"""
Positive number of seconds.

"""

NonNegSeconds: _t.TypeAlias = _t.Annotated[Seconds, yuio.parse.Ge(_TD_ZERO)]
"""
Non-negative number of seconds.

"""
