# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Yuio's primary format for higher-level io is Markdown (well, a reasonably rich subset
of it).


Formatting markdown
-------------------

.. autoclass:: MdFormatter
   :members:


Markdown AST
------------

.. warning::

   This is experimental API which can change within a minor release.

.. autofunction:: parse

.. autoclass:: AstBase
   :members:

.. autoclass:: Text
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

.. autoclass:: Code
   :members:

.. autoclass:: ListItem
   :members:

.. autoclass:: List
   :members:


"""

from __future__ import annotations

import abc
import contextlib
import dataclasses
import math
import re
from dataclasses import dataclass

import yuio.color
import yuio.hl
import yuio.string
from yuio.util import dedent as _dedent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "AstBase",
    "AstBase",
    "Code",
    "Code",
    "Container",
    "Container",
    "Document",
    "Document",
    "Heading",
    "Heading",
    "List",
    "List",
    "ListItem",
    "ListItem",
    "MdFormatter",
    "Paragraph",
    "Paragraph",
    "Quote",
    "Quote",
    "Raw",
    "Text",
    "Text",
    "ThematicBreak",
    "ThematicBreak",
    "parse",
]

T = _t.TypeVar("T")
TAst = _t.TypeVar("TAst", bound="AstBase")


@_t.final
class MdFormatter:
    """
    A simple markdown formatter suitable for displaying rich text in the terminal.

    :param ctx:
        a :class:`~yuio.string.ReprContext` that's used to colorize or wrap
        rendered markdown.
    :param allow_headings:
        if set to :data:`False`, headings are rendered as paragraphs.

    All CommonMark block markup except tables is supported:

    - headings:

      .. code-block:: markdown

         # Heading 1
         ## Heading 2

      Yuio has only two levels of headings. Headings past level two will look the same
      as level two headings (you can adjust theme to change this).

      If `allow_headings` is set to :data:`False`, headings look like paragraphs.

    - lists, numbered lists, quotes:

      .. code-block:: markdown

         -  List item 1,
         -  list item 2.

         1. Numbered list item 1,
         1. numbered list item 2.

         > Quoted text.

    - fenced code blocks with minimal syntax highlighting
      (see :class:`yuio.hl.SyntaxHighlighter`):

      .. code-block:: markdown

         ```python
         for i in range(5, 8):
             print(f"Hello, world! This is {{i}}th day past the apocalypse.")
         ```

    Inline markdown only handles inline code blocks:

    .. code-block:: markdown

       This is `code`. It will be rendered as code.
       Other inline styles, such as _italic_, are not supported!

    However, color tags are supported, so you can highlight text as follows:

    .. code-block:: markdown

       This is <c b>bold text</c>. It will be rendered bold.

    """

    def __init__(
        self,
        ctx: yuio.string.ReprContext,
        *,
        allow_headings: bool = True,
    ):
        self._ctx = ctx
        self.allow_headings: bool = allow_headings

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

    def format(
        self, md: str, *, dedent: bool = True
    ) -> list[yuio.string.ColorizedString]:
        """
        Format a markdown document.

        :param md:
            markdown to format. Common indentation will be removed from this string,
            making it suitable to use with triple quote literals.
        :param dedent:
            remove lading indent from markdown.
        :returns:
            rendered markdown as a list of individual lines without newline
            characters at the end.

        """

        return self.format_node(self.parse(md, dedent=dedent))

    def parse(self, md: str, /, *, dedent: bool = True) -> Document:
        """
        Parse a markdown document and return an AST node.

        .. warning::

           This is experimental API which can change within a minor release.

        :param md:
            markdown to parse. Common indentation will be removed from this string,
            making it suitable to use with triple quote literals.
        :param dedent:
            remove lading indent from markdown.
        :returns:
            parsed AST node.

        """

        if dedent:
            md = _dedent(md)

        return _MdParser(self.allow_headings).parse(md)

    def format_node(self, node: AstBase, /) -> list[yuio.string.ColorizedString]:
        """
        Format a parsed markdown document.

        .. warning::

           This is an experimental API which can change within a minor release.

        :param md:
            AST node to format.
        :returns:
            rendered markdown as a list of individual lines without newline
            characters at the end.

        """

        self._is_first_line = True
        self._separate_paragraphs = True
        self._out = []
        self._indent = yuio.string.ColorizedString()
        self._continuation_indent = yuio.string.ColorizedString()

        self._format(node)

        return self._out

    def colorize(
        self,
        text: str,
        /,
        *,
        default_color: yuio.color.Color | str = yuio.color.Color.NONE,
    ):
        """
        Parse and colorize contents of a paragraph.

        This is a shortcut for calling :func:`colorize` with this formatter's theme.

        :param line:
            text to colorize.
        :param default_color:
            color or color tag to apply to the entire text.
        :returns:
            a colorized string.

        """

        return yuio.string.colorize(text, default_color=default_color, ctx=self.ctx)

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

        self._indent = self._indent + indent
        self._continuation_indent = self._continuation_indent + continuation_indent

        try:
            yield
        finally:
            self._indent = old_indent
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

    def _format_Text(self, node: Text, /, *, default_color: yuio.color.Color):
        s = self.colorize(
            "\n".join(node.lines).strip(),
            default_color=default_color,
        )

        for line in s.wrap(
            self.width,
            indent=self._indent,
            continuation_indent=self._continuation_indent,
            preserve_newlines=False,
            break_long_nowrap_words=True,
        ):
            self._line(line)

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
        self._line(self._indent + decoration)

    def _format_Heading(self, node: Heading, /):
        if not self._is_first_line:
            self._line(self._indent)

        decoration = self.ctx.get_msg_decoration(f"heading/{node.level}")
        with self._with_indent(f"msg/decoration:heading/{node.level}", decoration):
            self._format_Text(
                node,
                default_color=self.ctx.get_color(f"msg/text:heading/{node.level}"),
            )

        self._line(self._indent)
        self._is_first_line = True

    def _format_Paragraph(self, node: Paragraph, /):
        self._format_Text(node, default_color=self.ctx.get_color("msg/text:paragraph"))

    def _format_ListItem(self, node: ListItem, /, *, min_width: int = 0):
        decoration = self.ctx.get_msg_decoration("list")
        if node.number is not None:
            decoration = f"{node.number:>{min_width}}." + " " * (
                yuio.string.line_width(decoration) - min_width - 1
            )
        with self._with_indent("msg/decoration:list", decoration):
            self._format_Container(node)

    def _format_Quote(self, node: Quote, /):
        decoration = self.ctx.get_msg_decoration("quote")
        with self._with_indent(
            "msg/decoration:quote", decoration, continue_with_spaces=False
        ):
            self._format_Container(node)

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
        max_number = max(item.number or 0 for item in node.items)
        min_width = math.ceil(math.log10(max_number)) if max_number > 0 else 1
        self._is_first_line = True
        for item in node.items:
            if not self._is_first_line:
                self._line(self._indent)
            self._format_ListItem(item, min_width=min_width)


@dataclass(kw_only=True, slots=True)
class AstBase(abc.ABC):
    """
    Base class for all AST nodes that represent parsed markdown document.

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

    lines: list[str] = dataclasses.field(repr=False)
    """
    Text lines as parsed from the original document.

    """

    def dump(self, indent: str = "") -> str:
        s = f"{indent}({self._dump_params()}"
        indent += "  "
        for line in self.lines:
            s += "\n" + indent
            s += repr(line)
        s += ")"
        return s


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
    Root node that contains the entire markdown document.

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
class Code(Text):
    """
    Represents a highlighted block of code.

    """

    syntax: str
    """
    Syntax indicator as parsed form the original document.

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


_HEADING_RE = re.compile(
    r"""
    ^
    \s{0,3}                     # - Initial indent.
    (?P<marker>\#{1,6})         # - Heading marker.
    (?P<text>\s.*?)?            # - Heading text. Unless empty, text must be separated
                                #   from the heading marker by a space.
    (?:(?<=\s)\#+)?             # - Optional closing hashes. Must be separated from
                                #   the previous content by a space. We use lookbehind
                                #   here, because if the text is empty, the space
                                #   between heading marker and closing hashes will be
                                #   matched by the `text` group.
    \s*                         # - Closing spaces.
    $
    """,
    re.VERBOSE,
)
_SETEXT_HEADING_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial indent.
    (?P<level>-|=)              # - Heading underline.
    \2*                         # - More heading underline.
    \s*                         # - Closing spaces.
    $
    """,
    re.VERBOSE,
)
_LIST_RE = re.compile(
    r"""
    ^
    (?P<marker>
      \s{0,3}                   # - Initial indent.
      (?P<type>[-*+])           # - List marker.
      (?:
          \s(?:\s{0,3}(?=\S))?  # - One mandatory and up to three optional spaces;
                                #   When there are more than three optional spaces,
                                #   we treat then as a list marker followed
                                #   by a single space, followed by a code block.
        | $))                   # - For cases when a list starts with an empty line.
    (?P<text>.*)                # - Text of the first line in the list.
    $
    """,
    re.VERBOSE,
)
_NUMBERED_LIST_RE = re.compile(
    r"""
    ^
    (?P<marker>
      \s{0,3}                   # - Initial indent.
      (?P<number>\d{1,9})       # - Number.
      (?P<type>[.:)])           # - Numbered list marker.
      (?:
          \s(?:\s{0,3}(?=\S))?  # - One mandatory and up to three optional spaces;
                                #   When there are more than three optional spaces,
                                #   we treat then as a list marker followed
                                #   by a single space, followed by a code block.
        | $))                   # - For cases when a list starts with an empty line.
    (?P<text>.*)                # - Text of the first line in the list.
    $
    """,
    re.VERBOSE,
)
_CODE_BACKTICK_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial indent.
    (?P<fence>```+)             # - Backtick fence.
    (?P<syntax>[^`]*)           # - Syntax, can't contain backtick.
    $
    """,
    re.VERBOSE,
)
_CODE_TILDE_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial indent.
    (?P<fence>~~~+)             # - Backtick fence.
    (?P<syntax>.*)              # - Syntax, can be anything.
    $
    """,
    re.VERBOSE,
)
_CODE_FENCE_END_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial indent.
    (?P<fence>~~~+|```+)        # - Fence.
    \s*                         # - Closing spaces.
    $
    """,
    re.VERBOSE,
)
_CODE_RE = re.compile(
    r"""
    ^
    \s{4}                       # - Initial code indent.
    (?P<text>.*)                # - First code line.
    $
    """,
    re.VERBOSE,
)
_QUOTE_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial quote indent.
    >                           # - Quote marker.
    \s?                         # - Optional space after the marker.
    (?P<text>.*)                # - Text of the first line in the quote.
    $
    """,
    re.VERBOSE,
)
_THEMATIC_BREAK_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial quote indent.
    ([-*_])\s*(\2\s*){2,}       # - At least three break characters separated by spaces.
    $
    """,
    re.VERBOSE,
)
_LINE_FEED_RE = re.compile(r"\r\n|\r|\n")


class _MdParser:
    @dataclass(kw_only=True, slots=True)
    class Default:
        pass

    @dataclass(kw_only=True, slots=True)
    class List:
        type: str
        marker_len: int
        list: List
        parser: _MdParser
        number: int | None = None

    @dataclass(kw_only=True, slots=True)
    class Quote:
        parser: _MdParser

    @dataclass(kw_only=True, slots=True)
    class Code:
        lines: list[str]

    @dataclass(kw_only=True, slots=True)
    class FencedCode:
        indent: int
        fence_symbol: str
        fence_length: int
        syntax: str
        lines: list[str]

    @dataclass(kw_only=True, slots=True)
    class Paragraph:
        lines: list[str]

    State: _t.TypeAlias = Default | List | Quote | Code | FencedCode | Paragraph

    def __init__(self, allow_headings: bool = True):
        self._allow_headings = allow_headings
        self._nodes: list[AstBase] = []
        self._state: _MdParser.State = self.Default()

    def _parser(self) -> _MdParser:
        return _MdParser(self._allow_headings)

    @staticmethod
    def _is_blank(s: str) -> bool:
        return not s or s.isspace()

    def parse(self, s: str) -> Document:
        s = s.expandtabs(tabsize=4)
        for line in _LINE_FEED_RE.split(s):
            self._handle_line(line)
        return Document(items=self._finalize())

    def _handle_line(self, line: str):
        getattr(self, f"_handle_line_{self._state.__class__.__name__}")(line)

    def _handle_lazy_line(self, line: str) -> bool:
        return getattr(self, f"_handle_lazy_line_{self._state.__class__.__name__}")(
            line
        )

    def _flush(self):
        getattr(self, f"_flush_{self._state.__class__.__name__}")()

    def _handle_line_List(self, line: str):
        assert type(self._state) is self.List
        if not line or line[: self._state.marker_len].isspace():
            self._state.parser._handle_line(line[self._state.marker_len :])
        elif (
            (match := _LIST_RE.match(line)) or (match := _NUMBERED_LIST_RE.match(line))
        ) and match.group("type") == self._state.type:
            item = ListItem(
                items=self._state.parser._finalize(),
                number=self._state.number,
            )
            self._state.list.items.append(item)
            self._state.marker_len = len(match.group("marker"))
            self._state.parser._handle_line(match.group("text"))
            if self._state.number is not None:
                self._state.number += 1
        elif not self._state.parser._handle_lazy_line(line):
            self._flush_List()
            self._handle_line_Default(line)

    def _handle_lazy_line_List(self, line: str) -> bool:
        assert type(self._state) is self.List
        if self._state.parser._handle_lazy_line(line):
            return True
        return False

    def _flush_List(self):
        assert type(self._state) is self.List
        item = ListItem(
            items=self._state.parser._finalize(),
            number=self._state.number,
        )
        self._state.list.items.append(item)
        self._nodes.append(self._state.list)
        self._state = self.Default()

    def _handle_line_Quote(self, line: str):
        assert type(self._state) is self.Quote
        if match := _QUOTE_RE.match(line):
            self._state.parser._handle_line(match.group("text"))
        elif self._is_blank(line) or not self._state.parser._handle_lazy_line(line):
            self._flush_Quote()
            self._handle_line_Default(line)

    def _handle_lazy_line_Quote(self, line: str) -> bool:
        assert type(self._state) is self.Quote
        if self._state.parser._handle_lazy_line(line):
            return True
        else:
            return False

    def _flush_Quote(self):
        assert type(self._state) is self.Quote
        self._nodes.append(Quote(items=self._state.parser._finalize()))
        self._state = self.Default()

    def _handle_line_Code(self, line: str):
        assert type(self._state) is self.Code
        if self._is_blank(line) or line.startswith("    "):
            self._state.lines.append(line[4:])
        else:
            self._flush_Code()
            self._handle_line_Default(line)

    def _handle_lazy_line_Code(self, line: str) -> bool:
        assert type(self._state) is self.Code
        return False  # No lazy continuations for code!

    def _flush_Code(self):
        assert type(self._state) is self.Code
        while self._state.lines and self._is_blank(self._state.lines[-1]):
            self._state.lines.pop()
        self._nodes.append(
            Code(
                lines=self._state.lines,
                syntax="",
            )
        )
        self._state = self.Default()

    def _handle_line_FencedCode(self, line: str):
        assert type(self._state) is self.FencedCode
        if (
            (match := _CODE_FENCE_END_RE.match(line))
            and match.group("fence")[0] == self._state.fence_symbol
            and len(match.group("fence")) == self._state.fence_length
        ):
            self._flush_FencedCode()
        else:
            if self._state.indent == 0:
                pass
            elif line[: self._state.indent].isspace():
                line = line[self._state.indent :]
            else:
                line = line.lstrip()
            self._state.lines.append(line)

    def _handle_lazy_line_FencedCode(self, line: str) -> bool:
        assert type(self._state) is self.FencedCode
        return False

    def _flush_FencedCode(self):
        assert type(self._state) is self.FencedCode
        self._nodes.append(
            Code(
                lines=self._state.lines,
                syntax=self._state.syntax,
            )
        )
        self._state = self.Default()

    def _handle_line_Paragraph(self, line: str):
        assert type(self._state) is self.Paragraph
        if match := _SETEXT_HEADING_RE.match(line):
            level = 1 if match.group("level") == "=" else 2
            self._nodes.append(
                Heading(
                    lines=self._state.lines,
                    level=level,
                )
            )
            self._state = self.Default()
        elif (
            self._is_blank(line)
            or _THEMATIC_BREAK_RE.match(line)
            or (self._allow_headings and _HEADING_RE.match(line))
            or _CODE_BACKTICK_RE.match(line)
            or _CODE_TILDE_RE.match(line)
            or _LIST_RE.match(line)
            or _NUMBERED_LIST_RE.match(line)
            or _QUOTE_RE.match(line)
        ):
            self._flush_Paragraph()
            self._handle_line_Default(line)
        else:
            self._state.lines.append(line)

    def _handle_lazy_line_Paragraph(self, line: str) -> bool:
        assert type(self._state) is self.Paragraph
        if (
            self._is_blank(line)
            or _THEMATIC_BREAK_RE.match(line)
            or (self._allow_headings and _HEADING_RE.match(line))
            or _CODE_BACKTICK_RE.match(line)
            or _CODE_TILDE_RE.match(line)
            or _LIST_RE.match(line)
            or _NUMBERED_LIST_RE.match(line)
            or _QUOTE_RE.match(line)
        ):
            self._flush_Paragraph()
            return False
        else:
            self._state.lines.append(line)
            return True

    def _flush_Paragraph(self):
        assert type(self._state) is self.Paragraph
        self._nodes.append(Paragraph(lines=self._state.lines))
        self._state = self.Default()

    def _handle_line_Default(self, line: str):
        assert type(self._state) is self.Default
        if self._is_blank(line):
            pass  # do nothing
        elif _THEMATIC_BREAK_RE.match(line):
            self._nodes.append(ThematicBreak())
        elif self._allow_headings and (match := _HEADING_RE.match(line)):
            level = len(match.group("marker"))
            self._nodes.append(
                Heading(
                    lines=[match.group("text").strip()],
                    level=level,
                )
            )
        elif (match := _CODE_BACKTICK_RE.match(line)) or (
            match := _CODE_TILDE_RE.match(line)
        ):
            indent = len(match.group("indent"))
            syntax = match.group("syntax").strip()
            fence_symbol = match.group("fence")[0]
            fence_length = len(match.group("fence"))
            self._state = self.FencedCode(
                indent=indent,
                fence_symbol=fence_symbol,
                fence_length=fence_length,
                syntax=syntax,
                lines=[],
            )
        elif match := _CODE_RE.match(line):
            self._state = self.Code(lines=[match.group("text")])
        elif (match := _LIST_RE.match(line)) or (
            match := _NUMBERED_LIST_RE.match(line)
        ):
            indent = len(match.group("marker"))
            list_type = match.group("type")
            number_str = match.groupdict().get("number", None)
            number = int(number_str) if number_str else None
            self._state = self.List(
                type=list_type,
                marker_len=indent,
                list=List(items=[]),
                parser=self._parser(),
                number=number,
            )
            self._state.parser._handle_line(match.group("text"))
        elif match := _QUOTE_RE.match(line):
            self._state = self.Quote(parser=self._parser())
            self._state.parser._handle_line(match.group("text"))
        else:
            self._state = self.Paragraph(lines=[line])

    def _handle_lazy_line_Default(self, line: str) -> bool:
        assert type(self._state) is self.Default
        return False

    def _flush_Default(self):
        assert type(self._state) is self.Default

    def _finalize(self) -> list[AstBase]:
        self._flush()
        result = self._nodes
        self._nodes = []
        return result


def parse(md: str, /, *, dedent: bool = True, allow_headings: bool = True) -> Document:
    """
    Parse a markdown document and return an AST node.

    :param md:
        markdown to parse. Common indentation will be removed from this string,
        making it suitable to use with triple quote literals.
    :param dedent:
        remove lading indent from markdown.
    :param allow_headings:
        if set to :data:`False`, headings are rendered as paragraphs.
    :returns:
        parsed AST node.

    """

    if dedent:
        md = _dedent(md)

    return _MdParser(allow_headings).parse(md)
