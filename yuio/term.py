# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Querying terminal info and working with ANSI terminals.

This is a low-level module upon which :mod:`yuio.io` builds
its higher-level abstraction.


Detecting terminal capabilities
-------------------------------

Terminal capabilities are stored in a :class:`Term` object.

Usually, you don't need to query terminal capabilities yourself,
as you can use Yuio's global configuration from :mod:`yuio.io`
(see :func:`yuio.io.get_term`).

However, you can get a :class:`Term` object by using :func:`get_term_from_stream`:

.. autofunction:: get_term_from_stream

.. autoclass:: Term
   :members:

.. autoclass:: TerminalTheme
   :members:

.. autoclass:: Lightness
   :members:

.. autoclass:: InteractiveSupport
   :members:


Utilities
---------

.. autofunction:: detect_ci

.. autofunction:: detect_ci_color_support

"""

from __future__ import annotations

import contextlib
import enum
import locale
import os
import re
import shutil
import sys
from dataclasses import dataclass

import yuio
import yuio.color
from yuio import _typing as _t
from yuio.color import ColorSupport

__all__ = [
    "ColorSupport",
    "InteractiveSupport",
    "Lightness",
    "Term",
    "TerminalTheme",
    "detect_ci",
    "detect_ci_color_support",
    "get_term_from_stream",
]

T = _t.TypeVar("T")


class Lightness(enum.Enum):
    """
    Overall color theme of a terminal.

    Can help with deciding which colors to use when printing output.

    """

    UNKNOWN = enum.auto()
    """
    We couldn't determine terminal background, or it wasn't dark
    or bright enough to fall in one category or another.

    """

    DARK = enum.auto()
    """
    Terminal background is dark.

    """

    LIGHT = enum.auto()
    """
    Terminal background is light.

    """


class InteractiveSupport(enum.IntEnum):
    """
    Terminal's capability for rendering interactive widgets.

    """

    NONE = 0
    """
    Terminal can't render anything interactive.

    """

    MOVE_CURSOR = 1
    """
    Terminal can move cursor and erase lines.

    """

    FULL = 2
    """
    Terminal can process queries, enter ``CBREAK`` mode, etc.

    """


@dataclass(frozen=True, slots=True)
class TerminalTheme:
    """
    Colors and theme of the attached terminal.

    """

    background: yuio.color.ColorValue
    """
    Background color of a terminal.

    """

    foreground: yuio.color.ColorValue
    """
    Foreground color of a terminal.

    """

    black: yuio.color.ColorValue
    """
    Color value for the default "black" color.

    """

    red: yuio.color.ColorValue
    """
    Color value for the default "red" color.

    """

    green: yuio.color.ColorValue
    """
    Color value for the default "green" color.

    """

    yellow: yuio.color.ColorValue
    """
    Color value for the default "yellow" color.

    """

    blue: yuio.color.ColorValue
    """
    Color value for the default "blue" color.

    """

    magenta: yuio.color.ColorValue
    """
    Color value for the default "magenta" color.

    """

    cyan: yuio.color.ColorValue
    """
    Color value for the default "cyan" color.

    """

    white: yuio.color.ColorValue
    """
    Color value for the default "white" color.

    """

    lightness: Lightness
    """
    Overall color theme of a terminal, i.e. dark or light.

    """


@dataclass(frozen=True, slots=True)
class Term:
    """
    This class contains all info about what kinds of things the terminal
    supports. If available, it will also have info about terminal's theme,
    i.e. dark or light background, etc.

    """

    ostream: _t.TextIO
    """
    Terminal's output stream.

    """

    istream: _t.TextIO
    """
    Terminal's input stream.

    """

    color_support: ColorSupport = ColorSupport.NONE
    """
    Terminal's capability for coloring output.

    """

    interactive_support: InteractiveSupport = InteractiveSupport.NONE
    """
    Terminal's capability for rendering interactive widgets.

    """

    terminal_theme: TerminalTheme | None = None
    """
    Terminal's default foreground, background, and text colors.

    """

    @property
    def supports_colors(self) -> bool:
        """
        Return :data:`True` if terminal supports simple 8-bit color codes.

        """

        return self.color_support >= ColorSupport.ANSI

    @property
    def supports_colors_256(self) -> bool:
        """
        Return :data:`True` if terminal supports 256-encoded colors.

        """

        return self.color_support >= ColorSupport.ANSI_256

    @property
    def supports_colors_true(self) -> bool:
        """
        Return :data:`True` if terminal supports true colors.

        """

        return self.color_support >= ColorSupport.ANSI_TRUE

    @property
    def can_move_cursor(self) -> bool:
        """
        Return :data:`True` if terminal can move cursor and erase lines.

        """

        return (
            self.supports_colors
            and self.interactive_support >= InteractiveSupport.MOVE_CURSOR
        )

    @property
    def can_query_terminal(self) -> bool:
        """
        Return :data:`True` if terminal can process queries, enter ``CBREAK`` mode, etc.

        This is an alias to :attr:`~Term.is_fully_interactive`.

        """

        return self.is_fully_interactive

    @property
    def is_fully_interactive(self) -> bool:
        """
        Return :data:`True` if we're in a fully interactive environment.

        """

        return (
            self.supports_colors and self.interactive_support >= InteractiveSupport.FULL
        )

    @property
    def is_unicode(self) -> bool:
        encoding = (
            getattr(self.ostream, "encoding", None) or locale.getpreferredencoding()
        )
        return "utf" in encoding or "unicode" in encoding


_CI_ENV_VARS = [
    "TRAVIS",
    "CIRCLECI",
    "APPVEYOR",
    "GITLAB_CI",
    "BUILDKITE",
    "DRONE",
    "TEAMCITY_VERSION",
    "GITHUB_ACTIONS",
]


def get_term_from_stream(
    ostream: _t.TextIO, istream: _t.TextIO, /, *, query_terminal_theme: bool = True
) -> Term:
    """
    Query info about a terminal attached to the given stream.

    :param ostream:
        output stream.
    :param istream:
        input stream.
    :param query_terminal_theme:
        By default, this function queries background, foreground, and text colors
        of the terminal if ``ostream`` and ``istream`` are connected to a TTY.

        Set this parameter to :data:`False` to disable querying.

    """

    if "__YUIO_FORCE_FULL_TERM_SUPPORT" in os.environ:  # pragma: no cover
        # For building docs in github
        return Term(
            ostream=ostream,
            istream=istream,
            color_support=ColorSupport.ANSI_TRUE,
            interactive_support=InteractiveSupport.FULL,
        )

    # Note: we don't rely on argparse to parse out flags and send them to us
    # because these functions can be called before parsing arguments.
    if (
        "--no-color" in sys.argv
        or "--no-colors" in sys.argv
        or "--force-no-color" in sys.argv
        or "--force-no-colors" in sys.argv
        or "FORCE_NO_COLOR" in os.environ
        or "FORCE_NO_COLORS" in os.environ
    ):
        return Term(ostream, istream)

    term = os.environ.get("TERM", "").lower()
    colorterm = os.environ.get("COLORTERM", "").lower()

    has_interactive_output = _is_interactive_output(ostream)
    has_interactive_input = _is_interactive_input(istream)
    is_foreground = _is_foreground(ostream) and _is_foreground(istream)
    in_ci = detect_ci()
    color_support = ColorSupport.NONE
    if (
        "--force-color" in sys.argv
        or "--force-colors" in sys.argv
        or "FORCE_COLOR" in os.environ
        or "FORCE_COLORS" in os.environ
    ):
        color_support = ColorSupport.ANSI
    if has_interactive_output:
        if in_ci:
            color_support = detect_ci_color_support()
        elif os.name == "nt":
            if _enable_vt_processing(ostream, istream):
                color_support = ColorSupport.ANSI_TRUE
        elif colorterm in ("truecolor", "24bit") or term == "xterm-kitty":
            color_support = ColorSupport.ANSI_TRUE
        elif colorterm in ("yes", "true") or "256color" in term or term == "screen":
            if (
                os.name == "posix"
                and term == "xterm-256color"
                and shutil.which("wslinfo")
            ):
                color_support = ColorSupport.ANSI_TRUE
            else:
                color_support = ColorSupport.ANSI_256
        elif "linux" in term or "color" in term or "ansi" in term or "xterm" in term:
            color_support = ColorSupport.ANSI

    interactive_support = InteractiveSupport.NONE
    theme = None
    if is_foreground and color_support >= ColorSupport.ANSI and not in_ci:
        if has_interactive_output and has_interactive_input:
            interactive_support = InteractiveSupport.FULL
            if (
                query_terminal_theme
                and color_support >= ColorSupport.ANSI_256
                and "YUIO_DISABLE_OSC_QUERIES" not in os.environ
            ):
                theme = _get_standard_colors(ostream, istream)
        else:
            interactive_support = InteractiveSupport.MOVE_CURSOR

    return Term(
        ostream=ostream,
        istream=istream,
        color_support=color_support,
        interactive_support=interactive_support,
        terminal_theme=theme,
    )


def detect_ci() -> bool:
    """
    Scan environment variables to detect if we're in a known CI environment.

    """

    return "CI" in os.environ or any(ci in os.environ for ci in _CI_ENV_VARS)


def detect_ci_color_support() -> ColorSupport:
    """
    Scan environment variables to detect an appropriate level of color support
    of a CI environment.

    If we're not in CI, return :attr:`ColorSupport.NONE`.

    """

    if "GITHUB_ACTIONS" in os.environ:
        return ColorSupport.ANSI_TRUE
    elif any(ci in os.environ for ci in _CI_ENV_VARS):
        return ColorSupport.ANSI
    else:
        return ColorSupport.NONE


def _get_standard_colors(
    ostream: _t.TextIO, istream: _t.TextIO
) -> TerminalTheme | None:
    try:
        query = "\x1b]10;?\x1b\\\x1b]11;?\x1b\\" + "".join(
            [f"\x1b]4;{i};?\x1b\\" for i in range(8)]
        )
        response = _query_term(ostream, istream, query)
        if not response:
            return None

        # Deal with foreground color.

        match = re.match(
            r"^\x1b]10;rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})(?:\x1b\\|\a)",
            response,
            re.IGNORECASE,
        )
        if match is None:  # pragma: no cover
            return None

        r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups())
        foreground = yuio.color.ColorValue.from_rgb(r, g, b)

        response = response[match.end() :]

        # Deal with background color.

        match = re.match(
            r"^\x1b]11;rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})(?:\x1b\\|\a)",
            response,
            re.IGNORECASE,
        )
        if match is None:  # pragma: no cover
            return None

        r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups())
        background = yuio.color.ColorValue.from_rgb(r, g, b)
        luma = (0.2627 * r + 0.6780 * g + 0.0593 * b) / 256

        if luma <= 0.2:
            lightness = Lightness.DARK
        elif luma >= 0.85:
            lightness = Lightness.LIGHT
        else:
            lightness = Lightness.UNKNOWN

        response = response[match.end() :]

        # Deal with other colors

        colors = {}

        while response:
            match = re.match(
                r"^\x1b]4;(\d+);rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})(?:\x1b\\|\a)",
                response,
                re.IGNORECASE,
            )
            if match is None:  # pragma: no cover
                return None

            c = int(match.group(1))
            r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups()[1:])
            colors[c] = yuio.color.ColorValue.from_rgb(r, g, b)

            response = response[match.end() :]

        if set(colors.keys()) != {0, 1, 2, 3, 4, 5, 6, 7}:  # pragma: no cover
            return None

        # return colors
        return TerminalTheme(
            background=background,
            foreground=foreground,
            black=colors[0],
            red=colors[1],
            green=colors[2],
            yellow=colors[3],
            blue=colors[4],
            magenta=colors[5],
            cyan=colors[6],
            white=colors[7],
            lightness=lightness,
        )

    except Exception:  # pragma: no cover
        return None


def _query_term(ostream: _t.TextIO, istream: _t.TextIO, query: str) -> str | None:
    try:
        with _enter_raw_mode(ostream, istream):
            # Lock the keyboard.
            ostream.write("\x1b[2h")
            ostream.flush()
            _flush_input_buffer(ostream, istream)

            # It is important that we unlock keyboard before exiting `cbreak`,
            # hence the nested `try`.
            try:
                # Append a DA1 query, as virtually all terminals support it.
                ostream.write(query + "\x1b[c")
                ostream.flush()

                buf = _read_keycode(ostream, istream)
                if not buf.startswith("\x1b"):
                    yuio._logger.warning("_query_term invalid response: %r", buf)
                    return None

                # Read till we find a DA1 response.
                while not re.search(r"\x1b\[\?.*?c", buf):
                    buf += _read_keycode(ostream, istream)

                return buf[: buf.index("\x1b[?")]
            finally:
                _flush_input_buffer(ostream, istream)

                # Release the keyboard.
                ostream.write("\x1b[2i")
                ostream.flush()
    except Exception:  # pragma: no cover
        yuio._logger.warning("_query_term error", exc_info=True)
        return None


def _is_tty(stream: _t.TextIO | None) -> bool:
    try:
        return stream is not None and stream.isatty()
    except Exception:  # pragma: no cover
        return False


if os.name == "posix":

    def _is_foreground(stream: _t.TextIO | None) -> bool:
        try:
            return stream is not None and os.getpgrp() == os.tcgetpgrp(stream.fileno())
        except Exception:  # pragma: no cover
            return False

elif os.name == "nt":

    def _is_foreground(stream: _t.TextIO | None) -> bool:
        return True

else:

    def _is_foreground(stream: _t.TextIO | None) -> bool:
        return False


def _is_interactive_input(stream: _t.TextIO | None) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.readable()
    except Exception:  # pragma: no cover
        return False


def _is_interactive_output(stream: _t.TextIO | None) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.writable()
    except Exception:  # pragma: no cover
        return False


# Platform-specific code for working with terminals.
if os.name == "posix":
    import select
    import termios
    import tty

    @contextlib.contextmanager
    def _enter_raw_mode(
        ostream: _t.TextIO,
        istream: _t.TextIO,
        bracketed_paste: bool = False,
        modify_keyboard: bool = False,
    ):
        prev_mode = termios.tcgetattr(istream)
        tty.setcbreak(istream, termios.TCSANOW)

        prologue = []
        if bracketed_paste:
            prologue.append("\x1b[?2004h")
        if modify_keyboard:
            prologue.append("\033[>4;2m")
        if prologue:
            ostream.write("".join(prologue))
            ostream.flush()

        try:
            yield
        finally:
            epilogue = []
            if bracketed_paste:
                epilogue.append("\x1b[?2004l")
            if modify_keyboard:
                epilogue.append("\033[>4m")
            if epilogue:
                ostream.write("".join(epilogue))
                ostream.flush()
            termios.tcsetattr(istream, termios.TCSAFLUSH, prev_mode)

    def _read_keycode(ostream: _t.TextIO, istream: _t.TextIO) -> str:
        key = os.read(istream.fileno(), 128)
        while bool(select.select([istream], [], [], 0)[0]):
            key += os.read(istream.fileno(), 128)

        return key.decode(istream.encoding, errors="replace")

    def _flush_input_buffer(ostream: _t.TextIO, istream: _t.TextIO):
        while bool(select.select([istream], [], [], 0.001)[0]):
            os.read(istream.fileno(), 1)

    def _enable_vt_processing(ostream: _t.TextIO, istream: _t.TextIO) -> bool:
        return False  # This is a windows functionality

elif os.name == "nt":
    import ctypes
    import ctypes.wintypes
    import msvcrt

    _FlushConsoleInputBuffer = ctypes.windll.kernel32.FlushConsoleInputBuffer
    _FlushConsoleInputBuffer.argtypes = [ctypes.wintypes.HANDLE]
    _FlushConsoleInputBuffer.restype = ctypes.wintypes.BOOL

    _GetConsoleMode = ctypes.windll.kernel32.GetConsoleMode
    _GetConsoleMode.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.LPDWORD]
    _GetConsoleMode.restype = ctypes.wintypes.BOOL

    _SetConsoleMode = ctypes.windll.kernel32.SetConsoleMode
    _SetConsoleMode.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    _SetConsoleMode.restype = ctypes.wintypes.BOOL

    _ReadConsoleW = ctypes.windll.kernel32.ReadConsoleW
    _ReadConsoleW.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.LPVOID,
        ctypes.wintypes.DWORD,
        ctypes.wintypes.LPDWORD,
        ctypes.wintypes.LPVOID,
    ]
    _ReadConsoleW.restype = ctypes.wintypes.BOOL

    _ENABLE_PROCESSED_OUTPUT = 0x0001
    _ENABLE_WRAP_AT_EOL_OUTPUT = 0x0002
    _ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    _ENABLE_VIRTUAL_TERMINAL_INPUT = 0x0200

    if sys.__stdin__ is not None:  # TODO: don't rely on sys.__stdin__?
        _ISTREAM_HANDLE = msvcrt.get_osfhandle(sys.__stdin__.fileno())
    else:
        _ISTREAM_HANDLE = None

    @contextlib.contextmanager
    def _enter_raw_mode(
        ostream: _t.TextIO,
        istream: _t.TextIO,
        bracketed_paste: bool = False,
        modify_keyboard: bool = False,
    ):
        assert _ISTREAM_HANDLE is not None

        mode = ctypes.wintypes.DWORD()
        success = _GetConsoleMode(_ISTREAM_HANDLE, ctypes.byref(mode))
        if not success:
            raise ctypes.WinError()
        success = _SetConsoleMode(_ISTREAM_HANDLE, _ENABLE_VIRTUAL_TERMINAL_INPUT)
        if not success:
            raise ctypes.WinError()

        try:
            yield
        finally:
            success = _SetConsoleMode(_ISTREAM_HANDLE, mode)
            if not success:
                raise ctypes.WinError()

    def _read_keycode(ostream: _t.TextIO, istream: _t.TextIO) -> str:
        assert _ISTREAM_HANDLE is not None

        CHAR16 = ctypes.wintypes.WCHAR * 16

        n_read = ctypes.wintypes.DWORD()
        buffer = CHAR16()

        success = _ReadConsoleW(
            _ISTREAM_HANDLE,
            ctypes.byref(buffer),
            16,
            ctypes.byref(n_read),
            0,
        )
        if not success:
            raise ctypes.WinError()

        return buffer.value

    def _flush_input_buffer(ostream: _t.TextIO, istream: _t.TextIO):
        assert _ISTREAM_HANDLE is not None

        success = _FlushConsoleInputBuffer(_ISTREAM_HANDLE)
        if not success:
            raise ctypes.WinError()

    def _enable_vt_processing(ostream: _t.TextIO, istream: _t.TextIO) -> bool:
        try:
            version = sys.getwindowsversion()
            if version.major < 10 or version.build < 14931:
                return False

            handle = msvcrt.get_osfhandle(ostream.fileno())
            return bool(
                _SetConsoleMode(
                    handle,
                    _ENABLE_PROCESSED_OUTPUT
                    | _ENABLE_WRAP_AT_EOL_OUTPUT
                    | _ENABLE_VIRTUAL_TERMINAL_PROCESSING,
                )
            )
        except Exception:  # pragma: no cover
            return False

else:

    @contextlib.contextmanager
    def _enter_raw_mode(
        ostream: _t.TextIO,
        istream: _t.TextIO,
        bracketed_paste: bool = False,
        modify_keyboard: bool = False,
    ):
        raise OSError("not supported")
        yield

    def _read_keycode(ostream: _t.TextIO, istream: _t.TextIO) -> str:
        raise OSError("not supported")

    def _flush_input_buffer(ostream: _t.TextIO, istream: _t.TextIO):
        raise OSError("not supported")

    def _enable_vt_processing(ostream: _t.TextIO, istream: _t.TextIO) -> bool:
        raise OSError("not supported")
