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


Highlighting code
-----------------

Yuio supports basic code highlighting; it is just enough to format help messages
for CLI, and color tracebacks when an error occurs.

.. autoclass:: SyntaxHighlighter
   :members:


Markdown AST
------------

.. warning::

   This is an experimental API which can change within a minor release.

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

import abc
import contextlib
import dataclasses
import math
import os
import re
import shutil
import string
import textwrap
from dataclasses import dataclass

import yuio.term
import yuio.theme
from yuio import _t
from yuio.term import Color
from yuio.theme import Theme

T = _t.TypeVar("T")
TAst = _t.TypeVar("TAst", bound="AstBase")


@_t.final
class MdFormatter:
    """A simple markdown formatter suitable for displaying reach text in the terminal.

    All CommonMark block markup is supported:

    - headings:

      .. code-block:: markdown

         # Heading 1
         ## Heading 2

      Yuio has only two levels of headings. Headings past level two will look the same
      as level two headings (you can adjust theme to change this).

      If `allow_headings` is set to false, headings look like paragraphs.

    - lists, numbered lists, quotes:

      .. code-block:: markdown

         -  List item 1,
         -  list item 2.

         1. Numbered list item 1,
         1. numbered list item 2.

         > Quoted text.

    - fenced code blocks with minimal syntax highlighting
      (see :class:`SyntaxHighlighter`):

      .. code-block:: markdown

         ```python
         for i in range(5, 8):
             print(
                f"Hello, world! "
                "This is {i}th day past the apocalypse."
            )
         ```

      Yuio supports ``python``, ``traceback``, and ``bash`` syntaxes.

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
        theme: Theme,
        *,
        width: _t.Optional[int] = None,
        allow_headings: bool = True,
    ):
        self.width = width
        self.theme: Theme = theme
        self.allow_headings: bool = allow_headings

        self._is_first_line: bool
        self._out: yuio.term.ColorizedString
        self._first_line_indent: yuio.term.ColorizedString
        self._continuation_indent: yuio.term.ColorizedString

    @property
    def width(self) -> int:
        """Target width for soft-wrapping text."""

        return self.__width

    @width.setter
    def width(self, width: _t.Optional[int]):
        if width is None:
            width = min(shutil.get_terminal_size().columns, 90)
        self.__width = max(width, 30)

    def format(self, s: str, /) -> yuio.term.ColorizedString:
        """Format a markdown document."""

        return self.format_node(self.parse(s))

    def parse(self, s: str, /) -> "AstBase":
        """Parse a markdown document and return an AST node.

        .. warning::

           This is an experimental API which can change within a minor release.

        """

        return _MdParser(self.allow_headings).parse(self._dedent(s))

    def format_node(self, node: "AstBase", /) -> yuio.term.ColorizedString:
        """Format a parsed markdown document.

        .. warning::

           This is an experimental API which can change within a minor release.

        """

        self._is_first_line = True
        self._out = yuio.term.ColorizedString()
        self._first_line_indent = yuio.term.ColorizedString()
        self._continuation_indent = yuio.term.ColorizedString()

        self._format(node)
        self._out += Color.NONE

        return self._out

    def colorize(
        self,
        s: str,
        /,
        *,
        default_color: _t.Union[Color, str] = Color.NONE,
    ):
        """Parse and colorize contents of a paragraph.

        Apply ``default_color`` to the entire paragraph, and process color tags
        and backticks within it.

        """

        return _colorize(self.theme, s, default_color=default_color)

    @contextlib.contextmanager
    def _indent(
        self,
        color: _t.Union[Color, str, None],
        s: yuio.term.AnyString,
        /,
        *,
        continue_with_spaces: bool = True,
    ):
        color = self.theme.to_color(color)
        indent = yuio.term.ColorizedString(color) + s

        old_first_line_indent = self._first_line_indent
        old_continuation_indent = self._continuation_indent

        if continue_with_spaces:
            continuation_indent = yuio.term.ColorizedString(" " * indent.width)
        else:
            continuation_indent = indent

        self._first_line_indent = self._first_line_indent + indent
        self._continuation_indent = self._continuation_indent + continuation_indent

        try:
            yield
        finally:
            self._first_line_indent = old_first_line_indent
            self._continuation_indent = old_continuation_indent

    @staticmethod
    def _dedent(s: str, /) -> str:
        first_line, *rest = s.split("\n", 1)
        return (first_line + ("\n" + textwrap.dedent(rest[0]) if rest else "")).strip()

    def _line(self, line: yuio.term.AnyString, /):
        self._out += line
        self._out += "\n"

        self._is_first_line = False
        self._first_line_indent = self._continuation_indent

    def _format(self, node: "AstBase", /):
        getattr(self, f"_format_{node.__class__.__name__.lstrip('_')}")(node)

    def _format_Text(self, node: "Text", /, *, default_color: Color):
        s = self.colorize(
            "\n".join(node.lines).strip(),
            default_color=default_color,
        )

        for line in s.wrap(
            self.width,
            preserve_newlines=False,
            first_line_indent=self._first_line_indent,
            continuation_indent=self._continuation_indent,
        ):
            self._line(line)

    def _format_Container(self, node: "Container[TAst]", /):
        self._is_first_line = True
        for item in node.items:
            if not self._is_first_line:
                self._line(self._first_line_indent)
            self._format(item)

    def _format_Document(self, node: "Document", /):
        self._format_Container(node)

    def _format_ThematicBreak(self, _: "ThematicBreak"):
        decoration = self.theme.msg_decorations.get("thematic_break", "")
        self._line(self._first_line_indent + decoration)

    def _format_Heading(self, node: "Heading", /):
        if not self._is_first_line:
            self._line(self._first_line_indent)

        decoration = self.theme.msg_decorations.get(f"heading/{node.level}", "")
        with self._indent(f"msg/decoration:heading/{node.level}", decoration):
            self._format_Text(
                node,
                default_color=self.theme.get_color(f"msg/text:heading/{node.level}"),
            )

        self._line(self._first_line_indent)
        self._is_first_line = True

    def _format_Paragraph(self, node: "Paragraph", /):
        self._format_Text(
            node, default_color=self.theme.get_color("msg/text:paragraph")
        )

    def _format_ListItem(self, node: "ListItem", /, *, min_width: int = 0):
        decoration = self.theme.msg_decorations.get("list", "")
        if node.number is not None:
            decoration = f"{node.number:>{min_width}}." + " " * (
                yuio.term.line_width(decoration) - min_width - 1
            )
        with self._indent("msg/decoration:list", decoration):
            self._format_Container(node)

    def _format_Quote(self, node: "Quote", /):
        decoration = self.theme.msg_decorations.get("quote", "")
        with self._indent(
            "msg/decoration:quote", decoration, continue_with_spaces=False
        ):
            self._format_Container(node)

    def _format_Code(self, node: "Code", /):
        s = SyntaxHighlighter.get_highlighter(node.syntax).highlight(
            self.theme,
            "\n".join(node.lines),
        )

        decoration = self.theme.msg_decorations.get("code", "")
        with self._indent("msg/decoration:code", decoration):
            for line in s.wrap(
                self.width,
                break_on_hyphens=False,
                preserve_spaces=True,
                preserve_newlines=True,
                first_line_indent=self._first_line_indent,
                continuation_indent=self._continuation_indent,
            ):
                self._line(line)

    def _format_List(self, node: "List", /):
        max_number = max(item.number or 0 for item in node.items)
        min_width = math.ceil(math.log10(max_number)) if max_number > 0 else 1
        self._is_first_line = True
        for item in node.items:
            if not self._is_first_line:
                self._line(self._first_line_indent)
            self._format_ListItem(item, min_width=min_width)


@dataclass(**yuio._with_slots())
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


@dataclass(**yuio._with_slots())
class Text(AstBase):
    """
    Base class for all text-based AST nodes, i.e. paragraphs.

    """

    #: Text lines as parsed from the original document.
    lines: _t.List[str] = dataclasses.field(repr=False)

    def dump(self, indent: str = "") -> str:
        s = f"{indent}({self._dump_params()}"
        indent += "  "
        for line in self.lines:
            s += "\n" + indent
            s += repr(line)
        s += ")"
        return s


@dataclass(**yuio._with_slots())
class Container(AstBase, _t.Generic[TAst]):
    """
    Base class for all container-based AST nodes, i.e. list items or quotes.

    This class works as a list of items. Usually it contains arbitrary AST nodes,
    but it can also be limited to specific kinds of nodes via its generic variable.

    """

    #: Inner AST nodes in the container.
    items: _t.List[TAst] = dataclasses.field(repr=False)

    def dump(self, indent: str = "") -> str:
        s = f"{indent or ''}({self._dump_params()}"
        indent += "  "
        for items in self.items:
            s += "\n"
            s += items.dump(indent)
        s += ")"
        return s


@dataclass(**yuio._with_slots())
class Document(Container[AstBase]):
    """
    Root node that contains the entire markdown document.

    """


@dataclass(**yuio._with_slots())
class ThematicBreak(AstBase):
    """
    Represents a visual break in text, a.k.a. an asterism.

    """


@dataclass(**yuio._with_slots())
class Heading(Text):
    """
    Represents a heading.

    """

    #: Level of the heading, `1`-based.
    level: int


@dataclass(**yuio._with_slots())
class Paragraph(Text):
    """
    Represents a regular paragraph.

    """


@dataclass(**yuio._with_slots())
class Quote(Container[AstBase]):
    """
    Represents a quotation block.

    """


@dataclass(**yuio._with_slots())
class Code(Text):
    """
    Represents a highlighted block of code.

    """

    #: Syntax indicator as parsed form the original document.
    syntax: str


@dataclass(**yuio._with_slots())
class ListItem(Container[AstBase]):
    """
    A possibly numbered element of a list.

    """

    #: If present, this is the item's number in a numbered list.
    number: _t.Optional[int]


@dataclass(**yuio._with_slots())
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
    @dataclass(**yuio._with_slots())
    class Default:
        pass

    @dataclass(**yuio._with_slots())
    class List:
        type: str
        marker_len: int
        list: List
        parser: "_MdParser"
        number: _t.Optional[int] = None

    @dataclass(**yuio._with_slots())
    class Quote:
        parser: "_MdParser"

    @dataclass(**yuio._with_slots())
    class Code:
        lines: _t.List[str]

    @dataclass(**yuio._with_slots())
    class FencedCode:
        indent: int
        fence_symbol: str
        fence_length: int
        syntax: str
        lines: _t.List[str]

    @dataclass(**yuio._with_slots())
    class Paragraph:
        lines: _t.List[str]

    State: _t.TypeAlias = _t.Union[Default, List, Quote, Code, FencedCode, Paragraph]

    def __init__(self, allow_headings: bool = True):
        self._allow_headings = allow_headings
        self._nodes: _t.List[AstBase] = []
        self._state: _MdParser.State = self.Default()

    def _parser(self) -> "_MdParser":
        return _MdParser(self._allow_headings)

    @staticmethod
    def _is_blank(s: str) -> bool:
        return not s or s.isspace()

    def parse(self, s: str) -> AstBase:
        s = s.expandtabs(tabsize=4)
        for line in _LINE_FEED_RE.split(s):
            self._handle_line(line)
        return Document(self._finalize())

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
            item = ListItem(self._state.parser._finalize(), self._state.number)
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
        return self._state.parser._handle_lazy_line(line)

    def _flush_List(self):
        assert type(self._state) is self.List
        item = ListItem(self._state.parser._finalize(), self._state.number)
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
        return self._state.parser._handle_lazy_line(line)

    def _flush_Quote(self):
        assert type(self._state) is self.Quote
        items = self._state.parser._finalize()
        self._nodes.append(Quote(items))
        self._state = self.Default()

    def _handle_line_Code(self, line: str):
        assert type(self._state) == self.Code
        if self._is_blank(line) or line.startswith("    "):
            self._state.lines.append(line[4:])
        else:
            self._flush_Code()
            self._handle_line_Default(line)

    def _handle_lazy_line_Code(self, line: str) -> bool:
        assert type(self._state) == self.Code
        return False  # No lazy continuations for code!

    def _flush_Code(self):
        assert type(self._state) == self.Code
        while self._state.lines and self._is_blank(self._state.lines[-1]):
            self._state.lines.pop()
        self._nodes.append(Code(self._state.lines, ""))
        self._state = self.Default()

    def _handle_line_FencedCode(self, line: str):
        assert type(self._state) == self.FencedCode
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
        assert type(self._state) == self.FencedCode
        return False

    def _flush_FencedCode(self):
        assert type(self._state) == self.FencedCode
        self._nodes.append(Code(self._state.lines, self._state.syntax))
        self._state = self.Default()

    def _handle_line_Paragraph(self, line: str):
        assert type(self._state) == self.Paragraph
        if match := _SETEXT_HEADING_RE.match(line):
            level = 1 if match.group("level") == "=" else 2
            self._nodes.append(Heading(self._state.lines, level))
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
        assert type(self._state) == self.Paragraph
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
        assert type(self._state) == self.Paragraph
        self._nodes.append(Paragraph(self._state.lines))
        self._state = self.Default()

    def _handle_line_Default(self, line: str):
        assert type(self._state) == self.Default
        if self._is_blank(line):
            pass  # do nothing
        elif _THEMATIC_BREAK_RE.match(line):
            self._nodes.append(ThematicBreak())
        elif self._allow_headings and (match := _HEADING_RE.match(line)):
            level = len(match.group("marker"))
            self._nodes.append(Heading([match.group("text").strip()], level))
        elif (match := _CODE_BACKTICK_RE.match(line)) or (
            match := _CODE_TILDE_RE.match(line)
        ):
            indent = len(match.group("indent"))
            syntax = match.group("syntax").strip()
            fence_symbol = match.group("fence")[0]
            fence_length = len(match.group("fence"))
            self._state = self.FencedCode(
                indent, fence_symbol, fence_length, syntax, []
            )
        elif match := _CODE_RE.match(line):
            self._state = self.Code([match.group("text")])
        elif (match := _LIST_RE.match(line)) or (
            match := _NUMBERED_LIST_RE.match(line)
        ):
            indent = len(match.group("marker"))
            list_type = match.group("type")
            number_str = match.groupdict().get("number", None)
            number = int(number_str) if number_str else None
            self._state = self.List(list_type, indent, List([]), self._parser(), number)
            self._state.parser._handle_line(match.group("text"))
        elif match := _QUOTE_RE.match(line):
            self._state = self.Quote(self._parser())
            self._state.parser._handle_line(match.group("text"))
        else:
            self._state = self.Paragraph([line])

    def _handle_lazy_line_Default(self, line: str) -> bool:
        assert type(self._state) == self.Default
        return False

    def _flush_Default(self):
        assert type(self._state) == self.Default

    def _finalize(self) -> _t.List[AstBase]:
        self._flush()
        result = self._nodes
        self._nodes = []
        return result


#: Global syntax registry.
_SYNTAXES: _t.Dict[str, "SyntaxHighlighter"] = {}


class SyntaxHighlighter(abc.ABC):
    @property
    @abc.abstractmethod
    def syntaxes(self) -> _t.List[str]:
        """
        List of syntax names that should be associated with this highlighter.

        The first name in this list is a canonical syntax name,
        i.e. it will be used to look up colors in a theme.

        """

        return []

    @property
    def syntax(self) -> str:
        """
        The primary syntax name for this highlighter.

        This name is used to look up colors in a theme.

        """

        return self.syntaxes[0] if self.syntaxes else "unknown"

    @classmethod
    def register_highlighter(cls, highlighter: "SyntaxHighlighter"):
        """
        Register a highlighter in a global registry, and allow looking it up
        via the :meth:`~SyntaxHighlighter.get_highlighter` method.

        """

        for syntax in highlighter.syntaxes:
            _SYNTAXES[syntax.lower().replace("_", "-")] = highlighter

    @classmethod
    def get_highlighter(cls, syntax: str, /) -> "SyntaxHighlighter":
        """
        Look up highlighter by a syntax name.

        """

        return _SYNTAXES.get(
            syntax.lower().replace("_", "-"),
            _DummySyntaxHighlighter(),
        )

    @abc.abstractmethod
    def highlight(
        self,
        theme: Theme,
        code: str,
        default_color: _t.Union[Color, str, None] = None,
    ) -> yuio.term.ColorizedString:
        """
        Highlight the given code using the given theme.

        """

    def _get_default_color(
        self,
        theme: Theme,
        default_color: _t.Union[Color, str, None],
    ) -> Color:
        return theme.to_color(default_color) | theme.get_color(
            f"msg/text:code/{self.syntax}"
        )


class _DummySyntaxHighlighter(SyntaxHighlighter):
    @property
    def syntaxes(self) -> _t.List[str]:
        return ["text", "plain-text"]

    def highlight(
        self,
        theme: Theme,
        code: str,
        default_color: _t.Union[Color, str, None] = None,
    ) -> yuio.term.ColorizedString:
        return yuio.term.ColorizedString(
            [
                self._get_default_color(theme, default_color),
                code,
                Color.NONE,
            ]
        )


SyntaxHighlighter.register_highlighter(_DummySyntaxHighlighter())


class _ReSyntaxHighlighter(SyntaxHighlighter):
    def __init__(
        self,
        syntaxes: _t.List[str],
        pattern: _t.StrRePattern,
        str_esc_pattern: _t.Optional[_t.StrRePattern] = None,
    ):
        self._syntaxes = syntaxes
        self._pattern = pattern
        self._str_esc_pattern = str_esc_pattern

    @property
    def syntaxes(self) -> _t.List[str]:
        return self._syntaxes

    def highlight(
        self,
        theme: Theme,
        code: str,
        default_color: _t.Union[Color, str, None] = None,
    ) -> yuio.term.ColorizedString:
        default_color = self._get_default_color(theme, default_color)

        out = yuio.term.ColorizedString()

        last_pos = 0
        for code_unit in self._pattern.finditer(code):
            if last_pos < code_unit.start():
                out += default_color
                out += code[last_pos : code_unit.start()]
            last_pos = code_unit.end()

            for name, text in sorted(code_unit.groupdict().items()):
                if not text:
                    continue
                name = name.split("__", maxsplit=1)[-1]
                str_color = default_color | theme.get_color(f"hl/str:{self.syntax}")
                esc_color = default_color | theme.get_color(f"hl/str/esc:{self.syntax}")
                if self._str_esc_pattern is not None and name == "str":
                    last_escape_pos = 0
                    for escape_unit in self._str_esc_pattern.finditer(text):
                        if last_escape_pos < escape_unit.start():
                            out += str_color
                            out += text[last_escape_pos : escape_unit.start()]
                        last_escape_pos = escape_unit.end()
                        if escape := code_unit.group(0):
                            out += esc_color
                            out += escape
                    if last_escape_pos < len(text):
                        out += str_color
                        out += code[last_escape_pos:]
                else:
                    out += default_color | theme.get_color(f"hl/{name}:{self.syntax}")
                    out += text

        if last_pos < len(code):
            out += default_color
            out += code[last_pos:]

        out += Color.NONE

        return out


SyntaxHighlighter.register_highlighter(
    _ReSyntaxHighlighter(
        ["py", "py3", "py-3", "python", "python3", "python-3"],
        re.compile(
            r"""
          (?P<kwd>
            \b(?:                                   # keyword
              and|as|assert|async|await|break|class|continue|def|del|elif|else|
              except|False|finally|for|from|global|if|import|in|is|lambda|None|
              nonlocal|not|or|pass|raise|return|True|try|while|with|yield
            )\b)
        | (?P<str>
            [rfu]*(                                 # string prefix
                '(?:\\.|[^\\'])*(?:'|\n)            # singly-quoted string
              | "(?:\\.|[^\\"])*(?:"|\n)            # doubly-quoted string
              | \"""(\\.|[^\\]|\n)*?\"""            # long singly-quoted string
              | \'''(\\.|[^\\]|\n)*?\'''))          # long doubly-quoted string
        | (?P<lit>
              \d+(?:\.\d*(?:e[+-]?\d+)?)?           # int or float
            | \.\d+(?:e[+-]?\d+)?                   # float that starts with dot
            | 0x[0-9a-fA-F]+                        # hex
            | 0b[01]+)                              # bin
        | (?P<punct>[{}()[\]\\;|!&])                # punctuation
        | (?P<comment>\#.*$)                        # comment
        """,
            re.MULTILINE | re.VERBOSE,
        ),
    )
)
SyntaxHighlighter.register_highlighter(
    _ReSyntaxHighlighter(
        ["sh", "bash"],
        re.compile(
            r"""
        (?P<kwd>
            \b(?:                                   # keyword
              if|then|elif|else|fi|time|for|in|until|while|do|done|case|
              esac|coproc|select|function
            )\b
          | \[\[                                    # `test` syntax: if [[ ... ]]
          | \]\])
        | (?P<a0__punct>(?:^|\|\|?|&&|\$\())        # chaining operator: pipe or logic
          (?P<a1__>\s*)
          (?P<a2__prog>\S+)                         # prog
        | (?P<str>
            '(?:[.\n]*?)*'                          # singly-quoted string
          | "(?:\\.|[^\\"])*")                      # doubly-quoted string
        | (?P<punct>
              [{}()[\]\\;!&|&]                      # punctuation
            | <{1,3}                                # input redirect
            | [12]?>{1,2}(?:&[12])?)                # output redirect
        | (?P<comment>\#.*$)                        # comment
        | (?P<flag>(?<![\w-])-[a-zA-Z0-9_-]+\b)     # flag
        """,
            re.MULTILINE | re.VERBOSE,
        ),
    ),
)
SyntaxHighlighter.register_highlighter(
    _ReSyntaxHighlighter(
        ["sh-usage", "bash-usage"],
        re.compile(
            r"""
        (?P<kwd>
          \b(?:                                     # keyword
            if|then|elif|else|fi|time|for|in|until|while|do|done|case|
            esac|coproc|select|function
          )\b)
        | (?P<prog>%%\(prog\)s)                     # prog
        | (?P<metavar>(?<=<)[^>]+(?=>))             # metavar
        | (?P<str>
              '(?:[.\n]*?)*'                        # singly-quoted string
            | "(?:\\.|[^\\"])*")                    # doubly-quoted string
        | (?P<comment>\#.*$)                        # comment
        | (?P<flag>(?<![\w-])-[-a-zA-Z0-9_]+\b)     # flag
    """,
            re.MULTILINE | re.VERBOSE,
        ),
    )
)


