import pytest

import yuio.color


@pytest.mark.parametrize(
    ("color", "expect"),
    [
        (yuio.color.Color.NONE | yuio.color.Color.NONE, yuio.color.Color.NONE),
        (yuio.color.Color.NONE | yuio.color.Color.FORE_RED, yuio.color.Color.FORE_RED),
        (yuio.color.Color.NONE | yuio.color.Color.BACK_RED, yuio.color.Color.BACK_RED),
        (
            yuio.color.Color.FORE_BLUE | yuio.color.Color.FORE_RED,
            yuio.color.Color.FORE_RED,
        ),
        (
            yuio.color.Color.BACK_BLUE | yuio.color.Color.BACK_RED,
            yuio.color.Color.BACK_RED,
        ),
        (
            yuio.color.Color.FORE_RED | yuio.color.Color.BACK_BLUE,
            yuio.color.Color(
                fore=yuio.color.ColorValue(1), back=yuio.color.ColorValue(4)
            ),
        ),
        (
            yuio.color.Color.FORE_RED | yuio.color.Color.STYLE_BOLD,
            yuio.color.Color(fore=yuio.color.ColorValue(1), bold=True),
        ),
        (
            yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_RED,
            yuio.color.Color(fore=yuio.color.ColorValue(1), bold=True),
        ),
        (
            yuio.color.Color.FORE_RED | yuio.color.Color.STYLE_DIM,
            yuio.color.Color(fore=yuio.color.ColorValue(1), dim=True),
        ),
        (
            yuio.color.Color.STYLE_DIM | yuio.color.Color.FORE_RED,
            yuio.color.Color(fore=yuio.color.ColorValue(1), dim=True),
        ),
        (
            yuio.color.Color.FORE_RED
            | yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.STYLE_DIM,
            yuio.color.Color(fore=yuio.color.ColorValue(1), bold=True, dim=True),
        ),
        (
            yuio.color.Color.FORE_RED
            | yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.STYLE_NORMAL,
            yuio.color.Color(
                fore=yuio.color.ColorValue(1),
                bold=False,
                dim=False,
                italic=False,
                underline=False,
                inverse=False,
                blink=False,
            ),
        ),
        (
            yuio.color.Color.FORE_RED
            | yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_NORMAL,
            yuio.color.Color(
                fore=yuio.color.ColorValue(1),
                bold=False,
                dim=False,
                italic=False,
                underline=False,
                inverse=False,
                blink=False,
            ),
        ),
        (
            yuio.color.Color.FORE_RED
            | yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_NORMAL
            | yuio.color.Color.STYLE_DIM,
            yuio.color.Color(
                fore=yuio.color.ColorValue(1),
                bold=False,
                dim=True,
                italic=False,
                underline=False,
                inverse=False,
                blink=False,
            ),
        ),
        (
            yuio.color.Color.FORE_RED
            | yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_NORMAL
            | yuio.color.Color.STYLE_BOLD,
            yuio.color.Color(
                fore=yuio.color.ColorValue(1),
                bold=True,
                dim=False,
                italic=False,
                underline=False,
                inverse=False,
                blink=False,
            ),
        ),
    ],
)
def test_combine(color, expect):
    assert color == expect


