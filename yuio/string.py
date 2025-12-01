# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
The higher-level :mod:`io` module uses strings with xml-like color
tags to store information about line formatting. Here, on the lower level,
these strings are parsed and transformed to :class:`ColorizedString`\\ s:

This is a low-level module upon which :mod:`yuio.io` builds
its higher-level abstraction.

.. autoclass:: ColorizedString
   :members:


Parsing color tags
------------------

.. autofunction:: colorize

.. autofunction:: strip_color_tags


Pretty ``str`` and ``repr``
---------------------------

.. autofunction:: colorized_str

.. autofunction:: colorized_repr


.. _pretty-protocol:

Pretty printing protocol
------------------------

Yuio searches for special methods on your objects when rendering them.

``__colorized_str__``, ``__colorized_repr__``
    This should be a method that accepts a single positional argument,
    :class:`ReprContext`, and returns a :class:`ColorizedString`.

    .. warning::

        Don't call :func:`colorized_repr` or :func:`colorized_str` from these
        implementations, as this may result in infinite recursion. Instead,
        use :meth:`ReprContext.repr` and :meth:`ReprContext.str`.

    .. tip::

        Prefer ``__rich_repr__`` for simpler use cases, and only use
        ``__colorized_repr__`` when you need something advanced.

    **Example:**

    .. code-block:: python

        class MyObject:
            def __init__(self, value):
                self.value = value

            def __colorized_str__(self, ctx: yuio.string.ReprContext):
                result = yuio.string.ColorizedString()
                result += ctx.theme.get_color("magenta")
                result += "MyObject"
                result += ctx.theme.get_color("normal")
                result += "MyObject"
                result += ctx.repr(self.value)
                result += ctx.theme.get_color("normal")
                result += ")"
                return result

``__rich_repr__``
    This method doesn't have any arguments. It should return an iterable of tuples
    describing object's arguments:

    -   ``yield name, value`` will generate a keyword argument,
    -   ``yield name, value, default`` will generate a keyword argument if value
        is not equal to default,
    -   if ``name`` is :data:`None`, it will generate positional argument instead.

    See the `Rich library documentation`__ for more info.

    __ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

    **Example:**

    .. code-block:: python

        class MyObject:
            def __init__(self, value1, value2):
                self.value1 = value1
                self.value2 = value2

            def __rich_repr__(self) -> yuio.string.RichReprResult:
                yield "value1", self.value1
                yield "value2", self.value2

.. autoclass:: ReprContext
    :members:

.. type:: RichReprResult
    :canonical: typing.Iterable[tuple[typing.Any] | tuple[str | None, typing.Any] | tuple[str | None, typing.Any, typing.Any]]

    This is an alias similar to ``rich.repr.Result``, but stricter: it only
    allows tuples, not arbitrary values.

    This is done to avoid bugs where you yield a single value which happens to contain
    a tuple, and Yuio (or Rich) renders it as a named argument.


.. type:: ColorizedStrProtocol

    Protocol for objects that define ``__colorized_str__`` method.

.. type:: ColorizedReprProtocol

    Protocol for objects that define ``__colorized_repr__`` method.

.. type:: RichReprProtocol

    Protocol for objects that define ``__rich_repr__`` method.

.. type:: Printable

    Any object that supports printing.

    Technically, any object supports colorized printing because we'll fall back
    to ``__repr__`` or ``__str__`` if there are no special methods on it.

    However, we don't use :class:`typing.Any` to avoid potential errors.

.. type:: Colorable
    :canonical: Printable | ColorizedStrProtocol | ColorizedReprProtocol | RichReprProtocol | str | BaseException

    An object that supports colorized printing.

.. autofunction:: repr_from_rich


.. _formatting-utilities:

Formatting utilities
--------------------

.. autoclass:: Format
    :members:

.. autoclass:: Repr
    :members:

.. autoclass:: TypeRepr
    :members:

.. autoclass:: JoinStr
    :members:
    :inherited-members:

.. autoclass:: JoinRepr
    :members:
    :inherited-members:

.. autofunction:: And

.. autofunction:: Or

.. autoclass:: Stack
    :members:

.. autoclass:: Indent
    :members:

.. autoclass:: Md
    :members:

.. autoclass:: Hl
    :members:

.. autoclass:: Wrap
    :members:

.. autoclass:: WithBaseColor
    :members:

.. autoclass:: Hr
    :members:

.. autoclass:: ColorableBase
    :members:


Helper types
------------

.. type:: AnyString
    :canonical: str | ~yuio.color.Color | ColorizedString | NoWrapMarker | typing.Iterable[AnyString]

    Any string (i.e. a :class:`str`, a raw colorized string,
    or a normal colorized string).

.. autodata:: NO_WRAP_START

.. autodata:: NO_WRAP_END

.. type:: NoWrapMarker
          NoWrapStart
          NoWrapEnd

    Type of a no-wrap marker.

.. autofunction:: line_width

"""

from __future__ import annotations

import abc
import collections
import dataclasses
import functools
import os
import re
import reprlib
import shutil
import string
import types
import unicodedata
from enum import Enum

import yuio
import yuio.color
import yuio.theme
from yuio import _typing as _t
from yuio.color import Color as _Color
from yuio.util import UserString as _UserString
from yuio.util import dedent as _dedent

if _t.TYPE_CHECKING:
    import yuio.md

__all__ = [
    "NO_WRAP_END",
    "NO_WRAP_START",
    "And",
    "AnyString",
    "Colorable",
    "ColorableBase",
    "ColorizedReprProtocol",
    "ColorizedStrProtocol",
    "ColorizedString",
    "Esc",
    "Format",
    "Hl",
    "Hr",
    "Indent",
    "JoinRepr",
    "JoinStr",
    "Md",
    "NoWrapEnd",
    "NoWrapMarker",
    "NoWrapStart",
    "Or",
    "Printable",
    "Repr",
    "ReprContext",
    "RichReprProtocol",
    "RichReprResult",
    "Stack",
    "TypeRepr",
    "WithBaseColor",
    "Wrap",
    "colorize",
    "colorized_repr",
    "colorized_str",
    "line_width",
    "repr_from_rich",
    "strip_color_tags",
]


def line_width(s: str, /) -> int:
    """
    Calculates string width when the string is displayed
    in a terminal.

    This function makes effort to detect wide characters
    such as emojis. If does not, however, work correctly
    with extended grapheme clusters, and so it may fail
    for emojis with modifiers, or other complex characters.

    Example where it fails is ``👩🏽‍💻``. It consists
    of four code points:

    - Unicode Character `WOMAN` (``U+1F469``, ``👩``),
    - Unicode Character `EMOJI MODIFIER FITZPATRICK TYPE-4` (``U+1F3FD``),
    - Unicode Character `ZERO WIDTH JOINER` (``U+200D``),
    - Unicode Character `PERSONAL COMPUTER` (``U+1F4BB``, ``💻``).

    Since :func:`line_width` can't understand that these code points
    are combined into a single emoji, it treats them separately,
    resulting in answer `6` (`2` for every code point except `ZERO WIDTH JOINER`)::

        >>> line_width("\U0001f469\U0001f3fd\U0000200d\U0001f4bb")
        6

    In all fairness, detecting how much space such an emoji will take
    is not so straight forward, as that will depend on unicode capabilities
    of a specific terminal. Since a lot of terminals will not handle such emojis
    correctly, I've decided to go with this simplistic implementation.

    """

    # Note: it may be better to bundle `wcwidth` and use it instead of the code below.
    # However, there is an issue that `wcwidth`'s results are not additive.
    # In the above example, `wcswidth('👩🏽‍💻')` will see that it is two-spaces wide,
    # while `sum(wcwidth(c) for c in '👩🏽‍💻')` will report that it is four-spaces wide.
    # To render it properly, the widget will have to be aware of extended grapheme
    # clusters, and generally this will be a lot of headache. Since most terminals
    # won't handle these edge cases correctly, I don't want to bother.

    if s.isascii():
        # Fast path. Note that our renderer replaces unprintable characters
        # with spaces, so ascii strings always have width equal to their length.
        return len(s)
    else:
        # Long path. It kinda works, but not always, but most of the times...
        return sum(
            (unicodedata.east_asian_width(c) in "WF") + 1
            for c in s
            if unicodedata.category(c)[0] not in "MC"
        )


RichReprResult: _t.TypeAlias = _t.Iterable[
    tuple[_t.Any] | tuple[str | None, _t.Any] | tuple[str | None, _t.Any, _t.Any]
]
"""
Similar to ``rich.repr.Result``, but only allows tuples, not arbitrary values.

"""


@_t.runtime_checkable
class ColorizedStrProtocol(_t.Protocol):
    """
    Protocol for objects that define ``__colorized_str__`` method.

    """

    @abc.abstractmethod
    def __colorized_str__(self, ctx: ReprContext, /) -> ColorizedString: ...


@_t.runtime_checkable
class ColorizedReprProtocol(_t.Protocol):
    """
    Protocol for objects that define ``__colorized_repr__`` method.

    """

    @abc.abstractmethod
    def __colorized_repr__(self, ctx: ReprContext, /) -> ColorizedString: ...


@_t.runtime_checkable
class RichReprProtocol(_t.Protocol):
    """
    Protocol for objects that define ``__rich_repr__`` method.

    """

    @abc.abstractmethod
    def __rich_repr__(self) -> _t.Iterable[_t.Any]: ...


Printable = _t.NewType("Printable", object)
"""
Any object that supports printing.

Technically, any object supports colorized printing because we'll fall back
to ``__repr__`` or ``__str__`` if there are no special methods on it.

However, we don't use :class:`typing.Any` to avoid potential errors.

"""


Colorable: _t.TypeAlias = (
    Printable
    | ColorizedStrProtocol
    | ColorizedReprProtocol
    | RichReprProtocol
    | str
    | BaseException
)
"""
Any object that supports colorized printing.

This can be a string, and exception, or any object that follows
:class:`ColorableProtocol`. Additionally, you can pass any object that has
``__repr__``, but you'll have to wrap it into :type:`Printable` to confirm
your intent to print it.

"""


RichReprProtocolT = _t.TypeVar("RichReprProtocolT", bound=RichReprProtocol)


def repr_from_rich(cls: type[RichReprProtocolT], /) -> type[RichReprProtocolT]:
    """repr_from_rich(cls: RichReprProtocol) -> RichReprProtocol

    A decorator that generates ``__repr__`` from ``__rich_repr__``.

    :param cls:
        class that needs ``__repr__``.
    :returns:
        always returns ``cls``.
    :example:
        .. code-block:: python

            @yuio.string.repr_from_rich
            class MyClass:
                def __init__(self, value):
                    self.value = value

                def __rich_repr__(self) -> yuio.string.RichReprResult:
                    yield "value", self.value

        ::

            >>> print(repr(MyClass("plush!")))
            MyClass(value='plush!')


    """

    setattr(cls, "__repr__", _repr_from_rich_impl)
    return cls


def _repr_from_rich_impl(self: RichReprProtocol):
    if rich_repr := getattr(self, "__rich_repr__", None):
        args = rich_repr()
        angular = getattr(rich_repr, "angular", False)
    else:
        args = []
        angular = False

    if args is None:
        args = []  # `rich_repr` didn't yield?

    res = []

    if angular:
        res.append("<")
    res.append(self.__class__.__name__)
    if angular:
        res.append(" ")
    else:
        res.append("(")

    sep = False
    for arg in args:
        if isinstance(arg, tuple):
            if len(arg) == 3:
                key, child, default = arg
                if default == child:
                    continue
            elif len(arg) == 2:
                key, child = arg
            elif len(arg) == 1:
                key, child = None, arg[0]
            else:
                key, child = None, arg
        else:
            key, child = None, arg

        if sep:
            res.append(" " if angular else ", ")
        if key:
            res.append(str(key))
            res.append("=")
        res.append(repr(child))
        sep = True

    res.append(">" if angular else ")")

    return "".join(res)


class _NoWrapMarker(Enum):
    """
    Type for a no-wrap marker.

    """

    NO_WRAP_START = "<no_wrap_start>"
    NO_WRAP_END = "<no_wrap_end>"

    def __repr__(self):
        return f"yuio.string.{self.name}"  # pragma: no cover

    def __str__(self) -> str:
        return self.value  # pragma: no cover


NoWrapStart: _t.TypeAlias = _t.Literal[_NoWrapMarker.NO_WRAP_START]
"""
Type of the :data:`NO_WRAP_START` placeholder.

