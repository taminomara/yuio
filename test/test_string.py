import pytest

import yuio.color
import yuio.string
import yuio.theme


@pytest.mark.parametrize(
    "text,width,length",
    [
        (yuio.string.ColorizedString(), 0, 0),
        (yuio.string.ColorizedString([]), 0, 0),
        (yuio.string.ColorizedString(""), 0, 0),
        (yuio.string.ColorizedString("abc"), 3, 3),
        (yuio.string.ColorizedString("абв"), 3, 3),
        (yuio.string.ColorizedString("a\nb"), 3, 3),
        (yuio.string.ColorizedString("👻"), 2, 1),
        (yuio.string.ColorizedString(["abc", "def"]), 6, 6),
        (yuio.string.ColorizedString(["abc", "👻"]), 5, 4),
        (yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "abc", "def"]), 6, 6),
        (yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "abc", "👻"]), 5, 4),
        (
            yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "abc", "", "def"]),
            6,
            6,
        ),
    ],
)
def test_width_and_len(text, width, length):
    assert text.width == width
    assert text.len == len(text) == length
    assert bool(text) is (len(text) > 0)


@pytest.mark.skip(reason="TODO")
@pytest.mark.parametrize(
    "text,args,expect",
    [
        (
            [""],
            (),
            [],
        ),
        (
            ["hello world!"],
            (),
            ["hello world!"],
        ),
        (
            ["hello %s!"],
            "username",
            ["hello ", "username", "!"],
        ),
        (
            ["hello %r!"],
            "username",
            ["hello ", "'username'", "!"],
        ),
        (
            ["hello %05.2f!"],
            1.5,
            ["hello ", "01.50", "!"],
        ),
        (
            ["hello %05.2lf!"],
            1.5,
            ["hello ", "01.50", "!"],
        ),
        (
            ["hello %s %% %s!"],
            (1, 2),
            ["hello ", "1", " ", "%", " ", "2", "!"],
        ),
        (
            ["hello %s"],
            {"a": "b"},
            ["hello ", "{'a': 'b'}"],
        ),
        (
            ["%10s"],
            "123",
            ["       ", "123"],
        ),
        (
            ["%-10s"],
            "123",
            ["123", "       "],
        ),
        (
            ["%10.2s"],
            "123",
            ["        ", "12"],
        ),
        (
            ["%-10.2s"],
            "123",
            ["12", "        "],
        ),
        (
            ["%*s"],
            (10, "123"),
            ["       ", "123"],
        ),
        (
            ["%*s"],
            (-10, "123"),
            ["123", "       "],
        ),
        (
            ["%-*s"],
            (-10, "123"),
            ["123", "       "],
        ),
        (
            ["%*.*s"],
            (10, 2, "123"),
            ["        ", "12"],
        ),
        (
            ["%*.*s"],
            (-10, 2, "123"),
            ["12", "        "],
        ),
        (
            ["%-*.*s"],
            (-10, 2, "123"),
            ["12", "        "],
        ),
        (
            ["%.*s"],
            (2, "123"),
            ["12"],
        ),
        (
            ["%10s"],
            yuio.string.ColorizedString("123"),
            ["       ", "123"],
        ),
        (
            ["%-10s"],
            yuio.string.ColorizedString("123"),
            ["123", "       "],
        ),
        (
            ["%10.2s"],
            yuio.string.ColorizedString("123"),
            ["        ", "12"],
        ),
        (
            ["%-10.2s"],
            yuio.string.ColorizedString("123"),
            ["12", "        "],
        ),
        (
            ["%*s"],
            (10, yuio.string.ColorizedString("123")),
            ["       ", "123"],
        ),
        (
            ["%*s"],
            (-10, yuio.string.ColorizedString("123")),
            ["123", "       "],
        ),
        (
            ["%-*s"],
            (-10, yuio.string.ColorizedString("123")),
            ["123", "       "],
        ),
        (
            ["%*.*s"],
            (10, 2, yuio.string.ColorizedString("123")),
            ["        ", "12"],
        ),
        (
            ["%*.*s"],
            (-10, 2, yuio.string.ColorizedString("123")),
            ["12", "        "],
        ),
        (
            ["%-*.*s"],
            (-10, 2, yuio.string.ColorizedString("123")),
            ["12", "        "],
        ),
        (
            ["%.*s"],
            (2, yuio.string.ColorizedString("123")),
            ["12"],
        ),
        (
            ["%.*s"],
            (-2, yuio.string.ColorizedString("123")),
            [],
        ),
        (
            ["%.5s"],
            yuio.string.ColorizedString(["123", "456"]),
            ["123", "45"],
        ),
        (
            ["%.5s"],
            yuio.string.ColorizedString(["123"]),
            ["123"],
        ),
        (
            ["%.5s"],
            yuio.string.ColorizedString(["123", "4💥"]),
            ["123", "4", " "],
        ),
        (
            ["%.5s"],
            yuio.string.ColorizedString(["123", "💥6"]),
            ["123", "💥"],
        ),
    ],
)
def test_format(text, args, expect):
    formatted = yuio.string.ColorizedString(text).percent_format(
        args, yuio.theme.Theme()
    )
    assert formatted._parts == expect


