import pytest

import yuio.string
from yuio.color import Color
from yuio.string import NO_WRAP_END, NO_WRAP_START


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


def _join_consecutive_strings(l):
    r = []
    for x in l:
        if isinstance(x, str) and r and isinstance(r[-1], str):
            r[-1] += x
        else:
            r.append(x)
    return r


@pytest.mark.parametrize(
    ("text", "kwargs", "expect"),
    [
        pytest.param(
            t"foo bar",
            {},
            [Color.NONE, "foo bar"],
            id="simple",
        ),
        pytest.param(
            t"foo {'interpolation'} bar",
            {},
            [Color.NONE, "foo ", "interpolation", " bar"],
            id="interpolation",
        ),
        pytest.param(
            t"foo {'абв'!s} bar",
            {},
            [Color.NONE, "foo ", "абв", " bar"],
            id="str",
        ),
        pytest.param(
            t"foo {'абв'!r} bar",
            {},
            [Color.NONE, "foo ", "'абв'", " bar"],
            id="repr",
        ),
        pytest.param(
            t"foo {'абв'!a} bar",
            {},
            [
                Color.NONE,
                "foo ",
                "'\\u0430\\u0431\\u0432'",
                " bar",
            ],
            id="ascii",
        ),
        pytest.param(
            t"foo {(1, 2)!r:#} bar",
            {},
            [
                Color.NONE,
                "foo ",
                Color.FORE_CYAN,
                "(",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ")",
                Color.NONE,
                " bar",
            ],
            id="colorized_repr",
        ),
        pytest.param(
            t"foo {(1, 2):#} bar",
            {},
            [
                Color.NONE,
                "foo ",
                Color.FORE_CYAN,
                "(",
                Color.FORE_YELLOW,
                "1",
                Color.FORE_CYAN,
                ", ",
                Color.FORE_YELLOW,
                "2",
                Color.FORE_CYAN,
                ")",
                Color.NONE,
                " bar",
            ],
            id="colorized_repr_fallback",
        ),
        pytest.param(
            t"foo {(1, 2)!r:+} bar",
            {},
            [
                Color.NONE,
                "foo ",
                "(\n  1,\n  2\n)",
                " bar",
            ],
            id="multiline_repr",
        ),
        pytest.param(
            t"foo {(1, 2)!r:#+} bar",
            {},
            [
                Color.NONE,
                "foo ",
                Color.FORE_CYAN,
                "(",
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
                Color.NONE,
                "\n",
                Color.FORE_CYAN,
                ")",
                Color.NONE,
                " bar",
            ],
            id="colorized_multiline_repr",
        ),
        pytest.param(
            t"foo {10:+05} bar",
            {},
            [
                Color.NONE,
                "foo ",
                "+0010",
                " bar",
            ],
            id="overridden_format",
        ),
        pytest.param(
            t"<c bold magenta>foo {(1, 2)!r:#}</c> bar",
            {},
            [
                Color.FORE_MAGENTA | Color.STYLE_BOLD,
                "foo ",
                Color.FORE_CYAN | Color.STYLE_BOLD,
                "(",
                Color.FORE_YELLOW | Color.STYLE_BOLD,
                "1",
                Color.FORE_CYAN | Color.STYLE_BOLD,
                ", ",
                Color.FORE_YELLOW | Color.STYLE_BOLD,
                "2",
                Color.FORE_CYAN | Color.STYLE_BOLD,
                ")",
                Color.NONE,
                " bar",
            ],
            id="colorized_repr_with_background",
        ),
        pytest.param(
            t"foo {'param':10} bar",
            {},
            [Color.NONE, "foo ", "param     ", " bar"],
            id="width",
        ),
        pytest.param(
            t"foo {'param':~<10} bar",
            {},
            [Color.NONE, "foo ", "param~~~~~", " bar"],
            id="fill",
        ),
        pytest.param(
            t"foo {'param':<10} bar",
            {},
            [Color.NONE, "foo ", "param     ", " bar"],
            id="flush_left",
        ),
        pytest.param(
            t"foo {'param':>10} bar",
            {},
            [Color.NONE, "foo ", "     param", " bar"],
            id="flush_right",
        ),
        pytest.param(
            t"foo {'param':^10} bar",
            {},
            [Color.NONE, "foo ", "  param   ", " bar"],
            id="center",
        ),
        pytest.param(
            t"foo {'param':✨<10} bar",
            {},
            [
                Color.NONE,
                "foo ",
                "param✨✨ ",
                " bar",
            ],
            id="flush_left_wide",
        ),
        pytest.param(
            t"foo {'param':✨>10} bar",
            {},
            [
                Color.NONE,
                "foo ",
                "✨✨ param",
                " bar",
            ],
            id="flush_right_wide",
        ),
        pytest.param(
            t"foo {'param':✨^10} bar",
            {},
            [
                Color.NONE,
                "foo ",
                "✨param✨ ",
                " bar",
            ],
            id="center_wide",
        ),
        pytest.param(
            t"foo `{10}` bar",
            {},
            [
                Color.NONE,
                "foo ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "10",
                NO_WRAP_END,
                Color.NONE,
                " bar",
            ],
            id="code",
        ),
        pytest.param(
            t"foo `...{10}...` bar",
            {},
            [
                Color.NONE,
                "foo ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "...10...",
                NO_WRAP_END,
                Color.NONE,
                " bar",
            ],
            id="code_with_symbols",
        ),
        pytest.param(
            t"`{10}` bar",
            {},
            [NO_WRAP_START, Color.FORE_MAGENTA, "10", NO_WRAP_END, Color.NONE, " bar"],
            id="code_start",
        ),
        pytest.param(
            t"foo `{10}`",
            {},
            [Color.NONE, "foo ", NO_WRAP_START, Color.FORE_MAGENTA, "10", NO_WRAP_END],
            id="code_end",
        ),
        pytest.param(
            t"foo `{10} {11}` bar",
            {},
            [
                Color.NONE,
                "foo ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "10 11",
                NO_WRAP_END,
                Color.NONE,
                " bar",
            ],
            id="code_multiple_interpolations",
        ),
        pytest.param(
            t"foo ` {10} ` bar",
            {},
            [
                Color.NONE,
                "foo ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "10",
                NO_WRAP_END,
                Color.NONE,
                " bar",
            ],
            id="code_trim_spaces",
        ),
        pytest.param(
            t"foo `  {10}  ` bar",
            {},
            [
                Color.NONE,
                "foo ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                " 10 ",
                NO_WRAP_END,
                Color.NONE,
                " bar",
            ],
            id="code_trim_spaces_2",
        ),
        pytest.param(
            t"foo ```{10}``` bar",
            {},
            [
                Color.NONE,
                "foo ",
                NO_WRAP_START,
                Color.FORE_MAGENTA,
                "10",
                NO_WRAP_END,
                Color.NONE,
                " bar",
            ],
            id="code_long_fence",
        ),
    ],
)
def test_colorize(text, kwargs, expect, ctx):
    formatted = yuio.string.colorize(text, ctx=ctx, **kwargs)
    assert _join_consecutive_strings(formatted._parts) == _join_consecutive_strings(
        expect
    )
