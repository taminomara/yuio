import re as _re
import types as _types
import typing as _typing
from typing import *  # type: ignore

import typing_extensions as _typing_extensions
from typing_extensions import *  # type: ignore

assert _typing.Union is _typing_extensions.Union
assert _typing.Annotated is _typing_extensions.Annotated


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