"""

NO_WRAP_START: NoWrapStart = _NoWrapMarker.NO_WRAP_START
"""
Indicates start of a no-wrap region in a :class:`ColorizedString`.

"""


NoWrapEnd: _t.TypeAlias = _t.Literal[_NoWrapMarker.NO_WRAP_END]
"""
Type of the :data:`NO_WRAP_END` placeholder.

"""

NO_WRAP_END: NoWrapEnd = _NoWrapMarker.NO_WRAP_END
"""
Indicates end of a no-wrap region in a :class:`ColorizedString`.

"""

NoWrapMarker: _t.TypeAlias = NoWrapStart | NoWrapEnd
"""
Type of a no-wrap marker.

"""


@_t.final
@repr_from_rich
class ColorizedString:
    """ColorizedString(content: AnyString = '', /)

    A string with colors.

    This class is a wrapper over a list of strings, colors, and no-wrap markers.
    Each color applies to strings after it, right until the next color.

    :class:`ColorizedString` supports some basic string operations.
    Most notably, it supports wide-character-aware wrapping
    (see :meth:`~ColorizedString.wrap`),
    and ``%``-like formatting (see :meth:`~ColorizedString.percent_format`).

    Unlike :class:`str`, :class:`ColorizedString` is mutable through
    the ``+=`` operator and ``append``/``extend`` methods.

    :param content:
        initial content of the string. Can be :class:`str`, color, no-wrap marker,
        or another colorized string.


    **String combination semantics**

    When you append a :class:`str`, it will take on color and no-wrap semantics
    according to the last appended color and no-wrap marker.

    When you append another :class:`ColorizedString`, it will not change its colors
    based on the last appended color, nor will it affect colors of the consequent
    strings. If appended :class:`ColorizedString` had an unterminated no-wrap region,
    this region will be terminated after appending.

    Thus, appending a colorized string does not change current color
    or no-wrap setting::

        >>> s1 = yuio.string.ColorizedString()
        >>> s1 += yuio.color.Color.FORE_RED
        >>> s1 += yuio.string.NO_WRAP_START
        >>> s1 += "red nowrap text"
        >>> s1  # doctest: +NORMALIZE_WHITESPACE
        ColorizedString([yuio.string.NO_WRAP_START,
                         <Color fore=<RED>>,
                         'red nowrap text'])

        >>> s2 = yuio.string.ColorizedString()
        >>> s2 += yuio.color.Color.FORE_GREEN
        >>> s2 += "green text "
        >>> s2 += s1
        >>> s2 += " green text continues"
        >>> s2  # doctest: +NORMALIZE_WHITESPACE
        ColorizedString([<Color fore=<GREEN>>,
                         'green text ',
                         yuio.string.NO_WRAP_START,
                         <Color fore=<RED>>,
                         'red nowrap text',
                         yuio.string.NO_WRAP_END,
                         <Color fore=<GREEN>>,
                         ' green text continues'])

    """

    # Invariants:
    #
    # - there is always a color before the first string in `_parts`.
    # - there are no empty strings in `_parts`.
    # - for every pair of colors in `_parts`, there is a string between them
    #   (i.e. there are no colors that don't highlight anything).
    # - every color in `_parts` is different from the previous one
    #   (i.e. there are no redundant color markers).
    # - `start-no-wrap` and `end-no-wrap` markers form a balanced bracket sequence,
    #   except for the last `start-no-wrap`, which may have no corresponding
    #   `end-no-wrap` yet.
    # - no-wrap regions can't be nested.
    # - fo every pair of (start-no-wrap, end-no-wrap) markers, there is a string
    #   between them (i.e. no empty no-wrap regions).

    def __init__(
        self,
        content: AnyString = "",
        /,
        *,
        _isolate_colors: bool = True,
    ):
        if isinstance(content, ColorizedString):
            self._parts = content._parts.copy()
            self._last_color = content._last_color
            self._active_color = content._active_color
            self._explicit_newline = content._explicit_newline
            self._len = content._len
            self._has_no_wrap = content._has_no_wrap
            if (width := content.__dict__.get("width", None)) is not None:
                self.__dict__["width"] = width
        else:
            self._parts: list[_Color | NoWrapMarker | str] = []
            self._active_color = _Color.NONE
            self._last_color: _Color | None = None
            self._explicit_newline: str = ""
            self._len = 0
            self._has_no_wrap = False

            if not _isolate_colors:
                # Prevent adding `_Color.NONE` to the front of the string.
                self._last_color = self._active_color

            if content:
                self += content

    @property
    def explicit_newline(self) -> str:
        """
        Explicit newline indicates that a line of a wrapped text
        was broken because the original text contained a new line character.

        See :meth:`~ColorizedString.wrap` for details.

        """

        return self._explicit_newline

    @property
    def active_color(self) -> _Color:
        """
        Last color appended to this string.

        """

        return self._active_color

    @functools.cached_property
    def width(self) -> int:
        """
        String width when the string is displayed in a terminal.

        See :func:`line_width` for more information.

        """

        return sum(line_width(s) for s in self._parts if isinstance(s, str))

    @property
    def len(self) -> int:
        """
        Line length in bytes, ignoring all colors.

        """

        return self._len

    def append_color(self, color: _Color, /):
        """
        Append new color to this string.

        This operation is lazy, the color will be appended if a non-empty string
        is appended after it.

        :param color:
            color to append.

        """

        self._active_color = color

    def append_str(self, s: str, /):
        """
        Append new plain string to this string.

        :param s:
            plain string to append.

        """

        if not s:
            return
        if self._last_color != self._active_color:
            self._parts.append(self._active_color)
            self._last_color = self._active_color
        self._parts.append(s)
        self._len += len(s)
        self.__dict__.pop("width", None)

    def append_colorized_str(self, s: ColorizedString, /):
        """
        Append new colorized string to this string.

        :param s:
            colorized string to append.

        """
        if not s:
            # Nothing to append.
            return

        parts = s._parts

        # Cleanup color at the beginning of the string.
        for i, part in enumerate(parts):
            if part in (NO_WRAP_START, NO_WRAP_END):
                continue
            elif isinstance(part, str):  # pragma: no cover
                # We never hit this branch in normal conditions because colorized
                # strings always start with a color. The only way to trigger this
                # branch is to tamper with `_parts` and break colorized string
                # invariants.
                break

            # First color in the appended string is the same as our last color.
            # We can remove it without changing the outcome.
            if part == self._last_color:
                if i == 0:
                    parts = parts[i + 1 :]
                else:
                    parts = parts[:i] + parts[i + 1 :]

            break

        if self._has_no_wrap:
            # We're in a no-wrap sequence, we don't need any more markers.
            self._parts.extend(
                part for part in parts if part not in (NO_WRAP_START, NO_WRAP_END)
            )
        else:
            # We're not in a no-wrap sequence. We preserve no-wrap regions from the
            # appended string, but we make sure that they don't affect anything
            # appended after.
            self._parts.extend(parts)
            if s._has_no_wrap:
                self._has_no_wrap = True
                self.end_no_wrap()

        self._last_color = s._last_color
        self._len += s._len
        if (lw := self.__dict__.get("width")) and (rw := s.__dict__.get("width")):
            self.__dict__["width"] = lw + rw
        else:
            self.__dict__.pop("width", None)

    def append_no_wrap(self, m: NoWrapMarker, /):
        """
        Append a no-wrap marker.

        :param m:
            no-wrap marker, will be dispatched
            to :meth:`~ColorizedString.start_no_wrap`
            or :meth:`~ColorizedString.end_no_wrap`.

        """

        if m is NO_WRAP_START:
            self.start_no_wrap()
        else:
            self.end_no_wrap()

    def start_no_wrap(self):
        """
        Start a no-wrap region.

        String parts within no-wrap regions are not wrapped on spaces; they can be
        hard-wrapped if ``break_long_nowrap_words`` is :data:`True`. Whitespaces and
        newlines in no-wrap regions are preserved regardless of ``preserve_spaces``
        and ``preserve_newlines`` settings.

        """

        if self._has_no_wrap:
            return

        self._has_no_wrap = True
        self._parts.append(NO_WRAP_START)

    def end_no_wrap(self):
        """
        End a no-wrap region.

        """

        if not self._has_no_wrap:
            return

        if self._parts and self._parts[-1] is NO_WRAP_START:
            # Empty no-wrap sequence, just remove it.
            self._parts.pop()
        else:
            self._parts.append(NO_WRAP_END)

        self._has_no_wrap = False

    def extend(
        self,
        parts: _t.Iterable[str | ColorizedString | _Color | NoWrapMarker],
        /,
    ):
        """
        Extend string from iterable of raw parts.

        :param parts:
            raw parts that will be appended to the string.

        """

        for part in parts:
            self += part

    def copy(self) -> ColorizedString:
        """
        Copy this string.

        :returns:
            copy of the string.

        """

        return ColorizedString(self)

    def _split_at(self, i: int, /) -> tuple[ColorizedString, ColorizedString]:
        l, r = ColorizedString(), ColorizedString()
        l.extend(self._parts[:i])
        r._active_color = l._active_color
        r._has_no_wrap = l._has_no_wrap
        r.extend(self._parts[i:])
        r._active_color = self._active_color
        return l, r

    def with_base_color(self, base_color: _Color) -> ColorizedString:
        """
        Apply the given color "under" all parts of this string. That is, all colors
        in this string will be combined with this color on the left:
        ``base_color | color``.

        :param base_color:
            color that will be added under the string.
        :returns:
            new string with changed colors, or current string if base color
            is :attr:`~yuio.color.Color.NONE`.
        :example:
            ::

                >>> s1 = yuio.string.ColorizedString([
                ...     "part 1",
                ...     yuio.color.Color.FORE_GREEN,
                ...     "part 2",
                ... ])
                >>> s2 = s1.with_base_color(
                ...     yuio.color.Color.FORE_RED
                ...     | yuio.color.Color.STYLE_BOLD
                ... )
                >>> s2  # doctest: +NORMALIZE_WHITESPACE
                ColorizedString([<Color fore=<RED> bold=True>,
                                 'part 1',
                                 <Color fore=<GREEN> bold=True>,
                                 'part 2'])

        """

        if base_color == _Color.NONE:
            return self

        res = ColorizedString()

        for part in self._parts:
            if isinstance(part, _Color):
                res.append_color(base_color | part)
            else:
                res += part
        res._active_color = base_color | self._active_color
        if self._last_color is not None:
            res._last_color = base_color | self._last_color

        return res

    def process_colors(self, color_support: yuio.color.ColorSupport, /) -> list[str]:
        """
        Convert colors in this string to ANSI escape sequences.

        :param term:
            terminal that will be used to print the resulting string.
        :returns:
            raw parts of colorized string with all colors converted to ANSI
            escape sequences.

        """

        if color_support == yuio.color.ColorSupport.NONE:
            return [part for part in self._parts if isinstance(part, str)]
        else:
            parts = [
                part if isinstance(part, str) else yuio.term.color_to_code(part, term)
                for part in self._parts
                if part not in (NO_WRAP_START, NO_WRAP_END)
            ]
            if self._last_color != _Color.NONE:
                parts.append(yuio.term.color_to_code(_Color.NONE, term))
            return parts

    def wrap(
        self,
        width: int,
        /,
        *,
        preserve_spaces: bool = False,
        preserve_newlines: bool = True,
        break_long_words: bool = True,
        break_long_nowrap_words: bool = False,
        overflow: _t.Literal[False] | str = False,
        indent: AnyString | int = "",
        continuation_indent: AnyString | int | None = None,
    ) -> list[ColorizedString]:
        """
        Wrap a long line of text into multiple lines.

        :param preserve_spaces:
            if set to :data:`True`, all spaces are preserved.
            Otherwise, consecutive spaces are collapsed into a single space.

            Note that tabs always treated as a single whitespace.
        :param preserve_newlines:
            if set to :data:`True` (default), text is additionally wrapped
            on newline sequences. When this happens, the newline sequence that wrapped
            the line will be placed into :attr:`~ColorizedString.explicit_newline`.

            If set to :data:`False`, newline sequences are treated as whitespaces.

            .. list-table:: Whitespace sequences
                :header-rows: 1
                :stub-columns: 1

                * - Sequence
                  - ``preserve_newlines``
                  - Result
                * - ``\\n``, ``\\r\\n``, ``\\r``
                  - ``False``
                  - Treated as a single whitespace.
                * - ``\\n``, ``\\r\\n``, ``\\r``
                  - ``True``
                  - Creates a new line.
                * - ``\\v``, ``\\v\\n``, ``\\v\\r\\n``, ``\\v\\r``
                  - Any
                  - Always creates a new line.

        :param break_long_words:
            if set to :data:`True` (default), words that don't fit into a single line
            will be split into multiple lines.
        :param break_long_nowrap_words:
            if set to :data:`True`, words in no-wrap regions that don't fit
            into a single line will be split into multiple lines.
        :param overflow:
            a symbol that will be added to a line if it doesn't fit the given width.
            Pass :data:`False` to keep the overflowing lines without modification.
        :param indent:
            a string that will be prepended before the first line.
        :param continuation_indent:
            a string that will be prepended before all subsequent lines.
        :returns:
            a list of individual lines without newline characters at the end.

        """

        return _TextWrapper(
            width,
            preserve_spaces=preserve_spaces,
            preserve_newlines=preserve_newlines,
            break_long_words=break_long_words,
            break_long_nowrap_words=break_long_nowrap_words,
            overflow=overflow,
            indent=indent,
            continuation_indent=continuation_indent,
        ).wrap(self)

    def indent(
        self,
        indent: AnyString | int = "  ",
        continuation_indent: AnyString | int | None = None,
    ) -> ColorizedString:
        """
        Indent this string.

        :param indent:
            this will be prepended to the first line in the string.
            Defaults to two spaces.
        :param continuation_indent:
            this will be prepended to subsequent lines in the string.
            Defaults to ``indent``.
        :returns:
            indented string.

        """

        if isinstance(indent, int):
            indent = ColorizedString(" " * indent)
        else:
            indent = ColorizedString(indent)
        if continuation_indent is None:
            continuation_indent = indent
        elif isinstance(continuation_indent, int):
            continuation_indent = ColorizedString(" " * continuation_indent)
        else:
            continuation_indent = ColorizedString(continuation_indent)

        if not indent and not continuation_indent:
            return self

        res = ColorizedString()

        needs_indent = True
        for part in self._parts:
            if not isinstance(part, str) or isinstance(part, Esc):
                res += part
                continue

            for line in _WORDSEP_NL_RE.split(part):
                if not line:
                    continue
                if needs_indent:
                    res.append_colorized_str(indent)
                    indent = continuation_indent
                res.append_str(line)
                needs_indent = line.endswith(("\n", "\r", "\v"))

        return res

    def percent_format(
        self, args: _t.Any, ctx: yuio.theme.Theme | ReprContext | None = None
    ) -> ColorizedString:
        """
        Format colorized string as if with ``%``-formatting
        (i.e. `printf-style formatting`__).

        __ https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting

        :param args:
            arguments for formatting. Can be either a tuple of a mapping. Any other
            value will be converted to a tuple of one element.
        :param ctx:
            :class:`ReprContext` or theme that will be passed to ``__colorized_str__``
            and ``__colorized_repr__``. If not given, uses theme
            from :func:`yuio.io.get_theme`.
        :returns:
            formatted string.
        :raises:
            :class:`TypeError`, :class:`ValueError`, :class:`KeyError` if formatting
            fails.

        """

        return _percent_format(self, args, ctx)

    def __len__(self) -> int:
        return self.len

    def __bool__(self) -> bool:
        return self.len > 0

    def __iter__(self) -> _t.Iterator[_Color | NoWrapMarker | str]:
        return self._parts.__iter__()

    def __add__(self, rhs: AnyString) -> ColorizedString:
        copy = self.copy()
        copy += rhs
        return copy

    def __radd__(self, lhs: AnyString) -> ColorizedString:
        copy = ColorizedString(lhs)
        copy += self
        return copy

    def __iadd__(self, rhs: AnyString) -> ColorizedString:
        if isinstance(rhs, str):
            self.append_str(rhs)
        elif isinstance(rhs, ColorizedString):
            self.append_colorized_str(rhs)
        elif isinstance(rhs, _Color):
            self.append_color(rhs)
        elif rhs in (NO_WRAP_START, NO_WRAP_END):
            self.append_no_wrap(rhs)
        else:
            self.extend(rhs)

        return self

    def __eq__(self, value: object) -> bool:
        if isinstance(value, ColorizedString):
            return self._parts == value._parts
        else:
            return NotImplemented

    def __ne__(self, value: object) -> bool:
        return not (self == value)

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._parts
        yield "explicit_newline", self._explicit_newline, ""

    def __str__(self) -> str:
        return "".join(c for c in self._parts if isinstance(c, str))

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return self


AnyString: _t.TypeAlias = (
    str
    | ColorizedString
    | _Color
    | NoWrapMarker
    | _t.Iterable[str | ColorizedString | _Color | NoWrapMarker]
)
"""
Any string (i.e. a :class:`str`, a raw colorized string, or a normal colorized string).

