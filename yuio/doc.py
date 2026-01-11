# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Utilities for parsing and formatting documentation.

.. autoclass:: Formatter
    :members:

.. autoclass:: DocParser
    :members:


AST
---

.. autoclass:: AstBase
    :members:

.. autoclass:: Raw
    :members:

.. autoclass:: Text
    :members:

.. autoclass:: TextRegion
    :members:

.. autoclass:: Container
    :members:

.. autoclass:: Document
    :members:

.. autoclass:: ThematicBreak
    :members:

.. autoclass:: Heading
    :members:

.. autoclass:: Paragraph
    :members:

.. autoclass:: Quote
    :members:

.. autoclass:: Admonition
    :members:

.. autoclass:: Footnote
    :members:

.. autoclass:: FootnoteContainer
    :members:

.. autoclass:: Code
    :members:

.. autoclass:: ListEnumeratorKind
    :members:

.. autoclass:: ListMarkerKind
    :members:

.. autoclass:: ListItem
    :members:

.. autoclass:: List
    :members:

.. autoclass:: NoHeadings
    :members:


Helpers
-------

.. autofunction:: to_roman

.. autofunction:: from_roman

.. autofunction:: to_letters

.. autofunction:: from_letters

"""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import re
from dataclasses import dataclass
from enum import Enum

import yuio.color
import yuio.hl
import yuio.string

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "Admonition",
    "AstBase",
    "Code",
    "Container",
    "DocParser",
    "Document",
    "Footnote",
    "FootnoteContainer",
    "Formatter",
    "Heading",
    "List",
    "ListEnumeratorKind",
    "ListItem",
    "ListMarkerKind",
    "NoHeadings",
    "Paragraph",
    "Quote",
    "Raw",
    "Text",
    "TextRegion",
    "ThematicBreak",
    "from_letters",
    "from_roman",
    "to_letters",
    "to_roman",
]


class DocParser(abc.ABC):
    """
    Base class for document parsers.

    """

    @abc.abstractmethod
    def parse(self, s: str, /) -> Document:
        """
        Parse the given document and return its AST structure.

        :param s:
            document to parse.
        :returns:
            document AST.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def parse_paragraph(self, s: str, /) -> list[str | TextRegion]:
        """
        Parse inline markup in the given paragraph.

        :param s:
            paragraph to parse.
        :returns:
            inline AST.

        """

        raise NotImplementedError()


