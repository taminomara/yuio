# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
The higher-level :mod:`yuio.io` module uses strings with xml-like color
tags to store information about line formatting. Here, on the lower level,
these strings are parsed and transformed to :class:`ColorizedString`\\ s.

.. autoclass:: ColorizedString
   :members:


.. _pretty-protocol:

Pretty printing protocol
------------------------

Complex message formatting requires knowing capabilities of the target terminal.
This affects which message decorations are used (Unicode or ASCII), how lines are
wrapped, and so on. This data is encapsulated in an instance of :class:`ReprContext`:

.. autoclass:: ReprContext
    :members:

Repr context may not always be available when a message is created, though.
For example, we may know that we will be printing some data, but we don't know
whether we'll print it to a file or to a terminal.

The solution is to defer formatting by creating a :type:`Colorable`, i.e. an object
that defines one of the following special methods:

``__colorized_str__``, ``__colorized_repr__``
    This should be a method that accepts a single positional argument,
    :class:`ReprContext`, and returns a :class:`ColorizedString`.

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
                result += ctx.get_color("magenta")
                result += "MyObject"
                result += ctx.get_color("normal")
                result += "("
                result += ctx.repr(self.value)
                result += ")"
                return result

``__rich_repr__``
    This method doesn't have any arguments. It should return an iterable of tuples
    describing object's arguments:

    -   ``yield name, value`` will generate a keyword argument,
    -   ``yield name, value, default`` will generate a keyword argument if value
        is not equal to default,
    -   if `name` is :data:`None`, it will generate positional argument instead.

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
    :canonical: Printable | ColorizedStrProtocol | ColorizedReprProtocol | RichReprProtocol | ~typing.LiteralString | BaseException

    An object that supports colorized printing.

    This can be a string, and exception, or any object that follows
    :class:`ColorizedStrProtocol`. Additionally, you can pass any object that has
    ``__repr__``, but you'll have to wrap it into :type:`Printable` to confirm
    your intent to print it.

.. type:: ToColorable
    :canonical: Colorable | ~string.templatelib.Template

    Any object that can be converted to a :type:`Colorable` by formatting it via
    :class:`Format`.

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

.. autoclass:: Link
   :members:

.. autoclass:: Indent
    :members:

.. autoclass:: Md
    :members:

.. autoclass:: Rst
    :members:

.. autoclass:: Hl
    :members:

.. autoclass:: Wrap
    :members:

.. autoclass:: WithBaseColor
    :members:

.. autoclass:: Hr
    :members:


Parsing color tags
------------------

.. autofunction:: colorize

.. autofunction:: strip_color_tags


Helpers
-------

.. autofunction:: line_width

.. type:: AnyString
    :canonical: str | ~yuio.color.Color | ColorizedString | NoWrapMarker | typing.Iterable[AnyString]

    Any string (i.e. a :class:`str`, a raw colorized string,
    or a normal colorized string).

.. autoclass:: LinkMarker

.. autodata:: NO_WRAP_START

.. autodata:: NO_WRAP_END

.. type:: NoWrapMarker
          NoWrapStart
          NoWrapEnd

    Type of a no-wrap marker.

"""

from __future__ import annotations

import abc
import collections
import contextlib
import dataclasses
import functools
import os
import pathlib
import re
import reprlib
import string
import sys
import types
import unicodedata
from dataclasses import dataclass
from enum import Enum

import yuio
import yuio.color
import yuio.term
import yuio.theme
from yuio.color import Color as _Color
from yuio.util import UserString as _UserString
from yuio.util import dedent as _dedent

import yuio._typing_ext as _tx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

if sys.version_info >= (3, 14):
    from string.templatelib import Interpolation as _Interpolation
    from string.templatelib import Template as _Template
else:

    class _Interpolation: ...

    class _Template: ...

    _Interpolation.__module__ = "string.templatelib"
    _Interpolation.__name__ = "Interpolation"
    _Interpolation.__qualname__ = "Interpolation"
    _Template.__module__ = "string.templatelib"
    _Template.__name__ = "Template"
    _Template.__qualname__ = "Template"


__all__ = [
    "NO_WRAP_END",
    "NO_WRAP_START",
    "And",
    "AnyString",
    "Colorable",
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
    "Link",
    "LinkMarker",
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
    "Rst",
    "Stack",
    "ToColorable",
    "TypeRepr",
    "WithBaseColor",
    "Wrap",
    "colorize",
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
:class:`ColorizedStrProtocol`. Additionally, you can pass any object that has
``__repr__``, but you'll have to wrap it into :type:`Printable` to confirm
your intent to print it.

"""

ToColorable: _t.TypeAlias = Colorable | _Template
"""
Any object that can be converted to a :type:`Colorable` by formatting it via
:class:`Format`.

"""


RichReprProtocolT = _t.TypeVar("RichReprProtocolT", bound=RichReprProtocol)


def repr_from_rich(cls: type[RichReprProtocolT], /) -> type[RichReprProtocolT]:
    """repr_from_rich(cls: RichReprProtocol) -> RichReprProtocol

    A decorator that generates ``__repr__`` from ``__rich_repr__``.

    :param cls:
        class that needs ``__repr__``.
    :returns:
        always returns `cls`.
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


class NoWrapMarker(Enum):
    """
    Type for a no-wrap marker.

    """

    NO_WRAP_START = "<no_wrap_start>"
    NO_WRAP_END = "<no_wrap_end>"

    def __repr__(self):
        return f"yuio.string.{self.name}"  # pragma: no cover

    def __str__(self) -> str:
        return self.value  # pragma: no cover


NoWrapStart: _t.TypeAlias = _t.Literal[NoWrapMarker.NO_WRAP_START]
"""
Type of the :data:`NO_WRAP_START` placeholder.

"""

NO_WRAP_START: NoWrapStart = NoWrapMarker.NO_WRAP_START
"""
Indicates start of a no-wrap region in a :class:`ColorizedString`.

"""


NoWrapEnd: _t.TypeAlias = _t.Literal[NoWrapMarker.NO_WRAP_END]
"""
Type of the :data:`NO_WRAP_END` placeholder.

"""

NO_WRAP_END: NoWrapEnd = NoWrapMarker.NO_WRAP_END
"""
Indicates end of a no-wrap region in a :class:`ColorizedString`.

