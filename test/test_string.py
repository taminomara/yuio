import collections
import dataclasses
from dataclasses import dataclass

import pytest

import yuio.string
import yuio.term
import yuio.theme
from yuio.color import Color
from yuio.string import NO_WRAP_END, NO_WRAP_START, Esc, LinkMarker, ReprContext

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


_s = yuio.string.ColorizedString


def _touch_width(s: yuio.string.ColorizedString):
    _ = s.width
    return s


@pytest.fixture(autouse=True)
def setup_repr_hl(theme):
    theme.set_color("hl/kwd:repr", Color.FORE_RED)
    theme.set_color("hl/str:repr", Color.FORE_GREEN)
    theme.set_color("hl/str/esc:repr", Color.FORE_BLUE)
    theme.set_color("hl/punct:repr", Color.FORE_CYAN)
    theme.set_color("hl/comment:repr", Color.FORE_MAGENTA)
    theme.set_color("hl/lit:repr", Color.FORE_YELLOW)
    theme.set_color("hl/type:repr", Color.FORE_BLACK)
    theme.set_color("hl/more:repr", Color.FORE_WHITE)


@pytest.mark.parametrize(
    ("text", "width", "length"),
    [
        pytest.param(
            _s(),
            0,
            0,
            id="empty",
        ),
        pytest.param(
            _s(Color.FORE_RED),
            0,
            0,
            id="color",
        ),
        pytest.param(
            _s(NO_WRAP_START),
            0,
            0,
            id="no-wrap-marker",
        ),
        pytest.param(
            _s(""),
            0,
            0,
            id="empty-string",
        ),
        pytest.param(
            _s("abc"),
            3,
            3,
            id="ascii",
        ),
        pytest.param(
            _s("абв"),
            3,
            3,
            id="cyrillic",
        ),
        pytest.param(
            _s("a\nb"),
            3,
            3,
            id="newline",
        ),
        pytest.param(
            _s("👻"),
            2,
            1,
            id="wide",
        ),
        pytest.param(
            _s("abc", ""),
            3,
            3,
            id="empty-string",
        ),
        pytest.param(
            _s("abc", "def"),
            6,
            6,
            id="ascii",
        ),
        pytest.param(
            _s("abc", "👻"),
            5,
            4,
            id="wide",
        ),
        pytest.param(
            _s(_s()),
            0,
            0,
            id="col-string-empty",
        ),
        pytest.param(
            _s(_s("asd")),
            3,
            3,
            id="col-string-non-empty",
        ),
        pytest.param(
            _s(_s("asd", "👻")),
            5,
            4,
            id="col-string-wide",
        ),
        pytest.param(
            _s(_touch_width(_s())),
            0,
            0,
            id="col-string-empty-with-cached-width",
        ),
        pytest.param(
            _s(_touch_width(_s("asd"))),
            3,
            3,
            id="col-string-non-empty-with-cached-width",
        ),
        pytest.param(
            _s(_touch_width(_s("asd", "👻"))),
            5,
            4,
            id="col-string-wide-with-cached-width",
        ),
        pytest.param(
            _touch_width(_s("asd")) + "👻",
            5,
            4,
            id="cached-width-resets",
        ),
        pytest.param(
            _touch_width(_s("asd")) + _s("👻"),
            5,
            4,
            id="cached-width-resets",
        ),
        pytest.param(
            _touch_width(_s("asd")) + _touch_width(_s("👻")),
            5,
            4,
            id="cached-width-sum",
        ),
        pytest.param(
            _s(LinkMarker("https://example.com"), "link"),
            4,
            4,
            id="link-marker",
        ),
    ],
)
def test_width_and_len(text, width, length):
    assert text.width == width
    assert text.len == len(text) == length
    assert bool(text) is (len(text) > 0)


@pytest.mark.parametrize(
    ("l", "r", "expected"),
    [
        ("asd", _s("asd"), False),
        (_s("asd"), "asd", False),
        (_s(), _s(), True),
        (_s("foo"), _s("foo"), True),
        (_s(Color.NONE, "foo"), _s("foo"), True),
        (_s(Color.FORE_RED, "foo"), _s("foo"), False),
        (_s("foo", "bar"), _s("foobar"), False),
    ],
)
def test_eq(l, r, expected):
    assert (l == r) is expected
    assert (l != r) is (not expected)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param(
            [],
            [],
            id="empty",
        ),
        pytest.param(
            [""],
            [],
            id="empty-string",
        ),
        pytest.param(
            ["abc"],
            [Color.NONE, "abc"],
            id="normal",
        ),
        pytest.param(
            [Color.FORE_RED, "abc"],
            [Color.FORE_RED, "abc"],
            id="color",
        ),
        pytest.param(
            [LinkMarker("https://example.com"), "link"],
            [LinkMarker("https://example.com"), Color.NONE, "link"],
            id="link",
        ),
        pytest.param(
            ["abc", LinkMarker("https://example.com")],
            [Color.NONE, "abc"],
            id="link-tail",
        ),
        pytest.param(
            ["abc", LinkMarker("https://example.com"), "def"],
            [Color.NONE, "abc", LinkMarker("https://example.com"), "def"],
            id="link-tail-string",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), LinkMarker("https://b.com"), "abc"],
            [LinkMarker("https://b.com"), Color.NONE, "abc"],
            id="link-change",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), LinkMarker(None), "abc"],
            [Color.NONE, "abc"],
            id="link-none",
        ),
        pytest.param(
            ["abc", Color.FORE_GREEN],
            [Color.NONE, "abc"],
            id="color-tail",
        ),
        pytest.param(
            ["abc", Color.FORE_GREEN, "def"],
            [Color.NONE, "abc", Color.FORE_GREEN, "def"],
            id="color-tail-string",
        ),
        pytest.param(
            [Color.FORE_RED, Color.FORE_GREEN, "abc"],
            [Color.FORE_GREEN, "abc"],
            id="color-change",
        ),
        pytest.param(
            [NO_WRAP_END],
            [],
            id="no-wrap-extra-end",
        ),
        pytest.param(
            [NO_WRAP_START],
            [NO_WRAP_START],
            id="no-wrap-start",
        ),
        pytest.param(
            [NO_WRAP_START, NO_WRAP_END],
            [],
            id="no-wrap-empty",
        ),
        pytest.param(
            [NO_WRAP_START, "asd", NO_WRAP_END],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END],
            id="no-wrap",
        ),
        pytest.param(
            [NO_WRAP_START, "asd", NO_WRAP_END, "dsa"],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END, "dsa"],
            id="no-wrap-continue",
        ),
        pytest.param(
            [NO_WRAP_START, "asd", NO_WRAP_END, NO_WRAP_START],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END, NO_WRAP_START],
            id="no-wrap-continue-start",
        ),
        pytest.param(
            [NO_WRAP_START, "asd", NO_WRAP_END, NO_WRAP_START, NO_WRAP_END],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END],
            id="no-wrap-continue-empty",
        ),
        pytest.param(
            [NO_WRAP_START, NO_WRAP_START, "asd", NO_WRAP_END, NO_WRAP_END],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END],
            id="no-wrap-nested",
        ),
        pytest.param(
            [_s("abc")],
            [Color.NONE, "abc"],
            id="col-string-simple",
        ),
        pytest.param(
            [_s("abc", "def")],
            [Color.NONE, "abc", "def"],
            id="col-string-multi",
        ),
        pytest.param(
            [_s("abc", Color.FORE_RED, "def")],
            [Color.NONE, "abc", Color.FORE_RED, "def"],
            id="col-string-colors",
        ),
        pytest.param(
            ["xxx", _s("abc")],
            [Color.NONE, "xxx", "abc"],
            id="col-string-prefix",
        ),
        pytest.param(
            ["xxx", _s(Color.FORE_RED, "abc")],
            [Color.NONE, "xxx", Color.FORE_RED, "abc"],
            id="col-string-prefix-different-color",
        ),
        pytest.param(
            [Color.FORE_RED, "xxx", _s("abc")],
            [Color.FORE_RED, "xxx", Color.NONE, "abc"],
            id="col-string-prefix-different-color",
        ),
        pytest.param(
            [_s("abc", Color.FORE_RED, "def"), "xxx"],
            [Color.NONE, "abc", Color.FORE_RED, "def", Color.NONE, "xxx"],
            id="col-string-active-color-did-not-change",
        ),
        pytest.param(
            [Color.FORE_GREEN, _s("abc", Color.FORE_RED, "def"), "xxx"],
            [Color.NONE, "abc", Color.FORE_RED, "def", Color.FORE_GREEN, "xxx"],
            id="col-string-active-color-did-not-change",
        ),
        pytest.param(
            [Color.FORE_GREEN, "xxx", _s("abc", Color.FORE_RED, "def"), "xxx"],
            [
                Color.FORE_GREEN,
                "xxx",
                Color.NONE,
                "abc",
                Color.FORE_RED,
                "def",
                Color.FORE_GREEN,
                "xxx",
            ],
            id="col-string-active-color-did-not-change",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), _s("abc")],
            [LinkMarker("https://a.com"), Color.NONE, "abc"],
            id="col-string-with-active-link",
        ),
        pytest.param(
            [_s(LinkMarker("https://a.com"), "abc"), "def"],
            [LinkMarker("https://a.com"), Color.NONE, "abc", LinkMarker(None), "def"],
            id="col-string-with-link-preserves-link-context",
        ),
        pytest.param(
            [_s(LinkMarker("https://a.com"), "abc"), _s("def")],
            [LinkMarker("https://a.com"), Color.NONE, "abc", LinkMarker(None), "def"],
            id="col-string-with-link-preserves-link-context",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), _s(LinkMarker("https://b.com"), "abc")],
            [LinkMarker("https://a.com"), Color.NONE, "abc"],
            id="active-link-overrides-appended-links",
        ),
        pytest.param(
            [_s(NO_WRAP_START, "asd", NO_WRAP_END)],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END],
            id="col-string-with-no-wraps",
        ),
        pytest.param(
            [_s("asd", NO_WRAP_START)],
            [Color.NONE, "asd"],
            id="col-string-with-no-wraps-made-empty",
        ),
        pytest.param(
            [_s(NO_WRAP_START, "asd")],
            [NO_WRAP_START, Color.NONE, "asd", NO_WRAP_END],
            id="col-string-with-unterminated-no-wraps",
        ),
        pytest.param(
            [NO_WRAP_START, _s("asd", "xyz")],
            [NO_WRAP_START, Color.NONE, "asd", "xyz"],
            id="col-string-in-no-wrap",
        ),
        pytest.param(
            [NO_WRAP_START, "x", _s(NO_WRAP_START, "asd", NO_WRAP_END), "y"],
            [NO_WRAP_START, Color.NONE, "x", "asd", "y"],
            id="col-string-with-no-wraps-in-no-wrap",
        ),
    ],
)
def test_extend(text, expected):
    assert _s(text)._parts == expected


@pytest.mark.parametrize(
    ("text", "kwargs", "expect"),
    [
        pytest.param(
            "",
            {},
            [],
            id="empty",
        ),
        pytest.param(
            "foo bar",
            {},
            [Color.NONE, "foo bar"],
            id="simple",
        ),
        pytest.param(
            "`bar`",
            {},
            [NO_WRAP_START, Color.FORE_MAGENTA, "bar", NO_WRAP_END],
            id="code",
        ),
        pytest.param(
            "`--foo` `-10`",
            {},
            [
                NO_WRAP_START,
                Color.FORE_CYAN,
                "--foo",
                NO_WRAP_END,
                Color.NONE,
                " ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "-10",
                NO_WRAP_END,
            ],
            id="code-flags",
        ),
        pytest.param(
            "xx`bar`xx",
            {},
            [
                Color.NONE,
                "xx",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "bar",
                NO_WRAP_END,
                Color.NONE,
                "xx",
            ],
            id="code",
        ),
        pytest.param(
            "``b`a```r`s``",
            {},
            [NO_WRAP_START, Color.FORE_MAGENTA, "b`a```r`s", NO_WRAP_END],
            id="code-multiple-backticks",
        ),
        pytest.param(
            "`` bar ``",
            {},
            [NO_WRAP_START, Color.FORE_MAGENTA, "bar", NO_WRAP_END],
            id="code-strip-space",
        ),
        pytest.param(
            "`` `bar` ``",
            {},
            [NO_WRAP_START, Color.FORE_MAGENTA, "`bar`", NO_WRAP_END],
            id="code-strip-space",
        ),
        pytest.param(
            "foo \\`bar\\`",
            {},
            [Color.NONE, "foo ", "`", "bar", "`"],
            id="escape-punct",
        ),
        pytest.param(
            "foo \\nbar\\n",
            {},
            [Color.NONE, "foo \\nbar\\n"],
            id="escape-non-punct",
        ),
        pytest.param(
            "xyz",
            {"default_color": Color.FORE_RED},
            [Color.FORE_RED, "xyz"],
            id="default-color",
        ),
        pytest.param(
            "xyz <c bold>abc <c green>def</c> ghi</c> zxy",
            {"default_color": Color.FORE_RED},
            [
                Color.FORE_RED,
                "xyz ",
                Color.FORE_RED | Color.STYLE_BOLD,
                "abc ",
                Color.FORE_GREEN | Color.STYLE_BOLD,
                "def",
                Color.FORE_RED | Color.STYLE_BOLD,
                " ghi",
                Color.FORE_RED,
                " zxy",
            ],
            id="color-tags",
        ),
        pytest.param(
            "xyz <c bold>abc <c green>def ghi zxy",
            {"default_color": Color.FORE_RED},
            [
                Color.FORE_RED,
                "xyz ",
                Color.FORE_RED | Color.STYLE_BOLD,
                "abc ",
                Color.FORE_GREEN | Color.STYLE_BOLD,
                "def ghi zxy",
            ],
            id="color-tags-unbalanced",
        ),
    ],
)
def test_colorize(text, kwargs, expect, ctx):
    formatted = yuio.string.colorize(text, ctx=ctx, **kwargs)
    assert formatted._parts == expect