@_t.final
class Formatter:
    """
    A formatter suitable for displaying RST/Markdown documents in the terminal.

    :param ctx:
        a :class:`~yuio.string.ReprContext` that's used to colorize or wrap
        rendered document.
    :param allow_headings:
        if set to :data:`False`, headings are rendered as paragraphs.

    """

    def __init__(
        self,
        ctx: yuio.string.ReprContext,
        *,
        allow_headings: bool = True,
    ):
        self._ctx = ctx
        self._allow_headings: bool = allow_headings
        self._is_first_line: bool
        self._out: list[yuio.string.ColorizedString]
        self._indent: yuio.string.ColorizedString
        self._continuation_indent: yuio.string.ColorizedString

    @property
    def ctx(self):
        return self._ctx

    @property
    def width(self):
        return self._ctx.width

    def format(self, node: AstBase, /) -> list[yuio.string.ColorizedString]:
        """
        Format a parsed document.

        :param node:
            AST node to format.
        :returns:
            rendered document as a list of individual lines without newline
            characters at the end.

        """

        self._is_first_line = True
        self._separate_paragraphs = True
        self._out = []
        self._indent = yuio.string.ColorizedString()
        self._continuation_indent = yuio.string.ColorizedString()

        self._format(node)

        return self._out

    @contextlib.contextmanager
    def _with_indent(
        self,
        color: yuio.color.Color | str | None,
        s: yuio.string.AnyString,
        /,
        *,
        continue_with_spaces: bool = True,
    ):
        color = self.ctx.to_color(color)
        indent = yuio.string.ColorizedString(color)
        indent += s

        old_indent = self._indent
        old_continuation_indent = self._continuation_indent

        if continue_with_spaces:
            continuation_indent = yuio.string.ColorizedString(" " * indent.width)
        else:
            continuation_indent = indent

        self._indent = first_line_indent = self._indent + indent
        self._continuation_indent = self._continuation_indent + continuation_indent

        try:
            yield
        finally:
            self._indent = (
                old_indent
                if self._indent == first_line_indent
                else old_continuation_indent
            )
            self._continuation_indent = old_continuation_indent

    def _line(self, line: yuio.string.ColorizedString, /):
        self._out.append(line)

        self._is_first_line = False
        self._indent = self._continuation_indent

    def _format(self, node: AstBase, /):
        getattr(self, f"_format_{node.__class__.__name__.lstrip('_')}")(node)

    def _format_Raw(self, node: Raw, /):
        for line in node.raw.wrap(
            self.width,
            indent=self._indent,
            continuation_indent=self._continuation_indent,
            break_long_nowrap_words=True,
        ):
            self._line(line)

    def _format_inline(
        self, items: list[str | TextRegion], /, *, default_color: yuio.color.Color
    ):
        s = yuio.string.ColorizedString()

        for item in items:
            if isinstance(item, str):
                s.append_color(default_color)
                s.append_str(item)
            else:
                color = default_color
                for path in item.colors:
                    color |= self.ctx.get_color(path)
                s.append_color(color)
                if item.no_wrap:
                    s.start_no_wrap()
                s.append_str(item.content)
                if item.no_wrap:
                    s.end_no_wrap()

        for line in s.wrap(
            self.width,
            indent=self._indent,
            continuation_indent=self._continuation_indent,
            preserve_newlines=False,
            break_long_nowrap_words=True,
        ):
            self._line(line)

    def _format_Text(self, node: Text, /, *, default_color: yuio.color.Color):
        self._format_inline(node.items, default_color=default_color)

    def _format_Container(self, node: Container[TAst], /):
        self._is_first_line = True
        for item in node.items:
            if not self._is_first_line and self._separate_paragraphs:
                self._line(self._indent)
            self._format(item)

    def _format_Document(self, node: Document, /):
        self._format_Container(node)

    def _format_ThematicBreak(self, _: ThematicBreak):
        decoration = self.ctx.get_msg_decoration("thematic_break")
        color = self.ctx.get_color("msg/decoration:thematic_break")
        self._line(self._indent + color + decoration)

    def _format_Heading(self, node: Heading, /):
        if not self._allow_headings:
            self._format_Text(
                node, default_color=self.ctx.get_color("msg/text:paragraph")
            )
            return

        if not self._is_first_line:
            self._line(self._indent)

        level = node.level
        decoration = self.ctx.get_msg_decoration(f"heading/{level}")
        with self._with_indent(f"msg/decoration:heading/{level}", decoration):
            self._format_Text(
                node,
                default_color=self.ctx.get_color(f"msg/text:heading/{level}"),
            )

        self._line(self._indent)
        self._is_first_line = True

    def _format_Paragraph(self, node: Paragraph, /):
        self._format_Text(node, default_color=self.ctx.get_color("msg/text:paragraph"))

    def _format_ListItem(
        self,
        node: ListItem,
        /,
        *,
        marker: str | None = None,
        max_marker_width: int = 0,
    ):
        decoration = self.ctx.get_msg_decoration("list")
        if marker:
            max_marker_width = max(max_marker_width, yuio.string.line_width(decoration))
            decoration = f"{marker:<{max_marker_width}}"
        if not node.items:
            node.items = [Paragraph(items=[])]
        with self._with_indent("msg/decoration:list", decoration):
            self._format_Container(node)

    def _format_Quote(self, node: Quote, /):
        decoration = self.ctx.get_msg_decoration("quote")
        with self._with_indent(
            "msg/decoration:quote", decoration, continue_with_spaces=False
        ):
            self._format_Container(node)

    def _format_Admonition(self, node: Admonition, /):
        decoration = self.ctx.get_msg_decoration("admonition/title")
        with self._with_indent(
            f"admonition/decoration/title:{node.type}",
            decoration,
            continue_with_spaces=False,
        ):
            self._format_inline(
                node.title,
                default_color=self.ctx.get_color(f"admonition/title:{node.type}"),
            )
        decoration = self.ctx.get_msg_decoration("admonition/body")
        with self._with_indent(
            f"admonition/decoration/body:{node.type}",
            decoration,
            continue_with_spaces=False,
        ):
            self._format_Container(node)

    def _format_Footnote(self, node: Footnote, /):
        if yuio.string.line_width(node.marker) > 2:
            indent = "    "
            self._line(self._indent + self.ctx.get_color("footnote") + node.marker)
        else:
            indent = f"{node.marker!s:4}"
        with self._with_indent("footnote", indent):
            self._format_Container(node)

    def _format_FootnoteContainer(self, node: FootnoteContainer, /):
        prev_separate_paragraphs = self._separate_paragraphs
        self._separate_paragraphs = False
        try:
            self._format_ThematicBreak(ThematicBreak())
            self._format_Container(node)
        finally:
            self._separate_paragraphs = prev_separate_paragraphs

    def _format_Code(self, node: Code, /):
        highlighter, syntax_name = yuio.hl.get_highlighter(node.syntax)
        s = highlighter.highlight(
            "\n".join(node.lines),
            theme=self.ctx.theme,
            syntax=syntax_name,
        )

        decoration = self.ctx.get_msg_decoration("code")
        with self._with_indent("msg/decoration:code", decoration):
            self._line(
                s.indent(
                    indent=self._indent,
                    continuation_indent=self._continuation_indent,
                )
            )

    def _format_List(self, node: List, /):
        if not node.items:
            return

        match node.enumerator_kind:
            case ListEnumeratorKind.NUMBER:
                format_marker = lambda c: f"{c}."
            case ListEnumeratorKind.SMALL_LETTER:
                format_marker = lambda c: f"{to_letters(c)}."
            case ListEnumeratorKind.CAPITAL_LETTER:
                format_marker = lambda c: f"{to_letters(c).upper()}."
            case ListEnumeratorKind.SMALL_ROMAN:
                format_marker = lambda c: f"{to_roman(c)}."
            case ListEnumeratorKind.CAPITAL_ROMAN:
                format_marker = lambda c: f"{to_roman(c).upper()}."
            case _:
                format_marker = None

        n = node.items[0].number

        if n and format_marker:
            formatted_markers = [format_marker(n + i) for i in range(len(node.items))]
            max_marker_width = (
                max(yuio.string.line_width(marker) for marker in formatted_markers) + 1
            )
        else:
            formatted_markers = [None] * len(node.items)
            max_marker_width = 0

        self._is_first_line = True
        separate_paragraphs = self._separate_paragraphs
        if all(
            not item.items
            or (len(item.items) == 1 and isinstance(item.items[0], Paragraph))
            for item in node.items
        ):
            separate_paragraphs = False
        for item, marker in zip(node.items, formatted_markers):
            if not self._is_first_line and separate_paragraphs:
                self._line(self._indent)
            self._format_ListItem(
                item, marker=marker, max_marker_width=max_marker_width
            )

    def _format_NoHeadings(self, node: NoHeadings, /):
        prev_allow_headings = self._allow_headings
        self._allow_headings = False
        try:
            self._format_Container(node)
        finally:
            self._allow_headings = prev_allow_headings