"""


_S_SYNTAX = re.compile(
    r"""
        %                               # Percent
        (?:\((?P<mapping>[^)]*)\))?     # Mapping key
        (?P<flag>[#0\-+ ]*)             # Conversion Flag
        (?P<width>\*|\d+)?              # Field width
        (?:\.(?P<precision>\*|\d*))?    # Precision
        [hlL]?                          # Unused length modifier
        (?P<format>.)                   # Conversion type
    """,
    re.VERBOSE,
)


def _percent_format(
    s: ColorizedString, args: object, ctx: yuio.theme.Theme | ReprContext | None
) -> ColorizedString:
    if ctx is None:
        import yuio.io

        ctx = yuio.io.get_theme()
    if not isinstance(ctx, ReprContext):
        ctx = ReprContext(theme=ctx)
    seen_mapping = False
    arg_index = 0
    res = ColorizedString()
    for part in s:
        if isinstance(part, str):
            pos = 0
            for match in _S_SYNTAX.finditer(part):
                if pos < match.start():
                    res.append_str(part[pos : match.start()])
                seen_mapping = seen_mapping or bool(match.group("mapping"))
                last_color = res.active_color
                arg_index, replaced = _percent_format_repl(
                    match, args, arg_index, last_color, ctx
                )
                res += replaced
                res.append_color(last_color)
                pos = match.end()
            if pos < len(part):
                res.append_str(part[pos:])
        else:
            res += part

    if (isinstance(args, tuple) and arg_index < len(args)) or (
        not isinstance(args, tuple)
        and (
            not hasattr(args, "__getitem__")
            or isinstance(args, (str, bytes, bytearray))
        )
        and not seen_mapping
        and not arg_index
    ):
        raise TypeError("not all arguments converted during string formatting")

    return res


def _percent_format_repl(
    match: _t.StrReMatch,
    args: object,
    arg_index: int,
    base_color: _Color,
    ctx: ReprContext,
) -> tuple[int, str | ColorizedString]:
    if match.group("format") == "%":
        if match.group(0) != "%%":
            raise ValueError("unsupported format character '%'")
        return arg_index, "%"

    if match.group("format") in "rs":
        return _percent_format_repl_str(match, args, arg_index, base_color, ctx)

    if mapping := match.group("mapping"):
        try:
            fmt_arg = args[mapping]  # type: ignore
        except TypeError:
            raise TypeError("format requires a mapping") from None
        fmt_arg, added_color = _unwrap_base_color(fmt_arg, ctx.theme)
        if added_color:
            fmt_args = {mapping: fmt_arg}
        else:
            fmt_args = args
    elif isinstance(args, tuple):
        try:
            fmt_arg = args[arg_index]
        except IndexError:
            raise TypeError("not enough arguments for format string")
        fmt_arg, added_color = _unwrap_base_color(fmt_arg, ctx.theme)
        begin = arg_index + 1
        end = arg_index = (
            arg_index
            + 1
            + (match.group("width") == "*")
            + (match.group("precision") == "*")
        )
        fmt_args = (fmt_arg,) + args[begin:end]
    elif arg_index == 0:
        fmt_args, added_color = _unwrap_base_color(args, ctx.theme)
        arg_index += 1
    else:
        raise TypeError("not enough arguments for format string")

    fmt = match.group(0) % fmt_args
    if added_color:
        added_color = ctx.theme.to_color(added_color)
        fmt = ColorizedString([base_color | added_color, fmt])
    return arg_index, fmt


def _unwrap_base_color(x, theme: yuio.theme.Theme):
    color = None
    while isinstance(x, WithBaseColor):
        x, base_color = x._msg, x._base_color
        base_color = theme.to_color(base_color)
        if color:
            color = color | base_color
        else:
            color = base_color
    else:
        return x, color


def _percent_format_repl_str(
    match: _t.StrReMatch,
    args: object,
    arg_index: int,
    base_color: _Color,
    ctx: ReprContext,
) -> tuple[int, str | ColorizedString]:
    if width_s := match.group("width"):
        if width_s == "*":
            if not isinstance(args, tuple):
                raise TypeError("* wants int")
            try:
                width = args[arg_index]
                arg_index += 1
            except (KeyError, IndexError):
                raise TypeError("not enough arguments for format string")
            if not isinstance(width, int):
                raise TypeError("* wants int")
        else:
            width = int(width_s)
    else:
        width = None

    if precision_s := match.group("precision"):
        if precision_s == "*":
            if not isinstance(args, tuple):
                raise TypeError("* wants int")
            try:
                precision = args[arg_index]
                arg_index += 1
            except (KeyError, IndexError):
                raise TypeError("not enough arguments for format string")
            if not isinstance(precision, int):
                raise TypeError("* wants int")
        else:
            precision = int(precision_s)
    else:
        precision = None

    if mapping := match.group("mapping"):
        try:
            fmt_arg = args[mapping]  # type: ignore
        except TypeError:
            raise TypeError("format requires a mapping") from None
    elif isinstance(args, tuple):
        try:
            fmt_arg = args[arg_index]
            arg_index += 1
        except IndexError:
            raise TypeError("not enough arguments for format string") from None
    elif arg_index == 0:
        fmt_arg = args
        arg_index += 1
    else:
        raise TypeError("not enough arguments for format string")

    flag = match.group("flag")
    multiline = "+" in flag
    highlighted = "#" in flag
    if match.group("format") == "r":
        res = ctx.repr(fmt_arg, multiline=multiline, highlighted=highlighted)
    else:
        res = ctx.str(fmt_arg, multiline=multiline, highlighted=highlighted)

    if precision is not None and res.width > precision:
        cut = ColorizedString()
        for part in res:
            if precision <= 0:
                break
            if isinstance(part, str):
                part_width = line_width(part)
                if part_width <= precision:
                    cut.append_str(part)
                    precision -= part_width
                elif part.isascii():
                    cut.append_str(part[:precision])
                    break
                else:
                    for j, ch in enumerate(part):
                        precision -= line_width(ch)
                        if precision == 0:
                            cut.append_str(part[: j + 1])
                            break
                        elif precision < 0:
                            cut.append_str(part[:j])
                            cut.append_str(" ")
                            break
                    break
            else:
                cut += part
        res = cut

    if width is not None:
        spacing = " " * (abs(width) - res.width)
        if spacing:
            if match.group("flag") == "-" or width < 0:
                res = res + spacing
            else:
                res = spacing + res

    return arg_index, res.with_base_color(base_color)


__TAG_RE = re.compile(
    r"""
          <c (?P<tag_open>[a-z0-9 _/@:-]+)>         # _Color tag open.
        | </c>                                      # _Color tag close.
        | \\(?P<punct>[%(punct)s])                  # Escape character.
        | (?<!`)(`+)(?!`)(?P<code>.*?)(?<!`)\3(?!`) # Inline code block (backticks).
    """
    % {"punct": re.escape(string.punctuation)},
    re.VERBOSE | re.MULTILINE,
)
__NEG_NUM_RE = re.compile(r"^-(0x[0-9a-fA-F]+|0b[01]+|\d+(e[+-]?\d+)?)$")
__FLAG_RE = re.compile(r"^-[-a-zA-Z0-9_]*$")


def colorize(
    line: str,
    /,
    *args: _t.Any,
    ctx: yuio.theme.Theme | ReprContext | None = None,
    default_color: _Color | str = _Color.NONE,
    parse_cli_flags_in_backticks: bool = False,
) -> ColorizedString:
    """
    Parse color tags and produce a colorized string.

    Apply ``default_color`` to the entire paragraph, and process color tags
    and backticks within it.

    :param line:
        text to colorize.
    :param args:
        if given, string will be ``%``-formatted after parsing.
    :param ctx:
        :class:`ReprContext` or theme that will be used to look up color tags.
        If not given, uses theme from :func:`yuio.io.get_theme`.
    :param default_color:
        color or color tag to apply to the entire text.
    :returns:
        a colorized string.

    """

    if ctx is None:
        import yuio.io

        ctx = yuio.io.get_theme()
    if not isinstance(ctx, ReprContext):
        ctx = ReprContext(theme=ctx)

    default_color = ctx.theme.to_color(default_color)

    res = ColorizedString(default_color)

    stack = [default_color]

    last_pos = 0
    for tag in __TAG_RE.finditer(line):
        res.append_str(line[last_pos : tag.start()])
        last_pos = tag.end()

        if name := tag.group("tag_open"):
            color = stack[-1] | ctx.theme.get_color(name)
            res.append_color(color)
            stack.append(color)
        elif code := tag.group("code"):
            code = code.replace("\n", " ")
            if code.startswith(" ") and code.endswith(" ") and not code.isspace():
                code = code[1:-1]
            if (
                parse_cli_flags_in_backticks
                and __FLAG_RE.match(code)
                and not __NEG_NUM_RE.match(code)
            ):
                res.append_color(stack[-1] | ctx.theme.get_color("flag"))
            else:
                res.append_color(stack[-1] | ctx.theme.get_color("code"))
            res.start_no_wrap()
            res.append_str(code)
            res.end_no_wrap()
            res.append_color(stack[-1])
        elif punct := tag.group("punct"):
            res.append_str(punct)
        elif len(stack) > 1:
            stack.pop()
            res.append_color(stack[-1])

    res.append_str(line[last_pos:])

    if args:
        return res.percent_format(args, ctx)
    else:
        return res


def strip_color_tags(s: str) -> str:
    """
    Remove all color tags from a string.

    """

    raw: list[str] = []

    last_pos = 0
    for tag in __TAG_RE.finditer(s):
        raw.append(s[last_pos : tag.start()])
        last_pos = tag.end()

        if code := tag.group("code"):
            code = code.replace("\n", " ")
            if code.startswith(" ") and code.endswith(" ") and not code.isspace():
                code = code[1:-1]
            raw.append(code)
        elif punct := tag.group("punct"):
            raw.append(punct)

    raw.append(s[last_pos:])

    return "".join(raw)


class Esc(_UserString):
    """
    A string that can't be broken during word wrapping even
    if ``break_long_nowrap_words`` is :data:`True`.

    """

    __slots__ = ()


_SPACE_TRANS = str.maketrans("\r\n\t\v\b\f", "      ")

_WORD_PUNCT = r'[\w!"\'&.,?]'
_LETTER = r"[^\d\W]"
_NOWHITESPACE = r"[^ \r\n\t\v\b\f]"

# Copied from textwrap with some modifications in newline handling
_WORDSEP_RE = re.compile(
    r"""
    ( # newlines and line feeds are matched one-by-one
        (?:\r\n|\r|\n|\v\r\n|\v\r|\v\n|\v)
    | # any whitespace
        [ \t\b\f]+
    | # em-dash between words
        (?<=%(wp)s) -{2,} (?=\w)
    | # word, possibly hyphenated
        %(nws)s+? (?:
        # hyphenated word
            -(?: (?<=%(lt)s{2}-) | (?<=%(lt)s-%(lt)s-))
            (?= %(lt)s -? %(lt)s)
        | # end of word
            (?=[ \r\n\t\v\b\f]|\Z)
        | # em-dash
            (?<=%(wp)s) (?=-{2,}\w)
        )
    )"""
    % {"wp": _WORD_PUNCT, "lt": _LETTER, "nws": _NOWHITESPACE},
    re.VERBOSE,
)
_WORDSEP_NL_RE = re.compile(r"(\r\n|\r|\n|\v\r\n|\v\r|\v\n|\v)")


class _TextWrapper:
    def __init__(
        self,
        width: float,
        /,
        *,
        preserve_spaces: bool,
        preserve_newlines: bool,
        break_long_words: bool,
        break_long_nowrap_words: bool,
        overflow: _t.Literal[False] | str,
        indent: AnyString | int,
        continuation_indent: AnyString | int | None,
    ):
        self.width: float = width  # Actual type is `int | +inf`.
        self.preserve_spaces: bool = preserve_spaces
        self.preserve_newlines: bool = preserve_newlines
        self.break_long_words: bool = break_long_words
        self.break_long_nowrap_words: bool = break_long_nowrap_words
        self.overflow: _t.Literal[False] | str = overflow

        if isinstance(indent, int):
            self.indent = ColorizedString(" " * indent)
        else:
            self.indent = ColorizedString(indent)
        if continuation_indent is None:
            self.continuation_indent = self.indent
        elif isinstance(continuation_indent, int):
            self.continuation_indent = ColorizedString(" " * continuation_indent)
        else:
            self.continuation_indent = ColorizedString(continuation_indent)

        self.lines: list[ColorizedString] = []

        self.current_line = ColorizedString()
        if self.indent:
            self.current_line += self.indent
        self.current_line_width: int = self.indent.width
        self.at_line_start: bool = True
        self.has_ellipsis: bool = False
        self.need_space_before_word = False

        self.nowrap_start_index = None
        self.nowrap_start_width = 0
        self.nowrap_start_added_space = False

    def _flush_line(self, explicit_newline=""):
        self.current_line._explicit_newline = explicit_newline
        self.lines.append(self.current_line)

        self.current_line = ColorizedString(self.current_line.active_color)

        if self.continuation_indent:
            self.current_line += self.continuation_indent

        self.current_line_width: int = self.continuation_indent.width
        self.at_line_start = True
        self.has_ellipsis = False
        self.nowrap_start_index = None
        self.nowrap_start_width = 0
        self.nowrap_start_added_space = False
        self.need_space_before_word = False

    def _flush_line_part(self):
        assert self.nowrap_start_index is not None
        self.current_line, tail = self.current_line._split_at(self.nowrap_start_index)
        tail_width = self.current_line_width - self.nowrap_start_width
        if (
            self.nowrap_start_added_space
            and self.current_line._parts
            and self.current_line._parts[-1] == " "
        ):
            # Remove space that was added before no-wrap sequence.
            self.current_line._parts.pop()
        self._flush_line()
        self.current_line += tail
        self.current_line.append_color(tail.active_color)
        self.current_line_width += tail_width

    def _append_word(self, word: str, word_width: int):
        if (
            self.overflow is not False
            and self.current_line_width + word_width > self.width
        ):
            if isinstance(word, Esc):
                if self.overflow:
                    self._add_ellipsis()
                return

            word_head_len = word_head_width = 0

            for c in word:
                c_width = line_width(c)
                if self.current_line_width + word_head_width + c_width > self.width:
                    break
                word_head_len += 1
                word_head_width += c_width

            if word_head_len:
                self.current_line.append_str(word[:word_head_len])
                self.at_line_start = False
                self.has_ellipsis = False
                self.current_line_width += word_head_width

            if self.overflow:
                self._add_ellipsis()
        else:
            self.current_line.append_str(word)
            self.current_line_width += word_width
            self.has_ellipsis = False
            self.at_line_start = False

    def _add_ellipsis(self):
        if self.has_ellipsis:
            # Already has an ellipsis.
            return

        if self.current_line_width + 1 <= self.width:
            # There's enough space on this line to add new ellipsis.
            self.current_line.append_str(str(self.overflow))
            self.current_line_width += 1
            self.at_line_start = False
            self.has_ellipsis = True
        elif not self.at_line_start:
            # Modify last word on this line, if there is any.
            parts = self.current_line._parts
            for i in range(len(parts) - 1, -1, -1):
                part = parts[i]
                if isinstance(part, str):
                    if not isinstance(part, Esc):
                        parts[i] = f"{part[:-1]}{self.overflow}"
                        self.has_ellipsis = True
                    return

    def _append_word_with_breaks(self, word: str, word_width: int):
        while self.current_line_width + word_width > self.width:
            word_head_len = word_head_width = 0

            for c in word:
                c_width = line_width(c)
                if self.current_line_width + word_head_width + c_width > self.width:
                    break
                word_head_len += 1
                word_head_width += c_width

            if self.at_line_start and not word_head_len:
                if self.overflow:
                    return
                else:
                    word_head_len = 1
                    word_head_width += line_width(word[:1])

            self._append_word(word[:word_head_len], word_head_width)

            word = word[word_head_len:]
            word_width -= word_head_width

            self._flush_line()

        if word:
            self._append_word(word, word_width)

    def wrap(self, text: ColorizedString) -> list[ColorizedString]:
        nowrap = False

        for part in text:
            if isinstance(part, _Color):
                if (
                    self.need_space_before_word
                    and self.current_line_width + self.need_space_before_word
                    < self.width
                ):
                    # Make sure any whitespace that was added before color
                    # is flushed. If it doesn't fit, we just forget it: the line
                    # will be wrapped soon anyways.
                    self._append_word(" ", 1)
                self.need_space_before_word = False
                self.current_line.append_color(part)
                continue
            elif part is NO_WRAP_START:
                if nowrap:  # pragma: no cover
                    continue
                if (
                    self.need_space_before_word
                    and self.current_line_width + self.need_space_before_word
                    < self.width
                ):
                    # Make sure any whitespace that was added before no-wrap
                    # is flushed. If it doesn't fit, we just forget it: the line
                    # will be wrapped soon anyways.
                    self._append_word(" ", 1)
                    self.nowrap_start_added_space = True
                else:
                    self.nowrap_start_added_space = False
                self.need_space_before_word = False
                if self.at_line_start:
                    self.nowrap_start_index = None
                    self.nowrap_start_width = 0
                else:
                    self.nowrap_start_index = len(self.current_line._parts)
                    self.nowrap_start_width = self.current_line_width
                nowrap = True
                continue
            elif part is NO_WRAP_END:
                nowrap = False
                self.nowrap_start_index = None
                self.nowrap_start_width = 0
                self.nowrap_start_added_space = False
                continue

            esc = False
            if isinstance(part, Esc):
                words = [Esc(part.translate(_SPACE_TRANS))]
                esc = True
            elif nowrap:
                words = _WORDSEP_NL_RE.split(part)
            else:
                words = _WORDSEP_RE.split(part)

            for word in words:
                if not word:
                    # `_WORDSEP_RE` produces empty strings, skip them.
                    continue

                if word.startswith(("\v", "\r", "\n")):
                    # `_WORDSEP_RE` yields one newline sequence at a time, we don't
                    # need to split the word further.
                    if nowrap or self.preserve_newlines or word.startswith("\v"):
                        self._flush_line(explicit_newline=word)
                        continue
                    else:
                        # Treat any newline sequence as a single space.
                        word = " "

                isspace = not esc and word.isspace()
                if isspace:
                    if (
                        # Spaces are preserved in no-wrap sequences.
                        nowrap
                        # Spaces are explicitly preserved.
                        or self.preserve_spaces
                        # We preserve indentation even if `preserve_spaces` is `False`.
                        # We need to check that the previous line ended with an
                        # explicit newline, otherwise this is not an indent.
                        or (
                            self.at_line_start
                            and (not self.lines or self.lines[-1].explicit_newline)
                        )
                    ):
                        word = word.translate(_SPACE_TRANS)
                    else:
                        self.need_space_before_word = True
                        continue

                word_width = line_width(word)

                if self._try_fit_word(word, word_width):
                    # Word fits onto the current line.
                    continue

                if self.nowrap_start_index is not None:
                    # Move the entire no-wrap sequence onto the new line.
                    self._flush_line_part()

                    if self._try_fit_word(word, word_width):
                        # Word fits onto the current line after we've moved
                        # no-wrap sequence. Nothing more to do.
                        continue

                if (
                    not self.at_line_start
                    and (
                        # Spaces can be broken anywhere, so we don't break line
                        # for them: `_append_word_with_breaks` will do it for us.
                        # Note: `esc` implies `not isspace`, so all `esc` words
                        # outside of no-wrap sequences are handled by this check.
                        (not nowrap and not isspace)
                        # No-wrap sequences are broken in the middle of any word,
                        # so we don't need any special handling for them
                        # (again, `_append_word_with_breaks` will do breaking for us).
                        # An exception is `esc` words which can't be broken in the middle;
                        # if the break is possible at all, it must happen here.
                        or (nowrap and esc and self.break_long_nowrap_words)
                    )
                    and not (
                        # This is an esc word which wouldn't fit onto this line, nor onto
                        # the next line, and there's enough space for an ellipsis
                        # on this line (or it already has one). We don't need to break
                        # the line here: this word will be passed to `_append_word`,
                        # which will handle ellipsis for us.
                        self.overflow is not False
                        and esc
                        and self.continuation_indent.width + word_width > self.width
                        and (
                            self.has_ellipsis
                            or self.current_line_width + self.need_space_before_word + 1
                            <= self.width
                        )
                    )
                ):
                    # Flush a non-empty line.
                    self._flush_line()

                # Note: `need_space_before_word` is always `False` at this point.
                # `need_space_before_word` becomes `True` only when current line
                # is non-empty, we're not in no-wrap sequence, and `preserve_spaces`
                # is `False` (meaning `isspace` is also `False`). In such situation,
                # we flush the line in the condition above.
                if not esc and (
                    (nowrap and self.break_long_nowrap_words)
                    or (not nowrap and (self.break_long_words or isspace))
                ):
                    # We will break the word in the middle if it doesn't fit.
                    self._append_word_with_breaks(word, word_width)
                else:
                    self._append_word(word, word_width)

        if self.current_line or not self.lines or self.lines[-1].explicit_newline:
            self._flush_line()

        return self.lines

    def _try_fit_word(self, word: str, word_width: int):
        if (
            self.current_line_width + word_width + self.need_space_before_word
            <= self.width
        ):
            if self.need_space_before_word:
                self._append_word(" ", 1)
                self.need_space_before_word = False
            self._append_word(word, word_width)
            return True
        else:
            return False


class _ReprContextState(Enum):
    START = 0
    """
    Initial state.

    """

    CONTAINER_START = 1
    """
    Right after a token starting a container was pushed.

    """

    ITEM_START = 2
    """
    Right after a token separating container items was pushed.

    """

    NORMAL = 3
    """
    In the middle of a container element.

    """


@_t.final
class ReprContext:
    """
    Context object that tracks repr settings and ensures that recursive objects
    are handled properly.

    :param theme:
        theme will be passed to ``__colorized_repr__``.
    :param multiline:
        indicates that values rendered via `rich repr protocol`_
        should be split into multiple lines.
    :param highlighted:
        indicates that values rendered via `rich repr protocol`_
        or via built-in :func:`repr` should be highlighted according to python syntax.
    :param max_depth:
        maximum depth of nested containers, after which container's contents
        are not rendered.
    :param max_width:
        maximum width of the content, used when wrapping text or rendering markdown.

    .. _rich repr protocol: https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

    """

    def __init__(
        self,
        *,
        theme: yuio.theme.Theme | None = None,
        multiline: bool = False,
        highlighted: bool = False,
        max_depth: int = 5,
        max_width: int | None = None,
    ):
        if theme is None:
            import yuio.io

            theme = yuio.io.get_theme()
        self._theme = theme
        self._multiline = multiline
        self._highlighted = highlighted
        self._max_depth = max_depth
        self._max_width = max(max_width or shutil.get_terminal_size().columns, 1)

        self._seen: set[int] = set()
        self._line = ColorizedString()
        self._indent = 0
        self._state = _ReprContextState.START
        self._pending_sep = None

        import yuio.md

        self._hl = yuio.md.SyntaxHighlighter.get_highlighter("repr")
        self._base_color = theme.get_color("msg/text:code/repr")

    @property
    def theme(self) -> yuio.theme.Theme:
        """
        Current theme.

        """

        return self._theme  # pragma: no cover

    @property
    def multiline(self) -> bool:
        """
        Whether values rendered with ``repr`` are split into multiple lines.

        """

        return self._multiline  # pragma: no cover

    @property
    def highlighted(self) -> bool:
        """
        Whether values rendered with ``repr`` are highlighted.

        """

        return self._highlighted  # pragma: no cover

    @property
    def max_depth(self) -> int:
        """
        Maximum depth of nested containers, after which container's contents
        are not rendered.

        """

        return self._max_depth  # pragma: no cover

    @property
    def max_width(self) -> int:
        """
        Maximum width of the content, used when wrapping text or rendering markdown.

        """

        return self._max_width  # pragma: no cover

    def _flush_sep(self):
        if self._pending_sep is not None:
            self._push_color("punct")
            self._line.append_str(self._pending_sep)
            self._pending_sep = None

    def _flush_line(self):
        if self._multiline:
            self._line.append_color(_Color.NONE)
            self._line.append_str("\n")
            if self._indent:
                self._line.append_str("  " * self._indent)

    def _push_color(self, tag: str):
        if self._highlighted:
            self._line.append_color(
                self._base_color | self._theme.to_color(f"hl/{tag}:repr")
            )

    def _push_token(self, content: str, tag: str):
        self._flush_sep()

        if self._state in [
            _ReprContextState.CONTAINER_START,
            _ReprContextState.ITEM_START,
        ]:
            self._flush_line()

        self._push_color(tag)
        self._line.append_str(content)

        self._state = _ReprContextState.NORMAL

    def _terminate_item(self, sep: str = ", "):
        self._flush_sep()
        self._pending_sep = sep
        self._state = _ReprContextState.ITEM_START

    def _start_container(self):
        self._state = _ReprContextState.CONTAINER_START
        self._indent += 1

    def _end_container(self):
        self._indent -= 1

        if self._state in [_ReprContextState.NORMAL, _ReprContextState.ITEM_START]:
            self._flush_line()

        self._state = _ReprContextState.NORMAL
        self._pending_sep = None

    def repr(
        self,
        value: _t.Any,
        /,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        max_width: int | None = None,
    ) -> ColorizedString:
        """
        Convert value to colorized string using repr methods.

        :param value:
            value to be rendered.
        :param multiline:
            if given, overrides settings passed to :func:`colorized_str` for this call.
        :param highlighted:
            if given, overrides settings passed to :func:`colorized_str` for this call.
        :param max_width:
            if given, overrides settings passed to :func:`colorized_str` for this call.
        :returns:
            a colorized string containing representation of the ``value``.
        :raises:
            this method does not raise any errors. If any inner object raises an
            exception, this function returns a colorized string with
            an error description.

        """

        return self._print(
            value,
            multiline=multiline,
            highlighted=highlighted,
            use_str=False,
            max_width=max_width,
        )

    def str(
        self,
        value: _t.Any,
        /,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        max_width: int | None = None,
    ) -> ColorizedString:
        """
        Convert value to colorized string.

        :param value:
            value to be rendered.
        :param multiline:
            if given, overrides settings passed to :func:`colorized_str` for this call.
        :param highlighted:
            if given, overrides settings passed to :func:`colorized_str` for this call.
        :param max_width:
            if given, overrides settings passed to :func:`colorized_str` for this call.
        :returns:
            a colorized string containing string representation of the ``value``.
        :raises:
            this method does not raise any errors. If any inner object raises an
            exception, this function returns a colorized string with
            an error description.

        """

        return self._print(
            value,
            multiline=multiline,
            highlighted=highlighted,
            use_str=True,
            max_width=max_width,
        )

    def hl(
        self,
        value: str,
        /,
        *,
        highlighted: bool | None = None,
    ) -> ColorizedString:
        """
        Highlight result of :func:`repr`.

        :meth:`ReprContext.repr` does this automatically, but sometimes you need
        to highlight a string without :func:`repr`-ing it one more time.

        :param value:
            result of :func:`repr` that needs highlighting.
        :returns:
            highlighted string.

        """

        highlighted = highlighted if highlighted is not None else self._highlighted

        if highlighted:
            return self._hl.highlight(
                self._theme, value, default_color=self._base_color
            )
        else:
            return ColorizedString(value)

    def _print(
        self,
        value: _t.Any,
        multiline: bool | None,
        highlighted: bool | None,
        max_width: int | None,
        use_str: bool,
    ) -> ColorizedString:
        old_line, self._line = self._line, ColorizedString()
        old_state, self._state = self._state, _ReprContextState.START
        old_pending_sep, self._pending_sep = self._pending_sep, None
        old_multiline, self._multiline = (
            self._multiline,
            (self._multiline if multiline is None else multiline),
        )
        old_highlighted, self._highlighted = (
            self._highlighted,
            (self._highlighted if highlighted is None else highlighted),
        )
        old_max_width, self._max_width = (
            self._max_width,
            (self._max_width if max_width is None else max_width),
        )

        try:
            self._print_nested(value, use_str)
            return self._line
        except Exception as e:
            yuio._logger.exception("error in repr context")
            res = ColorizedString()
            res.append_color(_Color.STYLE_INVERSE | _Color.FORE_RED)
            res.append_str(f"{_t.type_repr(type(e))}: {e}")
            return res
        finally:
            self._line = old_line
            self._state = old_state
            self._pending_sep = old_pending_sep
            self._multiline = old_multiline
            self._highlighted = old_highlighted
            self._max_width = old_max_width

    def _print_nested(self, value: _t.Any, use_str: bool = False):
        if id(value) in self._seen or self._indent > self._max_depth:
            self._push_token("...", "more")
            return
        self._seen.add(id(value))
        old_indent = self._indent
        try:
            if use_str:
                self._print_nested_as_str(value)
            else:
                self._print_nested_as_repr(value)
        finally:
            self._indent = old_indent
            self._seen.remove(id(value))

    def _print_nested_as_str(self, value):
        if isinstance(value, type):
            # This is a type.
            self._print_plain(value, convert=_t.type_repr)
        elif hasattr(value, "__colorized_str__"):
            # Has `__colorized_str__`.
            self._print_colorized_str(value)
        elif getattr(type(value), "__str__", None) is not object.__str__:
            # Has custom `__str__`.
            self._print_plain(value, convert=str, hl=False)
        else:
            # Has default `__str__` which falls back to `__repr__`.
            self._print_nested_as_repr(value)

    def _print_nested_as_repr(self, value):
        if isinstance(value, type):
            # This is a type.
            self._print_plain(value, convert=_t.type_repr)
        elif hasattr(value, "__colorized_repr__"):
            # Has `__colorized_repr__`.
            self._print_colorized_repr(value)
        elif hasattr(value, "__rich_repr__"):
            # Has `__rich_repr__`.
            self._print_rich_repr(value)
        elif isinstance(value, _CONTAINER_TYPES):
            # Is a known container.
            for ty, repr_fn in _CONTAINERS.items():
                if isinstance(value, ty):
                    if getattr(type(value), "__repr__", None) is ty.__repr__:
                        repr_fn(self, value)  # type: ignore
                    else:
                        self._print_plain(value)
                    break
        elif dataclasses.is_dataclass(value):
            # Is a dataclass.
            self._print_dataclass(value)
        else:
            # Fall back to regular `__repr__`.
            self._print_plain(value)

    def _print_plain(self, value, convert=None, hl=True):
        convert = convert or repr

        self._flush_sep()

        if self._state in [
            _ReprContextState.CONTAINER_START,
            _ReprContextState.ITEM_START,
        ]:
            self._flush_line()

        if hl and self._highlighted:
            self._line += self._hl.highlight(
                self._theme, convert(value), default_color=self._base_color
            )
        else:
            self._line.append_str(convert(value))

        self._state = _ReprContextState.NORMAL

    def _print_list(self, name: str, obrace: str, cbrace: str, items):
        if name:
            self._push_token(name, "type")
        self._push_token(obrace, "punct")
        if self._indent >= self._max_depth:
            self._push_token("...", "more")
        else:
            self._start_container()
            for item in items:
                self._print_nested(item)
                self._terminate_item()
            self._end_container()
        self._push_token(cbrace, "punct")

    def _print_dict(self, name: str, obrace: str, cbrace: str, items):
        if name:
            self._push_token(name, "type")
        self._push_token(obrace, "punct")
        if self._indent >= self._max_depth:
            self._push_token("...", "more")
        else:
            self._start_container()
            for key, value in items:
                self._print_nested(key)
                self._push_token(": ", "punct")
                self._print_nested(value)
                self._terminate_item()
            self._end_container()
        self._push_token(cbrace, "punct")

    def _print_defaultdict(self, value: collections.defaultdict[_t.Any, _t.Any]):
        self._push_token("defaultdict", "type")
        self._push_token("(", "punct")
        if self._indent >= self._max_depth:
            self._push_token("...", "more")
        else:
            self._start_container()
            self._print_nested(value.default_factory)
            self._terminate_item()
            self._print_dict("", "{", "}", value.items())
            self._terminate_item()
            self._end_container()
        self._push_token(")", "punct")

    def _print_dequeue(self, value: collections.deque[_t.Any]):
        self._push_token("deque", "type")
        self._push_token("(", "punct")
        if self._indent >= self._max_depth:
            self._push_token("...", "more")
        else:
            self._start_container()
            self._print_list("", "[", "]", value)
            self._terminate_item()
            if value.maxlen is not None:
                self._push_token("maxlen", "param")
                self._push_token("=", "punct")
                self._print_nested(value.maxlen)
                self._terminate_item()
            self._end_container()
        self._push_token(")", "punct")

    def _print_dataclass(self, value):
        try:
            # If dataclass has a custom repr, fall back to it.
            # This code is copied from Rich, MIT License.
            has_custom_repr = value.__repr__.__code__.co_filename not in (
                dataclasses.__file__,
                reprlib.__file__,
            )
        except Exception:  # pragma: no cover
            has_custom_repr = True

        if has_custom_repr:
            self._print_plain(value)
            return

        self._push_token(value.__class__.__name__, "type")
        self._push_token("(", "punct")

        if self._indent >= self._max_depth:
            self._push_token("...", "more")
        else:
            self._start_container()
            for field in dataclasses.fields(value):
                if not field.repr:
                    continue
                self._push_token(field.name, "param")
                self._push_token("=", "punct")
                self._print_nested(getattr(value, field.name))
                self._terminate_item()
            self._end_container()

        self._push_token(")", "punct")

    def _print_colorized_repr(self, value):
        self._flush_sep()

        if self._state in [
            _ReprContextState.CONTAINER_START,
            _ReprContextState.ITEM_START,
        ]:
            self._flush_line()

        res = value.__colorized_repr__(self)
        if not isinstance(res, ColorizedString):
            raise TypeError(
                f"__colorized_repr__ returned non-colorized-string (type {_t.type_repr(type(res))})"
            )
        self._line += res

        self._state = _ReprContextState.NORMAL

    def _print_colorized_str(self, value):
        self._flush_sep()

        if self._state in [
            _ReprContextState.CONTAINER_START,
            _ReprContextState.ITEM_START,
        ]:  # pragma: no cover
            self._flush_line()
            # This never happens because `_state` is always `START`
            # when rendering as `str`.

        res = value.__colorized_str__(self)
        if not isinstance(res, ColorizedString):
            raise TypeError(
                f"__colorized_str__ returned non-colorized-string (type {_t.type_repr(type(res))})"
            )
        self._line += res
        self._state = _ReprContextState.NORMAL

    def _print_rich_repr(self, value):
        rich_repr = getattr(value, "__rich_repr__")
        angular = getattr(rich_repr, "angular", False)

        if angular:
            self._push_token("<", "punct")
        self._push_token(value.__class__.__name__, "type")
        if angular:
            self._push_token(" ", "space")
        else:
            self._push_token("(", "punct")

        if self._indent >= self._max_depth:
            self._push_token("...", "more")
        else:
            self._start_container()
            args = rich_repr()
            if args is None:
                args = []  # `rich_repr` didn't yield?
            for arg in args:
                if isinstance(arg, tuple):
                    if len(arg) == 3:
                        key, child, default = arg
                        if default == child:
                            continue
                    elif len(arg) == 2:
                        key, child = arg
                    elif len(arg) == 1:
                        key, child = None, arg[0]
                    else:
                        key, child = None, arg
                else:
                    key, child = None, arg

                if key:
                    self._push_token(str(key), "param")
                    self._push_token("=", "punct")
                self._print_nested(child)
                self._terminate_item("" if angular else ", ")
            self._end_container()

        self._push_token(">" if angular else ")", "punct")


_CONTAINERS = {
    os._Environ: lambda c, o: c._print_dict("environ", "({", "})", o.items()),
    collections.defaultdict: ReprContext._print_defaultdict,
    collections.deque: ReprContext._print_dequeue,
    collections.Counter: lambda c, o: c._print_dict("Counter", "({", "})", o.items()),
    collections.UserList: lambda c, o: c._print_list("", "[", "]", o),
    collections.UserDict: lambda c, o: c._print_dict("", "{", "}", o.items()),
    list: lambda c, o: c._print_list("", "[", "]", o),
    set: lambda c, o: c._print_list("", "{", "}", o),
    frozenset: lambda c, o: c._print_list("frozenset", "({", "})", o),
    tuple: lambda c, o: c._print_list("", "(", ")", o),
    dict: lambda c, o: c._print_dict("", "{", "}", o.items()),
    types.MappingProxyType: lambda _: lambda c, o: c._print_dict(
        "mappingproxy", "({", "})", o.items()
    ),
}
_CONTAINER_TYPES = tuple(_CONTAINERS)


def colorized_str(
    value: _t.Any,
    /,
    theme: yuio.theme.Theme | None = None,
    **kwargs,
) -> ColorizedString:
    """
    Like :class:`str() <str>`, but uses ``__colorized_str__`` and returns
    a colorized string.

    This function is used when formatting values
    via :meth:`ColorizedString.percent_format`, or printing them via :mod:`yuio.io`
    functions.

    :param value:
        value to colorize.
    :param theme:
        theme will be passed to ``__colorized_str__``.
    :param kwargs:
        all other keyword arguments will be forwarded to :class:`ReprContext`.
    :returns:
        a colorized string containing representation of ``value``.
    :raises:
        this method does not raise any errors. If any inner object raises an
        exception, this function returns a colorized string with an error description.

    .. _rich repr protocol: https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

    """

    ctx = ReprContext(theme=theme, **kwargs)
    return ctx.str(value)


def colorized_repr(
    value: _t.Any,
    /,
    theme: yuio.theme.Theme | None = None,
    **kwargs,
) -> ColorizedString:
    """
    Like :func:`repr`, but uses ``__colorized_repr__`` and returns
    a colorized string.

    This function is used when formatting values
    via :meth:`ColorizedString.percent_format`, or printing them via :mod:`yuio.io`
    functions.

    :param value:
        value to colorize.
    :param theme:
        theme will be passed to ``__colorized_repr__``.
    :param kwargs:
        all other keyword arguments will be forwarded to :class:`ReprContext`.
    :returns:
        a colorized string containing representation of ``value``.
    :raises:
        this method does not raise any errors. If any inner object raises an
        exception, this function returns a colorized string with an error description.

    .. _rich repr protocol: https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

    """

    ctx = ReprContext(theme=theme, **kwargs)
    return ctx.repr(value)


def _to_colorable(msg: _t.Any, args: tuple[_t.Any, ...] | None = None) -> Colorable:
    """
    Convert generic ``msg, args`` tuple to a colorable.

    If msg is a string, returns :class:`Format`. Otherwise, check that no arguments
    were given, and returns ``msg`` unchanged.

    """

    if isinstance(msg, str):
        return Format(_t.cast(_t.LiteralString, msg), *(args or ()))
    else:
        if args:
            raise TypeError(
                f"non-string type {_t.type_repr(type(msg))} can't have format arguments"
            )
        return msg


class _StrBase(abc.ABC):
    def __str__(self) -> str:
        return str(ReprContext().str(self))

    @abc.abstractmethod
    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        raise NotImplementedError()


@repr_from_rich
class Format(_StrBase):
    """Format(msg: typing.LiteralString, /, *args: typing.Any)
    Format(msg: str, /)

    Lazy wrapper that ``%``-formats the given message.

    This utility allows saving ``%``-formatted messages and performing actual
    formatting lazily when requested. Color tags and backticks are handled as usual.

    :param msg:
        message to format.
    :param args:
        arguments for ``%``-formatting the message.
    :example:
        ::

            >>> message = Format("Hello, `%s`!", "world")
            >>> print(message)
            Hello, world!

    """

    @_t.overload
    def __init__(self, msg: _t.LiteralString, /, *args: _t.Any): ...
    @_t.overload
    def __init__(self, msg: str, /): ...
    def __init__(self, msg: str, /, *args: _t.Any):
        self._msg: str = msg
        self._args: tuple[_t.Any, ...] = args

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield from ((None, arg) for arg in self._args)

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return colorize(self._msg, *self._args, ctx=ctx)


@_t.final
@repr_from_rich
class Repr:
    """
    Lazy wrapper that calls :func:`colorized_repr` on the given value.

    :param value:
        value to repr.
    :param multiline:
        if given, overrides settings passed to :func:`colorized_repr` for this call.
    :param highlighted:
        if given, overrides settings passed to :func:`colorized_repr` for this call.
    :example:
        .. code-block:: python

            config = ...
            yuio.io.info(
                "Loaded config:\\n`%#+s`", yuio.string.Indent(yuio.string.Repr(config))
            )

    """

    def __init__(
        self,
        value: _t.Any,
        /,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
    ):
        self.value = value
        self.multiline = multiline
        self.highlighted = highlighted

    def __rich_repr__(self) -> RichReprResult:
        yield None, self.value
        yield "multiline", self.multiline, None
        yield "highlighted", self.highlighted, None

    def __str__(self):
        return repr(self.value)

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return ctx.repr(
            self.value, multiline=self.multiline, highlighted=self.highlighted
        )


@_t.final
@repr_from_rich
class TypeRepr(_StrBase):
    """
    Lazy wrapper that calls :func:`typing.type_repr` on the given value
    and highlights the result.

    :param ty:
        type to format.

        If ``ty`` is a string, :func:`typing.type_repr` is not called on it, allowing
        you to mix types and arbitrary descriptions.
    :param highlighted:
        if given, overrides settings passed to :func:`colorized_repr` for this call.
    :example:
        .. invisible-code-block: python

            value = ...

        .. code-block:: python

            yuio.io.error("Expected `str`, got `%s`", yuio.string.TypeRepr(type(value)))

    """

    def __init__(self, ty: _t.Any, /, *, highlighted: bool | None = None):
        self._ty = ty
        self._highlighted = highlighted

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._ty
        yield "highlighted", self._highlighted, None

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        if not isinstance(self._ty, type) and isinstance(
            self._ty, (str, ColorizedString)
        ):
            return ColorizedString(self._ty)
        else:
            return ctx.hl(_t.type_repr(self._ty), highlighted=self._highlighted)


@repr_from_rich
class _JoinBase(_StrBase):
    def __init__(
        self,
        collection: _t.Iterable[_t.Any],
        /,
        *,
        sep: str = ", ",
        sep_two: str | None = None,
        sep_last: str | None = None,
        fallback: AnyString = "",
        color: str | _Color | None = "code",
    ):
        self.__collection = collection
        self._sep = sep
        self._sep_two = sep_two
        self._sep_last = sep_last
        self._fallback: AnyString = fallback
        self._color = color

    @functools.cached_property
    def _collection(self):
        return list(self.__collection)

    @classmethod
    def or_(
        cls,
        collection: _t.Iterable[_t.Any],
        /,
        *,
        fallback: AnyString = "",
        color: str | _Color | None = "code",
    ) -> _t.Self:
        """
        Shortcut for joining arguments using word "or" as the last separator.

        :example:
            ::

                >>> print(yuio.string.JoinStr.or_([1, 2, 3]))
                1, 2, or 3

        """

        return cls(
            collection, sep_last=", or ", sep_two=" or ", fallback=fallback, color=color
        )

    @classmethod
    def and_(
        cls,
        collection: _t.Iterable[_t.Any],
        /,
        *,
        fallback: AnyString = "",
        color: str | _Color | None = "code",
    ) -> _t.Self:
        """
        Shortcut for joining arguments using word "and" as the last separator.

        :example:
            ::

                >>> print(yuio.string.JoinStr.and_([1, 2, 3]))
                1, 2, and 3

        """

        return cls(
            collection,
            sep_last=", and ",
            sep_two=" and ",
            fallback=fallback,
            color=color,
        )

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._collection
        yield "sep", self._sep, ", "
        yield "sep_two", self._sep_two, None
        yield "sep_last", self._sep_last, None
        yield "color", self._color, "code"

    def _render(
        self,
        theme: yuio.theme.Theme,
        to_str: _t.Callable[[_t.Any], ColorizedString],
    ) -> ColorizedString:
        res = ColorizedString()
        color = theme.to_color(self._color)

        size = len(self._collection)
        if not size:
            res += self._fallback
            return res
        elif size == 1:
            return to_str(self._collection[0]).with_base_color(color)
        elif size == 2:
            res.append_colorized_str(to_str(self._collection[0]).with_base_color(color))
            res.append_str(self._sep if self._sep_two is None else self._sep_two)
            res.append_colorized_str(to_str(self._collection[1]).with_base_color(color))
            return res

        last_i = size - 1

        sep = self._sep
        sep_last = self._sep if self._sep_last is None else self._sep_last

        do_sep = False
        for i, value in enumerate(self._collection):
            if do_sep:
                if i == last_i:
                    res.append_str(sep_last)
                else:
                    res.append_str(sep)
            res.append_colorized_str(to_str(value).with_base_color(color))
            do_sep = True
        return res


@_t.final
class JoinStr(_JoinBase):
    """
    Lazy wrapper that calls :class:`colorized_str` on elements of the given collection,
    then joins the results using the given separator.

    :param collection:
        collection that will be printed.
    :param sep:
        separator that's printed between elements of the collection.
    :param sep_two:
        separator that's used when there are only two elements in the collection.
        Defaults to ``sep``.
    :param sep_last:
        separator that's used between the last and prior-to-last element
        of the collection. Defaults to ``sep``.
    :param fallback:
        printed if collection is empty.
    :param color:
        color applied to elements of the collection.
    :example:
        .. code-block:: python

            values = ["foo", "bar"]
            yuio.io.info("Available values: %s", yuio.string.JoinStr(values))

    """

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return self._render(ctx._theme, ctx.str)


@_t.final
class JoinRepr(_JoinBase):
    """
    Lazy wrapper that calls :class:`colorized_repr` on elements of the given collection,
    then joins the results using the given separator.

    :param collection:
        collection that will be printed.
    :param sep:
        separator that's printed between elements of the collection.
    :param sep_two:
        separator that's used when there are only two elements in the collection.
        Defaults to ``sep``.
    :param sep_last:
        separator that's used between the last and prior-to-last element
        of the collection. Defaults to ``sep``.
    :param fallback:
        printed if collection is empty.
    :param color:
        color applied to elements of the collection.
    :example:
        .. code-block:: python

            values = ["foo", "bar"]
            yuio.io.info("Available values: %s", yuio.string.JoinRepr(values))

    """

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return self._render(ctx._theme, ctx.repr)


And = JoinStr.and_
"""
Shortcut for :meth:`JoinStr.and_`.

"""


Or = JoinStr.or_
"""
Shortcut for :meth:`JoinStr.or_`.

"""


@_t.final
@repr_from_rich
class Stack(_StrBase):
    """
    Lazy wrapper that joins multiple :obj:`Colorable` objects with newlines,
    effectively stacking them one on top of another.

    :param args:
        colorables to stack.
    :example:
        ::

            >>> print(
            ...     yuio.string.Stack(
            ...         yuio.string.Format("<c bold magenta>Example:</c>"),
            ...         yuio.string.Indent(
            ...             yuio.string.Hl(
            ...                 \"""
            ...                     {
            ...                         "foo": "bar"
            ...                     }
            ...                 \""",
            ...                 syntax="json",
            ...             ),
            ...             indent="->  ",
            ...         ),
            ...     )
            ... )
            Example:
            ->  {
            ->      "foo": "bar"
            ->  }

    """

    def __init__(self, *args: Colorable):
        self._args = args

    def __rich_repr__(self) -> RichReprResult:
        yield from ((None, arg) for arg in self._args)

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        res = ColorizedString()
        sep = False
        for arg in self._args:
            if sep:
                res.append_color(_Color.NONE)
                res.append_str("\n")
            res += ctx.str(arg)
            sep = True
        return res


@_t.final
@repr_from_rich
class Indent(_StrBase):
    """
    Lazy wrapper that indents the message during formatting.

    .. seealso::

        :meth:`ColorizedString.indent`.

    :param msg:
        message to indent.
    :param indent:
        this will be prepended to the first line in the string.
        Defaults to two spaces.
    :param continuation_indent:
        this will be prepended to subsequent lines in the string.
        Defaults to ``indent``.
    :example:
        .. code-block:: python

            config = ...
            yuio.io.info(
                "Loaded config:\\n`%#+s`", yuio.string.Indent(yuio.string.Repr(config))
            )

    """

    def __init__(
        self,
        msg: Colorable,
        /,
        *,
        indent: AnyString | int = "  ",
        continuation_indent: AnyString | int | None = None,
    ):
        self._msg = msg
        self._indent: AnyString | int = indent
        self._continuation_indent: AnyString | int | None = continuation_indent

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield "indent", self._indent, "  "
        yield "continuation_indent", self._continuation_indent, None

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        if isinstance(self._indent, int):
            indent = ColorizedString(" " * self._indent)
        else:
            indent = ColorizedString(self._indent)
        if self._continuation_indent is None:
            continuation_indent = indent
        elif isinstance(self._continuation_indent, int):
            continuation_indent = ColorizedString(" " * self._continuation_indent)
        else:
            continuation_indent = ColorizedString(self._continuation_indent)

        indent_width = max(indent.width, continuation_indent.width)
        max_width = max(1, ctx.max_width - indent_width)

        return ctx.str(self._msg, max_width=max_width).indent(
            indent, continuation_indent
        )


@_t.final
@repr_from_rich
class Md(_StrBase):
    """Md(msg: typing.LiteralString, /, *args, max_width: int | None | yuio.Missing = yuio.MISSING, dedent: bool = True, allow_headings: bool = True)
    Md(msg: str, /, *, max_width: int | None | yuio.Missing = yuio.MISSING, dedent: bool = True, allow_headings: bool = True)

    Lazy wrapper that renders markdown during formatting.

    :param md:
        markdown to format.
    :param args:
        arguments for ``%``-formatting the rendered markdown.
    :param max_width:
        if given, overrides settings passed to :func:`colorized_repr` for this call.
    :param dedent:
        whether to remove leading indent from markdown.
    :param allow_headings:
        whether to render headings as actual headings or as paragraphs.

    """

    @_t.overload
    def __init__(
        self,
        md: _t.LiteralString,
        /,
        *args: _t.Any,
        max_width: int | None = None,
        dedent: bool = True,
        allow_headings: bool = True,
    ): ...
    @_t.overload
    def __init__(
        self,
        md: str,
        /,
        *,
        max_width: int | None = None,
        dedent: bool = True,
        allow_headings: bool = True,
    ): ...
    def __init__(
        self,
        md: str,
        /,
        *args: _t.Any,
        max_width: int | None = None,
        dedent: bool = True,
        allow_headings: bool = True,
    ):
        self._md: str = md
        self._args: tuple[_t.Any, ...] = args
        self._max_width: int | None = max_width
        self._dedent: bool = dedent
        self._allow_headings: bool = allow_headings

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._md
        yield from ((None, arg) for arg in self._args)
        yield "max_width", self._max_width, yuio.MISSING
        yield "dedent", self._dedent, True
        yield "allow_headings", self._allow_headings, True

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        import yuio.md

        max_width = self._max_width or ctx.max_width

        formatter = yuio.md.MdFormatter(
            ctx.theme,
            width=max_width,
            allow_headings=self._allow_headings,
        )

        res = ColorizedString()
        res.start_no_wrap()
        sep = False
        for line in formatter.format(self._md, dedent=self._dedent):
            if sep:
                res += "\n"
            res += line
            sep = True
        res.end_no_wrap()
        if self._args:
            res = res.percent_format(self._args, ctx)

        return res


@_t.final
@repr_from_rich
class Hl(_StrBase):
    """Hl(code: typing.LiteralString, /, *args, syntax: str | yuio.md.SyntaxHighlighter, dedent: bool = True)
    Hl(code: str, /, *, syntax: str | yuio.md.SyntaxHighlighter, dedent: bool = True)

    Lazy wrapper that highlights code during formatting.

    :param md:
        code to highlight.
    :param args:
        arguments for ``%``-formatting the highlighted code.
    :param syntax:
        name of syntax or a :class:`~yuio.md.SyntaxHighlighter` instance.
    :param dedent:
        whether to remove leading indent from code.

    """

    @_t.overload
    def __init__(
        self,
        code: _t.LiteralString,
        /,
        *args: _t.Any,
        syntax: str | yuio.md.SyntaxHighlighter,
        dedent: bool = True,
    ): ...
    @_t.overload
    def __init__(
        self,
        code: str,
        /,
        *,
        syntax: str | yuio.md.SyntaxHighlighter,
        dedent: bool = True,
    ): ...
    def __init__(
        self,
        code: str,
        /,
        *args: _t.Any,
        syntax: str | yuio.md.SyntaxHighlighter,
        dedent: bool = True,
    ):
        self._code: str = code
        self._args: tuple[_t.Any, ...] = args
        self._syntax: str | yuio.md.SyntaxHighlighter = syntax
        self._dedent: bool = dedent

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._code
        yield from ((None, arg) for arg in self._args)
        yield "syntax", self._syntax
        yield "dedent", self._dedent, True

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        import yuio.md

        syntax = (
            self._syntax
            if isinstance(self._syntax, yuio.md.SyntaxHighlighter)
            else yuio.md.SyntaxHighlighter.get_highlighter(self._syntax)
        )
        code = self._code
        if self._dedent:
            code = _dedent(code)
        code = code.rstrip()

        res = ColorizedString()
        res.start_no_wrap()
        res += syntax.highlight(ctx.theme, code)
        res.end_no_wrap()
        if self._args:
            res = res.percent_format(self._args, ctx)

        return res


@_t.final
@repr_from_rich
class Wrap(_StrBase):
    """
    Lazy wrapper that wraps the message during formatting.

    .. seealso::

        :meth:`ColorizedString.wrap`.

    :param msg:
        message to wrap.
    :param max_width:
        if given, overrides settings passed to :func:`colorized_repr` for this call.
    :param preserve_spaces:
        if set to :data:`True`, all spaces are preserved.
        Otherwise, consecutive spaces are collapsed into a single space.

        Note that tabs always treated as a single whitespace.
    :param preserve_newlines:
        if set to :data:`True` (default), text is additionally wrapped
        on newline sequences. When this happens, the newline sequence that wrapped
        the line will be placed into :attr:`~ColorizedString.explicit_newline`.

        If set to :data:`False`, newline sequences are treated as whitespaces.
    :param break_long_words:
        if set to :data:`True` (default), words that don't fit into a single line
        will be split into multiple lines.
    :param overflow:
        Pass :data:`True` to trim overflowing lines and replace them with ellipsis.
    :param break_long_nowrap_words:
        if set to :data:`True`, words in no-wrap regions that don't fit
        into a single line will be split into multiple lines.
    :param indent:
        this will be prepended to the first line in the string.
        Defaults to two spaces.
    :param continuation_indent:
        this will be prepended to subsequent lines in the string.
        Defaults to ``indent``.

    """

    def __init__(
        self,
        msg: Colorable,
        /,
        *,
        max_width: int | None = None,
        preserve_spaces: bool = False,
        preserve_newlines: bool = True,
        break_long_words: bool = True,
        break_long_nowrap_words: bool = False,
        overflow: bool | str = False,
        indent: AnyString | int = "",
        continuation_indent: AnyString | int | None = None,
    ):
        self._msg = msg
        self._max_width: int | None = max_width
        self._preserve_spaces = preserve_spaces
        self._preserve_newlines = preserve_newlines
        self._break_long_words = break_long_words
        self._break_long_nowrap_words = break_long_nowrap_words
        self._overflow = overflow
        self._indent: AnyString | int = indent
        self._continuation_indent: AnyString | int | None = continuation_indent

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield "max_width", self._max_width, None
        yield "indent", self._indent, ""
        yield "continuation_indent", self._continuation_indent, None
        yield "preserve_spaces", self._preserve_spaces, None
        yield "preserve_newlines", self._preserve_newlines, True
        yield "break_long_words", self._break_long_words, True
        yield "break_long_nowrap_words", self._break_long_nowrap_words, False

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        if isinstance(self._indent, int):
            indent = ColorizedString(" " * self._indent)
        else:
            indent = ColorizedString(self._indent)
        if self._continuation_indent is None:
            continuation_indent = indent
        elif isinstance(self._continuation_indent, int):
            continuation_indent = ColorizedString(" " * self._continuation_indent)
        else:
            continuation_indent = ColorizedString(self._continuation_indent)

        max_width = self._max_width or ctx.max_width
        indent_width = max(indent.width, continuation_indent.width)
        inner_max_width = max(1, max_width - indent_width)

        overflow = self._overflow
        if overflow is True:
            overflow = ctx.theme.msg_decorations.get("overflow", "")

        res = ColorizedString()
        res.start_no_wrap()
        sep = False
        for line in ctx.str(self._msg, max_width=inner_max_width).wrap(
            max_width,
            preserve_spaces=self._preserve_spaces,
            preserve_newlines=self._preserve_newlines,
            break_long_words=self._break_long_words,
            break_long_nowrap_words=self._break_long_nowrap_words,
            overflow=overflow,
            indent=indent,
            continuation_indent=continuation_indent,
        ):
            if sep:
                res.append_str("\n")
            res.append_colorized_str(line)
            sep = True
        res.end_no_wrap()

        return res


@_t.final
@repr_from_rich
class WithBaseColor(_StrBase):
    """
    Lazy wrapper that applies the given color "under" the given colorable.
    That is, all colors in the rendered colorable will be combined with this color
    on the left: ``base_color | color``.

    .. seealso::

        :meth:`ColorizedString.with_base_color`.

    :param msg:
        message to highlight.
    :param base_color:
        color that will be added under the message.

    """

    def __init__(
        self,
        msg: Colorable,
        /,
        *,
        base_color: str | _Color,
    ):
        self._msg = msg
        self._base_color = base_color

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield "base_color", self._base_color

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return ctx.str(self._msg).with_base_color(ctx.theme.to_color(self._base_color))


@repr_from_rich
class Hr(_StrBase):
    """Hr(msg: Colorable = "", /, *, weight: int | str = 1, overflow: bool | str = True, **kwargs)

    Produces horizontal ruler when converted to string.

    :param msg:
        any colorable that will be placed in the middle of the ruler.
    :param weight:
        weight or style of the ruler:

        -   ``0`` prints no ruler (but still prints centered text),
        -   ``1`` prints normal ruler,
        -   ``2`` prints bold ruler.

        Additional styles can be added through
        :attr:`Theme.msg_decorations <yuio.theme.Theme.msg_decorations>`.
    :param max_width:
        if given, overrides settings passed to :func:`colorized_repr` for this call.
    :param overflow:
        pass :data:`False` to disable trimming ``msg`` to terminal width.
    :param kwargs:
        Other keyword arguments override corresponding decorations from the theme:

        :``left_start``:
            start of the ruler to the left of the message.
        :``left_middle``:
            filler of the ruler to the left of the message.
        :``left_end``:
            end of the ruler to the left of the message.
        :``middle``:
            filler of the ruler that's used if ``msg`` is empty.
        :``right_start``:
            start of the ruler to the right of the message.
        :``right_middle``:
            filler of the ruler to the right of the message.
        :``right_end``:
            end of the ruler to the right of the message.

    """

    def __init__(
        self,
        msg: Colorable = "",
        /,
        *,
        max_width: int | None = None,
        overflow: bool | str = True,
        weight: int | str = 1,
        left_start: str | None = None,
        left_middle: str | None = None,
        left_end: str | None = None,
        middle: str | None = None,
        right_start: str | None = None,
        right_middle: str | None = None,
        right_end: str | None = None,
    ):
        self._msg = msg
        self._max_width = max_width
        self._overflow = overflow
        self._weight = weight
        self._left_start = left_start
        self._left_middle = left_middle
        self._left_end = left_end
        self._middle = middle
        self._right_start = right_start
        self._right_middle = right_middle
        self._right_end = right_end

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg, None
        yield "weight", self._weight, None
        yield "max_width", self._max_width, None
        yield "overflow", self._overflow, None
        yield "left_start", self._left_start, None
        yield "left_middle", self._left_middle, None
        yield "left_end", self._left_end, None
        yield "middle", self._middle, None
        yield "right_start", self._right_start, None
        yield "right_middle", self._right_middle, None
        yield "right_end", self._right_end, None

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        max_width = self._max_width or ctx.max_width

        color = ctx.theme.get_color(f"msg/decoration:hr/{self._weight}")

        res = ColorizedString(color)
        res.start_no_wrap()

        msg = ctx.str(self._msg)
        if not msg:
            res.append_str(self._make_whole(max_width, ctx.theme.msg_decorations))
            return res

        overflow = self._overflow
        if overflow is True:
            overflow = ctx.theme.msg_decorations.get("overflow", "")

        sep = False
        for line in msg.wrap(
            max_width, preserve_spaces=True, break_long_words=False, overflow=overflow
        ):
            if sep:
                res.append_color(yuio.color.Color.NONE)
                res.append_str("\n")
                res.append_color(color)

            line_w = line.width
            line_w_fill = max(0, max_width - line_w)
            line_w_fill_l = line_w_fill // 2
            line_w_fill_r = line_w_fill - line_w_fill_l
            if not line_w_fill_l and not line_w_fill_r:
                res.append_colorized_str(line)
                return res

            res.append_str(self._make_left(line_w_fill_l, ctx.theme.msg_decorations))
            res.append_colorized_str(line)
            res.append_str(self._make_right(line_w_fill_r, ctx.theme.msg_decorations))

            sep = True

        return res

    def _make_left(self, w: int, msg_decorations: _t.Mapping[str, str]):
        weight = self._weight
        start = (
            self._left_start
            if self._left_start is not None
            else msg_decorations.get(f"hr/{weight}/left_start", "")
        )
        middle = (
            self._left_middle
            if self._left_middle is not None
            else msg_decorations.get(f"hr/{weight}/left_middle")
        ) or " "
        end = (
            self._left_end
            if self._left_end is not None
            else msg_decorations.get(f"hr/{weight}/left_end", "")
        )

        return _make_left(w, start, middle, end)

    def _make_right(self, w: int, msg_decorations: _t.Mapping[str, str]):
        weight = self._weight
        start = (
            self._right_start
            if self._right_start is not None
            else msg_decorations.get(f"hr/{weight}/right_start", "")
        )
        middle = (
            self._right_middle
            if self._right_middle is not None
            else msg_decorations.get(f"hr/{weight}/right_middle")
        ) or " "
        end = (
            self._right_end
            if self._right_end is not None
            else msg_decorations.get(f"hr/{weight}/right_end", "")
        )

        return _make_right(w, start, middle, end)

    def _make_whole(self, w: int, msg_decorations: _t.Mapping[str, str]):
        weight = self._weight
        start = (
            self._left_start
            if self._left_start is not None
            else msg_decorations.get(f"hr/{weight}/left_start", " ")
        )
        middle = (
            self._middle
            if self._middle is not None
            else msg_decorations.get(f"hr/{weight}/middle")
        ) or " "
        end = (
            self._right_end
            if self._right_end is not None
            else msg_decorations.get(f"hr/{weight}/right_end", " ")
        )

        start_w = line_width(start)
        middle_w = line_width(middle)
        end_w = line_width(end)

        if w >= start_w:
            w -= start_w
        else:
            start = ""
        if w >= end_w:
            w -= end_w
        else:
            end = ""
        middle_times = w // middle_w
        w -= middle_times * middle_w
        middle *= middle_times
        return start + middle + end + " " * w


def _make_left(
    w: int,
    start: str,
    middle: str,
    end: str,
):
    start_w = line_width(start)
    middle_w = line_width(middle)
    end_w = line_width(end)

    if w >= end_w:
        w -= end_w
    else:
        end = ""
    if w >= start_w:
        w -= start_w
    else:
        start = ""
    middle_times = w // middle_w
    w -= middle_times * middle_w
    middle *= middle_times
    return start + middle + end + " " * w


def _make_right(
    w: int,
    start: str,
    middle: str,
    end: str,
):
    start_w = line_width(start)
    middle_w = line_width(middle)
    end_w = line_width(end)

    if w >= start_w:
        w -= start_w
    else:
        start = ""
    if w >= end_w:
        w -= end_w
    else:
        end = ""
    middle_times = w // middle_w
    w -= middle_times * middle_w
    middle *= middle_times
    return " " * w + start + middle + end


@repr_from_rich
class ColorableBase:
    """ColorableBase(msg: typing.LiteralString, /, *args: typing.Any)
    ColorableBase(msg: str, /)

    Base class for colorable object utilities.

    This is a base for classes that wrap other colorables and alter behavior of their
    ``__str__`` and ``__colorized_str__`` methods.

    .. tip::

        You can use this base as a mixin for your errors, making them pretty-printable
        with Yuio:

        .. code-block:: python

            class MyError(yuio.string.ColorableBase, Exception):
                pass


            try:
                ...
                raise MyError("A formatted <c b>error message</c>")
                ...
            except MyError as e:
                yuio.io.error_with_tb(e)

    :param msg:
        message to format. Can be a literal string or any other colorable object.

        If it's given as a literal string, additional arguments for ``%``-formatting
        may be given. Otherwise, giving additional arguments will cause
        a :class:`TypeError`.
    :param args:
        arguments for ``%``-formatting the message.
    :raises:
        :class:`TypeError` if ``args`` are given with a non-string ``msg``.

    """

    @_t.overload
    def __init__(self, msg: _t.LiteralString, /, *args): ...
    @_t.overload
    def __init__(self, msg: Colorable, /): ...
    def __init__(self, msg: _t.Any, /, *args):
        self.msg: Colorable = _to_colorable(msg, args)
        """
        Colorable message.

        """

    def __rich_repr__(self) -> RichReprResult:
        yield None, self.msg

    def __str__(self) -> str:
        return str(self.msg)

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return ctx.str(self.msg)
