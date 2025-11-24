# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

# pyright: reportDeprecated=false
# ruff: noqa: F403, F405, I002

import re as _re
import sys as _sys
import types as _types
import typing as _typing
from typing import *  # type: ignore

try:
    import typing_extensions as _typing_extensions
    from typing_extensions import *  # type: ignore
except ImportError:
    import yuio._vendor.typing_extensions as _typing_extensions_v

    # This is an evil hack to make type checkers behave. Otherwise,
    # they don't recognize `yuio._vendor.typing_extensions` as something special.
    _sys.modules["typing_extensions"] = _typing_extensions_v

    import typing_extensions as _typing_extensions
    from typing_extensions import *  # type: ignore

assert _typing.Union is _typing_extensions.Union
assert _typing.Annotated is _typing_extensions.Annotated

# Note: dataclass doesn't always recognize class vars
# if they're re-exported from typing.
# See https://github.com/python/cpython/issues/133956.
del ClassVar  # noqa: F821


def is_union(origin):
    return origin is Union or origin is _types.UnionType


if TYPE_CHECKING:
    StrRePattern: TypeAlias = _re.Pattern[str]
    StrReMatch: TypeAlias = _re.Match[str]

else:
    try:
        StrRePattern = _re.Pattern[str]
        StrReMatch = _re.Match[str]
    except TypeError:
        StrRePattern = _re.Pattern
        StrReMatch = _re.Match


if _sys.version_info < (3, 11):

    def type_repr(obj: Any) -> str:
        # Better `type_repr` for older pythons.
        if origin := get_origin(obj):
            return type_repr(origin) + type_repr(get_args(obj))
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