TAst = _t.TypeVar("TAst", bound="AstBase")


@dataclass(kw_only=True, slots=True)
class AstBase(abc.ABC):
    """
    Base class for all AST nodes that represent parsed Markdown and RST documents.

    """

    def _dump_params(self) -> str:
        s = self.__class__.__name__.lstrip("_")
        for field in dataclasses.fields(self):
            if field.repr:
                s += f" {getattr(self, field.name)!r}"
        return s

    def dump(self, indent: str = "") -> str:
        """
        Dump an AST node into a lisp-like text representation.

        """

        return f"{indent}({self._dump_params()})"


@dataclass(kw_only=True, slots=True)
class Raw(AstBase):
    """
    Embeds already formatted paragraph into the document.

    """

    raw: yuio.string.ColorizedString
    """
    Raw colorized string to add to the document.

    """


@dataclass(kw_only=True, slots=True)
class Text(AstBase):
    """
    Base class for all text-based AST nodes, i.e. paragraphs, headings, etc.

    """

    items: list[str | TextRegion] = dataclasses.field(repr=False)
    """
    Text lines as parsed from the original document.

    """

    def dump(self, indent: str = "") -> str:
        s = f"{indent}({self._dump_params()}"
        indent += "  "
        for line in self.items:
            s += "\n" + indent
            s += repr(line)
        s += ")"
        return s