@pytest.mark.parametrize(
    "text,width,kwargs,expect",
    [
        (
            ["hello world!"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!"],
            ],
        ),
        (
            ["hello world! 15"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!", " ", "15"],
            ],
        ),
        (
            ["hello world! 👻"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!", " ", "👻"],
            ],
        ),
        (
            ["hello world! 👻👻"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!"],
                [yuio.color.Color.NONE, "👻👻"],
            ],
        ),
        (
            ["hello world! this will wrap"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!"],
                [yuio.color.Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
        ),
        (
            ["hello world!     this will wrap"],
            15,
            {"preserve_spaces": False},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!"],
                [yuio.color.Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
        ),
        (
            ["hello     world!     this     will     wrap"],
            15,
            {"preserve_spaces": False},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!"],
                [yuio.color.Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
        ),
        (
            ["this-will-wrap-on-hyphen"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "this-", "will-", "wrap-"],
                [yuio.color.Color.NONE, "on-", "hyphen"],
            ],
        ),
        (
            ["this.will.not.wrap.on.hyphen.this.is.too.long"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "this.will.not.w"],
                [yuio.color.Color.NONE, "rap.on.hyphen.t"],
                [yuio.color.Color.NONE, "his.is.too.long"],
            ],
        ),
        (
            ["newlines will\nbe\nhonored!"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "newlines", " ", "will"],
                [yuio.color.Color.NONE, "be"],
                [yuio.color.Color.NONE, "honored!"],
            ],
        ),
        (
            ["space before nl    \nis removed"],
            15,
            {"preserve_spaces": False},
            [
                [yuio.color.Color.NONE, "space", " ", "before", " ", "nl"],
                [yuio.color.Color.NONE, "is", " ", "removed"],
            ],
        ),
        (
            ["space after nl\n    is kept"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "space", " ", "after", " ", "nl"],
                [yuio.color.Color.NONE, "    ", "is", " ", "kept"],
            ],
        ),
        (
            ["wo", "rd wo", "rd"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "wo", "rd", " ", "wo", "rd"],
            ],
        ),
        pytest.param(
            ["wo", "rd wo", "rd"],
            7,
            {},
            [
                [yuio.color.Color.NONE, "wo", "rd"],
                [yuio.color.Color.NONE, "wo", "rd"],
            ],
            marks=pytest.mark.xfail(
                reason="this is a bug which I'm not sure how to fix atm"
            ),
        ),
        (
            ["hello world!"],
            15,
            {"preserve_spaces": True},
            [
                [yuio.color.Color.NONE, "hello", " ", "world!"],
            ],
        ),
        (
            ["hello   world!"],
            15,
            {"preserve_spaces": True},
            [
                [yuio.color.Color.NONE, "hello", "   ", "world!"],
            ],
        ),
        (
            ["hello     world!"],
            15,
            {"preserve_spaces": True},
            [
                [yuio.color.Color.NONE, "hello", "     "],
                [yuio.color.Color.NONE, "world!"],
            ],
        ),
        (
            ["hello                    world"],
            15,
            {"preserve_spaces": True},
            [
                [yuio.color.Color.NONE, "hello", "          "],
                [yuio.color.Color.NONE, "          ", "world"],
            ],
        ),
        (
            ["hello                    longlongworld"],
            15,
            {"preserve_spaces": True},
            [
                [yuio.color.Color.NONE, "hello", "          "],
                [yuio.color.Color.NONE, "          "],
                [yuio.color.Color.NONE, "longlongworld"],
            ],
        ),
        (
            ["hello ", yuio.color.Color.STYLE_BOLD, "world", yuio.color.Color.NONE],
            15,
            {},
            [
                [
                    yuio.color.Color.NONE,
                    "hello",
                    " ",
                    yuio.color.Color.STYLE_BOLD,
                    "world",
                    yuio.color.Color.NONE,
                ]
            ],
        ),
        (
            [],
            15,
            {},
            [
                [yuio.color.Color.NONE],
            ],
        ),
        (
            [""],
            15,
            {},
            [
                [yuio.color.Color.NONE],
            ],
        ),
        (
            ["12345678901234 12345"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "12345678901234"],
                [yuio.color.Color.NONE, "12345"],
            ],
        ),
        (
            ["Hello line break", yuio.color.Color.NONE],
            15,
            {},
            [
                [yuio.color.Color.NONE, "Hello", " ", "line"],
                [yuio.color.Color.NONE, "break"],
            ],
        ),
        (
            [yuio.color.Color.STYLE_BOLD, yuio.color.Color.NONE],
            15,
            {},
            [
                [
                    yuio.color.Color.NONE,
                    yuio.color.Color.STYLE_BOLD,
                    yuio.color.Color.NONE,
                ],
            ],
        ),
        (
            [yuio.color.Color.STYLE_BOLD, "", yuio.color.Color.NONE],
            15,
            {},
            [
                [
                    yuio.color.Color.NONE,
                    yuio.color.Color.STYLE_BOLD,
                    yuio.color.Color.NONE,
                ],
            ],
        ),
        (
            ["break\n", yuio.color.Color.NONE],
            15,
            {},
            [
                [yuio.color.Color.NONE, "break"],
                [yuio.color.Color.NONE],
            ],
        ),
        (
            ["break\n"],
            15,
            {},
            [
                [yuio.color.Color.NONE, "break"],
                [yuio.color.Color.NONE],
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
                    yuio.color.Color.NONE,
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
                yuio.color.Color.FORE_MAGENTA,
                "usage: ",
                yuio.color.Color.NONE,
                yuio.color.Color.NONE,
                "app.py train",
                yuio.color.Color.NONE,
                yuio.color.Color.NONE,
                " ",
                yuio.color.Color.NONE,
                "[",
                yuio.color.Color.FORE_BLUE,
                "-h",
                yuio.color.Color.NONE,
                "]",
                yuio.color.Color.NONE,
                " ",
                yuio.color.Color.NONE,
                "[",
                yuio.color.Color.FORE_BLUE,
                "-v",
                yuio.color.Color.NONE,
                "]",
                yuio.color.Color.NONE,
                " [",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_BLUE,
                "--force-color",
                yuio.color.Color.NONE,
                " | ",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_BLUE,
                "--force-no-color",
                yuio.color.Color.NONE,
                "] ",
                yuio.color.Color.NONE,
                "[",
                yuio.color.Color.FORE_BLUE,
                "-o",
                yuio.color.Color.NONE,
                " ",
                yuio.color.Color.FORE_MAGENTA,
                "",
                yuio.color.Color.NONE,
                "{",
                yuio.color.Color.FORE_MAGENTA,
                "path",
                yuio.color.Color.NONE,
                "}",
                yuio.color.Color.FORE_MAGENTA,
                "",
                yuio.color.Color.NONE,
                "]",
                yuio.color.Color.NONE,
                " ",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_MAGENTA,
                "",
                yuio.color.Color.NONE,
                "<",
                yuio.color.Color.FORE_MAGENTA,
                "data",
                yuio.color.Color.NONE,
                ">",
                yuio.color.Color.FORE_MAGENTA,
                "",
            ],
            100,
            {},
            [
                [
                    yuio.color.Color.NONE,
                    yuio.color.Color.FORE_MAGENTA,
                    "usage:",
                    " ",
                    yuio.color.Color.NONE,
                    "app.py",
                    " ",
                    "train",
                    " ",
                    "[",
                    yuio.color.Color.FORE_BLUE,
                    "-h",
                    yuio.color.Color.NONE,
                    "]",
                    " ",
                    "[",
                    yuio.color.Color.FORE_BLUE,
                    "-v",
                    yuio.color.Color.NONE,
                    "]",
                    " ",
                    "[",
                    yuio.color.Color.FORE_BLUE,
                    "--force-",
                    "color",
                    yuio.color.Color.NONE,
                    " ",
                    "|",
                    " ",
                    yuio.color.Color.FORE_BLUE,
                    "--force-",
                    "no-",
                    "color",
                    yuio.color.Color.NONE,
                    "]",
                    " ",
                    "[",
                    yuio.color.Color.FORE_BLUE,
                    "-o",
                    yuio.color.Color.NONE,
                    " ",
                    yuio.color.Color.FORE_MAGENTA,
                    yuio.color.Color.NONE,
                    "{",
                    yuio.color.Color.FORE_MAGENTA,
                    "path",
                    yuio.color.Color.NONE,
                    "}",
                    yuio.color.Color.FORE_MAGENTA,
                    yuio.color.Color.NONE,
                    "]",
                    " ",
                    yuio.color.Color.FORE_MAGENTA,
                    yuio.color.Color.NONE,
                    "<",
                    yuio.color.Color.FORE_MAGENTA,
                    "data",
                    yuio.color.Color.NONE,
                    ">",
                    yuio.color.Color.FORE_MAGENTA,
                ]
            ],
        ),
        (
            ["single string"],
            100,
            {"first_line_indent": ">>"},
            [
                [
                    yuio.color.Color.NONE,
                    ">>",
                    yuio.color.Color.NONE,
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
                [yuio.color.Color.NONE, "single", " ", "string"],
            ],
        ),
        (
            ["single string"],
            13,
            {},
            [
                [yuio.color.Color.NONE, "single", " ", "string"],
            ],
        ),
        (
            ["single string"],
            13,
            {"first_line_indent": ">>", "continuation_indent": ".."},
            [
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE, "single"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "string"],
            ],
        ),
        (
            ["foo bar baz"],
            8,
            {"first_line_indent": ">>>", "continuation_indent": "|"},
            [
                [yuio.color.Color.NONE, ">>>", yuio.color.Color.NONE, "foo"],
                [
                    yuio.color.Color.NONE,
                    "|",
                    yuio.color.Color.NONE,
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
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE, "word"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "werywe"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "rylong"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "unbrea"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "kablew"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "ord"],
            ],
        ),
        (
            ["werywerylongunbreakableword"],
            8,
            {"first_line_indent": ">>>", "continuation_indent": "."},
            [
                [yuio.color.Color.NONE, ">>>", yuio.color.Color.NONE, "weryw"],
                [yuio.color.Color.NONE, ".", yuio.color.Color.NONE, "erylong"],
                [yuio.color.Color.NONE, ".", yuio.color.Color.NONE, "unbreak"],
                [yuio.color.Color.NONE, ".", yuio.color.Color.NONE, "ablewor"],
                [yuio.color.Color.NONE, ".", yuio.color.Color.NONE, "d"],
            ],
        ),
        (
            ["single string", "\nnext string"],
            13,
            {"first_line_indent": ">>", "continuation_indent": ".."},
            [
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE, "single"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "string"],
                [
                    yuio.color.Color.NONE,
                    "..",
                    yuio.color.Color.NONE,
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
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE, "a"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "b"],
            ],
        ),
        (
            ["a\n"],
            13,
            {"first_line_indent": ">>", "continuation_indent": ".."},
            [
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE, "a"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE],
            ],
        ),
        (
            ["\na"],
            13,
            {"first_line_indent": ">>", "continuation_indent": ".."},
            [
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "a"],
            ],
        ),
        (
            ["\nwerywerylongunbreakableword"],
            13,
            {"first_line_indent": ">>", "continuation_indent": ".."},
            [
                [yuio.color.Color.NONE, ">>", yuio.color.Color.NONE],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "werywerylon"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "gunbreakabl"],
                [yuio.color.Color.NONE, "..", yuio.color.Color.NONE, "eword"],
            ],
        ),
        (
            [yuio.color.Color.FORE_BLUE, "single string"],
            13,
            {
                "first_line_indent": yuio.string.ColorizedString(
                    [yuio.color.Color.FORE_MAGENTA, ">>"]
                ),
                "continuation_indent": yuio.string.ColorizedString(
                    [yuio.color.Color.FORE_BLUE, ".."]
                ),
            },
            [
                [
                    yuio.color.Color.NONE,
                    yuio.color.Color.FORE_MAGENTA,
                    ">>",
                    yuio.color.Color.NONE,
                    yuio.color.Color.FORE_BLUE,
                    "single",
                ],
                [
                    yuio.color.Color.NONE,
                    yuio.color.Color.FORE_BLUE,
                    "..",
                    yuio.color.Color.FORE_BLUE,
                    "string",
                ],
            ],
        ),
    ],
)
def test_wrap(text, width, kwargs, expect):
    wrapped = yuio.string.ColorizedString(text).wrap(width, **kwargs)
    raw = [line._parts for line in wrapped]
    assert raw == expect


