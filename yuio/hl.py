# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Yuio supports basic code highlighting; it is just enough to format help messages
for CLI, and color tracebacks when an error occurs.

Yuio supports the following languages:

- ``python``,
- ``traceback``,
- ``bash``,
- ``diff``,
- ``json``.


Highlighters registry
---------------------

.. autofunction:: get_highlighter

.. autofunction:: register_highlighter


Highlighter base class
----------------------

.. autoclass:: SyntaxHighlighter
    :members:

.. autoclass:: ReSyntaxHighlighter
    :members:


Implementing regexp-based highlighter
-------------------------------------

Let's implement a syntax highlighter for JSON.

We will start by creating regular expressions for JSON tokens. We will need:

-   built-in literals: ``\\b(true|false|null)\\b``, token name ``"lit/builtin"``;
-   numbers: ``-?\\d+(\\.\\d+)?([eE][+-]?\\d+)?``, token name ``lit/num``;
-   strings: ``"(\\\\.|[^\\\\"])*"``, token name ``str``;
-   punctuation: ``[{}\\[\\],:]``, token name ``punct``.

Now that we know our tokens and regular expressions to parse them, we can pass them
to :class:`ReSyntaxHighlighter`:

.. code-block:: python

    json_highlighter = yuio.hl.ReSyntaxHighlighter(
        [
            (
                # Literals.
                r"\\b(true|false|null)\\b",
                "lit/builtin",
            ),
            (
                # Numbers.
                r"-?\\d+(\\.\\d+)?([eE][+-]?\\d+)?",
                "lit/num",
            ),
            (
                # Strings.
                r'"(\\\\.|[^\\\\"])*"',
                "str",
            ),
            (
                # Punctuation.
                r"[{}\\[\\],:]",
                "punct",
            ),
        ],
    )

:class:`ReSyntaxHighlighter` will scan source code and look for given regular
expressions. If found, it will color matched part of the code depending on the
associated token name.

We can also color different parts of matched code with different colors, and even
pass them to nested syntax highlighters.

For example, let's define a highlighter that searches for escape sequences in strings:

.. code-block:: python

    str_highlighter = yuio.hl.ReSyntaxHighlighter(
        [
            (
                # Escape sequence.
                r'\\([\\/"bfnrt]|u[0-9a-fA-F]{4})',
                "str/esc",
            )
        ],
        base_color="str",
    )

We can now apply ``str_highlighter`` to strings when ``json_highlighter`` matches them:

.. code-block:: python

    json_highlighter = yuio.hl.ReSyntaxHighlighter(
        [
            ...,
            (
                # Strings.
                r'(")(\\\\.|[^\\\\"])*(")',
                ("str", str_highlighter, "str"),
            ),
            ...,
        ],
    )

Our regular expression for strings contains three capturing groups:

.. raw:: html

    <div class="highlight-text notranslate">
    <div class="highlight">
    <pre class="ascii-graphics">
        <span class="k">(</span>"<span class="k">)</span><span class="k">(</span><span class="w">(?:</span>\\\\.|[^\\\\"]<span class="w">)</span>*<span class="k">)(</span>"<span class="k">)</span>
         │  └┬────────────┘  │
         │   │              #2, matches closing quote
         │   └ #1, matches string content
         └ #0, matches opening quote
    </pre>
    </div>
    </div>

And we've passed token names and highlighters for each of these groups:

.. raw:: html

    <div class="highlight-text notranslate">
    <div class="highlight">
    <pre class="ascii-graphics">
        (<span class="s">"str"</span>, str_highlighter, <span class="s">"str"</span>)
         └┬──┘  └┬────────────┘  └┬──┘
          │      │                │
          │      │               highlights contents of group #2
          │      └ highlights contents of group #1
          └ highlights contents of group #0
    </pre>
    </div>
    </div>

"""

from __future__ import annotations

import abc
import functools
import re

import yuio.color
import yuio.string
import yuio.theme

import yuio._typing_ext as _tx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "ReSyntaxHighlighter",
    "SyntaxHighlighter",
    "TokenDescription",
    "TokenHighlight",
    "get_highlighter",
    "register_highlighter",
]


class SyntaxHighlighter(abc.ABC):
    @abc.abstractmethod
    def highlight(
        self,
        code: str,
        /,
        *,
        theme: yuio.theme.Theme,
        syntax: str,
        default_color: yuio.color.Color | str | None = None,
    ) -> yuio.string.ColorizedString:
        """
        Highlight the given code using the given theme.

        :param code:
            code to highlight.
        :param syntax:
            canonical name of the syntax.
        :param theme:
            theme that will be used to look up color tags.
        :param default_color:
            color or color path to apply to the entire code.

        """

        raise NotImplementedError()

    def _get_default_color(
        self,
        theme: yuio.theme.Theme,
        default_color: yuio.color.Color | str | None,
        syntax: str,
    ) -> yuio.color.Color:
        return theme.to_color(default_color) | theme.get_color(
            f"msg/text:code/{syntax}"
        )


_SYNTAXES: dict[str, tuple[SyntaxHighlighter, str]] = {}


def register_highlighter(syntaxes: list[str], highlighter: SyntaxHighlighter):
    """
    Register a highlighter in a global registry, and allow looking it up
    via the :meth:`~get_highlighter` method.

    :param syntaxes:
        syntax names which correspond to this highlighter. The first syntax
        is considered *canonical*, meaning that it should be used to look up
        colors in a theme.
    :param highlighter:
        a highlighter instance.

    """

    canonical_syntax = syntaxes[0]
    for syntax in syntaxes:
        _SYNTAXES[syntax.lower().replace("_", "-")] = highlighter, canonical_syntax


def get_highlighter(syntax: str, /) -> tuple[SyntaxHighlighter, str]:
    """
    Look up highlighter by a syntax name.

    :param syntax:
        name of the syntax highlighter.
    :returns:
        a highlighter instance and a string with canonical syntax name.
        If highlighter with the given name can't be found, returns a dummy
        highlighter that does nothing.
    :example:
        .. invisible-code-block: python

            import yuio.hl, yuio.theme
            code = ""
            theme = yuio.theme.Theme()

        .. code-block:: python

            highlighter, syntax_name = yuio.hl.get_highlighter("python")

            highlighted = highlighter.highlight(
                code,
                theme=theme,
                syntax=syntax_name,
            )

    """

    return _SYNTAXES.get(syntax.lower().replace("_", "-")) or (
        _DummySyntaxHighlighter(),
        syntax,
    )


class _DummySyntaxHighlighter(SyntaxHighlighter):
    def highlight(
        self,
        code: str,
        /,
        *,
        theme: yuio.theme.Theme,
        syntax: str,
        default_color: yuio.color.Color | str | None = None,
    ) -> yuio.string.ColorizedString:
        return yuio.string.ColorizedString(
            self._get_default_color(theme, default_color, syntax),
            code,
            yuio.color.Color.NONE,
        )


register_highlighter(["text", "plain", "plain-text"], _DummySyntaxHighlighter())


TokenHighlight: _t.TypeAlias = (
    str | SyntaxHighlighter | None | tuple[str | SyntaxHighlighter | None, ...]
)
"""
See :class:`ReSyntaxHighlighter`.

"""

TokenDescription: _t.TypeAlias = tuple[str, TokenHighlight]
"""
See :class:`ReSyntaxHighlighter`.

"""


class ReSyntaxHighlighter(SyntaxHighlighter):
    """
    A highlighter implementation that uses regular expressions to tokenize source code.

    This highlighter accepts regular expressions for tokens, and corresponding token
    names.

    Regular expressions are compiled with flag :data:`re.MULTILINE`; they should not
    contain global flags or named groups. :class:`ReSyntaxHighlighter` will combine
    all given regexps into a single regular expression, and run it using
    :func:`re.finditer` (similar to a tokenizer example from `Python documentation`__.

    __ https://docs.python.org/3/library/re.html#writing-a-tokenizer

    :param patterns:
        regular expressions and corresponding colors that will be used to tokenize
        code.

        Each pattern should be a tuple of two elements:

        -   the first is a string with a regular expression, which will be combined
            with multiline flag;

        -   the second is name of a token, or another :class:`SyntaxHighlighter`.

            It can also be a tuple of token names and syntax highlighters, one for
            every capturing group in the regular expression.

            Token names will be converted to colors by looking up
            :color-path:`hl/{token}:{syntax}` in a :class:`~yuio.theme.Theme`.
    :param base_color:
        color that will be added to the entire code regardless of tokens

    """

    def __init__(
        self,
        patterns: list[TokenDescription],
        *,
        base_color: str | None = None,
    ):
        self._patterns = patterns
        self._base_color = base_color

    @functools.cached_property
    def _tokenizer_data(self):
        first_group = 0
        all_patterns = []
        all_groups: dict[str, tuple[int, TokenHighlight]] = {}
        for i, (pattern, groups) in enumerate(self._patterns):
            first_group += 1
            pattern = re.compile(pattern, re.MULTILINE)
            pattern_name = f"_p_{i}_"
            all_patterns.append(f"(?P<{pattern_name}>{pattern.pattern})")
            all_groups[pattern_name] = (first_group, groups)
            first_group += pattern.groups
        return re.compile("|".join(all_patterns), re.MULTILINE), all_groups

    def highlight(
        self,
        code: str,
        /,
        *,
        theme: yuio.theme.Theme,
        syntax: str,
        default_color: yuio.color.Color | str | None = None,
    ) -> yuio.string.ColorizedString:
        default_color = self._get_default_color(theme, default_color, syntax)
        if self._base_color:
            default_color = default_color | theme.get_color(
                f"hl/{self._base_color}:{syntax}"
            )

        res = yuio.string.ColorizedString()
        pattern, all_groups = self._tokenizer_data
        pos = 0
        for match in pattern.finditer(code):
            start, end = match.span()
            if pos < start:
                res.append_color(default_color)
                res.append_str(code[pos:start])
            assert match.lastgroup
            first_group_index, groups = all_groups[match.lastgroup]
            self._process_groups(
                syntax, theme, default_color, res, match, first_group_index, groups
            )
            pos = end
        if pos < len(code):
            res.append_color(default_color)
            res.append_str(code[pos:])

        return res

    def _process_groups(
        self,
        syntax: str,
        theme: yuio.theme.Theme,
        default_color: yuio.color.Color,
        res: yuio.string.ColorizedString,
        match: _tx.StrReMatch,
        first_group_index: int,
        groups: TokenHighlight,
    ):
        if not groups:
            res.append_color(default_color)
            res.append_str(match.group())
        elif isinstance(groups, str):
            res.append_color(default_color | theme.get_color(f"hl/{groups}:{syntax}"))
            res.append_str(match.group())
        elif isinstance(groups, SyntaxHighlighter):
            res.append_colorized_str(
                groups.highlight(
                    match.group(),
                    theme=theme,
                    syntax=syntax,
                    default_color=default_color,
                )
            )
        else:
            pos = match.start()
            code = match.string
            for i, text in enumerate(match.groups()):
                if not text or i < first_group_index:
                    continue
                elif i - first_group_index >= len(groups):
                    break
                group = groups[i - first_group_index]
                if not group:
                    continue
                start = match.start(i + 1)
                end = match.end(i + 1)
                if start < pos:
                    continue
                elif start > pos:
                    res.append_color(default_color)
                    res.append_str(code[pos:start])
                if isinstance(group, str):
                    res.append_color(
                        default_color | theme.get_color(f"hl/{group}:{syntax}")
                    )
                    res.append_str(code[start:end])
                elif isinstance(group, SyntaxHighlighter):
                    res.append_colorized_str(
                        group.highlight(
                            code[start:end],
                            theme=theme,
                            syntax=syntax,
                            default_color=default_color,
                        )
                    )
                pos = end
            if pos < match.end():
                res.append_color(default_color)
                res.append_str(code[pos : match.end()])


_PY_STRING_ESCAPES = ReSyntaxHighlighter(
    [
        (
            r"\\[\n\'\"\\abfnrtv]",
            "str/esc",
        ),
        (
            r"\\[0-7]{3}",
            "str/esc",
        ),
        (
            r"\\x[0-9a-fA-F]{2}",
            "str/esc",
        ),
        (
            r"\\u[0-9a-fA-F]{4}",
            "str/esc",
        ),
        (
            r"\\U[0-9a-fA-F]{8}",
            "str/esc",
        ),
        (
            r"\\N\{[^}\n]+\}",
            "str/esc",
        ),
        (
            r"{{|}}",
            "str/esc",
        ),
        (
            r"{[^}]*?}",
            "str/esc",
        ),
        (
            r"%(?:\([^)]*\))?[#0\-+ ]*(?:\*|\d+)?(?:\.(?:\*|\d*))?[hlL]?.",
            "str/esc",
        ),
    ],
    base_color="str",
)


_PY_HIGHLIGHTER_INNER = ReSyntaxHighlighter(
    [
        (
            r"\b(?:and|as|assert|async|await|break|class|continue|def|del|elif|else|except"
            r"|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise"
            r"|return|try|while|with|yield)\b",
            "kwd",
        ),
        (
            r'([rfut]*)(""")((?:\\.|[^\\]|\n)*?)(?:(""")|($))',
            ("str/prefix", "str", _PY_STRING_ESCAPES, "str", "error"),
        ),
        (
            r"([rfut]*)(''')((?:\\.|[^\\]|\n)*?)(?:(''')|($))",
            ("str/prefix", "str", _PY_STRING_ESCAPES, "str", "error"),
        ),
        (
            r'([rfut]*)(")((?:\\.|[^\\"])*)(?:(")|(\n|$))',
            ("str/prefix", "str", _PY_STRING_ESCAPES, "str", "error"),
        ),
        (
            r"([rfut]*)(')((?:\\.|[^\\'])*)(?:(')|(\n|$))",
            ("str/prefix", "str", _PY_STRING_ESCAPES, "str", "error"),
        ),
        (
            r"(?<![\.\w])[+-]?\d+(?:\.\d*(?:e[+-]?\d+)?)?",
            "lit/num/dec",
        ),
        (
            r"(?<![\.\w])[+-]?\.\d+(?:e[+-]?\d+)?",
            "lit/num/dec",
        ),
        (
            r"(?<![\.\w])[+-]?0x[0-9a-fA-F]+",
            "lit/num/hex",
        ),
        (
            r"(?<![\.\w])[+-]?0o[0-7]+",
            "lit/num/oct",
        ),
        (
            r"(?<![\.\w])[+-]?0b[01]+",
            "lit/num/bin",
        ),
        (
            r"(?<![\.\w])\b(?:None|True|False)\b",
            "lit/builtin",
        ),
        (
            r"\b(?:str|int|float|complex|list|tuple|range|dict|set|frozenset|bool"
            r"|bytes|bytearray|memoryview)\b",
            "type/builtin",
        ),
        (
            r"\b(?:[A-Z](?:[A-Z0-9_]*?[a-z]\w*)?)\b",
            "type/user",
        ),
        (
            r"[{}()\[\]\\;,]",
            "punct",
        ),
        (
            r"\#.*$",
            "comment",
        ),
    ],
)


class _PyHighlighter(SyntaxHighlighter):
    def highlight(
        self,
        code: str,
        /,
        *,
        theme: yuio.theme.Theme,
        syntax: str,
        default_color: yuio.color.Color | str | None = None,
    ) -> yuio.string.ColorizedString:
        if not code.startswith(">>>"):
            return _PY_HIGHLIGHTER_INNER.highlight(
                code, theme=theme, syntax=syntax, default_color=default_color
            )

        default_color = theme.to_color(default_color)

        blocks = []

        PLAIN_TEXT, CODE = 1, 2
        state = PLAIN_TEXT

        block: list[str] = []
        results: list[str] = []
        for line in code.splitlines(keepends=True):
            if state == PLAIN_TEXT:
                if line.startswith(">>>"):
                    if block:
                        blocks.append((block, results))
                    state = CODE
                    block = [line[3:]]
                    results = []
                else:
                    results.append(line)
            else:
                if line.startswith("..."):
                    block.append(line[3:])
                else:
                    results.append(line)
                    state = PLAIN_TEXT
        if block:
            blocks.append((block, results))

        res = yuio.string.ColorizedString(default_color)
        indent_a = yuio.string.ColorizedString(
            default_color | theme.get_color(f"hl/doctest_marker/start:{syntax}"),
            ">>>",
        )
        indent_b = yuio.string.ColorizedString(
            default_color | theme.get_color(f"hl/doctest_marker/continue:{syntax}"),
            "...",
        )

        for block, results in blocks:
            code = "".join(block)
            res.append_colorized_str(
                _PY_HIGHLIGHTER_INNER.highlight(
                    code,
                    theme=theme,
                    syntax=syntax,
                    default_color=default_color,
                ).indent(indent_a, indent_b)
            )
            res.append_str("".join(results))

        return res


register_highlighter(
    ["py", "py3", "py-3", "python", "python3", "python-3", "repr"],
    _PyHighlighter(),
)


register_highlighter(
    ["sh", "bash", "console"],
    ReSyntaxHighlighter(
        [
            (
                r"\b(?:if|then|elif|else|fi|time|for|in|until|while|do|done|case|"
                r"esac|coproc|select|function)\b",
                "kwd",
            ),
            (
                r"\[\[",
                "kwd",
            ),
            (
                r"\]\]",
                "kwd",
            ),
            (
                r"(^|\|\|?|&&|\$\()(?:\s*)([\w./~]([\w.@/-]|\\.)+)",
                ("kwd", "prog"),
            ),
            (
                r"(^\$)(?:\s*)([\w./~]([\w.@/-]|\\.)+)",
                ("punct", "prog"),
            ),
            (
                r"\|\|?|&&",
                "kwd",
            ),
            (
                r"'[^']*'",
                "str",
            ),
            (
                r'"(?:\\.|[^\\"])*"',
                "str",
            ),
            (
                r"<{1,3}",
                "kwd",
            ),
            (
                r"[12]?>{1,2}(?:&[12])?",
                "kwd",
            ),
            (
                r"\#.*$",
                "comment",
            ),
            (
                r"(?<![\w-])-[a-zA-Z0-9_-]+\b",
                "flag",
            ),
            (
                r"[{}()\[\]\\;!&|]",
                "punct",
            ),
        ],
    ),
)

register_highlighter(
    ["sh-usage", "bash-usage"],
    ReSyntaxHighlighter(
        [
            (
                r"\b(?:if|then|elif|else|fi|time|for|in|until|while|do|done|case|"
                r"esac|coproc|select|function)\b",
                "kwd",
            ),
            (
                r"%\(prog\)s",
                "prog",
            ),
            (
                r"'[^']*'",
                "str",
            ),
            (
                r'"(?:\\.|[^\\"])*"',
                "str",
            ),
            (
                r"\#.*$",
                "comment",
            ),
            (
                r"(?<![\w-])-[a-zA-Z0-9_-]+\b",
                "flag",
            ),
            (
                r"<options>",
                "flag",
            ),
            (
                r"<[^>]+>",
                "metavar",
            ),
            (
                r"[{}()\[\]\\;!&|]",
                "punct",
            ),
            (
                r"^\$",
                "punct",
            ),
            (
                r"(?<=[{(\[|])(?!\s)([^})\]|\n\r\t\v\b]*?)(?<!\s)(?=[})\]|])",
                "metavar",
            ),
        ],
    ),
)

register_highlighter(
    ["diff"],
    ReSyntaxHighlighter(
        [
            (
                r"^(\-\-\-|\+\+\+|\@\@)[^\r\n]*$",
                "meta",
            ),
            (
                r"^\+[^\r\n]*$",
                "added",
            ),
            (
                r"^\-[^\r\n]*$",
                "removed",
            ),
        ],
    ),
)

_JSON_STRING_ESCAPES = ReSyntaxHighlighter(
    [
        (
            r'\\([\\/"bfnrt]|u[0-9a-fA-F]{4})',
            "str/esc",
        )
    ],
    base_color="str",
)

register_highlighter(
    ["json"],
    ReSyntaxHighlighter(
        [
            (
                r"\b(?:true|false|null)\b",
                "lit/builtin",
            ),
            (
                r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?",
                "lit/num/dec",
            ),
            (
                r'(")((?:\\.|[^\\"])*)(")',
                ("str", _JSON_STRING_ESCAPES, "str"),
            ),
            (
                r"[{}\[\],:]",
                "punct",
            ),
        ],
    ),
)


class _TbHighlighter(SyntaxHighlighter):
    class _StackColors:
        def __init__(
            self, theme: yuio.theme.Theme, default_color: yuio.color.Color, tag: str
        ):
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
    _SITE_PACKAGES = re.compile(r"[/\\]lib[/\\]site-packages[/\\]")
    _LIB_PYTHON = re.compile(r"[/\\]lib[/\\]python")

    def highlight(
        self,
        code: str,
        /,
        *,
        theme: yuio.theme.Theme,
        syntax: str,
        default_color: yuio.color.Color | str | None = None,
    ) -> yuio.string.ColorizedString:
        default_color = self._get_default_color(theme, default_color, syntax)

        py_highlighter, py_highlighter_syntax_name = get_highlighter("py")

        heading_color = default_color | theme.get_color("tb/heading")
        message_color = default_color | theme.get_color("tb/message")

        stack_normal_colors = self._StackColors(theme, default_color, "usr")
        stack_lib_colors = self._StackColors(theme, default_color, "lib")
        stack_colors = stack_normal_colors

        res = yuio.string.ColorizedString()

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

                        if self._SITE_PACKAGES.search(file) or self._LIB_PYTHON.search(
                            file
                        ):
                            stack_colors = stack_lib_colors
                        else:
                            stack_colors = stack_normal_colors

                        res += yuio.color.Color.NONE
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
                        res += yuio.color.Color.NONE
                        res += stack_indent
                        res += stack_colors.highlight_color
                        res += line[len(stack_indent) :]
                    else:
                        res += yuio.color.Color.NONE
                        res += stack_indent
                        res += py_highlighter.highlight(
                            line[len(stack_indent) :],
                            theme=theme,
                            syntax=py_highlighter_syntax_name,
                            default_color=stack_colors.code_color,
                        )
                    continue
                else:
                    # Stack has ended, this line is actually a message.
                    state = MESSAGE

            if state is MESSAGE:
                if line and line != "\n" and line.startswith(message_indent):
                    # We're still in the message.
                    res += yuio.color.Color.NONE
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

                    res += yuio.color.Color.NONE
                    res += message_indent
                    res += heading_color
                    res += line[len(message_indent) :]

                    state = STACK
                    continue
                elif match := self._TB_MSG_RE.match(line):
                    # Plain text has ended, this is an error message (without a traceback).
                    message_indent = match.group("indent").replace("+", "|")
                    stack_indent = message_indent + "  "

                    res += yuio.color.Color.NONE
                    res += message_indent
                    res += message_color
                    res += line[len(message_indent) :]

                    state = MESSAGE
                    continue
                else:
                    # We're still in plain text.
                    res += yuio.color.Color.NONE
                    res += line
                    continue

        return res


register_highlighter(
    [
        "tb",
        "traceback",
        "py-tb",
        "py3-tb",
        "py-3-tb",
        "py-traceback",
        "py3-traceback",
        "py-3-traceback",
        "python-tb",
        "python3-tb",
        "python-3-tb",
        "python-traceback",
        "python3-traceback",
        "python-3-traceback",
    ],
    _TbHighlighter(),
)
