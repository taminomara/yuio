import contextlib
import io
import os
import sys

import pytest

import yuio.term
import yuio.theme
from yuio import _typing as _t


class TestColor:
    @pytest.mark.parametrize(
        "color,expect",
        [
            (yuio.term.Color.NONE | yuio.term.Color.NONE, yuio.term.Color.NONE),
            (yuio.term.Color.NONE | yuio.term.Color.FORE_RED, yuio.term.Color.FORE_RED),
            (yuio.term.Color.NONE | yuio.term.Color.BACK_RED, yuio.term.Color.BACK_RED),
            (
                yuio.term.Color.FORE_BLUE | yuio.term.Color.FORE_RED,
                yuio.term.Color.FORE_RED,
            ),
            (
                yuio.term.Color.BACK_BLUE | yuio.term.Color.BACK_RED,
                yuio.term.Color.BACK_RED,
            ),
            (
                yuio.term.Color.FORE_RED | yuio.term.Color.BACK_BLUE,
                yuio.term.Color(
                    fore=yuio.term.ColorValue(1), back=yuio.term.ColorValue(4)
                ),
            ),
            (
                yuio.term.Color.FORE_RED | yuio.term.Color.STYLE_BOLD,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=True),
            ),
            (
                yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=True),
            ),
            (
                yuio.term.Color.FORE_RED | yuio.term.Color.STYLE_DIM,
                yuio.term.Color(fore=yuio.term.ColorValue(1), dim=True),
            ),
            (
                yuio.term.Color.STYLE_DIM | yuio.term.Color.FORE_RED,
                yuio.term.Color(fore=yuio.term.ColorValue(1), dim=True),
            ),
            (
                yuio.term.Color.FORE_RED
                | yuio.term.Color.STYLE_BOLD
                | yuio.term.Color.STYLE_DIM,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=True, dim=True),
            ),
            (
                yuio.term.Color.FORE_RED
                | yuio.term.Color.STYLE_BOLD
                | yuio.term.Color.STYLE_NORMAL,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=False, dim=False),
            ),
            (
                yuio.term.Color.FORE_RED
                | yuio.term.Color.STYLE_DIM
                | yuio.term.Color.STYLE_NORMAL,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=False, dim=False),
            ),
            (
                yuio.term.Color.FORE_RED
                | yuio.term.Color.STYLE_DIM
                | yuio.term.Color.STYLE_NORMAL
                | yuio.term.Color.STYLE_DIM,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=False, dim=True),
            ),
            (
                yuio.term.Color.FORE_RED
                | yuio.term.Color.STYLE_DIM
                | yuio.term.Color.STYLE_NORMAL
                | yuio.term.Color.STYLE_BOLD,
                yuio.term.Color(fore=yuio.term.ColorValue(1), bold=True, dim=False),
            ),
        ],
    )
    def test_combine(self, color, expect):
        assert color == expect

    @pytest.mark.parametrize(
        "color,cap,expect",
        [
            (yuio.term.Color.NONE, yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.NONE, yuio.term.ColorSupport.ANSI, "\x1b[m"),
            (yuio.term.Color.NONE, yuio.term.ColorSupport.ANSI_256, "\x1b[m"),
            (yuio.term.Color.NONE, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[m"),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.ANSI, "\x1b[;31m"),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.ANSI_256, "\x1b[;31m"),
            (yuio.term.Color.FORE_RED, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;31m"),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.NONE, ""),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.ANSI, "\x1b[;41m"),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.ANSI_256, "\x1b[;41m"),
            (yuio.term.Color.BACK_RED, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;41m"),
            (yuio.term.Color.fore_from_hex("#338F15"), yuio.term.ColorSupport.NONE, ""),
            (
                yuio.term.Color.fore_from_hex("#338F15"),
                yuio.term.ColorSupport.ANSI,
                "\x1b[;32m",
            ),
            (
                yuio.term.Color.fore_from_hex("#338F15"),
                yuio.term.ColorSupport.ANSI_256,
                "\x1b[;38;5;64m",
            ),
            (
                yuio.term.Color.fore_from_hex("#338F15"),
                yuio.term.ColorSupport.ANSI_TRUE,
                "\x1b[;38;2;51;143;21m",
            ),
            (yuio.term.Color.back_from_hex("#338F15"), yuio.term.ColorSupport.NONE, ""),
            (
                yuio.term.Color.back_from_hex("#338F15"),
                yuio.term.ColorSupport.ANSI,
                "\x1b[;42m",
            ),
            (
                yuio.term.Color.back_from_hex("#338F15"),
                yuio.term.ColorSupport.ANSI_256,
                "\x1b[;48;5;64m",
            ),
            (
                yuio.term.Color.back_from_hex("#338F15"),
                yuio.term.ColorSupport.ANSI_TRUE,
                "\x1b[;48;2;51;143;21m",
            ),
        ],
    )
    def test_as_code(self, color: yuio.term.Color, cap, expect):
        term = yuio.term.Term(None, color_support=cap)  # type: ignore
        assert color.as_code(term) == expect

    @pytest.mark.parametrize(
        "colors,coeffs,expect",
        [
            (
                [yuio.term.Color.FORE_RED, yuio.term.Color.FORE_GREEN],
                [i / 4 for i in range(5)],
                [yuio.term.Color.FORE_RED] * 5,
            ),
            (
                [yuio.term.Color.FORE_RED, yuio.term.Color.fore_from_hex("#AA0000")],
                [i / 4 for i in range(5)],
                [yuio.term.Color.FORE_RED] * 5,
            ),
            (
                [yuio.term.Color.fore_from_hex("#AA0000"), yuio.term.Color.FORE_RED],
                [i / 4 for i in range(5)],
                [yuio.term.Color.fore_from_hex("#AA0000")] * 5,
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ],
                [i / 4 for i in range(5)],
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#7F2A00"),
                    yuio.term.Color.fore_from_hex("#555500"),
                    yuio.term.Color.fore_from_hex("#2A7F00"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ],
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                    yuio.term.Color.fore_from_hex("#0000AA"),
                ],
                [i / 8 for i in range(9)],
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#7F2A00"),
                    yuio.term.Color.fore_from_hex("#555500"),
                    yuio.term.Color.fore_from_hex("#2A7F00"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                    yuio.term.Color.fore_from_hex("#007F2A"),
                    yuio.term.Color.fore_from_hex("#005555"),
                    yuio.term.Color.fore_from_hex("#002A7F"),
                    yuio.term.Color.fore_from_hex("#0000AA"),
                ],
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ],
                [0, 0.5, 1],
                [
                    yuio.term.Color.fore_from_hex("#AA0000"),
                    yuio.term.Color.fore_from_hex("#555500"),
                    yuio.term.Color.fore_from_hex("#00AA00"),
                ],
            ),
            (
                [
                    yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.back_from_hex("#00AA00"),
                ],
                [0, 0.5, 1],
                [
                    yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.back_from_hex("#005555"),
                    yuio.term.Color.back_from_hex("#00AA00"),
                ],
            ),
            (
                [
                    yuio.term.Color.fore_from_hex("#AA0000")
                    | yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.fore_from_hex("#00AA00")
                    | yuio.term.Color.back_from_hex("#00AA00"),
                ],
                [0, 0.5, 1],
                [
                    yuio.term.Color.fore_from_hex("#AA0000")
                    | yuio.term.Color.back_from_hex("#0000AA"),
                    yuio.term.Color.fore_from_hex("#555500")
                    | yuio.term.Color.back_from_hex("#005555"),
                    yuio.term.Color.fore_from_hex("#00AA00")
                    | yuio.term.Color.back_from_hex("#00AA00"),
                ],
            ),
        ],
    )
    def test_lerp(self, colors, coeffs, expect):
        lerp = yuio.term.Color.lerp(*colors)
        result = [lerp(c) for c in coeffs]
        assert result == expect

    @pytest.mark.parametrize(
        "color,expect",
        [
            (
                yuio.term.ColorValue(0).lighten(0.5),
                yuio.term.ColorValue((127, 127, 127)),
            ),
            (yuio.term.ColorValue(0).darken(0.5), yuio.term.ColorValue((0, 0, 0))),
            (
                yuio.term.ColorValue(7).lighten(0.5),
                yuio.term.ColorValue((255, 255, 255)),
            ),
            (
                yuio.term.ColorValue(7).darken(0.5),
                yuio.term.ColorValue((127, 127, 127)),
            ),
            (
                yuio.term.ColorValue.from_hex("#005555").lighten(0.5),
                yuio.term.ColorValue.from_hex("#00AAAA"),
            ),
            (
                yuio.term.ColorValue.from_hex("#005555").darken(0.5),
                yuio.term.ColorValue.from_hex("#002A2A"),
            ),
            (yuio.term.ColorValue("0").darken(0.5), yuio.term.ColorValue("0")),
            (
                yuio.term.ColorValue.from_hex("#005555").match_luminosity(
                    yuio.term.ColorValue.from_hex("#002A2A")
                ),
                yuio.term.ColorValue.from_hex("#002A2A"),
            ),
            (
                yuio.term.ColorValue.from_hex("#005555").match_luminosity(
                    yuio.term.ColorValue.from_hex("#AA4700")
                ),
                yuio.term.ColorValue.from_hex("#00AAAA"),
            ),
        ],
    )
    def test_color_operations(self, color, expect):
        assert color == expect


class TestColorizedString:
    @pytest.mark.parametrize(
        "text,width,length",
        [
            (yuio.term.ColorizedString(), 0, 0),
            (yuio.term.ColorizedString([]), 0, 0),
            (yuio.term.ColorizedString(""), 0, 0),
            (yuio.term.ColorizedString("abc"), 3, 3),
            (yuio.term.ColorizedString("абв"), 3, 3),
            (yuio.term.ColorizedString("a\nb"), 3, 3),
            (yuio.term.ColorizedString("👻"), 2, 1),
            (yuio.term.ColorizedString(["abc", "def"]), 6, 6),
            (yuio.term.ColorizedString(["abc", "👻"]), 5, 4),
            (yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "abc", "def"]), 6, 6),
            (yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "abc", "👻"]), 5, 4),
            (
                yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "abc", "", "def"]),
                6,
                6,
            ),
        ],
    )
    def test_width_and_len(self, text, width, length):
        assert text.width == width
        assert text.len == len(text) == length
        assert bool(text) is (len(text) > 0)

    @pytest.mark.parametrize(
        "text,args,expect",
        [
            (
                [""],
                (),
                [""],
            ),
            (
                ["hello world!"],
                (),
                ["hello world!"],
            ),
            (
                ["hello %s!"],
                "username",
                ["hello username!"],
            ),
            (
                ["hello %r!"],
                "username",
                ["hello 'username'!"],
            ),
            (
                ["hello %05.2f!"],
                1.5,
                ["hello 01.50!"],
            ),
            (
                ["hello %05.2lf!"],
                1.5,
                ["hello 01.50!"],
            ),
            (
                ["hello %s %% %s!"],
                (1, 2),
                ["hello 1 % 2!"],
            ),
            (
                ["hello %s"],
                {"a": "b"},
                ["hello {'a': 'b'}"],
            ),
            (
                ["hello %s %(a)s"],
                {"a": "b"},
                ["hello {'a': 'b'} b"],
            ),
        ],
    )
    def test_format(self, text, args, expect):
        formatted = yuio.term.ColorizedString(text) % args
        assert formatted._parts == expect

    @pytest.mark.parametrize(
        "text,width,kwargs,expect",
        [
            (
                ["hello world!"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                ],
            ),
            (
                ["hello world! 15"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!", " ", "15"],
                ],
            ),
            (
                ["hello world! 👻"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!", " ", "👻"],
                ],
            ),
            (
                ["hello world! 👻👻"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!", " "],
                    [yuio.term.Color.NONE, "👻👻"],
                ],
            ),
            (
                ["hello world! this will wrap"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!", " "],
                    [yuio.term.Color.NONE, "this", " ", "will", " ", "wrap"],
                ],
            ),
            (
                ["hello world!     this will wrap"],
                15,
                {"preserve_spaces": False},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                    [yuio.term.Color.NONE, "this", " ", "will", " ", "wrap"],
                ],
            ),
            (
                ["hello     world!     this     will     wrap"],
                15,
                {"preserve_spaces": False},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                    [yuio.term.Color.NONE, "this", " ", "will", " ", "wrap"],
                ],
            ),
            (
                ["this-will-wrap-on-hyphen"],
                15,
                {"break_on_hyphens": True},
                [
                    [yuio.term.Color.NONE, "this-", "will-", "wrap-"],
                    [yuio.term.Color.NONE, "on-", "hyphen"],
                ],
            ),
            (
                ["this.will.not.wrap.on.hyphen.this.is.too.long"],
                15,
                {"break_on_hyphens": True},
                [
                    [yuio.term.Color.NONE, "this.will.not.w"],
                    [yuio.term.Color.NONE, "rap.on.hyphen.t"],
                    [yuio.term.Color.NONE, "his.is.too.long"],
                ],
            ),
            (
                ["this-will-not-wrap-on-hyphen-this-is-too-long"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "this-will-not-w"],
                    [yuio.term.Color.NONE, "rap-on-hyphen-t"],
                    [yuio.term.Color.NONE, "his-is-too-long"],
                ],
            ),
            (
                ["newlines will\nbe\nhonored!"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "newlines", " ", "will"],
                    [yuio.term.Color.NONE, "be"],
                    [yuio.term.Color.NONE, "honored!"],
                ],
            ),
            (
                ["space before nl    \nis removed"],
                15,
                {"preserve_spaces": False},
                [
                    [yuio.term.Color.NONE, "space", " ", "before", " ", "nl"],
                    [yuio.term.Color.NONE, "is", " ", "removed"],
                ],
            ),
            (
                ["space after nl\n    is kept"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "space", " ", "after", " ", "nl"],
                    [yuio.term.Color.NONE, "    ", "is", " ", "kept"],
                ],
            ),
            (
                ["wo", "rd wo", "rd"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "wo", "rd", " ", "wo", "rd"],
                ],
            ),
            pytest.param(
                ["wo", "rd wo", "rd"],
                7,
                {},
                [
                    [yuio.term.Color.NONE, "wo", "rd"],
                    [yuio.term.Color.NONE, "wo", "rd"],
                ],
                marks=pytest.mark.skip(
                    "this is a bug which I'm not sure how to fix atm"
                ),
            ),
            (
                ["hello world!"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                ],
            ),
            (
                ["hello   world!"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", "   ", "world!"],
                ],
            ),
            (
                ["hello     world!"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", "     "],
                    [yuio.term.Color.NONE, "world!"],
                ],
            ),
            (
                ["hello                    world"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", "          "],
                    [yuio.term.Color.NONE, "          ", "world"],
                ],
            ),
            (
                ["hello                    longlongworld"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", "          "],
                    [yuio.term.Color.NONE, "          "],
                    [yuio.term.Color.NONE, "longlongworld"],
                ],
            ),
            (
                ["hello ", yuio.term.Color.STYLE_BOLD, "world", yuio.term.Color.NONE],
                15,
                {},
                [
                    [
                        yuio.term.Color.NONE,
                        "hello",
                        " ",
                        yuio.term.Color.STYLE_BOLD,
                        "world",
                        yuio.term.Color.NONE,
                    ]
                ],
            ),
            (
                [],
                15,
                {},
                [
                    [yuio.term.Color.NONE],
                ],
            ),
            (
                [""],
                15,
                {},
                [
                    [yuio.term.Color.NONE],
                ],
            ),
            (
                ["12345678901234 12345"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "12345678901234", " "],
                    [yuio.term.Color.NONE, "12345"],
                ],
            ),
            (
                ["Hello line break", yuio.term.Color.NONE],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "Hello", " ", "line", " "],
                    [yuio.term.Color.NONE, "break"],
                ],
            ),
            (
                [yuio.term.Color.STYLE_BOLD, yuio.term.Color.NONE],
                15,
                {},
                [
                    [
                        yuio.term.Color.NONE,
                        yuio.term.Color.STYLE_BOLD,
                        yuio.term.Color.NONE,
                    ],
                ],
            ),
            (
                [yuio.term.Color.STYLE_BOLD, "", yuio.term.Color.NONE],
                15,
                {},
                [
                    [
                        yuio.term.Color.NONE,
                        yuio.term.Color.STYLE_BOLD,
                        yuio.term.Color.NONE,
                    ],
                ],
            ),
            (
                ["break\n", yuio.term.Color.NONE],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "break"],
                    [yuio.term.Color.NONE],
                ],
            ),
            (
                ["break\n"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "break"],
                    [yuio.term.Color.NONE],
                ],
            ),
            (
                [
                    "usage: app.py train [-h] [-v] [--force-color | --force-no-color] [-o {path}] <data>"
                ],
                100,
                {},
                [
                    [
                        yuio.term.Color.NONE,
                        "usage:",
                        " ",
                        "app.py",
                        " ",
                        "train",
                        " ",
                        "[-h]",
                        " ",
                        "[-v]",
                        " ",
                        "[--force-color",
                        " ",
                        "|",
                        " ",
                        "--force-no-color]",
                        " ",
                        "[-o",
                        " ",
                        "{path}]",
                        " ",
                        "<data>",
                    ]
                ],
            ),
            (
                [
                    yuio.term.Color.FORE_MAGENTA,
                    "usage: ",
                    yuio.term.Color.NONE,
                    yuio.term.Color.NONE,
                    "app.py train",
                    yuio.term.Color.NONE,
                    yuio.term.Color.NONE,
                    " ",
                    yuio.term.Color.NONE,
                    "[",
                    yuio.term.Color.FORE_BLUE,
                    "-h",
                    yuio.term.Color.NONE,
                    "]",
                    yuio.term.Color.NONE,
                    " ",
                    yuio.term.Color.NONE,
                    "[",
                    yuio.term.Color.FORE_BLUE,
                    "-v",
                    yuio.term.Color.NONE,
                    "]",
                    yuio.term.Color.NONE,
                    " [",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_BLUE,
                    "--force-color",
                    yuio.term.Color.NONE,
                    " | ",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_BLUE,
                    "--force-no-color",
                    yuio.term.Color.NONE,
                    "] ",
                    yuio.term.Color.NONE,
                    "[",
                    yuio.term.Color.FORE_BLUE,
                    "-o",
                    yuio.term.Color.NONE,
                    " ",
                    yuio.term.Color.FORE_MAGENTA,
                    "",
                    yuio.term.Color.NONE,
                    "{",
                    yuio.term.Color.FORE_MAGENTA,
                    "path",
                    yuio.term.Color.NONE,
                    "}",
                    yuio.term.Color.FORE_MAGENTA,
                    "",
                    yuio.term.Color.NONE,
                    "]",
                    yuio.term.Color.NONE,
                    " ",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_MAGENTA,
                    "",
                    yuio.term.Color.NONE,
                    "<",
                    yuio.term.Color.FORE_MAGENTA,
                    "data",
                    yuio.term.Color.NONE,
                    ">",
                    yuio.term.Color.FORE_MAGENTA,
                    "",
                ],
                100,
                {},
                [
                    [
                        yuio.term.Color.NONE,
                        yuio.term.Color.FORE_MAGENTA,
                        "usage:",
                        " ",
                        yuio.term.Color.NONE,
                        "app.py",
                        " ",
                        "train",
                        " ",
                        "[",
                        yuio.term.Color.FORE_BLUE,
                        "-h",
                        yuio.term.Color.NONE,
                        "]",
                        " ",
                        "[",
                        yuio.term.Color.FORE_BLUE,
                        "-v",
                        yuio.term.Color.NONE,
                        "]",
                        " ",
                        "[",
                        yuio.term.Color.FORE_BLUE,
                        "--force-color",
                        yuio.term.Color.NONE,
                        " ",
                        "|",
                        " ",
                        yuio.term.Color.FORE_BLUE,
                        "--force-no-color",
                        yuio.term.Color.NONE,
                        "]",
                        " ",
                        "[",
                        yuio.term.Color.FORE_BLUE,
                        "-o",
                        yuio.term.Color.NONE,
                        " ",
                        yuio.term.Color.FORE_MAGENTA,
                        yuio.term.Color.NONE,
                        "{",
                        yuio.term.Color.FORE_MAGENTA,
                        "path",
                        yuio.term.Color.NONE,
                        "}",
                        yuio.term.Color.FORE_MAGENTA,
                        yuio.term.Color.NONE,
                        "]",
                        " ",
                        yuio.term.Color.FORE_MAGENTA,
                        yuio.term.Color.NONE,
                        "<",
                        yuio.term.Color.FORE_MAGENTA,
                        "data",
                        yuio.term.Color.NONE,
                        ">",
                        yuio.term.Color.FORE_MAGENTA,
                    ]
                ],
            ),
            (
                ["single string"],
                100,
                {"first_line_indent": ">>"},
                [
                    [
                        yuio.term.Color.NONE,
                        ">>",
                        yuio.term.Color.NONE,
                        "single",
                        " ",
                        "string",
                    ],
                ],
            ),
            (
                ["single string"],
                100,
                {"continuation_indent": ">>"},
                [
                    [yuio.term.Color.NONE, "single", " ", "string"],
                ],
            ),
            (
                ["single string"],
                13,
                {},
                [
                    [yuio.term.Color.NONE, "single", " ", "string"],
                ],
            ),
            (
                ["single string"],
                13,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "single", " "],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "string"],
                ],
            ),
            (
                ["foo bar baz"],
                8,
                {"first_line_indent": ">>>", "continuation_indent": "|"},
                [
                    [yuio.term.Color.NONE, ">>>", yuio.term.Color.NONE, "foo", " "],
                    [
                        yuio.term.Color.NONE,
                        "|",
                        yuio.term.Color.NONE,
                        "bar",
                        " ",
                        "baz",
                    ],
                ],
            ),
            (
                ["word werywerylongunbreakableword"],
                8,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "word", " "],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "werywe"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "rylong"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "unbrea"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "kablew"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "ord"],
                ],
            ),
            (
                ["werywerylongunbreakableword"],
                8,
                {"first_line_indent": ">>>", "continuation_indent": "."},
                [
                    [yuio.term.Color.NONE, ">>>", yuio.term.Color.NONE, "weryw"],
                    [yuio.term.Color.NONE, ".", yuio.term.Color.NONE, "erylong"],
                    [yuio.term.Color.NONE, ".", yuio.term.Color.NONE, "unbreak"],
                    [yuio.term.Color.NONE, ".", yuio.term.Color.NONE, "ablewor"],
                    [yuio.term.Color.NONE, ".", yuio.term.Color.NONE, "d"],
                ],
            ),
            (
                ["single string", "\nnext string"],
                13,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "single", " "],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "string"],
                    [
                        yuio.term.Color.NONE,
                        "..",
                        yuio.term.Color.NONE,
                        "next",
                        " ",
                        "string",
                    ],
                ],
            ),
            (
                ["a\n\nb"],
                13,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "a"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "b"],
                ],
            ),
            (
                ["a\n"],
                13,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "a"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE],
                ],
            ),
            (
                ["\na"],
                13,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "a"],
                ],
            ),
            (
                ["\nwerywerylongunbreakableword"],
                13,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "werywerylon"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "gunbreakabl"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "eword"],
                ],
            ),
            (
                [yuio.term.Color.FORE_BLUE, "single string"],
                13,
                {
                    "first_line_indent": yuio.term.ColorizedString(
                        [yuio.term.Color.FORE_MAGENTA, ">>"]
                    ),
                    "continuation_indent": yuio.term.ColorizedString(
                        [yuio.term.Color.FORE_BLUE, ".."]
                    ),
                },
                [
                    [
                        yuio.term.Color.NONE,
                        yuio.term.Color.FORE_MAGENTA,
                        ">>",
                        yuio.term.Color.NONE,
                        yuio.term.Color.FORE_BLUE,
                        "single",
                        " ",
                    ],
                    [
                        yuio.term.Color.NONE,
                        yuio.term.Color.FORE_BLUE,
                        "..",
                        yuio.term.Color.FORE_BLUE,
                        "string",
                    ],
                ],
            ),
        ],
    )
    def test_wrap(self, text, width, kwargs, expect):
        wrapped = yuio.term.ColorizedString(text).wrap(width, **kwargs)
        raw = [line._parts for line in wrapped]
        assert raw == expect

    @pytest.mark.parametrize(
        "text,first_line_indent,continuation_indent,expect",
        [
            (
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString(),
                [],
            ),
            (
                yuio.term.ColorizedString(""),
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString(),
                [],
            ),
            (
                yuio.term.ColorizedString("abc"),
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString(),
                [yuio.term.Color.NONE, "abc"],
            ),
            (
                yuio.term.ColorizedString("abc\n"),
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString(),
                [yuio.term.Color.NONE, "abc\n"],
            ),
            (
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                [],
            ),
            (
                yuio.term.ColorizedString(""),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                [],
            ),
            (
                yuio.term.ColorizedString("abc"),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                ["1", yuio.term.Color.NONE, "abc"],
            ),
            (
                yuio.term.ColorizedString("abc\n"),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                ["1", yuio.term.Color.NONE, "abc\n"],
            ),
            (
                yuio.term.ColorizedString(["abc", "def"]),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                ["1", yuio.term.Color.NONE, "abc", "def"],
            ),
            (
                yuio.term.ColorizedString("abc\ndef"),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                ["1", yuio.term.Color.NONE, "abc\n", "2", yuio.term.Color.NONE, "def"],
            ),
            (
                yuio.term.ColorizedString(["abc\n", "def"]),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                ["1", yuio.term.Color.NONE, "abc\n", "2", yuio.term.Color.NONE, "def"],
            ),
            (
                yuio.term.ColorizedString(["abc", "\n", "def"]),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                [
                    "1",
                    yuio.term.Color.NONE,
                    "abc",
                    "\n",
                    "2",
                    yuio.term.Color.NONE,
                    "def",
                ],
            ),
            (
                yuio.term.ColorizedString("abc\ndef\n"),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString("2"),
                [
                    "1",
                    yuio.term.Color.NONE,
                    "abc\n",
                    "2",
                    yuio.term.Color.NONE,
                    "def\n",
                ],
            ),
            (
                yuio.term.ColorizedString("abc\ndef"),
                yuio.term.ColorizedString("1"),
                yuio.term.ColorizedString(),
                ["1", yuio.term.Color.NONE, "abc\n", yuio.term.Color.NONE, "def"],
            ),
            (
                yuio.term.ColorizedString("abc\ndef"),
                yuio.term.ColorizedString(),
                yuio.term.ColorizedString("2"),
                [yuio.term.Color.NONE, "abc\n", "2", yuio.term.Color.NONE, "def"],
            ),
            (
                yuio.term.ColorizedString(["abc\ndef"]),
                yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "1"]),
                yuio.term.ColorizedString([yuio.term.Color.FORE_BLUE, "2"]),
                [
                    yuio.term.Color.FORE_RED,
                    "1",
                    yuio.term.Color.NONE,
                    "abc\n",
                    yuio.term.Color.FORE_BLUE,
                    "2",
                    yuio.term.Color.NONE,
                    "def",
                ],
            ),
            (
                yuio.term.ColorizedString([yuio.term.Color.FORE_YELLOW, "abc\ndef"]),
                yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "1"]),
                yuio.term.ColorizedString([yuio.term.Color.FORE_BLUE, "2"]),
                [
                    yuio.term.Color.FORE_RED,
                    "1",
                    yuio.term.Color.FORE_YELLOW,
                    "abc\n",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_BLUE,
                    "2",
                    yuio.term.Color.FORE_YELLOW,
                    "def",
                ],
            ),
            (
                yuio.term.ColorizedString(
                    ["abc\n", yuio.term.Color.FORE_YELLOW, "def\nhig"]
                ),
                yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "1"]),
                yuio.term.ColorizedString([yuio.term.Color.FORE_BLUE, "2"]),
                [
                    yuio.term.Color.FORE_RED,
                    "1",
                    yuio.term.Color.NONE,
                    "abc\n",
                    yuio.term.Color.FORE_BLUE,
                    "2",
                    yuio.term.Color.FORE_YELLOW,
                    "def\n",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_BLUE,
                    "2",
                    yuio.term.Color.FORE_YELLOW,
                    "hig",
                ],
            ),
            (
                yuio.term.ColorizedString(
                    ["abc", yuio.term.Color.FORE_YELLOW, "\ndef\nhig"]
                ),
                yuio.term.ColorizedString([yuio.term.Color.FORE_RED, "1"]),
                yuio.term.ColorizedString([yuio.term.Color.FORE_BLUE, "2"]),
                [
                    yuio.term.Color.FORE_RED,
                    "1",
                    yuio.term.Color.NONE,
                    "abc",
                    yuio.term.Color.FORE_YELLOW,
                    "\n",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_BLUE,
                    "2",
                    yuio.term.Color.FORE_YELLOW,
                    "def\n",
                    yuio.term.Color.NONE,
                    yuio.term.Color.FORE_BLUE,
                    "2",
                    yuio.term.Color.FORE_YELLOW,
                    "hig",
                ],
            ),
        ],
    )
    def test_indent(self, text, first_line_indent, continuation_indent, expect):
        indented = text.indent(first_line_indent, continuation_indent)
        assert indented._parts == expect