@dataclass(kw_only=True, slots=True)
class TextRegion:
    """
    Highlighted text region.

    """

    content: str
    """
    Highlighted text.

    """

    colors: list[str]
    """
    Color paths to be applied.

    """

    no_wrap: bool = False
    """
    Whether to wrap contents.

    """

    def __str__(self):
        return self.content


@dataclass(kw_only=True, slots=True)
class Container(AstBase, _t.Generic[TAst]):
    """
    Base class for all container-based AST nodes, i.e. list items or quotes.

    This class works as a list of items. Usually it contains arbitrary AST nodes,
    but it can also be limited to specific kinds of nodes via its generic variable.

    """

    items: list[TAst] = dataclasses.field(repr=False)
    """
    Inner AST nodes in the container.

    """

    def dump(self, indent: str = "") -> str:
        s = f"{indent or ''}({self._dump_params()}"
        indent += "  "
        for items in self.items:
            s += "\n"
            s += items.dump(indent)
        s += ")"
        return s


@dataclass(kw_only=True, slots=True)
class Document(Container[AstBase]):
    """
    Root node that contains the entire document.

    """


@dataclass(kw_only=True, slots=True)
class ThematicBreak(AstBase):
    """
    Represents a visual break in text, a.k.a. an asterism.

    """


@dataclass(kw_only=True, slots=True)
class Heading(Text):
    """
    Represents a heading.

    """

    level: int
    """
    Level of the heading, `1`-based.

    """


@dataclass(kw_only=True, slots=True)
class Paragraph(Text):
    """
    Represents a regular paragraph.

    """


@dataclass(kw_only=True, slots=True)
class Quote(Container[AstBase]):
    """
    Represents a quotation block.

    """


@dataclass(kw_only=True, slots=True)
class Admonition(Container[AstBase]):
    """
    Represents an admonition block.

    """

    title: list[str | TextRegion]
    """
    Main title.

    """

    type: str
    """
    Admonition type.

    """


@dataclass(kw_only=True, slots=True)
class Footnote(Container[AstBase]):
    """
    Represents a footnote.

    """

    marker: str
    """
    Footnote number or marker.

    """


@dataclass(eq=False, match_args=False, slots=True)
class FootnoteContainer(Container[Footnote]):
    """
    Container for footnotes, enables compact rendering.

    """


@dataclass(kw_only=True, slots=True)
class Code(AstBase):
    """
    Represents a highlighted block of code.

    """

    lines: list[str] = dataclasses.field(repr=False)
    """
    Code lines as parsed from the original document.

    """

    def dump(self, indent: str = "") -> str:
        s = f"{indent}({self._dump_params()}"
        indent += "  "
        for line in self.lines:
            s += "\n" + indent
            s += repr(line)
        s += ")"
        return s

    syntax: str
    """
    Syntax indicator as parsed form the original document.

    """


class ListEnumeratorKind(Enum):
    """
    For enumerated lists, represents how numbers should look.

    """

    NUMBER = "NUMBER"
    """
    Numeric, i.e. ``1, 2, 3``.
    """

    SMALL_LETTER = "SMALL_LETTER"
    """
    Small letters, i.e. ``a, b, c``.
    """

    CAPITAL_LETTER = "CAPITAL_LETTER"
    """
    Capital letters, i.e. ``A, B, C``.
    """

    SMALL_ROMAN = "SMALL_ROMAN"
    """
    Small roman numerals, i.e. ``i, ii, iii``.
    """

    CAPITAL_ROMAN = "CAPITAL_ROMAN"
    """
    Capital roman numerals, i.e. ``I, II, III``.
    """


class ListMarkerKind(Enum):
    """
    For enumerated lists, represents how numbers are stylized.

    """

    DOT = "DOT"
    """
    Dot after a number, i.e. ``1.``.

    """

    PAREN = "PAREN"
    """
    Paren after a number, i.e. ``1)``.

    """

    ENCLOSED = "ENCLOSED"
    """
    Parens around a number, i.e. ``(1)``.

    """


