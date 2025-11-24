# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Utilities
---------

.. autofunction:: to_dash_case


Placeholder values
^^^^^^^^^^^^^^^^^^

These values are used in places where :data:`None` is ambiguous.

.. autodata:: DISABLED

.. autodata:: MISSING

.. autodata:: POSITIONAL

.. autodata:: GROUP

"""

from __future__ import annotations

import abc as _abc
import enum as _enum
import logging as _logging
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap
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
    "SupportsLt",
    "YuioWarning",
    "dedent",
    "enable_internal_logging",
    "to_dash_case",
]


_T_contra = _t.TypeVar("_T_contra", contravariant=True)


class SupportsLt(_t.Protocol[_T_contra]):
    """
    Protocol for objects that can be compared to each other.

    """

    @_abc.abstractmethod
    def __lt__(self, other: _T_contra, /) -> bool: ...


_TO_DASH_CASE_RE = _re.compile(
    r"""
      # We will add a dash (bear with me here):
      [_\s]                             # 1. instead of underscore or space,
      | (                               # 2. OR in the following case:
        (?<!^)                          #   - not at the beginning of the string,
        (                               #   - AND EITHER:
            (?<=[A-Z])(?=[A-Z][a-z])    #     - before case gets lower (`XMLTag` -> `XML-Tag`),
          | (?<=[a-zA-Z])(?![a-zA-Z_])  #     - between a letter and a non-letter (`HTTP20` -> `HTTP-20`),
          | (?<![A-Z_])(?=[A-Z])        #     - between non-uppercase and uppercase letter (`TagXML` -> `Tag-XML`),
        )                               #   - AND ALSO:
        (?!$)                           #     - not at the end of the string.
      )
    """,
    _re.VERBOSE | _re.MULTILINE,
)


def to_dash_case(msg: str, /) -> str:
    """
    Convert ``CamelCase`` or ``snake_case`` identifier to a ``dash-case`` one.

    This function assumes ASCII input, and will not work correctly
    with non-ASCII characters.

    :param msg:
        identifier to convert.
    :returns:
        identifier in ``dash-case``.
    :example:
        ::

            >>> to_dash_case("SomeClass")
            'some-class'
            >>> to_dash_case("HTTP20XMLUberParser")
            'http-20-xml-uber-parser'

    """

    return _TO_DASH_CASE_RE.sub("-", msg).lower()


def dedent(msg: str, /):
    """
    Remove leading indentation from a message and normalize trailing newlines.

    This function is intended to be used with triple-quote string literals,
    such as docstrings. It will remove common indentation from second
    and subsequent lines, then it will strip any leading and trailing whitespaces
    and add a new line at the end.

    :param msg:
        message to dedent.
    :returns:
        normalized message.
    :example:
        ::

            >>> def foo():
            ...     \"""Documentation for function ``foo``.
            ...
            ...     Leading indent is stripped.
            ...     \"""
            ...
            ...     ...

            >>> dedent(foo.__doc__)
            'Documentation for function ``foo``.\\n\\nLeading indent is stripped.\\n'

    """

    if not msg:
        return msg

    first, *rest = msg.splitlines(keepends=True)
    return (first.rstrip() + "\n" + _textwrap.dedent("".join(rest))).strip() + "\n"


_COMMENT_RE = _re.compile(r"^\s*#:(.*)\r?\n?$")
_RST_ROLE_RE = _re.compile(
    r"(?::[\w+.:-]+:|__?)?`((?:[^`\n\\]|\\.)+)`(?::[\w+.:-]+:|__?)?", _re.DOTALL
)
_RST_ROLE_TITLE_RE = _re.compile(
    r"^((?:[^`\n\\]|\\.)*) <(?:[^`\n\\]|\\.)*>$", _re.DOTALL
)
_ESC_RE = _re.compile(r"\\(.)", _re.DOTALL)


def _rst_esc_repl(match: _re.Match[str]):
    symbol = match.group(1)
    if symbol in "\n\r\t\v\b":
        return " "
    return symbol