class MockOStream(io.StringIO):
    def __init__(
        self,
        out: "MockIStream",
        tty: bool,
        should_query_osc: bool,
        osc_response: _t.Optional[str],
    ):
        super().__init__()
        self.__out = out
        self.__tty = tty
        self.__should_query_osc = should_query_osc
        self.__osc_response = osc_response

    def isatty(self) -> bool:
        return self.__tty

    _OSC_Q = (
        "\x1b]10;?\x1b\\"
        "\x1b]11;?"
        "\x1b\\"
        "\x1b]4;0;?\x1b\\"
        "\x1b]4;1;?\x1b\\"
        "\x1b]4;2;?\x1b\\"
        "\x1b]4;3;?\x1b\\"
        "\x1b]4;4;?\x1b\\"
        "\x1b]4;5;?\x1b\\"
        "\x1b]4;6;?\x1b\\"
        "\x1b]4;7;?\x1b\\"
        "\x1b[c"
    )

    _OSC_R = (
        "\x1b]10;rgb:bfbf/bfbf/bfbf\x1b\\"
        "\x1b]11;rgb:0000/0000/0000\x1b\\"
        "\x1b]4;0;rgb:0000/0000/0000\x1b\\"
        "\x1b]4;1;rgb:d4d4/2c2c/3a3a\x1b\\"
        "\x1b]4;2;rgb:1c1c/a8a8/0000\x1b\\"
        "\x1b]4;3;rgb:c0c0/a0a0/0000\x1b\\"
        "\x1b]4;4;rgb:0000/5d5d/ffff\x1b\\"
        "\x1b]4;5;rgb:b1b1/4848/c6c6\x1b\\"
        "\x1b]4;6;rgb:0000/a8a8/9a9a\x1b\\"
        "\x1b]4;7;rgb:bfbf/bfbf/bfbf\x1b\\"
        "\x1b[?c"
    )

    def write(self, s) -> int:
        if s == self._OSC_Q and self.__osc_response != "":
            if not self.__should_query_osc:
                raise RuntimeError("terminal is not supposed to query OSC")
            self._add_to_out(self.__osc_response or self._OSC_R)
        ret = super().write(s)
        return ret

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def _add_to_out(self, s):
        pos = self.__out.tell()
        self.__out.seek(0, io.SEEK_END)
        self.__out.write(s)
        self.__out.seek(pos)
        self.__out.flush()
        self.__out._load_ch()


