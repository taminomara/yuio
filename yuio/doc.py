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

.. autoclass:: Cut
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
    "Cut",
    "DecorationRegion",
    "DocParser",
    "Document",
    "Footnote",
    "FootnoteContainer",
    "Formatter",
    "Heading",
    "HighlightedRegion",
    "LinkRegion",
    "List",
    "ListEnumeratorKind",
    "ListItem",
    "ListMarkerKind",
    "NoHeadings",
    "NoWrapRegion",
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
        self._colors: list[yuio.color.Color]

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
        self._colors = []

        self._format(node)

        return self._out

    @contextlib.contextmanager
    def _with_color(self, color: yuio.color.Color | str | None):
        color = self.ctx.to_color(color)
        if self._colors:
            color = self._colors[-1] | color
        self._colors.append(color)
        try:
            yield
        finally:
            self._colors.pop()

    def _text_color(self) -> yuio.color.Color:
        if self._colors:
            return self._colors[-1]
        else:
            return yuio.color.Color.NONE

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
            if self._indent == first_line_indent:
                self._indent = old_indent
            else:
                self._indent = old_continuation_indent
            self._continuation_indent = old_continuation_indent

    def _line(self, line: yuio.string.ColorizedString, /):
        self._out.append(line)

        self._is_first_line = False
        self._indent = self._continuation_indent

    def _format(self, node: AstBase, /):
        getattr(self, f"_format_{node.__class__.__name__.lstrip('_')}")(node)

    def _format_Raw(self, node: Raw, /):
        for line in node.raw.with_base_color(self._text_color()).wrap(
            self.width,
            indent=self._indent,
            continuation_indent=self._continuation_indent,
            break_long_nowrap_words=True,
        ):
            self._line(line)

    def _format_Text(self, node: Text, /):
        text = self._format_inline(node.items, default_color=self._text_color())
        for line in text.wrap(
            self.width,
            indent=self._indent,
            continuation_indent=self._continuation_indent,
            preserve_newlines=False,
            break_long_nowrap_words=True,
        ):
            self._line(line)

    def _format_Container(self, node: Container[TAst], /, *, allow_empty: bool = False):
        self._is_first_line = True
        items = node.items
        if not items and not allow_empty:
            items = [Paragraph(items=[""])]
        for item in items:
            if not self._is_first_line and self._separate_paragraphs:
                self._line(self._indent)
            self._format(item)

    def _format_Document(self, node: Document, /):
        self._format_Container(node, allow_empty=True)

    def _format_ThematicBreak(self, _: ThematicBreak):
        decoration = self.ctx.get_msg_decoration("thematic_break")
        color = self.ctx.get_color("msg/decoration:thematic_break")
        self._line(self._indent + color + decoration)

    def _format_Heading(self, node: Heading, /):
        if not self._allow_headings:
            with self._with_color("msg/text:paragraph"):
                self._format_Text(node)
            return

        if not self._is_first_line:
            self._line(self._indent)

        level = node.level
        decoration = self.ctx.get_msg_decoration(f"heading/{level}")
        with (
            self._with_indent(f"msg/decoration:heading/{level}", decoration),
            self._with_color(f"msg/text:heading/{level}"),
        ):
            self._format_Text(node)

        self._line(self._indent)
        self._is_first_line = True

    def _format_Paragraph(self, node: Paragraph, /):
        with self._with_color("msg/text:paragraph"):
            self._format_Text(node)

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
        with (
            self._with_indent("msg/decoration:list", decoration),
            self._with_color("msg/text:list"),
        ):
            self._format_Container(node)

    def _format_Quote(self, node: Quote, /):
        decoration = self.ctx.get_msg_decoration("quote")
        with (
            self._with_indent(
                "msg/decoration:quote", decoration, continue_with_spaces=False
            ),
            self._with_color("msg/text:quote"),
        ):
            self._format_Container(node)

    def _format_Admonition(self, node: Admonition, /):
        if node.title:
            decoration = self.ctx.get_msg_decoration("admonition/title")
            with self._with_indent(
                f"msg/decoration:admonition/title/{node.type}",
                decoration,
                continue_with_spaces=False,
            ):
                title = self._format_inline(
                    node.title,
                    default_color=self.ctx.get_color(
                        f"msg/text:admonition/title/{node.type}"
                    ),
                )
                for line in title.wrap(
                    self.width,
                    indent=self._indent,
                    continuation_indent=self._continuation_indent,
                    preserve_newlines=False,
                    break_long_nowrap_words=True,
                ):
                    self._line(line)
        if node.items:
            decoration = self.ctx.get_msg_decoration("admonition/body")
            with (
                self._with_indent(
                    f"msg/decoration:admonition/body/{node.type}",
                    decoration,
                    continue_with_spaces=False,
                ),
                self._with_color(f"msg/text:admonition/body/{node.type}"),
            ):
                self._format_Container(node)

    def _format_Footnote(self, node: Footnote, /):
        if yuio.string.line_width(node.marker) > 2:
            indent = "    "
            self._line(self._indent + self.ctx.get_color("role/footnote") + node.marker)
        else:
            indent = f"{node.marker!s:4}"
        with (
            self._with_indent("msg/decoration:footnote", indent),
            self._with_color("msg/text:footnote"),
        ):
            self._format_Container(node)

    def _format_FootnoteContainer(self, node: FootnoteContainer, /):
        if not node.items:
            return

        prev_separate_paragraphs = self._separate_paragraphs
        self._separate_paragraphs = False
        try:
            self._format_ThematicBreak(ThematicBreak())
            self._format_Container(node)
        finally:
            self._separate_paragraphs = prev_separate_paragraphs

    def _format_Code(self, node: Code, /):
        if not node.lines:
            return

        highlighter, syntax_name = yuio.hl.get_highlighter(node.syntax)
        s = highlighter.highlight(
            "\n".join(node.lines),
            theme=self.ctx.theme,
            syntax=syntax_name,
            default_color=self._text_color(),
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

    def _format_inline(
        self,
        items: _t.Sequence[str | TextRegion],
        /,
        *,
        default_color: yuio.color.Color,
    ):
        s = yuio.string.ColorizedString()

        for item in items:
            if isinstance(item, str):
                s.append_color(default_color)
                s.append_str(item)
            else:
                s += getattr(
                    self, f"_format_inline_{item.__class__.__name__.lstrip('_')}"
                )(item, default_color=default_color)

        return s

    def _format_inline_TextRegion(
        self, node: TextRegion, /, *, default_color: yuio.color.Color
    ):
        return self._format_inline(node.content, default_color=default_color)

    def _format_inline_HighlightedRegion(
        self, node: HighlightedRegion, /, *, default_color: yuio.color.Color
    ):
        if node.color:
            default_color |= self.ctx.get_color(node.color)
        return self._format_inline(node.content, default_color=default_color)

    def _format_inline_NoWrapRegion(
        self, node: NoWrapRegion, /, *, default_color: yuio.color.Color
    ):
        s = yuio.string.ColorizedString()
        s.start_no_wrap()
        s += self._format_inline(node.content, default_color=default_color)
        s.end_no_wrap()
        return s

    def _format_inline_LinkRegion(
        self, node: LinkRegion, /, *, default_color: yuio.color.Color
    ):
        s = yuio.string.ColorizedString()
        if node.url:
            s.start_link(node.url)
        s += self._format_inline(node.content, default_color=default_color)
        if node.url:
            if not self.ctx.term.supports_colors:
                s.append_color(default_color)
                s.append_str(f" [{node.url}]")
            s.end_link()
        return s

    def _format_inline_DecorationRegion(
        self, node: DecorationRegion, /, *, default_color: yuio.color.Color
    ):
        return yuio.string.ColorizedString(
            default_color, self.ctx.get_msg_decoration(node.decoration_path)
        )


TAst = _t.TypeVar("TAst", bound="AstBase")


@dataclass(kw_only=True, slots=True)
class AstBase:
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
    Text region with special formatting.

    """

    content: list[str | TextRegion]
    """
    Region contents.

    """

    def __init__(self, *args: str | TextRegion):
        self.content = list(args)


@dataclass(kw_only=True, slots=True)
class HighlightedRegion(TextRegion):
    """
    Highlighted text region.

    """

    color: str
    """
    Color path to be applied to the region's contents.

    """

    def __init__(self, *args: str | TextRegion, color: str):
        self.content = list(args)
        self.color = color


@dataclass(kw_only=True, slots=True)
class DecorationRegion(TextRegion):
    """
    Inserts a single decoration from current theme.

    """

    decoration_path: str
    """
    Decoration path.

    """

    def __init__(self, decoration_path: str):
        self.content = []
        self.decoration_path = decoration_path


@dataclass(kw_only=True, slots=True)
class NoWrapRegion(TextRegion):
    """
    Text region with disabled line wrapping.

    """

    def __init__(self, *args: str | TextRegion):
        self.content = list(args)


@dataclass(kw_only=True, slots=True)
class LinkRegion(TextRegion):
    """
    Text region with a link.

    """

    url: str
    """
    Makes this region into a hyperlink.

    """

    def __init__(self, *args: str | TextRegion, url: str):
        self.content = list(args)
        self.url = url


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

    title: list[str | TextRegion] = dataclasses.field(repr=False)
    """
    Main title.

    """

    type: str
    """
    Admonition type.

    """

    def dump(self, indent: str = "") -> str:
        s = f"{indent}({self._dump_params()}\n{indent}  (title"
        indent += "  "
        for line in self.title:
            s += "\n  " + indent
            s += repr(line)
        s += ")"
        for items in self.items:
            s += "\n"
            s += items.dump(indent)
        s += ")"
        return s


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

    syntax: str
    """
    Syntax indicator as parsed form the original document.

    """

    def dump(self, indent: str = "") -> str:
        s = f"{indent}({self._dump_params()}"
        indent += "  "
        for line in self.lines:
            s += "\n" + indent
            s += repr(line)
        s += ")"
        return s


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


@dataclass(kw_only=True, slots=True)
class Cut(AstBase):
    """
    Stops rendering of the container.

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


_DirectiveHandler: _t.TypeAlias = _t.Callable[
    [str, str, _t.Callable[[], list[str]], _t.Callable[[], list[AstBase]]],
    _t.Sequence[AstBase],
]

_KNOWN_DIRECTIVES: dict[str, _DirectiveHandler] = {}


def _process_directive(
    name: str,
    arg: str,
    get_lines: _t.Callable[[], list[str]],
    get_parsed: _t.Callable[[], list[AstBase]],
) -> _t.Sequence[AstBase]:
    if name in _KNOWN_DIRECTIVES:
        return _KNOWN_DIRECTIVES[name](name, arg, get_lines, get_parsed)
    else:
        return [
            Admonition(
                items=get_parsed(), title=[f".. {name}:: {arg}"], type="unknown-dir"
            )
        ]


def _directive(names: list[str]) -> _t.Callable[[_DirectiveHandler], _DirectiveHandler]:
    def _registrar(fn):
        for name in names:
            _KNOWN_DIRECTIVES[name] = fn
        return fn

    return _registrar


@_directive(["code-block", "sourcecode", "code"])
def _process_code_directive(name, arg, get_lines, get_parsed):
    return [Code(lines=get_lines(), syntax=arg)]


@_directive(
    [
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
    ]
)
def _process_admonition_directive(name, arg, get_lines, get_parsed):
    return [Admonition(title=[name.title()], items=get_parsed(), type=name)]


@_directive(["admonition"])
def _process_custom_admonition_directive(name, arg, get_lines, get_parsed):
    return [Admonition(title=[arg], items=get_parsed(), type=name)]


@_directive(
    [
        "versionadded",
        "versionchanged",
        "deprecated",
    ]
)
def _process_version_directive(name, arg, get_lines, get_parsed):
    return [
        Admonition(
            title=[
                name.removeprefix("version").title(),
                " in version ",
                arg,
            ],
            items=get_parsed(),
            type=name,
        )
    ]


@_directive(["if-not-sphinx", "if-opt-doc"])
def _process_id_directive(name, arg, get_lines, get_parsed):
    return get_parsed()


@_directive(["if-sphinx", "if-not-opt-doc"])
def _process_nop_directive(name, arg, get_lines, get_parsed):
    return []


@_directive(["cut-if-not-sphinx"])
def _process_cut_directive(name, arg, get_lines, get_parsed):
    return [Cut()]


_CROSSREF_RE = re.compile(
    r"""
        ^
        (?P<title>(?:[^\\]|\\.)*?)
        (?:(?<!^)\s*<(?P<target>.*)>)?
        $
    """,
    re.VERBOSE,
)


_RoleHandler: _t.TypeAlias = _t.Callable[[str, str], TextRegion]

_KNOWN_ROLES: dict[str, _RoleHandler] = {}


def _role(names: list[str]) -> _t.Callable[[_RoleHandler], _RoleHandler]:
    def _registrar(fn):
        for name in names:
            _KNOWN_ROLES[name] = fn
        return fn

    return _registrar


def _process_role(text: str, role: str) -> TextRegion:
    if not role:
        role = "default"

    if role in _KNOWN_ROLES:
        return _KNOWN_ROLES[role](role, text)
    else:
        # Assume generic reference role by default.
        role = role.replace(":", "/")
        return NoWrapRegion(
            HighlightedRegion(_process_ref(text), color=f"role/unknown/{role}")
        )


def _process_ref(
    text: str, parse_path=None, join_path=None, refspecific_marker: str = "."
):
    if parse_path is None:
        parse_path = lambda s: s.split(".")
    if join_path is None:
        join_path = lambda p: ".".join(p)

    if text.startswith("!"):
        text = text[1:]

    match = _CROSSREF_RE.match(text)
    if not match:  # pragma: no cover
        return text

    title = match.group("title")
    target = match.group("target")

    # Sphinx unescapes role contents.
    title = re.sub(r"\\(?:\s|(.))", r"\1", title)

    if not target:
        # Implicit title.def _unescape(text: str) -> str:
        if title.startswith("~"):
            title = parse_path(title[1:])[-1]
        else:
            title = join_path(parse_path(title.removeprefix(refspecific_marker)))
    else:
        title = title.rstrip()

    return title


@_role(
    [
        "flag",
        "code",
        "literal",
        "math",
        "abbr",
        "command",
        "dfn",
        "mailheader",
        "makevar",
        "mimetype",
        "newsgroup",
        "program",
        "regexp",
        "cve",
        "cwe",
        "pep",
        "rfc",
        "manpage",
        "kbd",
    ]
)
def _process_simple_role(name: str, text: str):
    return NoWrapRegion(HighlightedRegion(text, color=f"role/{name}"))


@_role(
    [
        "any",
        "doc",
        "download",
        "envvar",
        "keyword",
        "numref",
        "option",
        "cmdoption",
        "ref",
        "term",
        "token",
        "eq",
    ]
)
def _process_ref_role(name: str, text: str):
    return NoWrapRegion(HighlightedRegion(_process_ref(text), color=f"role/{name}"))


@_role(
    [
        "cli:cfg",
        "cli:field",
        "cli:obj",
        "cli:env",
        "cli:any",
    ]
)
def _process_cli_cfg_role(name: str, text: str):
    name = name.replace(":", "/")
    return NoWrapRegion(
        HighlightedRegion(
            _process_ref(text, _parse_cfg_path, ".".join), color=f"role/{name}"
        )
    )


@_role(
    [
        "cli:cmd",
        "cli:flag",
        "cli:arg",
        "cli:opt",
        "cli:cli",
    ]
)
def _process_cli_cmd_role(name: str, text: str):
    name = name.replace(":", "/")
    return NoWrapRegion(
        HighlightedRegion(
            _process_ref(text, _parse_cmd_path, " ".join, refspecific_marker=". "),
            color=f"role/{name}",
        )
    )


@_role(["guilabel"])
def _process_gui_label_role(name: str, text: str):
    spans = re.split(r"(?<!&)&(?![&\s])", text)

    res = NoWrapRegion()
    if start := spans.pop(0):
        res.content.append(HighlightedRegion(start, color=f"role/{name}"))

    for span in spans:
        span = span.replace("&&", "&")
        if span[0]:
            res.content.append(
                HighlightedRegion(span[0], color=f"role/{name}/accelerator")
            )
        if span[1:]:
            res.content.append(HighlightedRegion(span[1:], color=f"role/{name}"))

    return res


@_role(["menuselection"])
def _process_menuselection_role(name: str, text: str):
    res = NoWrapRegion()

    for region in _process_gui_label_role(name, text).content:
        if not isinstance(region, HighlightedRegion):  # pragma: no cover
            res.content.append(region)
            continue
        if len(region.content) != 1:  # pragma: no cover
            res.content.append(region)
            continue
        if not isinstance(region.content[0], str):  # pragma: no cover
            res.content.append(region)
            continue
        if "-->" not in region.content[0]:
            res.content.append(region)
            continue

        for part in re.split(r"\s*(-->)\s*", region.content[0]):
            if part == "-->":
                res.content.append(
                    HighlightedRegion(
                        DecorationRegion("menuselection_separator"),
                        color=f"role/{name}/separator",
                    )
                )
            elif part:
                res.content.append(HighlightedRegion(part, color=region.color))
    return res


@_role(["file", "samp"])
def _process_samp_role(name: str, text: str):
    res = NoWrapRegion()

    stack = [""]
    for part in re.split(r"(\\\\|\\{|\\}|{|})", text):
        if part == "\\\\":  # escaped backslash
            stack[-1] += "\\"
        elif part == "{":
            if len(stack) >= 2 and stack[-2] == "{":  # nested
                stack[-1] += "{"
            else:
                # start emphasis
                stack.extend(("{", ""))
        elif part == "}":
            if len(stack) == 3 and stack[1] == "{" and len(stack[2]) > 0:
                # emphasized word found
                if stack[0]:
                    res.content.append(
                        HighlightedRegion(stack[0], color=f"role/{name}")
                    )
                res.content.append(
                    HighlightedRegion(f"{{{stack[2]}}}", color=f"role/{name}/variable")
                )
                stack = [""]
            else:
                # emphasized word not found; the rparen is not a special symbol
                stack.append("}")
                stack = ["".join(stack)]
        elif part == "\\{":  # escaped left-brace
            stack[-1] += "{"
        elif part == "\\}":  # escaped right-brace
            stack[-1] += "}"
        else:  # others (containing escaped braces)
            stack[-1] += part

    if "".join(stack):
        # remaining is treated as Text
        res.content.append(HighlightedRegion("".join(stack), color=f"role/{name}"))

    return res


def _process_link(text: str):
    match = _CROSSREF_RE.match(text)
    if not match:
        return None, text
    return match.group("target"), match.group("title")


def _read_parenthesized_until(s: str, end_cond: _t.Callable[[str], bool]):
    paren_stack = []
    i = 0
    res_start = 0
    res: list[str] = []

    def push_res():
        nonlocal res_start
        res.append(s[res_start:i])
        res_start = i

    while i < len(s):
        match s[i]:
            case c if not paren_stack and end_cond(c):
                push_res()
                return "".join(res), s[i:]
            case c if paren_stack and c == paren_stack[-1]:
                paren_stack.pop()
                i += 1
            case "\\":
                push_res()
                i += 2
                res_start += 1
            case "(":
                paren_stack.append(")")
                i += 1
            case "[":
                paren_stack.append("]")
                i += 1
            case "{":
                paren_stack.append("}")
                i += 1
            case "<":
                paren_stack.append(">")
                i += 1
            case "'" | '"':
                end_char = s[i]
                i += 1
                while i < len(s):
                    match s[i]:
                        case "\\":
                            i += 2
                        case c if c == end_char:
                            i += 1
                            break
                        case _:
                            i += 1
            case _:
                i += 1

    push_res()
    return "".join(res), ""


def _parse_cfg_path(path: str) -> tuple[str, ...]:
    path = re.sub(r"\s+", " ", path.strip())
    return tuple(path.split("."))


def _parse_cmd_path(path: str) -> tuple[str, ...]:
    path = re.sub(r"\s+", " ", path.strip())
    res: list[str] = []
    while path:
        part, path = _read_parenthesized_until(path, lambda c: c.isspace())
        path = path.lstrip()
        res.append(part)
    return tuple(res)


def _cmd2cfg(cmd: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(map(_cmd2cfg_part, cmd))


def _cmd2cfg_part(cmd: str) -> str:
    cmd = cmd.lstrip("-")
    cmd = re.sub(r"[\s-]+", r"_", cmd)
    cmd = re.sub(r"[^\w]", "", cmd)
    return cmd  # noqa: RET504


def _clean_tree(node: AstBase):
    if isinstance(node, List):
        if not node.items:
            # Empty list is left as-is.
            return node

        new_nodes = []
        for subnode in node.items:
            # List was cut at this point.
            if len(subnode.items) == 1 and isinstance(subnode.items[0], Cut):
                break
            if (new_subnode := _clean_tree(subnode)) is not None:
                new_nodes.append(new_subnode)

        if new_nodes:
            node.items = new_nodes
        else:
            # List became empty because of our cutting, don't render it.
            return None
    elif isinstance(node, Container):
        if not node.items:
            # Empty container is left as-is.
            return node

        new_nodes = []
        for subnode in node.items:
            if isinstance(subnode, Cut):
                break
            if (new_subnode := _clean_tree(subnode)) is not None:
                new_nodes.append(new_subnode)

        if new_nodes:
            node.items = new_nodes
        else:
            # Container became empty because of our cutting, don't render it.
            return None
    return node