@pytest.mark.parametrize(
    "text,first_line_indent,continuation_indent,expect",
    [
        (
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString(),
            [],
        ),
        (
            yuio.string.ColorizedString(""),
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString(),
            [],
        ),
        (
            yuio.string.ColorizedString("abc"),
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString(),
            [yuio.color.Color.NONE, "abc"],
        ),
        (
            yuio.string.ColorizedString("abc\n"),
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString(),
            [yuio.color.Color.NONE, "abc\n"],
        ),
        (
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            [],
        ),
        (
            yuio.string.ColorizedString(""),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            [],
        ),
        (
            yuio.string.ColorizedString("abc"),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            ["1", yuio.color.Color.NONE, "abc"],
        ),
        (
            yuio.string.ColorizedString("abc\n"),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            ["1", yuio.color.Color.NONE, "abc\n"],
        ),
        (
            yuio.string.ColorizedString(["abc", "def"]),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            ["1", yuio.color.Color.NONE, "abc", "def"],
        ),
        (
            yuio.string.ColorizedString("abc\ndef"),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            ["1", yuio.color.Color.NONE, "abc\n", "2", yuio.color.Color.NONE, "def"],
        ),
        (
            yuio.string.ColorizedString(["abc\n", "def"]),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            ["1", yuio.color.Color.NONE, "abc\n", "2", yuio.color.Color.NONE, "def"],
        ),
        (
            yuio.string.ColorizedString(["abc", "\n", "def"]),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            [
                "1",
                yuio.color.Color.NONE,
                "abc",
                "\n",
                "2",
                yuio.color.Color.NONE,
                "def",
            ],
        ),
        (
            yuio.string.ColorizedString("abc\ndef\n"),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString("2"),
            [
                "1",
                yuio.color.Color.NONE,
                "abc\n",
                "2",
                yuio.color.Color.NONE,
                "def\n",
            ],
        ),
        (
            yuio.string.ColorizedString("abc\ndef"),
            yuio.string.ColorizedString("1"),
            yuio.string.ColorizedString(),
            ["1", yuio.color.Color.NONE, "abc\n", yuio.color.Color.NONE, "def"],
        ),
        (
            yuio.string.ColorizedString("abc\ndef"),
            yuio.string.ColorizedString(),
            yuio.string.ColorizedString("2"),
            [yuio.color.Color.NONE, "abc\n", "2", yuio.color.Color.NONE, "def"],
        ),
        (
            yuio.string.ColorizedString(["abc\ndef"]),
            yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "1"]),
            yuio.string.ColorizedString([yuio.color.Color.FORE_BLUE, "2"]),
            [
                yuio.color.Color.FORE_RED,
                "1",
                yuio.color.Color.NONE,
                "abc\n",
                yuio.color.Color.FORE_BLUE,
                "2",
                yuio.color.Color.NONE,
                "def",
            ],
        ),
        (
            yuio.string.ColorizedString([yuio.color.Color.FORE_YELLOW, "abc\ndef"]),
            yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "1"]),
            yuio.string.ColorizedString([yuio.color.Color.FORE_BLUE, "2"]),
            [
                yuio.color.Color.FORE_RED,
                "1",
                yuio.color.Color.FORE_YELLOW,
                "abc\n",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_BLUE,
                "2",
                yuio.color.Color.FORE_YELLOW,
                "def",
            ],
        ),
        (
            yuio.string.ColorizedString(
                ["abc\n", yuio.color.Color.FORE_YELLOW, "def\nhig"]
            ),
            yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "1"]),
            yuio.string.ColorizedString([yuio.color.Color.FORE_BLUE, "2"]),
            [
                yuio.color.Color.FORE_RED,
                "1",
                yuio.color.Color.NONE,
                "abc\n",
                yuio.color.Color.FORE_BLUE,
                "2",
                yuio.color.Color.FORE_YELLOW,
                "def\n",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_BLUE,
                "2",
                yuio.color.Color.FORE_YELLOW,
                "hig",
            ],
        ),
        (
            yuio.string.ColorizedString(
                ["abc", yuio.color.Color.FORE_YELLOW, "\ndef\nhig"]
            ),
            yuio.string.ColorizedString([yuio.color.Color.FORE_RED, "1"]),
            yuio.string.ColorizedString([yuio.color.Color.FORE_BLUE, "2"]),
            [
                yuio.color.Color.FORE_RED,
                "1",
                yuio.color.Color.NONE,
                "abc",
                yuio.color.Color.FORE_YELLOW,
                "\n",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_BLUE,
                "2",
                yuio.color.Color.FORE_YELLOW,
                "def\n",
                yuio.color.Color.NONE,
                yuio.color.Color.FORE_BLUE,
                "2",
                yuio.color.Color.FORE_YELLOW,
                "hig",
            ],
        ),
    ],
)
def test_indent(text, first_line_indent, continuation_indent, expect):
    indented = text.indent(first_line_indent, continuation_indent)
    assert indented._parts == expect
