from __future__ import annotations

import contextlib
import dataclasses
import io
import os
import pathlib
import re
import sys
import traceback
from dataclasses import dataclass

import pytest

import yuio
import yuio.color
import yuio.io
import yuio.string
import yuio.term
import yuio.theme
import yuio.widget

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


T = _t.TypeVar("T")
W = _t.TypeVar("W", bound=yuio.widget.Widget[object])


class TestTheme(yuio.theme.Theme):
    progress_bar_width = 5
    msg_decorations_ascii = {
        **yuio.theme.DefaultTheme.msg_decorations_ascii,
        "spinner/pattern": "#",
    }
    msg_decorations_unicode = {
        **yuio.theme.DefaultTheme.msg_decorations_unicode,
        "spinner/pattern": "⣿",
    }
    colors = {
        "code": "magenta",
        "note": "cyan",
        "path": "code",
        "flag": "note",
        "bold": yuio.color.Color.STYLE_BOLD,
        "b": "bold",
        "dim": yuio.color.Color.STYLE_DIM,
        "d": "dim",
        "italic": yuio.color.Color.STYLE_ITALIC,
        "i": "italic",
        "underline": yuio.color.Color.STYLE_UNDERLINE,
        "u": "underline",
        "inverse": yuio.color.Color.STYLE_INVERSE,
        "normal": yuio.color.Color.FORE_NORMAL,
        "muted": yuio.color.Color.FORE_NORMAL_DIM,
        "black": yuio.color.Color.FORE_BLACK,
        "red": yuio.color.Color.FORE_RED,
        "green": yuio.color.Color.FORE_GREEN,
        "yellow": yuio.color.Color.FORE_YELLOW,
        "blue": yuio.color.Color.FORE_BLUE,
        "magenta": yuio.color.Color.FORE_MAGENTA,
        "cyan": yuio.color.Color.FORE_CYAN,
        "white": yuio.color.Color.FORE_WHITE,
        "msg/decoration": "magenta",
        "msg/text:heading": "bold",
        "msg/text:question": "blue",
        "msg/text:error": "red",
        "msg/text:failure": "bold red",
        "msg/text:warning": "yellow",
        "msg/text:success": "green",
        "msg/text:info": "cyan",
        "menu/text/error": "bold red",
    }


_WIDTH = 20
_HEIGHT = 5


@pytest.fixture
def width() -> int:
    return _WIDTH


@pytest.fixture
def height() -> int:
    return _HEIGHT


@pytest.fixture
def ostream() -> io.StringIO:
    return _MockedOStream()


@pytest.fixture
def istream() -> _t.TextIO:
    return _MockedIStream()


@pytest.fixture
def theme() -> yuio.theme.Theme:
    return TestTheme()


