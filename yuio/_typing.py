# pyright: reportDeprecated=false

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
del ClassVar


def is_union(origin):
    return origin is Union or origin is _types.UnionType


if TYPE_CHECKING:
    StrRePattern: TypeAlias = _re.Pattern[str]
    StrReMatch: TypeAlias = _re.Match[str]

    def type_repr(ty: Any) -> str: ...

else:
    try:
        StrRePattern = _re.Pattern[str]
        StrReMatch = _re.Match[str]
    except TypeError:
        StrRePattern = _re.Pattern
        StrReMatch = _re.Match

    if "type_repr" not in globals():

        def type_repr(ty: Any) -> str:
            if isinstance(
                value, (type, _types.FunctionType, _types.BuiltinFunctionType)
            ):
                if value.__module__ == "builtins":
                    return value.__qualname__
                return f"{value.__module__}.{value.__qualname__}"
            if value is ...:
                return "..."
            return repr(value)
