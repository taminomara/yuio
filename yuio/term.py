# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Everything to do with terminal output: detecting terminal capabilities,
working with colors and themes, formatting text.

This is a low-level API module, upon which :mod:`yuio.io` builds
its higher-level abstraction.


Detecting terminal capabilities
-------------------------------

Terminal capabilities are stored in a :class:`Term` object.

Usually, you don't need to query terminal capabilities yourself,
as you can use Yuio's global configuration from :mod:`yuio.io`
(see :func:`yuio.io.get_term`).

However, you can get a :class:`Term` object by using :func:`get_term_from_stream`:

.. autofunction:: get_term_from_stream

:class:`Term` contains all info about what kinds of things the terminal
supports. If available, it will also have info about terminal's theme,
i.e. dark or light background, etc:

.. autoclass:: Term
   :members:

.. autoclass:: Lightness
   :members:

.. autoclass:: ColorSupport
   :members:

.. autoclass:: InteractiveSupport
   :members:

.. autoclass:: TerminalColors
   :members:


Working with colors
-------------------

Text background and foreground color, as well as its style, is defined
by the :class:`Color` class. It stores RGB components and ANSI escape codes
for every aspect of text presentation:

.. autoclass:: Color
   :members:

A single color value is stored in the :class:`ColorValue` class.
Usually you don't need to use these directly, as you will be working
with :class:`Color` instances. Nevertheless, you can operate individual
colors should you need such thing:

.. autoclass:: ColorValue
   :members:


Coloring and formatting text
----------------------------

The higher-level :mod:`io` module uses strings with xml-like color
tags to transfer information about line formatting. Here, on the lower level,
these strings are parsed and transformed into :class:`ColorizedString`:

.. autoclass:: ColorizedString
   :members:

.. autodata:: RawString

.. autodata:: AnyString

.. autoclass:: NoWrap

.. autoclass:: Esc


Utilities
---------

.. autofunction:: line_width

"""

import colorsys
import contextlib
import dataclasses
import enum
import functools
import os
import re
import sys
import unicodedata
from dataclasses import dataclass

import yuio
from yuio import _typing as _t

T = _t.TypeVar("T")


class Lightness(enum.Enum):
    """Overall color theme of a terminal.

    Can help with deciding which colors to use when printing output.

    """

    #: We couldn't determine terminal background, or it wasn't dark
    #: or bright enough to fall in one category or another.
    UNKNOWN = enum.auto()

    #: Terminal background is dark.
    DARK = enum.auto()

    #: Terminal background is light.
    LIGHT = enum.auto()


class ColorSupport(enum.IntEnum):
    """Terminal's capability for coloring output."""

    #: Color codes are not supported.
    NONE = 0

    #: Only simple 8-bit color codes are supported.
    ANSI = 1

    #: 256-encoded colors are supported.
    ANSI_256 = 2

    #: True colors are supported.
    ANSI_TRUE = 3


class InteractiveSupport(enum.IntEnum):
    """Terminal's capability for rendering interactive widgets."""

    #: Terminal can't render anything interactive.
    NONE = 0

    #: Terminal can move cursor and erase lines.
    MOVE_CURSOR = 1

    #: Terminal can process queries, enter ``CBREAK`` mode, etc.
    FULL = 2


@dataclass(frozen=True)
class TerminalColors:
    """Colors and theme of the attached terminal."""

    #: Background color of a terminal.
    background: "ColorValue"

    #: Foreground color of a terminal.
    foreground: "ColorValue"

    #: Color value for the default "black" color.
    black: "ColorValue"

    #: Color value for the default "red" color.
    red: "ColorValue"

    #: Color value for the default "green" color.
    green: "ColorValue"

    #: Color value for the default "yellow" color.
    yellow: "ColorValue"

    #: Color value for the default "blue" color.
    blue: "ColorValue"

    #: Color value for the default "magenta" color.
    magenta: "ColorValue"

    #: Color value for the default "cyan" color.
    cyan: "ColorValue"

    #: Color value for the default "white" color.
    white: "ColorValue"

    #: Overall color theme of a terminal, i.e. dark or light.
    lightness: Lightness


@dataclass(frozen=True)
class Term:
    """Overall info about a terminal."""

    #: Terminal's output stream.
    ostream: _t.TextIO

    #: Terminal's input stream.
    istream: _t.TextIO

    #: Terminal's capability for coloring output.
    color_support: ColorSupport = ColorSupport.NONE

    #: Terminal's capability for rendering interactive widgets.
    interactive_support: InteractiveSupport = InteractiveSupport.NONE

    #: Terminal color settings.
    terminal_colors: _t.Optional[TerminalColors] = None

    @property
    def has_colors(self) -> bool:
        """Return :data:`True` if terminal supports simple 8-bit color codes."""

        return self.color_support >= ColorSupport.ANSI

    @property
    def has_colors_256(self) -> bool:
        """Return :data:`True` if terminal supports 256-encoded colors."""

        return self.color_support >= ColorSupport.ANSI_256

    @property
    def has_colors_true(self) -> bool:
        """Return :data:`True` if terminal supports true colors."""

        return self.color_support >= ColorSupport.ANSI_TRUE

    @property
    def can_move_cursor(self) -> bool:
        """Return :data:`True` if terminal can move cursor and erase lines."""

        return (
            self.has_colors
            and self.interactive_support >= InteractiveSupport.MOVE_CURSOR
        )

    @property
    def can_query_terminal(self) -> bool:
        """Return :data:`True` if terminal can process queries, enter CBREAK mode, etc.

        This is an alias to :attr:`~Term.is_fully_interactive`.

        """

        return self.is_fully_interactive

    @property
    def is_fully_interactive(self) -> bool:
        """Return :data:`True` if we're in a fully interactive environment."""

        return self.has_colors and self.interactive_support >= InteractiveSupport.FULL


_CI_ENV_VARS = [
    "TRAVIS",
    "CIRCLECI",
    "APPVEYOR",
    "GITLAB_CI",
    "BUILDKITE",
    "DRONE",
    "TEAMCITY_VERSION",
]


