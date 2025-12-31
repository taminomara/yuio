# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

# pyright: reportDeprecated=false
# ruff: noqa: F403, F405, I002

import sys as _sys

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