@pytest.fixture
def term(ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
    return yuio.term.Term(
        ostream,
        istream,
        color_support=yuio.term.ColorSupport.ANSI_TRUE,
        ostream_is_tty=True,
        istream_is_tty=True,
        is_unicode=True,
    )


@pytest.fixture
def rc(
    term: yuio.term.Term, theme: yuio.theme.Theme, width: int, height: int
) -> yuio.widget.RenderContext:
    rc = yuio.widget.RenderContext(term, theme)
    rc._override_wh = (width, height)
    rc.prepare()
    return rc


@pytest.fixture
def ctx(
    term: yuio.term.Term, theme: yuio.theme.Theme, width: int
) -> yuio.string.ReprContext:
    return yuio.string.ReprContext(
        term=term,
        theme=theme,
        width=width,
    )


@pytest.fixture
def io_mocker_factory(
    term: yuio.term.Term,
    theme: yuio.theme.Theme,
    width: int,
    height: int,
) -> _t.Callable[[], IOMocker]:
    def factory():
        return IOMocker(term, theme, width, height)

    return factory


@pytest.fixture
def io_mocker(io_mocker_factory) -> IOMocker:
    return io_mocker_factory()


@pytest.fixture
def widget_checker_factory(
    term: yuio.term.Term,
    theme: yuio.theme.Theme,
    width: int,
    height: int,
) -> _t.Callable[[], WidgetChecker[yuio.widget.Widget[object]]]:
    def factory():
        return WidgetChecker[yuio.widget.Widget[object]](term, theme, width, height)

    return factory


@pytest.fixture
def widget_checker(
    widget_checker_factory,
) -> WidgetChecker[yuio.widget.Widget[object]]:
    return widget_checker_factory()


@pytest.fixture
def enable_bg_updates() -> bool:
    return False


@pytest.fixture(autouse=True)
def setup_io(
    term: yuio.term.Term,
    theme: yuio.theme.Theme,
    monkeypatch: pytest.MonkeyPatch,
    enable_bg_updates: bool,
    width: int,
    height: int,
):
    assert yuio.term._TTY_SETUP_PERFORMED is False, "previous test didn't clean up"
    assert not hasattr(yuio.term, "_TTY_OUTPUT"), "previous test didn't clean up"
    assert not hasattr(yuio.term, "_TTY_INPUT"), "previous test didn't clean up"
    assert not hasattr(yuio.term, "_TERMINAL_THEME"), "previous test didn't clean up"
    assert not hasattr(yuio.term, "_EXPLICIT_COLOR_SUPPORT"), (
        "previous test didn't clean up"
    )
    assert not hasattr(yuio.term, "_COLOR_SUPPORT"), "previous test didn't clean up"
    assert yuio.io._STREAMS_WRAPPED is False, "previous test didn't clean up"
    assert yuio.io._IO_MANAGER is None, "previous test didn't clean up"
    assert yuio.io._ORIG_STDERR is None, "previous test didn't clean up"
    assert yuio.io._ORIG_STDOUT is None, "previous test didn't clean up"

    monkeypatch.setattr("sys.argv", ["prog"])

    monkeypatch.setattr(
        "yuio.term.get_tty_size",
        lambda *_, **__: os.terminal_size((width, height)),
    )

    monkeypatch.setattr("yuio.term._is_foreground", lambda *_, **__: True)
    yuio.term._TTY_SETUP_PERFORMED = True
    yuio.term._TTY_OUTPUT = term.ostream
    yuio.term._TTY_INPUT = term.istream
    yuio.term._TERMINAL_THEME = None
    yuio.term._EXPLICIT_COLOR_SUPPORT = None
    yuio.term._COLOR_SUPPORT = term.color_support

    io_manager = yuio.io._IoManager(term, theme, enable_bg_updates=enable_bg_updates)
    monkeypatch.setattr("yuio.io._IO_MANAGER", io_manager)

    yield

    io_manager.stop()

    yuio.term._TTY_SETUP_PERFORMED = False
    del yuio.term._TTY_OUTPUT
    del yuio.term._TTY_INPUT
    del yuio.term._TERMINAL_THEME
    del yuio.term._EXPLICIT_COLOR_SUPPORT
    del yuio.term._COLOR_SUPPORT
    try:
        assert yuio.io._STREAMS_WRAPPED is False, "this test didn't clean up"
        assert yuio.io._ORIG_STDERR is None, "this test didn't clean up"
        assert yuio.io._ORIG_STDOUT is None, "this test didn't clean up"
    finally:
        yuio.io._STREAMS_WRAPPED = False
        yuio.io._ORIG_STDERR = None
        yuio.io._ORIG_STDOUT = None


@pytest.fixture(scope="module")
def original_datadir(request: pytest.FixtureRequest):
    root = request.config.rootpath / "test"
    return root / "regression_data" / request.path.relative_to(root).with_suffix("")


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
    echo: bool = True

    def __str__(self):
        return self.__class__.__name__


_ExpectStdinReadline.__name__ = """<call to stdin.readline>"""


@dataclass
class _ExpectStdinReadlines:
    result: list[str]

    def __str__(self):
        return self.__class__.__name__


_ExpectStdinReadlines.__name__ = """<call to stdin.readlines>"""


@dataclass
class _WidgetAssert:
    fn: _t.Callable[[], None]

    def __str__(self):
        return self.__class__.__name__


_WidgetAssert.__name__ = """<assert widget state>"""


@dataclass
class _ExpectMark:
    mark: str | None

    def __str__(self):
        return f"<mark: {self.mark}>"


_ExpectMark.__name__ = """<mark>"""


class _KeyboardEventStream:
    def __init__(
        self,
        term: yuio.term.Term,
        theme: yuio.theme.Theme,
        events: list[
            tuple[
                traceback.StackSummary,
                yuio.widget.KeyboardEvent
                | RcCompare
                | _WidgetAssert
                | _KeyboardEventStreamDone
                | _ExpectStdinRead
                | _ExpectStdinReadline
                | _ExpectStdinReadlines
                | _ExpectMark,
            ]
        ],
        width: int,
    ):
        self.term = term
        self.theme = theme
        self.events = events
        self.index = 0
        self.width = width

    def __iter__(self):
        return self

    def __next__(self):
        return self._next()[1]

    def _next(
        self, expected_event_kind: type[T] = yuio.widget.KeyboardEvent
    ) -> tuple[traceback.StackSummary, T]:
        stack_summary, event = self._next_any()
        if not isinstance(event, expected_event_kind):
            raise AssertionError(
                f"expected {expected_event_kind.__name__}, got {event}"
            )
        return stack_summary, event

    def _next_any(self):
        while self.index < len(self.events):
            (stack_summary, event) = self.events[self.index]
            self.index += 1
            with self._patch_stack_summary(stack_summary):
                if isinstance(event, _KeyboardEventStreamDone):
                    raise event
                elif isinstance(event, RcCompare):
                    self.term.ostream.seek(0)
                    commands = self.term.ostream.read()
                    self.term.ostream.seek(0, io.SEEK_END)
                    assert RcCompare.from_commands(commands, self.width) == event
                elif isinstance(event, _WidgetAssert):
                    event.fn()
                else:
                    return stack_summary, event
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
            _, event = self._next(expected_event_kind=_ExpectStdinRead)
        except StopIteration:
            raise AssertionError("unexpected call to istream.read()") from None
        self.term.ostream.write(event.result)
        return event.result

    def readline(self, limit: int = -1) -> str:
        try:
            _, event = self._next(expected_event_kind=_ExpectStdinReadline)
        except StopIteration:
            raise AssertionError("unexpected call to istream.readline()") from None
        if event.echo:
            self.term.ostream.write(event.result)
        return event.result

    def readlines(self, hint: int = -1) -> list[str]:
        try:
            _, event = self._next(expected_event_kind=_ExpectStdinReadlines)
        except StopIteration:
            raise AssertionError("unexpected call to istream.read()") from None
        self.term.ostream.writelines(event.result)
        return event.result

    def mark(self, mark: str | None):
        try:
            stack_summary, event = self._next(expected_event_kind=_ExpectMark)
        except StopIteration:
            raise AssertionError("unexpected call to io_mocker.mark()") from None
        if event.mark != mark:
            with self._patch_stack_summary(stack_summary):
                raise AssertionError(f"expected {event}, got {_ExpectMark(mark)}")

    @contextlib.contextmanager
    def _patch_stack_summary(self, stack_summary: traceback.StackSummary):
        try:
            yield
        except Exception as e:
            stack_summary_text = "".join(stack_summary.format())
            e.args = (f"{e}\n\nAssertion origin:\n\n{stack_summary_text}",)
            raise e


_CURRENT_IOSTREAM_MOCK: _KeyboardEventStream | None = None


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

    def __init__(
        self,
        term: yuio.term.Term | None = None,
        theme: yuio.theme.Theme | None = None,
        width: int | None = None,
        height: int | None = None,
        wrap_streams: bool = False,
    ):
        self._events: list[
            tuple[
                traceback.StackSummary,
                yuio.widget.KeyboardEvent
                | RcCompare
                | _WidgetAssert
                | _KeyboardEventStreamDone
                | _ExpectStdinRead
                | _ExpectStdinReadline
                | _ExpectStdinReadlines
                | _ExpectMark,
            ]
        ] = []

        self._term = term
        self._theme = theme
        self._width = width
        self._height = height
        self._wrap_streams = wrap_streams

    def refresh(self) -> _t.Self:
        """
        Refresh screen.

        """
        return self.key("l", ctrl=True)

    def key(
        self,
        key: str | yuio.widget.Key,
        ctrl: bool = False,
        alt: bool = False,
        shift: bool = False,
    ) -> _t.Self:
        """
        Yield a key from the mocked keyboard event stream.

        """
        self._events.append(
            (
                self._get_stack_summary(),
                yuio.widget.KeyboardEvent(key, ctrl, alt, shift),
            )
        )
        return self

    def keyboard_event(self, keyboard_event: yuio.widget.KeyboardEvent) -> _t.Self:
        """
        Yield a keyboard event from the mocked keyboard event stream.

        """
        self._events.append((self._get_stack_summary(), keyboard_event))
        return self

    def text(self, text: str) -> _t.Self:
        """
        Yield a text, one letter at a time, from the mocked keyboard event stream.

        """
        stack_summary = self._get_stack_summary()
        self._events.extend((stack_summary, yuio.widget.KeyboardEvent(c)) for c in text)
        return self

    def paste(self, text: str) -> _t.Self:
        """
        Yield a text as a single paste event, from the mocked keyboard event stream.

        """
        stack_summary = self._get_stack_summary()
        self._events.append(
            (
                stack_summary,
                yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str=text),
            )
        )
        return self

    def expect_screen(
        self,
        screen: list[str] | None = None,
        colors: list[str] | None = None,
        urls: list[str] | None = None,
        cursor_x: int | None = None,
        cursor_y: int | None = None,
    ) -> _t.Self:
        """
        Check that the current contents of the output stream,
        when rendered onto a terminal, produce the given screen contents.

        """
        self._events.append(
            (
                self._get_stack_summary(),
                RcCompare(screen, colors, urls, cursor_x, cursor_y),
            )
        )
        return self

    def expect(self, fn: _t.Callable[[], bool]) -> _t.Self:
        """
        Run a lambda function and assert that it returns :data:`True`.

        """

        def cb():
            assert fn()

        self._events.append((self._get_stack_summary(), _WidgetAssert(cb)))
        return self

    def expect_eq(self, fn: _t.Callable[[], T], expected: T) -> _t.Self:
        """
        Run a lambda function and assert that it returns a value
        equal to the `expected`.

        """

        def cb():
            assert fn() == expected

        self._events.append((self._get_stack_summary(), _WidgetAssert(cb)))
        return self

    def expect_ne(self, fn: _t.Callable[[], T], expected: T) -> _t.Self:
        """
        Run a lambda function and assert that it returns a value
        not equal to the `expected`.

        """

        def cb():
            assert fn() != expected

        self._events.append((self._get_stack_summary(), _WidgetAssert(cb)))
        return self

    def expect_widget_to_continue(self) -> _t.Self:
        """
        Expect that a widget requests another event from
        the mocked keyboard event stream.

        This function will terminate mocked block early by raising an exception.
        The :meth:`KeyboardEventStream.mock` will catch it.

        """
        self._events.append((self._get_stack_summary(), _KeyboardEventStreamDone()))
        return self

    def expect_istream_read(self, result: str) -> _t.Self:
        """
        Expect a call to `istream.read()` and return the given result from it.

        """
        self._events.append((self._get_stack_summary(), _ExpectStdinRead(result)))
        return self

    def expect_istream_readline(self, result: str, echo: bool = True) -> _t.Self:
        """
        Expect a call to `istream.readline()` and return the given result from it.

        """
        self._events.append(
            (self._get_stack_summary(), _ExpectStdinReadline(result, echo))
        )
        return self

    def expect_istream_readlines(self, result: list[str]) -> _t.Self:
        """
        Expect a call to `istream.readlines()` and return the given result from it.

        """
        self._events.append((self._get_stack_summary(), _ExpectStdinReadlines(result)))
        return self

    def expect_mark(self, mark: str | None = None) -> _t.Self:
        """
        Expect a call to :meth:`IoMocker.mark`.

        This method allows adding custom checkpoints to the test code.
        This is useful when testing code that renders something but doesn't request
        any input from a user. Without a mark, all asserts will be checked at the end
        of the test, when :meth:`IoMocker.mock` exits. With a mark, you can manually
        trigger assert checks between redraws.

        :example:

            .. code-block:: python

                def test_something(io_mocker):
                    # First assert will be checked upon a call to `mark`.
                    io_mocker.expect_screen(...)
                    io_mocker.expect_mark()

                    # Second assert will be checked at the end of the test.
                    io_mocker.expect_screen(...)

                    with io_mocker.mock():
                        # Render things
                        ...

                        # Emit a mark event; this will check what we've rendered so far.
                        io_mocker.mark()

                        # Render some more things
                        ...

        """
        self._events.append((self._get_stack_summary(), _ExpectMark(mark)))
        return self

    def mark(self, mark: str | None = None):
        """
        Trigger a mark event.

        See :meth:`IoMocker.expect_mark` for details.

        """
        if _CURRENT_IOSTREAM_MOCK is None:
            raise RuntimeError(
                "you need to mock io streams before using this function; "
                "call KeyboardEventStream.mock or WidgetChecker.check to do so"
            )

        _CURRENT_IOSTREAM_MOCK.mark(mark)

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
        term: yuio.term.Term | None = None,
        theme: yuio.theme.Theme | None = None,
        width: int | None = None,
        height: int | None = None,
        wrap_streams: bool | None = None,
    ):
        """
        Bind :func:`yuio.widget._event_stream` and all mocked input streams
        to events from this mocker.

        """

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

        width = width or self._width
        if width is None:
            raise RuntimeError(
                "this mocker is not bound to any width; "
                "pass width to its constructor or its `mock`/`check` method"
            )

        height = height or self._height
        if height is None:
            raise RuntimeError(
                "this mocker is not bound to any height; "
                "pass height to its constructor or its `mock`/`check` method"
            )

        wrap_streams = wrap_streams if wrap_streams is not None else self._wrap_streams

        global _CURRENT_IOSTREAM_MOCK
        if _CURRENT_IOSTREAM_MOCK is not None:
            raise RuntimeError("can't have more than one mock at a time")
        _CURRENT_IOSTREAM_MOCK = _KeyboardEventStream(term, theme, self._events, width)

        old_event_stream, yuio.widget._event_stream = (
            yuio.widget._event_stream,
            lambda *_, **__: _CURRENT_IOSTREAM_MOCK,
        )
        old_enter_raw_mode, yuio.term._enter_raw_mode = (
            yuio.term._enter_raw_mode,
            lambda *_, **__: contextlib.nullcontext(),
        )
        old_stderr, sys.stderr = sys.stderr, term.ostream
        old_stdout, sys.stdout = sys.stdout, term.ostream
        old_stdin, sys.stdin = sys.stdin, term.istream

        yuio.widget.RenderContext._override_wh = (width, height)

        try:
            if wrap_streams:
                assert not yuio.io.streams_wrapped(), "previous test didn't clean up?"
                yuio.io.wrap_streams()

            try:
                yield
            except _KeyboardEventStreamDone:
                _CURRENT_IOSTREAM_MOCK.finish()
            else:
                _CURRENT_IOSTREAM_MOCK.finish()
        finally:
            if wrap_streams:
                yuio.io.restore_streams()
            yuio.widget.RenderContext._override_wh = None
            sys.stdin = old_stdin
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            yuio.term._enter_raw_mode = old_enter_raw_mode
            yuio.widget._event_stream = old_event_stream
            _CURRENT_IOSTREAM_MOCK = None