def get_term_from_stream(
    ostream: _t.TextIO, istream: _t.TextIO, /, *, query_terminal_colors: bool = True
) -> Term:
    """Query info about a terminal attached to the given stream.

    If ``query_terminal_colors`` is :data:`True`, Yuio will try to query background
    and foreground color of the terminal.

    """

    if "__YUIO_FORCE_FULL_TERM_SUPPORT" in os.environ:
        # For building docs in github
        return Term(
            ostream=ostream,
            istream=istream,
            color_support=ColorSupport.ANSI_TRUE,
            interactive_support=InteractiveSupport.FULL,
            terminal_colors=_get_standard_colors(ostream),
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

    color_support = ColorSupport.NONE
    in_ci = "CI" in os.environ
    if (
        "--force-color" in sys.argv
        or "--force-colors" in sys.argv
        or "FORCE_COLOR" in os.environ
        or "FORCE_COLORS" in os.environ
    ):
        color_support = ColorSupport.ANSI
    if has_interactive_output:
        if os.name == "nt":
            if _enable_vt_processing(ostream):
                color_support = ColorSupport.ANSI_TRUE
        elif "GITHUB_ACTIONS" in os.environ:
            color_support = ColorSupport.ANSI_TRUE
            in_ci = True
        elif any(ci in os.environ for ci in _CI_ENV_VARS):
            color_support = ColorSupport.ANSI
            in_ci = True
        elif colorterm in ("truecolor", "24bit") or term == "xterm-kitty":
            color_support = ColorSupport.ANSI_TRUE
        elif colorterm in ("yes", "true") or "256color" in term or term == "screen":
            color_support = ColorSupport.ANSI_256
        elif "linux" in term or "color" in term or "ansi" in term or "xterm" in term:
            color_support = ColorSupport.ANSI

    interactive_support = InteractiveSupport.NONE
    theme = None
    if is_foreground and color_support >= ColorSupport.ANSI and not in_ci:
        if has_interactive_output and has_interactive_input:
            interactive_support = InteractiveSupport.FULL
            if (
                query_terminal_colors
                and color_support >= ColorSupport.ANSI_256
                and "YUIO_DISABLE_OSC_QUERIES" not in os.environ
            ):
                theme = _get_standard_colors(ostream)
        else:
            interactive_support = InteractiveSupport.MOVE_CURSOR

    return Term(
        ostream=ostream,
        istream=istream,
        color_support=color_support,
        interactive_support=interactive_support,
        terminal_colors=theme,
    )


def _get_standard_colors(stream: _t.TextIO) -> _t.Optional[TerminalColors]:
    try:
        query = "\x1b]10;?\x1b\\\x1b]11;?\x1b\\" + "".join(
            [f"\x1b]4;{i};?\x1b\\" for i in range(8)]
        )
        response = _query_term(stream, query)
        if not response:
            return None

        # Deal with foreground color.

        match = re.match(
            r"^\x1b]10;rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})(?:\x1b\\|\a)",
            response,
            re.IGNORECASE,
        )
        if match is None:
            return None

        r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups())
        foreground = ColorValue.from_rgb(r, g, b)

        response = response[match.end() :]

        # Deal with background color.

        match = re.match(
            r"^\x1b]11;rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})(?:\x1b\\|\a)",
            response,
            re.IGNORECASE,
        )
        if match is None:
            return None

        r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups())
        background = ColorValue.from_rgb(r, g, b)
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
            if match is None:
                return None

            c = int(match.group(1))
            r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups()[1:])
            colors[c] = ColorValue.from_rgb(r, g, b)

            response = response[match.end() :]

        if set(colors.keys()) != {0, 1, 2, 3, 4, 5, 6, 7}:
            return None

        # return colors
        return TerminalColors(
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

    except Exception:
        return None


def _query_term(stream: _t.TextIO, query: str) -> _t.Optional[str]:
    try:
        with _enter_raw_mode(stream):
            # Lock the keyboard.
            stream.write("\x1b[2h")
            stream.flush()
            _flush_input_buffer()

            # It is important that we unlock keyboard before exiting `cbreak`,
            # hence the nested `try`.
            try:
                # Append a DA1 query, as virtually all terminals support it.
                stream.write(query + "\x1b[c")
                stream.flush()

                buf = _read_keycode()
                if not buf.startswith("\x1b"):
                    yuio._logger.debug("_query_term invalid response")
                    return None

                # Read till we find a DA1 response.
                while not re.search(r"\x1b\[\?.*?c", buf):
                    buf += _read_keycode()

                return buf[: buf.index("\x1b[?")]
            finally:
                _flush_input_buffer()

                # Release the keyboard.
                stream.write("\x1b[2i")
                stream.flush()
    except Exception:
        yuio._logger.debug("_query_term error", exc_info=True)
        return None


def _is_tty(stream: _t.Optional[_t.TextIO]) -> bool:
    try:
        return stream is not None and stream.isatty()
    except Exception:
        return False


if os.name == "posix":

    def _is_foreground(stream: _t.Optional[_t.TextIO]) -> bool:
        try:
            return stream is not None and os.getpgrp() == os.tcgetpgrp(stream.fileno())
        except Exception:
            return False

elif os.name == "nt":

    def _is_foreground(stream: _t.Optional[_t.TextIO]) -> bool:
        return True

else:

    def _is_foreground(stream: _t.Optional[_t.TextIO]) -> bool:
        return False


def _is_interactive_input(stream: _t.Optional[_t.TextIO]) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.readable()
    except Exception:
        return False


def _is_interactive_output(stream: _t.Optional[_t.TextIO]) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.writable()
    except Exception:
        return False


# Platform-specific code for working with terminals.
if os.name == "posix":
    import select
    import termios
    import tty

    @contextlib.contextmanager
    def _enter_raw_mode(stream: _t.TextIO, bracketed_paste: bool = False):
        assert sys.__stdin__ is not None

        prev_mode = termios.tcgetattr(sys.__stdin__)
        tty.setcbreak(sys.__stdin__, termios.TCSANOW)

        if bracketed_paste:
            stream.write("\x1b[?2004h")
            stream.flush()

        try:
            yield
        finally:
            if bracketed_paste:
                stream.write("\x1b[?2004l")
                stream.flush()
            termios.tcsetattr(sys.__stdin__, termios.TCSAFLUSH, prev_mode)

    def _read_keycode() -> str:
        assert sys.__stdin__ is not None

        key = os.read(sys.__stdin__.fileno(), 1)
        while bool(select.select([sys.__stdin__], [], [], 0)[0]):
            key += os.read(sys.__stdin__.fileno(), 1)

        return key.decode(sys.__stdin__.encoding, errors="replace")

    def _flush_input_buffer():
        pass

    def _enable_vt_processing(ostream: _t.TextIO) -> bool:
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
    def _enter_raw_mode(stream: _t.TextIO, bracketed_paste: bool = False):
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

    def _read_keycode() -> str:
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

    def _flush_input_buffer():
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
            if not bool(
                _SetConsoleMode(
                    handle,
                    _ENABLE_PROCESSED_OUTPUT
                    | _ENABLE_WRAP_AT_EOL_OUTPUT
                    | _ENABLE_VIRTUAL_TERMINAL_PROCESSING,
                )
            ):
                return False

            return True
        except Exception:
            return False

else:

    @contextlib.contextmanager
    def _enter_raw_mode(stream: _t.TextIO, bracketed_paste: bool = False):
        raise OSError("not supported")
        yield

    def _read_keycode() -> str:
        raise OSError("not supported")

    def _flush_input_buffer():
        raise OSError("not supported")

    def _enable_vt_processing(ostream: _t.TextIO) -> bool:
        raise OSError("not supported")


@dataclass(frozen=True, **yuio._with_slots())
class ColorValue:
    """Data about a single color.

    Can be either a single ANSI escape code, or an RGB-tuple.

    Single ANSI escape code represents a standard terminal color code.
    The actual color value for it is controlled by the terminal's user.
    Therefore, it doesn't permit operations on colors,
    such as :meth:`ColorValue.darken` or :meth:`ColorValue.lerp`.

    An RGB-tuple represents a true color. When displaying on a terminal that
    doesn't support true colors, it will be converted to a corresponding
    256-color or an 8-color automatically.

    """

    #: Color data.
    data: _t.Union[int, str, _t.Tuple[int, int, int]]

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, /) -> "ColorValue":
        """Create a color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> ColorValue.from_rgb(0xA0, 0x1E, 0x9C)
            <ColorValue #A01E9C>

        """

        return cls((r, g, b))

    @classmethod
    def from_hex(cls, h: str, /) -> "ColorValue":
        """Create a color value from a hex string.

        Example::

            >>> ColorValue.from_hex('#A01E9C')
            <ColorValue #A01E9C>

        """

        return cls(_parse_hex(h))

    def to_hex(self) -> _t.Optional[str]:
        """Return color in hex format with leading ``#``.

        Example::

            >>> a = ColorValue.from_hex('#A01E9C')
            >>> a.to_hex()
            '#A01E9C'

        """

        rgb = self.to_rgb()
        if rgb is not None:
            return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        else:
            return None

    def to_rgb(self) -> _t.Optional[_t.Tuple[int, int, int]]:
        """Return RGB components of the color.

        Example::

            >>> a = ColorValue.from_hex('#A01E9C')
            >>> a.to_rgb()
            (160, 30, 156)
        """

        if isinstance(self.data, int):
            return _8_to_rgb(self.data)
        elif isinstance(self.data, tuple):
            return self.data
        else:
            return None

    def darken(self, amount: float, /) -> "ColorValue":
        """Make this color darker by the given percentage.

        Amount should be between 0 and 1.

        Example::

            >>> # Darken by 30%.
            ... ColorValue.from_hex('#A01E9C').darken(0.30)
            <ColorValue #70156D>

        """

        rgb = self.to_rgb()
        if rgb is None:
            return self

        amount = max(min(amount, 1), 0)
        r, g, b = rgb
        h, s, v = colorsys.rgb_to_hsv(r / 0xFF, g / 0xFF, b / 0xFF)
        v = v - v * amount
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return ColorValue.from_rgb(int(r * 0xFF), int(g * 0xFF), int(b * 0xFF))

    def lighten(self, amount: float, /) -> "ColorValue":
        """Make this color lighter by the given percentage.

        Amount should be between 0 and 1.

        Example::

            >>> # Lighten by 30%.
            ... ColorValue.from_hex('#A01E9C').lighten(0.30)
            <ColorValue #BC23B7>

        """

        rgb = self.to_rgb()
        if rgb is None:
            return self

        amount = max(min(amount, 1), 0)
        r, g, b = rgb
        h, s, v = colorsys.rgb_to_hsv(r / 0xFF, g / 0xFF, b / 0xFF)
        v = 1 - v
        v = 1 - (v - v * amount)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return ColorValue.from_rgb(int(r * 0xFF), int(g * 0xFF), int(b * 0xFF))

    def match_luminosity(self, other: "ColorValue", /) -> "ColorValue":
        """Set luminosity of this color equal to one of the other color.

        This function will keep hue and saturation of the color intact,
        but it will become as bright as the other color.

        """

        rgb1, rgb2 = self.to_rgb(), other.to_rgb()
        if rgb1 is None or rgb2 is None:
            return self

        h, s, _ = colorsys.rgb_to_hsv(rgb1[0] / 0xFF, rgb1[1] / 0xFF, rgb1[2] / 0xFF)
        _, _, v = colorsys.rgb_to_hsv(rgb2[0] / 0xFF, rgb2[1] / 0xFF, rgb2[2] / 0xFF)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return ColorValue.from_rgb(int(r * 0xFF), int(g * 0xFF), int(b * 0xFF))

    @staticmethod
    def lerp(*colors: "ColorValue") -> _t.Callable[[float], "ColorValue"]:
        """Return a lambda that allows linear interpolation between several colors.

        If either color is a single ANSI escape code, the first color is always returned
        from the lambda.

        Example::

            >>> a = ColorValue.from_hex('#A01E9C')
            >>> b = ColorValue.from_hex('#22C60C')
            >>> lerp = ColorValue.lerp(a, b)

            >>> lerp(0)
            <ColorValue #A01E9C>
            >>> lerp(0.5)
            <ColorValue #617254>
            >>> lerp(1)
            <ColorValue #22C60C>

        """

        if not colors:
            raise TypeError("lerp expected at least 1 argument, got 0")
        elif len(colors) == 1 or not all(
            isinstance(color.data, tuple) for color in colors
        ):
            return lambda f, /: colors[0]
        else:
            l = len(colors) - 1

            def lerp(f: float, /) -> ColorValue:
                i = int(f * l)
                f = (f - (i / l)) * l

                if i == l:
                    return colors[l]
                else:
                    a, b = colors[i].data, colors[i + 1].data
                    return ColorValue(tuple(int(ca + f * (cb - ca)) for ca, cb in zip(a, b)))  # type: ignore

            return lerp

    def _as_fore(self, term: Term, /) -> str:
        return self._as_code(term, fg_bg_prefix="3")

    def _as_back(self, term: Term, /) -> str:
        return self._as_code(term, fg_bg_prefix="4")

    def _as_code(self, term: Term, /, fg_bg_prefix: str) -> str:
        if not term.has_colors:
            return ""
        elif isinstance(self.data, int):
            return f"{fg_bg_prefix}{self.data}"
        elif isinstance(self.data, str):
            return self.data
        elif term.has_colors_true:
            return f"{fg_bg_prefix}8;2;{self.data[0]};{self.data[1]};{self.data[2]}"
        elif term.has_colors_256:
            return f"{fg_bg_prefix}8;5;{_rgb_to_256(*self.data)}"
        else:
            return f"{fg_bg_prefix}{_rgb_to_8(*self.data)}"

    def __repr__(self) -> str:
        if isinstance(self.data, tuple):
            return f"<ColorValue {self.to_hex()}>"
        else:
            return f"<ColorValue {self.data}>"


