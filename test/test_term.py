import contextlib
import io
import os
import sys

import pytest

import yuio.color
import yuio.term


class MockOStream(io.StringIO):
    def __init__(
        self,
        out: "MockIStream",
        tty: bool,
        should_query_osc: bool,
        osc_response: str | None,
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
        return super().write(s)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def _add_to_out(self, s):
        pos = self.__out.tell()
        self.__out.seek(0, io.SEEK_END)
        self.__out.write(s)
        self.__out.seek(pos)
        self.__out.flush()


class MockIStream(io.StringIO):
    def __init__(
        self,
        tty: bool,
    ):
        super().__init__()
        self.__tty = tty

    def isatty(self) -> bool:
        return self.__tty

    def read(self, size=None):
        raise RuntimeError("term not supposed to use stream.read")

    def readline(self, size=None):
        raise RuntimeError("term not supposed to use stream.readline")

    def readlines(self, hint=-1):
        raise RuntimeError("term not supposed to use stream.readlines")

    def read_keycode(self):
        return super().read()


@contextlib.contextmanager
def mock_term_io(
    i_tty: bool = False,
    o_tty: bool = False,
    should_query_osc: bool = False,
    is_foreground: bool = False,
    env: dict[str, str] = {},
    args: list[str] = [],
    osc_response: str | None = "",
    enable_vt_processing: bool = False,
):
    istream = MockIStream(i_tty)
    ostream = MockOStream(istream, o_tty, should_query_osc, osc_response)

    old_env = os.environ.copy()
    os.environ.clear()
    os.environ.update(env)

    old_args = sys.argv[1:]
    sys.argv[1:] = args

    old_read_keycode, yuio.term._read_keycode = (
        yuio.term._read_keycode,
        istream.read_keycode,
    )
    old_is_foreground, yuio.term._is_foreground = (
        yuio.term._is_foreground,
        lambda _: is_foreground,
    )
    old_is_interactive_input, yuio.term._is_interactive_input = (
        yuio.term._is_interactive_input,
        lambda _: i_tty,
    )
    old_enter_raw_mode, yuio.term._enter_raw_mode = (
        yuio.term._enter_raw_mode,
        lambda *_, **__: contextlib.nullcontext(),
    )
    old_enable_vt_processing, yuio.term._enable_vt_processing = (
        yuio.term._enable_vt_processing,
        lambda ostream: enable_vt_processing,
    )
    old_flush_input_buffer, yuio.term._flush_input_buffer = (
        yuio.term._flush_input_buffer,
        lambda: None,
    )

    try:
        yield ostream, istream
    finally:
        os.environ.clear()
        os.environ.update(old_env)

        sys.argv[1:] = old_args

        yuio.term._read_keycode = old_read_keycode
        yuio.term._is_foreground = old_is_foreground
        yuio.term._is_interactive_input = old_is_interactive_input
        yuio.term._enter_raw_mode = old_enter_raw_mode
        yuio.term._enable_vt_processing = old_enable_vt_processing
        yuio.term._flush_input_buffer = old_flush_input_buffer


term_colors = yuio.term.TerminalTheme(
    background=yuio.color.ColorValue.from_hex("#000000"),
    foreground=yuio.color.ColorValue.from_hex("#BFBFBF"),
    black=yuio.color.ColorValue.from_hex("#000000"),
    red=yuio.color.ColorValue.from_hex("#D42C3A"),
    green=yuio.color.ColorValue.from_hex("#1CA800"),
    yellow=yuio.color.ColorValue.from_hex("#C0A000"),
    blue=yuio.color.ColorValue.from_hex("#005DFF"),
    magenta=yuio.color.ColorValue.from_hex("#B148C6"),
    cyan=yuio.color.ColorValue.from_hex("#00A89A"),
    white=yuio.color.ColorValue.from_hex("#BFBFBF"),
    lightness=yuio.term.Lightness.DARK,
)


@pytest.mark.parametrize(
    ("level", "ansi", "ansi_256", "ansi_true"),
    [
        (yuio.term.ColorSupport.ANSI, True, False, False),
        (yuio.term.ColorSupport.ANSI_256, True, True, False),
        (yuio.term.ColorSupport.ANSI_TRUE, True, True, True),
    ],
)
def test_color_support(level, ansi, ansi_256, ansi_true):
    term = yuio.term.Term(None, None, color_support=level)  # type: ignore
    assert term.supports_colors == ansi
    assert term.supports_colors_256 == ansi_256
    assert term.supports_colors_true == ansi_true


@pytest.mark.parametrize(
    ("level", "move", "query"),
    [
        (yuio.term.InteractiveSupport.NONE, False, False),
        (yuio.term.InteractiveSupport.MOVE_CURSOR, True, False),
        (yuio.term.InteractiveSupport.FULL, True, True),
    ],
)
def test_interactive_support(level, move, query):
    term = yuio.term.Term(
        None,  # type: ignore
        None,  # type: ignore
        color_support=yuio.term.ColorSupport.ANSI,
        interactive_support=level,
    )
    assert term.can_move_cursor == move
    assert term.can_query_terminal == term.is_fully_interactive == query
    term = yuio.term.Term(
        None,  # type: ignore
        None,  # type: ignore
        color_support=yuio.term.ColorSupport.NONE,
        interactive_support=level,
    )
    assert not term.can_move_cursor
    assert not term.can_query_terminal
    assert not term.is_fully_interactive


@pytest.mark.linux
@pytest.mark.darwin
@pytest.mark.parametrize(
    ("kwargs", "expected_term"),
    [
        (
            {},
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {"env": {"TERM": "xterm"}},
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,
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
                "terminal_theme": None,  # OSC query got no response
            },
        ),
        (
            {
                "env": {"TERM": "xterm", "COLORTERM": "yes"},
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "should_query_osc": True,
                "osc_response": "\x1b[?c",
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_256,
                "interactive_support": yuio.term.InteractiveSupport.FULL,
                "terminal_theme": None,  # kbhit responds, but OSC is not properly supported
            },
        ),
        (
            {
                "env": {"TERM": "xterm", "COLORTERM": "yes"},
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "should_query_osc": True,
                "osc_response": None,  # default response
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_256,
                "interactive_support": yuio.term.InteractiveSupport.FULL,
                "terminal_theme": term_colors,  # Got the response!
            },
        ),
        (
            {
                "env": {"TERM": "xterm", "COLORTERM": "yes"},
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "args": ["--no-color"],
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "env": {"TERM": "xterm", "COLORTERM": "yes", "FORCE_NO_COLOR": "1"},
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "args": ["--force-color"],
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {"env": {"FORCE_COLOR": "1"}},
            {
                "color_support": yuio.term.ColorSupport.ANSI,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
    ],
)
def test_capabilities_estimation(kwargs, expected_term):
    with mock_term_io(**kwargs) as streams:
        ostream, istream = streams
        term = yuio.term.get_term_from_stream(ostream, istream)
        expected = yuio.term.Term(ostream, istream, **expected_term)
        assert term == expected


@pytest.mark.windows
@pytest.mark.parametrize(
    ("kwargs", "expected_term"),
    [
        (
            {},
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {"enable_vt_processing": True},
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "i_tty": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "o_tty": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "o_tty": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "i_tty": True,
                "o_tty": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "i_tty": True,
                "o_tty": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "is_foreground": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "i_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "o_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                "interactive_support": yuio.term.InteractiveSupport.MOVE_CURSOR,
                "terminal_theme": None,
            },
        ),
        (
            {
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
                "should_query_osc": True,
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                "interactive_support": yuio.term.InteractiveSupport.FULL,
                "terminal_theme": None,  # OSC query got no response
            },
        ),
        (
            {
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
                "should_query_osc": True,
                "osc_response": "\x1b[?c",
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                "interactive_support": yuio.term.InteractiveSupport.FULL,
                "terminal_theme": None,  # kbhit responds, but OSC is not properly supported
            },
        ),
        (
            {
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
                "should_query_osc": True,
                "osc_response": None,  # default response
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI_TRUE,
                "interactive_support": yuio.term.InteractiveSupport.FULL,
                "terminal_theme": term_colors,  # Got the response!
            },
        ),
        (
            {
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
                "args": ["--no-color"],
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "env": {"FORCE_NO_COLOR": "1"},
                "i_tty": True,
                "o_tty": True,
                "is_foreground": True,
                "enable_vt_processing": True,
            },
            {
                "color_support": yuio.term.ColorSupport.NONE,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {
                "args": ["--force-color"],
            },
            {
                "color_support": yuio.term.ColorSupport.ANSI,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
        (
            {"env": {"FORCE_COLOR": "1"}},
            {
                "color_support": yuio.term.ColorSupport.ANSI,
                "interactive_support": yuio.term.InteractiveSupport.NONE,
                "terminal_theme": None,
            },
        ),
    ],
)
def test_capabilities_estimation_windows(kwargs, expected_term):
    with mock_term_io(**kwargs) as streams:
        ostream, istream = streams
        term = yuio.term.get_term_from_stream(ostream, istream)
        expected = yuio.term.Term(ostream, istream, **expected_term)
        assert term == expected


@pytest.mark.parametrize(
    ("color", "cap", "expect"),
    [
        (yuio.color.Color.NONE, yuio.term.ColorSupport.NONE, ""),
        (yuio.color.Color.NONE, yuio.term.ColorSupport.ANSI, "\x1b[m"),
        (yuio.color.Color.NONE, yuio.term.ColorSupport.ANSI_256, "\x1b[m"),
        (yuio.color.Color.NONE, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[m"),
        (yuio.color.Color.FORE_RED, yuio.term.ColorSupport.NONE, ""),
        (yuio.color.Color.FORE_RED, yuio.term.ColorSupport.ANSI, "\x1b[;31m"),
        (yuio.color.Color.FORE_RED, yuio.term.ColorSupport.ANSI_256, "\x1b[;31m"),
        (yuio.color.Color.FORE_RED, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;31m"),
        (yuio.color.Color.BACK_RED, yuio.term.ColorSupport.NONE, ""),
        (yuio.color.Color.BACK_RED, yuio.term.ColorSupport.ANSI, "\x1b[;41m"),
        (yuio.color.Color.BACK_RED, yuio.term.ColorSupport.ANSI_256, "\x1b[;41m"),
        (yuio.color.Color.BACK_RED, yuio.term.ColorSupport.ANSI_TRUE, "\x1b[;41m"),
        (yuio.color.Color.fore_from_hex("#338F15"), yuio.term.ColorSupport.NONE, ""),
        (
            yuio.color.Color.fore_from_hex("#338F15"),
            yuio.term.ColorSupport.ANSI,
            "\x1b[;32m",
        ),
        (
            yuio.color.Color.fore_from_hex("#338F15"),
            yuio.term.ColorSupport.ANSI_256,
            "\x1b[;38;5;64m",
        ),
        (
            yuio.color.Color.fore_from_hex("#338F15"),
            yuio.term.ColorSupport.ANSI_TRUE,
            "\x1b[;38;2;51;143;21m",
        ),
        (yuio.color.Color.back_from_hex("#338F15"), yuio.term.ColorSupport.NONE, ""),
        (
            yuio.color.Color.back_from_hex("#338F15"),
            yuio.term.ColorSupport.ANSI,
            "\x1b[;42m",
        ),
        (
            yuio.color.Color.back_from_hex("#338F15"),
            yuio.term.ColorSupport.ANSI_256,
            "\x1b[;48;5;64m",
        ),
        (
            yuio.color.Color.back_from_hex("#338F15"),
            yuio.term.ColorSupport.ANSI_TRUE,
            "\x1b[;48;2;51;143;21m",
        ),
    ],
)
def color_to_code(self, color: yuio.color.Color, cap, expect):
    term = yuio.term.Term(None, None, color_support=cap)  # type: ignore
    assert yuio.term.color_to_code(color, term) == expect