@pytest.mark.parametrize(
    ("text", "expect"),
    [
        pytest.param(
            "",
            "",
            id="empty",
        ),
        pytest.param(
            "foo bar",
            "foo bar",
            id="simple",
        ),
        pytest.param(
            "`bar`",
            "bar",
            id="code",
        ),
        pytest.param(
            "`--foo` `-10`",
            "--foo -10",
            id="code-flags",
        ),
        pytest.param(
            "xxbarxx",
            "xxbarxx",
            id="code",
        ),
        pytest.param(
            "``b`a```r`s``",
            "b`a```r`s",
            id="code-multiple-backticks",
        ),
        pytest.param(
            "`` bar ``",
            "bar",
            id="code-strip-space",
        ),
        pytest.param(
            "`` `bar` ``",
            "`bar`",
            id="code-strip-space",
        ),
        pytest.param(
            "foo \\`bar\\`",
            "foo `bar`",
            id="escape-punct",
        ),
        pytest.param(
            "foo \\nbar\\n",
            "foo \\nbar\\n",
            id="escape-non-punct",
        ),
        pytest.param(
            "xyz",
            "xyz",
            id="default-color",
        ),
        pytest.param(
            "xyz <c bold>abc <c green>def</c> ghi</c> zxy",
            "xyz abc def ghi zxy",
            id="color-tags",
        ),
        pytest.param(
            "xyz <c bold>abc <c green>def ghi zxy",
            "xyz abc def ghi zxy",
            id="color-tags-unbalanced",
        ),
    ],
)
def test_strip_color_tags(text, expect):
    assert yuio.string.strip_color_tags(text) == expect


@pytest.mark.parametrize(
    ("text", "args", "expect"),
    [
        pytest.param(
            [""],
            (),
            [],
            id="empty",
        ),
        pytest.param(
            [Color.NONE, "hello world!"],
            (),
            [Color.NONE, "hello world!"],
            id="no-args",
        ),
        pytest.param(
            [Color.NONE, "hello %%!"],
            (),
            [Color.NONE, "hello ", "%", "!"],
            id="percent-sign",
        ),
        pytest.param(
            ["hello %s %% %s!"],
            (1, 2),
            [Color.NONE, "hello ", "1", " ", "%", " ", "2", "!"],
            id="percent-sign-with-args",
        ),
        pytest.param(
            ["hello %s!"],
            "username",
            [Color.NONE, "hello ", "username", "!"],
            id="str",
        ),
        pytest.param(
            ["hello %r!"],
            "username",
            [Color.NONE, "hello ", "'username'", "!"],
            id="repr",
        ),
        pytest.param(
            ["hello %05.2f!"],
            1.5,
            [Color.NONE, "hello ", "01.50", "!"],
            id="float",
        ),
        pytest.param(
            ["hello %0*.*f!"],
            (5, 2, 1.5),
            [Color.NONE, "hello ", "01.50", "!"],
            id="float-dynamic-precision",
        ),
        pytest.param(
            ["hello %05.2lf!"],
            1.5,
            [Color.NONE, "hello ", "01.50", "!"],
            id="long-float",
        ),
        pytest.param(
            ["hello %s"],
            {"a": "b"},
            [Color.NONE, "hello ", "{", "'a'", ": ", "'b'", "}"],
            id="positional-with-mapping",
        ),
        pytest.param(
            ["hello %(a)s %s!"],
            {"a": "b"},
            [Color.NONE, "hello ", "b", " ", "{", "'a'", ": ", "'b'", "}", "!"],
            id="positional-and-named-with-mapping-str",
        ),
        pytest.param(
            ["hello %(a)s!"],
            {"a": "b"},
            [Color.NONE, "hello ", "b", "!"],
            id="named-str",
        ),
        pytest.param(
            ["hello %(a)d!"],
            {"a": 10},
            [Color.NONE, "hello ", "10", "!"],
            id="named-int",
        ),
        pytest.param(
            ["hello %(a)d %r!"],
            {"a": 10},
            [Color.NONE, "hello ", "10", " ", "{", "'a'", ": ", "10", "}", "!"],
            id="positional-and-named-with-mapping-repr",
        ),
        pytest.param(
            ["%10s"],
            "123",
            [Color.NONE, "       ", "123"],
            id="str-align-right",
        ),
        pytest.param(
            ["%-10s"],
            "123",
            [Color.NONE, "123", "       "],
            id="str-align-left",
        ),
        pytest.param(
            ["%10s"],
            "1234567890",
            [Color.NONE, "1234567890"],
            id="str-align-right-overflow",
        ),
        pytest.param(
            ["%-10s"],
            "1234567890",
            [Color.NONE, "1234567890"],
            id="str-align-left-overflow",
        ),
        pytest.param(
            ["%10.2s"],
            "123",
            [Color.NONE, "        ", "12"],
            id="str-align-left-and-cut",
        ),
        pytest.param(
            ["%-10.2s"],
            "123",
            [Color.NONE, "12", "        "],
            id="str-align-right-and-cut",
        ),
        pytest.param(
            ["%*s"],
            (10, "123"),
            [Color.NONE, "       ", "123"],
            id="str-align-left-dynamic",
        ),
        pytest.param(
            ["%*s"],
            (-10, "123"),
            [Color.NONE, "123", "       "],
            id="str-align-left-dynamic-neg",
        ),
        pytest.param(
            ["%-*s"],
            (-10, "123"),
            [Color.NONE, "123", "       "],
            id="str-align-right-dynamic",
        ),
        pytest.param(
            ["%*.*s"],
            (10, 2, "123"),
            [Color.NONE, "        ", "12"],
            id="str-align-right-dynamic-and-cut-dynamic",
        ),
        pytest.param(
            ["%*.*s"],
            (-10, 2, "123"),
            [Color.NONE, "12", "        "],
            id="str-align-right-dynamic-neg-and-cut-dynamic",
        ),
        pytest.param(
            ["%-*.*s"],
            (-10, 2, "123"),
            [Color.NONE, "12", "        "],
            id="str-align-left-dynamic-neg-and-cut-dynamic",
        ),
        pytest.param(
            ["%.*s"],
            (2, "123"),
            [Color.NONE, "12"],
            id="str-cut-dynamic",
        ),
        pytest.param(
            ["%10s"],
            _s("123"),
            [Color.NONE, "       ", "123"],
            id="str-align-left-col-string",
        ),
        pytest.param(
            ["%-10s"],
            _s("123"),
            [Color.NONE, "123", "       "],
            id="str-align-right-col-string",
        ),
        pytest.param(
            ["%10.2s"],
            _s("123"),
            [Color.NONE, "        ", "12"],
            id="str-align-left-and-cut-col-string",
        ),
        pytest.param(
            ["%-10.2s"],
            _s("123"),
            [Color.NONE, "12", "        "],
            id="str-align-right-and-cut-col-string",
        ),
        pytest.param(
            ["%*s"],
            (10, _s("123")),
            [Color.NONE, "       ", "123"],
            id="str-align-left-dynamic-col-string",
        ),
        pytest.param(
            ["%*s"],
            (-10, _s("123")),
            [Color.NONE, "123", "       "],
            id="str-align-left-dynamic-neg-col-string",
        ),
        pytest.param(
            ["%-*s"],
            (-10, _s("123")),
            [Color.NONE, "123", "       "],
            id="str-align-right-dynamic-col-string",
        ),
        pytest.param(
            ["%*.*s"],
            (10, 2, _s("123")),
            [Color.NONE, "        ", "12"],
            id="str-align-left-dynamic-and-cut-dynamic-col-string",
        ),
        pytest.param(
            ["%*.*s"],
            (-10, 2, _s("123")),
            [Color.NONE, "12", "        "],
            id="str-align-left-dynamic-neg-and-cut-dynamic-col-string",
        ),
        pytest.param(
            ["%-*.*s"],
            (-10, 2, _s("123")),
            [Color.NONE, "12", "        "],
            id="str-align-right-dynamic-neg-and-cut-dynamic-col-string",
        ),
        pytest.param(
            ["%.*s"],
            (2, _s("123")),
            [Color.NONE, "12"],
            id="str-cut-dynamic-col-string",
        ),
        pytest.param(
            ["%.*s"],
            (-2, _s("123")),
            [],
            id="str-cut-dynamic-neg-col-string",
        ),
        pytest.param(
            ["%.5s"],
            _s("123", "456"),
            [Color.NONE, "123", "45"],
            id="str-cut-col-string-multiple-parts",
        ),
        pytest.param(
            ["%.5s"],
            _s("123"),
            [Color.NONE, "123"],
            id="str-cut-col-string",
        ),
        pytest.param(
            ["%.5s"],
            _s("123", "4💥"),
            [Color.NONE, "123", "4", " "],
            id="str-cut-col-string-multiple-parts-wide-overflow",
        ),
        pytest.param(
            ["%.5s"],
            _s("123", "💥6"),
            [Color.NONE, "123", "💥"],
            id="str-cut-col-string-multiple-parts-wide",
        ),
        pytest.param(
            ["%.6r"],
            "1234💥",
            [Color.NONE, "'1234", " "],
            id="str-cut-wide-overflow",
        ),
        pytest.param(
            ["%.6r"],
            "123💥6",
            [Color.NONE, "'123💥"],
            id="str-cut-wide",
        ),
        pytest.param(
            [Color.STYLE_BOLD, "x %s y"],
            _s("foo", Color.FORE_RED, "bar"),
            [
                Color.STYLE_BOLD,
                "x ",
                "foo",
                Color.STYLE_BOLD | Color.FORE_RED,
                "bar",
                Color.STYLE_BOLD,
                " y",
            ],
            id="str-base-color",
        ),
        pytest.param(
            [Color.STYLE_BOLD, "x %.3s y"],
            _s("foo", Color.FORE_RED, "bar"),
            [
                Color.STYLE_BOLD,
                "x ",
                "foo",
                " y",
            ],
            id="str-base-color-cut",
        ),
        pytest.param(
            [Color.STYLE_BOLD, "x %.5s y"],
            _s("foo", Color.FORE_RED, "bar"),
            [
                Color.STYLE_BOLD,
                "x ",
                "foo",
                Color.STYLE_BOLD | Color.FORE_RED,
                "ba",
                Color.STYLE_BOLD,
                " y",
            ],
            id="str-base-color-cut",
        ),
        pytest.param(
            ["%d"],
            (
                yuio.string.WithBaseColor(
                    yuio.string.Printable(10), base_color=Color.FORE_BLUE
                )
            ),
            [Color.FORE_BLUE, "10"],
            id="non-str-format-with-base-color",
        ),
        pytest.param(
            _s(Color.STYLE_BOLD, "%d"),
            (
                yuio.string.WithBaseColor(
                    yuio.string.Printable(10), base_color=Color.FORE_BLUE
                )
            ),
            [Color.FORE_BLUE | Color.STYLE_BOLD, "10"],
            id="non-str-format-with-base-color",
        ),
        pytest.param(
            ["%d"],
            (
                yuio.string.WithBaseColor(
                    yuio.string.WithBaseColor(
                        yuio.string.Printable(10), base_color=Color.FORE_BLUE
                    ),
                    base_color=Color.STYLE_BOLD,
                )
            ),
            [Color.FORE_BLUE | Color.STYLE_BOLD, "10"],
            id="non-str-format-with-base-color-nested",
        ),
        pytest.param(
            ["%d"],
            (
                yuio.string.WithBaseColor(
                    yuio.string.WithBaseColor(
                        yuio.string.Printable(10), base_color=Color.FORE_BLUE
                    ),
                    base_color=Color.FORE_RED,
                )
            ),
            [Color.FORE_BLUE, "10"],
            id="non-str-format-with-base-color-nested",
        ),
    ],
)
def test_string_format(text, args, expect, ctx):
    formatted = _s(text).percent_format(args, ctx=ctx)
    assert formatted._parts == expect


@pytest.mark.parametrize(
    ("text", "args", "exc", "match"),
    [
        ("%-%", (), ValueError, r"unsupported format character '%'"),
        ("%s", (), TypeError, r"not enough arguments for format string"),
        ("%d", (), TypeError, r"not enough arguments for format string"),
        ("%s %s", {}, TypeError, r"not enough arguments for format string"),
        ("%s %d", {}, TypeError, r"not enough arguments for format string"),
        ("%*s", (), TypeError, r"not enough arguments for format string"),
        ("%.*s", (), TypeError, r"not enough arguments for format string"),
        ("%*s", ("a"), TypeError, r"\* wants int"),
        ("%*s", {}, TypeError, r"\* wants int"),
        ("%*.*s", ("a", 10), TypeError, r"\* wants int"),
        ("%*s", ("a", "x"), TypeError, r"\* wants int"),
        ("%.*s", ("a", "x"), TypeError, r"\* wants int"),
        ("%.*s", {}, TypeError, r"\* wants int"),
        ("%(x)s", 10, TypeError, r"format requires a mapping"),
        ("%(x)d", 10, TypeError, r"format requires a mapping"),
        (
            "",
            ("foo",),
            TypeError,
            r"not all arguments converted during string formatting",
        ),
        ("", "foo", TypeError, r"not all arguments converted during string formatting"),
    ],
)
def test_format_error(text, args, exc, match, ctx):
    with pytest.raises(exc, match=match):
        _s(text).percent_format(args, ctx=ctx)