"""


@dataclass(slots=True, frozen=True, unsafe_hash=True)
class LinkMarker:
    """
    Indicates start or end of a hyperlink in a colorized string.

    """

    url: str | None
    """
    Hyperlink's url.

    """


@_t.final
@repr_from_rich
class ColorizedString:
    """ColorizedString()
    ColorizedString(rhs: ColorizedString, /)
    ColorizedString(*args: AnyString, /)

    A string with colors.

    This class is a wrapper over a list of strings, colors, and no-wrap markers.
    Each color applies to strings after it, right until the next color.

    :class:`ColorizedString` supports some basic string operations.
    Most notably, it supports wide-character-aware wrapping
    (see :meth:`~ColorizedString.wrap`),
    and ``%``-like formatting (see :meth:`~ColorizedString.percent_format`).

    Unlike :class:`str`, :class:`ColorizedString` is mutable through
    the ``+=`` operator and ``append``/``extend`` methods.

    :param rhs:
        when constructor gets a single :class:`ColorizedString`, it makes a copy.
    :param args:
        when constructor gets multiple arguments, it creates an empty string
        and appends arguments to it.


    **String combination semantics**

    When you append a :class:`str`, it will take on color and no-wrap semantics
    according to the last appended color and no-wrap marker.

    When you append another :class:`ColorizedString`, it will not change its colors
    based on the last appended color, nor will it affect colors of the consequent
    strings. If appended :class:`ColorizedString` had an unterminated no-wrap region
    or link region, this region will be terminated after appending.

    Thus, appending a colorized string does not change current color, no-wrap
    or link setting::

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
    # - for every pair of (start-no-wrap, end-no-wrap) markers, there is a string
    #   between them (i.e. no empty no-wrap regions).

    def __init__(
        self,
        /,
        *args: AnyString,
        _isolate_colors: bool = True,
    ):
        if len(args) == 1 and isinstance(args[0], ColorizedString):
            content = args[0]
            self._parts = content._parts.copy()
            self._last_color = content._last_color
            self._active_color = content._active_color
            self._last_url = content._last_url
            self._active_url = content._active_url
            self._explicit_newline = content._explicit_newline
            self._len = content._len
            self._has_no_wrap = content._has_no_wrap
            if (width := content.__dict__.get("width", None)) is not None:
                self.__dict__["width"] = width
        else:
            self._parts: list[_Color | NoWrapMarker | LinkMarker | str] = []
            self._active_color = _Color.NONE
            self._last_color: _Color | None = None
            self._last_url: str | None = None
            self._active_url: str | None = None
            self._explicit_newline: str = ""
            self._len = 0
            self._has_no_wrap = False

            if not _isolate_colors:
                # Prevent adding `_Color.NONE` to the front of the string.
                self._last_color = self._active_color

            for arg in args:
                self += arg

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

    @property
    def active_url(self) -> str | None:
        """
        Last url appended to this string.

        """

        return self._active_url

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

    def append_link(self, url: str | None, /):
        """
        Append new link marker to this string.

        This operation is lazy, the link marker will be appended if a non-empty string
        is appended after it.s

        :param url:
            link url.

        """

        self._active_url = url

    def start_link(self, url: str, /):
        """
        Start hyperlink with the given url.

        :param url:
            link url.

        """

        self._active_url = url

    def end_link(self):
        """
        End hyperlink.

        """

        self._active_url = None

    def append_str(self, s: str, /):
        """
        Append new plain string to this string.

        :param s:
            plain string to append.

        """

        if not s:
            return
        if self._last_url != self._active_url:
            self._parts.append(LinkMarker(self._active_url))
            self._last_url = self._active_url
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
            if part in (NO_WRAP_START, NO_WRAP_END) or isinstance(part, LinkMarker):
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
            parts = filter(lambda part: part not in (NO_WRAP_START, NO_WRAP_END), parts)

        if self._active_url:
            # Current url overrides appended urls.
            parts = filter(lambda part: not isinstance(part, LinkMarker), parts)

        # Ensure that current url marker is added to the string.
        # We don't need to do this with colors because `parts` already starts with
        # a correct color.
        if self._last_url != self._active_url:
            self._parts.append(LinkMarker(self._active_url))
            self._last_url = self._active_url

        self._parts.extend(parts)

        if not self._has_no_wrap and s._has_no_wrap:
            self._has_no_wrap = True
            self.end_no_wrap()
        if not self._active_url and s._last_url:
            self._last_url = s._last_url

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
        hard-wrapped if `break_long_nowrap_words` is :data:`True`. Whitespaces and
        newlines in no-wrap regions are preserved regardless of `preserve_spaces`
        and `preserve_newlines` settings.

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
        parts: _t.Iterable[str | ColorizedString | _Color | NoWrapMarker | LinkMarker],
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
        r._active_url = l._active_url
        r._has_no_wrap = l._has_no_wrap  # TODO: waat???
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

    def as_code(self, color_support: yuio.color.ColorSupport, /) -> list[str]:
        """
        Convert colors in this string to ANSI escape sequences.

        :param color_support:
            desired level of color support.
        :returns:
            raw parts of colorized string with all colors converted to ANSI
            escape sequences.

        """

        if color_support == yuio.color.ColorSupport.NONE:
            return [part for part in self._parts if isinstance(part, str)]
        else:
            parts: list[str] = []
            for part in self:
                if isinstance(part, LinkMarker):
                    parts.append("\x1b]8;;")
                    parts.append(part.url or "")
                    parts.append("\x1b\\")
                elif isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, _Color):
                    parts.append(part.as_code(color_support))
            if self._last_color != _Color.NONE:
                parts.append(_Color.NONE.as_code(color_support))
            if self._last_url is not None:
                parts.append("\x1b]8;;\x1b\\")
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

        :param width:
            desired wrapping width.
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
                  - `preserve_newlines`
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
            Defaults to `indent`.
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
            Defaults to `indent`.
        :returns:
            indented string.

        """

        nowrap_indent = ColorizedString()
        nowrap_indent.start_no_wrap()
        nowrap_continuation_indent = ColorizedString()
        nowrap_continuation_indent.start_no_wrap()
        if isinstance(indent, int):
            nowrap_indent.append_str(" " * indent)
        else:
            nowrap_indent += indent
        if continuation_indent is None:
            nowrap_continuation_indent.append_colorized_str(nowrap_indent)
        elif isinstance(continuation_indent, int):
            nowrap_continuation_indent.append_str(" " * continuation_indent)
        else:
            nowrap_continuation_indent += continuation_indent

        if not nowrap_indent and not nowrap_continuation_indent:
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
                    url = res.active_url
                    res.end_link()
                    res.append_colorized_str(nowrap_indent)
                    res.append_link(url)
                    nowrap_indent = nowrap_continuation_indent
                res.append_str(line)
                needs_indent = line.endswith(("\n", "\r", "\v"))

        return res

    def percent_format(self, args: _t.Any, ctx: ReprContext) -> ColorizedString:
        """
        Format colorized string as if with ``%``-formatting
        (i.e. `printf-style formatting`__).

        __ https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting

        :param args:
            arguments for formatting. Can be either a tuple of a mapping. Any other
            value will be converted to a tuple of one element.
        :param ctx:
            :class:`ReprContext` that will be passed to ``__colorized_str__``
            and ``__colorized_repr__`` when formatting colorables.
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

    def __iter__(self) -> _t.Iterator[_Color | NoWrapMarker | LinkMarker | str]:
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
        elif isinstance(rhs, LinkMarker):
            self.append_link(rhs.url)
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
    | LinkMarker
    | _t.Iterable[str | ColorizedString | _Color | NoWrapMarker | LinkMarker]
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