@dataclass(frozen=True, **yuio._with_slots())
class Color:
    """Data about terminal output style. Contains
    foreground and background color, as well as text styles.

    This class only contains data about the color. It doesn't know anything about
    how to apply it to a terminal, or whether a terminal supports colors at all.
    These decisions are thus deferred to a lower level of API (see :meth:`Color.as_code`).

    When converted to an ANSI code and printed, a color completely overwrites a previous
    color that was used by a terminal. This behavior prevents different colors and styles
    bleeding one into another. So, for example, printing :data:`Color.STYLE_BOLD`
    and then :data:`Color.FORE_RED` will result in non-bold red text.

    Colors can be combined before printing, though::

        >>> Color.STYLE_BOLD | Color.FORE_RED  # Bold red
        Color(fore=<ColorValue 1>, back=None, bold=True, dim=None)

    Yuio supports true RGB colors. They are automatically converted
    to 256- or 8-bit colors if needed.

    """

    #: Foreground color.
    fore: _t.Optional[ColorValue] = None

    #: Background color.
    back: _t.Optional[ColorValue] = None

    #: If true, render text as bold.
    bold: _t.Optional[bool] = None

    #: If true, render text as dim.
    dim: _t.Optional[bool] = None

    def __or__(self, other: "Color", /):
        return Color(
            other.fore if other.fore is not None else self.fore,
            other.back if other.back is not None else self.back,
            other.bold if other.bold is not None else self.bold,
            other.dim if other.dim is not None else self.dim,
        )

    def __ior__(self, other: "Color", /):
        return self | other

    @classmethod
    def fore_from_rgb(cls, r: int, g: int, b: int) -> "Color":
        """Create a foreground color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> Color.fore_from_rgb(0xA0, 0x1E, 0x9C)
            Color(fore=<ColorValue #A01E9C>, back=None, bold=None, dim=None)

        """

        return cls(fore=ColorValue.from_rgb(r, g, b))

    @classmethod
    def fore_from_hex(cls, h: str) -> "Color":
        """Create a foreground color value from a hex string.

        Example::

            >>> Color.fore_from_hex('#A01E9C')
            Color(fore=<ColorValue #A01E9C>, back=None, bold=None, dim=None)

        """

        return cls(fore=ColorValue.from_hex(h))

    @classmethod
    def back_from_rgb(cls, r: int, g: int, b: int) -> "Color":
        """Create a background color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> Color.back_from_rgb(0xA0, 0x1E, 0x9C)
            Color(fore=None, back=<ColorValue #A01E9C>, bold=None, dim=None)

        """

        return cls(back=ColorValue.from_rgb(r, g, b))

    @classmethod
    def back_from_hex(cls, h: str) -> "Color":
        """Create a background color value from a hex string.

        Example::

            >>> Color.back_from_hex('#A01E9C')
            Color(fore=None, back=<ColorValue #A01E9C>, bold=None, dim=None)

        """

        return cls(back=ColorValue.from_hex(h))

    @staticmethod
    def lerp(*colors: "Color") -> _t.Callable[[float], "Color"]:
        """Return a lambda that allows linear interpolation between several colors.

        If either color is a single ANSI escape code, the first color is always returned
        from the lambda.

        Example::

            >>> a = Color.fore_from_hex('#A01E9C')
            >>> b = Color.fore_from_hex('#22C60C')
            >>> lerp = Color.lerp(a, b)

            >>> lerp(0)
            Color(fore=<ColorValue #A01E9C>, back=None, bold=None, dim=None)
            >>> lerp(0.5)
            Color(fore=<ColorValue #617254>, back=None, bold=None, dim=None)
            >>> lerp(1)
            Color(fore=<ColorValue #22C60C>, back=None, bold=None, dim=None)

        """

        if not colors:
            raise TypeError("lerp expected at least 1 argument, got 0")
        elif len(colors) == 1:
            return lambda f, /: colors[0]
        else:
            fore_lerp = all(
                color.fore is not None and isinstance(color.fore.data, tuple)
                for color in colors
            )
            if fore_lerp:
                fore = ColorValue.lerp(*(color.fore for color in colors))  # type: ignore

            back_lerp = all(
                color.back is not None and isinstance(color.back.data, tuple)
                for color in colors
            )
            if back_lerp:
                back = ColorValue.lerp(*(color.back for color in colors))  # type: ignore

            if fore_lerp and back_lerp:
                return lambda f: dataclasses.replace(colors[0], fore=fore(f), back=back(f))  # type: ignore
            elif fore_lerp:
                return lambda f: dataclasses.replace(colors[0], fore=fore(f))  # type: ignore
            elif back_lerp:
                return lambda f: dataclasses.replace(colors[0], back=back(f))  # type: ignore
            else:
                return lambda f, /: colors[0]

    def as_code(self, term: Term, /) -> str:
        """Convert this color into an ANSI escape code
        with respect to the given terminal capabilities.

        """

        if not term.has_colors:
            return ""

        codes = []
        if self.fore:
            codes.append(self.fore._as_fore(term))
        if self.back:
            codes.append(self.back._as_back(term))
        if self.bold:
            codes.append("1")
        if self.dim:
            codes.append("2")
        if codes:
            return "\x1b[;" + ";".join(codes) + "m"
        else:
            return "\x1b[m"

    #: No color.
    NONE: _t.ClassVar["Color"] = lambda: Color()  # type: ignore

    #: Bold font style.
    STYLE_BOLD: _t.ClassVar["Color"] = lambda: Color(bold=True)  # type: ignore
    #: Dim font style.
    STYLE_DIM: _t.ClassVar["Color"] = lambda: Color(dim=True)  # type: ignore
    #: Not bold nor dim.
    STYLE_NORMAL: _t.ClassVar["Color"] = lambda: Color(bold=False, dim=False)  # type: ignore

    #: Normal foreground color.
    FORE_NORMAL: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(9))  # type: ignore
    #: Normal foreground color rendered with dim setting.
    #:
    #: This is an alternative to bright black that works with
    #: most terminals and color schemes.
    FORE_NORMAL_DIM: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue("2"))  # type: ignore
    #: Black foreground color.
    #:
    #: .. warning::
    #:
    #:    Avoid using this color, in most terminals it is the same as background color.
    #:    Instead, use :attr:`~Color.FORE_NORMAL_DIM`.
    FORE_BLACK: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(0))  # type: ignore
    #: Red foreground color.
    FORE_RED: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(1))  # type: ignore
    #: Green foreground color.
    FORE_GREEN: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(2))  # type: ignore
    #: Yellow foreground color.
    FORE_YELLOW: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(3))  # type: ignore
    #: Blue foreground color.
    FORE_BLUE: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(4))  # type: ignore
    #: Magenta foreground color.
    FORE_MAGENTA: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(5))  # type: ignore
    #: Cyan foreground color.
    FORE_CYAN: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(6))  # type: ignore
    #: White foreground color.
    #:
    #: Avoid using it, in some terminals, notably in the Mac OS default terminal,
    #: it is unreadable.
    FORE_WHITE: _t.ClassVar["Color"] = lambda: Color(fore=ColorValue(7))  # type: ignore

    #: Normal background color.
    BACK_NORMAL: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(9))  # type: ignore
    #: Black background color.
    BACK_BLACK: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(0))  # type: ignore
    #: Red background color.
    BACK_RED: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(1))  # type: ignore
    #: Green background color.
    BACK_GREEN: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(2))  # type: ignore
    #: Yellow background color.
    BACK_YELLOW: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(3))  # type: ignore
    #: Blue background color.
    BACK_BLUE: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(4))  # type: ignore
    #: Magenta background color.
    BACK_MAGENTA: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(5))  # type: ignore
    #: Cyan background color.
    BACK_CYAN: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(6))  # type: ignore
    #: White background color.
    BACK_WHITE: _t.ClassVar["Color"] = lambda: Color(back=ColorValue(7))  # type: ignore


