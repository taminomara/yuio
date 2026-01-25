import contextlib
import io
import os
import sys

import pytest

import yuio.color
import yuio.term


class WindowsConsoleIO(io.BytesIO):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

    def isatty(self) -> bool:
        return True

    def fileno(self):
        return 123


class MockTTYStream(io.StringIO):
    def __init__(self, tty: bool):
        super().__init__()
        self.__tty = tty

    def isatty(self) -> bool:
        return self.__tty


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
        "\x1b]4;8;?\x1b\\"
        "\x1b]4;9;?\x1b\\"
        "\x1b]4;10;?\x1b\\"
        "\x1b]4;11;?\x1b\\"
        "\x1b]4;12;?\x1b\\"
        "\x1b]4;13;?\x1b\\"
        "\x1b]4;14;?\x1b\\"
        "\x1b]4;15;?\x1b\\"
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
        "\x1b]4;8;rgb:0000/0000/0000\x1b\\"
        "\x1b]4;9;rgb:d4d4/2c2c/3a3a\x1b\\"
        "\x1b]4;10;rgb:1c1c/a8a8/0000\x1b\\"
        "\x1b]4;11;rgb:c0c0/a0a0/0000\x1b\\"
        "\x1b]4;12;rgb:0000/5d5d/ffff\x1b\\"
        "\x1b]4;13;rgb:b1b1/4848/c6c6\x1b\\"
        "\x1b]4;14;rgb:0000/a8a8/9a9a\x1b\\"
        "\x1b]4;15;rgb:bfbf/bfbf/bfbf\x1b\\"
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

    def read_keycode(self, *_, **__):
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
        lambda *_, **__: is_foreground,
    )
    old_input_is_tty, yuio.term._input_is_tty = (
        yuio.term._input_is_tty,
        lambda *_, **__: i_tty,
    )
    old_output_is_tty, yuio.term._output_is_tty = (
        yuio.term._output_is_tty,
        lambda *_, **__: o_tty,
    )
    old_enter_raw_mode, yuio.term._enter_raw_mode = (
        yuio.term._enter_raw_mode,
        lambda *_, **__: contextlib.nullcontext(),
    )
    old_enable_vt_processing, yuio.term._enable_vt_processing = (
        yuio.term._enable_vt_processing,
        lambda *_, **__: enable_vt_processing,
    )
    old_flush_input_buffer, yuio.term._flush_input_buffer = (
        yuio.term._flush_input_buffer,
        lambda *_, **__: None,
    )

    try:
        yield ostream, istream
    finally:
        os.environ.clear()
        os.environ.update(old_env)

        sys.argv[1:] = old_args

        yuio.term._read_keycode = old_read_keycode
        yuio.term._is_foreground = old_is_foreground
        yuio.term._input_is_tty = old_input_is_tty
        yuio.term._output_is_tty = old_output_is_tty
        yuio.term._enter_raw_mode = old_enter_raw_mode
        yuio.term._enable_vt_processing = old_enable_vt_processing
        yuio.term._flush_input_buffer = old_flush_input_buffer


term_colors = yuio.term.TerminalTheme(
    background=yuio.color.ColorValue.from_hex("#000000"),
    foreground=yuio.color.ColorValue.from_hex("#BFBFBF"),
    black=yuio.color.ColorValue.from_hex("#000000"),
    bright_black=yuio.color.ColorValue.from_hex("#000000"),
    red=yuio.color.ColorValue.from_hex("#D42C3A"),
    bright_red=yuio.color.ColorValue.from_hex("#D42C3A"),
    green=yuio.color.ColorValue.from_hex("#1CA800"),
    bright_green=yuio.color.ColorValue.from_hex("#1CA800"),
    yellow=yuio.color.ColorValue.from_hex("#C0A000"),
    bright_yellow=yuio.color.ColorValue.from_hex("#C0A000"),
    blue=yuio.color.ColorValue.from_hex("#005DFF"),
    bright_blue=yuio.color.ColorValue.from_hex("#005DFF"),
    magenta=yuio.color.ColorValue.from_hex("#B148C6"),
    bright_magenta=yuio.color.ColorValue.from_hex("#B148C6"),
    cyan=yuio.color.ColorValue.from_hex("#00A89A"),
    bright_cyan=yuio.color.ColorValue.from_hex("#00A89A"),
    white=yuio.color.ColorValue.from_hex("#BFBFBF"),
    bright_white=yuio.color.ColorValue.from_hex("#BFBFBF"),
    lightness=yuio.term.Lightness.DARK,
)