@pytest.mark.parametrize(
    ("colors", "coeffs", "expect"),
    [
        (
            [yuio.color.Color.FORE_RED, yuio.color.Color.FORE_GREEN],
            [i / 4 for i in range(5)],
            [yuio.color.Color.FORE_RED] * 5,
        ),
        (
            [yuio.color.Color.FORE_RED, yuio.color.Color.fore_from_hex("#AA0000")],
            [i / 4 for i in range(5)],
            [yuio.color.Color.FORE_RED] * 5,
        ),
        (
            [yuio.color.Color.fore_from_hex("#AA0000"), yuio.color.Color.FORE_RED],
            [i / 4 for i in range(5)],
            [yuio.color.Color.fore_from_hex("#AA0000")] * 5,
        ),
        (
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
            ],
            [i / 4 for i in range(5)],
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#AA0000"),
            ],
        ),
        (
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#00AA00"),
            ],
            [i / 4 for i in range(5)],
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#7F2A00"),
                yuio.color.Color.fore_from_hex("#555500"),
                yuio.color.Color.fore_from_hex("#2A7F00"),
                yuio.color.Color.fore_from_hex("#00AA00"),
            ],
        ),
        (
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#00AA00"),
                yuio.color.Color.fore_from_hex("#0000AA"),
            ],
            [i / 8 for i in range(9)],
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#7F2A00"),
                yuio.color.Color.fore_from_hex("#555500"),
                yuio.color.Color.fore_from_hex("#2A7F00"),
                yuio.color.Color.fore_from_hex("#00AA00"),
                yuio.color.Color.fore_from_hex("#007F2A"),
                yuio.color.Color.fore_from_hex("#005555"),
                yuio.color.Color.fore_from_hex("#002A7F"),
                yuio.color.Color.fore_from_hex("#0000AA"),
            ],
        ),
        (
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#00AA00"),
            ],
            [0, 0.5, 1],
            [
                yuio.color.Color.fore_from_hex("#AA0000"),
                yuio.color.Color.fore_from_hex("#555500"),
                yuio.color.Color.fore_from_hex("#00AA00"),
            ],
        ),
        (
            [
                yuio.color.Color.back_from_hex("#0000AA"),
                yuio.color.Color.back_from_hex("#00AA00"),
            ],
            [0, 0.5, 1],
            [
                yuio.color.Color.back_from_hex("#0000AA"),
                yuio.color.Color.back_from_hex("#005555"),
                yuio.color.Color.back_from_hex("#00AA00"),
            ],
        ),
        (
            [
                yuio.color.Color.fore_from_hex("#AA0000")
                | yuio.color.Color.back_from_hex("#0000AA"),
                yuio.color.Color.fore_from_hex("#00AA00")
                | yuio.color.Color.back_from_hex("#00AA00"),
            ],
            [0, 0.5, 1],
            [
                yuio.color.Color.fore_from_hex("#AA0000")
                | yuio.color.Color.back_from_hex("#0000AA"),
                yuio.color.Color.fore_from_hex("#555500")
                | yuio.color.Color.back_from_hex("#005555"),
                yuio.color.Color.fore_from_hex("#00AA00")
                | yuio.color.Color.back_from_hex("#00AA00"),
            ],
        ),
    ],
)
def test_lerp(colors, coeffs, expect):
    lerp = yuio.color.Color.lerp(*colors)
    result = [lerp(c) for c in coeffs]
    assert result == expect


def test_lerp_fail():
    with pytest.raises(ValueError):
        yuio.color.Color.lerp()


@pytest.mark.parametrize(
    ("color", "expect"),
    [
        (
            yuio.color.ColorValue.from_hex("#005555").lighten(0.5),
            yuio.color.ColorValue.from_hex("#00AAAA"),
        ),
        (
            yuio.color.ColorValue.from_hex("#005555").darken(0.5),
            yuio.color.ColorValue.from_hex("#002A2A"),
        ),
        (yuio.color.ColorValue("0").darken(0.5), yuio.color.ColorValue("0")),
        (
            yuio.color.ColorValue.from_hex("#005555").match_luminosity(
                yuio.color.ColorValue.from_hex("#002A2A")
            ),
            yuio.color.ColorValue.from_hex("#002A2A"),
        ),
        (
            yuio.color.ColorValue.from_hex("#005555").match_luminosity(
                yuio.color.ColorValue.from_hex("#AA4700")
            ),
            yuio.color.ColorValue.from_hex("#00AAAA"),
        ),
        (
            yuio.color.ColorValue(0).match_luminosity(
                yuio.color.ColorValue.from_hex("#002A2A")
            ),
            yuio.color.ColorValue(0),
        ),
        (
            yuio.color.ColorValue.from_hex("#005555").match_luminosity(
                yuio.color.ColorValue(0)
            ),
            yuio.color.ColorValue.from_hex("#005555"),
        ),
    ],
)
def test_color_operations(color, expect):
    assert color == expect


