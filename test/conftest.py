import contextlib
import dataclasses
import io
import os
import re
import sys
from dataclasses import dataclass

import pytest

import yuio
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _typing as _t

T = _t.TypeVar("T")


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
def sstream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def theme() -> yuio.theme.Theme:
    return yuio.theme.Theme()


@pytest.fixture
def term(sstream) -> yuio.term.Term:
    return yuio.term.Term(
        sstream,
        color_support=yuio.term.ColorSupport.ANSI_TRUE,
        interactive_support=yuio.term.InteractiveSupport.FULL,
    )


@pytest.fixture
def rc(term, theme) -> yuio.widget.RenderContext:
    rc = yuio.widget.RenderContext(term, theme)
    rc._override_wh = (_WIDTH, _HEIGHT)
    rc.prepare()
    return rc


@pytest.fixture
def keyboard_event_stream_factory(
    sstream, term, theme
) -> _t.Callable[[], "KeyboardEventStream"]:
    def factory():
        return KeyboardEventStream(sstream, term, theme)

    return factory


@pytest.fixture
def keyboard_event_stream(
    keyboard_event_stream_factory,
) -> _t.Generator["KeyboardEventStream", None, None]:
    return keyboard_event_stream_factory()


class _KeyboardEventStreamDone(BaseException):
    pass


@dataclass
class _WidgetAssert:
    fn: _t.Callable[[], bool]


class KeyboardEventStream:
    def __init__(
        self, sstream: io.StringIO, term: yuio.term.Term, theme: yuio.theme.Theme
    ):
        self._events: _t.List[
            _t.Union[
                yuio.widget.KeyboardEvent,
                RcCompare,
                _WidgetAssert,
                _KeyboardEventStreamDone,
            ]
        ] = []
        self._index = 0

        self._sstream = sstream

        self._term = term
        self._theme = theme

    def key(
        self, key: _t.Union[str, yuio.widget.Key], ctrl: bool = False, alt: bool = False
    ) -> "KeyboardEventStream":
        self._events.append(yuio.widget.KeyboardEvent(key, ctrl, alt))
        return self

    def keyboard_event(
        self, keyboard_event: yuio.widget.KeyboardEvent
    ) -> "KeyboardEventStream":
        self._events.append(keyboard_event)
        return self

    def text(self, text: str) -> "KeyboardEventStream":
        self._events.extend(yuio.widget.KeyboardEvent(c) for c in text)
        return self

    def expect_screen(
        self,
        screen: _t.Optional[_t.List[str]] = None,
        colors: _t.Optional[_t.List[str]] = None,
        cursor_x: _t.Optional[int] = None,
        cursor_y: _t.Optional[int] = None,
    ) -> "KeyboardEventStream":
        self._events.append(RcCompare(screen, colors, cursor_x, cursor_y))
        return self

    def expect(self, fn: _t.Callable[[], bool]) -> "KeyboardEventStream":
        self._events.append(_WidgetAssert(fn))
        return self

    def expect_eq(self, fn: _t.Callable[[], T], expected: T) -> "KeyboardEventStream":
        def eq():
            assert fn() == expected
            return True

        self._events.append(_WidgetAssert(eq))
        return self

    def expect_widget_to_continue(self):
        self._events.append(_KeyboardEventStreamDone())
        return self

    def __iter__(self):
        return self

    def __next__(self):
        while self._index < len(self._events):
            event = self._events[self._index]
            self._index += 1
            if isinstance(event, _KeyboardEventStreamDone):
                raise event
            elif isinstance(event, RcCompare):
                self._sstream.seek(0)
                commands = self._sstream.read()
                self._sstream.seek(0, io.SEEK_END)
                assert RcCompare.from_commands(commands) == event
            elif isinstance(event, _WidgetAssert):
                assert event.fn()
            else:
                return event
        raise StopIteration

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            assert self._index == len(
                self._events
            ), f"some events haven't been queried: {self._events[self._index:]}"
        return exc_type is _KeyboardEventStreamDone

    def check(self, widget: yuio.widget.Widget[T]) -> _t.Optional[T]:
        old_event_stream, yuio.widget._event_stream = (
            yuio.widget._event_stream,
            lambda: self,
        )
        old_set_cbreak, yuio.term._set_cbreak = (
            yuio.term._set_cbreak,
            lambda: contextlib.nullcontext(),
        )
        yuio.widget.RenderContext._override_wh = (_WIDTH, _HEIGHT)

        try:
            return widget.run(self._term, self._theme)
        except _KeyboardEventStreamDone:
            return None
        finally:
            yuio.widget._event_stream = old_event_stream
            yuio.term._set_cbreak = old_set_cbreak
            yuio.widget.RenderContext._override_wh = None


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
    screen: _t.Optional[_t.List[str]] = None
    colors: _t.Optional[_t.List[str]] = None
    cursor_x: _t.Optional[int] = None
    cursor_y: _t.Optional[int] = None

    commands: str = dataclasses.field(default="", compare=False, hash=False)

    @classmethod
    def from_commands(cls, commands: str, width: int = _WIDTH, height: int = _HEIGHT):
        return cls(*_render_screen(commands, width, height), commands)

    def __eq__(self, rhs: object) -> bool:
        if not isinstance(rhs, RcCompare):
            return NotImplemented

        if None not in [self.screen, rhs.screen] and self.screen != rhs.screen:
            return False
        if None not in [self.colors, rhs.colors] and self.colors != rhs.colors:
            return False
        if None not in [self.cursor_x, rhs.cursor_x] and self.cursor_x != rhs.cursor_x:
            return False
        if None not in [self.cursor_y, rhs.cursor_y] and self.cursor_y != rhs.cursor_y:
            return False

        return True