class MockIStream(io.StringIO):
    def __init__(
        self,
        tty: bool,
        responds_to_kbhit: int,
    ):
        super().__init__()
        self.__tty = tty
        self.__responds_to_kbhit = responds_to_kbhit

        self.__last_ch = super().read(1)

    def isatty(self) -> bool:
        return self.__tty

    def kbhit(self, timeout=0):
        if self.__responds_to_kbhit:
            self.__responds_to_kbhit -= 1
            return bool(self.__last_ch)
        else:
            return False  # i.e. timeout

    def getch(self):
        last_ch = self.__last_ch
        if not last_ch:
            raise EOFError()
        self.__last_ch = super().read(1)
        return last_ch.encode()

    def read(self, size=None):
        raise RuntimeError("term not supposed to use stream.read")

    def readline(self, size=None):
        raise RuntimeError("term not supposed to use stream.readline")

    def readlines(self, hint=-1):
        raise RuntimeError("term not supposed to use stream.readlines")

    def _load_ch(self):
        if not self.__last_ch:
            self.__last_ch = super().read(1)


@contextlib.contextmanager
def _set_cbreak():
    yield


@contextlib.contextmanager
def mock_term_io(
    i_tty: bool = False,
    o_tty: bool = False,
    should_query_osc: bool = False,
    responds_to_kbhit: int = False,
    is_foreground: bool = False,
    env: _t.Dict[str, str] = {},
    args: _t.List[str] = [],
    osc_response: _t.Optional[str] = "",
):
    istream = MockIStream(i_tty, responds_to_kbhit)
    ostream = MockOStream(istream, o_tty, should_query_osc, osc_response)

    old_env = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)

    old_args = sys.argv[1:]
    sys.argv[1:] = args

    old_getch, yuio.term._getch = yuio.term._getch, istream.getch
    old_kbhit, yuio.term._kbhit = yuio.term._kbhit, istream.kbhit
    old_is_foreground, yuio.term._is_foreground = (
        yuio.term._is_foreground,
        lambda _: is_foreground,
    )
    old_is_interactive_input, yuio.term._is_interactive_input = (
        yuio.term._is_interactive_input,
        lambda _: i_tty,
    )
    old_set_cbreak, yuio.term._set_cbreak = yuio.term._set_cbreak, _set_cbreak

    try:
        yield ostream
    finally:
        os.environ.clear()
        os.environ.update(old_env)

        sys.argv[1:] = old_args

        yuio.term._getch = old_getch
        yuio.term._kbhit = old_kbhit
        yuio.term._is_foreground = old_is_foreground
        yuio.term._is_interactive_input = old_is_interactive_input
        yuio.term._set_cbreak = old_set_cbreak


