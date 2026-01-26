# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
.. autofunction:: to_dash_case

.. autofunction:: dedent

.. autofunction:: find_docs

.. autofunction:: commonprefix

.. autoclass:: UserString

    .. automethod:: _wrap

.. autoclass:: ClosedIO

"""

from __future__ import annotations

import io as _io
import re as _re
import textwrap as _textwrap
import weakref

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "ClosedIO",
    "UserString",
    "commonprefix",
    "dedent",
    "find_docs",
    "to_dash_case",
]

_UNPRINTABLE = "".join([chr(i) for i in range(32)]) + "\x7f"
_UNPRINTABLE_TRANS = str.maketrans(_UNPRINTABLE, " " * len(_UNPRINTABLE))
_UNPRINTABLE_RE = r"[" + _re.escape(_UNPRINTABLE) + "]"
_UNPRINTABLE_RE_WITHOUT_NL = r"[" + _re.escape(_UNPRINTABLE.replace("\n", "")) + "]"

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
_DOCS_CACHE: weakref.WeakKeyDictionary[_t.Any, dict[str, str]] = (
    weakref.WeakKeyDictionary()
)


def find_docs(obj: _t.Any, /) -> dict[str, str]:
    """
    Find documentation for fields of a class.

    Inspects source code of a class and finds docstrings and doc comments (``#:``)
    for variables in its body. Doesn't inspect ``__init__``, doesn't return documentation
    for class methods.

    """

    # Based on code from Sphinx, two clause BSD license.
    # See https://github.com/sphinx-doc/sphinx/blob/master/LICENSE.rst.

    try:
        return _DOCS_CACHE[obj]
    except KeyError:
        pass
    except TypeError:
        return {}

    import ast
    import inspect
    import itertools

    if (qualname := getattr(obj, "__qualname__", None)) is None:
        # Not a known object.
        _DOCS_CACHE[obj] = {}
        return {}

    if "<locals>" in qualname:
        # This will not work as expected!
        _DOCS_CACHE[obj] = {}
        return {}

    try:
        sourcelines, _ = inspect.getsourcelines(obj)
    except TypeError:
        _DOCS_CACHE[obj] = {}
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
                docs[last_field] = dedent(stmt.value.value).removesuffix("\n")
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
        _DOCS_CACHE[obj] = {}
        return {}

    for pos, name in fields:
        if name in docs:
            continue

        comment_lines: list[str] = []
        for before_line in sourcelines[pos - 2 :: -1]:
            if match := _COMMENT_RE.match(before_line):
                comment_lines.append(match.group(1))
            else:
                break

        if comment_lines:
            docs[name] = dedent("\n".join(reversed(comment_lines))).removesuffix("\n")

    _DOCS_CACHE[obj] = docs
    return docs


def commonprefix(m: _t.Collection[str]) -> str:
    if not m:
        return ""
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


if TYPE_CHECKING:

    class _FormatMapMapping(_t.Protocol):
        def __getitem__(self, key: str, /) -> _t.Any: ...

    class _TranslateTable(_t.Protocol):
        def __getitem__(self, key: int, /) -> str | int | None: ...


class UserString(str):
    """
    Base class for user string.

    This class is similar to :class:`collections.UserString`, but actually derived
    from string, with customizable wrapping semantics, and returns custom string
    instances from all string methods (:class:`collections.UserString` doesn't
    wrap strings returned from :meth:`str.split` and similar).

    .. tip::

        When deriving from this class, add ``__slots__`` to avoid making a string
        with a ``__dict__`` property.

    """

    __slots__ = ()

    def _wrap(self, data: str) -> _t.Self:
        """
        Wrap raw string that resulted from an operation on this instance into another
        instance of :class:`UserString`.

        Override this method if you need to preserve some internal state during
        operations.

        By default, this simply creates an instance of ``self.__class__`` with the
        given string.

        """

        return self.__class__(data)

    def __add__(self, value: str, /) -> _t.Self:
        return self._wrap(super().__add__(value))

    def __format__(self, format_spec: str, /) -> _t.Self:
        return self._wrap(super().__format__(format_spec))

    def __getitem__(self, key: _t.SupportsIndex | slice, /) -> _t.Self:
        return self._wrap(super().__getitem__(key))

    def __mod__(self, value: _t.Any, /) -> _t.Self:
        return self._wrap(super().__mod__(value))

    def __mul__(self, value: _t.SupportsIndex, /) -> _t.Self:
        return self._wrap(super().__mul__(value))

    def __rmul__(self, value: _t.SupportsIndex, /) -> _t.Self:
        return self._wrap(super().__rmul__(value))

    def capitalize(self) -> _t.Self:
        return self._wrap(super().capitalize())

    def casefold(self) -> _t.Self:
        return self._wrap(super().casefold())

    def center(self, width: _t.SupportsIndex, fillchar: str = " ", /) -> _t.Self:
        return self._wrap(super().center(width))

    def expandtabs(self, tabsize: _t.SupportsIndex = 8) -> _t.Self:
        return self._wrap(super().expandtabs(tabsize))

    def format_map(self, mapping: _FormatMapMapping, /) -> _t.Self:
        return self._wrap(super().format_map(mapping))

    def format(self, *args: object, **kwargs: object) -> _t.Self:
        return self._wrap(super().format(*args, **kwargs))

    def join(self, iterable: _t.Iterable[str], /) -> _t.Self:
        return self._wrap(super().join(iterable))

    def ljust(self, width: _t.SupportsIndex, fillchar: str = " ", /) -> _t.Self:
        return self._wrap(super().ljust(width, fillchar))

    def lower(self) -> _t.Self:
        return self._wrap(super().lower())

    def lstrip(self, chars: str | None = None, /) -> _t.Self:
        return self._wrap(super().lstrip(chars))

    def partition(self, sep: str, /) -> tuple[_t.Self, _t.Self, _t.Self]:
        l, c, r = super().partition(sep)
        return self._wrap(l), self._wrap(c), self._wrap(r)

    def removeprefix(self, prefix: str, /) -> _t.Self:
        return self._wrap(super().removeprefix(prefix))

    def removesuffix(self, suffix: str, /) -> _t.Self:
        return self._wrap(super().removesuffix(suffix))

    def replace(self, old: str, new: str, count: _t.SupportsIndex = -1, /) -> _t.Self:
        return self._wrap(super().replace(old, new, count))

    def rjust(self, width: _t.SupportsIndex, fillchar: str = " ", /) -> _t.Self:
        return self._wrap(super().rjust(width, fillchar))

    def rpartition(self, sep: str, /) -> tuple[_t.Self, _t.Self, _t.Self]:
        l, c, r = super().rpartition(sep)
        return self._wrap(l), self._wrap(c), self._wrap(r)

    def rsplit(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, sep: str | None = None, maxsplit: _t.SupportsIndex = -1
    ) -> list[_t.Self]:
        return [self._wrap(part) for part in super().rsplit(sep, maxsplit)]

    def rstrip(self, chars: str | None = None, /) -> _t.Self:
        return self._wrap(super().rstrip(chars))

    def split(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, sep: str | None = None, maxsplit: _t.SupportsIndex = -1
    ) -> list[_t.Self]:
        return [self._wrap(part) for part in super().split(sep, maxsplit)]

    def splitlines(  # pyright: ignore[reportIncompatibleMethodOverride]
        self, keepends: bool = False
    ) -> list[_t.Self]:
        return [self._wrap(part) for part in super().splitlines(keepends)]

    def strip(self, chars: str | None = None, /) -> _t.Self:
        return self._wrap(super().strip(chars))

    def swapcase(self) -> _t.Self:
        return self._wrap(super().swapcase())

    def title(self) -> _t.Self:
        return self._wrap(super().title())

    def translate(self, table: _TranslateTable, /) -> _t.Self:
        return self._wrap(super().translate(table))

    def upper(self) -> _t.Self:
        return self._wrap(super().upper())

    def zfill(self, width: _t.SupportsIndex, /) -> _t.Self:
        return self._wrap(super().zfill(width))


class ClosedIO(_io.TextIOBase, _t.TextIO):  # type: ignore
    """
    Dummy stream that's always closed.

    """

    def __init__(self) -> None:
        super().__init__()
        self.close()
