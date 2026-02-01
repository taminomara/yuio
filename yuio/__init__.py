# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Yuio library. See documentation at https://yuio.readthedocs.io/.

"""

from __future__ import annotations

import enum as _enum
import logging as _logging
import os as _os
import sys as _sys
import warnings

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

if TYPE_CHECKING:
    import yuio.string

try:
    from yuio._version import *  # noqa: F403
except ImportError:
    raise ImportError(
        "yuio._version not found. if you are developing locally, "
        "run `pip install -e .` to generate it"
    )

__all__ = [
    "COLLAPSE",
    "DISABLED",
    "MISSING",
    "POSITIONAL",
    "Collapse",
    "Disabled",
    "Missing",
    "Positional",
    "PrettyException",
    "YuioWarning",
    "enable_internal_logging",
]


class _Placeholders(_enum.Enum):
    DISABLED = "<disabled>"
    MISSING = "<missing>"
    POSITIONAL = "<positional>"
    COLLAPSE = "<group>"

    def __bool__(self) -> _t.Literal[False]:
        return False  # pragma: no cover

    def __repr__(self):
        return f"yuio.{self.name}"  # pragma: no cover

    def __str__(self) -> str:
        return self.value  # pragma: no cover


Disabled: _t.TypeAlias = _t.Literal[_Placeholders.DISABLED]
"""
Type of the :data:`DISABLED` placeholder.

"""

DISABLED: Disabled = _Placeholders.DISABLED
"""
Indicates that some functionality is disabled.

"""


Missing: _t.TypeAlias = _t.Literal[_Placeholders.MISSING]
"""
Type of the :data:`MISSING` placeholder.

"""

MISSING: Missing = _Placeholders.MISSING
"""
Indicates that some value is missing.

"""


Positional: _t.TypeAlias = _t.Literal[_Placeholders.POSITIONAL]
"""
Type of the :data:`POSITIONAL` placeholder.

"""

POSITIONAL: Positional = _Placeholders.POSITIONAL
"""
Used with :func:`yuio.app.field` to enable positional arguments.

"""


Collapse: _t.TypeAlias = _t.Literal[_Placeholders.COLLAPSE]
"""
Type of the :data:`COLLAPSE` placeholder.

"""

COLLAPSE: Collapse = _Placeholders.COLLAPSE
"""
Used with :func:`yuio.app.field` to omit arguments from CLI usage
and to collapse argument groups.

"""

GROUP = COLLAPSE  # Deprecated.


class YuioWarning(RuntimeWarning):
    """
    Base class for all runtime warnings.

    """


class PrettyException(Exception):
    """PrettyException(msg: typing.LiteralString, /, *args: typing.Any)
    PrettyException(msg: ~string.templatelib.Template, /)
    PrettyException(msg: str, /)

    Base class for pretty-printable exceptions.

    :param msg:
        message to format.
    :param args:
        arguments for ``%``-formatting the message.
    :example:
        .. invisible-code-block: python

            import yuio

        .. code-block:: python

            class MyError(yuio.PrettyException):
                pass


            try:
                ...
                raise MyError("A formatted <c b>error message</c>")
                ...
            except MyError as e:
                yuio.io.error_with_tb(e)

    """

    @_t.overload
    def __init__(self, msg: _t.LiteralString, /, *args): ...
    @_t.overload
    def __init__(self, msg: yuio.string.ToColorable | None = None, /): ...
    def __init__(self, *args):
        self.args = args

    def __rich_repr__(self) -> yuio.string.RichReprResult:
        yield from ((None, arg) for arg in self.args)

    def __str__(self) -> str:
        return str(self.to_colorable())

    def __colorized_str__(
        self, ctx: yuio.string.ReprContext
    ) -> yuio.string.ColorizedString:
        return ctx.str(self.to_colorable())

    def to_colorable(self) -> yuio.string.Colorable:
        """
        Return a colorable object with this exception's message.

        """

        if not self.args:
            return ""

        import yuio.string

        return yuio.string._to_colorable(self.args[0], self.args[1:])


_logger = _logging.getLogger("yuio.internal")
_logger.setLevel(_logging.DEBUG)
_logger.propagate = False

__stderr_handler = _logging.StreamHandler(_sys.__stderr__)
__stderr_handler.setLevel(_logging.CRITICAL)
_logger.addHandler(__stderr_handler)


def enable_internal_logging(
    path: str | None = None,
    level: str | int | None = None,
    propagate=None,
    add_handler: bool = False,
):  # pragma: no cover
    """
    Enable Yuio's internal logging.

    This function enables :func:`logging.captureWarnings`, and enables printing
    of :class:`YuioWarning` messages, and sets up logging channels ``yuio.internal``
    and ``py.warning``.

    :param path:
        if given, adds handlers that output internal log messages to the given file.
    :param level:
        configures logging level for file handler. Default is ``DEBUG``.
    :param propagate:
        if given, enables or disables log message propagation from ``yuio.internal``
        and ``py.warning`` to the root logger.
    :param add_handler:
        if :data:`True`, adds yuio handler to the logging. This is useful if you wish
        to see yuio log before main setup.

    """

    warn_logger = _logging.getLogger("py.warnings")

    if path:
        if level is None:
            level = _os.environ.get("YUIO_DEBUG", "").strip().upper() or "DEBUG"
        if level in ["1", "Y", "YES", "TRUE"]:
            level = "DEBUG"
        file_handler = _logging.FileHandler(path, delay=True)
        file_handler.setFormatter(
            _logging.Formatter("%(filename)s:%(lineno)d: %(levelname)s: %(message)s")
        )
        file_handler.setLevel(level)
        _logger.addHandler(file_handler)
        warn_logger.addHandler(file_handler)

    _logging.captureWarnings(True)
    warnings.simplefilter("default", category=YuioWarning)

    if propagate is not None:
        warn_logger.propagate = propagate
        _logger.propagate = propagate

    if add_handler:
        import yuio.io

        if not any(
            isinstance(handler, yuio.io.Handler) for handler in _logger.handlers
        ):
            _logger.addHandler(yuio.io.Handler())
        if not any(
            isinstance(handler, yuio.io.Handler) for handler in warn_logger.handlers
        ):
            warn_logger.addHandler(yuio.io.Handler())


_debug = "YUIO_DEBUG" in _os.environ or "YUIO_DEBUG_FILE" in _os.environ
if _debug:  # pragma: no cover
    enable_internal_logging(path=_os.environ.get("YUIO_DEBUG_FILE"), add_handler=True)
elif hasattr(_sys, "ps1"):
    enable_internal_logging(add_handler=True)
else:
    warnings.simplefilter("ignore", category=YuioWarning, append=True)