@pytest.mark.parametrize(
    ("color", "cap", "expect"),
    [
        (yuio.color.Color.NONE, yuio.color.ColorSupport.NONE, ""),
        (yuio.color.Color.NONE, yuio.color.ColorSupport.ANSI, "\x1b[m"),
        (yuio.color.Color.NONE, yuio.color.ColorSupport.ANSI_256, "\x1b[m"),
        (yuio.color.Color.NONE, yuio.color.ColorSupport.ANSI_TRUE, "\x1b[m"),
        (yuio.color.Color.FORE_RED, yuio.color.ColorSupport.NONE, ""),
        (yuio.color.Color.FORE_RED, yuio.color.ColorSupport.ANSI, "\x1b[;31m"),
        (yuio.color.Color.FORE_RED, yuio.color.ColorSupport.ANSI_256, "\x1b[;31m"),
        (yuio.color.Color.FORE_RED, yuio.color.ColorSupport.ANSI_TRUE, "\x1b[;31m"),
        (yuio.color.Color.BACK_RED, yuio.color.ColorSupport.NONE, ""),
        (yuio.color.Color.BACK_RED, yuio.color.ColorSupport.ANSI, "\x1b[;41m"),
        (yuio.color.Color.BACK_RED, yuio.color.ColorSupport.ANSI_256, "\x1b[;41m"),
        (yuio.color.Color.BACK_RED, yuio.color.ColorSupport.ANSI_TRUE, "\x1b[;41m"),
        (yuio.color.Color.fore_from_hex("#338F15"), yuio.color.ColorSupport.NONE, ""),
        (
            yuio.color.Color.fore_from_hex("#338F15"),
            yuio.color.ColorSupport.ANSI,
            "\x1b[;32m",
        ),
        (
            yuio.color.Color.fore_from_hex("#338F15"),
            yuio.color.ColorSupport.ANSI_256,
            "\x1b[;38;5;64m",
        ),
        (
            yuio.color.Color.fore_from_hex("#338F15"),
            yuio.color.ColorSupport.ANSI_TRUE,
            "\x1b[;38;2;51;143;21m",
        ),
        (yuio.color.Color.back_from_hex("#338F15"), yuio.color.ColorSupport.NONE, ""),
        (
            yuio.color.Color.back_from_hex("#338F15"),
            yuio.color.ColorSupport.ANSI,
            "\x1b[;42m",
        ),
        (
            yuio.color.Color.back_from_hex("#338F15"),
            yuio.color.ColorSupport.ANSI_256,
            "\x1b[;48;5;64m",
        ),
        (
            yuio.color.Color.back_from_hex("#338F15"),
            yuio.color.ColorSupport.ANSI_TRUE,
            "\x1b[;48;2;51;143;21m",
        ),
        (
            # Special case for grayscale.
            yuio.color.Color.fore_from_hex("#333333"),
            yuio.color.ColorSupport.ANSI_256,
            "\x1b[;38;5;236m",
        ),
        (yuio.color.Color.STYLE_BOLD, yuio.color.ColorSupport.ANSI, "\x1b[;1m"),
        (yuio.color.Color.STYLE_DIM, yuio.color.ColorSupport.ANSI, "\x1b[;2m"),
        (yuio.color.Color.STYLE_ITALIC, yuio.color.ColorSupport.ANSI, "\x1b[;3m"),
        (yuio.color.Color.STYLE_UNDERLINE, yuio.color.ColorSupport.ANSI, "\x1b[;4m"),
        (yuio.color.Color.STYLE_BLINK, yuio.color.ColorSupport.ANSI, "\x1b[;5m"),
        (yuio.color.Color.STYLE_INVERSE, yuio.color.ColorSupport.ANSI, "\x1b[;7m"),
        (
            yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_ITALIC
            | yuio.color.Color.STYLE_UNDERLINE
            | yuio.color.Color.STYLE_INVERSE
            | yuio.color.Color.STYLE_BLINK,
            yuio.color.ColorSupport.ANSI,
            "\x1b[;1;2;3;4;5;7m",
        ),
        (
            yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_ITALIC
            | yuio.color.Color.STYLE_UNDERLINE
            | yuio.color.Color.STYLE_INVERSE
            | yuio.color.Color.STYLE_BLINK
            | yuio.color.Color.STYLE_NORMAL,
            yuio.color.ColorSupport.ANSI,
            "\x1b[m",
        ),
        (yuio.color.Color.STYLE_NORMAL, yuio.color.ColorSupport.ANSI, "\x1b[m"),
        (yuio.color.Color.FORE_NORMAL_DIM, yuio.color.ColorSupport.ANSI, "\x1b[;2m"),
    ],
)
def test_color_to_code(color: yuio.color.Color, cap, expect):
    assert color.as_code(cap) == expect