for _n, _v in vars(Color).items():
    if _n == _n.upper():
        setattr(Color, _n, _v())
del _n, _v  # type: ignore


def _rgb_to_256(r: int, g: int, b: int) -> int:
    closest_idx = lambda x, vals: min((abs(x - v), i) for i, v in enumerate(vals))[1]
    color_components = [0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF]

    if r == g == b:
        i = closest_idx(r, color_components + [0x08 + 10 * i for i in range(24)])
        if i >= len(color_components):
            return 232 + i - len(color_components)
        r, g, b = i, i, i
    else:
        r, g, b = [closest_idx(x, color_components) for x in (r, g, b)]
    return r * 36 + g * 6 + b + 16


def _rgb_to_8(r: int, g: int, b: int) -> int:
    return (
        (1 if r >= 128 else 0)
        | (1 if g >= 128 else 0) << 1
        | (1 if b >= 128 else 0) << 2
    )


def _8_to_rgb(code: int) -> _t.Tuple[int, int, int]:
    return (
        (code & 1) and 0xFF,
        (code & 2) and 0xFF,
        (code & 4) and 0xFF,
    )


def _parse_hex(h: str) -> _t.Tuple[int, int, int]:
    if not re.match(r"^#[0-9a-fA-F]{6}$", h):
        raise ValueError(f"invalid hex string {h!r}")
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore


def line_width(s: str, /) -> int:
    """Calculates string width when the string is displayed
    in a terminal.

    This function makes effort to detect wide characters
    such as emojis. If does not, however, work correctly
    with extended grapheme clusters, and so it may fail
    for emojis with modifiers, or other complex characters.

    Example where it fails is ``👩🏽‍💻``. It consists
    of four code points:

    - Unicode Character `WOMAN` (``U+1F469``, ``👩``),
    - Unicode Character `EMOJI MODIFIER FITZPATRICK TYPE-4` (``U+1F3FD``),
    - Unicode Character `ZERO WIDTH JOINER` (``U+200D``),
    - Unicode Character `PERSONAL COMPUTER` (``U+1F4BB``, ``💻``).

    Since :func:`line_width` can't understand that these code points
    are combined into a single emoji, it treats them separately,
    resulting in answer `6` (`2` for every code point except `ZERO WIDTH JOINER`)::

        >>> line_width("\U0001f469\U0001f3fd\U0000200d\U0001f4bb")
        6

    In all fairness, detecting how much space such an emoji will take
    is not so straight forward, as that will depend on unicode capabilities
    of a specific terminal. Since a lot of terminals will not handle such emojis
    correctly, I've decided to go with this simplistic implementation.

    """

    # Note: it may be better to bundle `wcwidth` and use it instead of the code below.
    # However, there is an issue that `wcwidth`'s results are not additive.
    # In the above example, `wcswidth('👩🏽‍💻')` will see that it is two-spaces wide,
    # while `sum(wcwidth(c) for c in '👩🏽‍💻')` will report that it is four-spaces wide.
    # To render it properly, the widget will have to be aware of extended grapheme
    # clusters, and generally this will be a lot of headache. Since most terminals
    # won't handle these edge cases correctly, I don't want to bother.

    if s.isascii():
        # Fast path. Note that our renderer replaces unprintable characters
        # with spaces, so ascii strings always have width equal to their length.
        return len(s)
    else:
        # Long path. It kinda works, but not always, but most of the times...
        return sum(
            (unicodedata.east_asian_width(c) in "WF") + 1
            for c in s
            if unicodedata.category(c)[0] not in "MC"
        )


