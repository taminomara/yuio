# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides basic information about the process' terminal.

You can inspect `stdin` and `stderr` streams by using the following
functions:

.. autofunction:: get_stdout_info

.. autofunction:: get_stderr_info

.. autoclass:: TermTheme
   :members:

.. autoclass:: TermInfo
   :members:

"""

import contextlib
import colorsys
import enum
import functools
import os
import re
import sys
import typing as _t
import dataclasses
from dataclasses import dataclass


_STDIN: _t.Optional[_t.TextIO] = sys.__stdin__
_STDOUT: _t.Optional[_t.TextIO] = sys.__stdout__
_STDERR: _t.Optional[_t.TextIO] = sys.__stderr__


class TermTheme(enum.Enum):
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


class TermColors(enum.IntEnum):
    """Terminal's capability for coloring output.

    """

    #: Color codes are not supported.
    NONE = 0

    #: Only simple 8-bit color codes are supported.
    ANSI = 1

    #: 256-encoded colors are supported.
    ANSI_256 = 2

    #: True colors are supported.
    ANSI_TRUE = 3


@dataclass(frozen=True)
class TermInfo:
    """Overall info about a terminal.

    """

    #: If true, we're attached to a terminal.
    has_interactive_output: bool = False

    #: Terminal's capability for coloring output.
    colors: TermColors = TermColors.NONE

    #: Terminal's level of support for
    can_move_cursor: bool = False

    #: Background color of a terminal.
    background_color: _t.Optional['ColorValue'] = None

    #: Overall color theme of a terminal.
    theme: TermTheme = TermTheme.UNKNOWN

    @property
    def has_colors(self) -> bool:
        """Return true if terminal supports simple 8-bit color codes.

        """

        return self.colors >= TermColors.ANSI

    @property
    def has_colors_256(self) -> bool:
        """Return true if terminal supports 256-encoded colors.

        """

        return self.colors >= TermColors.ANSI_256

    @property
    def has_colors_true(self) -> bool:
        """Return true if terminal supports true colors.

        """

        return self.colors >= TermColors.ANSI_TRUE


@functools.cache
def get_stdout_info() -> TermInfo:
    """Query info about stdout stream.

    """

    return _get_term_info(_STDOUT)


@functools.cache
def get_stderr_info() -> TermInfo:
    """Query info about stderr stream.

    """

    return _get_term_info(_STDERR)


def _get_term_info(ostream: _t.Optional[_t.TextIO]) -> TermInfo:
    term = os.environ.get('TERM', '').lower()
    colorterm = os.environ.get('COLORTERM', '').lower()

    has_interactive_output = _is_interactive_output(ostream)

    colors = TermColors.NONE
    can_move_cursor = False
    if has_interactive_output:
        if os.name == 'nt':
            if _enable_vt_processing(ostream):
                colors = TermColors.ANSI_TRUE
                can_move_cursor = True
        elif 'GITHUB_ACTIONS' in os.environ:
            colors = TermColors.ANSI_TRUE
        elif any(ci in os.environ for ci in ['TRAVIS', 'CIRCLECI', 'APPVEYOR', 'GITLAB_CI', 'BUILDKITE', 'DRONE', 'TEAMCITY_VERSION']):
            colors = TermColors.ANSI
        elif colorterm in ('truecolor', '24bit') or term == 'xterm-kitty':
            colors = TermColors.ANSI_TRUE
            can_move_cursor = True
        elif colorterm in ('yes', 'true') or '256color' in term or term == 'screen':
            colors = TermColors.ANSI_256
            can_move_cursor = True
        elif term in 'linux' or 'color' in term or 'ansi' in term or 'xterm' in term:
            colors = TermColors.ANSI
            can_move_cursor = True

    theme = TermTheme.UNKNOWN
    background_color = None
    if colors >= TermColors.ANSI and can_move_cursor:
        theme, background_color = _get_theme(ostream)

    return TermInfo(
        has_interactive_output=has_interactive_output,
        colors=colors,
        can_move_cursor=can_move_cursor,
        background_color=ColorValue(background_color) if background_color else None,
        theme=theme,
    )


def _get_theme(ostream: _t.Optional[_t.TextIO]) -> _t.Tuple[TermTheme, _t.Optional[_t.Tuple[int, int, int]]]:
    try:
        response = _query_term(ostream, '\x1b]11;?\a')
        if response is None:
            return TermTheme.UNKNOWN, None

        match = re.match(r'^]11;rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})$', response, re.IGNORECASE)
        if match is None:
            return TermTheme.UNKNOWN, None

        r, g, b = (int(v, 16) // 4 ** len(v) for v in match.groups())

        luma = (0.2627 * r + 0.6780 * g + 0.0593 * b) / 256

        if luma <= 0.2:
            return TermTheme.DARK, (r, g, b)
        elif luma >=0.85:
            return TermTheme.LIGHT, (r, g, b)
        else:
            return TermTheme.UNKNOWN, (r, g, b)
    except Exception:
        return TermTheme.UNKNOWN, None


def _query_term(ostream: _t.Optional[_t.TextIO], query: str, timeout: float = 0.1) -> _t.Optional[str]:
    try:
        istream = _STDIN
        if not _is_interactive_output(ostream) or not _is_interactive_input(istream):
            return None
        if not _is_foreground(ostream) or not _is_foreground(istream):
            return None

        with _set_raw(ostream):
            while _kbhit():
                _getch()

            ostream.write(query)
            ostream.flush()

            if not _kbhit(timeout):
                return None

            if _getch() != '\x1b':
                return

            buf = ''
            while (c := _getch()) not in ('\x1b', '\a'):
                buf += c
            if c == '\x1b':
                _getch()

            return buf
    except Exception:
        return None


def _is_tty(stream: _t.Optional[_t.TextIO]) -> _t.TypeGuard[_t.TextIO]:
    try:
        return stream is not None and stream.isatty()
    except Exception:
        return False


def _is_foreground(stream: _t.Optional[_t.TextIO]) -> _t.TypeGuard[_t.TextIO]:
    try:
        return stream is not None and os.getpgrp() == os.tcgetpgrp(stream.fileno())
    except Exception:
        return False


def _is_interactive_input(stream: _t.Optional[_t.TextIO]) -> _t.TypeGuard[_t.TextIO]:
    try:
        return _is_tty(stream) and stream.readable()
    except Exception:
        return False


def _is_interactive_output(stream: _t.Optional[_t.TextIO]) -> _t.TypeGuard[_t.TextIO]:
    try:
        return _is_tty(stream) and stream.writable()
    except Exception:
        return False


# Platform-specific code for working with terminals.
if os.name == 'posix':
    import select
    import termios
    import tty

    @contextlib.contextmanager
    def _set_raw(ostream: _t.TextIO):
        prev_mode = termios.tcgetattr(ostream)
        tty.setcbreak(ostream, termios.TCSANOW)

        try:
            yield
        finally:
            termios.tcsetattr(ostream, termios.TCSAFLUSH, prev_mode)

    def _getch() -> str:
        return _STDIN.read(1)

    def _kbhit(timeout: float = 0) -> bool:
        return bool(select.select([_STDIN], [], [], timeout)[0])
else:
    @contextlib.contextmanager
    def _set_raw(ostream: _t.TextIO):
        raise OSError('not supported')
        yield

    def _getch() -> str:
        raise OSError('not supported')

    def _kbhit(timeout: float = 0) -> bool:
        raise OSError('not supported')


if os.name == 'nt':
    import ctypes
    import msvcrt

    def _enable_vt_processing(ostream: _t.TextIO) -> bool:
        try:
            version = sys.getwindowsversion()
            if version.major < 10 or version.build < 14931:
                return False

            stderr_handle = msvcrt.get_osfhandle(ostream.fileno())
            return bool(ctypes.windll.kernel32.SetConsoleMode(stderr_handle, 7))

        except Exception:
            return False


@dataclass(frozen=True, slots=True)
class ColorValue:
    """Data about a single color.

    Can be either a single ANSI escape code, or an RGB-tuple.

    Single ANSI escape code represents a standard terminal color code.
    The actual color value for it is controlled by the terminal's user.
    Therefore, it doesn't permit operations on colors,
    such as :meth:`Color.darken` or :meth:`Color.interpolate`.

    An RGB-tuple represents a true color. When displaying on a terminal that
    doesn't support true colors, it will be converted to a corresponding
    256-color or an 8-color automatically.

    """

    #: Color data.
    data: _t.Union[int, _t.Tuple[int, int, int]]

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int) -> 'ColorValue':
        """Create a color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> ColorValue.from_rgb(0xA0, 0x1E, 0x9C)
            <ColorValue #A01E9C>

        """

        return cls((r, g, b))

    @classmethod
    def from_hex(cls, h: str) -> 'ColorValue':
        """Create a color value from a hex string

        Example::

            >>> ColorValue.from_hex('#A01E9C')
            <ColorValue #A01E9C>

        """

        return cls(_parse_hex(h))

    def darken(self, amount: float) -> 'ColorValue':
        """Make this color darker by the given percentage.

        Example::

            >>> # Darken by 30%.
            ... ColorValue.from_hex('#A01E9C').darken(0.30)
            <ColorValue #70156D>

        """

        return _adjust_lightness(self, -amount)

    def lighten(self, amount: float) -> 'ColorValue':
        """Make this color darker by the given percentage.

        Example::

            >>> # Lighten by 30%.
            ... ColorValue.from_hex('#A01E9C').lighten(0.30)
            <ColorValue #DB42D6>

        """

        return _adjust_lightness(self, amount)

    @staticmethod
    def lerp(*colors: 'ColorValue') -> _t.Callable[[float], 'ColorValue']:
        """Return a lambda that allows linear interpolation between several colors.

        If either color is a single ANSI escape code, the first color is always returned
        from the lambda.

        Example::

            >>> a = ColorValue.from_hex('#A01E9C')
            ... b = ColorValue.from_hex('#22C60C')
            ... lerp = a.lerp(b)

            >>> lerp(0)
            <ColorValue #A01E9C>
            >>> lerp(0.5)
            <ColorValue #617254>
            >>> lerp(1)
            <ColorValue #22C60C>

        """

        if not colors:
            return lambda f, /: ColorValue(9)
        elif len(colors) >= 2 and all(isinstance(color.data, tuple) for color in colors):
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
        else:
            return lambda f, /: colors[0]

    def _as_fore(self, cap: TermInfo, /) -> str:
        return self._as_code('3', cap)

    def _as_back(self, cap: TermInfo, /) -> str:
        return self._as_code('4', cap)

    def _as_code(self, fg_bg_code: str, cap: TermInfo, /) -> str:
        if not cap.has_colors:
            return ''
        elif isinstance(self.data, int):
            return f'{fg_bg_code}{self.data}'
        elif cap.has_colors_true:
            return f'{fg_bg_code}8;2;{self.data[0]};{self.data[1]};{self.data[2]}'
        elif cap.has_colors_256:
            return f'{fg_bg_code}8;5;{_rgb_to_256(*self.data)}'
        else:
            return f'{fg_bg_code}{_rgb_to_8(*self.data)}'

    def __repr__(self) -> str:
        if isinstance(self.data, tuple):
            return f'<ColorValue #{self.data[0]:02X}{self.data[1]:02X}{self.data[2]:02X}>'
        else:
            return f'<ColorValue {self.data}>'


@dataclass(frozen=True, slots=True)
class Color:
    """Data about

    """

    fore: _t.Optional[ColorValue] = None
    back: _t.Optional[ColorValue] = None
    bold: bool = False
    dim: bool = False

    def __or__(self, other: 'Color', /):
        return Color(
            other.fore or self.fore,
            other.back or self.back,
            other.bold or self.bold,
            other.dim or self.dim,
        )

    def __ior__(self, other: 'Color', /):
        return self | other

    @classmethod
    def fore_from_rgb(cls, r: int, g: int, b: int) -> 'Color':
        return cls(fore=ColorValue.from_rgb(r, g, b))

    @classmethod
    def fore_from_hex(cls, h: str) -> 'Color':
        return cls(fore=ColorValue.from_hex(h))

    @classmethod
    def back_from_rgb(cls, r: int, g: int, b: int) -> 'Color':
        return cls(back=ColorValue.from_rgb(r, g, b))

    @classmethod
    def back_from_hex(cls, h: str) -> 'Color':
        return cls(back=ColorValue.from_hex(h))

    def darken(self, amount: float) -> 'Color':
        return dataclasses.replace(
            self,
            fore=self.fore.darken(amount) if self.fore else None,
            back=self.back.darken(amount) if self.back else None,
        )

    def lighten(self, amount: float) -> 'Color':
        return dataclasses.replace(
            self,
            fore=self.fore.lighten(amount) if self.fore else None,
            back=self.back.lighten(amount) if self.back else None,
        )

    @staticmethod
    def lerp(*colors: 'Color') -> _t.Callable[[float], 'Color']:
        if not colors:
            return lambda f, /: Color.NONE

        if len(colors) >= 2:
            fore_lerp = all(color.fore is not None and isinstance(color.fore.data, tuple) for color in colors)
            if fore_lerp:
                fore = ColorValue.lerp(*(color.fore for color in colors))  # type: ignore

            back_lerp = all(color.back is not None and isinstance(color.back.data, tuple) for color in colors)
            if back_lerp:
                back = ColorValue.lerp(*(color.back for color in colors))  # type: ignore

            if fore_lerp and back_lerp:
                return lambda f: dataclasses.replace(colors[0], fore=fore(f), back=back(f))
            elif fore_lerp:
                return lambda f: dataclasses.replace(colors[0], fore=fore(f))
            elif back_lerp:
                return lambda f: dataclasses.replace(colors[0], back=back(f))

        return lambda f, /: colors[0]


    def as_code(self, cap: TermInfo, /) -> str:
        """Convert this color into an ANSI escape code
        with respect to the given terminal capabilities.

        """

        if cap == TermColors.NONE:
            return ''

        codes = ['0']
        if self.fore:
            codes.append(self.fore._as_fore(cap))
        if self.back:
            codes.append(self.back._as_back(cap))
        if self.bold:
            codes.append('1')
        if self.dim:
            codes.append('2')
        return '\x1b[' + ';'.join(codes) + 'm'

    #: No color.
    NONE: _t.ClassVar['Color'] = lambda: Color()  # type: ignore

    #: Bold font style.
    STYLE_BOLD: _t.ClassVar['Color'] = lambda: Color(bold=True)  # type: ignore
    #: Dim font style.
    STYLE_DIM: _t.ClassVar['Color'] = lambda: Color(dim=True)  # type: ignore

    #: Normal foreground color.
    FORE_NORMAL: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(9))  # type: ignore
    #: Black foreground color.
    FORE_BLACK: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(0))  # type: ignore
    #: Red foreground color.
    FORE_RED: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(1))  # type: ignore
    #: Green foreground color.
    FORE_GREEN: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(2))  # type: ignore
    #: Yellow foreground color.
    FORE_YELLOW: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(3))  # type: ignore
    #: Blue foreground color.
    FORE_BLUE: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(4))  # type: ignore
    #: Magenta foreground color.
    FORE_MAGENTA: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(5))  # type: ignore
    #: Cyan foreground color.
    FORE_CYAN: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(6))  # type: ignore
    #: White foreground color.
    FORE_WHITE: _t.ClassVar['Color'] = lambda: Color(fore=ColorValue(7))  # type: ignore

    #: Normal background color.
    BACK_NORMAL: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(9))  # type: ignore
    #: Black background color.
    BACK_BLACK: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(0))  # type: ignore
    #: Red background color.
    BACK_RED: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(1))  # type: ignore
    #: Green background color.
    BACK_GREEN: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(2))  # type: ignore
    #: Yellow background color.
    BACK_YELLOW: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(3))  # type: ignore
    #: Blue background color.
    BACK_BLUE: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(4))  # type: ignore
    #: Magenta background color.
    BACK_MAGENTA: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(5))  # type: ignore
    #: Cyan background color.
    BACK_CYAN: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(6))  # type: ignore
    #: White background color.
    BACK_WHITE: _t.ClassVar['Color'] = lambda: Color(back=ColorValue(7))  # type: ignore

for _n, _v in vars(Color).items():
    if _n == _n.upper():
        setattr(Color, _n, _v())
del _n, _v  # type: ignore


def _rgb_to_256(r: int, g: int, b: int) -> int:
    closest_idx = lambda x, vals: min((abs(x - v), i) for i, v in enumerate(vals))[1]
    color_components = [0x00, 0x5f, 0x87, 0xaf, 0xd7, 0xff]

    if r == g == b:
        i = closest_idx(r, color_components + [0x08 + 10 * i for i in range(24)])
        if i >= len(color_components):
            return 232 + i - len(color_components)
        r, g, b = i, i, i
    else:
        r, g, b = [closest_idx(x, color_components) for x in (r, g, b)]
    return r * 36 + g * 6 + b + 16


def _rgb_to_8(r: int, g: int, b: int) -> int:
    return (1 if r >= 128 else 0) | (1 if g >= 128 else 0) << 1 | (1 if b >= 128 else 0) << 2


def _parse_hex(h: str) -> _t.Tuple[int, int, int]:
    if not re.match(r'^#[0-9a-fA-F]{6}$', h):
        raise ValueError(f'invalid hex string {h!r}')
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def _adjust_lightness(color: ColorValue, factor: float):
    if isinstance(color.data, tuple):
        r, g, b = color.data
        h, l, s = colorsys.rgb_to_hls(r / 0xff, g / 0xff, b / 0xff)
        if factor > 0:
            l = 1 - ((1 - l) * (1 - factor))
        elif factor < 0:
            l = l * (1 + factor)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return ColorValue.from_rgb(int(r * 0xff), int(g * 0xff), int(b * 0xff))
    else:
        return color

# lerp = ColorValue.lerp(
#     ColorValue.from_hex('#6719D5'),
#     ColorValue.from_hex('#C00FBA'),
# )
# for i in range(0, 81):
#     print(f'\x1b[{lerp(i / 80)._as_back(TermColors.ANSI_TRUE)}m ', end='')
# print('')