@pytest.mark.parametrize(
    ("level", "ansi", "ansi_256", "ansi_true"),
    [
        (yuio.color.ColorSupport.ANSI, True, False, False),
        (yuio.color.ColorSupport.ANSI_256, True, True, False),
        (yuio.color.ColorSupport.ANSI_TRUE, True, True, True),
    ],
)
def test_color_support(level, ansi, ansi_256, ansi_true):
    term = yuio.term.Term(None, None, color_support=level)  # type: ignore
    assert term.supports_colors == ansi
    assert term.supports_colors_256 == ansi_256
    assert term.supports_colors_true == ansi_true


@pytest.mark.parametrize(
    ("env", "os_name", "has_wsl", "expected"),
    [
        ({"GITHUB_ACTIONS": "true"}, "posix", False, yuio.color.ColorSupport.ANSI_TRUE),
        ({"TRAVIS": "true"}, "posix", False, yuio.color.ColorSupport.ANSI),
        ({}, "nt", False, yuio.color.ColorSupport.NONE),
        ({"COLORTERM": "truecolor"}, "posix", False, yuio.color.ColorSupport.ANSI_TRUE),
        ({"COLORTERM": "24bit"}, "posix", False, yuio.color.ColorSupport.ANSI_TRUE),
        ({"TERM": "xterm-kitty"}, "posix", False, yuio.color.ColorSupport.ANSI_TRUE),
        ({"COLORTERM": "yes"}, "posix", False, yuio.color.ColorSupport.ANSI_256),
        ({"TERM": "xterm-256color"}, "posix", False, yuio.color.ColorSupport.ANSI_256),
        ({"TERM": "screen"}, "posix", False, yuio.color.ColorSupport.ANSI_256),
        ({"TERM": "xterm-256color"}, "posix", True, yuio.color.ColorSupport.ANSI_TRUE),
        ({"TERM": "linux"}, "posix", False, yuio.color.ColorSupport.ANSI),
        ({"TERM": "xterm"}, "posix", False, yuio.color.ColorSupport.ANSI),
        ({"TERM": "vt100-color"}, "posix", False, yuio.color.ColorSupport.ANSI),
        ({"TERM": "unknown"}, "posix", False, yuio.color.ColorSupport.NONE),
        ({}, "posix", False, yuio.color.ColorSupport.NONE),
    ],
)
def test_detect_color_support_from_env(monkeypatch, env, os_name, has_wsl, expected):
    for var in ["TERM", "COLORTERM"]:
        monkeypatch.delenv(var, raising=False)

    for k, v in env.items():
        monkeypatch.setenv(k, v)

    monkeypatch.setattr("os.name", os_name)
    monkeypatch.setattr(
        "shutil.which",
        lambda x: "/usr/bin/wslinfo" if x == "wslinfo" and has_wsl else None,
    )

    assert yuio.term._detect_color_support_from_env() == expected


@pytest.mark.parametrize(
    ("env", "argv", "expected"),
    [
        ({"FORCE_COLOR": "1"}, [], True),
        ({"NO_COLOR": "1"}, [], False),
        ({"FORCE_NO_COLOR": "1"}, [], False),
        ({}, ["--color"], True),
        ({}, ["--force-color"], True),
        ({}, ["--no-color"], False),
        ({}, ["--force-no-color"], False),
        ({}, ["--color=yes"], True),
        ({}, ["--colors=false"], False),
        ({}, ["--color=ansi"], yuio.color.ColorSupport.ANSI),
        ({}, ["--color=ansi256"], yuio.color.ColorSupport.ANSI_256),
        ({}, ["--color=ansi-true"], yuio.color.ColorSupport.ANSI_TRUE),
        ({"FORCE_COLOR": "1"}, ["--no-color"], False),
        ({"NO_COLOR": "1"}, ["--color=ansitrue"], yuio.color.ColorSupport.ANSI_TRUE),
        ({}, [], None),
    ],
)
def test_detect_explicit_color_settings(monkeypatch, env, argv, expected):
    for var in ["FORCE_COLOR", "NO_COLOR", "FORCE_NO_COLOR"]:
        monkeypatch.delenv(var, raising=False)

    for k, v in env.items():
        monkeypatch.setenv(k, v)

    monkeypatch.setattr(sys, "argv", ["script.py"] + argv)

    assert yuio.term._detect_explicit_color_settings() == expected


