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

.. type:: RawString
    :canonical: typing.Iterable[yuio.color.Color | str]

    Raw colorized string. This is the underlying type
    for :class:`ColorizedString`.

.. type:: AnyString
    :canonical: str | yuio.color.Color | RawString | ColorizedString

    Any string (i.e. a :class:`str`, a raw colorized string,
    or a normal colorized string).

.. autoclass:: NoWrap

.. autoclass:: Esc

.. autofunction:: line_width

"""

from __future__ import annotations

import functools
import re
import unicodedata

import yuio
import yuio.color
import yuio.term
import yuio.theme
from yuio import _typing as _t

__all__ = [
    "line_width",
    "NoWrap",
    "Esc",
    "ColorizedString",
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


class NoWrap(str):
    """
    A string that will not be wrapped by the text wrapper.

    See :meth:`ColorizedString.wrap` for more info.

    """


class Esc(NoWrap):
    """
    A string that signifies an escaped special symbol.

    This string is not wrapped even if ``break_long_nowrap_words`` is :data:`True`.

    """


@_t.final
class ColorizedString:
    """
    A string with colors.

    This class is a wrapper over a list of strings and colors.
    Each color applies to strings after it, right until the next color.

    :class:`ColorizedString` supports some basic string operations.
    Most notable, it supports wide-character-aware wrapping (see :func:`line_width`),
    and ``%``-formatting.

    Unlike :class:`str` instances, :class:`ColorizedString` is mutable through
    the ``+=`` operator.

    You can build a colorized string from raw parts,
    or you can use :meth:`yuio.md.colorize`.

    """

    def __init__(
        self,
        content: AnyString = "",
        /,
        *,
        explicit_newline: str = "",
    ):
        self._parts: list[yuio.color.Color | str]
        if isinstance(content, (str, yuio.color.Color)):
            self._parts = [content] if content else []
        elif isinstance(content, ColorizedString):
            self._parts = list(content._parts)
        else:
            self._parts = list(content)

        self._explicit_newline = explicit_newline

    @property
    def explicit_newline(self) -> str:
        """
        Explicit newline indicates that a line of a wrapped text
        was broken because the original text contained a new line character.

        See :meth:`~ColorizedString.wrap` for details.

        """

        return self._explicit_newline

    @functools.cached_property
    def width(self) -> int:
        """
        String width when the string is displayed in a terminal.

        See :func:`line_width` for more information.

        """

        return sum(line_width(s) for s in self._parts if isinstance(s, str))

    @functools.cached_property
    def len(self) -> int:
        """
        Line length in bytes, ignoring all colors.

        """

        return sum(len(s) for s in self._parts if isinstance(s, str))

    def __len__(self) -> int:
        return self.len

    def __bool__(self) -> bool:
        return self.len > 0

    def iter(self) -> _t.Iterator[yuio.color.Color | str]:
        """
        Iterate over raw parts of the string,
        i.e. the underlying list of strings and colors.

        """

        return self._parts.__iter__()

    def __iter__(self) -> _t.Iterator[yuio.color.Color | str]:
        return self.iter()

    def wrap(
        self,
        width: int,
        /,
        *,
        preserve_spaces: bool = False,
        preserve_newlines: bool = True,
        break_long_words: bool = True,
        break_long_nowrap_words: bool = False,
        first_line_indent: AnyString = "",
        continuation_indent: AnyString = "",
    ) -> list[ColorizedString]:
        r"""
        Wrap a long line of text into multiple lines.

        :param preserve_spaces:
            if set to :data:`True`, all spaces are preserved.
            Otherwise, consecutive spaces are collapsed into a single space.
            Note that tabs are always treated as a single space.
        :param preserve_newlines:
            if set to :data:`True` (default), text is additionally wrapped
            on newline characters. When this happens, the newline sequence that wrapped
            the line will be placed into :attr:`~ColorizedString.explicit_newline`.

            If set to :data:`False`, newlines are treated as whitespaces.
        :param break_long_words:
            if set to :data:`True` (default), words that don't fit into a single line
            will be split into multiple lines.
        :param break_long_nowrap_words:
            if set to :data:`True`, :class:`NoWrap` words that don't fit
            into a single line will be split into multiple lines.
        :param first_line_indent:
            a string that will be prepended before the first line.
        :param continuation_indent:
            a string that will be prepended before all subsequent lines.
        :returns:
            a list of individual lines without newline characters at the end.
        :example:
            ::

                >>> ColorizedString("hello, world!\nit's a good day!").wrap(13)  # doctest: +NORMALIZE_WHITESPACE
                [<ColorizedString('hello, world!', explicit_newline='\n')>,
                <ColorizedString("it's a good")>,
                <ColorizedString('day!')>]

        """

        return _TextWrapper(
            width,
            preserve_spaces=preserve_spaces,
            preserve_newlines=preserve_newlines,
            break_long_words=break_long_words,
            break_long_nowrap_words=break_long_nowrap_words,
            first_line_indent=first_line_indent,
            continuation_indent=continuation_indent,
        ).wrap(self)

    def indent(
        self,
        first_line_indent: AnyString = "",
        continuation_indent: AnyString = "",
    ) -> ColorizedString:
        r"""
        Indent this string by the given sequence.

        :param first_line_indent:
            this will be appended to the first line in the string.
        :param continuation_indent:
            this will be appended to subsequent lines in the string.

        :example:
            ::

                >>> ColorizedString("hello, world!\nit's a good day!").indent("# ", "  ")
                <ColorizedString("# hello, world!\n  it's a good day!")>

        """

        res = ColorizedString()

        color: yuio.color.Color = yuio.color.Color.NONE
        cur_color: yuio.color.Color = yuio.color.Color.NONE
        needs_indent = True

        for part in self._parts:
            if isinstance(part, yuio.color.Color):
                color = part
                continue

            for line in part.splitlines(keepends=True):
                if needs_indent:
                    if cur_color != yuio.color.Color.NONE:
                        res += yuio.color.Color.NONE
                    res += first_line_indent
                    first_line_indent = ColorizedString(continuation_indent)

                if color and (needs_indent or color != cur_color):
                    res += color
                    cur_color = color

                res += line

                needs_indent = line.endswith("\n")

        if color and color != cur_color:
            res += color

        return res

    def percent_format(self, args: _t.Any, theme: yuio.theme.Theme) -> ColorizedString:
        """
        Format colorized string as if with ``%``-formatting
        (i.e. `printf-style formatting`__).

        Calling this method is equivalent to using ``%`` operator with this string
        on its left hand side.

        __ https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting

        :param args:
            arguments for formatting. Can be either a tuple of a dict. Any other value
            will be converted to a tuple of one element.
        :param theme:
            theme will be used to colorize ``repr`` values.
        :returns:
            formatted string.
        :raises:
            :class:`TypeError` if formatting fails.

        """

        return ColorizedString(_percent_format(self, args))

    def __add__(self, rhs: AnyString) -> ColorizedString:
        copy = ColorizedString(self)
        copy += rhs
        return copy

    def __radd__(self, lhs: AnyString) -> ColorizedString:
        copy = ColorizedString(lhs)
        copy += self
        return copy

    def __iadd__(self, rhs: AnyString) -> ColorizedString:
        if isinstance(rhs, (str, yuio.color.Color)):
            if rhs:
                self._parts.append(rhs)
        elif isinstance(rhs, ColorizedString):
            self._parts.extend(rhs._parts)
        else:
            self._parts.extend(rhs)

        self.__dict__.pop("width", None)
        self.__dict__.pop("len", None)

        return self

    def process_colors(self, term: yuio.term.Term, /) -> list[str]:
        """
        Convert colors in this string to ANSI escape sequences.

        """

        out: list[str] = []

        color: yuio.color.Color | None = None
        cur_color: yuio.color.Color | None = None

        for part in self._parts:
            if isinstance(part, yuio.color.Color):
                color = part
            else:
                if color != cur_color:
                    if color is not None:
                        out.append(yuio.term.color_to_code(color, term))
                    cur_color = color
                out.append(part)

        if color and color != cur_color:
            out.append(yuio.term.color_to_code(color, term))

        return out

    def __str__(self) -> str:
        return "".join(c for c in self._parts if isinstance(c, str))

    def __repr__(self) -> str:
        if self.explicit_newline:
            return f"<ColorizedString({str(self)!r}, explicit_newline={self.explicit_newline!r})>"
        else:
            return f"<ColorizedString({str(self)!r})>"


RawString: _t.TypeAlias = _t.Iterable[yuio.color.Color | str]
"""
Raw colorized string. This is the underlying type for :class:`ColorizedString`.