class _TbHighlighter(SyntaxHighlighter):
    @property
    def syntaxes(self) -> _t.List[str]:
        return [
            "tb",
            "traceback",
            "py-tb",
            "py-traceback",
            "python-tb",
            "python-traceback",
        ]

    class _StackColors:
        def __init__(self, theme: Theme, default_color: Color, tag: str):
            self.file_color = default_color | theme.get_color(f"tb/frame/{tag}/file")
            self.file_path_color = default_color | theme.get_color(
                f"tb/frame/{tag}/file/path"
            )
            self.file_line_color = default_color | theme.get_color(
                f"tb/frame/{tag}/file/line"
            )
            self.file_module_color = default_color | theme.get_color(
                f"tb/frame/{tag}/file/module"
            )
            self.code_color = default_color | theme.get_color(f"tb/frame/{tag}/code")
            self.highlight_color = default_color | theme.get_color(
                f"tb/frame/{tag}/highlight"
            )

    _TB_RE = re.compile(
        r"^(?P<indent>[ |+]*)(Stack|Traceback|Exception Group Traceback) \(most recent call last\):$"
    )
    _TB_MSG_RE = re.compile(r"^(?P<indent>[ |+]*)[A-Za-z_][A-Za-z0-9_]*($|:.*$)")
    _TB_LINE_FILE = re.compile(
        r'^[ |+]*File (?P<file>"[^"]*"), line (?P<line>\d+)(?:, in (?P<loc>.*))?$'
    )
    _TB_LINE_HIGHLIGHT = re.compile(r"^[ |+^~-]*$")
    _SITE_PACKAGES = os.sep + "lib" + os.sep + "site-packages" + os.sep
    _LIB_PYTHON = os.sep + "lib" + os.sep + "python"

    def highlight(
        self,
        theme: Theme,
        code: str,
        default_color: _t.Union[Color, str, None] = None,
    ) -> yuio.term.ColorizedString:
        default_color = self._get_default_color(theme, default_color)

        py_highlighter = SyntaxHighlighter.get_highlighter("python")

        heading_color = default_color | theme.get_color("tb/heading")
        message_color = default_color | theme.get_color("tb/message")

        stack_normal_colors = self._StackColors(theme, default_color, "usr")
        stack_lib_colors = self._StackColors(theme, default_color, "lib")
        stack_colors = stack_normal_colors

        res = yuio.term.ColorizedString()

        PLAIN_TEXT, STACK, MESSAGE = 1, 2, 3
        state = PLAIN_TEXT
        stack_indent = ""
        message_indent = ""

        for line in code.splitlines(keepends=True):
            if state is STACK:
                if line.startswith(stack_indent):
                    # We're still in the stack.
                    if match := self._TB_LINE_FILE.match(line):
                        file, line, loc = match.group("file", "line", "loc")

                        if self._SITE_PACKAGES in file or self._LIB_PYTHON in file:
                            stack_colors = stack_lib_colors
                        else:
                            stack_colors = stack_normal_colors

                        res += Color.NONE
                        res += stack_indent
                        res += stack_colors.file_color
                        res += "File "
                        res += stack_colors.file_path_color
                        res += file
                        res += stack_colors.file_color
                        res += ", line "
                        res += stack_colors.file_line_color
                        res += line
                        res += stack_colors.file_color

                        if loc:
                            res += ", in "
                            res += stack_colors.file_module_color
                            res += loc
                            res += stack_colors.file_color

                        res += "\n"
                    elif match := self._TB_LINE_HIGHLIGHT.match(line):
                        res += Color.NONE
                        res += stack_indent
                        res += stack_colors.highlight_color
                        res += line[len(stack_indent) :]
                    else:
                        res += Color.NONE
                        res += stack_indent
                        res += py_highlighter.highlight(
                            theme,
                            line[len(stack_indent) :],
                            stack_colors.code_color,
                        )
                    continue
                else:
                    # Stack has ended, this line is actually a message.
                    state = MESSAGE

            if state is MESSAGE:
                if line and line != "\n" and line.startswith(message_indent):
                    # We're still in the message.
                    res += Color.NONE
                    res += message_indent
                    res += message_color
                    res += line[len(message_indent) :]
                    continue
                else:
                    # Message has ended, this line is actually a plain text.
                    state = PLAIN_TEXT

            if state is PLAIN_TEXT:
                if match := self._TB_RE.match(line):
                    # Plain text has ended, this is actually a heading.
                    message_indent = match.group("indent").replace("+", "|")
                    stack_indent = message_indent + "  "

                    res += Color.NONE
                    res += message_indent
                    res += heading_color
                    res += line[len(message_indent) :]

                    state = STACK
                    continue
                elif match := self._TB_MSG_RE.match(line):
                    # Plain text has ended, this is an error message (without a traceback).
                    message_indent = match.group("indent").replace("+", "|")
                    stack_indent = message_indent + "  "

                    res += Color.NONE
                    res += message_indent
                    res += message_color
                    res += line[len(message_indent) :]

                    state = MESSAGE
                    continue
                else:
                    # We're still in plain text.
                    res += Color.NONE
                    res += line
                    continue

        res += Color.NONE

        return res