class TestFindTty:
    @pytest.fixture(autouse=True)
    def setup_io(self):
        yield

        yuio.term._TTY_SETUP_PERFORMED = False
        if hasattr(yuio.term, "_TTY_OUTPUT"):
            del yuio.term._TTY_OUTPUT
        if hasattr(yuio.term, "_TTY_INPUT"):
            del yuio.term._TTY_INPUT
        if hasattr(yuio.term, "_TERMINAL_THEME"):
            del yuio.term._TERMINAL_THEME
        if hasattr(yuio.term, "_EXPLICIT_COLOR_SUPPORT"):
            del yuio.term._EXPLICIT_COLOR_SUPPORT
        if hasattr(yuio.term, "_COLOR_SUPPORT"):
            del yuio.term._COLOR_SUPPORT

    @pytest.mark.parametrize(
        ("can_open_tty", "o_tty", "e_tty", "i_tty", "expected"),
        [
            (True, True, True, True, ("tty", "tty")),
            (False, True, True, True, ("stderr", "stdin")),
            (False, True, False, True, ("stdout", "stdin")),
            (False, False, False, True, ("stderr", "stdin")),
        ],
    )
    def test_find_tty(
        self,
        can_open_tty,
        o_tty,
        e_tty,
        i_tty,
        expected,
        monkeypatch: pytest.MonkeyPatch,
    ):
        tty_fd = None

        if os.name != "nt":
            _open = os.open

            def open(path, flags):
                nonlocal tty_fd
                assert tty_fd is None
                if path == "/dev/tty":
                    if can_open_tty:
                        tty_fd = _open(__file__, os.O_RDONLY)
                        return tty_fd
                    else:
                        raise OSError()
                else:
                    assert False

            monkeypatch.setattr("os.open", open)
        else:

            def windows_console_io(path, mode):
                nonlocal tty_fd
                if path in ["CONIN$", "CONOUT$"]:
                    if can_open_tty:
                        tty_fd = 123
                        return WindowsConsoleIO(path)
                    else:
                        raise OSError()
                else:
                    assert False

            monkeypatch.setattr("io._WindowsConsoleIO", windows_console_io)

        monkeypatch.setattr("yuio.term.__stdin", stdin := MockTTYStream(i_tty))
        monkeypatch.setattr("yuio.term.__stdout", stdout := MockTTYStream(o_tty))
        monkeypatch.setattr("yuio.term.__stderr", stderr := MockTTYStream(e_tty))

        streams = {
            "stdin": stdin,
            "stdout": stdout,
            "stderr": stderr,
        }

        expected_out = streams.get(expected[0])
        expected_in = streams.get(expected[1])

        term = yuio.term.get_tty()
        if expected_out:
            assert term.ostream is expected_out
        else:
            assert term.ostream.name == "/dev/tty" if os.name != "nt" else "CONOUT$"
            assert term.ostream.fileno() == tty_fd
        if expected_in:
            assert term.istream is expected_in
        else:
            assert term.istream.name == "/dev/tty" if os.name != "nt" else "CONIN$"
            assert term.istream.fileno() == tty_fd