@pytest.mark.parametrize(
    ("text", "width", "kwargs", "expect"),
    [
        pytest.param(
            [],
            15,
            {},
            [
                [],
            ],
            id="empty",
        ),
        pytest.param(
            [""],
            15,
            {},
            [
                [],
            ],
            id="empty",
        ),
        pytest.param(
            ["hello world!"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
            ],
            id="single-part-no-wrap",
        ),
        pytest.param(
            ["hello world! 15"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!", " ", "15"],
            ],
            id="single-part-exact-fit",
        ),
        pytest.param(
            ["hello world! 👻"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!", " ", "👻"],
            ],
            id="single-part-exact-fit-wide-chars",
        ),
        pytest.param(
            ["hello world! this will wrap"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
                [Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
            id="single-part-wrap",
        ),
        pytest.param(
            ["hello world! 👻👻"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
                [Color.NONE, "👻👻"],
            ],
            id="single-part-wrap-wide-chars",
        ),
        pytest.param(
            ["hello", " ", "world!"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
            ],
            id="multi-parts-no-wrap",
        ),
        pytest.param(
            ["hello", " ", "world!", " ", "15"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!", " ", "15"],
            ],
            id="multi-parts-exact-fit",
        ),
        pytest.param(
            ["hello world!", " ", "👻"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!", " ", "👻"],
            ],
            id="multi-parts-exact-fit-wide-chars",
        ),
        pytest.param(
            ["hello", " ", "world!", " ", "this", " ", "will", " ", "wrap"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
                [Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
            id="multi-parts-wrap",
        ),
        pytest.param(
            ["hello", " ", "world!", " ", "👻👻"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
                [Color.NONE, "👻👻"],
            ],
            id="multi-parts-wrap-wide-chars",
        ),
        pytest.param(
            ["wo", "rd wo", "rd"],
            7,
            {},
            [
                [Color.NONE, "wo", "rd", " ", "wo"],
                [Color.NONE, "rd"],
            ],
            id="multi-parts-wrap-at-part-boundary",
        ),
        pytest.param(
            ["wo", "rd wo", "rd"],
            5,
            {},
            [
                [Color.NONE, "wo", "rd"],
                [Color.NONE, "wo", "rd"],
            ],
            id="multi-parts-wrap-in-middle",
        ),
        pytest.param(
            ["this-will-wrap-on-hyphen"],
            15,
            {},
            [
                [Color.NONE, "this-", "will-", "wrap-"],
                [Color.NONE, "on-", "hyphen"],
            ],
            id="single-part-hyphens",
        ),
        pytest.param(
            ["this.will.not.wrap.on.dot.this.is.too.long"],
            15,
            {},
            [
                [Color.NONE, "this.will.not.w"],
                [Color.NONE, "rap.on.dot.this"],
                [Color.NONE, ".is.too.long"],
            ],
            id="single-part-dots",
        ),
        pytest.param(
            ["this.will.not.wrap.on.dot.this.is.too.long"],
            15,
            {"break_long_words": False},
            [
                [Color.NONE, "this.will.not.wrap.on.dot.this.is.too.long"],
            ],
            id="single-part-dots-dont-break-long-words-hide-overflow",
        ),
        pytest.param(
            ["this.will.not.", "wrap.on.hyphen.this.is.too.long"],
            15,
            {},
            [
                [Color.NONE, "this.will.not."],
                [Color.NONE, "wrap.on.hyphen."],
                [Color.NONE, "this.is.too.lon"],
                [Color.NONE, "g"],
            ],
            id="multi-parts-dots",
        ),
        pytest.param(
            ["newlines will\nbe\nhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored",
        ),
        pytest.param(
            ["newlines will\r\nbe\r\nhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored",
        ),
        pytest.param(
            ["newlines will\rbe\rhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored",
        ),
        pytest.param(
            ["newlines will\v\nbe\v\nhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored-vertical-tab-sequence",
        ),
        pytest.param(
            ["newlines will\v\r\nbe\v\r\nhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored-vertical-tab-sequence",
        ),
        pytest.param(
            ["newlines will\v\rbe\v\rhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored-vertical-tab-sequence",
        ),
        pytest.param(
            ["newlines will\vbe\vhonored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-honored-vertical-tab-single",
        ),
        pytest.param(
            ["newlines will\n\nbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\r\n\r\nbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\r\rbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\n\rbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\v\vbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\v\r\n\v\r\nbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\v\r\v\rbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["newlines will\v\n\rbe honored!"],
            15,
            {},
            [
                [Color.NONE, "newlines", " ", "will"],
                [],
                [Color.NONE, "be", " ", "honored!"],
            ],
            id="explicit-newlines-honored-seq-line-breaks",
        ),
        pytest.param(
            ["break\n"],
            15,
            {},
            [
                [Color.NONE, "break"],
                [],
            ],
            id="explicit-newlines-honored-dangling-newline",
        ),
        pytest.param(
            ["newlines will\nnot be\nhonored!"],
            15,
            {"preserve_newlines": False},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "not", " ", "be", " ", "honored!"],
            ],
            id="explicit-newlines-not-honored",
        ),
        pytest.param(
            ["newlines will\v\nbe\v\nhonored!"],
            15,
            {"preserve_newlines": False},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-not-honored-but-vertical-tab-creates-break-anyways",
        ),
        pytest.param(
            ["newlines will\v\r\nbe\v\r\nhonored!"],
            15,
            {"preserve_newlines": False},
            [
                [Color.NONE, "newlines", " ", "will"],
                [Color.NONE, "be"],
                [Color.NONE, "honored!"],
            ],
            id="explicit-newlines-not-honored-but-vertical-tab-creates-break-anyways",
        ),
        pytest.param(
            ["hello world!     this will wrap"],
            15,
            {},
            [
                [Color.NONE, "hello", " ", "world!"],
                [Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
            id="multiple-spaces-collapsed-line-boundary",
        ),
        pytest.param(
            ["space before nl    \nis removed"],
            15,
            {},
            [
                [Color.NONE, "space", " ", "before", " ", "nl"],
                [Color.NONE, "is", " ", "removed"],
            ],
            id="multiple-spaces-collapsed-explicit-newline",
        ),
        pytest.param(
            ["space after nl\n    is kept"],
            15,
            {},
            [
                [Color.NONE, "space", " ", "after", " ", "nl"],
                [Color.NONE, "    ", "is", " ", "kept"],
            ],
            id="multiple-spaces-collapsed-explicit-newline-indent",
        ),
        pytest.param(
            ["hello\n\n\n\nworld!\r\n\r\n\r\rthis\n\n\n\n\nwill\n\n\n\n\nwrap"],
            15,
            {"preserve_spaces": False, "preserve_newlines": False},
            [
                [Color.NONE, "hello", " ", "world!"],
                [Color.NONE, "this", " ", "will", " ", "wrap"],
            ],
            id="multiple-spaces-collapsed-newlines-treated-as-spaces",
        ),
        pytest.param(
            ["hello   world!"],
            15,
            {"preserve_spaces": True},
            [
                [Color.NONE, "hello", "   ", "world!"],
            ],
            id="multiple-spaces-preserved",
        ),
        pytest.param(
            ["hello   world!"],
            15,
            {"preserve_spaces": False},
            [
                [Color.NONE, "hello", "   ", "world!"],
            ],
            id="multiple-spaces-preserved-when-no-line-boundary-happened",
        ),
        pytest.param(
            ["hello     world!"],
            15,
            {"preserve_spaces": True},
            [
                [Color.NONE, "hello", "     "],
                [Color.NONE, "world!"],
            ],
            id="multiple-spaces-preserved-line-boundary",
        ),
        pytest.param(
            ["hello                    world"],
            15,
            {"preserve_spaces": True},
            [
                [Color.NONE, "hello", "          "],
                [Color.NONE, "          ", "world"],
            ],
            id="multiple-spaces-preserved-line-boundary-long",
        ),
        pytest.param(
            ["hello                    longlongworld"],
            15,
            {"preserve_spaces": True},
            [
                [Color.NONE, "hello", "          "],
                [Color.NONE, "          "],
                [Color.NONE, "longlongworld"],
            ],
            id="multiple-spaces-preserved-line-boundary-long",
        ),
        pytest.param(
            ["hello                    world"],
            15,
            {"preserve_spaces": True, "break_long_words": False},
            [
                [Color.NONE, "hello", "          "],
                [Color.NONE, "          ", "world"],
            ],
            id="multiple-spaces-preserved-line-boundary-long-dont-break-long-words",
        ),
        pytest.param(
            ["hello                    longlongworld"],
            15,
            {"preserve_spaces": True, "break_long_words": False},
            [
                [Color.NONE, "hello", "          "],
                [Color.NONE, "          "],
                [Color.NONE, "longlongworld"],
            ],
            id="multiple-spaces-preserved-line-boundary-long",
        ),
        pytest.param(
            ["hello\n\n\n\nworld!\r\n\r\n\r\rthis\n\n\n\n\nwill\n\n\n\n\nwrap"],
            15,
            {"preserve_spaces": True, "preserve_newlines": False},
            [
                [Color.NONE, "hello", " ", " ", " ", " ", "world!"],
                [Color.NONE, " ", " ", " ", " ", "this", " ", " ", " ", " ", " "],
                [Color.NONE, "will", " ", " ", " ", " ", " ", "wrap"],
            ],
            id="multiple-spaces-preserved-newlines-treated-as-spaces",
        ),
        pytest.param(
            [
                Color.FORE_MAGENTA,
                "usage: ",
                Color.NONE,
                Color.NONE,
                "app.py train",
                Color.NONE,
                Color.NONE,
                " ",
                Color.NONE,
                "[",
                Color.FORE_BLUE,
                "-h",
                Color.NONE,
                "]",
                Color.NONE,
                " ",
                Color.NONE,
                "[",
                Color.FORE_BLUE,
                "-v",
                Color.NONE,
                "]",
                Color.NONE,
                " [",
                Color.NONE,
                Color.FORE_BLUE,
                "--force-color",
                Color.NONE,
                " | ",
                Color.NONE,
                Color.FORE_BLUE,
                "--force-no-color",
                Color.NONE,
                "] ",
                Color.NONE,
                "[",
                Color.FORE_BLUE,
                "-o",
                Color.NONE,
                " ",
                Color.FORE_MAGENTA,
                "",
                Color.NONE,
                "{",
                Color.FORE_MAGENTA,
                "path",
                Color.NONE,
                "}",
                Color.FORE_MAGENTA,
                "",
                Color.NONE,
                "]",
                Color.NONE,
                " ",
                Color.NONE,
                Color.FORE_MAGENTA,
                "",
                Color.NONE,
                "<",
                Color.FORE_MAGENTA,
                "data",
                Color.NONE,
                ">",
                Color.FORE_MAGENTA,
                "",
            ],
            100,
            {},
            [
                [
                    Color.FORE_MAGENTA,
                    "usage:",
                    " ",
                    Color.NONE,
                    "app.py",
                    " ",
                    "train",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "-h",
                    Color.NONE,
                    "]",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "-v",
                    Color.NONE,
                    "]",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "--force-",
                    "color",
                    Color.NONE,
                    " ",
                    "|",
                    " ",
                    Color.FORE_BLUE,
                    "--force-",
                    "no-",
                    "color",
                    Color.NONE,
                    "]",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "-o",
                    Color.NONE,
                    " ",
                    "{",
                    Color.FORE_MAGENTA,
                    "path",
                    Color.NONE,
                    "}",
                    "]",
                    " ",
                    "<",
                    Color.FORE_MAGENTA,
                    "data",
                    Color.NONE,
                    ">",
                ]
            ],
            id="colors",
        ),
        pytest.param(
            [
                Color.FORE_MAGENTA,
                "usage: ",
                Color.NONE,
                Color.NONE,
                "app.py train",
                Color.NONE,
                Color.NONE,
                " ",
                Color.NONE,
                "[",
                Color.FORE_BLUE,
                "-h",
                Color.NONE,
                "]",
                Color.NONE,
                " ",
                Color.NONE,
                "[",
                Color.FORE_BLUE,
                "-v",
                Color.NONE,
                "]",
                Color.NONE,
                " [",
                Color.NONE,
                Color.FORE_BLUE,
                "--force-color",
                Color.NONE,
                " | ",
                Color.NONE,
                Color.FORE_BLUE,
                "--force-no-color",
                Color.NONE,
                "] ",
                Color.NONE,
                "[",
                Color.FORE_BLUE,
                "-o",
                Color.NONE,
                " ",
                Color.FORE_MAGENTA,
                "",
                Color.NONE,
                "{",
                Color.FORE_MAGENTA,
                "path",
                Color.NONE,
                "}",
                Color.FORE_MAGENTA,
                "",
                Color.NONE,
                "]",
                Color.NONE,
                " ",
                Color.NONE,
                Color.FORE_MAGENTA,
                "",
                Color.NONE,
                "<",
                Color.FORE_MAGENTA,
                "data",
                Color.NONE,
                ">",
                Color.FORE_MAGENTA,
                "",
            ],
            15,
            {},
            [
                [
                    Color.FORE_MAGENTA,
                    "usage:",
                    " ",
                    Color.NONE,
                    "app.py",
                ],
                [
                    Color.NONE,
                    "train",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "-h",
                    Color.NONE,
                    "]",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "-v",
                    Color.NONE,
                    "]",
                ],
                [
                    Color.NONE,
                    "[",
                    Color.FORE_BLUE,
                    "--force-",
                    "color",
                ],
                [
                    Color.NONE,
                    "|",
                    " ",
                    Color.FORE_BLUE,
                    "--force-",
                    "no-",
                ],
                [
                    Color.FORE_BLUE,
                    "color",
                    Color.NONE,
                    "]",
                    " ",
                    "[",
                    Color.FORE_BLUE,
                    "-o",
                    Color.NONE,
                    " ",
                    "{",
                ],
                [
                    Color.FORE_MAGENTA,
                    "path",
                    Color.NONE,
                    "}",
                    "]",
                    " ",
                    "<",
                    Color.FORE_MAGENTA,
                    "data",
                    Color.NONE,
                    ">",
                ],
            ],
            id="colors-wrap",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo bar baz"],
            15,
            {},
            [
                [Color.FORE_RED, "foo bar baz"],
            ],
            id="no-wrap-simple",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo\nbar"],
            5,
            {},
            [
                [Color.FORE_RED, "foo"],
                [Color.FORE_RED, "bar"],
            ],
            id="no-wrap-newline",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo\nbar"],
            5,
            {"preserve_newlines": False},
            [
                [Color.FORE_RED, "foo"],
                [Color.FORE_RED, "bar"],
            ],
            id="no-wrap-newline-preserved",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo     baz"],
            15,
            {},
            [
                [Color.FORE_RED, "foo     baz"],
            ],
            id="no-wrap-preserve-spaces",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo", "     ", "baz"],
            15,
            {},
            [
                [Color.FORE_RED, "foo", "     ", "baz"],
            ],
            id="no-wrap-preserve-spaces-multi-parts",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo bar baz"],
            7,
            {},
            [
                [Color.FORE_RED, "foo bar baz"],
            ],
            id="no-wrap-long",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo", " ", "bar", " ", "baz"],
            7,
            {},
            [
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-long-multi-parts",
        ),
        pytest.param(
            [Color.FORE_RED, "xxx", NO_WRAP_START, "foo", " ", "bar", " ", "baz"],
            7,
            {},
            [
                [Color.FORE_RED, "xxx"],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [
                Color.FORE_RED,
                "xxx",
                "yyy",
                NO_WRAP_START,
                "foo",
                " ",
                "bar",
                " ",
                "baz",
            ],
            7,
            {},
            [
                [Color.FORE_RED, "xxx", "yyy"],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [Color.FORE_RED, "xxx", "yyy", NO_WRAP_START, "   "],
            7,
            {},
            [
                [Color.FORE_RED, "xxx", "yyy"],
                [Color.FORE_RED, "   "],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [Color.FORE_RED, "xxx ", NO_WRAP_START, "foo", " ", "bar", " ", "baz"],
            7,
            {},
            [
                [Color.FORE_RED, "xxx"],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [
                Color.FORE_RED,
                NO_WRAP_START,
                "xxx ",
                NO_WRAP_END,
                NO_WRAP_START,
                "foo",
                " ",
                "bar",
                " ",
                "baz",
            ],
            7,
            {},
            [
                [Color.FORE_RED, "xxx "],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [
                Color.FORE_RED,
                NO_WRAP_START,
                " ",
                NO_WRAP_END,
                NO_WRAP_START,
                "foo",
                " ",
                "bar",
                " ",
                "baz",
            ],
            7,
            {},
            [
                [Color.FORE_RED, " "],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [
                Color.FORE_RED,
                "xxx",
                NO_WRAP_START,
                " ",
                NO_WRAP_END,
                NO_WRAP_START,
                "foo",
                " ",
                "bar",
                " ",
                "baz",
            ],
            7,
            {},
            [
                [Color.FORE_RED, "xxx", " "],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [Color.FORE_RED, Esc(" "), NO_WRAP_START, "foo", " ", "bar", " ", "baz"],
            7,
            {},
            [
                [Color.FORE_RED, " "],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [
                Color.FORE_RED,
                "xxx",
                Esc(" "),
                NO_WRAP_START,
                "foo",
                " ",
                "bar",
                " ",
                "baz",
            ],
            7,
            {},
            [
                [Color.FORE_RED, "xxx", " "],
                [Color.FORE_RED, "foo", " ", "bar", " ", "baz"],
            ],
            id="no-wrap-break-before",
        ),
        pytest.param(
            [
                Color.FORE_RED,
                NO_WRAP_START,
                "foo",
                " ",
                Color.FORE_GREEN,
                "bar",
                " ",
                "baz",
                NO_WRAP_END,
                "xxx",
            ],
            7,
            {},
            [
                [Color.FORE_RED, "foo", " ", Color.FORE_GREEN, "bar", " ", "baz"],
                [Color.FORE_GREEN, "xxx"],
            ],
            id="no-wrap-break-after",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo bar baz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.FORE_RED, "foo bar"],
                [Color.FORE_RED, " baz"],
            ],
            id="no-wrap-break-long",
        ),
        pytest.param(
            [Color.FORE_RED, NO_WRAP_START, "foo", " ", "bar baz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.FORE_RED, "foo", " ", "bar"],
                [Color.FORE_RED, " baz"],
            ],
            id="no-wrap-break-long-multi-parts",
        ),
        pytest.param(
            [Color.FORE_RED, "xxx", NO_WRAP_START, "foo", " ", "bar"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.FORE_RED, "xxx"],
                [Color.FORE_RED, "foo", " ", "bar"],
            ],
            id="no-wrap-break-long-multi-parts",
        ),
        pytest.param(
            [Color.FORE_RED, "xxx", NO_WRAP_START, "foo", " ", "bar", " baz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.FORE_RED, "xxx"],
                [Color.FORE_RED, "foo", " ", "bar"],
                [Color.FORE_RED, " baz"],
            ],
            id="no-wrap-break-long-multi-parts",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), "hello world"],
            15,
            {},
            [
                [LinkMarker("https://a.com"), Color.NONE, "hello", " ", "world"],
            ],
            id="link-no-wrap",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), "this will wrap and keep link"],
            15,
            {},
            [
                [
                    LinkMarker("https://a.com"),
                    Color.NONE,
                    "this",
                    " ",
                    "will",
                    " ",
                    "wrap",
                ],
                [
                    LinkMarker("https://a.com"),
                    Color.NONE,
                    "and",
                    " ",
                    "keep",
                    " ",
                    "link",
                ],
            ],
            id="link-wrap",
        ),
        pytest.param(
            [LinkMarker("https://a.com"), "link wrap indent"],
            10,
            {"continuation_indent": "  "},
            [
                [
                    LinkMarker("https://a.com"),
                    Color.NONE,
                    "link",
                    " ",
                    "wrap",
                ],
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "  ",
                    NO_WRAP_END,
                    LinkMarker("https://a.com"),
                    "indent",
                ],
            ],
            id="link-wrap-indent-isolation",
        ),
        pytest.param(
            [Esc("xxx")],
            7,
            {},
            [
                [Color.NONE, "xxx"],
            ],
            id="esc",
        ),
        pytest.param(
            [Esc("a\nb")],
            7,
            {},
            [
                [Color.NONE, "a b"],
            ],
            id="esc-newline",
        ),
        pytest.param(
            [Esc("xxx xxx xxx")],
            7,
            {},
            [
                [Color.NONE, "xxx xxx xxx"],
            ],
            id="esc-long",
        ),
        pytest.param(
            ["yyy", Esc("xxx xxx xxx"), "zzz"],
            7,
            {},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "xxx xxx xxx"],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-wrap",
        ),
        pytest.param(
            ["yyy", Esc("          "), "zzz"],
            7,
            {},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "          "],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-space",
        ),
        pytest.param(
            [Esc("xxx xxx xxx")],
            7,
            {"preserve_spaces": True},
            [
                [Color.NONE, "xxx xxx xxx"],
            ],
            id="esc-long-preserve-spaces",
        ),
        pytest.param(
            ["yyy", Esc("xxx xxx xxx"), "zzz"],
            7,
            {"preserve_spaces": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "xxx xxx xxx"],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-wrap-preserve-spaces",
        ),
        pytest.param(
            ["yyy", Esc("          "), "zzz"],
            7,
            {"preserve_spaces": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "          "],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-space-preserve-spaces",
        ),
        pytest.param(
            [Esc("xxx xxx xxx")],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "xxx xxx xxx"],
            ],
            id="esc-long-break-long-nowrap-words",
        ),
        pytest.param(
            ["yyy", Esc("xxx xxx xxx"), "zzz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "xxx xxx xxx"],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-wrap-break-long-nowrap-words",
        ),
        pytest.param(
            ["yyy", Esc("          "), "zzz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "          "],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-space-break-long-nowrap-words",
        ),
        pytest.param(
            [Esc("xxx xxx xxx")],
            7,
            {"break_long_nowrap_words": True, "preserve_spaces": True},
            [
                [Color.NONE, "xxx xxx xxx"],
            ],
            id="esc-long-break-long-nowrap-words-preserve-spaces",
        ),
        pytest.param(
            ["yyy", Esc("xxx xxx xxx"), "zzz"],
            7,
            {"break_long_nowrap_words": True, "preserve_spaces": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "xxx xxx xxx"],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-wrap-break-long-nowrap-words-preserve-spaces",
        ),
        pytest.param(
            ["yyy", Esc("          "), "zzz"],
            7,
            {"break_long_nowrap_words": True, "preserve_spaces": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "          "],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-space-break-long-nowrap-words-preserve-spaces",
        ),
        pytest.param(
            [NO_WRAP_START, Esc("xxx")],
            7,
            {},
            [
                [Color.NONE, "xxx"],
            ],
            id="esc-nowrap",
        ),
        pytest.param(
            [NO_WRAP_START, Esc("xxx xxx xxx")],
            7,
            {},
            [
                [Color.NONE, "xxx xxx xxx"],
            ],
            id="esc-long-nowrap",
        ),
        pytest.param(
            [NO_WRAP_START, "yyy", Esc("xxx xxx xxx"), "zzz"],
            7,
            {},
            [
                [Color.NONE, "yyy", "xxx xxx xxx", "zzz"],
            ],
            id="esc-long-wrap-nowrap",
        ),
        pytest.param(
            [NO_WRAP_START, "yyy", Esc("          "), "zzz"],
            7,
            {},
            [
                [Color.NONE, "yyy", "          ", "zzz"],
            ],
            id="esc-long-space-nowrap",
        ),
        pytest.param(
            [NO_WRAP_START, Esc("xxx")],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "xxx"],
            ],
            id="esc-nowrap-break-long-nowrap-words",
        ),
        pytest.param(
            [NO_WRAP_START, Esc("xxx xxx xxx")],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "xxx xxx xxx"],
            ],
            id="esc-long-nowrap-break-long-nowrap-words",
        ),
        pytest.param(
            [NO_WRAP_START, "yyy", Esc("xxx xxx xxx"), "zzz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "xxx xxx xxx"],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-wrap-nowrap-break-long-nowrap-words",
        ),
        pytest.param(
            [NO_WRAP_START, "yyy", Esc("          "), "zzz"],
            7,
            {"break_long_nowrap_words": True},
            [
                [Color.NONE, "yyy"],
                [Color.NONE, "          "],
                [Color.NONE, "zzz"],
            ],
            id="esc-long-space-nowrap-break-long-nowrap-words",
        ),
        pytest.param(
            ["single string"],
            100,
            {"indent": ">>"},
            [
                [
                    NO_WRAP_START,
                    Color.NONE,
                    ">>",
                    NO_WRAP_END,
                    "single",
                    " ",
                    "string",
                ],
            ],
            id="first-line-indent",
        ),
        pytest.param(
            ["single string"],
            100,
            {"continuation_indent": ">>"},
            [
                [Color.NONE, "single", " ", "string"],
            ],
            id="continuation-indent",
        ),
        pytest.param(
            ["single string"],
            13,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END, "single"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "string"],
            ],
            id="indent",
        ),
        pytest.param(
            ["single string"],
            13,
            {"indent": 2, "continuation_indent": 3},
            [
                [NO_WRAP_START, Color.NONE, "  ", NO_WRAP_END, "single"],
                [NO_WRAP_START, Color.NONE, "   ", NO_WRAP_END, "string"],
            ],
            id="indent-int",
        ),
        pytest.param(
            ["foo bar baz"],
            8,
            {"indent": ">>>", "continuation_indent": "|"},
            [
                [NO_WRAP_START, Color.NONE, ">>>", NO_WRAP_END, "foo"],
                [NO_WRAP_START, Color.NONE, "|", NO_WRAP_END, "bar", " ", "baz"],
            ],
            id="indent-different-widths",
        ),
        pytest.param(
            ["word werywerylongunbreakableword"],
            8,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END, "word"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "werywe"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "rylong"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "unbrea"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "kablew"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "ord"],
            ],
            id="indent-break-long-words",
        ),
        pytest.param(
            ["werywerylongunbreakableword"],
            8,
            {"indent": ">>>", "continuation_indent": "."},
            [
                [NO_WRAP_START, Color.NONE, ">>>", NO_WRAP_END, "weryw"],
                [NO_WRAP_START, Color.NONE, ".", NO_WRAP_END, "erylong"],
                [NO_WRAP_START, Color.NONE, ".", NO_WRAP_END, "unbreak"],
                [NO_WRAP_START, Color.NONE, ".", NO_WRAP_END, "ablewor"],
                [NO_WRAP_START, Color.NONE, ".", NO_WRAP_END, "d"],
            ],
            id="indent-different-widths-break-long-words",
        ),
        pytest.param(
            ["single string", "\nnext string"],
            13,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END, "single"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "string"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "next", " ", "string"],
            ],
            id="indent-explicit-newline",
        ),
        pytest.param(
            ["a\n\nb"],
            13,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END, "a"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "b"],
            ],
            id="indent-explicit-newline-empty",
        ),
        pytest.param(
            ["a\n"],
            13,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END, "a"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END],
            ],
            id="indent-explicit-newline-empty",
        ),
        pytest.param(
            ["\na"],
            13,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "a"],
            ],
            id="indent-explicit-newline-empty",
        ),
        pytest.param(
            ["\nwerywerylongunbreakableword"],
            13,
            {"indent": ">>", "continuation_indent": ".."},
            [
                [NO_WRAP_START, Color.NONE, ">>", NO_WRAP_END],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "werywerylon"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "gunbreakabl"],
                [NO_WRAP_START, Color.NONE, "..", NO_WRAP_END, "eword"],
            ],
            id="indent-explicit-newline-empty",
        ),
        pytest.param(
            [Color.FORE_BLUE, "single string"],
            13,
            {
                "indent": _s(Color.FORE_MAGENTA, ">>"),
                "continuation_indent": _s(Color.FORE_BLUE, ".."),
            },
            [
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    ">>",
                    NO_WRAP_END,
                    Color.FORE_BLUE,
                    "single",
                ],
                [
                    NO_WRAP_START,
                    Color.FORE_BLUE,
                    "..",
                    NO_WRAP_END,
                    "string",
                ],
            ],
            id="indent-colors",
        ),
        pytest.param(
            ["this.will.not.wrap.on.dot.this.is.too.long"],
            15,
            {"break_long_words": False, "overflow": ""},
            [
                [Color.NONE, "this.will.not.w"],
            ],
            id="ellipsis-long-word-empty",
        ),
        pytest.param(
            ["this.will.not.wrap.on.dot.this.is.too.long"],
            15,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "this.will.not.…"],
            ],
            id="ellipsis-long-word",
        ),
        pytest.param(
            ["this.will.not.wrap.on.dot.this.is.too.long"],
            15,
            {"overflow": ""},
            [
                [Color.NONE, "this.will.not.w"],
                [Color.NONE, "rap.on.dot.this"],
                [Color.NONE, ".is.too.long"],
            ],
            id="ellipsis-long-word-break",
        ),
        pytest.param(
            ["some.very.long.word some.very.long.word"],
            15,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "some.very.long…"],
                [Color.NONE, "some.very.long…"],
            ],
            id="ellipsis-long-word-consecutive-words",
        ),
        pytest.param(
            [Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": ""},
            [
                [],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            [Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word", Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": ""},
            [
                [Color.NONE, "word"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word", Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word", Esc("some-long-esc-word"), Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word", Esc("some-long-esc-word"), Esc("some-long-esc-word"), "12"],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…", "12"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word\n", Esc("some-long-esc-word"), Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word"],
                [Color.NONE, "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word", Esc("some-long-esc-word"), "\n", Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…"],
                [Color.NONE, "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            [
                "word",
                Esc("some-long-esc-word"),
                "\n",
                Esc("some-long-esc-word"),
                "123",
                Esc("some-long-esc-word"),
            ],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…"],
                [Color.NONE, "…", "123", "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            [
                "word",
                Esc("some-long-esc-word"),
                "\n",
                Esc("some-long-esc-word"),
                "123",
                Esc("esc-esc"),
            ],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…"],
                [Color.NONE, "…", "123"],
                [Color.NONE, "esc-esc"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["1234567", Esc("some-long-esc-word")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [[Color.NONE, "1234567"], [Color.NONE, "…"]],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["1234567", Esc("some-long-esc-word"), Esc("some-long-esc-word-2")],
            7,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "1234567"],
                [Color.NONE, "…"],
            ],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["1234567", Esc("some-long-esc-word"), "long_word_2"],
            7,
            {"break_long_words": False, "overflow": "…"},
            [[Color.NONE, "1234567"], [Color.NONE, "…"], [Color.NONE, "long_w…"]],
            id="ellipsis-esc",
        ),
        pytest.param(
            ["word", Esc("some-long-esc-word"), "    x"],
            10,
            {"break_long_words": False, "overflow": "…"},
            [
                [Color.NONE, "word", "…", "    ", "x"],
            ],
            id="ellipsis-esc-indent",
        ),
        pytest.param(
            [NO_WRAP_START, "some long word"],
            7,
            {"overflow": ""},
            [
                [Color.NONE, "some lo"],
            ],
            id="no-wrap-ellipsis",
        ),
        pytest.param(
            [NO_WRAP_START, "some long word"],
            7,
            {"overflow": "~"},
            [
                [Color.NONE, "some l~"],
            ],
            id="no-wrap-ellipsis",
        ),
        pytest.param(
            ["word"],
            0,
            {},
            [
                [Color.NONE, "w"],
                [Color.NONE, "o"],
                [Color.NONE, "r"],
                [Color.NONE, "d"],
            ],
            id="not-enough-space",
        ),
        pytest.param(
            ["word"],
            0,
            {"overflow": ""},
            [[], [], [], []],
            id="not-enough-space-overflow",
        ),
        pytest.param(
            ["word"],
            0,
            {"overflow": "~"},
            [[]],
            id="not-enough-space-overflow-2",
        ),
    ],
)
def test_wrap(text, width, kwargs, expect):
    wrapped = _s(text).wrap(width, **kwargs)
    raw = [line._parts for line in wrapped]
    assert raw == expect


@pytest.mark.parametrize(
    ("text", "indent", "continuation_indent", "expect"),
    [
        (
            _s(),
            _s(),
            _s(),
            [],
        ),
        (
            _s(""),
            _s(),
            _s(),
            [],
        ),
        (
            _s("abc"),
            _s(),
            _s(),
            [Color.NONE, "abc"],
        ),
        (
            _s("abc\n"),
            _s(),
            _s(),
            [Color.NONE, "abc\n"],
        ),
        (
            _s(),
            _s("1"),
            _s("2"),
            [],
        ),
        (
            _s(""),
            _s("1"),
            _s("2"),
            [],
        ),
        (
            _s("abc"),
            _s("1"),
            _s("2"),
            [NO_WRAP_START, Color.NONE, "1", NO_WRAP_END, "abc"],
        ),
        (
            _s("abc\n"),
            _s("1"),
            _s("2"),
            [NO_WRAP_START, Color.NONE, "1", NO_WRAP_END, "abc\n"],
        ),
        (
            _s("abc", "def"),
            _s("1"),
            _s("2"),
            [NO_WRAP_START, Color.NONE, "1", NO_WRAP_END, "abc", "def"],
        ),
        (
            _s("abc\ndef"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def",
            ],
        ),
        (
            _s("abc\n", "def"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def",
            ],
        ),
        (
            _s("abc", "\n", "def"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc",
                "\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def",
            ],
        ),
        (
            _s("abc\ndef\n"),
            4,
            None,
            [
                NO_WRAP_START,
                Color.NONE,
                "    ",
                NO_WRAP_END,
                "abc\n",
                NO_WRAP_START,
                "    ",
                NO_WRAP_END,
                "def\n",
            ],
        ),
        (
            _s("abc\ndef\n"),
            4,
            3,
            [
                NO_WRAP_START,
                Color.NONE,
                "    ",
                NO_WRAP_END,
                "abc\n",
                NO_WRAP_START,
                "   ",
                NO_WRAP_END,
                "def\n",
            ],
        ),
        (
            _s("abc\ndef\n"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\n",
            ],
        ),
        (
            _s("abc\r\ndef\r\n"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\r\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\r\n",
            ],
        ),
        (
            _s("abc\rdef\r"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\r",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\r",
            ],
        ),
        (
            _s("abc\v\ndef\v\n"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\v\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\v\n",
            ],
        ),
        (
            _s("abc\v\r\ndef\v\r\n"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\v\r\n",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\v\r\n",
            ],
        ),
        (
            _s("abc\v\rdef\v\r"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\v\r",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\v\r",
            ],
        ),
        (
            _s("abc\vdef\v"),
            _s("1"),
            _s("2"),
            [
                NO_WRAP_START,
                Color.NONE,
                "1",
                NO_WRAP_END,
                "abc\v",
                NO_WRAP_START,
                "2",
                NO_WRAP_END,
                "def\v",
            ],
        ),
        (
            _s("abc\ndef"),
            _s("1"),
            _s(),
            [NO_WRAP_START, Color.NONE, "1", NO_WRAP_END, "abc\n", "def"],
        ),
        (
            _s("abc\ndef"),
            _s(),
            _s("2"),
            [Color.NONE, "abc\n", NO_WRAP_START, "2", NO_WRAP_END, "def"],
        ),
        (
            _s("abc\ndef"),
            _s(Color.FORE_RED, "1"),
            _s(Color.FORE_BLUE, "2"),
            [
                NO_WRAP_START,
                Color.FORE_RED,
                "1",
                NO_WRAP_END,
                Color.NONE,
                "abc\n",
                NO_WRAP_START,
                Color.FORE_BLUE,
                "2",
                NO_WRAP_END,
                Color.NONE,
                "def",
            ],
        ),
        (
            _s(Color.FORE_YELLOW, "abc\ndef"),
            _s(Color.FORE_RED, "1"),
            _s(Color.FORE_BLUE, "2"),
            [
                NO_WRAP_START,
                Color.FORE_RED,
                "1",
                NO_WRAP_END,
                Color.FORE_YELLOW,
                "abc\n",
                NO_WRAP_START,
                Color.FORE_BLUE,
                "2",
                NO_WRAP_END,
                Color.FORE_YELLOW,
                "def",
            ],
        ),
        (
            _s("abc\n", Color.FORE_YELLOW, "def\nghi"),
            _s(Color.FORE_RED, "1"),
            _s(Color.FORE_BLUE, "2"),
            [
                NO_WRAP_START,
                Color.FORE_RED,
                "1",
                NO_WRAP_END,
                Color.NONE,
                "abc\n",
                NO_WRAP_START,
                Color.FORE_BLUE,
                "2",
                NO_WRAP_END,
                Color.FORE_YELLOW,
                "def\n",
                NO_WRAP_START,
                Color.FORE_BLUE,
                "2",
                NO_WRAP_END,
                Color.FORE_YELLOW,
                "ghi",
            ],
        ),
        (
            _s("abc", Color.FORE_YELLOW, "\ndef\nghi"),
            _s(Color.FORE_RED, "1"),
            _s(Color.FORE_BLUE, "2"),
            [
                NO_WRAP_START,
                Color.FORE_RED,
                "1",
                NO_WRAP_END,
                Color.NONE,
                "abc",
                Color.FORE_YELLOW,
                "\n",
                NO_WRAP_START,
                Color.FORE_BLUE,
                "2",
                NO_WRAP_END,
                Color.FORE_YELLOW,
                "def\n",
                NO_WRAP_START,
                Color.FORE_BLUE,
                "2",
                NO_WRAP_END,
                Color.FORE_YELLOW,
                "ghi",
            ],
        ),
        (
            _s(LinkMarker("https://a.com"), "abc\ndef"),
            _s(">>"),
            None,
            [
                NO_WRAP_START,
                Color.NONE,
                ">>",
                NO_WRAP_END,
                LinkMarker("https://a.com"),
                "abc\n",
                LinkMarker(None),
                NO_WRAP_START,
                ">>",
                NO_WRAP_END,
                LinkMarker("https://a.com"),
                "def",
            ],
        ),
    ],
)
def test_indent(text, indent, continuation_indent, expect):
    assert _join_consecutive_strings(
        text.indent(indent, continuation_indent)._parts
    ) == _join_consecutive_strings(expect)


class ColorfulObject:
    def __colorized_str__(self, ctx):
        return _s(Color.FORE_RED | Color.BACK_WHITE, "boop")

    def __colorized_repr__(self, ctx):
        return _s(Color.FORE_RED | Color.BACK_WHITE, "repr")


class NotSoColorfulObject:
    def __colorized_str__(self, ctx):
        return _s("foo")

    def __colorized_repr__(self, ctx):
        return _s("bar")


class ColorfulObjectBroken:
    def __colorized_str__(self, ctx):
        return 10

    def __colorized_repr__(self, ctx):
        return 10


class ColorfulObjectTheme:
    def __colorized_str__(self, ctx):
        return _s(ctx.theme.get_color("red") | Color.BACK_WHITE, "boop")

    def __colorized_repr__(self, ctx):
        return _s(ctx.theme.get_color("red") | Color.BACK_WHITE, "repr")


class ColorfulObjectError:
    def __colorized_str__(self, ctx):
        raise RuntimeError("something went wrong")

    def __colorized_repr__(self, ctx):
        raise RuntimeError("something went wrong")


class FallbackToStr:
    def __colorized_repr__(self, ctx):
        return _s("__colorized_repr__")

    def __str__(self):
        return "__str__"


class FallbackToColorizedRepr:
    def __colorized_repr__(self, ctx):
        return _s("__colorized_repr__")


class FallbackToRepr:
    def __repr__(self):
        return "__repr__"


class ColorfulObjectNested:
    def __colorized_str__(self, ctx):
        return _s("boop") + ctx.str("123")


class ColorfulObjectRecursive:
    def __colorized_str__(self, ctx):
        return _s("boop") + ctx.str(self)


class ColorfulObjectDeep:
    def __init__(self, depth: int) -> None:
        self.depth = depth

    def __colorized_str__(self, ctx):
        if self.depth == 0:
            return _s("boop")
        else:
            return str(self.depth) + " " + ctx.str(ColorfulObjectDeep(self.depth - 1))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(
            None,
            [Color.NONE, "None"],
            id="none",
        ),
        pytest.param(
            "string",
            [Color.NONE, "string"],
            id="str",
        ),
        pytest.param(
            [1, 2, 3],
            [
                Color.NONE,
                "[1, 2, 3]",
            ],
            id="object",
        ),
        pytest.param(
            _s(Color.FORE_RED, "boop"),
            [
                Color.FORE_RED,
                "boop",
            ],
            id="colorized-str",
        ),
        pytest.param(
            ColorfulObject,
            [
                Color.NONE,
                "test.test_string.ColorfulObject",
            ],
            id="type",
        ),
        pytest.param(
            ColorfulObject(),
            [
                Color.FORE_RED | Color.BACK_WHITE,
                "boop",
            ],
            id="custom-impl",
        ),
        pytest.param(
            NotSoColorfulObject(),
            [
                Color.NONE,
                "foo",
            ],
            id="custom-impl-return-str",
        ),
        pytest.param(
            ColorfulObjectBroken(),
            [
                Color.STYLE_INVERSE | Color.FORE_RED,
                "TypeError: __colorized_str__ returned non-colorized-string (type int)",
            ],
            id="custom-impl-return-non-str",
        ),
        pytest.param(
            ColorfulObjectTheme(),
            [
                Color.FORE_RED | Color.BACK_WHITE,
                "boop",
            ],
            id="custom-impl-use-theme",
        ),
        pytest.param(
            ColorfulObjectError(),
            [
                Color.STYLE_INVERSE | Color.FORE_RED,
                "RuntimeError: something went wrong",
            ],
            id="error-in-impl",
        ),
        pytest.param(
            FallbackToStr(),
            [Color.NONE, "__str__"],
            id="fallback-to-str",
        ),
        pytest.param(
            FallbackToColorizedRepr(),
            [
                Color.NONE,
                "__colorized_repr__",
            ],
            id="fallback-to-colorized-repr",
        ),
        pytest.param(
            FallbackToRepr(),
            [Color.NONE, "__repr__"],
            id="fallback-to-repr",
        ),
        pytest.param(
            ColorfulObjectNested(),
            [
                Color.NONE,
                "boop123",
            ],
            id="nested-call",
        ),
        pytest.param(
            ColorfulObjectRecursive(),
            [Color.NONE, "boop", "..."],
            id="nested-recursive-call",
        ),
        pytest.param(
            ColorfulObjectDeep(10),
            [
                Color.NONE,
                "10 9 8 7 6 5 4 3 2 1 boop",
            ],
            id="str-does-not-affect-depth",
        ),
    ],
)
def test_colorized_str(value, expected, ctx):
    assert _join_consecutive_strings(
        ctx.str(value)._parts
    ) == _join_consecutive_strings(expected)


