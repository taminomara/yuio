"""
Utilities
---------

.. autoclass:: SupportsLt

.. autofunction:: to_dash_case


Placeholder values
^^^^^^^^^^^^^^^^^^

These values are used in places where :data:`None` is ambiguous.

.. autodata:: DISABLED

.. autodata:: MISSING

.. autodata:: POSITIONAL

.. autodata:: Disabled

.. autodata:: Missing

.. autodata:: Positional

"""

from __future__ import annotations

import abc as _abc
import enum as _enum
import logging as _logging
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from yuio import _typing as _t

try:
    from yuio._version import *
except ImportError:
    raise ImportError(
        "yuio._version not found. if you are developing locally, "
        "run `pip install -e .[test,doc]` to generate it"
    )

__all__ = [
    "SupportsLt",
    "to_dash_case",
    "Disabled",
    "DISABLED",
    "Missing",
    "MISSING",
    "Positional",
    "POSITIONAL",
]

_logger = _logging.getLogger("yuio.internal")
_logger.setLevel("DEBUG")  # handlers will do all the filtering
_logger.propagate = False

_debug = "YUIO_DEBUG" in _os.environ
if _debug:
    __level = _os.environ.get("YUIO_DEBUG_LEVEL", "DEBUG")
    __file = _os.environ.get("YUIO_DEBUG_FILE") or "yuio.log"
    __file_handler = _logging.FileHandler(__file, delay=True)
    __file_handler.setLevel(__level)
    _logger.addHandler(__file_handler)

__stderr_handler = _logging.StreamHandler(_sys.__stderr__)
__stderr_handler.setLevel("CRITICAL")
_logger.addHandler(__stderr_handler)


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
      _                                 # 1. instead of underscore,
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


def to_dash_case(s: str, /) -> str:
    """
    Convert ``CamelCase`` or ``snake_case`` identifier to a ``dash-case`` one.

    This function assumes ASCII input, and will not work correctly
    with non-ASCII characters.

    """

    return _TO_DASH_CASE_RE.sub("-", s).lower()


_COMMENT_RE = _re.compile(r"^\s*#:(.*)\r?\n?$")
_RST_ROLE_RE = _re.compile(r"(?::[\w+.:-]+:|__?)`((?:[^`\n\\]|\\.)+)`")
_RST_ROLE_TITLE_RE = _re.compile(r"^((?:[^`\n\\]|\\.)*) <(?:[^`\n\\]|\\.)*>$")


def _rst_repl(match: _re.Match[str]):
    text: str = match.group(1)
    if title_match := _RST_ROLE_TITLE_RE.match(text):
        text = title_match.group(1)
    elif text.startswith("~"):
        text = text.rsplit(".", maxsplit=1)[-1]
    return f"`{text}`"


def _process_docstring(s: str):
    first, *rest = s.splitlines(keepends=True)
    value = (first.strip() + "\n" + _textwrap.dedent("".join(rest))).strip()

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


def _find_docs(obj: _t.Any) -> dict[str, str]:
    # based on code from Sphinx

    import ast
    import inspect
    import itertools

    if "<locals>" in obj.__qualname__:
        # This will not work as expected!
        return {}

    sourcelines, _ = inspect.getsourcelines(obj)

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
    else:
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
    return {} if _sys.version_info < (3, 11) else {"slots": True}


class _Placeholders(_enum.Enum):
    DISABLED = "<disabled>"
    MISSING = "<missing>"
    POSITIONAL = "<positional>"
    OMIT = "<omit>"

    def __repr__(self):
        return self.value


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


Omit: _t.TypeAlias = _t.Literal[_Placeholders.OMIT]
"""
Type of the :data:`OMIT` placeholder.

"""

OMIT: Omit = _Placeholders.OMIT
"""
Used with :func:`yuio.app.field` to omit arguments from CLI usage.

"""
