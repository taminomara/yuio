# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Everything to do with terminal output: detecting terminal capabilities,
working with colors and themes, formatting text.


Detecting terminal capabilities
-------------------------------

Terminal capabilities are stored in a :class:`Term` object.
You can get one for `stdin` and `stderr` streams by using the following
functions:

.. autofunction:: get_stdout_info

.. autofunction:: get_stderr_info

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


Assembling colors into themes
-----------------------------

The overall look and feel of a Yuio application is declared
in a :class:`Theme` object:

.. autoclass:: Theme
   :members:

.. autoclass:: DefaultTheme
   :members:


Colorizing and formatting text
------------------------------

The higher-level :mod:`io` module uses strings with xml-like color
tags to transfer information about line formatting. Here, on the lower level,
these strings are parsed and transformed into :class:`ColorizedString`:

.. autoclass:: ColorizedString
   :members:

.. autodata:: AnyString

.. autodata:: RawColorizedString


Utilities
---------

.. autofunction:: line_width

.. autofunction:: strip_color_tags

"""

import contextlib
import dataclasses
import colorsys
import enum
import functools
import os
import re
import sys

from dataclasses import dataclass
import typing as _t
import unicodedata


T = _t.TypeVar('T')

_STDIN: _t.TextIO = sys.__stdin__
_STDOUT: _t.TextIO = sys.__stdout__
_STDERR: _t.TextIO = sys.__stderr__


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


class InteractiveSupport(enum.IntEnum):
    """Terminal's capability for rendering interactive widgets.

    """

    #: Terminal can't render anything interactive.
    NONE = 0

    #: Terminal can move cursor and erase lines.
    MOVE_CURSOR = 1

    #: Terminal can process queries, enter CBREAK mode, etc.
    FULL = 2


@dataclass(frozen=True)
class Term:
    """Overall info about a terminal.

    """

    #: Terminal's output stream.
    stream: _t.TextIO

    #: Terminal's capability for coloring output.
    color_support: ColorSupport = ColorSupport.NONE

    #: Terminal's capability for rendering interactive widgets.
    interactive_support: InteractiveSupport = InteractiveSupport.NONE

    #: Background color of a terminal.
    background_color: _t.Optional[_t.Tuple[int, int, int]] = None

    #: Overall color theme of a terminal, i.e. dark or light.
    lightness: Lightness = Lightness.UNKNOWN

    @property
    def has_colors(self) -> bool:
        """Return true if terminal supports simple 8-bit color codes.

        """

        return self.color_support >= ColorSupport.ANSI

    @property
    def has_colors_256(self) -> bool:
        """Return true if terminal supports 256-encoded colors.

        """

        return self.color_support >= ColorSupport.ANSI_256

    @property
    def has_colors_true(self) -> bool:
        """Return true if terminal supports true colors.

        """

        return self.color_support >= ColorSupport.ANSI_TRUE

    @property
    def can_move_cursor(self) -> bool:
        """Return true if terminal can move cursor and erase lines.

        """

        return self.has_colors and self.interactive_support >= InteractiveSupport.MOVE_CURSOR

    @property
    def can_query_terminal(self) -> bool:
        """Return true if terminal can process queries, enter CBREAK mode, etc.

        This is an alias to :attr:`~Term.is_fully_interactive`.

        """

        return self.is_fully_interactive

    @property
    def is_fully_interactive(self) -> bool:
        """Return true if we're in a fully interactive environment.

        """

        return self.has_colors and self.interactive_support >= InteractiveSupport.FULL


@functools.cache
def get_stdout_info() -> Term:
    """Query info about stdout stream.

    """

    return _get_term_info(_STDOUT)


@functools.cache
def get_stderr_info() -> Term:
    """Query info about stderr stream.

    """

    return _get_term_info(_STDERR)


def get_cursor_position(term: Term) -> _t.Optional[_t.Tuple[int, int]]:
    """Query cursor position for the terminal.

    """

    if not term.can_query_terminal:
        return None
    else:
        return _get_dsr(term.stream)


_CI_ENV_VARS = [
    'TRAVIS', 'CIRCLECI', 'APPVEYOR', 'GITLAB_CI', 'BUILDKITE', 'DRONE', 'TEAMCITY_VERSION'
]


def _get_term_info(stream: _t.TextIO) -> Term:
    # Note: we don't rely on argparse to parse out flags and send them to us
    # because these functions can be called before parsing arguments.
    if '--force-no-color' in sys.argv or 'FORCE_NO_COLOR' in os.environ:
        return Term(stream)

    term = os.environ.get('TERM', '').lower()
    colorterm = os.environ.get('COLORTERM', '').lower()

    has_interactive_output = _is_interactive_output(stream)
    has_interactive_input = _is_interactive_input(_STDIN)
    is_foreground = _is_foreground(stream) and _is_foreground(_STDIN)

    color_support = ColorSupport.NONE
    in_ci = 'CI' in os.environ
    if '--force-color' in sys.argv or 'FORCE_COLOR' in os.environ:
        color_support = ColorSupport.ANSI
    if has_interactive_output:
        if os.name == 'nt':
            if _enable_vt_processing(stream):
                color_support = ColorSupport.ANSI_TRUE
        elif 'GITHUB_ACTIONS' in os.environ:
            color_support = ColorSupport.ANSI_TRUE
            in_ci = True
        elif any(ci in os.environ for ci in _CI_ENV_VARS):
            color_support = ColorSupport.ANSI
            in_ci = True
        elif colorterm in ('truecolor', '24bit') or term == 'xterm-kitty':
            color_support = ColorSupport.ANSI_TRUE
        elif colorterm in ('yes', 'true') or '256color' in term or term == 'screen':
            color_support = ColorSupport.ANSI_256
        elif term in 'linux' or 'color' in term or 'ansi' in term or 'xterm' in term:
            color_support = ColorSupport.ANSI

    interactive_support = InteractiveSupport.NONE
    lightness = Lightness.UNKNOWN
    background_color = None
    if is_foreground and color_support >= ColorSupport.ANSI and not in_ci:
        if has_interactive_output and has_interactive_input:
            interactive_support = InteractiveSupport.FULL
            lightness, background_color = _get_lightness(stream)
        else:
            interactive_support = InteractiveSupport.MOVE_CURSOR

    return Term(
        stream=stream,
        color_support=color_support,
        interactive_support=interactive_support,
        background_color=background_color,
        lightness=lightness,
    )


def _get_lightness(stream: _t.TextIO) -> _t.Tuple[Lightness, _t.Optional[_t.Tuple[int, int, int]]]:
    try:
        response = _query_term(stream, '\x1b]11;?\a')
        if response is None:
            return Lightness.UNKNOWN, None

        match = re.match(rb'^]11;rgb:([0-9a-f]{2,4})/([0-9a-f]{2,4})/([0-9a-f]{2,4})', response, re.IGNORECASE)
        if match is None:
            return Lightness.UNKNOWN, None

        r, g, b = (int(v, 16) // 16 ** (len(v) - 2) for v in match.groups())

        luma = (0.2627 * r + 0.6780 * g + 0.0593 * b) / 256

        if luma <= 0.2:
            return Lightness.DARK, (r, g, b)
        elif luma >=0.85:
            return Lightness.LIGHT, (r, g, b)
        else:
            return Lightness.UNKNOWN, (r, g, b)
    except Exception:
        return Lightness.UNKNOWN, None


def _get_dsr(stream: _t.TextIO) -> _t.Optional[_t.Tuple[int, int]]:
    try:
        response = _query_term(stream, '\x1b[6n', end_sequences=b'R')
        if response is None:
            return None

        match = re.match(rb'^\[(\d+);(\d+)R$', response, re.IGNORECASE)
        if match is None:
            return None

        return tuple(int(v) - 1 for v in match.groups())[::-1]
    except Exception:
        return None


def _query_term(stream: _t.TextIO, query: str, timeout: float = 0.3, end_sequences: _t.Union[bytes, _t.Tuple[bytes, ...]] = (b'\a', b'\x1b\\')) -> _t.Optional[bytes]:
    try:
        with _set_cbreak():
            while _kbhit():
                _getch()

            stream.write(query)
            stream.flush()

            if not _kbhit(timeout):
                return None

            if _getch() != b'\x1b':
                return None

            buf = b''
            while _kbhit() and not buf.endswith(end_sequences):
                buf += _getch()

            return buf
    except Exception:
        return None


def _is_tty(stream: _t.Optional[_t.IO]) -> bool:
    try:
        return stream is not None and stream.isatty()
    except Exception:
        return False


def _is_foreground(stream: _t.Optional[_t.IO]) -> bool:
    try:
        return stream is not None and os.getpgrp() == os.tcgetpgrp(stream.fileno())
    except Exception:
        return False


def _is_interactive_input(stream: _t.Optional[_t.IO]) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.readable()
    except Exception:
        return False


def _is_interactive_output(stream: _t.Optional[_t.IO]) -> bool:
    try:
        return stream is not None and _is_tty(stream) and stream.writable()
    except Exception:
        return False


# Platform-specific code for working with terminals.
if os.name == 'posix':
    import select
    import termios
    import tty

    @contextlib.contextmanager
    def _set_cbreak():
        prev_mode = termios.tcgetattr(_STDIN)
        tty.setcbreak(_STDIN, termios.TCSANOW)

        try:
            yield
        finally:
            termios.tcsetattr(_STDIN, termios.TCSAFLUSH, prev_mode)

    def _getch() -> bytes:
        return os.read(_STDIN.fileno(), 1)

    def _kbhit(timeout: float = 0) -> bool:
        return bool(select.select([_STDIN], [], [], timeout)[0])
else:
    @contextlib.contextmanager
    def _set_cbreak(stream: _t.TextIO):
        raise OSError('not supported')
        yield

    def _getch() -> bytes:
        raise OSError('not supported')

    def _kbhit(timeout: float = 0) -> bool:
        raise OSError('not supported')


if os.name == 'nt':
    import ctypes
    import msvcrt

    def _enable_vt_processing(stream: _t.TextIO) -> bool:
        try:
            version = sys.getwindowsversion()
            if version.major < 10 or version.build < 14931:
                return False

            stderr_handle = msvcrt.get_osfhandle(stream.fileno())
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
    def from_rgb(cls, r: int, g: int, b: int, /) -> 'ColorValue':
        """Create a color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> ColorValue.from_rgb(0xA0, 0x1E, 0x9C)
            <ColorValue #A01E9C>

        """

        return cls((r, g, b))

    @classmethod
    def from_hex(cls, h: str, /) -> 'ColorValue':
        """Create a color value from a hex string.

        Example::

            >>> ColorValue.from_hex('#A01E9C')
            <ColorValue #A01E9C>

        """

        return cls(_parse_hex(h))

    def darken(self, amount: float, /) -> 'ColorValue':
        """Make this color darker by the given percentage.

        Amount should be between 0 and 1.

        Example::

            >>> # Darken by 30%.
            ... ColorValue.from_hex('#A01E9C').darken(0.30)
            <ColorValue #70156D>

        """

        return _adjust_lightness(self, -amount)

    def lighten(self, amount: float, /) -> 'ColorValue':
        """Make this color lighter by the given percentage.

        Amount should be between 0 and 1.

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
            raise TypeError('lerp expected at least 1 argument, got 0')
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

    def _as_fore(self, term: Term, /) -> str:
        return self._as_code('3', term)

    def _as_back(self, term: Term, /) -> str:
        return self._as_code('4', term)

    def _as_code(self, fg_bg_code: str, term: Term, /) -> str:
        if not term.has_colors:
            return ''
        elif isinstance(self.data, int):
            return f'{fg_bg_code}{self.data}'
        elif term.has_colors_true:
            return f'{fg_bg_code}8;2;{self.data[0]};{self.data[1]};{self.data[2]}'
        elif term.has_colors_256:
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
    """Data about terminal output style. Contains
    foreground and background color, as well as text styles.

    This class only contains data about the color. It doesn't know anything about
    how to apply it to a terminal, or whether a terminal supports colors at all.
    These decisions are thus deferred to a lower level of API (see :meth:`Color.as_code`
    and :func:`join`).

    When converted to an ANSI code and printed, a color completely overwrites a previous
    color that was used by a terminal. This behavior prevents different colors and styles
    bleeding one into another. So, for example, printing :data:`Color.STYLE_BOLD`
    and then :data:`Color.FORE_RED` will result in non-bold red text.

    Colors can be combined before printing though::

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

    def __or__(self, other: 'Color', /):
        return Color(
            other.fore if other.fore is not None else self.fore,
            other.back if other.back is not None else self.back,
            other.bold if other.bold is not None else self.bold,
            other.dim if other.dim is not None else self.dim,
        )

    def __ior__(self, other: 'Color', /):
        return self | other

    @classmethod
    def fore_from_rgb(cls, r: int, g: int, b: int) -> 'Color':
        """Create a foreground color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> Color.fore_from_rgb(0xA0, 0x1E, 0x9C)
            Color(fore=<ColorValue #A01E9C>, back=None, bold=None, dim=None)

        """

        return cls(fore=ColorValue.from_rgb(r, g, b))

    @classmethod
    def fore_from_hex(cls, h: str) -> 'Color':
        """Create a foreground color value from a hex string.

        Example::

            >>> Color.fore_from_hex('#A01E9C')
            Color(fore=<ColorValue #A01E9C>, back=None, bold=None, dim=None)

        """

        return cls(fore=ColorValue.from_hex(h))

    @classmethod
    def back_from_rgb(cls, r: int, g: int, b: int) -> 'Color':
        """Create a background color value from rgb components.

        Each component should be between 0 and 255.

        Example::

            >>> Color.back_from_rgb(0xA0, 0x1E, 0x9C)
            Color(fore=None, back=<ColorValue #A01E9C>, bold=None, dim=None)

        """

        return cls(back=ColorValue.from_rgb(r, g, b))

    @classmethod
    def back_from_hex(cls, h: str) -> 'Color':
        """Create a background color value from a hex string.

        Example::

            >>> Color.back_from_hex('#A01E9C')
            Color(fore=None, back=<ColorValue #A01E9C>, bold=None, dim=None)

        """

        return cls(back=ColorValue.from_hex(h))

    def darken(self, amount: float) -> 'Color':
        """Make this color darker by the given percentage.

        Amount should be between 0 and 1.

        Example::

            >>> # Darken by 30%.
            ... Color.fore_from_hex('#A01E9C').darken(0.30)
            Color(fore=<ColorValue #70156D>, back=None, bold=None, dim=None)

        """

        return dataclasses.replace(
            self,
            fore=self.fore.darken(amount) if self.fore else None,
            back=self.back.darken(amount) if self.back else None,
        )

    def lighten(self, amount: float) -> 'Color':
        """Make this color lighter by the given percentage.

        Amount should be between 0 and 1.

        Example::

            >>> # Lighten by 30%.
            ... Color.fore_from_hex('#A01E9C').lighten(0.30)
            Color(fore=<ColorValue #DB42D6>, back=None, bold=None, dim=None)

        """

        return dataclasses.replace(
            self,
            fore=self.fore.lighten(amount) if self.fore else None,
            back=self.back.lighten(amount) if self.back else None,
        )

    @staticmethod
    def lerp(*colors: 'Color') -> _t.Callable[[float], 'Color']:
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
            raise TypeError('lerp expected at least 1 argument, got 0')

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


    def as_code(self, term: Term, /) -> str:
        """Convert this color into an ANSI escape code
        with respect to the given terminal capabilities.

        """

        if not term.has_colors:
            return ''

        codes = []
        if self.fore:
            codes.append(self.fore._as_fore(term))
        if self.back:
            codes.append(self.back._as_back(term))
        if self.bold:
            codes.append('1')
        if self.dim:
            codes.append('2')
        if codes:
            return '\x1b[;' + ';'.join(codes) + 'm'
        else:
            return '\x1b[m'

    #: No color.
    NONE: _t.ClassVar['Color'] = lambda: Color()  # type: ignore

    #: Bold font style.
    STYLE_BOLD: _t.ClassVar['Color'] = lambda: Color(bold=True)  # type: ignore
    #: Dim font style.
    STYLE_DIM: _t.ClassVar['Color'] = lambda: Color(dim=True)  # type: ignore
    #: Not bold nor dim.
    STYLE_NORMAL: _t.ClassVar['Color'] = lambda: Color(bold=False, dim=False)  # type: ignore

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
        if 1 >= factor > 0:
            l = 1 - ((1 - l) * (1 - factor))
        elif -1 <= factor < 0:
            l = l * (1 + factor)
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return ColorValue.from_rgb(int(r * 0xff), int(g * 0xff), int(b * 0xff))
    else:
        return color


class Theme:
    """Base class for Yuio themes.

    TODO

    """

    msg_decorations: _t.Dict[str, str] = {
        'heading': '⣿',
        'question': '>',
        'task': '>',

        # TODO: support these in widgets
        # 'menu_selected_item': '▶︎',
        # 'menu_default_item': '★',
        # 'menu_select': '#',
        # 'menu_search': '/',
    }

    progress_bar_width = 15
    progress_bar_start_symbol = ''
    progress_bar_end_symbol = ''
    progress_bar_done_symbol = '■'
    progress_bar_pending_symbol = '□'

    spinner_pattern = '⣤⣤⣤⠶⠛⠛⠛⠶'
    spinner_static_symbol = '⣿'
    spinner_update_rate_ms = 200

    #: Mapping of color paths to actual colors.
    #:
    #: Themes use color paths to describe styles and colors for different
    #: parts of an application. Color paths are similar to file paths.
    #: For example, a color for the filled part of the task's progress bar
    #: has path ``'task/progressbar/done'``.
    #:
    #: A color at a certain path is propagated to all sub-paths. For example,
    #: if ``'task/progressbar'`` is bold, and ``'task/progressbar/done'`` is green,
    #: the final color will be bold green.
    #:
    #: Each color path can be associated with either an instance of :class:`Color`,
    #: another path, or a list of colors and paths.
    #:
    #: If path is mapped to a :class:`Color`, then the path is associated
    #: with that particular color.
    #:
    #: If path is mapped to another path, then the path is associated with
    #: the color value for that other path (please don't create recursions here).
    #:
    #: If path is mapped to a list of colors and paths, then those colors and paths
    #: are combined.
    #:
    #: For example::
    #:
    #:     colors = {
    #:         'heading_color': Color.BOLD,
    #:         'error_color': Color.RED,
    #:         'tb/heading': ['heading_color', 'error_color'],
    #:     }
    #:
    #: Here, color of traceback's heading ``'tb/heading'`` will be bold and red.
    #:
    #: The base theme class provides colors for basic tags, such as `bold`, `red`,
    #: `code`, `note`, etc. :class:`DefaultTheme` expands on it, providing
    #:
    #: When deriving from a theme, you can override this mapping. Its elements will
    #: be merged with colors from all base classes.
    #:
    #: ..
    #:    TODO: document which paths are used by standard Yuio's widgets.
    colors: _t.Dict[str, _t.Union[str, Color, _t.List[_t.Union[str, Color]]]] = {
        'code': 'magenta',
        'note': 'green',

        'bold': Color.STYLE_BOLD,
        'b': 'bold',
        'dim': Color.STYLE_DIM,
        'd': 'dim',

        'normal': Color.FORE_NORMAL,
        'black': Color.FORE_BLACK,
        'red': Color.FORE_RED,
        'green': Color.FORE_GREEN,
        'yellow': Color.FORE_YELLOW,
        'blue': Color.FORE_BLUE,
        'magenta': Color.FORE_MAGENTA,
        'cyan': Color.FORE_CYAN,
        'white': Color.FORE_WHITE,
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        colors = {}
        for base in reversed(cls.__mro__):
            colors.update(getattr(base, 'colors', {}))
        cls.colors = colors

        msg_decorations = {}
        for base in reversed(cls.__mro__):
            msg_decorations.update(getattr(base, 'msg_decorations', {}))
        cls.msg_decorations = msg_decorations

    @_t.final
    @functools.cache
    def get_color(self, path: str, /) -> Color:
        """Lookup a color by path.

        """

        color = Color.NONE

        for prefix in self._prefixes(path.split('/')):
            if (res := self.colors.get('/'.join(prefix))) is not None:
                if isinstance(res, str):
                    color |= self.get_color(res)
                elif isinstance(res, list):
                    for c in res:
                        color |= (self.get_color(c) if isinstance(c, str) else c)
                else:
                    color |= res

        return color

    @staticmethod
    def _prefixes(it: _t.List[T]) -> _t.Iterable[_t.List[T]]:
        for i in range(1, len(it) + 1):
            yield it[:i]

    def colorize(
        self,
        s: str,
        /,
        *,
        default_color: _t.Union[Color, str] = Color.NONE,
    ) -> 'ColorizedString':
        """
        Colorize the given string.

        Apply `default_color` to the entire message, and process color tags
        within the message.

        """

        if isinstance(default_color, str):
            default_color = self.get_color(default_color)

        raw: "RawColorizedString" = []

        last_pos = 0
        stack = [default_color]

        raw.append(default_color)

        for tag in _TAG_RE.finditer(s):
            raw.append(s[last_pos:tag.start()])
            last_pos = tag.end()

            if name := tag.group('name'):
                color = stack[-1]
                for sub_name in name.split(','):
                    sub_name = sub_name.strip()
                    color = color | self.get_color(sub_name)
                raw.append(color)
                stack.append(color)
            elif len(stack) > 1:
                stack.pop()
                raw.append(stack[-1])

        raw.append(s[last_pos:])

        raw.append(Color.NONE)

        return ColorizedString(raw)


class DefaultTheme(Theme):
    """Default yuio theme. Adapts for terminal background color,
    if one can be detected.

    This theme defines *main colors*, which you can override by subclassing.

    - ``'heading_color'``: for headings,
    - ``'primary_color'``: for main text,
    - ``'accent_color'``: for visually highlighted elements,
    - ``'secondary_color'``: for visually dimmed elements,
    - ``'error_color'``: for everything that indicates an error,
    - ``'warning_color'``: for everything that indicates a warning,
    - ``'success_color'``: for everything that indicates a success,
    - ``'low_priority_color_a'``: for auxiliary elements such as help widget,
    - ``'low_priority_color_b'``: for auxiliary elements such as help widget.

    """

    colors = {
        # Basic theme colors, the rest is derived from them.
        'heading_color': 'bold',
        'primary_color': 'normal',
        'accent_color': 'magenta',
        'secondary_color': 'dim',
        'error_color': 'red',
        'warning_color': 'yellow',
        'success_color': 'green',
        'low_priority_color_a': 'dim',
        'low_priority_color_b': 'dim',

        # The rest...

        'code': 'magenta',
        'note': 'cyan',

        'msg/heading/decoration': 'accent_color',
        'msg/heading/text': 'heading_color',
        'msg/question/decoration': 'accent_color',
        'msg/question/text': 'heading_color',
        'msg/error': 'error_color',
        'msg/warning': 'warning_color',
        'msg/success': 'success_color',
        'msg/info': 'primary_color',
        'msg/hr': 'low_priority_color_a',
        'msg/group': 'accent_color',

        'log/plain_text': 'secondary_color',
        'log/asctime': 'secondary_color',
        'log/logger': 'secondary_color',
        'log/level': 'heading_color',
        'log/level/critical': 'error_color',
        'log/level/error': 'error_color',
        'log/level/warning': 'warning_color',
        'log/level/info': 'success_color',
        'log/level/debug': 'secondary_color',
        'log/message': 'primary_color',

        'tb/plain_text': 'secondary_color',
        'tb/heading': ['heading_color', 'error_color'],
        'tb/frame/usr': 'primary_color',
        'tb/frame/usr/file': 'primary_color',
        'tb/frame/usr/file/module': 'code',
        'tb/frame/usr/file/line': 'code',
        'tb/frame/usr/file/path': 'code',
        'tb/frame/usr/code': 'primary_color',
        'tb/frame/usr/highlight': 'primary_color',
        'tb/frame/lib': 'dim',
        'tb/frame/lib/file': 'tb/frame/usr/file',
        'tb/frame/lib/file/module': 'tb/frame/usr/file/module',
        'tb/frame/lib/file/line': 'tb/frame/usr/file/line',
        'tb/frame/lib/file/path': 'tb/frame/usr/file/path',
        'tb/frame/lib/code': 'tb/frame/usr/code',
        'tb/frame/lib/highlight': 'tb/frame/usr/highlight',
        'tb/message': 'tb/heading',

        'task/plain_text': 'secondary_color',
        'task/heading': 'heading_color',
        'task/comment': 'primary_color',
        'task/decoration': 'accent_color',
        'task/decoration/done': 'success_color',
        'task/decoration/error': 'error_color',
        'task/progress': 'task/plain_text',
        'task/progressbar/done': 'accent_color',
        'task/progressbar/pending': 'secondary_color',

        'cli/flag': 'note',
        'cli/metavar': 'code',
        'cli/section': 'msg/group',

        'menu/input/decoration': 'low_priority_color_a',
        'menu/input/text': 'primary_color',
        'menu/input/placeholder': 'low_priority_color_a',
        'menu/choice/normal/plain_text': 'secondary_color',
        'menu/choice/normal/decoration': 'primary_color',
        'menu/choice/normal/text': 'primary_color',
        'menu/choice/normal/text/dir': 'blue',
        'menu/choice/normal/text/exec': 'red',
        'menu/choice/normal/text/symlink': 'magenta',
        'menu/choice/normal/text/socket': 'green',
        'menu/choice/normal/text/pipe': 'yellow',
        'menu/choice/normal/text/block_device': ['cyan', 'bold'],
        'menu/choice/normal/text/char_device': ['yellow', 'bold'],
        'menu/choice/normal/comment': 'note',
        'menu/choice/normal/comment/original': "success_color",
        'menu/choice/normal/comment/corrected': "error_color",
        'menu/choice/active/plain_text': 'secondary_color',
        'menu/choice/active/decoration': 'accent_color',
        'menu/choice/active/text': 'accent_color',
        'menu/choice/active/comment': 'note',
        'menu/choice/active/comment/original': "success_color",
        'menu/choice/active/comment/corrected': "error_color",
        **{f"menu/choice/{status}/{role}/{color}": color
           for color in Theme.colors
           for status in ["normal", "active"]
           for role in ["plain_text", "decoration", "text", "comment"]},
        'menu/help/plain_text': 'low_priority_color_b',
        'menu/help/text': 'low_priority_color_b',
        'menu/help/key': 'low_priority_color_a',
        'menu/help/heading': ['heading_color', 'low_priority_color_a']
    }

    def __init__(self, term: Term) -> None:
        super().__init__()

        if term.lightness == Lightness.UNKNOWN or term.background_color is None:
            return

        background_color = ColorValue(term.background_color)

        if term.lightness.DARK:
            self.colors['low_priority_color_a'] = Color(fore=background_color.lighten(0.25))
            self.colors['low_priority_color_b'] = Color(fore=background_color.lighten(0.15))
        else:
            self.colors['low_priority_color_a'] = Color(fore=background_color.darken(0.25))
            self.colors['low_priority_color_b'] = Color(fore=background_color.darken(0.15))


def line_width(s: str, /) -> int:
    """Calculates string width when the string is displayed
    in a terminal.

    This function makes effort to detect wide characters
    such as emojis. If does not, however, works correctly
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
    correctly, I've decided to go with this simplistic implementation for now.

    """

    if s.isascii():
        # Fast path. Note that our renderer replaces unprintable characters
        # with spaces, so ascii strings always have width equal to their length.
        return len(s)
    else:
        # Long path. It kinda works, but not always, but most of the times...
        return sum(
            (unicodedata.east_asian_width(c) in 'WF') + 1
            for c in s if unicodedata.category(c)[0] not in 'MC'
        )


#: Raw colorized string (i.e. a list of strings and colors).
RawColorizedString: _t.TypeAlias = _t.List[_t.Union[str, Color]]

#: Any string (i.e. a :class:`str`, a raw colorized string, or a normal colorized string).
AnyString: _t.TypeAlias = _t.Union[str, "ColorizedString", "RawColorizedString", "Color"]


@_t.final
class ColorizedString:
    """A string with colors.

    This class is a wrapper over a list of strings and colors.
    Each color applies to strings after it, right until the next color.

    :class:`ColorizedString` supports some basic string operations.
    Most notable, it supports wide-character-aware wrapping (see :func:`line_width`),
    and ``%``-formatting.

    Unlike `str` instances, :class:`ColorizedString` is mutable through
    the ``+=`` operator.

    You can build a colorized string from raw parts,
    or you can use :meth:`Theme.colorize`.

    """

    def __init__(self, contents: _t.Optional["AnyString"] = None, /, *, explicit_newline: str = ''):
        self._items: "RawColorizedString" = []
        self._explicit_newline = explicit_newline
        if contents is not None:
            self += contents

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

        return sum(line_width(s) for s in self._items if isinstance(s, str))

    @functools.cached_property
    def len(self) -> int:
        """Line length in bytes, ignoring all colors.

        """

        return sum(len(s) for s in self._items if isinstance(s, str))

    def __len__(self) -> int:
        return self.len

    def iter(self) -> _t.Iterator[str]:
        """Iterate over code points in this string, ignoring all colors.

        If you want colors included, use :meth:`~ColorizedString.iter_raw`.

        """

        return self.__iter__()

    def iter_raw(self) -> _t.Iterator[_t.Union[str, Color]]:
        """Iterate over raw parts of the string,
        i.e. the underlying list of strings and colors.

        """
        return self._items.__iter__()

    def __iter__(self):
        for s in self._items:
            if isinstance(s, str):
                yield from s

    def wrap(
        self,
        width: int,
        /,
        *,
        break_on_hyphens: bool = True,
        preserve_spaces: bool = False,
        preserve_newlines: bool = True,
    ) -> _t.List['ColorizedString']:
        """Wrap a long line of text into multiple lines.

        If `break_on_hyphens` is `True` (default),
        lines can be broken after hyphens in hyphenated words.

        If `preserve_spaces` is `True`, all spaces are preserved.
        Otherwise, consecutive spaces are collapsed into a single space.
        Note that tabs are always treated as a single space.

        If `preserve_newlines` is `True` (default), text is additionally wrapped
        on newline characters. When this happens, the newline sequence that wrapped
        the line will be placed into :attr:`~ColorizedString.explicit_newline`.

        If `preserve_newlines` is `False`, newlines are treated as whitespaces.

        Example::

            >>> ColorizedString("hello, world!\\nit's a good day!").wrap(13)  # doctest: +NORMALIZE_WHITESPACE
            [<ColorizedString('hello, world!', explicit_newline='\\n')>,
             <ColorizedString("it's a good")>,
             <ColorizedString('day!')>]

        """

        return _TextWrapper(
            width,
            break_on_hyphens=break_on_hyphens,
            preserve_spaces=preserve_spaces,
            preserve_newlines=preserve_newlines,
        ).wrap(self)

    def percent_format(self, args: _t.Any) -> 'ColorizedString':
        """Format colorized string as if with ``%``-formatting
        (i.e. `old-style formatting`_).

        .. _old-style formatting: https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting

        ..
            >>> theme = Theme()

        Example::

            >>> line = theme.colorize("Hello, <c:b>%s!</c>")
            >>> line % "Username"
            <ColorizedString('Hello, Username!')>

        """

        return ColorizedString(_percent_format(self, args))

    def __mod__(self, args: _t.Any) -> 'ColorizedString':
        return self.percent_format(args)

    def __imod__(self, args: _t.Any) -> 'ColorizedString':
        self._items = _percent_format(self, args)

        self.__dict__.pop('width', None)
        self.__dict__.pop('len', None)

        return self

    def __add__(self, rhs: "AnyString") -> "ColorizedString":
        if isinstance(rhs, (str, Color)):
            return ColorizedString(self._items + [rhs])
        elif isinstance(rhs, list):
            return ColorizedString(self._items + rhs)
        elif isinstance(rhs, ColorizedString):
            return ColorizedString(self._items + rhs._items)
        else:
            return NotImplemented

    def __radd__(self, rhs: "AnyString") -> "ColorizedString":
        if isinstance(rhs, (str, Color)):
            return ColorizedString([rhs] + self._items)
        elif isinstance(rhs, list):
            return ColorizedString(rhs + self._items)
        elif isinstance(rhs, ColorizedString):
            return ColorizedString(rhs._items + self._items)
        else:
            return NotImplemented

    def __iadd__(self, rhs: "AnyString") -> "ColorizedString":
        if isinstance(rhs, (str, Color)):
            self._items.append(rhs)
        elif isinstance(rhs, list):
            self._items.extend(rhs)
        elif isinstance(rhs, ColorizedString):
            self._items.extend(rhs._items)
        else:
            return NotImplemented

        self.__dict__.pop('width', None)
        self.__dict__.pop('len', None)

        return self

    def merge(self, term: Term, /) -> str:
        """Convert this colorized string into a normal string
        with ANSI escape sequences.

        """

        return ''.join(s if isinstance(s, str) else s.as_code(term) for s in self._items)

    def write_to(self, term: Term, /):
        """Write the given string to a terminal.

        Will convert all colors into ANSI escape sequences
        suitable for the given terminals.

        Will not flush the terminal's stream.

        """

        term.stream.write(self.merge(term))

    def __str__(self) -> str:
        return ''.join(s for s in self._items if isinstance(s, str))

    def __repr__(self) -> str:
        if self.explicit_newline:
            return f"<ColorizedString({self.__str__()!r}, explicit_newline={self.explicit_newline!r})>"
        else:
            return f"<ColorizedString({self.__str__()!r})>"


_TAG_RE = re.compile(r'<c:(?P<name>[a-z0-9, _/@]+)>|</c>')


def strip_color_tags(s: str, /) -> str:
    """Remove all color tags from the given string.

    """

    return _TAG_RE.sub('', s)


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
    re.VERBOSE
)


def _percent_format(s: ColorizedString, args: _t.Any) -> "RawColorizedString":
    if not isinstance(args, (dict, tuple)):
        args = args,

    i = 0
    def repl(m: re.Match) -> str:
        nonlocal i
        groups = m.groupdict()
        if groups['format'] == '%':
            if m.group(0) != "%%":
                raise ValueError("unsupported format character '%'")
            return '%'

        if groups['mapping'] is not None:
            fmt_args = args
        elif isinstance(args, tuple):
            begin = i
            end = i = i + 1 + (m.group('width') == '*') + (m.group('precision') == '*')
            fmt_args = args[begin:end]
        elif i == 0:
            # We've passed a dict, and now want to format it with `%s`.
            # We allow that once. I.e. `"%s" % {}` is fine, `"%s %s" % {}` is not.
            fmt_args = args
            i = 1
        else:
            raise TypeError("not enough arguments for format string")

        return m.group(0) % fmt_args

    raw = [_S_SYNTAX.sub(repl, s) if isinstance(s, str) else s for s in s.iter_raw()]

    if isinstance(args, tuple) and i < len(args):
        raise TypeError("not all arguments converted during string formatting")

    return raw


_SPACE_TRANS = str.maketrans("\r\n\t\v\b\f", '      ')

_WORD_PUNCT = r'[\w!"\'&.,?]'
_LETTER = r'[^\d\W]'
_NOWHITESPACE = r'[^ \r\n\t\v\b\f]'

# Copied from textwrap with some modifications in newline handling
_WORDSEP_RE = re.compile(r'''
    ( # newlines and line feeds are matched one-by-one
        (?:\r\n|\r|\n)
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
    )''' % {'wp': _WORD_PUNCT, 'lt': _LETTER, 'nws': _NOWHITESPACE},
    re.VERBOSE)

_WORDSEP_SIMPLE_RE = re.compile(r"(\r\n|\r|\n|[ \t\v\b\f]+)")

class _TextWrapper:
    def __init__(
        self,
        width: int,
        /,
        *,
        break_on_hyphens: bool,
        preserve_spaces: bool,
        preserve_newlines: bool,
    ):
        if width <= 1:
            raise ValueError("width should be at least 2")

        self.width: int = width
        self.break_on_hyphens: bool = break_on_hyphens
        self.preserve_spaces: bool = preserve_spaces
        self.preserve_newlines: bool = preserve_newlines

        self.lines: _t.List[ColorizedString] = []

        self.current_line: "RawColorizedString" = []
        self.current_line_width: int = 0

    def _flush_line(self, explicit_newline=''):
        self.lines.append(ColorizedString(self.current_line, explicit_newline=explicit_newline))
        self.current_line = []
        self.current_line_width = 0

    def _append_word(self, word: str, word_width: int):
        self.current_line.append(word)
        self.current_line_width += word_width

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
            self.current_line.append(word)
            self.current_line_width += word_width

    def wrap(self, text: ColorizedString) -> _t.List[ColorizedString]:
        need_space_before_word = False
        at_line_beginning = True

        for item in text.iter_raw():
            if isinstance(item, Color):
                self.current_line.append(item)
                continue

            if self.break_on_hyphens is True:
                words = _WORDSEP_RE.split(item)
            else:
                words = _WORDSEP_SIMPLE_RE.split(item)

            for word in words:
                if not word:
                    continue

                if word in ('\r', '\n', '\r\n') and self.preserve_newlines:
                    self._flush_line(explicit_newline=word)
                    need_space_before_word = False
                    at_line_beginning = True
                    continue

                if word.isspace():
                    if at_line_beginning or self.preserve_spaces:
                        word = word.translate(_SPACE_TRANS)
                        self._append_word_with_breaks(word, len(word))
                    else:
                        need_space_before_word = True
                    continue

                word_width = line_width(word)

                if self.current_line_width + word_width + need_space_before_word <= self.width:
                    # Word fits onto the current line.
                    if need_space_before_word:
                        self._append_word(' ', 1)
                    self._append_word(word, word_width)
                else:
                    # Word doesn't fit, so we start a new line.
                    if self.current_line_width:
                        self._flush_line()
                    # We will break the word in the middle if it doesn't fit
                    # onto the whole line.
                    self._append_word_with_breaks(word, word_width)

                need_space_before_word = False
                at_line_beginning = False

        if self.current_line or not self.lines or self.lines[-1].explicit_newline:
            self._flush_line()

        return self.lines