#: Raw colorized string. This is the underlying type for :class:`ColorizedString`.
RawString: _t.TypeAlias = _t.Iterable[_t.Union[Color, str]]


#: Any string (i.e. a :class:`str`, a raw colorized string, or a normal colorized string).
AnyString: _t.TypeAlias = _t.Union[str, Color, RawString, "ColorizedString"]


class NoWrap(str):
    """A string that will not be wrapped by the text wrapper.

    See :meth:`ColorizedString.wrap` for more info.

    """


class Esc(NoWrap):
    """
    A string that signifies an escaped special symbol.

    This string is not wrapped even if ``break_long_nowrap_words`` is :data:`True`.

    """


@_t.final
class ColorizedString:
    """A string with colors.

    This class is a wrapper over a list of strings and colors.
    Each color applies to strings after it, right until the next color.

    :class:`ColorizedString` supports some basic string operations.
    Most notable, it supports wide-character-aware wrapping (see :func:`line_width`),
    and ``%``-formatting.

    Unlike :class:`str` instances, :class:`ColorizedString` is mutable through
    the ``+=`` operator.

    You can build a colorized string from raw parts,
    or you can use :meth:`yuio.md.colorize`.

    """

    def __init__(
        self,
        content: AnyString = "",
        /,
        *,
        explicit_newline: str = "",
    ):
        self._parts: _t.List[_t.Union[Color, str]]
        if isinstance(content, (str, Color)):
            self._parts = [content] if content else []
        elif isinstance(content, ColorizedString):
            self._parts = list(content._parts)
        else:
            self._parts = list(content)

        self._explicit_newline = explicit_newline

    @property
    def explicit_newline(self) -> str:
        """Explicit newline indicates that a line of a wrapped text
        was broken because the original text contained a new line character.

        See :meth:`~ColorizedString.wrap` for details.

        """

        return self._explicit_newline

    @functools.cached_property
    def width(self) -> int:
        """String width when the string is displayed in a terminal.

        See :func:`line_width` for more information.

        """

        return sum(line_width(s) for s in self._parts if isinstance(s, str))

    @functools.cached_property
    def len(self) -> int:
        """Line length in bytes, ignoring all colors."""

        return sum(len(s) for s in self._parts if isinstance(s, str))

    def __len__(self) -> int:
        return self.len

    def __bool__(self) -> bool:
        return self.len > 0

    def iter(self) -> _t.Iterator[_t.Union[Color, str]]:
        """Iterate over raw parts of the string,
        i.e. the underlying list of strings and colors.

        """

        return self._parts.__iter__()

    def __iter__(self) -> _t.Iterator[_t.Union[Color, str]]:
        return self.iter()

    def wrap(
        self,
        width: int,
        /,
        *,
        preserve_spaces: bool = False,
        preserve_newlines: bool = True,
        break_long_words: bool = True,
        break_long_nowrap_words: bool = False,
        first_line_indent: AnyString = "",
        continuation_indent: AnyString = "",
    ) -> _t.List["ColorizedString"]:
        r"""Wrap a long line of text into multiple lines.

        :param preserve_spaces:
            if set to :data:`True`, all spaces are preserved.
            Otherwise, consecutive spaces are collapsed into a single space.
            Note that tabs are always treated as a single space.
        :param preserve_newlines:
            if set to :data:`True` (default), text is additionally wrapped
            on newline characters. When this happens, the newline sequence that wrapped
            the line will be placed into :attr:`~ColorizedString.explicit_newline`.

            If set to :data:`False`, newlines are treated as whitespaces.
        :param break_long_words:
            if set to :data:`True` (default), words that don't fit into a single line
            will be split into multiple lines.
        :param break_long_nowrap_words:
            if set to :data:`True`, :class:`NoWrap` words that don't fit
            into a single line will be split into multiple lines.
        :param first_line_indent:
            a string that will be prepended before the first line.
        :param continuation_indent:
            a string that will be prepended before all subsequent lines.

        Example::

            >>> ColorizedString("hello, world!\nit's a good day!").wrap(13)  # doctest: +NORMALIZE_WHITESPACE
            [<ColorizedString('hello, world!', explicit_newline='\n')>,
             <ColorizedString("it's a good")>,
             <ColorizedString('day!')>]

        """

        return _TextWrapper(
            width,
            preserve_spaces=preserve_spaces,
            preserve_newlines=preserve_newlines,
            break_long_words=break_long_words,
            break_long_nowrap_words=break_long_nowrap_words,
            first_line_indent=first_line_indent,
            continuation_indent=continuation_indent,
        ).wrap(self)

    def indent(
        self,
        first_line_indent: AnyString = "",
        continuation_indent: AnyString = "",
    ) -> "ColorizedString":
        r"""Indent this string by the given sequence.

        :param first_line_indent:
            this will be appended to the first line in the string.
        :param continuation_indent:
            this will be appended to subsequent lines in the string.

        Example::

            >>> ColorizedString("hello, world!\nit's a good day!").indent("# ", "  ")
            <ColorizedString("# hello, world!\n  it's a good day!")>

        """

        res = ColorizedString()

        color: Color = Color.NONE
        cur_color: Color = Color.NONE
        needs_indent = True

        for part in self._parts:
            if isinstance(part, Color):
                color = part
                continue

            for line in part.splitlines(keepends=True):
                if needs_indent:
                    if cur_color != Color.NONE:
                        res += Color.NONE
                    res += first_line_indent
                    first_line_indent = ColorizedString(continuation_indent)

                if color and (needs_indent or color != cur_color):
                    res += color
                    cur_color = color

                res += line

                needs_indent = line.endswith("\n")

        if color and color != cur_color:
            res += color

        return res

    def percent_format(self, args: _t.Any) -> "ColorizedString":
        """Format colorized string as if with ``%``-formatting
        (i.e. `old-style formatting`_).

        .. _old-style formatting: https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting

        Example::

            >>> line = ColorizedString("Hello, %s!")
            >>> line % "Username"
            <ColorizedString('Hello, Username!')>

        """

        return ColorizedString(_percent_format(self, args))

    def __mod__(self, args: _t.Any) -> "ColorizedString":
        return self.percent_format(args)

    def __imod__(self, args: _t.Any) -> "ColorizedString":
        self._parts = _percent_format(self, args)

        self.__dict__.pop("width", None)
        self.__dict__.pop("len", None)

        return self

    def __add__(self, rhs: AnyString) -> "ColorizedString":
        copy = ColorizedString(self)
        copy += rhs
        return copy

    def __radd__(self, lhs: AnyString) -> "ColorizedString":
        copy = ColorizedString(lhs)
        copy += self
        return copy

    def __iadd__(self, rhs: AnyString) -> "ColorizedString":
        if isinstance(rhs, (str, Color)):
            if rhs:
                self._parts.append(rhs)
        elif isinstance(rhs, ColorizedString):
            self._parts.extend(rhs._parts)
        else:
            self._parts.extend(rhs)

        self.__dict__.pop("width", None)
        self.__dict__.pop("len", None)

        return self

    def process_colors(self, term: Term, /) -> _t.List[str]:
        """Convert colors in this string into a normal string
        with ANSI escape sequences.

        """

        out: _t.List[str] = []

        color: _t.Optional[Color] = None
        cur_color: _t.Optional[Color] = None

        for part in self._parts:
            if isinstance(part, Color):
                color = part
            else:
                if color and color != cur_color:
                    out.append(color.as_code(term))
                    cur_color = color
                out.append(part)

        if color and color != cur_color:
            out.append(color.as_code(term))

        return out

    def __str__(self) -> str:
        return "".join(c for c in self._parts if isinstance(c, str))

    def __repr__(self) -> str:
        if self.explicit_newline:
            return f"<ColorizedString({str(self)!r}, explicit_newline={self.explicit_newline!r})>"
        else:
            return f"<ColorizedString({str(self)!r})>"