"""

AnyString: _t.TypeAlias = _t.Union[str, yuio.color.Color, RawString, ColorizedString]  # type: ignore
"""
Any string (i.e. a :class:`str`, a raw colorized string, or a normal colorized string).

"""


_S_SYNTAX = re.compile(
    r"""
        %                               # Percent
        (?:\((?P<mapping>[^)]*)\))?     # Mapping key
        (?P<flag>[#0\-+ ])*             # Conversion Flag
        (?P<width>\*|\d+)?              # Field width
        (?:\.(?P<precision>\*|\d*))?    # Precision
        [hlL]?                          # Unused length modifier
        (?P<format>.)                   # Conversion type
    """,
    re.VERBOSE,
)


def _percent_format(s: ColorizedString, args: object) -> list[yuio.color.Color | str]:
    seen_mapping = False
    arg_index = 0
    raw: list[yuio.color.Color | str] = []
    color: yuio.color.Color | None = None
    cur_color: yuio.color.Color | None = None
    for part in s:
        if isinstance(part, str):
            if color != cur_color:
                if color is not None:
                    raw.append(color)
                cur_color = color
            pos = 0
            for match in _S_SYNTAX.finditer(part):
                if pos < match.start():
                    raw.append(part[pos : match.start()])
                seen_mapping = seen_mapping or bool(match.group("mapping"))
                arg_index, replaced = _percent_format_repl(
                    match, args, arg_index, cur_color or yuio.color.Color()
                )
                if isinstance(replaced, str):
                    raw.append(replaced)
                else:
                    raw.extend(replaced)
                pos = match.end()
            if pos < len(part):
                raw.append(part[pos:])
        else:
            color = part

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

    return raw


def _percent_format_repl(
    match: _t.StrReMatch,
    args: object,
    arg_index: int,
    out_color: yuio.color.Color,
) -> tuple[int, str | ColorizedString]:
    if match.group("format") == "%":
        if match.group(0) != "%%":
            raise ValueError("unsupported format character '%'")
        return arg_index, "%"

    if match.group("format") in "rs":
        return _percent_format_repl_str(match, args, arg_index, out_color)

    if match.group("mapping"):
        fmt_args = args
    elif isinstance(args, tuple):
        begin = arg_index
        end = arg_index = (
            arg_index
            + 1
            + (match.group("width") == "*")
            + (match.group("precision") == "*")
        )
        fmt_args = args[begin:end]
    elif arg_index == 0:
        fmt_args = args
        arg_index += 1
    else:
        raise TypeError("not enough arguments for format string")

    return arg_index, match.group(0) % fmt_args


def _percent_format_repl_str(
    match: _t.StrReMatch,
    args: object,
    arg_index: int,
    out_color: yuio.color.Color,
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

    if match.group("format") == "r":
        fmt_arg_r = repr(fmt_arg)
        if width is None and precision is None:
            return arg_index, fmt_arg_r
        else:
            fmt_arg = ColorizedString(fmt_arg_r)
    elif not isinstance(fmt_arg, ColorizedString):
        fmt_arg_s = str(fmt_arg)
        if width is None and precision is None:
            return arg_index, fmt_arg_s
        else:
            fmt_arg = ColorizedString(fmt_arg_s)

    if precision is not None and fmt_arg.width > precision:
        raw: list[yuio.color.Color | str] = []
        color = out_color
        cur_color = out_color
        for part in fmt_arg:
            if precision <= 0:
                break
            if isinstance(part, str):
                if color != cur_color:
                    raw.append(color)
                    cur_color = color

                part_width = line_width(part)
                if part_width <= precision:
                    raw.append(part)
                    precision -= part_width
                elif part.isascii():
                    raw.append(part[:precision])
                    break
                else:
                    for j, ch in enumerate(part):
                        precision -= line_width(ch)
                        if precision == 0:
                            raw.append(part[: j + 1])
                            break
                        elif precision < 0:
                            raw.append(part[:j])
                            raw.append(" ")
                            break
                    break
            else:
                color = out_color | part
        if cur_color != out_color:
            raw.append(out_color)
        fmt_arg = ColorizedString(raw)
    else:
        raw: list[yuio.color.Color | str] = []
        color = out_color
        cur_color = out_color
        for part in fmt_arg:
            if isinstance(part, str):
                if color != cur_color:
                    raw.append(color)
                    cur_color = color
                raw.append(part)
            else:
                color = out_color | part
        if cur_color != out_color:
            raw.append(out_color)
        fmt_arg = ColorizedString(raw)

    if width is not None:
        spacing = " " * (abs(width) - fmt_arg.width)
        if match.group("flag") == "-" or width < 0:
            fmt_arg = fmt_arg + spacing
        else:
            fmt_arg = spacing + fmt_arg

    return arg_index, fmt_arg


_SPACE_TRANS = str.maketrans("\r\n\t\v\b\f", "      ")

_WORD_PUNCT = r'[\w!"\'&.,?]'
_LETTER = r"[^\d\W]"
_NOWHITESPACE = r"[^ \r\n\t\v\b\f]"

# Copied from textwrap with some modifications in newline handling
_WORDSEP_RE = re.compile(
    r"""
    ( # newlines and line feeds are matched one-by-one
        \v?(?:\r\n|\r|\n)
    | # any whitespace
        [ \t\v\b\f]+
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
_WORDSEP_NL_RE = re.compile(r"(\v?(?:\r\n|\r|\n))")


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
        first_line_indent: AnyString = "",
        continuation_indent: AnyString = "",
    ):
        self.width: int = width
        self.preserve_spaces: bool = preserve_spaces
        self.preserve_newlines: bool = preserve_newlines
        self.break_long_words: bool = break_long_words
        self.break_long_nowrap_words: bool = break_long_nowrap_words
        self.first_line_indent: ColorizedString = ColorizedString(first_line_indent)
        self.continuation_indent: ColorizedString = ColorizedString(continuation_indent)

        if (
            self.width - self.first_line_indent.width <= 1
            or self.width - self.continuation_indent.width <= 1
        ):
            self.width = (
                max(self.first_line_indent.width, self.continuation_indent.width) + 2
            )

        self.lines: list[ColorizedString] = []

        self.current_line: list[yuio.color.Color | str] = [yuio.color.Color.NONE]
        if self.first_line_indent:
            self.current_line.extend(list(self.first_line_indent))
            self.current_line.append(yuio.color.Color.NONE)
        self.current_line_width: int = self.first_line_indent.width
        self.current_color: yuio.color.Color = yuio.color.Color.NONE
        self.current_line_is_nonempty: bool = False

    def _flush_line(self, explicit_newline=""):
        self.lines.append(
            ColorizedString(self.current_line, explicit_newline=explicit_newline)
        )
        self.current_line: list[yuio.color.Color | str] = []
        if self.continuation_indent:
            self.current_line.append(yuio.color.Color.NONE)
            self.current_line.extend(list(self.continuation_indent))
        self.current_line.append(self.current_color)
        self.current_line_width: int = self.continuation_indent.width
        self.current_line_is_nonempty = False

    def _append_word(self, word: str, word_width: int):
        self.current_line_is_nonempty = True
        self.current_line.append(word)
        self.current_line_width += word_width

    def _append_color(self, color: yuio.color.Color):
        if color != self.current_color:
            self.current_color = color
            self.current_line.append(color)

    def _append_word_with_breaks(self, word: str, word_width: int):
        while self.current_line_width + word_width > self.width:
            word_head_len = word_head_width = 0

            for c in word:
                c_width = line_width(c)
                if self.current_line_width + word_head_width + c_width > self.width:
                    break
                word_head_len += 1
                word_head_width += c_width

            self._append_word(word[:word_head_len], word_head_width)

            word = word[word_head_len:]
            word_width -= word_head_width

            self._flush_line()

        if word:
            self._append_word(word, word_width)

    def wrap(self, text: ColorizedString) -> list[ColorizedString]:
        need_space_before_word = False
        at_line_beginning = True

        for part in text:
            if isinstance(part, yuio.color.Color):
                if (
                    need_space_before_word
                    and self.current_line_width + need_space_before_word <= self.width
                ):
                    # Make sure any space that was issued before the color is flushed.
                    self._append_word(" ", 1)
                    need_space_before_word = False
                self._append_color(part)
                continue

            nowrap = False
            if isinstance(part, Esc):
                words = [part]
            elif isinstance(part, NoWrap):
                words = _WORDSEP_NL_RE.split(part)
                nowrap = True
            else:
                words = _WORDSEP_RE.split(part)

            for word in words:
                if not word:
                    continue

                if "\v" in word or (
                    word in ("\r", "\n", "\r\n") and self.preserve_newlines
                ):
                    self._flush_line(explicit_newline=word)
                    need_space_before_word = False
                    at_line_beginning = True
                    continue

                if word.isspace():
                    if nowrap:
                        word = word.translate(_SPACE_TRANS)
                        self._append_word(word, len(word))
                    elif at_line_beginning or self.preserve_spaces:
                        word = word.translate(_SPACE_TRANS)
                        self._append_word_with_breaks(word, len(word))
                    else:
                        need_space_before_word = True
                    continue

                word_width = line_width(word)

                if (
                    self.current_line_width + word_width + need_space_before_word
                    <= self.width
                ):
                    # Word fits onto the current line.
                    if need_space_before_word:
                        self._append_word(" ", 1)
                    self._append_word(word, word_width)
                else:
                    # Word doesn't fit, so we start a new line.
                    if self.current_line_is_nonempty:
                        self._flush_line()
                    if (
                        (nowrap and self.break_long_nowrap_words)
                        or (not nowrap and self.break_long_words)
                        and not isinstance(word, Esc)
                    ):
                        # We will break the word in the middle if it doesn't fit
                        # onto the whole line.
                        self._append_word_with_breaks(word, word_width)
                    else:
                        self._append_word(word, word_width)

                need_space_before_word = False
                at_line_beginning = False

        if self.current_line or not self.lines or self.lines[-1].explicit_newline:
            self._flush_line()

        return self.lines
