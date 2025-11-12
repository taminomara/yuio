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

from yuio import _typing as _t

try:
    from yuio._version import *  # noqa: F403
except ImportError:  # pragma: no cover
    raise ImportError(
        "yuio._version not found. if you are developing locally, "
        "run `pip install -e .` to generate it"
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
if _debug:  # pragma: no cover
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
            ...     \"\"\"Documentation for function ``foo``.
            ...
            ...     Leading indent is stripped.
            ...     \"\"\"
            ...
            ...     ...

            >>> dedent(foo.__doc__)
            'Documentation for function ``foo``.\\n\\nLeading indent is stripped.\\n'

    """

    first, *rest = msg.splitlines(keepends=True)
    return (first.strip() + "\n" + _textwrap.dedent("".join(rest))).strip() + "\n"


_COMMENT_RE = _re.compile(r"^\s*#:(.*)\r?\n?$")
_RST_ROLE_RE = _re.compile(
    r"(?::[\w+.:-]+:|__?)?`((?:[^`\n\\]|\\.)+)`(?::[\w+.:-]+:|__?)?"
)
_RST_ROLE_TITLE_RE = _re.compile(r"^((?:[^`\n\\]|\\.)*) <(?:[^`\n\\]|\\.)*>$")


def _process_docstring(msg: str, /):
    value = dedent(msg).removesuffix("\n")

    if (index := value.find("\n\n")) != -1:
        value = value[:index]

    def _rst_repl(match: _re.Match[str]):
        text: str = match.group(1)
        if title_match := _RST_ROLE_TITLE_RE.match(text):
            text = title_match.group(1)
        elif text.startswith("~"):
            text = text.rsplit(".", maxsplit=1)[-1]
        return f"`{text}`"

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
    """
    Helper for adding `__slots__` to dataclasses.

    :example:
        .. code-block:: python

            from dataclasses import dataclass

            # Will have `__slots__` in python>=3.11.
            @dataclass(**_with_slots())
            class Example:
                ...

    """

    return {} if _sys.version_info < (3, 11) else {"slots": True}


@staticmethod
def _join(
    l_msg: str,
    l_args: tuple[_t.Any, ...],
    r_msg: str,
    r_args: tuple[_t.Any, ...],
    /,
) -> tuple[str, tuple[_t.Any, ...]]:
    """
    Join two possibly ``%``-formatted strings without formatting them.

    This function joins two strings and their format args while ensuring that
    ``%``-formatting doesn't break.

    Yuio follows behavior of :mod:`logging` when it comes to ``%``-formatting:
    it only formats the message if it got non-empty ``args`` tuple. This means
    that to join two strings we need to escape ``%`` symbols in one of them
    if one of the ``args`` tuples is empty.

    :param l_msg:
        left message.
    :param l_args:
        arguments for ``%``-formatting the left message.
    :param r_msg:
        right message.
    :param r_args:
        arguments for ``%``-formatting the right message.
    :returns:
        concatenation of left and right messages and new formatting arguments.

    """

    if l_args and not r_args:
        r_msg = r_msg.replace("%", "%%")
    elif not l_args and r_args:
        l_msg = l_msg.replace("%", "%%")
    return l_msg + r_msg, l_args + r_args


def _to_msg(
    msg: str | Exception, args: tuple[_t.Any, ...] | None = None
) -> tuple[str, tuple[_t.Any, ...]]:
    """
    Helper for converting io/error params to ``msg, args`` tuple.

    """

    if isinstance(msg, FormattedExceptionMixin):
        if args:
            raise ValueError("exception can't have format arguments")
        return msg.msg, msg.args
    elif isinstance(msg, Exception):
        if args:
            raise ValueError("exception can't have format arguments")
        return "%s", (msg,)
    elif args is None:
        return msg, ()
    else:
        return msg, args


class FormattedExceptionMixin:
    """FormattedExceptionMixin(msg: str, /, *args: _t.Any)
    FormattedExceptionMixin(err: Exception, /)

    Mixin for exceptions with markdown-formatted messages.

    ..warning::

        This mixin should appear before :class:`Exception` in method resolution
        order. Put it first in the list of base classes (see example below).

    :param msg:
        error message.
    :param args:
        arguments for ``%``-formatting the error message.
    :param err:
        you can pass an error object to constructor,
        in which case new error will take message from the given one.
    :example:
        .. code-block:: python

            class MyError(FormattedExceptionMixin, Exception):
                pass

    """

    @_t.overload
    def __init__(self, msg: str, /, *args: _t.Any): ...
    @_t.overload
    def __init__(self, err: Exception, /): ...
    def __init__(self, msg: str | Exception, /, *args: _t.Any):
        msg, args = _to_msg(msg, args)

        self.msg: str = msg
        """
        Error message.

        """

        self.args: tuple[_t.Any, ...] = args
        """
        Arguments for ``%``-formatting the error message.

        """

    def __repr__(self) -> str:
        args = ", ".join(map(repr, self.args))
        return f"{self.__class__.__name__}({self.msg!r}, {args})"

    def __str__(self) -> str:
        msg = self.msg
        if msg and self.args:
            msg %= self.args
        return msg or super().__str__()

    @_t.overload
    def with_prefix(self, msg: str, /, *args: _t.Any): ...
    @_t.overload
    def with_prefix(self, err: Exception, /): ...
    def with_prefix(self, msg: str | Exception, /, *args: _t.Any) -> _t.Self:
        """with_prefix(msg: str, /, *args: _t.Any) -> typing.Self
        with_prefix(err: Exception, /) -> typing.Self

        Indent existing message and add a prefix before it.

        :param msg:
            prefix message.
        :param args:
            arguments for ``%``-formatting the prefix message.
        :returns:
            new exception with new message.
        :example:
            .. skip: next

            ::

                >>> try:
                ...     result = parser.parse("-5")
                ... except yuio.parse.ParsingError as e:
                ...     yuio.io.error(e.with_prefix("Can't parse `config.threads`:"))
                Can't parse `config.threads`:
                  Value `-5` should be greater than 0

        """

        msg, args = _to_msg(msg, args)
        msg, args = _join(msg + "\n", args, _textwrap.indent(self.msg, "  "), self.args)
        return self.__class__(msg, *args)

    @_t.overload
    def with_suffix(self, msg: str, /, *args: _t.Any): ...
    @_t.overload
    def with_suffix(self, err: Exception, /): ...
    def with_suffix(self, msg: str | Exception, /, *args: _t.Any) -> _t.Self:
        """with_suffix(msg: str, /, *args: _t.Any) -> typing.Self
        with_suffix(err: Exception, /) -> typing.Self

        Indent a suffix and append it to the error message.

        :param msg:
            suffix message.
        :param args:
            arguments for ``%``-formatting the suffix message.
        :returns:
            new exception with new message.

        """

        msg, args = _to_msg(msg, args)
        msg, args = _join(self.msg + "\n", self.args, _textwrap.indent(msg, "  "), args)
        return self.__class__(msg, *args)


class _Placeholders(_enum.Enum):
    DISABLED = "<disabled>"
    MISSING = "<missing>"
    POSITIONAL = "<positional>"
    GROUP = "<group>"

    def __bool__(self) -> _t.Literal[False]:
        return False

    def __repr__(self):
        return f"yuio.{self.name}"

    def __str__(self) -> str:
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


Group: _t.TypeAlias = _t.Literal[_Placeholders.GROUP]
"""
Type of the :data:`GROUP` placeholder.

"""

GROUP: Group = _Placeholders.GROUP
"""
Used with :func:`yuio.app.field` to omit arguments from CLI usage.

"""