@dataclass
class DataClassEmpty:
    pass


@dataclass
class DataClass:
    x: int = 11
    y: str = "asd"


@dataclass
class DataClassWithCustomRepr:
    x: int = 11
    y: str = "asd"

    def __repr__(self) -> str:
        return "custom repr"


@dataclass
class DataClassWithLimitedRepr:
    x: int = 11
    y: str = dataclasses.field(default="asd", repr=False)


@dataclass(repr=False)
class DataClassWithNoRepr:
    x: int = 11
    y: str = "asd"


DATA_CLASS_WITH_NO_REPR = DataClassWithNoRepr()
DATA_CLASS_WITH_NO_REPR_REPR = repr(DATA_CLASS_WITH_NO_REPR)


class ListWithCustomRepr(list):  # type: ignore
    def __repr__(self) -> str:
        return "custom repr"


class RichReprEmpty:
    def __rich_repr__(self):
        if False:
            yield


class RichReprDidNotReturn:
    def __rich_repr__(self):
        pass


class RichReprBroken:
    def __rich_repr__(self):
        raise RuntimeError("something went wrong")


class RichRepr:
    def __rich_repr__(self):
        yield "pos"
        yield ("pos-x",)
        yield None, "pos2"
        yield None, "pos3", "default"
        yield None, "pos4", "pos4"
        yield "kw2", "kw-val-2"
        yield "kw3", "kw-val-3", "default"
        yield "kw4", "kw-val-4", "kw-val-4"
        yield 1, 2, 3, 4, 5