term_colors = yuio.term.TerminalColors(
    background=yuio.term.ColorValue.from_hex("#000000"),
    foreground=yuio.term.ColorValue.from_hex("#BFBFBF"),
    black=yuio.term.ColorValue.from_hex("#000000"),
    red=yuio.term.ColorValue.from_hex("#D42C3A"),
    green=yuio.term.ColorValue.from_hex("#1CA800"),
    yellow=yuio.term.ColorValue.from_hex("#C0A000"),
    blue=yuio.term.ColorValue.from_hex("#005DFF"),
    magenta=yuio.term.ColorValue.from_hex("#B148C6"),
    cyan=yuio.term.ColorValue.from_hex("#00A89A"),
    white=yuio.term.ColorValue.from_hex("#BFBFBF"),
    lightness=yuio.term.Lightness.DARK,
)


class TestTerm:
    @pytest.mark.parametrize(
        "level,ansi,ansi_256,ansi_true",
        [
            (yuio.term.ColorSupport.ANSI, True, False, False),
            (yuio.term.ColorSupport.ANSI_256, True, True, False),
            (yuio.term.ColorSupport.ANSI_TRUE, True, True, True),
        ],
    )
    def test_color_support(self, level, ansi, ansi_256, ansi_true):
        term = yuio.term.Term(None, color_support=level)  # type: ignore
        assert term.has_colors == ansi
        assert term.has_colors_256 == ansi_256
        assert term.has_colors_true == ansi_true

    @pytest.mark.parametrize(
        "level,move,query",
        [
            (yuio.term.InteractiveSupport.NONE, False, False),
            (yuio.term.InteractiveSupport.MOVE_CURSOR, True, False),
            (yuio.term.InteractiveSupport.FULL, True, True),
        ],
    )
    def test_interactive_support(self, level, move, query):
        term = yuio.term.Term(None, color_support=yuio.term.ColorSupport.ANSI, interactive_support=level)  # type: ignore
        assert term.can_move_cursor == move
        assert term.can_query_terminal == term.is_fully_interactive == query
        term = yuio.term.Term(None, color_support=yuio.term.ColorSupport.NONE, interactive_support=level)  # type: ignore
        assert (
            term.can_move_cursor
            == term.can_query_terminal
            == term.is_fully_interactive
            == False
        )

    @pytest.mark.parametrize(
        "kwargs,expected_term",
        [
            (
                {},
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {"env": {"TERM": "xterm"}},
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "i_tty": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "o_tty": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "i_tty": True,
                    "o_tty": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "is_foreground": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "i_tty": True,
                    "is_foreground": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "o_tty": True,
                    "is_foreground": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI,
                    "interactive_support": yuio.term.InteractiveSupport.MOVE_CURSOR,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI_256,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "truecolor"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": True,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": None,  # OSC query got no response
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": True,
                    "responds_to_kbhit": -1,
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI_256,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": None,  # kbhit responds, but no OSC result
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": True,
                    "responds_to_kbhit": -1,
                    "osc_response": "\x1b[?c",
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI_256,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": None,  # kbhit responds, but OSC is not properly supported
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": True,
                    "responds_to_kbhit": -1,
                    "osc_response": None,  # default response
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI_256,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": term_colors,  # Got the response!
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": True,
                    "responds_to_kbhit": 2,  # kbhit only responds twice
                    "osc_response": None,  # default response
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI_256,
                    "interactive_support": yuio.term.InteractiveSupport.FULL,
                    "terminal_colors": term_colors,  # Got the response!
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": False,
                    "args": ["--no-color"],
                },
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "env": {"TERM": "xterm", "COLORTERM": "yes", "FORCE_NO_COLOR": "1"},
                    "i_tty": True,
                    "o_tty": True,
                    "is_foreground": True,
                    "should_query_osc": False,
                },
                {
                    "color_support": yuio.term.ColorSupport.NONE,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {
                    "args": ["--force-color"],
                },
                {
                    "color_support": yuio.term.ColorSupport.ANSI,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
            (
                {"env": {"FORCE_COLOR": "1"}},
                {
                    "color_support": yuio.term.ColorSupport.ANSI,
                    "interactive_support": yuio.term.InteractiveSupport.NONE,
                    "terminal_colors": None,
                },
            ),
        ],
    )
    def test_capabilities_estimation(self, kwargs, expected_term):
        with mock_term_io(**kwargs) as ostream:
            term = yuio.term.get_term_from_stream(ostream)
            expected = yuio.term.Term(ostream, **expected_term)
            assert term == expected
