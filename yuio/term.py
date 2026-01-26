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

.. autofunction:: get_tty

.. autoclass:: Term
   :members:

.. autoclass:: TerminalTheme
   :members:

.. autoclass:: Lightness
   :members:


Utilities
---------

.. autofunction:: stream_is_unicode

.. autofunction:: get_tty_size

.. autofunction:: detect_ci

.. autofunction:: detect_ci_color_support


Re-imports
----------

.. type:: ColorSupport
    :no-index:

    Alias of :obj:`yuio.color.ColorSupport`.

"""

from __future__ import annotations

import atexit
import contextlib
import dataclasses
import enum
import io
import locale
import os
import re
import shutil
import sys
import threading
from dataclasses import dataclass

import yuio
import yuio.color
from yuio.color import ColorSupport
from yuio.util import ClosedIO as _ClosedIO

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "ColorSupport",
    "Lightness",
    "Term",
    "TerminalTheme",
    "detect_ci",
    "detect_ci_color_support",
    "get_term_from_stream",
    "get_tty",
    "get_tty_size",
    "stream_is_unicode",
]

T = _t.TypeVar("T")


_LOCK = threading.Lock()

# These variables are set in `_prepare_tty`.
_TTY_SETUP_PERFORMED: bool = False
_TTY_OUTPUT: _t.TextIO | None
_TTY_INPUT: _t.TextIO | None
_TERMINAL_THEME: TerminalTheme | None
_EXPLICIT_COLOR_SUPPORT: ColorSupport | bool | None
_COLOR_SUPPORT: ColorSupport


# Redefine canonical streams so that we don't monkeypatch `sys.__std*__` in tests.
__stdin = sys.__stdin__
__stdout = sys.__stdout__
__stderr = sys.__stderr__


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

    bright_black: yuio.color.ColorValue
    """
    Color value for the default "bright black" color.

    """

    red: yuio.color.ColorValue
    """
    Color value for the default "red" color.

    """

    bright_red: yuio.color.ColorValue
    """
    Color value for the default "bright red" color.

    """

    green: yuio.color.ColorValue
    """
    Color value for the default "green" color.

    """

    bright_green: yuio.color.ColorValue
    """
    Color value for the default "bright green" color.

    """

    yellow: yuio.color.ColorValue
    """
    Color value for the default "yellow" color.

    """

    bright_yellow: yuio.color.ColorValue
    """
    Color value for the default "bright yellow" color.

    """

    blue: yuio.color.ColorValue
    """
    Color value for the default "blue" color.

    """

    bright_blue: yuio.color.ColorValue
    """
    Color value for the default "bright blue" color.

    """

    magenta: yuio.color.ColorValue
    """
    Color value for the default "magenta" color.

    """

    bright_magenta: yuio.color.ColorValue
    """
    Color value for the default "bright magenta" color.

    """

    cyan: yuio.color.ColorValue
    """
    Color value for the default "cyan" color.

    """

    bright_cyan: yuio.color.ColorValue
    """
    Color value for the default "bright cyan" color.

    """

    white: yuio.color.ColorValue
    """
    Color value for the default "white" color.

    """

    bright_white: yuio.color.ColorValue
    """
    Color value for the default "bright white" color.

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

    color_support: ColorSupport = dataclasses.field(
        default=ColorSupport.NONE, kw_only=True
    )
    """
    Terminal's capability for coloring output.

    """

    ostream_is_tty: bool = dataclasses.field(default=False, kw_only=True)
    """
    Output is connecter to a terminal, and we're not in CI.

    Note that output being connected to a TTY doesn't mean that it's interactive:
    this process can be in background.

    """

    istream_is_tty: bool = dataclasses.field(default=False, kw_only=True)
    """
    Output is connecter to a terminal, and we're not in CI.

    Note that output being connected to a TTY doesn't mean that it's interactive:
    this process can be in background.

    """

    terminal_theme: TerminalTheme | None = dataclasses.field(default=None, kw_only=True)
    """
    Terminal's default foreground, background, and text colors.

    """

    is_unicode: bool = dataclasses.field(default=False, kw_only=True)
    """
    Terminal's output supports unicode characters.

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
    def is_tty(self) -> bool:
        """
        Return :data:`True` if input and output are connected to a TTY. In this mode
        we can interact with the user by writing and reading lines of text.

        """

        return self.istream_is_tty and self.ostream_is_tty

    @property
    def can_run_widgets(self) -> bool:
        """
        Return :data:`True` if input and output are interactive and colors
        are supported. In this mode we can run interactive widgets.

        """

        return self.color_support >= ColorSupport.ANSI and self.is_tty

    @staticmethod
    def make_dummy(is_unicode: bool = True) -> Term:
        """
        Make a dummy terminal with closed streams and no capabilities.

        """

        stream = io.StringIO()
        stream.close()
        return Term(
            istream=_ClosedIO(),
            ostream=_ClosedIO(),
            is_unicode=is_unicode,
        )


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


def stream_is_unicode(stream: _t.TextIO, /) -> bool:
    """
    Determine of stream's encoding is some version of unicode.

    """

    encoding = getattr(stream, "encoding", None) or locale.getpreferredencoding() or ""
    encoding = encoding.casefold()
    return "utf" in encoding or "unicode" in encoding


def get_tty_size(fallback: tuple[int, int] = (80, 24)):
    """
    Like :func:`shutil.get_terminal_size`, but uses TTY stream if it's available.

    :param fallback:
        tuple with width and height that will be used if query fails.

    """

    _prepare_tty()

    try:
        columns = int(os.environ["COLUMNS"])
    except (KeyError, ValueError):
        columns = 0

    try:
        lines = int(os.environ["LINES"])
    except (KeyError, ValueError):
        lines = 0

    if columns <= 0 or lines <= 0:
        try:
            size = os.get_terminal_size(_TTY_OUTPUT.fileno())  # type: ignore
        except (AttributeError, ValueError, OSError):
            # stream is closed, detached, or not a terminal, or
            # os.get_tty_size() is unsupported
            size = os.terminal_size(fallback)
        if columns <= 0:
            columns = size.columns or fallback[0]
        if lines <= 0:
            lines = size.lines or fallback[1]

    return os.terminal_size((columns, lines))


def detect_ci() -> bool:
    """
    Scan environment variables to detect if we're in a known CI environment.

    """

    return "CI" in os.environ or any(ci in os.environ for ci in _CI_ENV_VARS)


def detect_ci_color_support() -> ColorSupport:
    """
    Scan environment variables to detect an appropriate level of color support
    of a CI environment.

    If we're not in CI, return :attr:`ColorSupport.NONE <yuio.color.ColorSupport.NONE>`.

    """

    if "GITHUB_ACTIONS" in os.environ:
        return ColorSupport.ANSI_TRUE
    elif any(ci in os.environ for ci in _CI_ENV_VARS):
        return ColorSupport.ANSI
    else:
        return ColorSupport.NONE


def get_tty() -> Term:
    """
    Query info about TTY.

    On Unix, this returns terminal connected to ``/dev/tty``. On Windows, this returns
    terminal connected to ``CONIN$``/``CONOUT$``.

    If opening any of these fails, returns :class:`Term` with ``stdin``/``stdout``
    as a fallback.

    .. note::

        Prefer using ``stderr`` for normal IO: your users expect to be able to redirect
        messages from your program.

        Only use ``/dev/tty`` for querying passwords or other things that must not
        be redirected.

    """

    _prepare_tty()
    ostream = _TTY_OUTPUT or __stderr
    istream = _TTY_INPUT or __stdin
    assert ostream is not None
    assert istream is not None
    return get_term_from_stream(ostream, istream, allow_env_overrides=True)


def get_term_from_stream(
    ostream: _t.TextIO,
    istream: _t.TextIO | None = None,
    /,
    *,
    allow_env_overrides: bool = False,
) -> Term:
    """
    Query info about a terminal attached to the given stream.

    :param ostream:
        output stream.
    :param istream:
        input stream. If not given, widgets will not work with this terminal.
    :param allow_env_overrides:
        honor environment variables and CLI flags when determining capabilities
        of streams.

    """

    is_unicode = stream_is_unicode(ostream)

    if (
        # For building docs in github.
        "YUIO_FORCE_FULL_TERM_SUPPORT" in os.environ and istream is not None
    ):  # pragma: no cover
        return Term(
            ostream=ostream,
            istream=istream,
            color_support=ColorSupport.ANSI_TRUE,
            ostream_is_tty=True,
            istream_is_tty=True,
            is_unicode=is_unicode,
        )

    _prepare_tty()

    output_is_tty = _output_is_tty(ostream)
    input_is_tty = _input_is_tty(istream)
    in_ci = detect_ci()

    # Detect colors.
    if output_is_tty or (_EXPLICIT_COLOR_SUPPORT is not None and allow_env_overrides):
        color_support = _COLOR_SUPPORT
    else:
        color_support = ColorSupport.NONE

    if istream is None:
        istream = _ClosedIO()

    return Term(
        ostream=ostream,
        istream=istream,
        color_support=color_support,
        ostream_is_tty=output_is_tty and not in_ci,
        istream_is_tty=input_is_tty and not in_ci,
        terminal_theme=_TERMINAL_THEME,
        is_unicode=is_unicode,
    )


def _prepare_tty():
    if not _TTY_SETUP_PERFORMED:
        with _LOCK:
            if not _TTY_SETUP_PERFORMED:
                _do_prepare_tty()


def _do_prepare_tty():
    global \
        _TTY_SETUP_PERFORMED, \
        _TERMINAL_THEME, \
        _EXPLICIT_COLOR_SUPPORT, \
        _COLOR_SUPPORT

    _find_tty()

    _TTY_SETUP_PERFORMED = True

    # Theme is `None` for now, will query it later.
    _TERMINAL_THEME = None

    # Find out if user specified `--color` or `FORCE_COLOR`.
    _EXPLICIT_COLOR_SUPPORT = _detect_explicit_color_settings()

    # Check user preferences.
    if _EXPLICIT_COLOR_SUPPORT is False:
        # Colors disabled, nothing more to do.
        _COLOR_SUPPORT = ColorSupport.NONE
        return
    elif _EXPLICIT_COLOR_SUPPORT is True:
        # At least ANSI. Might improve later.
        _COLOR_SUPPORT = max(ColorSupport.ANSI, _detect_color_support_from_env())
    elif _EXPLICIT_COLOR_SUPPORT is None:
        # At least NONE. Might improve later.
        _COLOR_SUPPORT = _detect_color_support_from_env()
    else:
        # Exact color support is given.
        _COLOR_SUPPORT = _EXPLICIT_COLOR_SUPPORT

    if _TTY_OUTPUT is None:
        # Can't find attached TTY output, hence can't improve color support.
        return

    if os.name == "nt":
        # Try enabling true colors.
        if _enable_vt_processing(_TTY_OUTPUT):
            # Success, can improve color support.
            if _EXPLICIT_COLOR_SUPPORT is None or _EXPLICIT_COLOR_SUPPORT is True:
                _COLOR_SUPPORT = ColorSupport.ANSI_TRUE
        else:
            # Failure, this version of Windows does not support colors.
            return

    if _TTY_INPUT is None:
        # Can't find attached TTY input, hence can't improve color support.
        return

    if not _is_foreground(_TTY_OUTPUT) or not _is_foreground(_TTY_INPUT):
        # We're not a foreground process, we won't be able to fetch colors.
        return
    if detect_ci():
        # We're in CI, we won't be able to fetch colors.
        return
    if not _is_tty(__stdin):
        # We don't want to query colors if our stdin is redirected: this is a sign
        # that this program runs in some sort of a pipeline, and multiple instances
        # of it might run at the same time. If this happens, several processes/threads
        # can interact with the same TTY, leading to garbled output.
        return

    if _COLOR_SUPPORT >= ColorSupport.ANSI:
        # We were able to find TTY, and colors are supported.
        # Try fetching terminal theme.
        _TERMINAL_THEME = _get_standard_colors(_TTY_OUTPUT, _TTY_INPUT)


def _find_tty():
    global _TTY_OUTPUT, _TTY_INPUT

    _TTY_OUTPUT = _TTY_INPUT = None

    closer = contextlib.ExitStack()
    try:
        if os.name == "nt":
            file_io_in = io._WindowsConsoleIO("CONIN$", "r")  # type: ignore
            tty_in = closer.enter_context(
                io.TextIOWrapper(file_io_in, encoding="utf-8")
            )
            file_io_out = io._WindowsConsoleIO("CONOUT$", "w")  # type: ignore
            tty_out = closer.enter_context(
                io.TextIOWrapper(file_io_out, encoding="utf-8")
            )
        else:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
            file_io = io.FileIO(fd, "w+")
            file_io.name = "/dev/tty"
            tty_in = tty_out = closer.enter_context(io.TextIOWrapper(file_io))
    except (OSError, AttributeError):
        closer.close()
    except:
        closer.close()
        raise
    else:
        atexit.register(closer.close)
        _TTY_INPUT = tty_in
        _TTY_OUTPUT = tty_out
        return

    for stream in (__stderr, __stdout):
        if stream is not None and _output_is_tty(stream):
            _TTY_OUTPUT = stream
            break
    if __stdin is not None and _input_is_tty(__stdin):
        _TTY_INPUT = __stdin


def _get_standard_colors(
    ostream: _t.TextIO, istream: _t.TextIO
) -> TerminalTheme | None:
    if "YUIO_DISABLE_OSC_QUERIES" in os.environ:
        return None

    try:
        query = "\x1b]10;?\x1b\\\x1b]11;?\x1b\\" + "".join(
            [f"\x1b]4;{i};?\x1b\\" for i in range(16)]
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

        for k in range(8):
            if k not in colors:
                return None

        # return colors
        return TerminalTheme(
            background=background,
            foreground=foreground,
            black=colors[0],
            bright_black=colors.get(8 + 0, colors[0]),
            red=colors[1],
            bright_red=colors.get(8 + 1, colors[1]),
            green=colors[2],
            bright_green=colors.get(8 + 2, colors[2]),
            yellow=colors[3],
            bright_yellow=colors.get(8 + 3, colors[3]),
            blue=colors[4],
            bright_blue=colors.get(8 + 4, colors[4]),
            magenta=colors[5],
            bright_magenta=colors.get(8 + 5, colors[5]),
            cyan=colors[6],
            bright_cyan=colors.get(8 + 6, colors[6]),
            white=colors[7],
            bright_white=colors.get(8 + 7, colors[7]),
            lightness=lightness,
        )

    except Exception:  # pragma: no cover
        return None


def _query_term(ostream: _t.TextIO, istream: _t.TextIO, query: str) -> str | None:
    try:
        # Lock the keyboard.
        ostream.write("\x1b[2h")
        ostream.flush()

        with _enter_raw_mode(ostream, istream):
            _flush_input_buffer(ostream, istream)

            # It is important that we unlock keyboard before exiting `cbreak`,
            # hence the nested `try`.
            try:
                # Append a DA1 query, as virtually all terminals support it.
                ostream.write(query + "\x1b[c")
                ostream.flush()

                buf = _read_keycode(ostream, istream, timeout=0.250)
                if not buf.startswith("\x1b"):
                    yuio._logger.warning("_query_term invalid response: %r", buf)
                    return None

                # Read till we find a DA1 response.
                while not re.search(r"\x1b\[\?.*?c", buf):
                    buf += _read_keycode(ostream, istream, timeout=0.250)

                return buf[: buf.index("\x1b[?")]
            finally:
                _flush_input_buffer(ostream, istream)

                # Release the keyboard.
                ostream.write("\x1b[2i")
                ostream.flush()
    except Exception:  # pragma: no cover
        yuio._logger.warning("_query_term error", exc_info=True)
        return None
    finally:
        # Release the keyboard.
        ostream.write("\x1b[2i")
        ostream.flush()


def _detect_explicit_color_settings() -> ColorSupport | bool | None:
    color_support = None

    if "FORCE_COLOR" in os.environ:
        color_support = True

    if "NO_COLOR" in os.environ or "FORCE_NO_COLOR" in os.environ:
        color_support = False

    # Note: we don't rely on argparse to parse flags and send them to us
    # because these functions can be called before parsing arguments.
    for arg in sys.argv[1:]:
        if arg in ("--color", "--force-color"):
            color_support = True
        elif arg in ("--no-color", "--force-no-color"):
            color_support = False
        elif arg.startswith(("--color=", "--colors=")):
            value = (
                arg.split("=", maxsplit=1)[1]
                .replace("_", "")
                .replace("-", "")
                .casefold()
            )
            if value in ["1", "yes", "true"]:
                color_support = True
            elif value in ["0", "no", "false"]:
                color_support = False
            elif value == "ansi":
                color_support = ColorSupport.ANSI
            elif value == "ansi256":
                color_support = ColorSupport.ANSI_256
            elif value == "ansitrue":
                color_support = ColorSupport.ANSI_TRUE

    return color_support


def _detect_color_support_from_env() -> ColorSupport:
    term = os.environ.get("TERM", "").lower()
    colorterm = os.environ.get("COLORTERM", "").lower()

    if detect_ci():
        return detect_ci_color_support()
    elif os.name == "nt":
        return ColorSupport.NONE
    elif colorterm in ("truecolor", "24bit") or term == "xterm-kitty":
        return ColorSupport.ANSI_TRUE
    elif colorterm in ("yes", "true") or "256color" in term or term == "screen":
        if os.name == "posix" and term == "xterm-256color" and shutil.which("wslinfo"):
            return ColorSupport.ANSI_TRUE
        else:
            return ColorSupport.ANSI_256
    elif "linux" in term or "color" in term or "ansi" in term or "xterm" in term:
        return ColorSupport.ANSI

    return ColorSupport.NONE


def _is_tty(stream: _t.TextIO | None) -> bool:
    try:
        return stream is not None and stream.isatty()
    except Exception:  # pragma: no cover
        return False


def _input_is_tty(stream: _t.TextIO | None) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.readable()
    except Exception:  # pragma: no cover
        return False


def _output_is_tty(stream: _t.TextIO | None) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.writable()
    except Exception:  # pragma: no cover
        return False


@contextlib.contextmanager
def _modify_keyboard(
    ostream: _t.TextIO,
    bracketed_paste: bool = False,
    modify_keyboard: bool = False,
):
    prologue = []
    if bracketed_paste:
        prologue.append("\x1b[?2004h")
    if modify_keyboard:
        prologue.append("\x1b[>1u")
    if prologue:
        ostream.write("".join(prologue))
        ostream.flush()
    try:
        yield
    finally:
        epilog = []
        if bracketed_paste:
            epilog.append("\x1b[?2004l")
        epilog.append("\x1b[<u")
        if epilog:
            ostream.write("".join(epilog))
            ostream.flush()


# Platform-specific code for working with terminals.
if os.name == "posix":
    import select
    import signal
    import termios
    import tty

    def _is_foreground(stream: _t.TextIO | None) -> bool:
        try:
            return stream is not None and os.getpgrp() == os.tcgetpgrp(stream.fileno())
        except Exception:  # pragma: no cover
            return False

    @contextlib.contextmanager
    def _enter_raw_mode(
        ostream: _t.TextIO,
        istream: _t.TextIO,
        bracketed_paste: bool = False,
        modify_keyboard: bool = False,
    ):
        prev_mode = termios.tcgetattr(istream)
        new_mode = prev_mode.copy()
        new_mode[tty.LFLAG] &= ~(
            termios.ECHO  # Don't print back what user types.
            | termios.ICANON  # Disable line editing.
            | termios.ISIG  # Disable signals on C-c and C-z.
        )
        new_mode[tty.CC] = new_mode[tty.CC].copy()
        new_mode[tty.CC][termios.VMIN] = 1
        new_mode[tty.CC][termios.VTIME] = 0
        termios.tcsetattr(istream, termios.TCSAFLUSH, new_mode)

        try:
            with _modify_keyboard(ostream, bracketed_paste, modify_keyboard):
                yield
        finally:
            termios.tcsetattr(istream, termios.TCSAFLUSH, prev_mode)

    def _read_keycode(
        ostream: _t.TextIO, istream: _t.TextIO, timeout: float = 0
    ) -> str:
        if timeout and not bool(select.select([istream], [], [], timeout)[0]):
            raise TimeoutError()
        key = os.read(istream.fileno(), 128)
        while bool(select.select([istream], [], [], 0)[0]):
            key += os.read(istream.fileno(), 128)

        return key.decode(istream.encoding, errors="replace")

    def _flush_input_buffer(ostream: _t.TextIO, istream: _t.TextIO):
        pass

    def _enable_vt_processing(ostream: _t.TextIO) -> bool:
        return False  # This is a windows functionality

    def _pause():
        os.kill(os.getpid(), signal.SIGTSTP)

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

    _GetConsoleWindow = ctypes.windll.kernel32.GetConsoleWindow
    _GetConsoleWindow.argtypes = []
    _GetConsoleWindow.restype = ctypes.wintypes.HWND

    _IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    _IsWindowVisible.argtypes = [ctypes.wintypes.HWND]
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

    _ISTREAM_HANDLE = None

    def _is_foreground(stream: _t.TextIO | None) -> bool:
        window = _GetConsoleWindow()
        if not window:
            return False
        return _IsWindowVisible(window)

    @contextlib.contextmanager
    def _enter_raw_mode(
        ostream: _t.TextIO,
        istream: _t.TextIO,
        bracketed_paste: bool = False,
        modify_keyboard: bool = False,
    ):
        global _ISTREAM_HANDLE

        if _ISTREAM_HANDLE is None:
            _prepare_tty()
            _ISTREAM_HANDLE = msvcrt.get_osfhandle((_TTY_INPUT or __stdin).fileno())  # type: ignore

        mode = ctypes.wintypes.DWORD()
        success = _GetConsoleMode(_ISTREAM_HANDLE, ctypes.byref(mode))
        if not success:
            raise ctypes.WinError()
        success = _SetConsoleMode(_ISTREAM_HANDLE, _ENABLE_VIRTUAL_TERMINAL_INPUT)
        if not success:
            raise ctypes.WinError()

        try:
            with _modify_keyboard(ostream, bracketed_paste, modify_keyboard):
                yield
        finally:
            success = _SetConsoleMode(_ISTREAM_HANDLE, mode)
            if not success:
                raise ctypes.WinError()

    def _read_keycode(
        ostream: _t.TextIO, istream: _t.TextIO, timeout: float = 0
    ) -> str:
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

    def _enable_vt_processing(ostream: _t.TextIO) -> bool:
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

    def _pause():
        pass

else:  # pragma: no cover

    def _is_foreground(stream: _t.TextIO | None) -> bool:
        return False

    @contextlib.contextmanager
    def _enter_raw_mode(
        ostream: _t.TextIO,
        istream: _t.TextIO,
        bracketed_paste: bool = False,
        modify_keyboard: bool = False,
    ):
        raise OSError("not supported")
        yield

    def _read_keycode(
        ostream: _t.TextIO, istream: _t.TextIO, timeout: float = 0
    ) -> str:
        raise OSError("not supported")

    def _flush_input_buffer(ostream: _t.TextIO, istream: _t.TextIO):
        raise OSError("not supported")

    def _enable_vt_processing(ostream: _t.TextIO) -> bool:
        raise OSError("not supported")

    def _pause():
        raise OSError("not supported")
