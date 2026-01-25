# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Parser for Markdown/MyST.

Yuio supports all CommonMark features except tables. It also supports directives
and interpreted text via MyST_ syntax.

**Supported block markup:**

-   headings,
-   numbered and bullet lists,
-   code blocks using backticks and indentation,
-   MyST-style code blocks using colons,
-   code blocks containing MyST directives,
-   quotes,
-   hyperlink targets,
-   thematic breaks.

**Supported roles:**

-   code:
    ``code-block``,
    ``sourcecode``,
    ``code``;
-   admonitions:
    ``attention``,
    ``caution``,
    ``danger``,
    ``error``,
    ``hint``,
    ``important``,
    ``note``,
    ``seealso``,
    ``tip``,
    ``warning``;
-   versioning:
    ``versionadded``,
    ``versionchanged``,
    ``deprecated``;
-   any other directive is rendered as un-highlighted code.

**Supported inline syntax:**

-   emphasis (``*em*``),
-   strong emphasis (``**strong*``),
-   inline code in backticks (```code```),
-   inline math (``$math$``),
-   MyST-style interpreted text (``{role}`content```),
-   hyperlinks (``[text](link)``, ``[text][anchor]``, ``[anchor]``)
    in terminals that can render them,
-   backslash-escaping.

**Supported inline roles:**

-   ``flag`` for CLI flags,
-   any other role is interpreted as documentation reference with explicit titles
    (``{py:class}`title <mod.Class>```) and shortening paths via tilde
    (``{py:class}`~mod.Class```).

.. _MyST: https://myst-parser.readthedocs.io/

.. autofunction:: parse

.. autoclass:: MdParser
    :members:

"""

from __future__ import annotations

import dataclasses
import re
import string
from dataclasses import dataclass

import yuio.doc
from yuio.util import dedent as _dedent

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "MdParser",
    "parse",
]


T = _t.TypeVar("T")


_HEADING_RE = re.compile(
    r"""
    ^
    \s{0,3}                     # - Initial indent.
    (?P<marker>\#{1,6})         # - Heading marker.
    (?P<text>(?:\s.*?)?)        # - Heading text. Unless empty, text must be separated
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
                                #   we treat them as a list marker followed
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
                                #   we treat them as a list marker followed
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
    (?P<fence>~~~+|:::+)        # - Backtick fence.
    (?P<syntax>.*)              # - Syntax, can be anything.
    $
    """,
    re.VERBOSE,
)
_CODE_FENCE_END_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial indent.
    (?P<fence>~~~+|```+|:::+)   # - Fence.
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
_LINK_ANCHOR_RE = re.compile(
    r"""
    ^
    (?P<indent>\s{0,3})         # - Initial indent.
    \[                          # - Opening marker.
    (?P<anchor>
        (?:[^\[\]]|\\.){1,999}  # - Link anchor, up to 999 symbols.
    )
    \]:                         # - Closing marker.
    (?P<href>.*)                # - Url. If empty, we look for url on the next line.
    $
    """,
    re.VERBOSE,
)
_MYST_DIRECTIVE_NAME_RE = re.compile(
    r"""
    ^
    \{                          # - Directive name starts with an opening brace.
    (?P<directive_name>(?:      # - The actual name consists of:
          [a-zA-Z0-9]           #   - alphanumerics,
        | [-_+:,](?![-_+:,])    #   - or isolated special characters,
    )+)                         #   - and it's non-empty.
    \}                          # - It ends with a closing brace.
    (?P<arg>.*)                 # - Followed by directive arguments.
    $
    """,
    re.VERBOSE,
)
_LINE_FEED_RE = re.compile(r"\r\n|\r|\n|\v\r\n|\v\r|\v\n|\v")


@dataclass(slots=True)
class _Token:
    """
    Token for processing inline markup.

    """

    start: int
    end: int
    kind: str

    # Length can decrease as we use up emphasis symbols.
    len: int = dataclasses.field(init=False)

    # Emphasis data.
    can_open: bool = False
    can_close: bool = False
    prev_delim: int = -1
    next_delim: int = -1

    # Action data.
    _data: dict[str, _t.Any] | None = dataclasses.field(init=False, default=None)

    def __post_init__(self):
        self.len = self.end - self.start

    @property
    def data(self):
        if self._data is None:
            self._data = {}
        return self._data


@dataclass(kw_only=True, slots=True)
class _Default:
    pass


@dataclass(kw_only=True, slots=True)
class _List:
    type: str
    marker_len: int
    list: yuio.doc.List
    parser: MdParser
    number: int | None = None
    starts_with_empty_line: bool = False


@dataclass(kw_only=True, slots=True)
class _Quote:
    parser: MdParser


@dataclass(kw_only=True, slots=True)
class _Code:
    lines: list[str]


@dataclass(kw_only=True, slots=True)
class _FencedCode:
    indent: int
    fence_symbol: str
    fence_length: int
    syntax: str
    lines: list[str]


@dataclass(kw_only=True, slots=True)
class _Paragraph:
    lines: list[str]


@dataclass(kw_only=True, slots=True)
class _Anchor:
    anchor: str


_State: _t.TypeAlias = (
    _Default | _List | _Quote | _Code | _FencedCode | _Paragraph | _Anchor
)


@_t.final
class MdParser(yuio.doc.DocParser):
    """
    Parses subset of CommonMark/MyST.

    """

    def __init__(self):
        self._nodes: list[yuio.doc.AstBase] = []
        self._state: _State = _Default()
        self._anchors: dict[str, tuple[str, str]] = {}

    def _parser(self) -> MdParser:
        parser = MdParser()
        parser._anchors = self._anchors
        return parser

    @staticmethod
    def _is_blank(s: str) -> bool:
        return not s or s.isspace()

    def parse(self, s: str) -> yuio.doc.Document:
        s = s.expandtabs(tabsize=4)
        root = self._do_parse(_LINE_FEED_RE.split(s))
        yuio.doc._clean_tree(root)
        self._process_inline_text(root)
        return root

    def parse_paragraph(self, s: str, /) -> list[str | yuio.doc.TextRegion]:
        return _InlineParser(s, {}).run()

    def _do_parse(self, lines: list[str]):
        for line in lines:
            self._handle_line(line)
        return yuio.doc.Document(items=self._finalize())

    def _process_inline_text(self, node: yuio.doc.AstBase):
        if isinstance(node, yuio.doc.Admonition):
            processor = _InlineParser("\n".join(map(str, node.title)), self._anchors)
            node.title = processor.run()
        if isinstance(node, yuio.doc.Text):
            processor = _InlineParser("\n".join(map(str, node.items)), self._anchors)
            node.items = processor.run()
        elif isinstance(node, yuio.doc.Container):
            for item in node.items:
                self._process_inline_text(item)

    def _handle_line(self, line: str):
        getattr(self, f"_handle_line_{self._state.__class__.__name__.lstrip('_')}")(
            line
        )

    def _handle_lazy_line(self, line: str) -> bool:
        return getattr(
            self, f"_handle_lazy_line_{self._state.__class__.__name__.lstrip('_')}"
        )(line)

    def _flush(self):
        getattr(self, f"_flush_{self._state.__class__.__name__.lstrip('_')}")()

    def _handle_line_List(self, line: str):
        assert type(self._state) is _List
        if self._is_blank(line) and self._state.starts_with_empty_line:
            self._flush_List()
            self._handle_line_Default(line)
        elif self._is_blank(line) or line[: self._state.marker_len].isspace():
            self._state.parser._handle_line(line[self._state.marker_len :])
        elif (
            (
                (match := _LIST_RE.match(line))
                or (match := _NUMBERED_LIST_RE.match(line))
            )
            and match.group("type") == self._state.type
            and not _THEMATIC_BREAK_RE.match(line)
        ):
            item = yuio.doc.ListItem(
                items=self._state.parser._finalize(),
                number=self._state.number,
            )
            self._state.list.items.append(item)
            marker = match.group("marker")
            indent = len(marker)
            if not marker.endswith(" "):
                indent += 1
            self._state.marker_len = indent
            self._state.parser._handle_line(match.group("text"))
            if self._state.number is not None:
                self._state.number += 1
        elif not self._state.parser._handle_lazy_line(line):
            self._flush_List()
            self._handle_line_Default(line)

    def _handle_lazy_line_List(self, line: str) -> bool:
        assert type(self._state) is _List
        if self._state.parser._handle_lazy_line(line):
            return True
        return False

    def _flush_List(self):
        assert type(self._state) is _List
        item = yuio.doc.ListItem(
            items=self._state.parser._finalize(),
            number=self._state.number,
        )
        self._state.list.items.append(item)
        self._nodes.append(self._state.list)
        self._state = _Default()

    def _handle_line_Quote(self, line: str):
        assert type(self._state) is _Quote
        if match := _QUOTE_RE.match(line):
            self._state.parser._handle_line(match.group("text"))
        elif self._is_blank(line) or not self._state.parser._handle_lazy_line(line):
            self._flush_Quote()
            self._handle_line_Default(line)

    def _handle_lazy_line_Quote(self, line: str) -> bool:
        assert type(self._state) is _Quote
        if self._state.parser._handle_lazy_line(line):
            return True
        else:
            return False

    def _flush_Quote(self):
        assert type(self._state) is _Quote
        self._nodes.append(yuio.doc.Quote(items=self._state.parser._finalize()))
        self._state = _Default()

    def _handle_line_Code(self, line: str):
        assert type(self._state) is _Code
        if self._is_blank(line) or line.startswith("    "):
            self._state.lines.append(line[4:])
        else:
            self._flush_Code()
            self._handle_line_Default(line)

    def _handle_lazy_line_Code(self, line: str) -> bool:
        assert type(self._state) is _Code
        return False  # No lazy continuations for code!

    def _flush_Code(self):
        assert type(self._state) is _Code
        while self._state.lines and self._is_blank(self._state.lines[-1]):
            self._state.lines.pop()
        if self._state.lines:
            self._nodes.append(
                yuio.doc.Code(
                    lines=self._state.lines,
                    syntax="",
                )
            )
        self._state = _Default()

    def _handle_line_FencedCode(self, line: str):
        assert type(self._state) is _FencedCode
        if (
            (match := _CODE_FENCE_END_RE.match(line))
            and match.group("fence")[0] == self._state.fence_symbol
            and len(match.group("fence")) >= self._state.fence_length
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
        assert type(self._state) is _FencedCode
        return False

    def _flush_FencedCode(self):
        assert type(self._state) is _FencedCode
        if match := _MYST_DIRECTIVE_NAME_RE.match(self._state.syntax):
            # This is a MyST directive.
            first_actual_line = 0

            # Parse yaml options block.
            if (
                first_actual_line < len(self._state.lines)
                and self._state.lines[first_actual_line] == "---"
            ):
                first_actual_line += 1
                while (
                    first_actual_line < len(self._state.lines)
                    and self._state.lines[first_actual_line] != "---"
                ):
                    first_actual_line += 1
            # Parse normal options block.
            if first_actual_line < len(self._state.lines) and self._state.lines[
                first_actual_line
            ].startswith(":"):
                first_actual_line += 1
            # Trim empty lines.
            if (
                first_actual_line < len(self._state.lines)
                and not self._state.lines[first_actual_line].strip()
            ):
                first_actual_line += 1
            self._state.lines = self._state.lines[first_actual_line:]

            name = match.group("directive_name")
            arg = match.group("arg").strip()
        else:
            name = "code-block"
            arg = self._state.syntax

        self._nodes.extend(
            yuio.doc._process_directive(
                name,
                arg,
                lambda: self._state.lines,  # type: ignore
                lambda: self._parser()._do_parse(self._state.lines).items,  # type: ignore
            )
        )
        self._state = _Default()

    def _handle_line_Paragraph(self, line: str):
        assert type(self._state) is _Paragraph
        if match := _SETEXT_HEADING_RE.match(line):
            level = 1 if match.group("level") == "=" else 2
            self._nodes.append(
                yuio.doc.Heading(
                    items=_t.cast(list[str | yuio.doc.TextRegion], self._state.lines),
                    level=level,
                )
            )
            self._state = _Default()
        elif (
            self._is_blank(line)
            or _THEMATIC_BREAK_RE.match(line)
            or _HEADING_RE.match(line)
            or _CODE_BACKTICK_RE.match(line)
            or _CODE_TILDE_RE.match(line)
            or (
                (match := _LIST_RE.match(line))
                and not self._is_blank(match.group("text"))
            )
            or (
                (match := _NUMBERED_LIST_RE.match(line))
                and not self._is_blank(match.group("text"))
                and match.group("number") == "1"
            )
            or _QUOTE_RE.match(line)
        ):
            self._flush_Paragraph()
            self._handle_line_Default(line)
        else:
            self._state.lines.append(line)

    def _handle_lazy_line_Paragraph(self, line: str) -> bool:
        assert type(self._state) is _Paragraph
        if (
            self._is_blank(line)
            or _THEMATIC_BREAK_RE.match(line)
            or _HEADING_RE.match(line)
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
        assert type(self._state) is _Paragraph
        self._nodes.append(
            yuio.doc.Paragraph(
                items=_t.cast(list[str | yuio.doc.TextRegion], self._state.lines)
            )
        )
        self._state = _Default()

    def _handle_line_Anchor(self, line: str):
        assert type(self._state) is _Anchor
        line = line.strip()
        if line:
            url, _ = _InlineParser.parse_link(line)
            if url:
                self._anchors.setdefault(self._state.anchor, (line, ""))
        else:
            self._nodes.append(yuio.doc.Paragraph(items=[f"[{self._state.anchor}]:"]))
        self._state = _Default()

    def _handle_lazy_line_Anchor(self, line: str):
        assert type(self._state) is _Anchor
        line = line.strip()
        if line:
            url, _ = _InlineParser.parse_link(line)
            if url:
                self._anchors.setdefault(self._state.anchor, (line, ""))
            self._state = _Default()
            return True
        else:
            self._nodes.append(yuio.doc.Paragraph(items=[f"[{self._state.anchor}]:"]))
            self._state = _Default()
            return False

    def _flush_Anchor(self):
        assert type(self._state) is _Anchor
        self._state = _Default()

    def _handle_line_Default(self, line: str):
        assert type(self._state) is _Default
        if self._is_blank(line):
            pass  # do nothing
        elif match := _LINK_ANCHOR_RE.match(line):
            anchor = match.group("anchor").strip()
            href = match.group("href").strip()
            if not anchor:
                self._state = _Paragraph(lines=[line])
            elif href:
                url, _ = _InlineParser.parse_link(href)
                if url is not None:
                    anchor = _InlineParser.norm_anchor(anchor)
                    self._anchors.setdefault(anchor, (url, ""))
                else:
                    self._state = _Paragraph(lines=[line])
            else:
                anchor = _InlineParser.norm_anchor(anchor)
                self._state = _Anchor(anchor=anchor)
        elif _THEMATIC_BREAK_RE.match(line):
            self._nodes.append(yuio.doc.ThematicBreak())
        elif match := _HEADING_RE.match(line):
            level = len(match.group("marker"))
            self._nodes.append(
                yuio.doc.Heading(
                    items=[match.group("text").strip()],
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
            self._state = _FencedCode(
                indent=indent,
                fence_symbol=fence_symbol,
                fence_length=fence_length,
                syntax=syntax,
                lines=[],
            )
        elif match := _CODE_RE.match(line):
            self._state = _Code(lines=[match.group("text")])
        elif (match := _LIST_RE.match(line)) or (
            match := _NUMBERED_LIST_RE.match(line)
        ):
            marker = match.group("marker")
            indent = len(marker)
            if not marker.endswith(" "):
                indent += 1
            list_type = match.group("type")
            number_str = match.groupdict().get("number", None)
            number = int(number_str) if number_str else None
            starts_with_empty_line = self._is_blank(match.group("text"))
            self._state = _List(
                type=list_type,
                marker_len=indent,
                list=yuio.doc.List(
                    items=[],
                    enumerator_kind=(
                        yuio.doc.ListEnumeratorKind.NUMBER
                        if number is not None
                        else None
                    ),
                ),
                parser=self._parser(),
                number=number,
                starts_with_empty_line=starts_with_empty_line,
            )
            self._state.parser._handle_line(match.group("text"))
        elif match := _QUOTE_RE.match(line):
            self._state = _Quote(parser=self._parser())
            self._state.parser._handle_line(match.group("text"))
        else:
            self._state = _Paragraph(lines=[line])

    def _handle_lazy_line_Default(self, line: str) -> bool:
        assert type(self._state) is _Default
        return False

    def _flush_Default(self):
        assert type(self._state) is _Default

    def _finalize(self) -> list[yuio.doc.AstBase]:
        self._flush()
        result = self._nodes
        self._nodes = []
        return result


_UNESCAPE_RE = re.compile(rf"\\([{re.escape(string.punctuation)}])")


class _InlineParser:
    # Based on https://spec.commonmark.org/0.31.2/#phase-2-inline-structure

    def __init__(self, text: str, anchors: dict[str, tuple[str, str]]) -> None:
        self._text = text
        self._pos = 0
        self._anchors = anchors
        self._tokens: list[_Token] = []
        self._link_opener_indices: list[int] = []
        self._delim_first = -1
        self._delim_last = -1

    @staticmethod
    def norm_anchor(anchor: str) -> str:
        return re.sub(r"\s+", " ", anchor.strip()).casefold()

    @staticmethod
    def unescape(text: str) -> str:
        return _UNESCAPE_RE.sub(r"\1", text)

    def run(self) -> list[str | yuio.doc.TextRegion]:
        while self._fits(self._pos):
            self._run()
        self._process_delims()

        res = yuio.doc.TextRegion()
        stack = [res]

        em = 0
        strong = 0

        def add_text(text: str | yuio.doc.TextRegion):
            if not text:
                return
            colors = []
            if em:
                colors.append("em")
            if strong:
                colors.append("strong")
            if colors:
                text = yuio.doc.HighlightedRegion(text, color=" ".join(colors))
            stack[-1].content.append(text)

        for token in self._tokens:
            match token.kind:
                case "text":
                    text = self._text[token.start : token.start + token.len]
                    add_text(text)
                case "*" | "_":
                    em += token.data.get("em", 0)
                    strong += token.data.get("strong", 0)
                    text = self._text[token.start : token.start + token.len]
                    add_text(text)
                case "link_start":
                    if (url := token.data.get("url")) is not None:
                        stack.append(yuio.doc.LinkRegion(url=url))
                    else:
                        text = self._text[token.start : token.start + token.len]
                        add_text(text)
                case "link_end":
                    assert len(stack) > 1
                    top = stack.pop()
                    stack[-1].content.append(top)
                case "escape":
                    text = self._text[token.start : token.start + token.len]
                    if text == "\n":
                        text = (
                            "\v\n"  # Vertical tab forces wrapper to make a line break.
                        )
                    elif not text or text not in string.punctuation:
                        text = "\\" + text
                    add_text(text)
                case "formatted":
                    add_text(token.data["content"])
                case kind:
                    assert False, kind

        return res.content

    @classmethod
    def parse_link(cls, link: str):
        return cls(link + ")", {})._parse_link()

    def _fits(self, i):
        return i < len(self._text)

    def _ch_eq(self, i, cs):
        return self._fits(i) and self._text[i] in cs

    def _ch_in(self, i, cs):
        return self._fits(i) and self._text[i] in cs

    def _ch_at(self, i):
        if 0 <= i < len(self._text):
            return self._text[i]
        else:
            return " "

    def _eat(self, ch):
        start = self._pos
        while self._pos < len(self._text) and self._text[self._pos] == ch:
            self._pos += 1
        return self._pos - start

    def _eat_in(self, ch):
        start = self._pos
        while self._pos < len(self._text) and self._text[self._pos] in ch:
            self._pos += 1
        return self._pos - start

    def _eat_not_in(self, ch):
        start = self._pos
        while self._pos < len(self._text) and self._text[self._pos] not in ch:
            self._pos += 1
        return self._pos - start

    def _run(self):
        match self._text[self._pos]:
            case "\\":
                self._tokens.append(_Token(self._pos + 1, self._pos + 2, "escape"))
                self._pos += 2
            case "`":
                self._parse_code()
            case "$":
                self._parse_math()
            case "{":
                self._parse_role()
            case "!" if self._ch_eq(self._pos + 1, "["):
                self._push_link_start("image_start", 2)
            case "[":
                self._push_link_start("link_start", 1)
            case "]":
                self._parse_link_end()
            case "*" | "_":
                self._parse_delim_run()
            case "!" | "\\":
                self._tokens.append(_Token(self._pos, self._pos + 1, "text"))
                self._pos += 1
            case _:
                start = self._pos
                self._eat_not_in("\\`[]!*_{$")
                self._tokens.append(_Token(start, self._pos, "text"))

    def _parse_role(self):
        start = self._pos
        self._pos += 1
        # alphanumerics plus isolated internal hyphens, underscores, plus signs, colons, and periods

        while self._fits(self._pos):
            match self._text[self._pos]:
                case "}":
                    self._pos += 1
                    break
                case ch if ch.isalnum():
                    self._pos += 1
                case ch if ch in "-_+:," and not self._ch_in(self._pos + 1, "-_+:,"):
                    self._pos += 1
                case _:
                    self._pos = start + 1
                    self._tokens.append(_Token(self._pos, self._pos + 1, "text"))
                    return
        if self._ch_eq(self._pos, "`"):
            role = self._text[start + 1 : self._pos - 1]
            self._parse_code(role)

    def _parse_code(self, role: str | None = None):
        start = self._pos
        n_backticks = self._eat("`")

        end = None
        while self._fits(self._pos):
            if self._text[self._pos] == "`":
                n_backticks_end = self._eat("`")
                if n_backticks == n_backticks_end:
                    end = self._pos
                    break
            else:
                self._pos += 1

        if end is None:
            self._tokens.append(_Token(start, start + n_backticks, "text"))
            self._pos = start + n_backticks
        else:
            code = self._text[start + n_backticks : end - n_backticks]
            if (
                code.startswith((" ", "\n"))
                and code.endswith((" ", "\n"))
                and len(code) > 2
            ):
                code = code[1:-1]
                start += 1
                end -= 1
            token = _Token(start + n_backticks, end - n_backticks, "formatted")
            token.data["content"] = yuio.doc._process_role(code, role or "code")
            self._tokens.append(token)

    def _parse_math(self):
        start = self._pos
        n_markers = self._eat("$")
        if n_markers > 2:
            self._tokens.append(_Token(start, self._pos, "text"))
            return

        end = None
        while self._fits(self._pos):
            if self._text[self._pos] == "$":
                n_markers_end = self._eat("$")
                if n_markers == n_markers_end:
                    end = self._pos
                    break
            else:
                self._pos += 1

        if end is None:
            self._tokens.append(_Token(start, start + n_markers, "text"))
            self._pos = start + n_markers
        else:
            code = self._text[start + n_markers : end - n_markers]
            token = _Token(start + n_markers, end - n_markers, "formatted")
            token.data["content"] = yuio.doc._process_role(code, "math")
            self._tokens.append(token)

    def _push_link_start(self, kind, length):
        self._link_opener_indices.append(len(self._tokens))
        self._tokens.append(
            _Token(
                self._pos,
                self._pos + length,
                kind,
            )
        )
        self._pos += length

    def _parse_link_end(self):
        if not self._link_opener_indices:
            # No corresponding link opener.
            self._tokens.append(_Token(self._pos, self._pos + 1, "text"))
            self._pos += 1
            return
        opener_token_idx = self._link_opener_indices.pop()
        opener_token = self._tokens[opener_token_idx]
        assert opener_token.kind in ["link_start", "image_start"]

        start = self._pos
        self._pos += 1

        if self._ch_eq(self._pos, "("):
            self._pos += 1
            url, title = self._parse_link()
        else:
            if self._ch_eq(self._pos, "["):
                self._pos += 1
                anchor = self._parse_anchor()
            else:
                anchor = self._text[opener_token.end : self._pos - 1]
            if anchor:
                url, title = self._anchors.get(self.norm_anchor(anchor), (None, None))
            else:
                url, title = None, None

        if url is None:
            self._tokens.append(_Token(start, start + 1, "text"))
            self._pos = start + 1
            return

        if opener_token.kind == "link_start":
            close_token = _Token(start, self._pos, "link_end")
            self._link_opener_indices.clear()  # Prevent nested links.
        else:
            close_token = _Token(start, self._pos, "image_end")
        opener_token.data["url"] = url
        opener_token.data["title"] = title
        opener_token.len = 0
        close_token.data["url"] = None
        close_token.data["title"] = None
        close_token.len = 0
        self._tokens.append(close_token)
        self._process_delims(opener_token_idx)

    def _parse_link(self):
        if self._ch_eq(self._pos, "<"):
            self._pos += 1
            url = self._parse_href_angled()
        else:
            url = self._parse_href_bare()
        if url is None:
            return None, None  # Href parsing failed.
        if self._ch_in(self._pos, " )"):
            title = self._parse_title()
            if title is None:
                return None, None  # Title parsing failed.
            else:
                url = self.unescape(url)  # Normal escaping rules apply.
                return url, title
        else:
            return None, None  # Href does not end with expected symbol.

    def _parse_href_angled(self):
        start = self._pos
        while self._fits(self._pos):
            match self._text[self._pos]:
                case "\\" if self._ch_in(self._pos + 1, string.punctuation):
                    self._pos += 2
                case ">":
                    self._pos += 1
                    return self._text[start : self._pos - 1]
                case "<" | "\n":
                    break
                case _:
                    self._pos += 1
        return None

    def _parse_href_bare(self):
        start = self._pos
        paren_level = 1
        url = None
        while self._fits(self._pos):
            match self._text[self._pos]:
                case "\\" if self._ch_in(self._pos + 1, string.punctuation):
                    self._pos += 2
                case ch if 0x00 <= ord(ch) <= 0x1F:
                    break
                case "\x7f":
                    break
                case " ":
                    url = self._text[start : self._pos]
                    break
                case "(":
                    paren_level += 1
                    self._pos += 1
                case ")":
                    paren_level -= 1
                    if paren_level == 0:
                        url = self._text[start : self._pos]
                        break
                    else:
                        self._pos += 1
                case _:
                    self._pos += 1
        if not url:
            # Empty url is not allowed in this case.
            url = None
        return url

    def _parse_title(self):
        self._eat(" ")
        if self._ch_eq(self._pos, ")"):
            self._pos += 1
            return ""  # Empty title is ok.
        elif self._ch_eq(self._pos, "'"):
            self._pos += 1
            end_char = "'"
        elif self._ch_eq(self._pos, '"'):
            self._pos += 1
            end_char = '"'
        elif self._ch_eq(self._pos, "("):
            self._pos += 1
            end_char = ")"
        else:
            return None  # Title parsing failed.
        start = self._pos
        title = None
        while self._fits(self._pos):
            match self._text[self._pos]:
                case "\\" if self._ch_in(self._pos + 1, string.punctuation):
                    self._pos += 2
                case ch if ch == end_char:
                    title = self._text[start : self._pos]
                    self._pos += 1
                    break
                case _:
                    self._pos += 1
        if self._ch_eq(self._pos, ")"):
            self._pos += 1
        else:
            return None  # Href does not end with expected symbol.
        return title

    def _parse_anchor(self):
        start = self._pos
        while self._fits(self._pos):
            match self._text[self._pos]:
                case "\\" if self._ch_in(self._pos + 1, string.punctuation):
                    self._pos += 2
                case "]":
                    self._pos += 1
                    return self._text[start : self._pos - 1]
                case _:
                    self._pos += 1
        return None

    def _parse_delim_run(self):
        start = self._pos
        ch = self._text[self._pos]
        self._eat(ch)

        char_before = self._ch_at(start - 1)
        char_after = self._ch_at(self._pos)

        left_flanking = not char_after.isspace() and (
            char_after not in string.punctuation
            or char_before.isspace()
            or char_before in string.punctuation
        )

        right_flanking = not char_before.isspace() and (
            char_before not in string.punctuation
            or char_after.isspace()
            or char_after in string.punctuation
        )

        if ch == "*":
            can_open = left_flanking
            can_close = right_flanking
        else:  # "_"
            can_open = left_flanking and (
                not right_flanking or (char_before in string.punctuation)
            )
            can_close = right_flanking and (
                not left_flanking or (char_after in string.punctuation)
            )

        if can_open or can_close:
            self._tokens.append(
                _Token(start, self._pos, ch, can_open=can_open, can_close=can_close)
            )
            self._push_delim(-1)
        else:
            self._tokens.append(_Token(start, self._pos, "text"))

    def _push_delim(self, idx: int):
        if idx == -1:
            idx += len(self._tokens)
        assert idx >= 0
        assert self._tokens[idx].kind in "*_"
        assert self._tokens[idx].prev_delim == -1
        assert self._tokens[idx].next_delim == -1

        if self._delim_last == -1:
            self._delim_last = self._delim_first = idx
        else:
            self._tokens[self._delim_last].next_delim = idx
            self._tokens[idx].prev_delim = self._delim_last
            self._delim_last = idx

    def _remove_delim(self, idx: int):
        tok = self._tokens[idx]
        if tok.prev_delim == -1:
            self._delim_first = tok.next_delim
        else:
            self._tokens[tok.prev_delim].next_delim = tok.next_delim
        if tok.next_delim == -1:
            self._delim_last = tok.prev_delim
        else:
            self._tokens[tok.next_delim].prev_delim = tok.prev_delim

    def _next_delim(self, idx: int):
        if idx == -1:
            return self._delim_first
        else:
            return self._tokens[idx].next_delim

    def _prev_delim(self, idx: int):
        if idx == -1:
            return self._delim_last
        else:
            return self._tokens[idx].prev_delim

    def _process_delims(self, first_delim: int = -1):
        if first_delim == -1:
            bottom_idx = -1
        else:
            for i in range(first_delim, len(self._tokens)):
                if self._tokens[i].kind in "*_":
                    bottom_idx = self._prev_delim(i)
                    break
            else:
                bottom_idx = -1

        openers_bottom_idxs = {
            ("*", 0, False): bottom_idx,
            ("*", 1, False): bottom_idx,
            ("*", 2, False): bottom_idx,
            ("*", 0, True): bottom_idx,
            ("*", 1, True): bottom_idx,
            ("*", 2, True): bottom_idx,
            ("_", 0, False): bottom_idx,
            ("_", 1, False): bottom_idx,
            ("_", 2, False): bottom_idx,
            ("_", 0, True): bottom_idx,
            ("_", 1, True): bottom_idx,
            ("_", 2, True): bottom_idx,
        }

        current_idx = self._next_delim(bottom_idx)
        while True:
            while current_idx != -1 and not self._tokens[current_idx].can_close:
                current_idx = self._next_delim(current_idx)
            if current_idx == -1:
                break
            # Current is a potential closer, find a matching opener for it.
            current = self._tokens[current_idx]
            bottom_idx_for_current = max(
                bottom_idx,
                openers_bottom_idxs[(current.kind, current.len % 3, current.can_open)],
            )

            opener_idx = self._prev_delim(current_idx)
            while opener_idx > bottom_idx_for_current:
                opener = self._tokens[opener_idx]

                # "If one of the delimiters can both open and close emphasis,
                # then the sum of the lengths of the delimiter runs containing
                # the opening and closing delimiters must not be a multiple
                # of 3 unless both lengths are multiples of 3."
                #
                # See https://spec.commonmark.org/0.31.2/#emphasis-and-strong-emphasis.
                if (
                    opener.can_open
                    and opener.kind == current.kind
                    and (
                        # None or the delimiters can open and close at the same time...
                        not (opener.can_close or current.can_open)
                        # ...or sum of their lengths is not a multiple of 3...
                        or (opener.len + current.len) % 3 != 0
                        # ...or both lengths are multiples of 3.
                        or not (opener.len % 3 != 0 or current.len % 3 != 0)
                    )
                ):
                    # Found an opener for current.
                    is_strong = opener.len >= 2 and current.len >= 2

                    data_key = "strong" if is_strong else "em"
                    opener.data.setdefault(data_key, 0)
                    opener.data[data_key] += 1
                    current.data.setdefault(data_key, 0)
                    current.data[data_key] -= 1

                    opener.next_delim = current_idx
                    current.prev_delim = opener_idx

                    opener.len -= 1 + is_strong
                    if not opener.len:
                        self._remove_delim(opener_idx)

                    current.len -= 1 + is_strong
                    next_idx = current_idx
                    if not current.len:
                        next_idx = self._next_delim(current_idx)
                        self._remove_delim(current_idx)

                    current_idx = next_idx

                    break
                else:
                    opener_idx = self._prev_delim(opener_idx)
            else:
                # No opener for current.
                openers_bottom_idxs[
                    (current.kind, current.len % 3, current.can_open)
                ] = self._prev_delim(current_idx)
                next_idx = self._next_delim(current_idx)
                if not current.can_open:
                    self._remove_delim(current_idx)
                current_idx = next_idx


def parse(text: str, /, *, dedent: bool = True) -> yuio.doc.Document:
    """
    Parse a markdown document and return an AST node.

    :param text:
        text to parse. Common indentation will be removed from this string,
        making it suitable to use with triple quote literals.
    :param dedent:
        remove lading indent from `text`.
    :returns:
        parsed AST node.

    """

    if dedent:
        text = _dedent(text)

    return MdParser().parse(text)