_F_SYNTAX = re.compile(
    r"""
        ^
        (?: # Options
            (?:
                (?P<fill>.)?
                (?P<align>[<>=^])
            )?
            (?P<flags>[+#]*)
            (?P<zero>0)?
        )
        (?: # Width
            (?P<width>\d+)?
            (?P<width_grouping>[,_])?
        )
        (?: # Precision
            \.
            (?P<precision>\d+)?
            (?P<precision_grouping>[,_])?
        )?
        (?: # Type
            (?P<type>.)
        )?
        $
    """,
    re.VERBOSE,
)


def _percent_format(
    s: ColorizedString, args: object, ctx: ReprContext
) -> ColorizedString:
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
    match: _tx.StrReMatch,
    args: object,
    arg_index: int,
    base_color: _Color,
    ctx: ReprContext,
) -> tuple[int, str | ColorizedString]:
    if match.group("format") == "%":
        if match.group(0) != "%%":
            raise ValueError("unsupported format character '%'")
        return arg_index, "%"

    if match.group("format") in "rsa":
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
        added_color = ctx.to_color(added_color)
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
    match: _tx.StrReMatch,
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

    res = ctx.convert(
        fmt_arg,
        match.group("format"),  # type: ignore
        multiline=multiline,
        highlighted=highlighted,
    )

    align = match.group("flag")
    if width is not None and width < 0:
        width = -width
        align = "<"
    elif align == "-":
        align = "<"
    else:
        align = ">"
    res = _apply_format(res, width, precision, align, " ")

    return arg_index, res.with_base_color(base_color)


def _format_interpolation(interp: _Interpolation, ctx: ReprContext) -> ColorizedString:
    value = interp.value
    if (
        interp.conversion is not None
        or getattr(type(value), "__format__", None) is object.__format__
        or isinstance(value, (str, ColorizedString))
    ):
        value = ctx.convert(value, interp.conversion, interp.format_spec)
    else:
        value = ColorizedString(format(value, interp.format_spec))

    return value


