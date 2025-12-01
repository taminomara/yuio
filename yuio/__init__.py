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

from yuio import _typing as _t

try:
    from yuio._version import *  # noqa: F403
except ImportError:
    raise ImportError(
        "yuio._version not found. if you are developing locally, "
        "run `pip install -e .` to generate it"
    )

__all__ = [
    "DISABLED",
    "GROUP",
    "MISSING",
    "POSITIONAL",
    "Disabled",
    "Group",
    "Missing",
    "Positional",
    "YuioWarning",
    "enable_internal_logging",
]


class _Placeholders(_enum.Enum):
    DISABLED = "<disabled>"
    MISSING = "<missing>"
    POSITIONAL = "<positional>"
    GROUP = "<group>"

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


Group: _t.TypeAlias = _t.Literal[_Placeholders.GROUP]
"""
Type of the :data:`GROUP` placeholder.

"""

GROUP: Group = _Placeholders.GROUP
"""
Used with :func:`yuio.app.field` to omit arguments from CLI usage.

"""


class YuioWarning(RuntimeWarning):
    """
    Base class for all runtime warnings.

    """


_logger = _logging.getLogger("yuio.internal")
_logger.propagate = False

__stderr_handler = _logging.StreamHandler(_sys.__stderr__)
__stderr_handler.setLevel("CRITICAL")
_logger.addHandler(__stderr_handler)


def enable_internal_logging(
    path: str | None = None, level: str | int | None = None, propagate=None
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

    """

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
        _logging.getLogger("py.warnings").addHandler(file_handler)

    _logging.captureWarnings(True)
    warnings.simplefilter("default", category=YuioWarning)

    if propagate is not None:
        _logging.getLogger("py.warnings").propagate = propagate
        _logger.propagate = propagate


_debug = "YUIO_DEBUG" in _os.environ or "YUIO_DEBUG_FILE" in _os.environ
if _debug:  # pragma: no cover
    enable_internal_logging(
        path=_os.environ.get("YUIO_DEBUG_FILE") or "yuio.log", propagate=False
    )
else:
    warnings.simplefilter("ignore", category=YuioWarning, append=True)