@dataclass(kw_only=True, slots=True)
class ListItem(Container[AstBase]):
    """
    A possibly numbered element of a list.

    """

    number: int | None
    """
    If present, this is the item's number in a numbered list.

    """


@dataclass(kw_only=True, slots=True)
class List(Container[ListItem]):
    """
    A collection of list items.

    """

    enumerator_kind: ListEnumeratorKind | str | None = None
    """
    Enumerator kind for numbered lists, or symbol for bullet lists.

    """

    marker_kind: ListMarkerKind | None = None
    """
    Marker kind for numbered lists.

    """


@dataclass(kw_only=True, slots=True)
class NoHeadings(Container[AstBase]):
    """
    Suppresses headings rendering for its children.

    """


_ROMAN_VALUES = {
    "m": 1000,
    "cm": 900,
    "d": 500,
    "cd": 400,
    "c": 100,
    "xc": 90,
    "l": 50,
    "xl": 40,
    "x": 10,
    "ix": 9,
    "v": 5,
    "iv": 4,
    "i": 1,
}


def to_roman(n: int, /) -> str:
    """
    Convert positive integer to lower-case roman numeral.

    """

    assert n > 0

    result = ""
    for numeral, integer in _ROMAN_VALUES.items():
        while n >= integer:
            result += numeral
            n -= integer
    return result


def from_roman(s: str, /) -> int | None:
    """
    Parse roman numeral, return :data:`None` if parsing fails.

    """

    total = 0
    prev_value = 0
    for c in reversed(s.casefold()):
        value = _ROMAN_VALUES.get(c, 0)
        if not value:
            return None
        if value < prev_value:
            # If current value is less than previous, subtract it (e.g. IV = 4).
            total -= value
        else:
            total += value
        prev_value = value
    return total


def to_letters(n: int, /) -> str:
    """
    Convert positive integer to lowercase excel-column-like letter numeral.

    """

    assert n > 0

    result = ""
    while n > 0:
        n -= 1
        result = chr(ord("a") + n % 26) + result
        n //= 26

    return result


def from_letters(s: str, /):
    """
    Parse excel-column-like letter numeral, return :data:`None` if parsing fails.

    """

    if not s.isalpha():
        return None

    s = s.casefold()
    result = 0

    for char in s:
        result = result * 26 + (ord(char) - ord("a") + 1)

    return result


def _make_directive(
    name: str,
    arg: str,
    get_lines: _t.Callable[[], list[str]],
    get_parsed: _t.Callable[[], list[AstBase]],
):
    if name in ["code-block", "sourcecode", "code"]:
        syntax = arg
    elif name in [
        "attention",
        "caution",
        "danger",
        "error",
        "hint",
        "important",
        "note",
        "seealso",
        "tip",
        "warning",
    ]:
        return Admonition(
            title=[name.title()],
            items=get_parsed(),
            type=name,
        )
    elif name == "admonition":
        return Admonition(
            title=[arg],
            items=get_parsed(),
            type=name,
        )
    elif name in [
        "versionadded",
        "versionchanged",
        "deprecated",
    ]:
        return Admonition(
            title=[
                name.removeprefix("version").title(),
                " in version ",
                arg,
            ],
            items=get_parsed(),
            type=name,
        )
    else:
        syntax = "text"
    return Code(lines=get_lines(), syntax=syntax)


_CROSSREF_RE = re.compile(
    r"""
        ^
        (?P<title>(?:[^\\]|\\.)*?)
        (?:\s*<(?P<target>.*)>)?
        $
    """,
    re.VERBOSE,
)


def _split_crossref(href: str):
    match = _CROSSREF_RE.match(href)
    if not match:
        return href, href
    title = match.group("title")
    target = match.group("target")
    if not target:
        target = title
        if title.startswith("~"):
            target = target[1:]
            title = title[1:].rsplit(".", maxsplit=1)[-1]
    else:
        title = title.rstrip()
    return target, title


def _split_link(href: str):
    match = _CROSSREF_RE.match(href)
    if not match:
        return None, href
    return match.group("target"), match.group("title")