def _apply_format(
    value: ColorizedString,
    width: int | None,
    precision: int | None,
    align: str | None,
    fill: str | None,
):
    if precision is not None and value.width > precision:
        cut = ColorizedString()
        for part in value:
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
        value = cut

    if width is not None and width > value.width:
        fill = fill or " "
        fill_width = line_width(fill)
        spacing = width - value.width
        spacing_fill = spacing // fill_width
        spacing_space = spacing - spacing_fill * fill_width
        value.append_color(_Color.NONE)
        if not align or align == "<":
            value = value + fill * spacing_fill + " " * spacing_space
        elif align == ">":
            value = fill * spacing_fill + " " * spacing_space + value
        else:
            left = spacing_fill // 2
            right = spacing_fill - left
            value = fill * left + value + fill * right + " " * spacing_space

    return value


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
    template: str | _Template,
    /,
    *args: _t.Any,
    ctx: ReprContext,
    default_color: _Color | str = _Color.NONE,
) -> ColorizedString:
    """colorize(line: str, /, *args: typing.Any, ctx: ReprContext, default_color: ~yuio.color.Color | str = Color.NONE, parse_cli_flags_in_backticks: bool = False) -> ColorizedString
    colorize(line: ~string.templatelib.Template, /, *, ctx: ReprContext, default_color: ~yuio.color.Color | str = Color.NONE, parse_cli_flags_in_backticks: bool = False) -> ColorizedString

    Parse color tags and produce a colorized string.

    Apply ``default_color`` to the entire paragraph, and process color tags
    and backticks within it.

    :param line:
        text to colorize.
    :param args:
        if given, string will be ``%``-formatted after parsing.
        Can't be given if `line` is :class:`~string.templatelib.Template`.
    :param ctx:
        :class:`ReprContext` that will be used to look up color tags
        and format arguments.
    :param default_color:
        color or color tag to apply to the entire text.
    :returns:
        a colorized string.

    """

    interpolations: list[tuple[int, _Interpolation]] = []
    if isinstance(template, _Template):
        if args:
            raise TypeError("args can't be given with template")
        line = ""
        index = 0
        for part, interp in zip(template.strings, template.interpolations):
            line += part
            # Each interpolation is replaced by a zero byte so that our regex knows
            # there is something.
            line += "\0"
            index += len(part) + 1
            interpolations.append((index, interp))
        line += template.strings[-1]
    else:
        line = template

    default_color = ctx.to_color(default_color)

    res = ColorizedString(default_color)
    stack = [default_color]
    last_pos = 0
    last_interp = 0

    def append_to_res(s: str, start: int):
        nonlocal last_interp

        index = 0
        while (
            last_interp < len(interpolations)
            and start + len(s) >= interpolations[last_interp][0]
        ):
            interp_start, interp = interpolations[last_interp]
            res.append_str(
                s[
                    index : interp_start
                    - start
                    - 1  # This compensates for that `\0` we added above.
                ]
            )
            res.append_colorized_str(
                _format_interpolation(interp, ctx).with_base_color(res.active_color)
            )
            index = interp_start - start
            last_interp += 1
        res.append_str(s[index:])

    for tag in __TAG_RE.finditer(line):
        append_to_res(line[last_pos : tag.start()], last_pos)
        last_pos = tag.end()

        if name := tag.group("tag_open"):
            color = stack[-1] | ctx.get_color(name)
            res.append_color(color)
            stack.append(color)
        elif code := tag.group("code"):
            code = code.replace("\n", " ")
            code_pos = tag.start("code")
            if code.startswith(" ") and code.endswith(" ") and not code.isspace():
                code = code[1:-1]
                code_pos += 1
            if __FLAG_RE.match(code) and not __NEG_NUM_RE.match(code):
                res.append_color(stack[-1] | ctx.get_color("flag"))
            else:
                res.append_color(stack[-1] | ctx.get_color("code"))
            res.start_no_wrap()
            append_to_res(code, code_pos)
            res.end_no_wrap()
            res.append_color(stack[-1])
        elif punct := tag.group("punct"):
            append_to_res(punct, tag.start("punct"))
        elif len(stack) > 1:
            stack.pop()
            res.append_color(stack[-1])

    append_to_res(line[last_pos:], last_pos)

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
    if `break_long_nowrap_words` is :data:`True`.

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
        width: int,
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
        self.width = width
        self.preserve_spaces: bool = preserve_spaces
        self.preserve_newlines: bool = preserve_newlines
        self.break_long_words: bool = break_long_words
        self.break_long_nowrap_words: bool = break_long_nowrap_words
        self.overflow: _t.Literal[False] | str = overflow

        self.indent = ColorizedString()
        self.indent.start_no_wrap()
        self.continuation_indent = ColorizedString()
        self.continuation_indent.start_no_wrap()
        if isinstance(indent, int):
            self.indent.append_str(" " * indent)
        else:
            self.indent += indent
        if continuation_indent is None:
            self.continuation_indent.append_colorized_str(self.indent)
        elif isinstance(continuation_indent, int):
            self.continuation_indent.append_str(" " * continuation_indent)
        else:
            self.continuation_indent += continuation_indent

        self.lines: list[ColorizedString] = []

        self.current_line = ColorizedString()
        if self.indent:
            self.current_line += self.indent
        self.current_line_width: int = self.indent.width
        self.at_line_start: bool = True
        self.at_line_start_or_indent: bool = True
        self.has_ellipsis: bool = False
        self.add_spaces_before_word: int = 0

        self.nowrap_start_index = None
        self.nowrap_start_width = 0
        self.nowrap_start_added_space = False

    def _flush_line(self, explicit_newline=""):
        self.current_line._explicit_newline = explicit_newline
        self.lines.append(self.current_line)

        next_line = ColorizedString()

        if self.continuation_indent:
            next_line += self.continuation_indent

        next_line.append_color(self.current_line.active_color)
        next_line.append_link(self.current_line.active_url)

        self.current_line = next_line
        self.current_line_width: int = self.continuation_indent.width
        self.at_line_start = True
        self.at_line_start_or_indent = True
        self.has_ellipsis = False
        self.nowrap_start_index = None
        self.nowrap_start_width = 0
        self.nowrap_start_added_space = False
        self.add_spaces_before_word = 0

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
        self.current_line.append_link(tail.active_url)
        self.current_line_width += tail_width

    def _append_str(self, s: str):
        self.current_line.append_str(s)
        self.at_line_start = False
        self.at_line_start_or_indent = self.at_line_start_or_indent and s.isspace()

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
                self._append_str(word[:word_head_len])
                self.has_ellipsis = False
                self.current_line_width += word_head_width

            if self.overflow:
                self._add_ellipsis()
        else:
            self._append_str(word)
            self.current_line_width += word_width
            self.has_ellipsis = False

    def _append_space(self):
        if self.add_spaces_before_word:
            word = " " * self.add_spaces_before_word
            self._append_word(word, 1)
            self.add_spaces_before_word = 0

    def _add_ellipsis(self):
        if self.has_ellipsis:
            # Already has an ellipsis.
            return

        if self.current_line_width + 1 <= self.width:
            # There's enough space on this line to add new ellipsis.
            self._append_str(str(self.overflow))
            self.current_line_width += 1
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
                    self.add_spaces_before_word
                    and self.current_line_width + self.add_spaces_before_word
                    < self.width
                ):
                    # Make sure any whitespace that was added before color
                    # is flushed. If it doesn't fit, we just forget it: the line
                    # will be wrapped soon anyways.
                    self._append_space()
                self.add_spaces_before_word = 0
                self.current_line.append_color(part)
                continue
            elif isinstance(part, LinkMarker):
                if (
                    self.add_spaces_before_word
                    and self.current_line_width + self.add_spaces_before_word
                    < self.width
                ):
                    # Make sure any whitespace that was added before color
                    # is flushed. If it doesn't fit, we just forget it: the line
                    # will be wrapped soon anyways.
                    self._append_space()
                self.add_spaces_before_word = 0
                self.current_line.append_link(part.url)
                continue
            elif part is NO_WRAP_START:
                if nowrap:  # pragma: no cover
                    continue
                if (
                    self.add_spaces_before_word
                    and self.current_line_width + self.add_spaces_before_word
                    < self.width
                ):
                    # Make sure any whitespace that was added before no-wrap
                    # is flushed. If it doesn't fit, we just forget it: the line
                    # will be wrapped soon anyways.
                    self._append_space()
                    self.nowrap_start_added_space = True
                else:
                    self.nowrap_start_added_space = False
                self.add_spaces_before_word = 0
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
                            self.at_line_start_or_indent
                            and (not self.lines or self.lines[-1].explicit_newline)
                        )
                    ):
                        word = word.translate(_SPACE_TRANS)
                    else:
                        self.add_spaces_before_word = len(word)
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
                            or self.current_line_width + self.add_spaces_before_word + 1
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
            self.current_line_width + word_width + self.add_spaces_before_word
            <= self.width
        ):
            self._append_space()
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

    .. warning::

        :class:`~yuio.string.ReprContext`\\ s are not thread safe. As such,
        you shouldn't create them for long term use.

    :param term:
        terminal that will be used to print formatted messages.
    :param theme:
        theme that will be used to format messages.
    :param multiline:
        indicates that values rendered via `rich repr protocol`_
        should be split into multiple lines. Default is :data:`False`.
    :param highlighted:
        indicates that values rendered via `rich repr protocol`_
        or via built-in :func:`repr` should be highlighted according to python syntax.
        Default is :data:`False`.
    :param max_depth:
        maximum depth of nested containers, after which container's contents
        are not rendered. Default is ``5``.
    :param width:
        maximum width of the content, used when wrapping text, rendering markdown,
        or rendering horizontal rulers. If not given, defaults
        to :attr:`Theme.fallback_width <yuio.theme.Theme.fallback_width>`.

    .. _rich repr protocol: https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

    """

    def __init__(
        self,
        *,
        term: yuio.term.Term,
        theme: yuio.theme.Theme,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        max_depth: int | None = None,
        width: int | None = None,
    ):
        self.term = term
        """
        Current term.

        """

        self.theme = theme
        """
        Current theme.

        """

        self.multiline: bool = multiline if multiline is not None else False
        """
        Whether values rendered with :meth:`~ReprContext.repr` are split into multiple lines.

        """

        self.highlighted: bool = highlighted if highlighted is not None else False
        """
        Whether values rendered with :meth:`~ReprContext.repr` are highlighted.

        """

        self.max_depth: int = max_depth if max_depth is not None else 5
        """
        Maximum depth of nested containers, after which container's contents
        are not rendered.

        """

        self.width: int = max(width or theme.fallback_width, 1)
        """
        Maximum width of the content, used when wrapping text or rendering markdown.

        """

        self._seen: set[int] = set()
        self._line = ColorizedString()
        self._indent = 0
        self._state = _ReprContextState.START
        self._pending_sep = None

        import yuio.hl

        self._hl, _ = yuio.hl.get_highlighter("repr")
        self._base_color = theme.get_color("msg/text:code/repr")

    @staticmethod
    def make_dummy(is_unicode: bool = True) -> ReprContext:
        """
        Make a dummy repr context with default settings.

        """

        return ReprContext(
            term=yuio.term.Term.make_dummy(is_unicode=is_unicode),
            theme=yuio.theme.Theme(),
        )

    def get_color(self, paths: str, /) -> yuio.color.Color:
        """
        Lookup a color by path.

        """

        return self.theme.get_color(paths)

    def to_color(
        self, color_or_path: yuio.color.Color | str | None, /
    ) -> yuio.color.Color:
        """
        Convert color or color path to color.

        """

        return self.theme.to_color(color_or_path)

    def get_msg_decoration(self, name: str, /) -> str:
        """
        Get message decoration by name.

        """

        return self.theme.get_msg_decoration(name, is_unicode=self.term.is_unicode)

    def _flush_sep(self, trim: bool = False):
        if self._pending_sep is not None:
            self._push_color("punct")
            if trim:
                self._pending_sep = self._pending_sep.rstrip()
            self._line.append_str(self._pending_sep)
            self._pending_sep = None

    def _flush_line(self):
        if self.multiline:
            self._line.append_color(self._base_color)
            self._line.append_str("\n")
            if self._indent:
                self._line.append_str("  " * self._indent)

    def _flush_sep_and_line(self):
        if self.multiline and self._state in [
            _ReprContextState.CONTAINER_START,
            _ReprContextState.ITEM_START,
        ]:
            self._flush_sep(trim=True)
            self._flush_line()
        else:
            self._flush_sep()

    def _push_color(self, tag: str):
        if self.highlighted:
            self._line.append_color(
                self._base_color | self.theme.to_color(f"hl/{tag}:repr")
            )

    def _push_token(self, content: str, tag: str):
        self._flush_sep_and_line()

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
        width: int | None = None,
        max_depth: int | None = None,
    ) -> ColorizedString:
        """
        Convert value to colorized string using repr methods.

        :param value:
            value to be rendered.
        :param multiline:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param highlighted:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param width:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param max_depth:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :returns:
            a colorized string containing representation of the `value`.
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
            width=width,
            max_depth=max_depth,
        )

    def str(
        self,
        value: _t.Any,
        /,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        width: int | None = None,
        max_depth: int | None = None,
    ) -> ColorizedString:
        """
        Convert value to colorized string.

        :param value:
            value to be rendered.
        :param multiline:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param highlighted:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param width:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param max_depth:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :returns:
            a colorized string containing string representation of the `value`.
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
            width=width,
            max_depth=max_depth,
        )

    def convert(
        self,
        value: _t.Any,
        conversion: _t.Literal["a", "r", "s"] | None,
        format_spec: str | None = None,
        /,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        width: int | None = None,
        max_depth: int | None = None,
    ):
        """
        Perform string conversion, similar to :func:`string.templatelib.convert`,
        and format the object with respect to the given `format_spec`.

        :param value:
            value to be converted.
        :param conversion:
            string conversion method:

            -   ``'s'`` calls :meth:`~ReprContext.str`,
            -   ``'r'`` calls :meth:`~ReprContext.repr`,
            -   ``'a'`` calls :meth:`~ReprContext.repr` and escapes non-ascii
                characters.
        :param format_spec:
            formatting spec can override `multiline` and `highlighted`, and controls
            width, alignment, fill chars, etc. See its syntax below.
        :param multiline:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param highlighted:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param width:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param max_depth:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :returns:
            a colorized string containing string representation of the `value`.
        :raises:
            :class:`ValueError` if `conversion` or `format_spec` are invalid.

        .. _t-string-spec:

        **Format specification**

        .. syntax:diagram::

            stack:
            - optional:
              - optional:
                - optional:
                  - non_terminal: "fill"
                    href: "#t-string-spec-fill"
                - non_terminal: "align"
                  href: "#t-string-spec-align"
              - non_terminal: "flags"
                href: "#t-string-spec-flags"
            - optional:
              - comment: "width"
                href: "#t-string-spec-width"
              - "[0-9]+"
            - optional:
              - comment: "precision"
                href: "#t-string-spec-precision"
              - "'.'"
              - "[0-9]+"
            - optional:
              - comment: "conversion type"
                href: "#t-string-spec-conversion-type"
              - "'s'"
              skip_bottom: true
              skip: true

        .. _t-string-spec-fill:

        ``fill``
            Any character that will be used to extend string to the desired width.

        .. _t-string-spec-align:

        ``align``
            Controls alignment of a string when `width` is given: ``"<"`` for flushing
            string left, ``">"`` for flushing string right, ``"^"`` for centering.

        .. _t-string-spec-flags:

        ``flags``
            One or several flags: ``"#"`` to enable highlighting, ``"+"`` to enable
            multiline repr.

        .. _t-string-spec-width:

        ``width``
            If formatted string is narrower than this value, it will be extended and
            aligned using `fill` and `align` settings.

        .. _t-string-spec-precision:

        ``precision``
            If formatted string is wider that this value, it will be cropped to this
            width.

        .. _t-string-spec-conversion-type:

        ``conversion type``
            The only supported conversion type is ``"s"``.

        """

        if format_spec:
            match = _F_SYNTAX.match(format_spec)
            if not match:
                raise ValueError(f"invalid format specifier {format_spec!r}")
            fill = match.group("fill")
            align = match.group("align")
            if align == "=":
                raise ValueError("'=' alignment not allowed in string format specifier")
            flags = match.group("flags")
            if "#" in flags:
                highlighted = True
            if "+" in flags:
                multiline = True
            zero = match.group("zero")
            if zero and not fill:
                fill = zero
            format_width = match.group("width")
            if format_width:
                format_width = int(format_width)
            else:
                format_width = None
            format_width_grouping = match.group("width_grouping")
            if format_width_grouping:
                raise ValueError(f"cannot specify {format_width_grouping!r} with 's'")
            format_precision = match.group("precision")
            if format_precision:
                format_precision = int(format_precision)
            else:
                format_precision = None
            type = match.group("type")
            if type and type != "s":
                raise ValueError(f"unknown format code {type!r}")
        else:
            format_width = format_precision = align = fill = None

        if conversion == "r":
            res = self.repr(
                value,
                multiline=multiline,
                highlighted=highlighted,
                width=width,
                max_depth=max_depth,
            )
        elif conversion == "a":
            res = ColorizedString()
            for part in self.repr(
                value,
                multiline=multiline,
                highlighted=highlighted,
                width=width,
                max_depth=max_depth,
            ):
                if isinstance(part, _UserString):
                    res += part._wrap(
                        part.encode(encoding="unicode_escape").decode("ascii")
                    )
                elif isinstance(part, str):
                    res += part.encode(encoding="unicode_escape").decode("ascii")
                else:
                    res += part
        elif not conversion or conversion == "s":
            res = self.str(
                value,
                multiline=multiline,
                highlighted=highlighted,
                width=width,
                max_depth=max_depth,
            )
        else:
            raise ValueError(
                f"unknown conversion {conversion!r}, should be 'a', 'r', or 's'"
            )

        return _apply_format(res, format_width, format_precision, align, fill)

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

        highlighted = highlighted if highlighted is not None else self.highlighted

        if highlighted:
            return self._hl.highlight(
                value, theme=self.theme, syntax="repr", default_color=self._base_color
            )
        else:
            return ColorizedString(value)

    @contextlib.contextmanager
    def with_settings(
        self,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        width: int | None = None,
        max_depth: int | None = None,
    ):
        """
        Temporarily replace settings of this context.

        :param multiline:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param highlighted:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param width:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :param max_depth:
            if given, overrides settings passed to :class:`ReprContext` for this call.
        :returns:
            a context manager that overrides settings.

        """

        old_multiline, self.multiline = (
            self.multiline,
            (self.multiline if multiline is None else multiline),
        )
        old_highlighted, self.highlighted = (
            self.highlighted,
            (self.highlighted if highlighted is None else highlighted),
        )
        old_width, self.width = (
            self.width,
            (self.width if width is None else max(width, 1)),
        )
        old_max_depth, self.max_depth = (
            self.max_depth,
            (self.max_depth if max_depth is None else max_depth),
        )

        try:
            yield
        finally:
            self.multiline = old_multiline
            self.highlighted = old_highlighted
            self.width = old_width
            self.max_depth = old_max_depth

    def _print(
        self,
        value: _t.Any,
        multiline: bool | None,
        highlighted: bool | None,
        width: int | None,
        max_depth: int | None,
        use_str: bool,
    ) -> ColorizedString:
        old_line, self._line = self._line, ColorizedString()
        old_state, self._state = self._state, _ReprContextState.START
        old_pending_sep, self._pending_sep = self._pending_sep, None

        try:
            with self.with_settings(
                multiline=multiline,
                highlighted=highlighted,
                width=width,
                max_depth=max_depth,
            ):
                self._print_nested(value, use_str)
            return self._line
        except Exception as e:
            yuio._logger.exception("error in repr context")
            res = ColorizedString()
            res.append_color(_Color.STYLE_INVERSE | _Color.FORE_RED)
            res.append_str(f"{_tx.type_repr(type(e))}: {e}")
            return res
        finally:
            self._line = old_line
            self._state = old_state
            self._pending_sep = old_pending_sep

    def _print_nested(self, value: _t.Any, use_str: bool = False):
        if id(value) in self._seen or self._indent > self.max_depth:
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
            self._print_plain(value, convert=_tx.type_repr)
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
            self._print_plain(value, convert=_tx.type_repr)
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

        self._flush_sep_and_line()

        if hl and self.highlighted:
            self._line += self._hl.highlight(
                convert(value),
                theme=self.theme,
                syntax="repr",
                default_color=self._base_color,
            )
        else:
            self._line.append_str(convert(value))

        self._state = _ReprContextState.NORMAL

    def _print_list(self, name: str, obrace: str, cbrace: str, items):
        if name:
            self._push_token(name, "type")
        self._push_token(obrace, "punct")
        if self._indent >= self.max_depth:
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
        if self._indent >= self.max_depth:
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
        if self._indent >= self.max_depth:
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
        if self._indent >= self.max_depth:
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
            # See https://github.com/Textualize/rich/blob/master/LICENSE
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

        if self._indent >= self.max_depth:
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
        self._flush_sep_and_line()

        res = value.__colorized_repr__(self)
        if not isinstance(res, ColorizedString):
            raise TypeError(
                f"__colorized_repr__ returned non-colorized-string (type {_tx.type_repr(type(res))})"
            )
        self._line += res

        self._state = _ReprContextState.NORMAL

    def _print_colorized_str(self, value):
        self._flush_sep_and_line()

        res = value.__colorized_str__(self)
        if not isinstance(res, ColorizedString):
            raise TypeError(
                f"__colorized_str__ returned non-colorized-string (type {_tx.type_repr(type(res))})"
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

        if self._indent >= self.max_depth:
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


def _to_colorable(msg: _t.Any, args: tuple[_t.Any, ...] | None = None) -> Colorable:
    """
    Convert generic `msg`, `args` tuple to a colorable.

    If msg is a string, returns :class:`Format`. Otherwise, check that no arguments
    were given, and returns `msg` unchanged.

    """

    if isinstance(msg, (str, _Template)):
        return Format(_t.cast(_t.LiteralString, msg), *(args or ()))
    else:
        if args:
            raise TypeError(
                f"non-string type {_tx.type_repr(type(msg))} can't have format arguments"
            )
        return msg


class _StrBase(abc.ABC):
    def __str__(self) -> str:
        import yuio.io

        return str(yuio.io.make_repr_context().str(self))

    @abc.abstractmethod
    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        raise NotImplementedError()


@repr_from_rich
class Format(_StrBase):
    """Format(msg: typing.LiteralString, /, *args: typing.Any)
    Format(msg: ~string.templatelib.Template, /)

    Lazy wrapper that ``%``-formats the given message,
    or formats a :class:`~string.templatelib.Template`.

    This utility allows saving ``%``-formatted messages and templates and performing
    actual formatting lazily when requested. Color tags and backticks
    are handled as usual.

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
    def __init__(self, msg: _Template, /): ...
    def __init__(self, msg: str | _Template, /, *args: _t.Any):
        self._msg: str | _Template = msg
        self._args: tuple[_t.Any, ...] = args

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield from ((None, arg) for arg in self._args)

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return colorize(self._msg, *self._args, ctx=ctx)


