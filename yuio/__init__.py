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

import abc as _abc
import enum as _enum
import logging as _logging
import os as _os
import re as _re
import sys as _sys
import textwrap as _textwrap

from yuio import _t

try:
    from yuio._version import __version__, __version_tuple__
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
    """Protocol for objects that can be compared to each other."""

    @_abc.abstractmethod
    def __lt__(self, other: _T_contra, /) -> bool:
        ...


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
    """Convert ``CamelCase`` or ``snake_case`` identifier to a ``dash-case`` one.

    This function assumes ASCII input, and will not work correctly
    with non-ASCII characters.

    """

    return _TO_DASH_CASE_RE.sub("-", s).lower()


_COMMENT_RE = _re.compile(r"^\s*#: ?(.*)\r?\n?$")


def _find_docs(obj: _t.Any) -> _t.Dict[str, str]:
    # based on code from Sphinx

    import ast
    import inspect
    import itertools

    if "<locals>" in obj.__qualname__:
        # This will not work as expected!
        return {}

    sourcelines, _ = inspect.getsourcelines(obj)

    docs: _t.Dict[str, str] = {}

    node = ast.parse(_textwrap.dedent("".join(sourcelines)))
    assert isinstance(node, ast.Module)
    assert len(node.body) == 1
    cdef = node.body[0]

    if isinstance(cdef, ast.ClassDef):
        fields = [
            (stmt.lineno, stmt.target.id)
            for stmt in cdef.body
            if (
                isinstance(stmt, ast.AnnAssign)
                and isinstance(stmt.target, ast.Name)
                and not stmt.target.id.startswith("_")
            )
        ]
    elif isinstance(cdef, ast.FunctionDef):
        fields = [
            (field.lineno, field.arg)
            for field in itertools.chain(cdef.args.args, cdef.args.kwonlyargs)
        ]
    else:
        return {}

    for pos, name in fields:
        comment_lines: _t.List[str] = []
        for before_line in sourcelines[pos - 2 :: -1]:
            if match := _COMMENT_RE.match(before_line):
                comment_lines.append(_textwrap.dedent(match.group(1)))
            else:
                break

        if comment_lines:
            docs[name] = "\n".join(reversed(comment_lines))

    return docs


def _with_slots() -> _t.Dict[_t.Literal["slots"], bool]:
    return {} if _sys.version_info < (3, 11) else {"slots": True}


class _Placeholders(_enum.Enum):
    DISABLED = "<disabled>"
    MISSING = "<missing>"
    POSITIONAL = "<positional>"

    def __repr__(self):
        return self.value


#: Type of the :data:`DISABLED` placeholder.
Disabled: _t.TypeAlias = _t.Literal[_Placeholders.DISABLED]
#: Indicates that some functionality is disabled.
DISABLED: Disabled = _Placeholders.DISABLED

#: Type of the :data:`MISSING` placeholder.
Missing: _t.TypeAlias = _t.Literal[_Placeholders.MISSING]
#: Indicates that some value is missing.
MISSING: Missing = _Placeholders.MISSING

#: Type of the :data:`POSITIONAL` placeholder.
Positional: _t.TypeAlias = _t.Literal[_Placeholders.POSITIONAL]
#: Used with :func:`field` to enable positional arguments.
POSITIONAL: Positional = _Placeholders.POSITIONAL