def _rst_repl(match: _re.Match[str]):
    full: str = match.group(0)
    text: str = match.group(1)
    if full.startswith(":") or full.endswith(":"):
        if title_match := _RST_ROLE_TITLE_RE.match(text):
            text = title_match.group(1)
        elif text.startswith("~"):
            text = text.rsplit(".", maxsplit=1)[-1]
    text = _ESC_RE.sub(_rst_esc_repl, text)
    n_backticks = 0
    cur_n_backticks = 0
    for ch in text:
        if ch == "`":
            cur_n_backticks += 1
        else:
            n_backticks = max(cur_n_backticks, n_backticks)
            cur_n_backticks = 0
    n_backticks = max(cur_n_backticks, n_backticks)
    if not n_backticks:
        return f"`{text}`"
    else:
        bt = "`" * (n_backticks + 1)
        return f"{bt} {text} {bt}"


def _process_docstring(msg: str, /):
    value = dedent(msg).removesuffix("\n")

    if (index := value.find("\n\n")) != -1:
        value = value[:index]

    value = _RST_ROLE_RE.sub(_rst_repl, value)

    if (
        len(value) > 2
        and value[0].isupper()
        and (value[1].islower() or value[1].isspace())
    ):
        value = value[0].lower() + value[1:]
    if value.endswith(".") and not value.endswith(".."):
        value = value[:-1]
    return value


def _find_docs(obj: _t.Any, /) -> dict[str, str]:
    """
    Find documentation for fields of a class.

    Inspects source code of a class and finds docstrings and doc comments (``#:``)
    for variables in its body. Doesn't inspect ``__init``, doesn't return documentation
    for class methods. Returns first paragraph from each docstring, formatted for use
    in CLI help messages.

    """

    # based on code from Sphinx

    import ast
    import inspect
    import itertools

    if (qualname := getattr(obj, "__qualname__", None)) is None:
        # Not a known object.
        return {}

    if "<locals>" in qualname:
        # This will not work as expected!
        return {}

    try:
        sourcelines, _ = inspect.getsourcelines(obj)
    except TypeError:
        return {}

    docs: dict[str, str] = {}

    node = ast.parse(_textwrap.dedent("".join(sourcelines)))
    assert isinstance(node, ast.Module)
    assert len(node.body) == 1
    cdef = node.body[0]

    if isinstance(cdef, ast.ClassDef):
        fields: list[tuple[int, str]] = []
        last_field: str | None = None
        for stmt in cdef.body:
            if (
                last_field
                and isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Constant)
                and isinstance(stmt.value.value, str)
            ):
                docs[last_field] = _process_docstring(stmt.value.value)
            last_field = None
            if isinstance(stmt, ast.AnnAssign):
                target = stmt.target
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = stmt.targets[0]
            else:
                continue
            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                fields.append((stmt.lineno, target.id))
                last_field = target.id
    elif isinstance(cdef, ast.FunctionDef):
        fields = [
            (field.lineno, field.arg)
            for field in itertools.chain(cdef.args.args, cdef.args.kwonlyargs)
        ]
    else:  # pragma: no cover
        return {}

    for pos, name in fields:
        comment_lines: list[str] = []
        for before_line in sourcelines[pos - 2 :: -1]:
            if match := _COMMENT_RE.match(before_line):
                comment_lines.append(match.group(1))
            else:
                break

        if comment_lines:
            docs[name] = _process_docstring("\n".join(reversed(comment_lines)))

    return docs


def _with_slots() -> dict[_t.Literal["slots"], bool]:
    """
    Helper for adding `__slots__` to dataclasses.

    :example:
        .. code-block:: python

            from dataclasses import dataclass


            # Will have `__slots__` in python>=3.11.
            @dataclass(**_with_slots())
            class Example: ...

    """

    return {} if _sys.version_info < (3, 11) else {"slots": True}


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