class WidgetChecker(IOMocker, _t.Generic[W]):
    """
    A keyboard event stream mocker that checks a specific widget.

    This class works like `KeyboardEventStream`, but it also knows that we're testing
    a specific widget. Because of that, we're able to write asserts
    on widget properties. For example:

    .. code-block:: python

       def test_something(term, theme, width, height):
           # We know that we're testing an `Input` widget...
           checker = (
               WidgetChecker[yuio.widget.Input](term, theme, width, height)
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
           ostream_is_tty=True,
           istream_is_tty=True,
       )
       _theme = yuio.theme.Theme()
       test_something(_term, _theme, 20, 5)

    """

    _widget: W | None = None

    def call(self, fn: _t.Callable[[W], None]) -> _t.Self:
        """
        Run a function with widget as an input.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            fn(self._widget)

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    def expect_widget(self, fn: _t.Callable[[W], bool]) -> _t.Self:
        """
        Assert some property of a widget.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            assert fn(self._widget)

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    def expect_widget_eq(self, fn: _t.Callable[[W], T], expected: T) -> _t.Self:
        """
        Assert that some property of a widget equals to the given value.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            assert fn(self._widget) == expected

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    def expect_widget_ne(self, fn: _t.Callable[[W], T], expected: T) -> _t.Self:
        """
        Assert that some property of a widget is not equal to the given value.

        """

        def widget_fn():
            assert self._widget is not None, "widget is required"
            assert fn(self._widget) != expected

        self._events.append((self._get_stack_summary(), _WidgetAssert(widget_fn)))
        return self

    @contextlib.contextmanager
    def mock(
        self,
        term: yuio.term.Term | None = None,
        theme: yuio.theme.Theme | None = None,
        width: int | None = None,
        height: int | None = None,
        wrap_streams: bool | None = None,
    ):
        raise RuntimeError("use WidgetChecker.check() instead")

    def check(
        self,
        widget: W,
        term: yuio.term.Term | None = None,
        theme: yuio.theme.Theme | None = None,
        width: int | None = None,
        height: int | None = None,
        wrap_streams: bool | None = None,
    ):
        """
        Run tests on the given widget, and return widget's result.

        """

        assert self._widget is None, "can't have more than one widget check at a time"
        self._widget = widget
        with super().mock(term, theme, width, height, wrap_streams):
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
        return 0

    def flush(self):
        self._assert_not_closed()

    def isatty(self) -> bool:
        return True

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

    def readlines(self, hint: int = -1) -> list[str]:
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

    def truncate(self, size: int | None = None) -> int:
        raise io.UnsupportedOperation("truncate")

    def __enter__(self) -> _t.TextIO:
        self._assert_not_closed()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def encoding(self) -> str:
        return "utf-8"

    @property
    def errors(self) -> str | None:
        return None


class _MockedOStream(io.StringIO):
    encoding = "utf-8"

    def isatty(self) -> bool:
        return True

    def fileno(self) -> int:
        return 1


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
    return None


@dataclass
class RcCompare:
    screen: list[str] | None = None
    colors: list[str] | None = None
    urls: list[str] | None = None
    cursor_x: int | None = None
    cursor_y: int | None = None

    commands: str = dataclasses.field(default="", compare=False, hash=False)

    def __post_init__(self, *args, **kwargs):
        prev_height, prev_name = None, ""
        for screen, name in [
            (self.screen, "screen"),
            (self.colors, "colors"),
            (self.colors, "colors"),
        ]:
            if screen is None:
                continue
            height = len(screen)
            if prev_height is None:
                prev_height = height
            elif height != prev_height:
                raise RuntimeError(
                    f"{prev_name} height does not match {name} height "
                    f"({prev_height} != {height})"
                )

        screen_width = None
        if self.screen:
            screen_width = yuio.string.line_width(self.screen[0])
            for i, line in enumerate(self.screen):
                if yuio.string.line_width(line) != screen_width:
                    raise RuntimeError(
                        f"width of screen line {i + 1} is not equal to the width of screen line 1: "
                        f"({yuio.string.line_width(self.screen[i])} != {screen_width})\n"
                        f"line: {line!r}"
                    )

        colors_width = None
        if self.colors:
            colors_width = yuio.string.line_width(self.colors[0])
            for i, line in enumerate(self.colors):
                if yuio.string.line_width(line) != colors_width:
                    raise RuntimeError(
                        f"width of colors line {i + 1} is not equal to the width of colors line 1: "
                        f"({yuio.string.line_width(self.colors[i])} != {colors_width})"
                    )

        urls_width = None
        if self.urls:
            urls_width = yuio.string.line_width(self.urls[0])
            for i, line in enumerate(self.urls):
                if yuio.string.line_width(line) != urls_width:
                    raise RuntimeError(
                        f"width of urls line {i + 1} is not equal to the width of urls line 1: "
                        f"({yuio.string.line_width(self.urls[i])} != {urls_width})"
                    )

        prev_width, prev_name = None, ""
        for width, name in [
            (screen_width, "screen"),
            (colors_width, "colors"),
            (urls_width, "colors"),
        ]:
            if width is None:
                continue
            if prev_width is None:
                prev_width = width
            elif width != prev_width:
                raise RuntimeError(
                    f"{prev_name} width does not match {name} width "
                    f"({prev_width} != {width})"
                )

        while self.screen or self.colors or self.urls:
            screen_is_space = self.screen is None or self.screen[-1].isspace()
            colors_is_space = self.colors is None or self.colors[-1].isspace()
            urls_is_space = self.urls is None or self.urls[-1].isspace()
            if screen_is_space and colors_is_space and urls_is_space:
                if self.screen:
                    self.screen.pop()
                if self.colors:
                    self.colors.pop()
                if self.urls:
                    self.urls.pop()
            elif not screen_is_space or not colors_is_space or not colors_is_space:
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
        if None not in [self.urls, rhs.urls] and self.urls != rhs.urls:
            return False
        if None not in [self.cursor_x, rhs.cursor_x] and self.cursor_x != rhs.cursor_x:
            return False
        if None not in [self.cursor_y, rhs.cursor_y] and self.cursor_y != rhs.cursor_y:
            return False

        return True

    def __str__(self):
        return "<assert rendered screen>"


_CSI_RE = re.compile(
    r"""
      \x1b\[
      (?P<csi>.*?(?:[umhlJHABCDG]))
    | (?P<bell>\a)
    | (?:\x1b]8;;(?P<url>.*?)\x1b\\)
    """,
    re.VERBOSE,
)
_COLOR_NAMES = "krgybmcw"


def _rc_diff(a: RcCompare, b: RcCompare):
    out = ["Comparing rendering results"]
    if a.screen is not None and b.screen is not None:
        out += _show_diff(a.screen, b.screen, "Text:")
    if a.colors is not None and b.colors is not None:
        out += _show_diff(a.colors, b.colors, "Colors:")
    if a.urls is not None and b.urls is not None:
        out += _show_diff(a.urls, b.urls, "Urls:")
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


def _show_diff(a_screen: list[str], b_screen: list[str], what: str) -> list[str]:
    if a_screen == b_screen:
        return []

    a_height = len(a_screen)
    b_height = len(b_screen)

    if not a_height and not b_height:
        return []

    a_width = len(a_screen[0]) if a_screen else 0
    b_width = len(b_screen[0]) if b_screen else 0
    if not a_screen:
        a_width = b_width
    elif not b_screen:
        b_width = a_width
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
    commands: str, width: int
) -> tuple[list[str], list[str], list[str], int, int]:
    height = 0
    x, y = 0, 0
    text = []
    colors = []
    urls = []
    color = " "
    url = " "

    def render_text(s: str):
        nonlocal height, x, y, text, colors, urls

        for c in s:
            assert c != "\r"
            if c == "\n":
                x = 0
                y += 1
            else:
                cw = yuio.string.line_width(c)
                if cw == 0:
                    raise RuntimeError("this checker can't handle zero-width chars")

                if x < 0 or y < 0:
                    raise RuntimeError(f"printing at negative coordinates: ({x}, {y})")
                if x + cw > width:
                    x = 0
                    y += 1
                if y >= height:
                    text += [[" "] * width for _ in range(y - height + 1)]
                    colors += [[" "] * width for _ in range(y - height + 1)]
                    urls += [[" "] * width for _ in range(y - height + 1)]
                    height = y + 1
                for _ in range(cw):
                    text[y][x] = c
                    colors[y][x] = color
                    urls[y][x] = url
                    c = ""
                    x += 1

    i = 0
    for match in _CSI_RE.finditer(commands):
        render_text(commands[i : match.start()])
        i = match.end()

        match match.lastgroup:
            case "csi":
                part = match.group("csi")

                fn = part[-1]
                args = part[:-1].split(";")

                if fn == "m":
                    # Color.
                    for code in part[:-1].split(";"):
                        bold = False
                        if not code or code in ["0", "39"]:
                            color = " "
                        else:
                            int_code = int(code)
                            if int_code == 1:
                                bold = True
                            elif int_code < 10:
                                pass  # dim, italic, etc.
                            elif 30 <= int_code <= 37:
                                color = _COLOR_NAMES[int_code - 30]
                            else:
                                assert False, (
                                    f"don't use non-standard colors with this assertion: {int_code}"
                                )
                        if bold:
                            color = "#" if color == " " else color.upper()
                elif fn == "J":
                    # Clear screen.
                    assert len(args) <= 1, f"invalid OSC: {part!r}"
                    if not args or args[0] in ("", "0"):
                        del text[y:]
                        del colors[y:]
                        height = y
                    elif args[0] == "2":
                        text = []
                        colors = []
                        height = 0
                    else:
                        assert False, f"invalid OSC: {part!r}"
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
            case "bell":
                pass
            case "url":
                url = (match.group("url") or " ")[0]
            case _:
                assert False

    render_text(commands[i:])

    return (
        ["".join(line) for line in text],
        ["".join(line) for line in colors],
        ["".join(line) for line in urls],
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