# @pytest.mark.linux
# @pytest.mark.darwin
# @pytest.mark.parametrize(
#     ("kwargs", "expected_term"),
#     [
#         (
#             {},
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {"env": {"TERM": "xterm"}},
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "i_tty": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "o_tty": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "i_tty": True,
#                 "o_tty": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "is_foreground": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "i_tty": True,
#                 "is_foreground": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "o_tty": True,
#                 "is_foreground": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "yes"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "should_query_osc": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_256,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,  # OSC query got no response
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "truecolor"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "should_query_osc": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,  # OSC query got no response
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "yes"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "should_query_osc": True,
#                 "osc_response": "\x1b[?c",
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_256,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,  # kbhit responds, but OSC is not properly supported
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "yes"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "should_query_osc": True,
#                 "osc_response": None,  # default response
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_256,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": term_colors,  # Got the response!
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "yes"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "args": ["--no-color"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "yes", "NO_COLOR": "1"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "truecolor"},
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color"],
#                 "env": {"TERM": "xterm", "COLORTERM": "truecolor"},
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {"env": {"FORCE_COLOR": "1"}},
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"TERM": "xterm", "COLORTERM": "yes"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "args": ["--color=0"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color=1"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color=ansi"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color=ansi-256"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_256,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color=ansi-true"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#     ],
# )
# def test_capabilities_estimation(kwargs, expected_term):
#     with mock_term_io(**kwargs) as streams:
#         ostream, istream = streams
#         term = yuio.term.get_term_from_stream(ostream, istream)
#         expected = yuio.term.Term(ostream, istream, **expected_term)
#         assert term == expected


# @pytest.mark.windows
# @pytest.mark.parametrize(
#     ("kwargs", "expected_term"),
#     [
#         (
#             {},
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {"enable_vt_processing": True},
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "o_tty": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "o_tty": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.BACKGROUND,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#                 "should_query_osc": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,  # OSC query got no response
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#                 "should_query_osc": True,
#                 "osc_response": "\x1b[?c",
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,  # kbhit responds, but OSC is not properly supported
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#                 "should_query_osc": True,
#                 "osc_response": None,  # default response
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI_TRUE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": term_colors,  # Got the response!
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#                 "args": ["--no-color"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "env": {"NO_COLOR": "1"},
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {"env": {"FORCE_COLOR": "1"}},
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "i_tty": True,
#                 "o_tty": True,
#                 "is_foreground": True,
#                 "enable_vt_processing": True,
#                 "args": ["--color=0"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.NONE,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.INTERACTIVE,
#                 "terminal_theme": None,
#             },
#         ),
#         (
#             {
#                 "args": ["--color=1"],
#             },
#             {
#                 "color_support": yuio.color.ColorSupport.ANSI,
#                 "ostream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "istream_interactive_support": yuio.term.InteractiveSupport.NONE,
#                 "terminal_theme": None,
#             },
#         ),
#     ],
# )
# def test_capabilities_estimation_windows(kwargs, expected_term):
#     with mock_term_io(**kwargs) as streams:
#         ostream, istream = streams
#         term = yuio.term.get_term_from_stream(ostream, istream)
#         expected = yuio.term.Term(ostream, istream, **expected_term)
#         assert term == expected


@pytest.mark.parametrize(
    ("env_vars", "expected"),
    [
        ({"GITHUB_ACTIONS": ""}, yuio.color.ColorSupport.ANSI_TRUE),
        ({"TRAVIS": ""}, yuio.color.ColorSupport.ANSI),
        ({"CIRCLECI": ""}, yuio.color.ColorSupport.ANSI),
        ({"APPVEYOR": ""}, yuio.color.ColorSupport.ANSI),
        ({"GITLAB_CI": ""}, yuio.color.ColorSupport.ANSI),
        ({"BUILDKITE": ""}, yuio.color.ColorSupport.ANSI),
        ({"DRONE": ""}, yuio.color.ColorSupport.ANSI),
        ({"TEAMCITY_VERSION": "2023.1"}, yuio.color.ColorSupport.ANSI),
        ({}, yuio.color.ColorSupport.NONE),
        ({"PATH": "/usr/bin", "HOME": "/home/user"}, yuio.color.ColorSupport.NONE),
        (
            {"GITHUB_ACTIONS": "", "TRAVIS": ""},
            yuio.color.ColorSupport.ANSI_TRUE,
        ),
        ({"TRAVIS": "", "CIRCLECI": ""}, yuio.color.ColorSupport.ANSI),
        ({"CI": ""}, yuio.color.ColorSupport.NONE),
    ],
)
def test_detect_ci_color_support(env_vars, expected, monkeypatch: pytest.MonkeyPatch):
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    assert yuio.term.detect_ci_color_support() == expected