class RichReprAngular:
    def __rich_repr__(self):
        yield 1
        yield "x", 2

    __rich_repr__.angular = True  # type: ignore


class Str:
    def __init__(self, value) -> None:
        self.value = value

    def __colorized_repr__(self, ctx):
        return ctx.str(self.value)


@pytest.mark.parametrize(
    "highlighted",
    [True, False],
    ids=["highlighted", "plain"],
)
@pytest.mark.parametrize(
    ("value", "expected", "multiline", "max_depth"),
    [
        pytest.param(
            list,
            [
                Color.FORE_BLACK,
                "list",
            ],
            False,
            5,
            id="type",
        ),
        pytest.param(
            None,
            [Color.FORE_YELLOW, "None"],
            False,
            5,
            id="none",
        ),
        pytest.param(
            None,
            [Color.FORE_YELLOW, "None"],
            True,
            5,
            id="none-multiline",
        ),
        pytest.param(
            "string",
            [Color.FORE_GREEN, "'string'"],
            False,
            5,
            id="str",
        ),
        pytest.param(
            [1, 2, 3],
            [
                Color.FORE_CYAN,
                "[",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                "]",
            ],
            False,
            5,
            id="list",
        ),
        pytest.param(
            [1, 2, 3],
            [
                Color.FORE_CYAN,
                "[",
                Color.NONE,
                "\n  ",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_YELLOW,
                "3",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                "]",
            ],
            True,
            5,
            id="list-multiline",
        ),
        pytest.param(
            [1, 2, 3],
            [
                Color.FORE_CYAN,
                "[",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                "]",
            ],
            False,
            0,
            id="list-more",
        ),
        pytest.param(
            [1, 2, 3],
            [
                Color.FORE_CYAN,
                "[",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                "]",
            ],
            True,
            0,
            id="list-more-multiline",
        ),
        pytest.param(
            DataClassEmpty(),
            [
                Color.FORE_BLACK,
                "DataClassEmpty",
                Color.FORE_CYAN,
                "()",
            ],
            False,
            5,
            id="dataclass-empty",
        ),
        pytest.param(
            DataClassEmpty(),
            [
                Color.FORE_BLACK,
                "DataClassEmpty",
                Color.FORE_CYAN,
                "()",
            ],
            True,
            5,
            id="dataclass-empty-multiline",
        ),
        pytest.param(
            DataClass(),
            [
                Color.FORE_BLACK,
                "DataClass",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "x",
                Color.FORE_CYAN,
                "=",
                Color.FORE_YELLOW,
                "11",
                Color.FORE_CYAN,
                ", ",
                Color.NONE,
                "y",
                Color.FORE_CYAN,
                "=",
                Color.FORE_GREEN,
                "'asd'",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            5,
            id="dataclass",
        ),
        pytest.param(
            DataClass(),
            [
                Color.FORE_BLACK,
                "DataClass",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "\n  ",
                "x",
                Color.FORE_CYAN,
                "=",
                Color.FORE_YELLOW,
                "11",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                "y",
                Color.FORE_CYAN,
                "=",
                Color.FORE_GREEN,
                "'asd'",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                ")",
            ],
            True,
            5,
            id="dataclass-multiline",
        ),
        pytest.param(
            DataClass(),
            [
                Color.FORE_BLACK,
                "DataClass",
                Color.FORE_CYAN,
                "(",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            0,
            id="dataclass-more",
        ),
        pytest.param(
            DataClass(),
            [
                Color.FORE_BLACK,
                "DataClass",
                Color.FORE_CYAN,
                "(",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ")",
            ],
            True,
            0,
            id="dataclass-more-multiline",
        ),
        pytest.param(
            DataClassWithCustomRepr(),
            [Color.NONE, "custom repr"],
            False,
            0,
            id="dataclass-custom-repr",
        ),
        pytest.param(
            DataClassWithLimitedRepr(),
            [
                Color.FORE_BLACK,
                "DataClassWithLimitedRepr",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "x",
                Color.FORE_CYAN,
                "=",
                Color.FORE_YELLOW,
                "11",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            5,
            id="dataclass-exclude-field",
        ),
        pytest.param(
            collections.defaultdict(int, {"a": 10}),
            [
                Color.FORE_BLACK,
                "defaultdict",
                Color.FORE_CYAN,
                "(",
                Color.FORE_BLACK,
                "int",
                Color.FORE_CYAN,
                ", {",
                Color.FORE_GREEN,
                "'a'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_YELLOW,
                "10",
                Color.FORE_CYAN,
                "})",
            ],
            False,
            5,
            id="defaultdict",
        ),
        pytest.param(
            collections.defaultdict(int, {"a": 10}),
            [
                Color.FORE_BLACK,
                "defaultdict",
                Color.FORE_CYAN,
                "(",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            0,
            id="defaultdict-more",
        ),
        pytest.param(
            collections.deque([1, 2, 3]),
            [
                Color.FORE_BLACK,
                "deque",
                Color.FORE_CYAN,
                "([",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                "])",
            ],
            False,
            5,
            id="deque",
        ),
        pytest.param(
            collections.deque([1, 2, 3]),
            [
                Color.FORE_BLACK,
                "deque",
                Color.FORE_CYAN,
                "(",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            0,
            id="deque-more",
        ),
        pytest.param(
            collections.deque([1, 2, 3], maxlen=10),
            [
                Color.FORE_BLACK,
                "deque",
                Color.FORE_CYAN,
                "([",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                "], ",
                Color.NONE,
                "maxlen",
                Color.FORE_CYAN,
                "=",
                Color.FORE_YELLOW,
                "10",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            5,
            id="deque-maxlen",
        ),
        pytest.param(
            collections.deque([1, 2, 3]),
            [
                Color.FORE_BLACK,
                "deque",
                Color.FORE_CYAN,
                "(",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            0,
            id="deque-maxlen-more",
        ),
        pytest.param(
            collections.Counter([1, 2, 2, 3]),
            [
                Color.FORE_BLACK,
                "Counter",
                Color.FORE_CYAN,
                "({",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                "})",
            ],
            False,
            5,
            id="counter",
        ),
        pytest.param(
            collections.Counter([1, 2, 2, 3]),
            [
                Color.FORE_BLACK,
                "Counter",
                Color.FORE_CYAN,
                "({",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                "})",
            ],
            False,
            0,
            id="counter-more",
        ),
        pytest.param(
            collections.UserList([1, 2, 3]),
            [
                Color.FORE_CYAN,
                "[",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                "]",
            ],
            False,
            5,
            id="user-list",
        ),
        pytest.param(
            collections.UserDict({"a": "b"}),
            [
                Color.FORE_CYAN,
                "{",
                Color.FORE_GREEN,
                "'a'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_GREEN,
                "'b'",
                Color.FORE_CYAN,
                "}",
            ],
            False,
            5,
            id="user-dict",
        ),
        pytest.param(
            {1, 2, 3},
            [
                Color.FORE_CYAN,
                "{",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                "}",
            ],
            False,
            5,
            id="set",
        ),
        pytest.param(
            frozenset([1, 2, 3]),
            [
                Color.FORE_BLACK,
                "frozenset",
                Color.FORE_CYAN,
                "({",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                "})",
            ],
            False,
            5,
            id="frozenset",
        ),
        pytest.param(
            (1, 2, 3),
            [
                Color.FORE_CYAN,
                "(",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            5,
            id="tuple",
        ),
        pytest.param(
            {"a": "b"},
            [
                Color.FORE_CYAN,
                "{",
                Color.FORE_GREEN,
                "'a'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_GREEN,
                "'b'",
                Color.FORE_CYAN,
                "}",
            ],
            False,
            5,
            id="dict",
        ),
        pytest.param(
            {"a": "b"},
            [
                Color.FORE_CYAN,
                "{",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'a'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_GREEN,
                "'b'",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                "}",
            ],
            True,
            5,
            id="dict-multiline",
        ),
        pytest.param(
            {"a": "b", "x": 10},
            [
                Color.FORE_CYAN,
                "{",
                Color.FORE_GREEN,
                "'a'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_GREEN,
                "'b'",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_GREEN,
                "'x'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_YELLOW,
                "10",
                Color.FORE_CYAN,
                "}",
            ],
            False,
            5,
            id="dict",
        ),
        pytest.param(
            {"a": "b", "x": 10},
            [
                Color.FORE_CYAN,
                "{",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'a'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_GREEN,
                "'b'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'x'",
                Color.FORE_CYAN,
                ": ",
                Color.FORE_YELLOW,
                "10",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                "}",
            ],
            True,
            5,
            id="dict-2-multiline",
        ),
        pytest.param(
            {},
            [Color.FORE_CYAN, "{", "}"],
            False,
            5,
            id="dict-empty",
        ),
        pytest.param(
            {},
            [Color.FORE_CYAN, "{", "}"],
            True,
            5,
            id="dict-empty-multiline",
        ),
        pytest.param(
            {(1, 2): "123"},
            [
                Color.FORE_CYAN,
                "{(",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                "): ",
                Color.FORE_GREEN,
                "'123'",
                Color.FORE_CYAN,
                "}",
            ],
            False,
            5,
            id="dict-tuple-key",
        ),
        pytest.param(
            {(1, 2): "123"},
            [
                Color.FORE_CYAN,
                "{",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "2",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                "): ",
                Color.FORE_GREEN,
                "'123'",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                "}",
            ],
            True,
            5,
            id="dict-tuple-key-multiline",
        ),
        pytest.param(
            {(1, 2): (3, 4)},
            [
                Color.FORE_CYAN,
                "{",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "2",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                "): (",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "4",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                ")",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                "}",
            ],
            True,
            5,
            id="dict-tuple-key-value-multiline",
        ),
        pytest.param(
            ListWithCustomRepr([1, 2, 3]),
            [Color.NONE, "custom repr"],
            True,
            5,
            id="list-custom-repr",
        ),
        pytest.param(
            RichReprEmpty(),
            [
                Color.FORE_BLACK,
                "RichReprEmpty",
                Color.FORE_CYAN,
                "()",
            ],
            False,
            5,
            id="rich-repr-empty",
        ),
        pytest.param(
            RichReprEmpty(),
            [
                Color.FORE_BLACK,
                "RichReprEmpty",
                Color.FORE_CYAN,
                "()",
            ],
            True,
            5,
            id="rich-repr-empty-multiline",
        ),
        pytest.param(
            RichReprDidNotReturn(),
            [
                Color.FORE_BLACK,
                "RichReprDidNotReturn",
                Color.FORE_CYAN,
                "()",
            ],
            False,
            5,
            id="rich-repr-did-not-return",
        ),
        pytest.param(
            RichReprBroken(),
            [
                Color.STYLE_INVERSE | Color.FORE_RED,
                "RuntimeError: something went wrong",
            ],
            False,
            5,
            id="rich-repr-broken",
        ),
        pytest.param(
            RichRepr(),
            [
                Color.FORE_BLACK,
                "RichRepr",
                Color.FORE_CYAN,
                "(",
                Color.FORE_GREEN,
                "'pos'",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_GREEN,
                "'pos-x'",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_GREEN,
                "'pos2'",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_GREEN,
                "'pos3'",
                Color.FORE_CYAN,
                ", ",
                Color.NONE,
                "kw2",
                Color.FORE_CYAN,
                "=",
                Color.FORE_GREEN,
                "'kw-val-2'",
                Color.FORE_CYAN,
                ", ",
                Color.NONE,
                "kw3",
                Color.FORE_CYAN,
                "=",
                Color.FORE_GREEN,
                "'kw-val-3'",
                Color.FORE_CYAN,
                ", (",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "4",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "5",
                Color.FORE_CYAN,
                "))",
            ],
            False,
            5,
            id="rich-repr",
        ),
        pytest.param(
            RichRepr(),
            [
                Color.FORE_BLACK,
                "RichRepr",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'pos'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'pos-x'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'pos2'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_GREEN,
                "'pos3'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                "kw2",
                Color.FORE_CYAN,
                "=",
                Color.FORE_GREEN,
                "'kw-val-2'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                "kw3",
                Color.FORE_CYAN,
                "=",
                Color.FORE_GREEN,
                "'kw-val-3'",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                "(",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "3",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "4",
                Color.FORE_CYAN,
                ",",
                Color.NONE,
                "\n    ",
                Color.FORE_YELLOW,
                "5",
                Color.NONE,
                "\n  ",
                Color.FORE_CYAN,
                ")",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                ")",
            ],
            True,
            5,
            id="rich-repr-multiline",
        ),
        pytest.param(
            RichRepr(),
            [
                Color.FORE_BLACK,
                "RichRepr",
                Color.FORE_CYAN,
                "(",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ")",
            ],
            False,
            0,
            id="rich-repr-more",
        ),
        pytest.param(
            RichReprAngular(),
            [
                Color.FORE_CYAN,
                "<",
                Color.FORE_BLACK,
                "RichReprAngular",
                Color.NONE,
                " ",
                Color.FORE_YELLOW,
                "1",
                Color.NONE,
                "x",
                Color.FORE_CYAN,
                "=",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ">",
            ],
            False,
            5,
            id="rich-repr-angular",
        ),
        pytest.param(
            RichReprAngular(),
            [
                Color.FORE_CYAN,
                "<",
                Color.FORE_BLACK,
                "RichReprAngular",
                Color.NONE,
                " \n  ",
                Color.FORE_YELLOW,
                "1",
                Color.NONE,
                "\n  ",
                "x",
                Color.FORE_CYAN,
                "=",
                Color.FORE_YELLOW,
                "2",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                ">",
            ],
            True,
            5,
            id="rich-repr-angular-multiline",
        ),
        pytest.param(
            RichReprAngular(),
            [
                Color.FORE_CYAN,
                "<",
                Color.FORE_BLACK,
                "RichReprAngular",
                Color.NONE,
                " ",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                ">",
            ],
            False,
            0,
            id="rich-repr-angular-more",
        ),
        pytest.param(
            ColorfulObject(),
            [
                Color.FORE_RED | Color.BACK_WHITE,
                "repr",
            ],
            False,
            5,
            id="custom-repr",
        ),
        pytest.param(
            NotSoColorfulObject(),
            [
                Color.NONE,
                "bar",
            ],
            False,
            5,
            id="custom-impl-return-str",
        ),
        pytest.param(
            ColorfulObjectBroken(),
            [
                Color.STYLE_INVERSE | Color.FORE_RED,
                "TypeError: __colorized_repr__ returned non-colorized-string (type int)",
            ],
            False,
            5,
            id="custom-impl-return-non-str",
        ),
        pytest.param(
            ColorfulObjectTheme(),
            [
                Color.FORE_RED | Color.BACK_WHITE,
                "repr",
            ],
            False,
            5,
            id="custom-repr-use-theme",
        ),
        pytest.param(
            [ColorfulObject()],
            [
                Color.FORE_CYAN,
                "[",
                Color.FORE_RED | Color.BACK_WHITE,
                "repr",
                Color.FORE_CYAN,
                "]",
            ],
            False,
            5,
            id="custom-repr-in-container",
        ),
        pytest.param(
            [ColorfulObject()],
            [
                Color.FORE_CYAN,
                "[",
                Color.NONE,
                "\n  ",
                Color.FORE_RED | Color.BACK_WHITE,
                "repr",
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                "]",
            ],
            True,
            5,
            id="custom-repr-in-container-multiline",
        ),
        pytest.param(
            [Str([Str([Str([Str([10])])])])],
            [
                Color.FORE_CYAN,
                "[[",
                Color.FORE_WHITE,
                "...",
                Color.FORE_CYAN,
                "]]",
            ],
            False,
            1,
            id="str-does-not-reset-depth",
        ),
    ],
)
def test_colorized_repr(value, expected, multiline, highlighted, max_depth, ctx):
    if not highlighted:
        expected = _s(
            (
                part
                if isinstance(part, str) or part.back is not None or part.inverse
                else Color.NONE
            )
            for part in expected
        )._parts

    assert _join_consecutive_strings(
        ctx.repr(
            value,
            multiline=multiline,
            highlighted=highlighted,
            max_depth=max_depth,
        )._parts
    ) == _join_consecutive_strings(expected)


@yuio.string.repr_from_rich
class RFREmpty:
    def __rich_repr__(self):
        return []


@yuio.string.repr_from_rich  # type: ignore
class RFRNone:
    def __rich_repr__(self):
        pass


@yuio.string.repr_from_rich  # type: ignore
class RFRNoMethod:
    pass


@yuio.string.repr_from_rich
class RFRSimple:
    def __rich_repr__(self):
        yield "arg_0"
        yield None, "arg_1"
        yield "key", "value"
        yield "key_2", "value_2", "xxx"
        yield "key_3", "value_3", "value_3"
        yield 1, 2, 3, 4
        yield ()
        yield (10,)


@yuio.string.repr_from_rich
class RFRAngular:
    def __rich_repr__(self):
        yield "arg_0"
        yield None, "arg_1"
        yield "key", "value"
        yield "key_2", "value_2", "xxx"
        yield "key_3", "value_3", "value_3"
        yield 1, 2, 3, 4
        yield ()
        yield (10,)

    __rich_repr__.angular = True  # type: ignore


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (RFREmpty(), "RFREmpty()"),
        (RFRNone(), "RFRNone()"),
        (RFRNoMethod(), "RFRNoMethod()"),
        (
            RFRSimple(),
            "RFRSimple('arg_0', 'arg_1', key='value', key_2='value_2', (1, 2, 3, 4), (), 10)",
        ),
        (
            RFRAngular(),
            "<RFRAngular 'arg_0' 'arg_1' key='value' key_2='value_2' (1, 2, 3, 4) () 10>",
        ),
    ],
)
def test_repr_from_rich(value, expected):
    assert repr(value) == expected


def _join_consecutive_strings(l):
    r = []
    for x in l:
        if isinstance(x, str) and r and isinstance(r[-1], str):
            r[-1] += x
        else:
            r.append(x)
    return r


class TestFormat:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (("",), []),
            (("%s",), [Color.NONE, "%s"]),
            (("%s", 10), [Color.NONE, "10"]),
            (("%s %r", 10, "asd"), [Color.NONE, "10 'asd'"]),
            (("%s", _s(Color.FORE_BLUE, "qux")), [Color.FORE_BLUE, "qux"]),
        ],
    )
    def test_format(self, args, expected, ctx):
        r = yuio.string.Format(*args)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(p for p in expected if isinstance(p, str))
        assert repr(r) == f"Format({', '.join(map(repr, args))})"


class TestRepr:
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            (None, {}, [Color.NONE, "None"]),
            ("asd", {}, [Color.NONE, "'asd'"]),
            ([1, 2, "x\ny"], {}, [Color.NONE, "[1, 2, 'x\\ny']"]),
            (
                [1, 2, "x\ny"],
                {"multiline": True},
                [Color.NONE, "[\n  1,\n  2,\n  'x\\ny'\n]"],
            ),
            (
                [1, 2, "x\ny"],
                {"highlighted": True},
                [
                    Color.FORE_CYAN,
                    "[",
                    Color.FORE_YELLOW,
                    "1",
                    Color.FORE_CYAN,
                    ", ",
                    Color.FORE_YELLOW,
                    "2",
                    Color.FORE_CYAN,
                    ", ",
                    Color.FORE_GREEN,
                    "'x",
                    Color.FORE_BLUE,
                    "\\n",
                    Color.FORE_GREEN,
                    "y'",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
            (
                [1, 2, "x\ny"],
                {"highlighted": True, "multiline": True},
                [
                    Color.FORE_CYAN,
                    "[",
                    Color.NONE,
                    "\n  ",
                    Color.FORE_YELLOW,
                    "1",
                    Color.FORE_CYAN,
                    ",",
                    Color.NONE,
                    "\n  ",
                    Color.FORE_YELLOW,
                    "2",
                    Color.FORE_CYAN,
                    ",",
                    Color.NONE,
                    "\n  ",
                    Color.FORE_GREEN,
                    "'x",
                    Color.FORE_BLUE,
                    "\\n",
                    Color.FORE_GREEN,
                    "y'",
                    Color.NONE,
                    "\n",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
        ],
    )
    def test_repr(self, value, kwargs, expected, ctx):
        r = yuio.string.Repr(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert [str(r)] == _join_consecutive_strings(
            part for part in expected if isinstance(part, str)
        )

    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            (
                [1, 2, "x\ny"],
                {"highlighted": False},
                [Color.NONE, "[\n  1,\n  2,\n  'x\\ny'\n]"],
            ),
            (
                [1, 2, "x\ny"],
                {"multiline": False},
                [
                    Color.FORE_CYAN,
                    "[",
                    Color.FORE_YELLOW,
                    "1",
                    Color.FORE_CYAN,
                    ", ",
                    Color.FORE_YELLOW,
                    "2",
                    Color.FORE_CYAN,
                    ", ",
                    Color.FORE_GREEN,
                    "'x",
                    Color.FORE_BLUE,
                    "\\n",
                    Color.FORE_GREEN,
                    "y'",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
            (
                [1, 2, "x\ny"],
                {},
                [
                    Color.FORE_CYAN,
                    "[",
                    Color.NONE,
                    "\n  ",
                    Color.FORE_YELLOW,
                    "1",
                    Color.FORE_CYAN,
                    ",",
                    Color.NONE,
                    "\n  ",
                    Color.FORE_YELLOW,
                    "2",
                    Color.FORE_CYAN,
                    ",",
                    Color.NONE,
                    "\n  ",
                    Color.FORE_GREEN,
                    "'x",
                    Color.FORE_BLUE,
                    "\\n",
                    Color.FORE_GREEN,
                    "y'",
                    Color.NONE,
                    "\n",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
        ],
    )
    def test_repr_hl(self, value, kwargs, expected, ctx):
        r = yuio.string.Repr(value, **kwargs)
        assert _join_consecutive_strings(
            ctx.str(r, multiline=True, highlighted=True)
        ) == _join_consecutive_strings(expected)


class TestTypeRepr:
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            (None, {}, [Color.NONE, "None"]),
            (list, {}, [Color.NONE, "list"]),
            (list[int], {}, [Color.NONE, "list[int]"]),
            ("explanation", {}, [Color.NONE, "explanation"]),
            (
                list[TestRepr],
                {"highlighted": True},
                [
                    Color.FORE_BLACK,
                    "list",
                    Color.FORE_CYAN,
                    "[",
                    Color.NONE,
                    "test.test_string.",
                    Color.FORE_BLACK,
                    "TestRepr",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
            (
                _t.Annotated[list[str], "description"],
                {"highlighted": True},
                [
                    Color.NONE,
                    "typing.",
                    Color.FORE_BLACK,
                    "Annotated",
                    Color.FORE_CYAN,
                    "[",
                    Color.FORE_BLACK,
                    "list",
                    Color.FORE_CYAN,
                    "[",
                    Color.FORE_BLACK,
                    "str",
                    Color.FORE_CYAN,
                    "],",
                    Color.NONE,
                    " ",
                    Color.FORE_GREEN,
                    "'description'",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
        ],
    )
    def test_repr(self, value, kwargs, expected, ctx):
        r = yuio.string.TypeRepr(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert [str(r)] == _join_consecutive_strings(
            part for part in expected if isinstance(part, str)
        )

    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            (list[int], {"highlighted": False}, [Color.NONE, "list[int]"]),
            ("explanation", {}, [Color.NONE, "explanation"]),
            (
                list[TestRepr],
                {},
                [
                    Color.FORE_BLACK,
                    "list",
                    Color.FORE_CYAN,
                    "[",
                    Color.NONE,
                    "test.test_string.",
                    Color.FORE_BLACK,
                    "TestRepr",
                    Color.FORE_CYAN,
                    "]",
                ],
            ),
        ],
    )
    def test_repr_hl(self, value, kwargs, expected, ctx):
        r = yuio.string.TypeRepr(value, **kwargs)
        assert _join_consecutive_strings(
            ctx.str(r, highlighted=True)
        ) == _join_consecutive_strings(expected)
        assert [str(r)] == _join_consecutive_strings(
            part for part in expected if isinstance(part, str)
        )


class TestJoinStr:
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            ((), {}, []),
            (
                ("foo", "bar"),
                {},
                [
                    Color.FORE_MAGENTA,
                    "foo",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "bar",
                ],
            ),
            (
                ("foo", _s(Color.FORE_RED, "bar"), "baz"),
                {},
                [
                    Color.FORE_MAGENTA,
                    "foo",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA | Color.FORE_RED,
                    "bar",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "baz",
                ],
            ),
            (
                ("foo", "bar", "baz"),
                {},
                [
                    Color.FORE_MAGENTA,
                    "foo",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "bar",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "baz",
                ],
            ),
            (
                ("foo", "bar", "baz"),
                {"color": None},
                [Color.NONE, "foo, bar, baz"],
            ),
            (
                ("foo", "bar", "baz"),
                {"color": Color.FORE_RED},
                [
                    Color.FORE_RED,
                    "foo",
                    Color.NONE,
                    ", ",
                    Color.FORE_RED,
                    "bar",
                    Color.NONE,
                    ", ",
                    Color.FORE_RED,
                    "baz",
                ],
            ),
            (
                ("foo", "bar"),
                {"sep": "; ", "sep_last": "; and ", "sep_two": " and "},
                [
                    Color.FORE_MAGENTA,
                    "foo",
                    Color.NONE,
                    " and ",
                    Color.FORE_MAGENTA,
                    "bar",
                ],
            ),
            (
                ("foo", "bar", "baz"),
                {"sep": "; ", "sep_last": "; and ", "sep_two": " and "},
                [
                    Color.FORE_MAGENTA,
                    "foo",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "bar",
                    Color.NONE,
                    "; and ",
                    Color.FORE_MAGENTA,
                    "baz",
                ],
            ),
            (
                ("foo", "bar", "baz", "qux", "duo"),
                {"sep": "; ", "sep_last": "; and ", "sep_two": " and "},
                [
                    Color.FORE_MAGENTA,
                    "foo",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "bar",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "baz",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "qux",
                    Color.NONE,
                    "; and ",
                    Color.FORE_MAGENTA,
                    "duo",
                ],
            ),
        ],
    )
    def test_join(self, value, kwargs, expected, ctx):
        r = yuio.string.JoinStr(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))

    def test_and(self, ctx):
        r = yuio.string.And("", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == []

        r = yuio.string.And("12", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "1 and 2",
        ]

        r = yuio.string.And("123", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "1, 2, and 3",
        ]

    def test_or(self, ctx):
        r = yuio.string.Or("", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == []

        r = yuio.string.Or("12", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "1 or 2",
        ]

        r = yuio.string.Or("123", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "1, 2, or 3",
        ]


class TestJoinRepr:
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            ((), {}, []),
            (
                ("foo", "bar"),
                {},
                [
                    Color.FORE_MAGENTA,
                    "'foo'",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "'bar'",
                ],
            ),
            (
                ("foo", "bar", "baz"),
                {},
                [
                    Color.FORE_MAGENTA,
                    "'foo'",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "'bar'",
                    Color.NONE,
                    ", ",
                    Color.FORE_MAGENTA,
                    "'baz'",
                ],
            ),
            (
                ("foo", "bar", "baz"),
                {"color": None},
                [Color.NONE, "'foo', 'bar', 'baz'"],
            ),
            (
                ("foo", "bar", "baz"),
                {"color": Color.FORE_RED},
                [
                    Color.FORE_RED,
                    "'foo'",
                    Color.NONE,
                    ", ",
                    Color.FORE_RED,
                    "'bar'",
                    Color.NONE,
                    ", ",
                    Color.FORE_RED,
                    "'baz'",
                ],
            ),
            (
                ("foo", "bar"),
                {"sep": "; ", "sep_last": "; and ", "sep_two": " and "},
                [
                    Color.FORE_MAGENTA,
                    "'foo'",
                    Color.NONE,
                    " and ",
                    Color.FORE_MAGENTA,
                    "'bar'",
                ],
            ),
            (
                ("foo", "bar", "baz"),
                {"sep": "; ", "sep_last": "; and ", "sep_two": " and "},
                [
                    Color.FORE_MAGENTA,
                    "'foo'",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "'bar'",
                    Color.NONE,
                    "; and ",
                    Color.FORE_MAGENTA,
                    "'baz'",
                ],
            ),
            (
                ("foo", "bar", "baz", "qux", "duo"),
                {"sep": "; ", "sep_last": "; and ", "sep_two": " and "},
                [
                    Color.FORE_MAGENTA,
                    "'foo'",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "'bar'",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "'baz'",
                    Color.NONE,
                    "; ",
                    Color.FORE_MAGENTA,
                    "'qux'",
                    Color.NONE,
                    "; and ",
                    Color.FORE_MAGENTA,
                    "'duo'",
                ],
            ),
        ],
    )
    def test_join(self, value, kwargs, expected, ctx):
        r = yuio.string.JoinRepr(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))

    def test_and(self, ctx):
        r = yuio.string.JoinRepr.and_("", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == []

        r = yuio.string.JoinRepr.and_("12", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "'1' and '2'",
        ]

        r = yuio.string.JoinRepr.and_("123", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "'1', '2', and '3'",
        ]

    def test_or(self, ctx):
        r = yuio.string.JoinRepr.or_("", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == []

        r = yuio.string.JoinRepr.or_("12", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "'1' or '2'",
        ]

        r = yuio.string.JoinRepr.or_("123", color=None)
        assert _join_consecutive_strings(ctx.str(r)) == [
            Color.NONE,
            "'1', '2', or '3'",
        ]


class TestStack:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ((), []),
            (("a"), [Color.NONE, "a"]),
            (("a", "b"), [Color.NONE, "a\nb"]),
            (
                (_s(Color.FORE_RED, "a"), "x", _s(Color.FORE_GREEN, "b")),
                [
                    Color.FORE_RED,
                    "a",
                    Color.NONE,
                    "\n",
                    "x",
                    "\n",
                    Color.FORE_GREEN,
                    "b",
                ],
            ),
        ],
    )
    def test_join(self, args, expected, ctx):
        r = yuio.string.Stack(*args)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))


class TestIndent:
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            ("", {}, []),
            (
                "foo\nbar",
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "  ",
                    NO_WRAP_END,
                    "foo\n",
                    NO_WRAP_START,
                    "  ",
                    NO_WRAP_END,
                    "bar",
                ],
            ),
            (
                "foo\nbar\n",
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "  ",
                    NO_WRAP_END,
                    "foo\n",
                    NO_WRAP_START,
                    "  ",
                    NO_WRAP_END,
                    "bar\n",
                ],
            ),
            (
                "foo\nbar\nbaz",
                {"indent": 4, "continuation_indent": 2},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "    ",
                    NO_WRAP_END,
                    "foo\n",
                    NO_WRAP_START,
                    "  ",
                    NO_WRAP_END,
                    "bar\n",
                    NO_WRAP_START,
                    "  ",
                    NO_WRAP_END,
                    "baz",
                ],
            ),
            (
                "foo\nbar\nbaz",
                {"indent": "> ", "continuation_indent": "| "},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "> ",
                    NO_WRAP_END,
                    "foo\n",
                    NO_WRAP_START,
                    "| ",
                    NO_WRAP_END,
                    "bar\n",
                    NO_WRAP_START,
                    "| ",
                    NO_WRAP_END,
                    "baz",
                ],
            ),
            (
                _s("abc\n", Color.FORE_YELLOW, "def\nghi"),
                {
                    "indent": _s(Color.FORE_RED, "1"),
                    "continuation_indent": _s(Color.FORE_BLUE, "2"),
                },
                [
                    NO_WRAP_START,
                    Color.FORE_RED,
                    "1",
                    NO_WRAP_END,
                    Color.NONE,
                    "abc\n",
                    NO_WRAP_START,
                    Color.FORE_BLUE,
                    "2",
                    NO_WRAP_END,
                    Color.FORE_YELLOW,
                    "def\n",
                    NO_WRAP_START,
                    Color.FORE_BLUE,
                    "2",
                    NO_WRAP_END,
                    Color.FORE_YELLOW,
                    "ghi",
                ],
            ),
            (
                yuio.string.Wrap(
                    "Some paragraph that will be wrapped at 20 characters"
                ),
                {"indent": ">>> "},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    ">>> Some paragraph\n>>> that will be\n>>> wrapped at 20\n>>> characters",
                    NO_WRAP_END,
                ],
            ),
            (
                yuio.string.Wrap(
                    "Some paragraph that will be wrapped at 20 characters"
                ),
                {"indent": ">>> ", "continuation_indent": "  "},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    ">>> Some paragraph\n  that will be\n  wrapped at 20\n  characters",
                    NO_WRAP_END,
                ],
            ),
        ],
    )
    def test_indent(self, value, kwargs, expected, ctx):
        r = yuio.string.Indent(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))