_CSI_RE = re.compile(r"\x1b\[((?:-?[0-9]+)?(?:;(?:-?[0-9]+)?)*(?:[mJHABCDG]))")
_COLOR_NAMES = "Brgybmcw"


def _rc_diff(a: RcCompare, b: RcCompare):
    out = ["Comparing rendering results"]
    if a.screen is not None and b.screen is not None:
        out += _show_diff(a.screen, b.screen, "Text:")
    if a.colors is not None and b.colors is not None:
        out += _show_diff(a.colors, b.colors, "Colors:")
    out.append("")
    if None not in [a.cursor_x, a.cursor_y]:
        out.append(f"Left cursor: ({a.cursor_x}, {a.cursor_y})")
    if None not in [b.cursor_x, b.cursor_y]:
        out.append(f"Right cursor: ({b.cursor_x}, {b.cursor_y})")
    if a.commands:
        out.append(f"Left commands: {_sanitize_commands(a.commands)}")
    if b.commands:
        out.append(f"Left commands: {_sanitize_commands(b.commands)}")
    return out


def _show_diff(
    a_screen: _t.List[str], b_screen: _t.List[str], what: str
) -> _t.List[str]:
    a_height = len(a_screen)
    b_height = len(b_screen)
    assert a_height == b_height

    if not a_height:
        return []

    a_width = len(a_screen[0])
    b_width = len(b_screen[0])
    assert a_width == b_width
    assert all(len(line) == a_width for line in a_screen)
    assert all(len(line) == b_width for line in b_screen)

    if not a_width:
        return []

    if a_screen == b_screen:
        return []

    out_h = "  expected"
    out_expected = [
        out_h + " " * (a_width + 4 - len(out_h)),
        "  ┌" + "─" * a_width + "┐",
        *[f"{i + 1} │{line}│" for i, line in enumerate(b_screen)],
        "  └" + "─" * a_width + "┘",
    ]

    got_h = "  actual"
    out_got = [
        got_h + " " * (a_width + 4 - len(got_h)),
        "  ┌" + "─" * a_width + "┐",
        *[f"{i + 1} │{line}│" for i, line in enumerate(a_screen)],
        "  └" + "─" * a_width + "┘",
    ]

    diff_h = "  diff"
    out_diff = [
        diff_h + " " * (a_width + 4 - len(diff_h)),
        "  ┌" + "─" * a_width + "┐",
    ]

    for i, (a_line, b_line) in enumerate(zip(a_screen, b_screen)):
        line = f"{i + 1} │"
        for a, b in zip(a_line, b_line):
            line += " " if a == b else "!"
        out_diff.append(line + "│")

    out_diff.append("  └" + "─" * a_width + "┘")

    return [what] + [
        f"{expected_line} {got_line} {diff_line}"
        for expected_line, got_line, diff_line in zip(out_expected, out_got, out_diff)
    ]


def _render_screen(
    commands: str, width: int = _WIDTH, height: int = _HEIGHT
) -> _t.Tuple[_t.List[str], _t.List[str], int, int]:
    import yuio.term

    x, y = 0, 0
    text = [[" "] * width for _ in range(height)]
    colors = [[" "] * width for _ in range(height)]
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
                        0 <= x < width and 0 <= y < height
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
                text = [[" "] * width for _ in range(height)]
                colors = [[" "] * width for _ in range(height)]
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
        x,
        y,
    )


def _sanitize_commands(commands: str) -> str:
    return (
        commands.replace("\x1b", "ESC")
        .replace("\a", "BEL")
        .replace("\r", "CR")
        .replace("\n", "LF")
    )