_S_SYNTAX = re.compile(
    r"""
        %                               # Percent
        (?:\((?P<mapping>[^)]*)\))?     # Mapping key
        (?P<flag>[#0\-+ ])*             # Conversion Flag
        (?P<width>\*|\d+)?              # Field width
        (?:\.(?P<precision>\*|\d*))?    # Precision
        [hlL]?                          # Unused length modifier
        (?P<format>.)                   # Conversion type
    """,
    re.VERBOSE,
)


def _percent_format(s: ColorizedString, args: _t.Any) -> _t.List[_t.Union[Color, str]]:
    if not isinstance(args, (dict, tuple)):
        args = (args,)

    i = 0

    def repl(m: _t.StrReMatch) -> str:
        nonlocal i
        groups = m.groupdict()
        if groups["format"] == "%":
            if m.group(0) != "%%":
                raise ValueError("unsupported format character '%'")
            return "%"

        if groups["mapping"] is not None:
            fmt_args = args
        elif isinstance(args, tuple):
            begin = i
            end = i = i + 1 + (m.group("width") == "*") + (m.group("precision") == "*")
            fmt_args = args[begin:end]
        elif i == 0:
            # We've passed a dict, and now want to format it with `%s`.
            # We allow that once. I.e. `"%s" % {}` is fine, `"%s %s" % {}` is not.
            fmt_args = args
            i = 1
        else:
            raise TypeError("not enough arguments for format string")

        return m.group(0) % fmt_args

    raw = []
    for part in s:
        if isinstance(part, NoWrap):
            raw.append(NoWrap(_S_SYNTAX.sub(repl, part)))
        elif isinstance(part, str):
            raw.append(_S_SYNTAX.sub(repl, part))
        else:
            raw.append(part)

    if isinstance(args, tuple) and i < len(args):
        raise TypeError("not all arguments converted during string formatting")

    return raw


_SPACE_TRANS = str.maketrans("\r\n\t\v\b\f", "      ")

_WORD_PUNCT = r'[\w!"\'&.,?]'
_LETTER = r"[^\d\W]"
_NOWHITESPACE = r"[^ \r\n\t\v\b\f]"