class TestMd:
    @pytest.mark.parametrize(
        ("args", "kwargs", "expected"),
        [
            (("",), {}, []),
            (
                ("Hello, world!",),
                {},
                [NO_WRAP_START, Color.NONE, "Hello, world!", NO_WRAP_END],
            ),
            (
                ("# Hello, world!",),
                {},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "⣿ ",
                    Color.STYLE_BOLD,
                    "Hello, world!",
                    Color.NONE,
                    "\n",
                    NO_WRAP_END,
                ],
            ),
            (
                ("# Hello, world!",),
                {"allow_headings": False},
                [NO_WRAP_START, Color.NONE, "Hello, world!", NO_WRAP_END],
            ),
            (
                ("Some paragraph that will be wrapped at 20 characters",),
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Some paragraph that\nwill be wrapped at\n20 characters",
                    NO_WRAP_END,
                ],
            ),
            (
                ("Some paragraph that will be wrapped at 10 characters",),
                {"width": 10},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Some\nparagraph\nthat will\nbe wrapped\nat 10\ncharacters",
                    NO_WRAP_END,
                ],
            ),
            (
                ("    Code",),
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Code",
                    NO_WRAP_END,
                ],
            ),
            (
                ("    Code",),
                {"dedent": False},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "    ",
                    Color.NONE,
                    "Code",
                    NO_WRAP_END,
                ],
            ),
        ],
    )
    def test_md(self, args, kwargs, expected, ctx):
        r = yuio.string.Md(*args, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))