SyntaxHighlighter.register_highlighter(_TbHighlighter())


__TAG_RE = re.compile(
    r"""
          <c (?P<tag_open>[a-z0-9 _/@:-]+)>         # Color tag open.
        | </c>                                      # Color tag close.
        | \\(?P<punct>[%(punct)s])                  # Escape character.
        | (?<!`)(`+)(?!`)(?P<code>.*?)(?<!`)\3(?!`) # Inline code block (backticks).
    """
    % {"punct": re.escape(string.punctuation)},
    re.VERBOSE | re.MULTILINE,
)
__NEG_NUM_RE = re.compile(r"^-(0x[0-9a-fA-F]+|0b[01]+|\d+(e[+-]?\d+)?)$")
__FLAG_RE = re.compile(r"^-[-a-zA-Z0-9_]*$")


def _colorize(
    theme: Theme,
    s: str,
    /,
    *,
    default_color: _t.Union[Color, str] = Color.NONE,
    parse_cli_flags_in_backticks: bool = False,
) -> "yuio.term.ColorizedString":
    default_color = theme.to_color(default_color)

    raw: _t.List[_t.Union[str, Color]] = []
    raw.append(default_color)

    stack = [default_color]

    last_pos = 0
    for tag in __TAG_RE.finditer(s):
        raw.append(s[last_pos : tag.start()])
        last_pos = tag.end()

        if name := tag.group("tag_open"):
            color = stack[-1]
            for sub_name in name.split():
                sub_name = sub_name.strip()
                color = color | theme.get_color(sub_name)
            raw.append(color)
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
                raw.append(stack[-1] | theme.get_color("hl/flag:sh-usage"))
            else:
                raw.append(stack[-1] | theme.get_color("code"))
            raw.append(code)
            raw.append(stack[-1])
        elif len(stack) > 1:
            stack.pop()
            raw.append(stack[-1])

    raw.append(s[last_pos:])

    raw.append(Color.NONE)

    return yuio.term.ColorizedString(raw)