@_t.final
@repr_from_rich
class Repr(_StrBase):
    """
    Lazy wrapper that calls :meth:`~ReprContext.repr` on the given value.

    :param value:
        value to repr.
    :param multiline:
        if given, overrides settings passed to :class:`ReprContext` for this call.
    :param highlighted:
        if given, overrides settings passed to :class:`ReprContext` for this call.
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

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        return ctx.repr(
            self.value, multiline=self.multiline, highlighted=self.highlighted
        )


@_t.final
@repr_from_rich
class TypeRepr(_StrBase):
    """
    Lazy wrapper that calls :func:`annotationlib.type_repr` on the given value
    and highlights the result.

    :param ty:
        type to format.

        If `ty` is a string, :func:`annotationlib.type_repr` is not called on it,
        allowing you to mix types and arbitrary descriptions.
    :param highlighted:
        if given, overrides settings passed to :class:`ReprContext` for this call.
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
            return ctx.hl(_tx.type_repr(self._ty), highlighted=self._highlighted)


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
    Lazy wrapper that calls :meth:`~ReprContext.str` on elements of the given collection,
    then joins the results using the given separator.

    :param collection:
        collection that will be printed.
    :param sep:
        separator that's printed between elements of the collection.
    :param sep_two:
        separator that's used when there are only two elements in the collection.
        Defaults to `sep`.
    :param sep_last:
        separator that's used between the last and prior-to-last element
        of the collection. Defaults to `sep`.
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
        return self._render(ctx.theme, ctx.str)