class TestRst:
    @pytest.mark.parametrize(
        ("args", "kwargs", "expected"),
        [
            (("",), {}, []),
            (
                ("Hello, world!",),
                {},
                [NO_WRAP_START, Color.NONE, "Hello, world!", NO_WRAP_END],
            ),
            (
                ("Hello, world!\n--------------",),
                {},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "⣿ ",
                    Color.STYLE_BOLD,
                    "Hello, world!",
                    Color.NONE,
                    "\n",
                    NO_WRAP_END,
                ],
            ),
            (
                ("Hello, world!\n--------------",),
                {"allow_headings": False},
                [NO_WRAP_START, Color.NONE, "Hello, world!", NO_WRAP_END],
            ),
            (
                ("Some paragraph that will be wrapped at 20 characters",),
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Some paragraph that\nwill be wrapped at\n20 characters",
                    NO_WRAP_END,
                ],
            ),
            (
                ("Some paragraph that will be wrapped at 10 characters",),
                {"width": 10},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Some\nparagraph\nthat will\nbe wrapped\nat 10\ncharacters",
                    NO_WRAP_END,
                ],
            ),
            (
                ("    Code",),
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Code",
                    NO_WRAP_END,
                ],
            ),
            (
                ("    Quote",),
                {"dedent": False},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    ">   ",
                    Color.NONE,
                    "Quote",
                    NO_WRAP_END,
                ],
            ),
        ],
    )
    def test_rst(self, args, kwargs, expected, ctx):
        r = yuio.string.Rst(*args, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))


