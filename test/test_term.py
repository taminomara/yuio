import pytest

import yuio.term
import yuio.theme


class TestColor:
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


class TestColorizedString:
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
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                    [yuio.term.Color.NONE, "👻👻"],
                ],
            ),
            (
                ["hello world! this will wrap"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                    [yuio.term.Color.NONE, "this", " ", "will", " ", "wrap"],
                ],
            ),
            (
                ["hello world!     this will wrap"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                    [yuio.term.Color.NONE, "this", " ", "will", " ", "wrap"],
                ],
            ),
            (
                ["hello     world!     this     will     wrap"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                    [yuio.term.Color.NONE, "this", " ", "will", " ", "wrap"],
                ],
            ),
            (
                ["this-will-wrap-on-hyphen"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "this-", "will-", "wrap-"],
                    [yuio.term.Color.NONE, "on-", "hyphen"],
                ],
            ),
            (
                ["this.will.not.wrap.on.hyphen.this.is.too.long"],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "this.will.not.w"],
                    [yuio.term.Color.NONE, "rap.on.hyphen.t"],
                    [yuio.term.Color.NONE, "his.is.too.long"],
                ],
            ),
            (
                ["this-will-not-wrap-on-hyphen-this-is-too-long"],
                15,
                {"break_on_hyphens": False},
                [
                    [yuio.term.Color.NONE, "this-will-not-w"],
                    [yuio.term.Color.NONE, "rap-on-hyphen-t"],
                    [yuio.term.Color.NONE, "his-is-too-long"],
                ],
            ),
            (
                ["newlines will\nbe\nhonored!"],
                15,
                {"break_on_hyphens": False},
                [
                    [yuio.term.Color.NONE, "newlines", " ", "will"],
                    [yuio.term.Color.NONE, "be"],
                    [yuio.term.Color.NONE, "honored!"],
                ],
            ),
            (
                ["space before nl    \nis removed"],
                15,
                {},
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
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE, "hello", " ", "world!"],
                ],
            ),
            (
                ["hello   world!"],
                15,
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE, "hello", "   ", "world!"],
                ],
            ),
            (
                ["hello     world!"],
                15,
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE, "hello", "     "],
                    [yuio.term.Color.NONE, "world!"],
                ],
            ),
            (
                ["hello                    world"],
                15,
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE, "hello", "          "],
                    [yuio.term.Color.NONE, "          ", "world"],
                ],
            ),
            (
                ["hello                    longlongworld"],
                15,
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE, "hello", "          "],
                    [yuio.term.Color.NONE, "          "],
                    [yuio.term.Color.NONE, "longlongworld"],
                ],
            ),
            (
                ["hello ", yuio.term.Color.STYLE_BOLD, "world", yuio.term.Color.NONE],
                15,
                {"preserve_spaces": True},
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
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE],
                ],
            ),
            (
                [""],
                15,
                {"preserve_spaces": True},
                [
                    [yuio.term.Color.NONE],
                ],
            ),
            (
                ["Hello line break", yuio.term.Color.NONE],
                15,
                {},
                [
                    [yuio.term.Color.NONE, "Hello", " ", "line"],
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
                        "[--force-",
                        "color",
                        " ",
                        "|",
                        " ",
                        "--force-",
                        "no-",
                        "color]",
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
                        yuio.term.Color.NONE,
                        " ",
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
                        "--force-",
                        "color",
                        yuio.term.Color.NONE,
                        " ",
                        "|",
                        yuio.term.Color.FORE_BLUE,
                        " ",
                        "--force-",
                        "no-",
                        "color",
                        yuio.term.Color.NONE,
                        "]",
                        " ",
                        "[",
                        yuio.term.Color.FORE_BLUE,
                        "-o",
                        yuio.term.Color.NONE,
                        yuio.term.Color.FORE_MAGENTA,
                        yuio.term.Color.NONE,
                        " ",
                        "{",
                        yuio.term.Color.FORE_MAGENTA,
                        "path",
                        yuio.term.Color.NONE,
                        "}",
                        yuio.term.Color.FORE_MAGENTA,
                        yuio.term.Color.NONE,
                        "]",
                        yuio.term.Color.FORE_MAGENTA,
                        yuio.term.Color.NONE,
                        " ",
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
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "single", " ", "string"],
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
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "single"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "string"],
                ],
            ),
            (
                ["foo bar baz"],
                8,
                {"first_line_indent": ">>>", "continuation_indent": "|"},
                [
                    [yuio.term.Color.NONE, ">>>", yuio.term.Color.NONE, "foo"],
                    [yuio.term.Color.NONE, "|", yuio.term.Color.NONE, "bar", " ", "baz"],
                ],
            ),
            (
                ["word werywerylongunbreakableword"],
                8,
                {"first_line_indent": ">>", "continuation_indent": ".."},
                [
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "word"],
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
                    [yuio.term.Color.NONE, ">>", yuio.term.Color.NONE, "single"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "string"],
                    [yuio.term.Color.NONE, "..", yuio.term.Color.NONE, "next", " ", "string"],
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