@_t.final
class JoinRepr(_JoinBase):
    """
    Lazy wrapper that calls :meth:`~ReprContext.repr` on elements of the given collection,
    then joins the results using the given separator.

    :param collection:
        collection that will be printed.
    :param sep:
        separator that's printed between elements of the collection.
    :param sep_two:
        separator that's used when there are only two elements in the collection.
        Defaults to `sep`.
    :param sep_last:
        separator that's used between the last and prior-to-last element
        of the collection. Defaults to `sep`.
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
        return self._render(ctx.theme, ctx.repr)


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
class Link(_StrBase):
    """
    Lazy wrapper that adds a hyperlink to whatever is passed to it.

    :param msg:
        link body.
    :param url:
        link url, should be properly urlencoded.

    """

    def __init__(self, msg: Colorable, /, *, url: str):
        self._msg = msg
        self._url = url

    @classmethod
    def from_path(cls, msg: Colorable, /, *, path: str | pathlib.Path) -> _t.Self:
        """
        Create a link to a local file.

        Ensures that file path is absolute and properly formatted.

        :param msg:
            link body.
        :param path:
            path to a file.

        """

        url = pathlib.Path(path).expanduser().absolute().as_uri()
        return cls(msg, url=url)

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield "url", self._url

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        res = ColorizedString()
        res.start_link(self._url)
        res.append_colorized_str(ctx.str(self._msg))
        if not ctx.term.supports_colors:
            res.start_no_wrap()
            res.append_str(" [")
            res.append_str(self._url)
            res.append_str("]")
            res.end_no_wrap()
        res.end_link()
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
        Defaults to `indent`.
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
        width = max(1, ctx.width - indent_width)

        return ctx.str(self._msg, width=width).indent(indent, continuation_indent)


@_t.final
@repr_from_rich
class Md(_StrBase):
    """Md(msg: typing.LiteralString, /, *args, width: int | None | yuio.Missing = yuio.MISSING, dedent: bool = True, allow_headings: bool = True)
    Md(msg: str, /, *, width: int | None | yuio.Missing = yuio.MISSING, dedent: bool = True, allow_headings: bool = True)

    Lazy wrapper that renders markdown during formatting.

    :param md:
        text to format.
    :param width:
        if given, overrides settings passed to :class:`ReprContext` for this call.
    :param dedent:
        whether to remove leading indent from text.
    :param allow_headings:
        whether to render headings as actual headings or as paragraphs.

    """

    def __init__(
        self,
        md: str,
        /,
        *,
        width: int | None = None,
        dedent: bool = True,
        allow_headings: bool = True,
    ):
        self._md: str = md
        self._width: int | None = width
        self._dedent: bool = dedent
        self._allow_headings: bool = allow_headings

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._md
        yield "width", self._width, yuio.MISSING
        yield "dedent", self._dedent, True
        yield "allow_headings", self._allow_headings, True

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        import yuio.doc
        import yuio.md

        width = self._width or ctx.width
        with ctx.with_settings(width=width):
            formatter = yuio.doc.Formatter(
                ctx,
                allow_headings=self._allow_headings,
            )

            res = ColorizedString()
            res.start_no_wrap()
            sep = False
            for line in formatter.format(yuio.md.parse(self._md, dedent=self._dedent)):
                if sep:
                    res += "\n"
                res += line
                sep = True
            res.end_no_wrap()

            return res


@_t.final
@repr_from_rich
class Rst(_StrBase):
    """Rst(msg: typing.LiteralString, /, *args, width: int | None | yuio.Missing = yuio.MISSING, dedent: bool = True, allow_headings: bool = True)
    Rst(msg: str, /, *, width: int | None | yuio.Missing = yuio.MISSING, dedent: bool = True, allow_headings: bool = True)

    Lazy wrapper that renders ReStructuredText during formatting.

    :param rst:
        text to format.
    :param width:
        if given, overrides settings passed to :class:`ReprContext` for this call.
    :param dedent:
        whether to remove leading indent from text.
    :param allow_headings:
        whether to render headings as actual headings or as paragraphs.

    """

    def __init__(
        self,
        rst: str,
        /,
        *,
        width: int | None = None,
        dedent: bool = True,
        allow_headings: bool = True,
    ):
        self._rst: str = rst
        self._width: int | None = width
        self._dedent: bool = dedent
        self._allow_headings: bool = allow_headings

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._rst
        yield "width", self._width, yuio.MISSING
        yield "dedent", self._dedent, True
        yield "allow_headings", self._allow_headings, True

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        import yuio.doc
        import yuio.rst

        width = self._width or ctx.width
        with ctx.with_settings(width=width):
            formatter = yuio.doc.Formatter(
                ctx,
                allow_headings=self._allow_headings,
            )

            res = ColorizedString()
            res.start_no_wrap()
            sep = False
            for line in formatter.format(
                yuio.rst.parse(self._rst, dedent=self._dedent)
            ):
                if sep:
                    res += "\n"
                res += line
                sep = True
            res.end_no_wrap()

            return res


@_t.final
@repr_from_rich
class Hl(_StrBase):
    """Hl(code: typing.LiteralString, /, *args, syntax: str, dedent: bool = True)
    Hl(code: str, /, *, syntax: str, dedent: bool = True)

    Lazy wrapper that highlights code during formatting.

    :param md:
        code to highlight.
    :param args:
        arguments for ``%``-formatting the highlighted code.
    :param syntax:
        name of syntax or a :class:`~yuio.hl.SyntaxHighlighter` instance.
    :param dedent:
        whether to remove leading indent from code.

    """

    @_t.overload
    def __init__(
        self,
        code: _t.LiteralString,
        /,
        *args: _t.Any,
        syntax: str,
        dedent: bool = True,
    ): ...
    @_t.overload
    def __init__(
        self,
        code: str,
        /,
        *,
        syntax: str,
        dedent: bool = True,
    ): ...
    def __init__(
        self,
        code: str,
        /,
        *args: _t.Any,
        syntax: str,
        dedent: bool = True,
    ):
        self._code: str = code
        self._args: tuple[_t.Any, ...] = args
        self._syntax: str = syntax
        self._dedent: bool = dedent

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._code
        yield from ((None, arg) for arg in self._args)
        yield "syntax", self._syntax
        yield "dedent", self._dedent, True

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        import yuio.hl

        highlighter, syntax_name = yuio.hl.get_highlighter(self._syntax)
        code = self._code
        if self._dedent:
            code = _dedent(code)
        code = code.rstrip()

        res = ColorizedString()
        res.start_no_wrap()
        res += highlighter.highlight(code, theme=ctx.theme, syntax=syntax_name)
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
    :param width:
        if given, overrides settings passed to :class:`ReprContext` for this call.
    :param preserve_spaces:
        if set to :data:`True`, all spaces are preserved.
        Otherwise, consecutive spaces are collapsed when newline break occurs.

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
        Defaults to `indent`.

    """

    def __init__(
        self,
        msg: Colorable,
        /,
        *,
        width: int | None = None,
        preserve_spaces: bool = False,
        preserve_newlines: bool = True,
        break_long_words: bool = True,
        break_long_nowrap_words: bool = False,
        overflow: bool | str = False,
        indent: AnyString | int = "",
        continuation_indent: AnyString | int | None = None,
    ):
        self._msg = msg
        self._width: int | None = width
        self._preserve_spaces = preserve_spaces
        self._preserve_newlines = preserve_newlines
        self._break_long_words = break_long_words
        self._break_long_nowrap_words = break_long_nowrap_words
        self._overflow = overflow
        self._indent: AnyString | int = indent
        self._continuation_indent: AnyString | int | None = continuation_indent

    def __rich_repr__(self) -> RichReprResult:
        yield None, self._msg
        yield "width", self._width, None
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

        width = self._width or ctx.width
        indent_width = max(indent.width, continuation_indent.width)
        inner_width = max(1, width - indent_width)

        overflow = self._overflow
        if overflow is True:
            overflow = ctx.get_msg_decoration("overflow")

        res = ColorizedString()
        res.start_no_wrap()
        sep = False
        for line in ctx.str(self._msg, width=inner_width).wrap(
            width,
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
        return ctx.str(self._msg).with_base_color(ctx.to_color(self._base_color))


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
        :attr:`Theme.msg_decorations <yuio.theme.Theme.msg_decorations_unicode>`.
    :param width:
        if given, overrides settings passed to :class:`ReprContext` for this call.
    :param overflow:
        pass :data:`False` to disable trimming `msg` to terminal width.
    :param kwargs:
        Other keyword arguments override corresponding decorations from the theme:

        :`left_start`:
            start of the ruler to the left of the message.
        :`left_middle`:
            filler of the ruler to the left of the message.
        :`left_end`:
            end of the ruler to the left of the message.
        :`middle`:
            filler of the ruler that's used if `msg` is empty.
        :`right_start`:
            start of the ruler to the right of the message.
        :`right_middle`:
            filler of the ruler to the right of the message.
        :`right_end`:
            end of the ruler to the right of the message.

    """

    def __init__(
        self,
        msg: Colorable = "",
        /,
        *,
        width: int | None = None,
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
        self._width = width
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
        yield "width", self._width, None
        yield "overflow", self._overflow, None
        yield "left_start", self._left_start, None
        yield "left_middle", self._left_middle, None
        yield "left_end", self._left_end, None
        yield "middle", self._middle, None
        yield "right_start", self._right_start, None
        yield "right_middle", self._right_middle, None
        yield "right_end", self._right_end, None

    def __colorized_str__(self, ctx: ReprContext) -> ColorizedString:
        width = self._width or ctx.width

        color = ctx.get_color(f"msg/decoration:hr/{self._weight}")

        res = ColorizedString(color)
        res.start_no_wrap()

        msg = ctx.str(self._msg)
        if not msg:
            res.append_str(self._make_whole(width, ctx))
            return res

        overflow = self._overflow
        if overflow is True:
            overflow = ctx.get_msg_decoration("overflow")

        sep = False
        for line in msg.wrap(
            width, preserve_spaces=True, break_long_words=False, overflow=overflow
        ):
            if sep:
                res.append_color(yuio.color.Color.NONE)
                res.append_str("\n")
                res.append_color(color)

            line_w = line.width
            line_w_fill = max(0, width - line_w)
            line_w_fill_l = line_w_fill // 2
            line_w_fill_r = line_w_fill - line_w_fill_l
            if not line_w_fill_l and not line_w_fill_r:
                res.append_colorized_str(line)
                return res

            res.append_str(self._make_left(line_w_fill_l, ctx))
            res.append_colorized_str(line)
            res.append_str(self._make_right(line_w_fill_r, ctx))

            sep = True

        return res

    def _make_left(self, w: int, ctx: ReprContext):
        weight = self._weight
        start = (
            self._left_start
            if self._left_start is not None
            else ctx.get_msg_decoration(f"hr/{weight}/left_start")
        )
        middle = (
            self._left_middle
            if self._left_middle is not None
            else ctx.get_msg_decoration(f"hr/{weight}/left_middle")
        ) or " "
        end = (
            self._left_end
            if self._left_end is not None
            else ctx.get_msg_decoration(f"hr/{weight}/left_end")
        )

        return _make_left(w, start, middle, end)

    def _make_right(self, w: int, ctx: ReprContext):
        weight = self._weight
        start = (
            self._right_start
            if self._right_start is not None
            else ctx.get_msg_decoration(f"hr/{weight}/right_start")
        )
        middle = (
            self._right_middle
            if self._right_middle is not None
            else ctx.get_msg_decoration(f"hr/{weight}/right_middle")
        ) or " "
        end = (
            self._right_end
            if self._right_end is not None
            else ctx.get_msg_decoration(f"hr/{weight}/right_end")
        )

        return _make_right(w, start, middle, end)

    def _make_whole(self, w: int, ctx: ReprContext):
        weight = self._weight
        start = (
            self._left_start
            if self._left_start is not None
            else ctx.get_msg_decoration(f"hr/{weight}/left_start")
        )
        middle = (
            self._middle
            if self._middle is not None
            else ctx.get_msg_decoration(f"hr/{weight}/middle")
        ) or " "
        end = (
            self._right_end
            if self._right_end is not None
            else ctx.get_msg_decoration(f"hr/{weight}/right_end")
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