# Copied from textwrap with some modifications in newline handling
_WORDSEP_RE = re.compile(
    r"""
    ( # newlines and line feeds are matched one-by-one
        \v?(?:\r\n|\r|\n)
    | # any whitespace
        [ \t\v\b\f]+
    | # em-dash between words
        (?<=%(wp)s) -{2,} (?=\w)
    | # word, possibly hyphenated
        %(nws)s+? (?:
        # hyphenated word
            -(?: (?<=%(lt)s{2}-) | (?<=%(lt)s-%(lt)s-))
            (?= %(lt)s -? %(lt)s)
        | # end of word
            (?=[ \r\n\t\v\b\f]|\Z)
        | # em-dash
            (?<=%(wp)s) (?=-{2,}\w)
        )
    )"""
    % {"wp": _WORD_PUNCT, "lt": _LETTER, "nws": _NOWHITESPACE},
    re.VERBOSE,
)
_WORDSEP_NL_RE = re.compile(r"(\v?(?:\r\n|\r|\n))")


class _TextWrapper:
    def __init__(
        self,
        width: int,
        /,
        *,
        preserve_spaces: bool,
        preserve_newlines: bool,
        break_long_words: bool,
        break_long_nowrap_words: bool,
        first_line_indent: AnyString = "",
        continuation_indent: AnyString = "",
    ):
        self.width: int = width
        self.preserve_spaces: bool = preserve_spaces
        self.preserve_newlines: bool = preserve_newlines
        self.break_long_words: bool = break_long_words
        self.break_long_nowrap_words: bool = break_long_nowrap_words
        self.first_line_indent: ColorizedString = ColorizedString(first_line_indent)
        self.continuation_indent: ColorizedString = ColorizedString(continuation_indent)

        if (
            self.width - self.first_line_indent.width <= 1
            or self.width - self.continuation_indent.width <= 1
        ):
            self.width = (
                max(self.first_line_indent.width, self.continuation_indent.width) + 2
            )

        self.lines: _t.List[ColorizedString] = []

        self.current_line: _t.List[_t.Union[Color, str]] = [Color.NONE]
        if self.first_line_indent:
            self.current_line.extend(list(self.first_line_indent))
            self.current_line.append(Color.NONE)
        self.current_line_width: int = self.first_line_indent.width
        self.current_color: Color = Color.NONE
        self.current_line_is_nonempty: bool = False

    def _flush_line(self, explicit_newline=""):
        self.lines.append(
            ColorizedString(self.current_line, explicit_newline=explicit_newline)
        )
        self.current_line: _t.List[_t.Union[Color, str]] = []
        if self.continuation_indent:
            self.current_line.append(Color.NONE)
            self.current_line.extend(list(self.continuation_indent))
        self.current_line.append(self.current_color)
        self.current_line_width: int = self.continuation_indent.width
        self.current_line_is_nonempty = False

    def _append_word(self, word: str, word_width: int):
        self.current_line_is_nonempty = True
        self.current_line.append(word)
        self.current_line_width += word_width

    def _append_color(self, color: Color):
        if color != self.current_color:
            self.current_color = color
            self.current_line.append(color)

    def _append_word_with_breaks(self, word: str, word_width: int):
        while self.current_line_width + word_width > self.width:
            word_head_len = word_head_width = 0

            for c in word:
                c_width = line_width(c)
                if self.current_line_width + word_head_width + c_width > self.width:
                    break
                word_head_len += 1
                word_head_width += c_width

            self._append_word(word[:word_head_len], word_head_width)

            word = word[word_head_len:]
            word_width -= word_head_width

            self._flush_line()

        if word:
            self._append_word(word, word_width)

    def wrap(self, text: ColorizedString) -> _t.List[ColorizedString]:
        need_space_before_word = False
        at_line_beginning = True

        for part in text:
            if isinstance(part, Color):
                if (
                    need_space_before_word
                    and self.current_line_width + need_space_before_word <= self.width
                ):
                    # Make sure any space that was issued before the color is flushed.
                    self._append_word(" ", 1)
                    need_space_before_word = False
                self._append_color(part)
                continue

            nowrap = False
            if isinstance(part, Esc):
                words = [part]
            elif isinstance(part, NoWrap):
                words = _WORDSEP_NL_RE.split(part)
                nowrap = True
            else:
                words = _WORDSEP_RE.split(part)

            for word in words:
                if not word:
                    continue

                if "\v" in word or (
                    word in ("\r", "\n", "\r\n") and self.preserve_newlines
                ):
                    self._flush_line(explicit_newline=word)
                    need_space_before_word = False
                    at_line_beginning = True
                    continue

                if word.isspace():
                    if nowrap:
                        word = word.translate(_SPACE_TRANS)
                        self._append_word(word, len(word))
                    elif at_line_beginning or self.preserve_spaces:
                        word = word.translate(_SPACE_TRANS)
                        self._append_word_with_breaks(word, len(word))
                    else:
                        need_space_before_word = True
                    continue

                word_width = line_width(word)

                if (
                    self.current_line_width + word_width + need_space_before_word
                    <= self.width
                ):
                    # Word fits onto the current line.
                    if need_space_before_word:
                        self._append_word(" ", 1)
                    self._append_word(word, word_width)
                else:
                    # Word doesn't fit, so we start a new line.
                    if self.current_line_is_nonempty:
                        self._flush_line()
                    if (
                        (nowrap and self.break_long_nowrap_words)
                        or (not nowrap and self.break_long_words)
                        and not isinstance(word, Esc)
                    ):
                        # We will break the word in the middle if it doesn't fit
                        # onto the whole line.
                        self._append_word_with_breaks(word, word_width)
                    else:
                        self._append_word(word, word_width)

                need_space_before_word = False
                at_line_beginning = False

        if self.current_line or not self.lines or self.lines[-1].explicit_newline:
            self._flush_line()

        return self.lines