class TestHl:
    @pytest.mark.parametrize(
        ("args", "kwargs", "expected"),
        [
            (("",), {}, []),
            (
                ('{"foo": "bar"}',),
                {},
                [yuio.string.NO_WRAP_START, Color.NONE, '{"foo": "bar"}', NO_WRAP_END],
            ),
            (
                ('{"foo": "%s"}', "bar"),
                {},
                [yuio.string.NO_WRAP_START, Color.NONE, '{"foo": "bar"}', NO_WRAP_END],
            ),
            (
                ('  {"foo": "bar"}',),
                {},
                [yuio.string.NO_WRAP_START, Color.NONE, '{"foo": "bar"}', NO_WRAP_END],
            ),
            (
                ('  {"foo": "bar"}',),
                {"dedent": True},
                [yuio.string.NO_WRAP_START, Color.NONE, '{"foo": "bar"}', NO_WRAP_END],
            ),
        ],
    )
    def test_hl(self, args, kwargs, expected, ctx):
        r = yuio.string.Hl(*args, syntax="json", **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))


class TestWrap:
    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            ("", {}, []),
            (
                _s("foo", Color.FORE_RED, "bar"),
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foo",
                    Color.FORE_RED,
                    "bar",
                    NO_WRAP_END,
                ],
            ),
            (
                "Some paragraph that will be wrapped at 20 characters",
                {},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Some paragraph that\nwill be wrapped at\n20 characters",
                    NO_WRAP_END,
                ],
            ),
            (
                "Some paragraph that will be wrapped at 10 characters",
                {"width": 10},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "Some\nparagraph\nthat will\nbe wrapped\nat 10\ncharacters",
                    NO_WRAP_END,
                ],
            ),
            (
                yuio.string.Wrap(
                    "Some paragraph that will be wrapped at 20 characters"
                ),
                {"indent": ">>> "},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    ">>> Some paragraph\n>>> that will be\n>>> wrapped at 20\n>>> characters",
                    NO_WRAP_END,
                ],
            ),
            (
                yuio.string.Wrap(
                    "Some paragraph that will be wrapped at 20 characters"
                ),
                {"indent": ">>> ", "continuation_indent": "  "},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    ">>> Some paragraph\n  that will be\n  wrapped at 20\n  characters",
                    NO_WRAP_END,
                ],
            ),
            (
                "Foo\nBar",
                {"indent": 3, "continuation_indent": 4},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "   Foo\n    Bar",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo_bar_baz_qux_duo",
                {"overflow": True, "break_long_words": False, "width": 10},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foo_bar_b…",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo_bar_baz_qux_duo",
                {"overflow": "!", "break_long_words": False, "width": 10},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foo_bar_b!",
                    NO_WRAP_END,
                ],
            ),
        ],
    )
    def test_wrap(self, value, kwargs, expected, ctx):
        r = yuio.string.Wrap(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))


class TestWithBaseColor:
    @pytest.mark.parametrize(
        ("value", "color", "expected"),
        [
            ("", None, []),
            ("", Color.FORE_RED, []),
            ("foo", None, [Color.NONE, "foo"]),
            ("foo", Color.FORE_RED, [Color.FORE_RED, "foo"]),
            ("foo", "code", [Color.FORE_MAGENTA, "foo"]),
            (
                _s(Color.STYLE_BOLD, "bold", Color.FORE_RED, "red"),
                None,
                [Color.STYLE_BOLD, "bold", Color.FORE_RED, "red"],
            ),
            (
                _s(Color.STYLE_BOLD, "bold", Color.FORE_RED, "red"),
                Color.FORE_RED,
                [Color.FORE_RED | Color.STYLE_BOLD, "bold", Color.FORE_RED, "red"],
            ),
            (
                _s(Color.STYLE_BOLD, "bold", Color.FORE_RED, "red"),
                "code",
                [Color.FORE_MAGENTA | Color.STYLE_BOLD, "bold", Color.FORE_RED, "red"],
            ),
        ],
    )
    def test_with_base_color(self, value, color, expected, ctx):
        r = yuio.string.WithBaseColor(value, base_color=color)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))

    class TestLink:
        @pytest.mark.parametrize(
            ("value", "url", "expected"),
            [
                ("", "https://a.com", []),
                (
                    "foo",
                    "https://a.com",
                    [LinkMarker("https://a.com"), Color.NONE, "foo"],
                ),
                (
                    _s(Color.FORE_RED, "red"),
                    "https://a.com",
                    [LinkMarker("https://a.com"), Color.FORE_RED, "red"],
                ),
            ],
        )
        def test_link(self, value, url, expected, ctx):
            r = yuio.string.Link(value, url=url)
            assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
                expected
            )
            assert str(r) == "".join(part for part in expected if isinstance(part, str))

        def test_link_no_colors(self, ostream, istream):
            ctx = ReprContext(
                term=yuio.term.Term(ostream, istream), theme=yuio.theme.Theme()
            )
            r = yuio.string.Link("foo", url="https://a.com")
            # When colors/links are not supported, Link appends the URL in brackets.
            expected = [
                LinkMarker("https://a.com"),
                Color.NONE,
                "foo",
                NO_WRAP_START,
                " [https://a.com]",
                NO_WRAP_END,
            ]
            assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
                expected
            )


class TestHr:
    _HR_KWARGS_1 = {
        "left_start": "<",
        "left_middle": "-",
        "left_end": ">",
        "middle": "~",
        "right_start": "[",
        "right_middle": "=",
        "right_end": "]",
    }
    _HR_KWARGS_2 = {
        "left_start": "<<",
        "left_middle": "@#",
        "left_end": ">>",
        "middle": "~^",
        "right_start": "[[",
        "right_middle": "=-",
        "right_end": "]]",
    }

    @pytest.mark.parametrize(
        ("value", "kwargs", "expected"),
        [
            (
                "",
                {},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "────────────────────",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "───────╴",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "╶────────",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo\nbar",
                {},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "───────╴",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "╶────────",
                    Color.NONE,
                    "\n",
                    Color.FORE_MAGENTA,
                    "───────╴",
                    Color.NONE,
                    "bar",
                    Color.FORE_MAGENTA,
                    "╶────────",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {"weight": 0},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "        ",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "         ",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {"weight": 2},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "━━━━━━━╸",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "╺━━━━━━━━",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {"width": 3},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foo",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {"width": 5},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "╴",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "╶",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {"width": 7},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "─╴",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "╶─",
                    NO_WRAP_END,
                ],
            ),
            (
                "foobar",
                {"width": 7},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foobar",
                    Color.FORE_MAGENTA,
                    "╶",
                    NO_WRAP_END,
                ],
            ),
            (
                "foobarbaz",
                {"width": 7},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foobar…",
                    NO_WRAP_END,
                ],
            ),
            (
                "foobarbaz",
                {"width": 7, "overflow": ""},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foobarb",
                    NO_WRAP_END,
                ],
            ),
            (
                "foobarbaz",
                {"width": 7, "overflow": False},
                [
                    NO_WRAP_START,
                    Color.NONE,
                    "foobarbaz",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                _HR_KWARGS_1,
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<~~~~~~~~~~~~~~~~~~]",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                _HR_KWARGS_1,
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<------>",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "[=======]",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                _HR_KWARGS_2,
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<~^~^~^~^~^~^~^~^]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                {**_HR_KWARGS_2, "width": 19},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<~^~^~^~^~^~^~^]] ",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                {**_HR_KWARGS_2, "width": 18},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<~^~^~^~^~^~^~^]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                {**_HR_KWARGS_2, "width": 5},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<]] ",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                {**_HR_KWARGS_2, "width": 4},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                {**_HR_KWARGS_2, "width": 3},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<< ",
                    NO_WRAP_END,
                ],
            ),
            (
                "",
                {**_HR_KWARGS_2, "width": 1},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    " ",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                _HR_KWARGS_2,
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<@#@#>>",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    " [[=-=-]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {**_HR_KWARGS_2, "width": 19},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<@#@#>>",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "[[=-=-]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {**_HR_KWARGS_2, "width": 15},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<@#>>",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "[[=-]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {**_HR_KWARGS_2, "width": 11},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    "<<>>",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "[[]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {**_HR_KWARGS_2, "width": 10},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    ">> ",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    "[[]]",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {**_HR_KWARGS_2, "width": 9},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    ">> ",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    " [[",
                    NO_WRAP_END,
                ],
            ),
            (
                "foo",
                {**_HR_KWARGS_2, "width": 5},
                [
                    NO_WRAP_START,
                    Color.FORE_MAGENTA,
                    " ",
                    Color.NONE,
                    "foo",
                    Color.FORE_MAGENTA,
                    " ",
                    NO_WRAP_END,
                ],
            ),
        ],
    )
    def test_hr(self, value, kwargs, expected, ctx):
        r = yuio.string.Hr(value, **kwargs)
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            expected
        )
        assert str(r) == "".join(part for part in expected if isinstance(part, str))

    def test_hr_no_args(self, ctx):
        r = yuio.string.Hr()
        assert _join_consecutive_strings(ctx.str(r)) == _join_consecutive_strings(
            [NO_WRAP_START, Color.FORE_MAGENTA, "────────────────────", NO_WRAP_END]
        )
        assert str(r) == "────────────────────"
