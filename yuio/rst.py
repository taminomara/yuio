# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Parser for ReStructuredText.

Yuio supports all RST features except tables and option lists.

**Supported block markup:**

-   headings,
-   numbered and bullet lists,
-   definition lists,
-   field lists,
-   literal blocks, both indented and quoted,
-   line blocks,
-   quotes,
-   doctest blocks,
-   directives,
-   hyperlink targets,
-   footnotes,
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
-   interpreted text (```code```, ``:role:`code```),
-   hyperlink references (```text`_``, ``text_``, ```text`__``, ``text__``)
    in terminals that can render them,
-   footnotes (``[...]_``),
-   inline internal targets and substitution references are parsed correctly,
    but they have no effect.

**Supported inline roles:**

-   ``flag`` for CLI flags,
-   any other role is interpreted as documentation reference with explicit titles
    (``{py:class}`title <mod.Class>```) and shortening paths via tilde
    (``{py:class}`~mod.Class```).

.. autofunction:: parse

.. autoclass:: RstParser
    :members:

"""

from __future__ import annotations

import dataclasses
import re
import string
from dataclasses import dataclass
from enum import Enum

import yuio.doc
from yuio.util import dedent as _dedent

import yuio._typing_ext as _tx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "RstParser",
    "parse",
]


class _LineEnding(Enum):
    NORMAL = "NORMAL"
    LITERAL_MARK = "LITERAL_MARK"  # Line ends with double colon


_LINE_BLOCK_START_RE = re.compile(
    r"""
        ^
        (?P<indent>
            (?P<open_marker>\|)
            (?P<space>\s+|$)
        )
        (?P<tail>.*)
    """,
    re.VERBOSE,
)


_BULLET_LIST_START_RE = re.compile(
    r"""
        ^
        (?P<indent>
            (?P<enumerator>[*+•‣⁃-])
            (?P<space>\s+|$)
        )
        (?P<tail>.*)
        $
    """,
    re.VERBOSE,
)


_NUM_LIST_START_RE = re.compile(
    r"""
        ^
        (?P<indent>
            (?P<open_marker>\(?)
            (?P<enumerator>
                  (?P<enumerator_num>\d+)
                | (?P<enumerator_auto>\#)
                | (?P<enumerator_lowercase>[a-z]+)
                | (?P<enumerator_uppercase>[A-Z]+)
            )
            (?P<close_marker>[).])
            (?P<space>\s+|$)
        )
        (?P<tail>.*)
        $
    """,
    re.VERBOSE,
)


_EXPLICIT_MARKUP_START_RE = re.compile(
    r"""
        ^
        (?P<indent>
            (?P<open_marker>\.\.)
            (?P<space>\s+|$)
        )
        (?P<tail>.*)
        $
    """,
    re.VERBOSE,
)

_IMPLICIT_HYPERLINK_TARGET_RE = re.compile(
    r"""
        ^
        (?P<indent>
            (?P<open_marker>__)
            (?P<space>\s+|$)
        )
        (?P<tail>.*)
        $
    """,
    re.VERBOSE,
)

_FIELD_START_RE = re.compile(
    r"""
        ^
        (?P<indent>
            (?P<open_marker>:)
            (?P<content>(?:[^:\\]|\\.|:(?!\s|`))+)
            (?P<close_marker>:)
            (?P<space>\s+|$)
        )
        (?P<tail>.*)
        $
    """,
    re.VERBOSE,
)


_PUNCT = tuple(string.punctuation)


@dataclass(slots=True)
class _Hyperlink:
    start: int
    end: int
    name: str
    type: _t.Literal["link", "footnote", "redirect"]
    content: str


class _LinkResolver:
    def __init__(
        self,
        targets: dict[str, _Hyperlink],
        anonymous_links: list[_Hyperlink],
        auto_numbered_footnotes: list[str] = [],
        auto_character_footnotes: list[str] = [],
    ) -> None:
        self._targets: dict[str, _Hyperlink] = targets

        self._anonymous_links: list[_Hyperlink] = anonymous_links
        self._current_anonymous_link = 0

        self._auto_numbered_footnotes: list[str] = auto_numbered_footnotes
        self._current_auto_numbered_footnote = 0
        self._auto_character_footnotes: list[str] = auto_character_footnotes
        self._current_auto_character_footnote = 0

    def find_link(self, title: str, target: str | None, is_anonymous: bool):
        if target:
            # Process explicit target.
            target, is_redirect = _normalize_hyperlink_target(target)
            if is_redirect:
                link = self._resolve_redirect(target)
            else:
                link = _Hyperlink(0, 0, title, "link", target)
            if link and not is_anonymous:
                # Save implicitly declared anchor.
                anchor = _normalize_hyperlink_anchor(title)
                self._targets.setdefault(anchor, link)
        elif is_anonymous:
            link = self._next_anonymous_link()
        else:
            anchor = _normalize_hyperlink_anchor(title)
            if anchor.startswith("#"):
                anchor = anchor[1:]
                if not anchor:
                    anchor = self._next_auto_numbered_footnote() or ""
            elif anchor.startswith("*"):
                anchor = anchor[1:]
                if not anchor:
                    anchor = self._next_auto_character_footnote() or ""
            if not anchor:
                return None
            link = self._targets.get(anchor)
        if link and link.type == "redirect":
            link = self._resolve_redirect(link.content)
        if not link or not link.content:
            return None
        else:
            return link

    def _next_anonymous_link(self):
        if self._current_anonymous_link >= len(self._anonymous_links):
            return None
        link = self._anonymous_links[self._current_anonymous_link]
        self._current_anonymous_link += 1
        return link

    def _next_auto_numbered_footnote(self):
        if self._current_auto_numbered_footnote >= len(self._auto_numbered_footnotes):
            return None
        link = self._auto_numbered_footnotes[self._current_auto_numbered_footnote]
        self._current_auto_numbered_footnote += 1
        return link

    def _next_auto_character_footnote(self):
        if self._current_auto_character_footnote >= len(self._auto_character_footnotes):
            return None
        link = self._auto_character_footnotes[self._current_auto_character_footnote]
        self._current_auto_character_footnote += 1
        return link

    def _resolve_redirect(self, target: str):
        seen = set()
        while target not in seen:
            seen.add(target)
            link = self._targets.get(target)
            if link and link.type == "redirect":
                target = link.content
            elif link:
                return link
        return None


_FOOTNOTE_CHARS = "*†‡§¶#♠♥♦♣"


def _char_footnote(n: int, /) -> str:
    assert n > 0
    n_chars = len(_FOOTNOTE_CHARS)
    result = ""
    while n > 0:
        n -= 1
        result = _FOOTNOTE_CHARS[n % n_chars] + result
        n //= n_chars
    return result


@_t.final
class RstParser(yuio.doc.DocParser):
    """
    Parses subset of CommonMark/MyST.

    """

    def parse(self, s: str, /) -> yuio.doc.Document:
        self._lines = s.expandtabs(tabsize=4).splitlines(keepends=False)
        self._headings: dict[tuple[str, bool], int] = {}
        self._links: list[_Hyperlink] = []
        self._anonymous_links: list[_Hyperlink] = []
        self._targets: dict[str, _Hyperlink] = {}
        self._last_numbered_footnote = 1
        self._last_character_footnote = 1
        self._auto_numbered_footnotes: list[str] = []
        self._auto_character_footnotes: list[str] = []

        root = yuio.doc.Document(items=[])
        self._process_block(root, 0, len(self._lines))
        link_resolver = _LinkResolver(
            self._targets,
            self._anonymous_links,
            self._auto_numbered_footnotes,
            self._auto_character_footnotes,
        )
        yuio.doc._clean_tree(root)
        self._process_inline_text(root, link_resolver)
        return root

    def parse_paragraph(self, s: str, /) -> list[str | yuio.doc.TextRegion]:
        return _InlineParser(s, _LinkResolver({}, [], [], [])).run()

    def _process_inline_text(
        self, node: yuio.doc.AstBase, link_resolver: _LinkResolver
    ):
        if isinstance(node, yuio.doc.Admonition):
            processor = _InlineParser("\n".join(map(str, node.title)), link_resolver)
            node.title = processor.run()
        if isinstance(node, yuio.doc.Text):
            processor = _InlineParser("\n".join(map(str, node.items)), link_resolver)
            node.items = processor.run()
        elif isinstance(node, yuio.doc.Container):
            for item in node.items:
                self._process_inline_text(item, link_resolver)

    def _process_block(self, parent: yuio.doc.Container[_t.Any], start: int, end: int):
        i = start
        prev_line_ending = _LineEnding.NORMAL

        while i < end:
            i, prev_line_ending = self._consume_block(parent, i, end, prev_line_ending)

        return parent

    def _consume_block(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        prev_line_ending: _LineEnding,
    ) -> tuple[int, _LineEnding]:
        if start >= end:  # pragma: no cover
            return start, prev_line_ending

        line = self._lines[start]

        if _is_blank(line):
            return start + 1, prev_line_ending

        result = None

        if prev_line_ending == _LineEnding.LITERAL_MARK and (
            line.startswith(" ") or line.startswith(_PUNCT)
        ):
            result = self._try_process_literal_text(parent, start, end)
        elif _is_heading_underline(self._lines, start, end):
            self._process_title(parent, line, self._lines[start + 1][0], False)
            result = start + 2
        elif _is_heading_overline(self._lines, start, end):
            self._process_title(parent, self._lines[start + 1], line[0], True)
            result = start + 3
        elif line.startswith(">>>"):
            result = self._process_doctest_block(parent, start, end)
        elif line.startswith(" "):
            result = self._process_block_quote(parent, start, end)
        elif match := _LINE_BLOCK_START_RE.match(line):
            result = self._process_line_block(parent, start, end, match)
        elif match := _BULLET_LIST_START_RE.match(line):
            result = self._process_bullet_list(parent, start, end, match)
        elif match := _NUM_LIST_START_RE.match(line):
            result = self._try_process_numbered_list(parent, start, end, match)
        elif match := _EXPLICIT_MARKUP_START_RE.match(line):
            result = self._try_process_explicit_markup(parent, start, end, match)
        elif match := _IMPLICIT_HYPERLINK_TARGET_RE.match(line):
            result = self._process_implicit_hyperlink_target(parent, start, end, match)
        elif match := _FIELD_START_RE.match(line):
            result = self._process_field_list(parent, start, end, match)
        elif (
            start + 1 < end
            and self._lines[start + 1].startswith(" ")
            and not _is_blank(self._lines[start + 1])
        ):
            result = self._process_def_list(parent, start, end)

        if result is None:
            return self._process_paragraph(parent, start, end)
        else:
            return result, _LineEnding.NORMAL

    def _process_title(
        self,
        parent: yuio.doc.Container[_t.Any],
        title: str,
        marker: str,
        is_overline: bool,
    ):
        if level := self._headings.get((marker, is_overline)):
            parent.items.append(yuio.doc.Heading(items=[title.strip()], level=level))
        else:
            level = len(self._headings) + 1
            self._headings[(marker, is_overline)] = level
            parent.items.append(yuio.doc.Heading(items=[title.strip()], level=level))

    def _try_process_literal_text(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int
    ) -> int | None:
        ch = self._lines[start][0]

        if ch.isspace():
            end = self._gather_indented_lines(start, end, True)
        elif ch in _PUNCT:
            end = self._gather_prefixed_lines(start, end, ch)
        else:  # pragma: no cover
            return None

        node = yuio.doc.Code(lines=[], syntax="text")
        for i in range(start, end):
            node.lines.append(self._lines[i])
        parent.items.append(node)

        return end

    def _process_line_block(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        match: _tx.StrReMatch | None,
    ) -> int | None:
        block_end = start + 1
        lines = []
        while match:
            self._lines[start] = match["tail"]
            block_end = self._gather_indented_lines(start + 1, end, False)
            lines.append(" ".join(self._lines[start:block_end]))

            start = block_end
            if start >= end:
                match = None
            else:
                match = _LINE_BLOCK_START_RE.match(self._lines[start])

        node = yuio.doc.Paragraph(items=["\v".join(lines)])
        parent.items.append(node)
        return block_end

    def _process_bullet_list(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        match: _tx.StrReMatch,
    ) -> int:
        if (
            parent.items
            and isinstance(parent.items[-1], yuio.doc.List)
            and parent.items[-1].items
        ):
            list_node = parent.items[-1]
            prev_enumerator_kind = list_node.enumerator_kind
            prev_marker_kind = list_node.marker_kind
            prev_num = list_node.items[-1].number
        else:
            list_node = None
            prev_enumerator_kind = None
            prev_marker_kind = None
            prev_num = None

        enumerator_kind = match["enumerator"]
        marker_kind = None
        num = None

        if (
            enumerator_kind != prev_enumerator_kind
            or marker_kind != prev_marker_kind
            or (prev_num is not None)
        ):
            list_node = None

        if list_node is None:
            list_node = yuio.doc.List(
                items=[], enumerator_kind=enumerator_kind, marker_kind=marker_kind
            )
            parent.items.append(list_node)

        self._lines[start] = match["tail"]
        if not match["space"]:
            end = self._gather_indented_lines(start + 1, end, True)
        else:
            indent = len(match["indent"])
            end = self._gather_exactly_indented_lines(start + 1, end, indent, True)

        node = yuio.doc.ListItem(items=[], number=num)
        self._process_block(node, start, end)
        list_node.items.append(node)
        return end

    def _try_process_numbered_list(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        match: _tx.StrReMatch,
    ) -> int | None:
        if (
            parent.items
            and isinstance(parent.items[-1], yuio.doc.List)
            and parent.items[-1].items
        ):
            list_node = parent.items[-1]
            prev_enumerator_kind = list_node.enumerator_kind
            prev_marker_kind = list_node.marker_kind
            prev_num = list_node.items[-1].number
        else:
            list_node = None
            prev_enumerator_kind = None
            prev_marker_kind = None
            prev_num = None

        list_data = _detect_num_list_type(
            match,
            prev_enumerator_kind,
            prev_marker_kind,
            prev_num,
        )

        if list_data is None:
            return None  # TODO: this is not covered, I don't know why

        enumerator_kind, marker_kind, num = list_data

        # Verify next line (if exists) is compatible
        if start + 1 < end:
            next_line = self._lines[start + 1]
            if not (
                not next_line
                or next_line.startswith(" ")
                or _is_list_start(next_line, enumerator_kind, marker_kind, num)
            ):
                return None

        if (
            enumerator_kind != prev_enumerator_kind
            or marker_kind != prev_marker_kind
            or (prev_num is None or num != prev_num + 1)
        ):
            list_node = None

        if list_node is None:
            list_node = yuio.doc.List(
                items=[], enumerator_kind=enumerator_kind, marker_kind=marker_kind
            )
            parent.items.append(list_node)

        self._lines[start] = match["tail"]
        if not match["space"]:
            end = self._gather_indented_lines(start + 1, end, True)
        else:
            indent = len(match["indent"])
            end = self._gather_exactly_indented_lines(start + 1, end, indent, True)

        node = yuio.doc.ListItem(items=[], number=num)
        self._process_block(node, start, end)
        list_node.items.append(node)
        return end

    def _process_doctest_block(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int
    ) -> int | None:
        node = yuio.doc.Code(lines=[], syntax="python")

        block_end = 0
        for i in range(start, end):
            line = self._lines[i]
            if _is_blank(line):
                break
            node.lines.append(line)
            block_end = i + 1

        parent.items.append(node)
        return block_end

    def _try_process_explicit_markup(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        match: _tx.StrReMatch,
    ) -> int | None:
        """Try to process explicit markup (directives, comments, etc.)."""
        content = match["tail"].strip()

        if not content:
            start += 1
            if start < end and not _is_blank(self._lines[start]):
                return self._gather_indented_lines(start + 1, end, True)
            else:
                return start

        if content.startswith("["):
            return self._parse_footnote(parent, start, end, content)

        if content.startswith("|"):
            # TODO: save substitution
            return self._gather_indented_lines(start + 1, end, False)

        if content.startswith("_"):
            return self._parse_hyperlink_target(start, end, content)

        # Directive
        if "::" in content:
            return self._parse_directive(parent, start, end, content)

        # Default to comment
        return self._gather_indented_lines(start + 1, end, True)

    def _parse_hyperlink_target(self, start: int, end: int, content: str):
        end = self._gather_indented_lines(start + 1, end, False)
        content += "\n".join(self._lines[start + 1 : end])
        anchor, _, target = content[1:].partition(":")
        anchor = _normalize_hyperlink_anchor(anchor)
        target, is_redirect = _normalize_hyperlink_target(target)
        self._add_link(
            _Hyperlink(
                start,
                end,
                anchor,
                "redirect" if is_redirect else "link",
                target,
            )
        )
        return end

    def _parse_footnote(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int, content: str
    ):
        end = self._gather_indented_lines(start + 1, end, True)
        name, _, content = content[1:].partition("]")
        self._lines[start] = content.strip()

        if name.startswith("#"):
            name = name[1:]
            while True:
                auto_name = str(self._last_numbered_footnote)
                self._last_numbered_footnote += 1
                if auto_name not in self._targets:
                    break
            if not name:
                self._auto_numbered_footnotes.append(auto_name)
        elif name.startswith("*"):
            name = name[1:]
            while True:
                auto_name = _char_footnote(self._last_character_footnote)
                self._last_character_footnote += 1
                if auto_name not in self._targets:
                    break
            if not name:
                self._auto_character_footnotes.append(auto_name)
        else:
            auto_name = name

        link = _Hyperlink(start, end, auto_name, "footnote", auto_name)
        self._add_link(link)
        if name and name not in self._targets:
            self._targets[name] = link

        if parent.items and isinstance(parent.items[-1], yuio.doc.FootnoteContainer):
            container = parent.items[-1]
        else:
            container = yuio.doc.FootnoteContainer(items=[])
            parent.items.append(container)

        node = yuio.doc.Footnote(
            items=[],
            marker=auto_name,
        )
        self._process_block(node, start, end)
        container.items.append(node)

        return end

    def _add_link(self, link: _Hyperlink):
        if link.content:
            start = link.start
            for prev_link in reversed(self._links):
                if prev_link.content:
                    break
                if not (
                    prev_link.end == start
                    or all(
                        _is_blank(line) for line in self._lines[prev_link.end : start]
                    )
                ):
                    break
                prev_link.type = link.type
                prev_link.content = link.content
                start = prev_link.start
        self._links.append(link)
        if link.name == "_":
            self._anonymous_links.append(link)
        elif link.name not in self._targets:
            self._targets[link.name] = link

    def _parse_directive(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int, content: str
    ) -> int:
        name, _, arg = content.partition("::")
        name = name.strip()
        arg = arg.strip()

        end = self._gather_indented_lines(start + 1, end, True)

        i = start + 1

        # Parse arguments and options.
        while i < end:
            arg_line = self._lines[i]
            i += 1
            if _is_blank(arg_line):
                break

        parent.items.extend(
            yuio.doc._process_directive(
                name,
                arg,
                lambda: self._lines[i:end],
                lambda: self._process_block(yuio.doc.Document(items=[]), i, end).items,
            )
        )

        return end

    def _process_block_quote(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int
    ) -> int:
        end = self._gather_indented_lines(start, end, True)
        node = yuio.doc.Quote(items=[])
        self._process_block(node, start, end)
        parent.items.append(node)
        return end

    def _process_implicit_hyperlink_target(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        match: _tx.StrReMatch,
    ) -> int:
        return self._parse_hyperlink_target(start, end, f"__: {match.group('tail')}")

    def _process_field_list(
        self,
        parent: yuio.doc.Container[_t.Any],
        start: int,
        end: int,
        match: _tx.StrReMatch,
    ) -> int:
        self._lines[start] = match["tail"]
        end = self._gather_indented_lines(start + 1, end, True)
        node = yuio.doc.Admonition(
            items=[],
            title=[match["content"].strip() + "\\ :"],
            type="field",
        )
        self._process_block(node, start, end)
        parent.items.append(node)
        return end

    def _process_def_list(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int
    ) -> int:
        end = self._gather_indented_lines(start + 1, end, True)
        node = yuio.doc.Admonition(
            items=[],
            title=[self._lines[start].strip()],
            type="definition",
        )
        self._process_block(node, start + 1, end)
        parent.items.append(node)
        return end

    def _process_paragraph(
        self, parent: yuio.doc.Container[_t.Any], start: int, end: int
    ) -> tuple[int, _LineEnding]:
        end = self._gather_exactly_indented_lines(start, end, 0, False)
        if end == start + 1 and self._lines[start].strip() == "::":
            return end, _LineEnding.LITERAL_MARK
        elif end == start + 1 and _is_transition(self._lines[start]):
            parent.items.append(yuio.doc.ThematicBreak())
            return end, _LineEnding.NORMAL
        elif end > start and self._lines[end - 1].rstrip().endswith("::"):
            line_ending = _LineEnding.LITERAL_MARK
            self._lines[end - 1] = self._lines[end - 1].rstrip()[:-1]
        else:
            line_ending = _LineEnding.NORMAL
        node = yuio.doc.Paragraph(
            items=_t.cast(list[str | yuio.doc.TextRegion], self._lines[start:end])
        )
        parent.items.append(node)
        return end, line_ending

    def _gather_indented_lines(self, start: int, end: int, allow_blank: bool) -> int:
        if start >= end:
            return start

        common_indent = None
        result_end = start

        for i in range(start, end):
            line = self._lines[i]
            if _is_blank(line):
                if allow_blank:
                    continue
                else:
                    break

            indent = len(line) - len(line.lstrip())
            if indent >= 1:
                result_end = i + 1
                if common_indent is None:
                    common_indent = indent
                else:
                    common_indent = min(common_indent, indent)
            else:
                break

        if common_indent:
            for i in range(start, result_end):
                self._lines[i] = self._lines[i][common_indent:]

        return result_end

    def _gather_exactly_indented_lines(
        self, start: int, end: int, min_indent: int, allow_blank: bool
    ) -> int:
        result_end = start

        for i in range(start, end):
            line = self._lines[i]
            if _is_blank(line):
                if allow_blank:
                    continue
                else:
                    break

            if not min_indent:
                result_end = i + 1
            elif len(line) - len(line.lstrip()) >= min_indent:
                result_end = i + 1
                self._lines[i] = self._lines[i][min_indent:]
            else:
                break

        return result_end

    def _gather_prefixed_lines(self, start: int, end: int, prefix: str) -> int:
        result_end = start

        for i in range(start, end):
            if self._lines[i] and self._lines[i][0] == prefix:
                result_end = i + 1
            else:
                break

        return result_end


def _is_blank(line: str) -> bool:
    return not line or line.isspace()


def _is_transition(line: str) -> bool:
    return len(line) >= 4 and line[0] in _PUNCT and all(c == line[0] for c in line)


def _is_heading_underline(lines, start, end):
    if end - start < 2:
        return False
    title, underline = lines[start : start + 2]
    return (
        title
        and not title.startswith(" ")
        and underline
        and underline[0] in _PUNCT
        and all(c == underline[0] for c in underline)
        and len(title) <= len(underline)
    )


def _is_heading_overline(lines, start, end):
    if end - start < 3:
        return False
    overline, title, underline = lines[start : start + 3]
    return (
        overline
        and title
        and underline
        and overline[0] in _PUNCT
        and overline[0] == underline[0]
        and all(c == overline[0] for c in overline)
        and len(title) <= len(overline)
        and all(c == underline[0] for c in underline)
        and len(title) <= len(underline)
    )


# fmt: off
# The following code is copied from docutils/utils/punctuation_chars.py
# Copyright 2011, 2017 Günter Milde, 2-Clause BSD license.
# See https://sourceforge.net/p/docutils/code/HEAD/tree/trunk/docutils/docutils/utils/punctuation_chars.py.
# See https://opensource.org/license/BSD-2-Clause.
_OPENERS = (
    "\"'(<\\[{\u0f3a\u0f3c\u169b\u2045\u207d\u208d\u2329\u2768"
    "\u276a\u276c\u276e\u2770\u2772\u2774\u27c5\u27e6\u27e8\u27ea"
    "\u27ec\u27ee\u2983\u2985\u2987\u2989\u298b\u298d\u298f\u2991"
    "\u2993\u2995\u2997\u29d8\u29da\u29fc\u2e22\u2e24\u2e26\u2e28"
    "\u3008\u300a\u300c\u300e\u3010\u3014\u3016\u3018\u301a\u301d"
    "\u301d\ufd3e\ufe17\ufe35\ufe37\ufe39\ufe3b\ufe3d\ufe3f\ufe41"
    "\ufe43\ufe47\ufe59\ufe5b\ufe5d\uff08\uff3b\uff5b\uff5f\uff62"
    "\xab\u2018\u201c\u2039\u2e02\u2e04\u2e09\u2e0c\u2e1c\u2e20"
    "\u201a\u201e\xbb\u2019\u201d\u203a\u2e03\u2e05\u2e0a\u2e0d"
    "\u2e1d\u2e21\u201b\u201f"
)
_CLOSERS = (
    "\"')>\\]}\u0f3b\u0f3d\u169c\u2046\u207e\u208e\u232a\u2769"
    "\u276b\u276d\u276f\u2771\u2773\u2775\u27c6\u27e7\u27e9\u27eb"
    "\u27ed\u27ef\u2984\u2986\u2988\u298a\u298c\u298e\u2990\u2992"
    "\u2994\u2996\u2998\u29d9\u29db\u29fd\u2e23\u2e25\u2e27\u2e29"
    "\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\u301e"
    "\u301f\ufd3f\ufe18\ufe36\ufe38\ufe3a\ufe3c\ufe3e\ufe40\ufe42"
    "\ufe44\ufe48\ufe5a\ufe5c\ufe5e\uff09\uff3d\uff5d\uff60\uff63"
    "\xbb\u2019\u201d\u203a\u2e03\u2e05\u2e0a\u2e0d\u2e1d\u2e21"
    "\u201b\u201f\xab\u2018\u201c\u2039\u2e02\u2e04\u2e09\u2e0c"
    "\u2e1c\u2e20\u201a\u201e"
)
_DELIMITERS = (
    "\\-/:\u058a\xa1\xb7\xbf\u037e\u0387\u055a-\u055f\u0589"
    "\u05be\u05c0\u05c3\u05c6\u05f3\u05f4\u0609\u060a\u060c"
    "\u060d\u061b\u061e\u061f\u066a-\u066d\u06d4\u0700-\u070d"
    "\u07f7-\u07f9\u0830-\u083e\u0964\u0965\u0970\u0df4\u0e4f"
    "\u0e5a\u0e5b\u0f04-\u0f12\u0f85\u0fd0-\u0fd4\u104a-\u104f"
    "\u10fb\u1361-\u1368\u1400\u166d\u166e\u16eb-\u16ed\u1735"
    "\u1736\u17d4-\u17d6\u17d8-\u17da\u1800-\u180a\u1944\u1945"
    "\u19de\u19df\u1a1e\u1a1f\u1aa0-\u1aa6\u1aa8-\u1aad\u1b5a-"
    "\u1b60\u1c3b-\u1c3f\u1c7e\u1c7f\u1cd3\u2010-\u2017\u2020-"
    "\u2027\u2030-\u2038\u203b-\u203e\u2041-\u2043\u2047-"
    "\u2051\u2053\u2055-\u205e\u2cf9-\u2cfc\u2cfe\u2cff\u2e00"
    "\u2e01\u2e06-\u2e08\u2e0b\u2e0e-\u2e1b\u2e1e\u2e1f\u2e2a-"
    "\u2e2e\u2e30\u2e31\u3001-\u3003\u301c\u3030\u303d\u30a0"
    "\u30fb\ua4fe\ua4ff\ua60d-\ua60f\ua673\ua67e\ua6f2-\ua6f7"
    "\ua874-\ua877\ua8ce\ua8cf\ua8f8-\ua8fa\ua92e\ua92f\ua95f"
    "\ua9c1-\ua9cd\ua9de\ua9df\uaa5c-\uaa5f\uaade\uaadf\uabeb"
    "\ufe10-\ufe16\ufe19\ufe30-\ufe32\ufe45\ufe46\ufe49-\ufe4c"
    "\ufe50-\ufe52\ufe54-\ufe58\ufe5f-\ufe61\ufe63\ufe68\ufe6a"
    "\ufe6b\uff01-\uff03\uff05-\uff07\uff0a\uff0c-\uff0f\uff1a"
    "\uff1b\uff1f\uff20\uff3c\uff61\uff64\uff65"
    "\U00010100\U00010101\U0001039f\U000103d0\U00010857"
    "\U0001091f\U0001093f\U00010a50-\U00010a58\U00010a7f"
    "\U00010b39-\U00010b3f\U000110bb\U000110bc\U000110be-"
    "\U000110c1\U00012470-\U00012473"
)
_CLOSING_DELIMITERS = r"\\.,;!?"
_QUOTE_PAIRS = {
    # open char: matching closing characters # use case
    "\xbb": "\xbb",  # » » Swedish
    "\u2018": "\u201a",  # ‘ ‚ Albanian/Greek/Turkish
    "\u2019": "\u2019",  # ’ ’ Swedish
    "\u201a": "\u2018\u2019",  # ‚ ‘ German, ‚ ’ Polish
    "\u201c": "\u201e",  # “ „ Albanian/Greek/Turkish
    "\u201e": "\u201c\u201d",  # „ “ German, „ ” Polish
    "\u201d": "\u201d",  # ” ” Swedish
    "\u203a": "\u203a",  # › › Swedish
}
def _match_chars(c1, c2):
    try:
        i = _OPENERS.index(c1)
    except ValueError:  # c1 not in openers
        return False
    return c2 == _CLOSERS[i] or c2 in _QUOTE_PAIRS.get(c1, "")
# End docutils code.
# fmt: on

_OPENERS_RE = re.compile(rf"[{_OPENERS}{_DELIMITERS}]")
_CLOSERS_RE = re.compile(rf"[{_CLOSERS}{_DELIMITERS}{_CLOSING_DELIMITERS}]")


def _is_start_string(prev: str, next: str) -> bool:
    if next.isspace():
        return False
    if prev.isspace():
        return True
    if _match_chars(prev, next):
        return False
    # if character_level_inline_markup:
    #     return True
    return _OPENERS_RE.match(prev) is not None


def _is_end_string(prev: str, next: str) -> bool:
    if prev.isspace():
        return False
    if next.isspace():
        return True
    if _match_chars(prev, next):
        return False
    # if character_level_inline_markup:
    #     return True
    return _CLOSERS_RE.match(next) is not None


def _detect_num_list_type(
    match: _tx.StrReMatch,
    prev_enumerator_kind: yuio.doc.ListEnumeratorKind | str | None,
    prev_marker_kind: yuio.doc.ListMarkerKind | None,
    prev_num: int | None,
) -> tuple[yuio.doc.ListEnumeratorKind, yuio.doc.ListMarkerKind, int] | None:
    match (match["open_marker"], match["close_marker"]):
        case ("(", ")"):
            marker_kind = yuio.doc.ListMarkerKind.ENCLOSED
        case ("", ")"):
            marker_kind = yuio.doc.ListMarkerKind.PAREN
        case ("", "."):
            marker_kind = yuio.doc.ListMarkerKind.DOT
        case _:
            return None

    if (
        prev_enumerator_kind is not None
        and prev_marker_kind is not None
        and prev_num is not None
        and marker_kind == prev_marker_kind
        and isinstance(prev_enumerator_kind, yuio.doc.ListEnumeratorKind)
    ):
        # List continues.
        if match["enumerator"] == "#":
            return prev_enumerator_kind, prev_marker_kind, prev_num + 1
        match prev_enumerator_kind:
            case yuio.doc.ListEnumeratorKind.NUMBER:
                expected_enumerator = str(prev_num + 1)
            case yuio.doc.ListEnumeratorKind.SMALL_LETTER:
                expected_enumerator = yuio.doc.to_letters(prev_num + 1)
            case yuio.doc.ListEnumeratorKind.CAPITAL_LETTER:
                expected_enumerator = yuio.doc.to_letters(prev_num + 1).upper()
            case yuio.doc.ListEnumeratorKind.SMALL_ROMAN:
                expected_enumerator = yuio.doc.to_roman(prev_num + 1)
            case yuio.doc.ListEnumeratorKind.CAPITAL_ROMAN:
                expected_enumerator = yuio.doc.to_roman(prev_num + 1).upper()
        if match["enumerator"].lstrip("0") == expected_enumerator:
            return prev_enumerator_kind, prev_marker_kind, prev_num + 1

    # List starts afresh.
    if enumerator := match["enumerator_num"]:
        return yuio.doc.ListEnumeratorKind.NUMBER, marker_kind, int(enumerator)
    elif enumerator := match["enumerator_auto"]:
        return yuio.doc.ListEnumeratorKind.NUMBER, marker_kind, 1
    elif enumerator := match["enumerator_lowercase"]:
        if (enumerator == "i" or len(enumerator) > 1) and (
            (num := yuio.doc.from_roman(enumerator)) is not None
        ):
            return yuio.doc.ListEnumeratorKind.SMALL_ROMAN, marker_kind, num
        elif len(enumerator) > 1:
            return None
        elif (num := yuio.doc.from_letters(enumerator)) is not None:
            return yuio.doc.ListEnumeratorKind.SMALL_LETTER, marker_kind, num
        else:
            return None
    elif enumerator := match["enumerator_uppercase"]:
        if (enumerator == "I" or len(enumerator) > 1) and (
            num := yuio.doc.from_roman(enumerator)
        ) is not None:
            return yuio.doc.ListEnumeratorKind.CAPITAL_ROMAN, marker_kind, num
        elif len(enumerator) > 1:
            return None
        elif (num := yuio.doc.from_letters(enumerator)) is not None:
            return yuio.doc.ListEnumeratorKind.CAPITAL_LETTER, marker_kind, num
        else:
            return None

    return None


def _is_list_start(
    line: str,
    prev_enumerator_kind: yuio.doc.ListEnumeratorKind | str,
    prev_marker_kind: yuio.doc.ListMarkerKind,
    prev_num: int,
):
    match = _NUM_LIST_START_RE.match(line)
    if not match:
        return False
    list_data = _detect_num_list_type(
        match, prev_enumerator_kind, prev_marker_kind, prev_num
    )
    if not list_data:
        return False
    enumerator_kind, marker_kind, num = list_data
    return (
        enumerator_kind == prev_enumerator_kind
        and marker_kind == prev_marker_kind
        and num == prev_num + 1
    )


def _normalize_hyperlink_anchor(anchor: str) -> str:
    return _unescape(re.sub(r"\s+", " ", anchor.strip()).casefold())


def _normalize_hyperlink_target(target: str) -> tuple[str, bool]:
    is_redirect = bool(re.match(r"^(\\.|[^\\])*_$", target))
    target = re.sub(r"\\(.)|\s", r"\1", target)
    if is_redirect:
        target = target[:-1]
    return target, is_redirect


def _unescape(text: str) -> str:
    return re.sub(r"\\(?:\s|(.))", r"\1", text)


@dataclass(slots=True)
class _Token:
    """
    Token for processing inline markup.

    """

    start: int
    end: int
    kind: str

    _data: dict[str, _t.Any] | None = dataclasses.field(init=False, default=None)

    @property
    def data(self):
        if self._data is None:
            self._data = {}
        return self._data


class _InlineParser:
    def __init__(self, text: str, link_resolver: _LinkResolver) -> None:
        self._text: str = text
        self._start: int = 0
        self._pos: int = 0
        self._tokens: list[_Token] = []
        self._link_resolver = link_resolver

    def run(self) -> list[str | yuio.doc.TextRegion]:
        while self._fits(self._pos):
            self._run()
        if self._start < len(self._text):
            self._tokens.append(_Token(self._start, len(self._text), "text"))

        res: list[str | yuio.doc.TextRegion] = []
        for token in self._tokens:
            text = _unescape(self._text[token.start : token.end])
            match token.kind:
                case "text":
                    res.append(text)
                case "em":
                    res.append(yuio.doc.HighlightedRegion(text, color="em"))
                case "strong":
                    res.append(yuio.doc.HighlightedRegion(text, color="strong"))
                case "formatted":
                    res.append(token.data["content"])
                case "link":
                    if title := token.data.get("title"):
                        text = _unescape(title)
                    res.append(yuio.doc.LinkRegion(text, url=token.data.get("url", "")))
                case "footnote":
                    if content := token.data.get("content"):
                        text = _unescape(content)
                    text = f"[{text}]"
                    res.append(
                        yuio.doc.NoWrapRegion(
                            yuio.doc.HighlightedRegion(text, color="role/footnote")
                        )
                    )
                case kind:
                    assert False, kind
        return res

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
        while self._pos < len(self._text) and self._text[self._pos] in ch:
            self._pos += 1

    def _eat_not_in(self, ch):
        while self._pos < len(self._text) and self._text[self._pos] not in ch:
            self._pos += 1

    def _emit(
        self,
        tok_start: int,
        content_start: int,
        content_end: int,
        token_end: int,
        kind: str,
    ):
        if tok_start > self._start:
            self._tokens.append(_Token(self._start, tok_start, "text"))
        assert token_end == self._pos  # sanity check
        self._start = self._pos
        token = _Token(content_start, content_end, kind)
        self._tokens.append(token)
        return token

    def _run(self):
        match self._text[self._pos]:
            case "\\":
                self._pos += 2
            case "`":
                if self._ch_eq(self._pos + 1, "`"):
                    self._parse_inline_literal()
                else:
                    self._parse_interpreted_text(
                        prefix_role=None, prefix_role_start=None
                    )
            case ":":
                self._parse_prefixed_interpreted_text()
            case "*":
                if self._ch_eq(self._pos + 1, "*"):
                    self._parse_strong()
                else:
                    self._parse_emphasis()
            case "|":
                self._parse_substitution()
            case "_":
                if self._ch_eq(self._pos + 1, "`"):
                    self._parse_inline_internal_target()
                else:
                    self._parse_unquoted_link()
            case "[":
                self._parse_footnote_reference()
            case _:
                self._eat_not_in("\\`:*|_[")

    def _scan_for_explicit_role(self) -> str | None:
        """
        Eat explicit role, leaving current position right after it. If explicit role
        can't be found, returns None and leaves current position untouched::

            text :role:`ref`
                 │     └ position if this function succeeds
                 └ initial position

            text :malformed-role
                 │
                 └ initial position, position if this function fails

        """

        if not self._ch_eq(self._pos, ":"):  # pragma: no cover
            return None

        token_start = self._pos
        self._pos += 1
        content_start = self._pos

        while self._fits(self._pos):
            match self._text[self._pos]:
                case ch if ch.isalnum():
                    self._pos += 1
                case ":":
                    if self._ch_at(self._pos + 1).isalnum():
                        # Isolated punctuation.
                        self._pos += 1
                        continue

                    content_end = self._pos
                    self._pos += 1

                    if content_start == content_end:
                        # Empty content is not allowed.
                        break

                    return self._text[content_start:content_end]
                case ch if ch in "-_+:," and not self._ch_in(self._pos + 1, "-_+:,"):
                    # Isolated punctuation.
                    self._pos += 1
                case _:
                    break

        self._pos = token_start  # Leave position as it was before.
        return None

    def _parse_inline_literal(self):
        """
        Eats and emits inline literal. If inline literal can't be parsed, advances
        current position one char and returns::

            text ``literal``
                 │          └ position if this function succeeds
                 └ initial position

            text ``literal
                 │└ position if this function fails
                 └ initial position

        """

        assert self._ch_eq(self._pos, "`")
        assert self._ch_eq(self._pos + 1, "`")

        token_start = self._pos
        self._pos += 2
        content_start = self._pos

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            match self._text[self._pos]:
                case "`" if self._ch_eq(self._pos + 1, "`"):
                    content_end = self._pos
                    self._pos += 2
                    token_end = self._pos

                    prev_char = self._ch_at(content_end - 1)
                    next_char = self._ch_at(token_end)
                    if not _is_end_string(prev_char, next_char):
                        self._pos = content_end + 1  # Skip 1 char and continue.
                        continue

                    if content_start == content_end:
                        # Empty content is not allowed.
                        break

                    token = self._emit(
                        token_start, content_start, content_end, token_end, "formatted"
                    )
                    token.data["content"] = yuio.doc._process_role(
                        self._text[content_start:content_end], "code"
                    )
                    return
                case _:
                    self._pos += 1

        self._pos = content_start + 1

    def _parse_interpreted_text(
        self, prefix_role: str | None, prefix_role_start: int | None
    ):
        """
        Eats and emits interpreted text and its tail role or hyperlink marker.
        If interpreted text can't be parsed, advances current position one char
        and returns::

            text `ref`
                 │    └ position if this function succeeds
                 └ initial position

            text `ref
                 │└ position if this function fails
                 └ initial position

            text :role:`ref`
                 │     │    └ position if this function succeeds
                 │     └ initial position
                 └ prefix_role_start

            text :role:`ref
                 ││    └ initial position
                 │└ position if this function fails
                 └ prefix_role_start

        """

        assert self._ch_eq(self._pos, "`")

        if prefix_role_start is None:
            prefix_role_start = self._pos

        token_start = prefix_role_start
        self._pos += 1
        content_start = self._pos

        # TODO: are these correct bounds?
        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(token_start + 1)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            if self._ch_eq(self._pos, "`"):
                content_end = self._pos
                self._pos += 1
                if self._ch_eq(self._pos, "_"):
                    n_underscores = self._eat("_")
                    suffix_role = None
                elif self._ch_eq(self._pos, ":"):
                    suffix_role = self._scan_for_explicit_role()
                    n_underscores = 0
                else:
                    suffix_role = None
                    n_underscores = 0
                token_end = self._pos

                # TODO: are these correct bounds?
                prev_char = self._ch_at(content_end - 1)
                next_char = self._ch_at(token_end)
                if not _is_end_string(prev_char, next_char):
                    self._pos = content_end + 1
                    continue

                if content_start == content_end:
                    # Empty content is not allowed.
                    break

                if n_underscores > 2:
                    # Too many underscores.
                    break

                if bool(n_underscores) + bool(prefix_role) + bool(suffix_role) > 1:
                    # Malformed interpreted text, just skip it as-is.
                    return

                if n_underscores:
                    target, title = yuio.doc._process_link(
                        self._text[content_start:content_end],
                    )
                    link = self._link_resolver.find_link(
                        title, target, is_anonymous=n_underscores == 2
                    )
                    if link and link.type == "link":
                        target = link.content
                    else:
                        target = None
                    token = self._emit(
                        token_start, content_start, content_end, token_end, "link"
                    )
                    token.data["url"] = target
                    token.data["title"] = title
                else:
                    token = self._emit(
                        token_start, content_start, content_end, token_end, "formatted"
                    )
                    token.data["content"] = yuio.doc._process_role(
                        self._text[content_start:content_end],
                        prefix_role or suffix_role or "literal",
                    )
                return
            elif self._ch_eq(self._pos, "\\"):
                self._pos += 2
            else:
                self._pos += 1

        self._pos = content_start + 1

    def _parse_prefixed_interpreted_text(self):
        assert self._ch_eq(self._pos, ":")

        token_start = self._pos
        role = self._scan_for_explicit_role()
        if role and self._ch_eq(self._pos, "`"):
            self._parse_interpreted_text(role, token_start)
        else:
            self._pos = token_start + 1

    def _parse_emphasis(self):
        assert self._ch_eq(self._pos, "*")

        token_start = self._pos
        self._pos += 1
        content_start = self._pos

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            if self._ch_eq(self._pos, "*"):
                content_end = self._pos
                self._pos += 1
                token_end = self._pos

                prev_char = self._ch_at(content_end - 1)
                next_char = self._ch_at(token_end)
                if not _is_end_string(prev_char, next_char):
                    self._pos = content_end + 1
                    continue

                if content_start == content_end:
                    # Empty content is not allowed.
                    break

                self._emit(token_start, content_start, content_end, token_end, "em")
                return
            elif self._ch_eq(self._pos, "\\"):
                self._pos += 2
            else:
                self._pos += 1

        self._pos = content_start + 1

    def _parse_strong(self):
        assert self._ch_eq(self._pos, "*")
        assert self._ch_eq(self._pos + 1, "*")

        token_start = self._pos
        self._pos += 2
        content_start = self._pos

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            if self._ch_eq(self._pos, "*") and self._ch_eq(self._pos + 1, "*"):
                content_end = self._pos
                self._pos += 2
                token_end = self._pos

                prev_char = self._ch_at(content_end - 1)
                next_char = self._ch_at(token_end)
                if not _is_end_string(prev_char, next_char):
                    self._pos = content_end + 1
                    continue

                if content_start == content_end:
                    # Empty content is not allowed.
                    break

                self._emit(token_start, content_start, content_end, token_end, "strong")
                return
            elif self._ch_eq(self._pos, "\\"):
                self._pos += 2
            else:
                self._pos += 1

        self._pos = content_start + 1

    def _parse_substitution(self):
        assert self._ch_eq(self._pos, "|")

        token_start = self._pos
        self._pos += 1
        content_start = self._pos

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            if self._ch_eq(self._pos, "|"):
                content_end = self._pos
                self._pos += 1
                token_end = self._pos

                prev_char = self._ch_at(content_end - 1)
                next_char = self._ch_at(token_end)
                if not _is_end_string(prev_char, next_char):
                    self._pos = content_end + 1
                    continue

                if content_start == content_end:
                    # Empty content is not allowed.
                    break

                # TODO: actually substitute things.
                self._emit(token_start, content_start, content_end, token_end, "text")
                return
            elif self._ch_eq(self._pos, "\\"):
                self._pos += 2
            else:
                self._pos += 1

        self._pos = content_start + 1

    def _parse_inline_internal_target(self):
        assert self._ch_eq(self._pos, "_")
        assert self._ch_eq(self._pos + 1, "`")

        token_start = self._pos
        self._pos += 2
        content_start = self._pos

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            if self._ch_eq(self._pos, "`"):
                content_end = self._pos
                self._pos += 1
                token_end = self._pos

                prev_char = self._ch_at(content_end - 1)
                next_char = self._ch_at(token_end)
                if not _is_end_string(prev_char, next_char):
                    self._pos = content_end + 1
                    continue

                if content_start == content_end:
                    # Empty content is not allowed.
                    break

                self._emit(token_start, content_start, content_end, token_end, "text")
                return
            elif self._ch_eq(self._pos, "\\"):
                self._pos += 2
            else:
                self._pos += 1

        self._pos = content_start + 1

    def _parse_footnote_reference(self):
        assert self._ch_eq(self._pos, "[")

        token_start = self._pos
        self._pos += 1
        content_start = self._pos

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            self._pos = content_start + 1
            return

        while self._fits(self._pos):
            if self._ch_eq(self._pos, "]") and self._ch_eq(self._pos + 1, "_"):
                content_end = self._pos
                self._pos += 2
                token_end = self._pos

                prev_char = self._ch_at(content_end - 1)
                next_char = self._ch_at(token_end)
                if not _is_end_string(prev_char, next_char):
                    self._pos = content_end + 1
                    continue

                if content_start == content_end:
                    # Empty content is not allowed.
                    break

                target = self._link_resolver.find_link(
                    self._text[content_start:content_end],
                    None,
                    is_anonymous=False,
                )
                if target and target.type == "footnote":
                    content = target.content
                else:
                    content = None
                token = self._emit(
                    token_start, content_start, content_end, token_end, "footnote"
                )
                token.data["content"] = content
                return
            elif self._ch_eq(self._pos, "\\"):
                self._pos += 2
            else:
                self._pos += 1

        self._pos = content_start + 1

    def _parse_unquoted_link(self):
        content_end = self._pos
        n_underscores = self._eat("_")
        token_end = self._pos

        assert n_underscores > 0

        if n_underscores > 2:
            return

        prev_char = self._ch_at(content_end - 1)
        next_char = self._ch_at(token_end)
        if not _is_end_string(prev_char, next_char):
            return

        # Can be a link without backticks. Scan back to find its start.
        content_start = content_end
        while content_start - 1 >= self._start:
            match self._text[content_start - 1]:
                case ch if ch.isalnum():
                    content_start -= 1
                case ch if ch in "-_+:," and not self._ch_in(
                    content_start - 2, "-_+:,"
                ):
                    # Isolated punctuation.
                    content_start -= 1
                case _:
                    break

        # Start string is empty as per RST spec.
        token_start = content_start

        prev_char = self._ch_at(token_start - 1)
        next_char = self._ch_at(content_start)
        if not _is_start_string(prev_char, next_char):
            return

        if content_start == content_end:
            return

        title = self._text[content_start:content_end]
        target = self._link_resolver.find_link(
            title,
            None,
            is_anonymous=n_underscores == 2,
        )
        if target and target.type == "link":
            url = target.content
        else:
            url = None
        token = self._emit(token_start, content_start, content_end, token_end, "link")
        token.data["url"] = url
        token.data["title"] = title


def parse(text: str, /, *, dedent: bool = True) -> yuio.doc.Document:
    """
    Parse a ReStructuredText document and return an AST node.

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

    return RstParser().parse(text)
