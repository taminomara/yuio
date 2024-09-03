import dataclasses
import io
import os
import re
import sys
from dataclasses import dataclass

import pytest

from yuio import _typing as _t


@pytest.fixture
def save_env():
    env = dict(os.environ)

    yield

    os.environ.clear()
    os.environ.update(env)


@pytest.fixture
def save_stdin():
    stdin = sys.stdin

    yield

    sys.stdin = stdin


_WIDTH = 20
_HEIGHT = 5


@pytest.fixture
def sstream():
    return io.StringIO()


@pytest.fixture
def term(sstream):
    import yuio.term

    return yuio.term.Term(
        sstream,
        color_support=yuio.term.ColorSupport.ANSI_TRUE,
        interactive_support=yuio.term.InteractiveSupport.FULL,
    )


@pytest.fixture
def rc(term):
    import yuio.theme
    import yuio.widget

    rc = yuio.widget.RenderContext(term, yuio.theme.Theme())
    rc._override_wh = (_WIDTH, _HEIGHT)
    rc.prepare()
    return rc


def pytest_assertrepr_compare(op, left, right):
    if op == "==" and (isinstance(left, RcCompare) or isinstance(right, RcCompare)):
        if isinstance(left, str):
            left = RcCompare.from_commands(left)
        elif not isinstance(left, RcCompare):
            return None
        if isinstance(right, str):
            right = RcCompare.from_commands(right)
        elif not isinstance(right, RcCompare):
            return None
        return _rc_diff(left, right)


@dataclass
class RcCompare:
    screen: _t.List[str] = dataclasses.field(
        default_factory=lambda: [" " * _WIDTH for _ in range(_HEIGHT)]
    )

    colors: _t.List[str] = dataclasses.field(
        default_factory=lambda: [" " * _WIDTH for _ in range(_HEIGHT)]
    )

    commands: str = dataclasses.field(default="", compare=False, hash=False)

    @classmethod
    def from_commands(cls, commands: str):
        return cls(*_render_screen(commands), commands)


_CSI_RE = re.compile(r"\x1b\[((?:-?[0-9]+)?(?:;(?:-?[0-9]+)?)*(?:[mJHABCDG]))")
_COLOR_NAMES = "Brgybmcw"


def _rc_diff(a: RcCompare, b: RcCompare):
    out = ["Comparing rendering results"]
    out += _show_diff(a.screen, b.screen, "Text:")
    out += _show_diff(a.colors, b.colors, "Colors:")
    out += ["", f"Left commands:", a.commands, "", "Right commands", b.commands]
    return out


def _show_diff(
    a_screen: _t.List[str], b_screen: _t.List[str], what: str
) -> _t.List[str]:
    if a_screen == b_screen:
        return []

    out_h = "  expected"
    out_expected = [
        out_h + " " * (_WIDTH + 4 - len(out_h)),
        "  ┌" + "─" * _WIDTH + "┐",
        *[f"{i + 1} │{line}│" for i, line in enumerate(b_screen)],
        "  └" + "─" * _WIDTH + "┘",
    ]

    got_h = "  actual"
    out_got = [
        got_h + " " * (_WIDTH + 4 - len(got_h)),
        "  ┌" + "─" * _WIDTH + "┐",
        *[f"{i + 1} │{line}│" for i, line in enumerate(a_screen)],
        "  └" + "─" * _WIDTH + "┘",
    ]

    diff_h = "  diff"
    out_diff = [
        diff_h + " " * (_WIDTH + 4 - len(diff_h)),
        "  ┌" + "─" * _WIDTH + "┐",
    ]

    for i, (a_line, b_line) in enumerate(zip(a_screen, b_screen)):
        line = f"{i + 1} │"
        for a, b in zip(a_line, b_line):
            line += " " if a == b else "!"
        out_diff.append(line + "│")

    out_diff.append("  └" + "─" * _WIDTH + "┘")

    return [what] + [
        f"{expected_line} {got_line} {diff_line}"
        for expected_line, got_line, diff_line in zip(out_expected, out_got, out_diff)
    ]


def _render_screen(commands: str) -> _t.Tuple[_t.List[str], _t.List[str]]:
    import yuio.term

    x, y = 0, 0
    text = [[" "] * _WIDTH for _ in range(_HEIGHT)]
    colors = [[" "] * _WIDTH for _ in range(_HEIGHT)]
    color = " "

    for i, part in enumerate(_CSI_RE.split(commands)):
        if i % 2 == 0:
            # Render text.
            for c in part:
                assert c not in "\r"
                if c == "\n":
                    x = 0
                    y += 1
                else:
                    assert (
                        0 <= x < _WIDTH and 0 <= y < _HEIGHT
                    ), "printing outside of the screen"
                    cw = yuio.term.line_width(c)
                    assert cw > 0, "this checker can't handle zero-width chars"
                    for _ in range(cw):
                        text[y][x] = c
                        colors[y][x] = color
                        c = ""
                        x += 1
        else:
            # Render an CSI.
            fn = part[-1]
            args = part[:-1].split(";")

            if fn == "m":
                # Color.
                for code in part[:-1].split(";"):
                    if not code or code == "0":
                        color = " "
                    else:
                        int_code = int(code)
                        assert (
                            30 <= int_code <= 37
                        ), "dont use non-standard colors with this assertion"
                        color = _COLOR_NAMES[int_code - 30]
            elif fn == "J":
                # Clear screen.
                assert args == [""], f"unexpected OSC args: {part!r}"
                text = [[" "] * _WIDTH for _ in range(_HEIGHT)]
                colors = [[" "] * _WIDTH for _ in range(_HEIGHT)]
            elif fn == "H":
                # Absolute cursor position.
                if len(args) == 0:
                    y, x = 0, 0
                elif len(args) == 1:
                    y, x = int(args[0] or "1") - 1, 0
                elif len(args) == 2:
                    y, x = int(args[0] or "1") - 1, int(args[1] or "1") - 1
                else:
                    assert False, f"invalid OSC: {part!r}"
            elif fn == "A":
                # Cursor up.
                assert len(args) <= 1, f"invalid OSC: {part!r}"
                y -= int(args[0] or "1") if args else 1
            elif fn == "B":
                # Cursor down.
                assert len(args) <= 1, f"invalid OSC: {part!r}"
                y += int(args[0] or "1") if args else 1
            elif fn == "C":
                # Cursor forward.
                assert len(args) <= 1, f"invalid OSC: {part!r}"
                x += int(args[0] or "1") if args else 1
            elif fn == "D":
                # Cursor back.
                assert len(args) <= 1, f"invalid OSC: {part!r}"
                x -= int(args[0] or "1") if args else 1
            elif fn == "G":
                # Absolute horizontal cursor position.
                assert len(args) <= 1, f"invalid OSC: {part!r}"
                x = int(args[0] or "1") - 1 if args else 1

    return (
        ["".join(line) for line in text],
        ["".join(line) for line in colors],
    )
