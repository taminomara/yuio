import contextlib
import dataclasses
import io
import pathlib
import re
import traceback
from dataclasses import dataclass

import pytest

import yuio
import yuio.io
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _typing as _t

T = _t.TypeVar("T")
W = _t.TypeVar("W", bound=yuio.widget.Widget[object])


_WIDTH = 20
_HEIGHT = 5


@pytest.fixture
def ostream() -> io.StringIO:
    return io.StringIO()


@pytest.fixture
def istream() -> _t.TextIO:
    return _MockedIStream()


@pytest.fixture
def theme() -> yuio.theme.Theme:
    return yuio.theme.Theme()


@pytest.fixture
def term(ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
    return yuio.term.Term(
        ostream,
        istream,
        color_support=yuio.term.ColorSupport.ANSI_TRUE,
        interactive_support=yuio.term.InteractiveSupport.FULL,
    )


@pytest.fixture
def rc(term: yuio.term.Term, theme: yuio.theme.Theme) -> yuio.widget.RenderContext:
    rc = yuio.widget.RenderContext(term, theme)
    rc._override_wh = (_WIDTH, _HEIGHT)
    rc.prepare()
    return rc


@pytest.fixture
def io_mocker_factory(
    ostream: io.StringIO,
    term: yuio.term.Term,
    theme: yuio.theme.Theme,
) -> _t.Callable[[], "IOMocker"]:
    def factory():
        return IOMocker(ostream, term, theme)

    return factory


@pytest.fixture
def io_mocker(io_mocker_factory) -> "IOMocker":
    return io_mocker_factory()


@pytest.fixture
def widget_checker_factory(
    ostream: io.StringIO,
    term: yuio.term.Term,
    theme: yuio.theme.Theme,
) -> _t.Callable[[], "WidgetChecker[yuio.widget.Widget[object]]"]:
    def factory():
        return WidgetChecker[yuio.widget.Widget[object]](ostream, term, theme)

    return factory


@pytest.fixture
def widget_checker(
    widget_checker_factory,
) -> "WidgetChecker[yuio.widget.Widget[object]]":
    return widget_checker_factory()


@dataclass
class _KeyboardEventStreamDone(BaseException):
    def __str__(self):
        return self.__class__.__name__


_KeyboardEventStreamDone.__name__ = """<finish event stream>"""


@dataclass
class _ExpectStdinRead:
    result: str

    def __str__(self):
        return self.__class__.__name__


_ExpectStdinRead.__name__ = """<call to stdin.read>"""


@dataclass
class _ExpectStdinReadline:
    result: str

    def __str__(self):
        return self.__class__.__name__


_ExpectStdinReadline.__name__ = """<call to stdin.readline>"""


@dataclass
class _ExpectStdinReadlines:
    result: _t.List[str]

    def __str__(self):
        return self.__class__.__name__


_ExpectStdinReadlines.__name__ = """<call to stdin.readlines>"""


@dataclass
class _WidgetAssert:
    fn: _t.Callable[[], bool]

    def __str__(self):
        return self.__class__.__name__


_WidgetAssert.__name__ = """<assert widget state>"""


class _KeyboardEventStream:
    def __init__(
        self,
        ostream: io.StringIO,
        term: yuio.term.Term,
        theme: yuio.theme.Theme,
        events: _t.List[
            _t.Tuple[
                traceback.StackSummary,
                _t.Union[
                    yuio.widget.KeyboardEvent,
                    "RcCompare",
                    _WidgetAssert,
                    _KeyboardEventStreamDone,
                    _ExpectStdinRead,
                    _ExpectStdinReadline,
                    _ExpectStdinReadlines,
                ],
            ]
        ],
    ):
        self.ostream = ostream
        self.term = term
        self.theme = theme
        self.events = events
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        return self._next()

    def _next(self, expected_event_kind: _t.Type[T] = yuio.widget.KeyboardEvent) -> T:
        event = self._next_any()
        if not isinstance(event, expected_event_kind):
            raise AssertionError(
                f"expected {expected_event_kind.__name__}, got {event}"
            )
        return event

    def _next_any(self):
        while self.index < len(self.events):
            (stack_summary, event) = self.events[self.index]
            self.index += 1
            with self._patch_stack_summary(stack_summary):
                if isinstance(event, _KeyboardEventStreamDone):
                    raise event
                elif isinstance(event, RcCompare):
                    self.ostream.seek(0)
                    commands = self.ostream.read()
                    self.ostream.seek(0, io.SEEK_END)
                    assert RcCompare.from_commands(commands) == event
                elif isinstance(event, _WidgetAssert):
                    assert event.fn()
                else:
                    return event
        raise StopIteration

    def finish(self):
        try:
            # Process all asserts at the end of the stream.
            self._next_any()
        except StopIteration:
            pass
        else:
            # There are some unconsumed events.
            self.index -= 1  # Adjust for event that we've got from `_next_any`.
            raise AssertionError(
                "some events haven't been queried:\n\n"
                + "\n".join(f"{event[1]}" for event in self.events[self.index :])
            )

    def read(self, n: int = -1) -> str:
        try:
            event = self._next(expected_event_kind=_ExpectStdinRead)
        except StopIteration:
            raise AssertionError("unexpected call to istream.read()") from None
        self.ostream.write(event.result)
        return event.result

    def readline(self, limit: int = -1) -> str:
        try:
            event = self._next(expected_event_kind=_ExpectStdinReadline)
        except StopIteration:
            raise AssertionError("unexpected call to istream.readline()") from None
        self.ostream.write(event.result)
        return event.result

    def readlines(self, hint: int = -1) -> _t.List[str]:
        try:
            event = self._next(expected_event_kind=_ExpectStdinReadlines)
        except StopIteration:
            raise AssertionError("unexpected call to istream.read()") from None
        self.ostream.writelines(event.result)
        return event.result

    @contextlib.contextmanager
    def _patch_stack_summary(self, stack_summary: traceback.StackSummary):
        try:
            yield
        except Exception as e:
            stack_summary_text = "".join(stack_summary.format())
            e.args = (f"{e}\n\nAssertion origin:\n\n{stack_summary_text}",)
            raise e


_CURRENT_IOSTREAM_MOCK: _t.Optional["_KeyboardEventStream"] = None


class IOMocker:
    """
    A class for mocking contents of input/output streams and keyboard event stream.

    All tests use a separate terminal (an instance of :class:`yuio.term.Term`),
    that's been initialized with mock streams (specifically, :class:`io.StringIO`
    as output, and :class:`_MockedIStream` as input). This class can manipulate these
    streams, as well as :func:`yuio.widget._event_stream`, so that they yield
    what we expect.

    See fixtures for more details.

    """

    _Self = _t.TypeVar("_Self", bound="IOMocker")

    def __init__(
        self,
        ostream: _t.Optional[io.StringIO] = None,
        term: _t.Optional[yuio.term.Term] = None,
        theme: _t.Optional[yuio.theme.Theme] = None,
    ):
        self._events: _t.List[
            _t.Tuple[
                traceback.StackSummary,
                _t.Union[
                    yuio.widget.KeyboardEvent,
                    RcCompare,
                    _WidgetAssert,
                    _KeyboardEventStreamDone,
                    _ExpectStdinRead,
                    _ExpectStdinReadline,
                    _ExpectStdinReadlines,
                ],
            ]
        ] = []

        self._ostream = ostream
        self._term = term
        self._theme = theme

    def key(
        self: "_Self",
        key: _t.Union[str, yuio.widget.Key],
        ctrl: bool = False,
        alt: bool = False,
    ) -> "_Self":
        """
        Yield a key from the mocked keyboard event stream.

        """
        self._events.append(
            (self._get_stack_summary(), yuio.widget.KeyboardEvent(key, ctrl, alt))
        )
        return self

    def keyboard_event(
        self: "_Self", keyboard_event: yuio.widget.KeyboardEvent
    ) -> "_Self":
        """
        Yield a keyboard event from the mocked keyboard event stream.

        """
        self._events.append((self._get_stack_summary(), keyboard_event))
        return self

    def text(self: "_Self", text: str) -> "_Self":
        """
        Yield a text, one letter at a time, from the mocked keyboard event stream.

        """
        stack_summary = self._get_stack_summary()
        self._events.extend((stack_summary, yuio.widget.KeyboardEvent(c)) for c in text)
        return self

    def expect_screen(
        self: "_Self",
        screen: _t.Optional[_t.List[str]] = None,
        colors: _t.Optional[_t.List[str]] = None,
        cursor_x: _t.Optional[int] = None,
        cursor_y: _t.Optional[int] = None,
    ) -> "_Self":
        """
        Check that the current contents of the output stream,
        when rendered onto a terminal, produce the given screen contents.

        """
        self._events.append(
            (self._get_stack_summary(), RcCompare(screen, colors, cursor_x, cursor_y))
        )
        return self

    def expect(self: "_Self", fn: _t.Callable[[], bool]) -> "_Self":
        """
        Run a lambda function and assert that it returns :data:`True`.

        """

        self._events.append((self._get_stack_summary(), _WidgetAssert(fn)))
        return self

    def expect_eq(self: "_Self", fn: _t.Callable[[], T], expected: T) -> "_Self":
        """
        Run a lambda function and assert that it returns a value
        equal to the `expected`.

        """

        def eq():
            assert fn() == expected
            return True

        self._events.append((self._get_stack_summary(), _WidgetAssert(eq)))
        return self

    def expect_ne(self: "_Self", fn: _t.Callable[[], T], expected: T) -> "_Self":
        """
        Run a lambda function and assert that it returns a value
        not equal to the `expected`.

        """

        def eq():
            assert fn() != expected
            return True

        self._events.append((self._get_stack_summary(), _WidgetAssert(eq)))
        return self

    def expect_widget_to_continue(self: "_Self") -> "_Self":
        """
        Expect that a widget requests another event from
        the mocked keyboard event stream.

        This function will terminate mocked block early by raising an exception.
        The :meth:`KeyboardEventStream.mock` will catch it.

        """
        self._events.append((self._get_stack_summary(), _KeyboardEventStreamDone()))
        return self

    def expect_istream_read(self: "_Self", result: str) -> "_Self":
        """
        Expect a call to `istream.read()` and return the given result from it.

        """
        self._events.append((self._get_stack_summary(), _ExpectStdinRead(result)))
        return self

    def expect_istream_readline(self: "_Self", result: str) -> "_Self":
        """
        Expect a call to `istream.readline()` and return the given result from it.

        """
        self._events.append((self._get_stack_summary(), _ExpectStdinReadline(result)))
        return self

    def expect_istream_read(self: "_Self", result: _t.List[str]) -> "_Self":
        """
        Expect a call to `istream.readlines()` and return the given result from it.

        """
        self._events.append((self._get_stack_summary(), _ExpectStdinReadlines(result)))
        return self

    @staticmethod
    def _get_stack_summary() -> traceback.StackSummary:
        base_path = str(pathlib.Path(__file__).parent.parent.absolute())
        stack_summary = traceback.extract_stack()
        stack_summary.pop()
        stack_summary.pop()
        while stack_summary and base_path not in stack_summary[0].filename:
            stack_summary.pop(0)
        return stack_summary

    @contextlib.contextmanager
    def mock(
        self,
        ostream: _t.Optional[io.StringIO] = None,
        term: _t.Optional[yuio.term.Term] = None,
        theme: _t.Optional[yuio.theme.Theme] = None,
    ):
        """
        Bind :func:`yuio.widget._event_stream` and all mocked inout streams
        to events from this mocker.

        """

        ostream = ostream or self._ostream
        if ostream is None:
            raise RuntimeError(
                "this mocker is not bound to any ostream; "
                "pass ostream to its constructor or its `mock`/`check` method"
            )

        term = term or self._term
        if term is None:
            raise RuntimeError(
                "this mocker is not bound to any term; "
                "pass term to its constructor or its `mock`/`check` method"
            )

        theme = theme or self._theme
        if theme is None:
            raise RuntimeError(
                "this mocker is not bound to any theme; "
                "pass theme to its constructor or its `mock`/`check` method"
            )

        global _CURRENT_IOSTREAM_MOCK
        if _CURRENT_IOSTREAM_MOCK is not None:
            raise RuntimeError("can't have more than one mock at a time")
        _CURRENT_IOSTREAM_MOCK = _KeyboardEventStream(
            ostream, term, theme, self._events
        )

        old_event_stream, yuio.widget._event_stream = (
            yuio.widget._event_stream,
            lambda: _CURRENT_IOSTREAM_MOCK,
        )
        old_enter_raw_mode, yuio.term._enter_raw_mode = (
            yuio.term._enter_raw_mode,
            lambda: contextlib.nullcontext(),
        )

        yuio.widget.RenderContext._override_wh = (_WIDTH, _HEIGHT)

        try:
            try:
                yield
            except _KeyboardEventStreamDone:
                _CURRENT_IOSTREAM_MOCK.finish()
            else:
                _CURRENT_IOSTREAM_MOCK.finish()
        finally:
            yuio.widget._event_stream = old_event_stream
            yuio.term._enter_raw_mode = old_enter_raw_mode
            yuio.widget.RenderContext._override_wh = None
            _CURRENT_IOSTREAM_MOCK = None


class WidgetChecker(IOMocker, _t.Generic[W]):
    """
    A keyboard event stream mocker that checks a specific widget.

    This class works like `KeyboardEventStream`, but it also knows that we're testing
    a specific widget. Because of that, we're able to write asserts
    on widget properties. For example:

    .. code-block:: python

       def test_something(ostream, term, theme):
          # We know that we're testing an `Input` widget...
          checker = (
              WidgetChecker[yuio.widget.Input](ostream, term, theme)
                  # ...therefore we can write asserts that check specific properties
                  # of the `Input` widget.
                  .expect_widget_eq(lambda widget: widget.text, "foo bar!")
                  .expect_widget_to_continue()
          )

          # Now we can run tests for a widget.
          checker.check(yuio.widget.Input(text="foo bar!"))

    .. invisible-code-block: python

       _ostream = io.StringIO()
       _istream = _MockedIStream()
       _term = yuio.term.Term(
           _ostream,
           _istream,
           color_support=yuio.term.ColorSupport.ANSI_TRUE,
           interactive_support=yuio.term.InteractiveSupport.FULL,
       )
       _theme = yuio.theme.Theme()
       test_something(_ostream, _term, _theme)

    """

    _Self = _t.TypeVar("_Self", bound="WidgetChecker[_t.Any]")

    _widget: _t.Optional[W] = None

    def expect_widget(self: "_Self", fn: _t.Callable[[W], bool]) -> "_Self":
        """
        Assert some property of a widget.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            return fn(self._widget)

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    def expect_widget_eq(
        self: "_Self", fn: _t.Callable[[W], T], expected: T
    ) -> "_Self":
        """
        Assert that some property of a widget equals to the given value.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            return fn(self._widget) == expected

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    def expect_widget_ne(
        self: "_Self", fn: _t.Callable[[W], T], expected: T
    ) -> "_Self":
        """
        Assert that some property of a widget is not equal to the given value.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            return fn(self._widget) != expected

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    @contextlib.contextmanager
    def mock(
        self,
        ostream: _t.Optional[io.StringIO] = None,
        term: _t.Optional[yuio.term.Term] = None,
        theme: _t.Optional[yuio.theme.Theme] = None,
    ):
        raise RuntimeError("use WidgetChecker.check() instead")

    def check(
        self,
        widget: W,
        ostream: _t.Optional[io.StringIO] = None,
        term: _t.Optional[yuio.term.Term] = None,
        theme: _t.Optional[yuio.theme.Theme] = None,
    ):
        """
        Run tests on the given widget, and return widget's result.

        """

        assert self._widget is None, "can't have more than one widget check at a time"
        self._widget = widget
        with super().mock(ostream, term, theme):
            if _CURRENT_IOSTREAM_MOCK is None:
                raise RuntimeError(
                    "mock() should've set _CURRENT_IOSTREAM_MOCK, but it didn't?"
                )

            try:
                return widget.run(
                    _CURRENT_IOSTREAM_MOCK.term, _CURRENT_IOSTREAM_MOCK.theme
                )
            finally:
                self._widget = None


class _MockedIStream(_t.TextIO):
    _closed: bool = False

    def close(self):
        self._closed = True

    def _assert_not_closed(self):
        if self._closed:
            raise ValueError("I/O operation on closed file")

    @property
    def closed(self) -> bool:
        return self._closed

    def fileno(self) -> int:
        raise io.UnsupportedOperation("fileno")

    def flush(self):
        self._assert_not_closed()

    def isatty(self) -> bool:
        return False

    def writable(self) -> bool:
        return False

    def write(self, s: str, /) -> int:
        raise io.UnsupportedOperation("write")

    def writelines(self, lines: _t.Iterable[str], /):
        raise io.UnsupportedOperation("writelines")

    def readable(self) -> bool:
        return True

    def read(self, n: int = -1) -> str:
        self._assert_not_closed()
        if _CURRENT_IOSTREAM_MOCK is None:
            raise RuntimeError(
                "you need to mock io streams before using this function; "
                "call KeyboardEventStream.mock or WidgetChecker.check to do so"
            )
        return _CURRENT_IOSTREAM_MOCK.read(n)

    def readline(self, limit: int = -1) -> str:
        self._assert_not_closed()
        if _CURRENT_IOSTREAM_MOCK is None:
            raise RuntimeError(
                "you need to mock io streams before using this function; "
                "call KeyboardEventStream.mock or WidgetChecker.check to do so"
            )
        return _CURRENT_IOSTREAM_MOCK.readline(limit)

    def readlines(self, hint: int = -1) -> _t.List[str]:
        self._assert_not_closed()
        if _CURRENT_IOSTREAM_MOCK is None:
            raise RuntimeError(
                "you need to mock io streams before using this function; "
                "call KeyboardEventStream.mock or WidgetChecker.check to do so"
            )
        return _CURRENT_IOSTREAM_MOCK.readlines(hint)

    def seek(self, offset: int, whence: int = 0) -> int:
        raise io.UnsupportedOperation("underlying stream is not seekable")

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        raise io.UnsupportedOperation("underlying stream is not seekable")

    def truncate(self, size: _t.Optional[int] = None) -> int:
        raise io.UnsupportedOperation("truncate")

    def __enter__(self) -> _t.TextIO:
        self._assert_not_closed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def encoding(self) -> str:
        return None  # type: ignore

    @property
    def errors(self) -> _t.Optional[str]:
        return None


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

    def __post_init__(self, *args, **kwargs):
        if self.screen is not None and self.colors is not None:
            if len(self.screen) != len(self.colors):
                raise RuntimeError(
                    f"screen height does not match colors height "
                    f"({len(self.screen)} != {len(self.colors)})"
                )

        screen_width = None
        if self.screen:
            screen_width = yuio.term.line_width(self.screen[0])
            for i, line in enumerate(self.screen):
                if yuio.term.line_width(line) != screen_width:
                    raise RuntimeError(
                        f"width of screen line {i + 1} is not equal to the width of screen line 1: "
                        f"({yuio.term.line_width(self.screen[i])} != {screen_width})"
                    )

        colors_width = None
        if self.colors:
            colors_width = yuio.term.line_width(self.colors[0])
            for i, line in enumerate(self.colors):
                if yuio.term.line_width(line) != colors_width:
                    raise RuntimeError(
                        f"width of colors line {i + 1} is not equal to the width of colors line 1: "
                        f"({yuio.term.line_width(self.colors[i])} != {colors_width})"
                    )

        if screen_width is not None and colors_width is not None:
            if screen_width != colors_width:
                raise RuntimeError(
                    f"screen width does not match colors width "
                    f"({screen_width} != {colors_width})"
                )

        while self.screen or self.colors:
            screen_is_space = self.screen is None or self.screen[-1].isspace()
            colors_is_space = self.colors is None or self.colors[-1].isspace()
            if screen_is_space and colors_is_space:
                if self.screen:
                    self.screen.pop()
                if self.colors:
                    self.colors.pop()
            elif not screen_is_space or not colors_is_space:
                break

    @classmethod
    def from_commands(cls, commands: str, width: int = _WIDTH):
        return cls(*_render_screen(commands, width), commands)

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

    def __str__(self):
        return "<assert rendered screen>"


_CSI_RE = re.compile(r"\x1b\[((?:-?[0-9]+)?(?:;(?:-?[0-9]+)?)*(?:[mJHABCDG]))|\a")
_COLOR_NAMES = "krgybmcw"


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
    if a_screen == b_screen:
        return []

    a_height = len(a_screen)
    b_height = len(b_screen)

    if not a_height and not b_height:
        return []

    a_width = len(a_screen[0])
    b_width = len(b_screen[0])
    if a_width != b_width:
        return [f"Screen widths differ: {a_width} != {b_width}"]
    width = max(a_width, b_width)

    if not width:
        return []

    out_h = "   expected"
    out_expected = [
        out_h + " " * (width + 5 - len(out_h)),
        "   ┌" + "─" * width + "┐",
        *[f"{i + 1: >2} │{line}│" for i, line in enumerate(b_screen)],
        "   └" + "─" * width + "┘",
    ]

    got_h = "   actual"
    out_got = [
        got_h + " " * (width + 5 - len(got_h)),
        "   ┌" + "─" * width + "┐",
        *[f"{i + 1: >2} │{line}│" for i, line in enumerate(a_screen)],
        "   └" + "─" * width + "┘",
    ]

    diff_h = "   diff"
    out_diff = [
        diff_h + " " * (width + 5 - len(diff_h)),
        "   ┌" + "─" * width + "┐",
    ]

    for i in range(max(a_height, b_height)):
        line = f"{i + 1: >2} │"
        a_line = a_screen[i] if i < a_height else "\0" * width
        b_line = b_screen[i] if i < b_height else "\0" * width
        for a, b in zip(a_line, b_line):
            line += " " if a == b else "!"
        out_diff.append(line + "│")

    out_diff.append("   └" + "─" * width + "┘")

    height = max(len(out_got), len(out_expected), len(out_diff))

    out_got += ["     " + " " * width for _ in range(height - len(out_got))]
    out_expected += ["     " + " " * width for _ in range(height - len(out_expected))]
    out_diff += ["     " + " " * width for _ in range(height - len(out_diff))]

    return [what] + [
        f"{expected_line} {got_line} {diff_line}"
        for expected_line, got_line, diff_line in zip(out_expected, out_got, out_diff)
    ]


def _render_screen(
    commands: str, width: int = _WIDTH
) -> _t.Tuple[_t.List[str], _t.List[str], int, int]:
    height = 0
    x, y = 0, 0
    text = []
    colors = []
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
                    cw = yuio.term.line_width(c)
                    if cw == 0:
                        raise RuntimeError("this checker can't handle zero-width chars")

                    if x < 0 or y < 0:
                        raise RuntimeError(
                            f"printing at negative coordinates: ({x}, {y})"
                        )
                    if x + cw > width:
                        x = 0
                        y += 1
                    if y >= height:
                        text += [[" "] * width for _ in range(y - height + 1)]
                        colors += [[" "] * width for _ in range(y - height + 1)]
                        height = y + 1
                    for _ in range(cw):
                        text[y][x] = c
                        colors[y][x] = color
                        c = ""
                        x += 1
        else:
            # Render a CSI.

            if not part:
                continue  # '\a'

            fn = part[-1]
            args = part[:-1].split(";")

            if fn == "m":
                # Color.
                for code in part[:-1].split(";"):
                    bold = False
                    if not code or code == "0":
                        color = " "
                    else:
                        int_code = int(code)
                        if int_code == 1:
                            bold = True
                        elif int_code == 2:
                            pass  # dim
                        elif 30 <= int_code <= 37:
                            color = _COLOR_NAMES[int_code - 30]
                        else:
                            assert (
                                False
                            ), "dont use non-standard colors with this assertion"
                    if bold:
                        color = "B" if color == " " else color.upper()
            elif fn == "J":
                # Clear screen.
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
