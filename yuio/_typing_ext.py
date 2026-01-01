# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

# pyright: reportDeprecated=false
# ruff: noqa: F403, F405, I002

from __future__ import annotations

import abc as _abc
import re as _re
import types as _types

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


def is_union(origin):
    return origin is _t.Union or origin is _types.UnionType


if TYPE_CHECKING:
    StrRePattern: _t.TypeAlias = _re.Pattern[str]
    StrReMatch: _t.TypeAlias = _re.Match[str]

else:
    try:
        StrRePattern = _re.Pattern[str]
        StrReMatch = _re.Match[str]
    except TypeError:
        StrRePattern = _re.Pattern
        StrReMatch = _re.Match


try:
    from typing import type_repr  # type: ignore
except ImportError:

    def type_repr(obj: _t.Any) -> str:
        # Better `type_repr` for older pythons.
        if origin := _t.get_origin(obj):
            return type_repr(origin) + type_repr(_t.get_args(obj))
        if isinstance(obj, (type, _types.FunctionType, _types.BuiltinFunctionType)):
            if obj.__module__ == "builtins":
                return obj.__qualname__
            return f"{obj.__module__}.{obj.__qualname__}"
        if obj is ...:
            return "..."
        if isinstance(obj, _types.FunctionType):
            return obj.__name__
        if isinstance(obj, tuple):
            # Special case for `repr` of types with `ParamSpec`:
            return "[" + ", ".join(type_repr(t) for t in obj) + "]"
        return repr(obj)


_T_contra = _t.TypeVar("_T_contra", contravariant=True)


class SupportsLt(_t.Protocol[_T_contra]):
    """
    Protocol for objects that can be compared to each other.

    """

    @_abc.abstractmethod
    def __lt__(self, other: _T_contra, /) -> bool: ...
