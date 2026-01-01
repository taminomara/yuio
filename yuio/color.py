# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Text background and foreground color, as well as its style, is defined
by the :class:`yuio.color.Color` class. It stores RGB components and ANSI escape codes
for every aspect of text presentation.

This is a low-level module upon which :mod:`yuio.io` builds
its higher-level abstraction.

.. autoclass:: Color
   :members:

.. autoclass:: ColorValue
   :members:

.. autoclass:: ColorSupport
   :members:

"""

from __future__ import annotations

import colorsys
import dataclasses
import enum
import re
from dataclasses import dataclass

from typing import TYPE_CHECKING
from typing import ClassVar as _ClassVar

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "Color",
    "ColorSupport",
    "ColorValue",
]


@dataclass(frozen=True, slots=True)
class ColorValue:
    """
    Data about a single color.

    """

    data: int | str | tuple[int, int, int]
    """
    Color data.

    Can be one of three things:

    -   an int value represents an 8-bit color code (a value between ``0`` and ``7``).

        The actual color value for 8-bit color codes is controlled by the terminal's user.
        Therefore, it doesn't permit operations on colors.

        Depending on where this value is used (foreground or background), it will
        result in either ``3x`` or ``4x`` SGR parameter.

    -   an RGB-tuple represents a true color.

        When converted for a terminal that doesn't support true colors,
        it is automatically mapped to a corresponding 256- or 8-bit color.

        Depending on where this value is used (foreground or background), it will
        result in either ``38``/``3x`` or ``48``/``4x`` SGR parameter sequence.

    -   A string value represents `a parameter for the SGR command`__. Yuio will add this
        value to an SGR escape sequence as is, without any modification.

    __ https://en.wikipedia.org/wiki/ANSI_escape_code#Select_Graphic_Rendition_parameters

    """

    _NAMES = ["BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE"]

    @classmethod
    def from_rgb(cls, r: int, g: int, b: int, /) -> ColorValue:
        """
        Create a color value from rgb components.

        Each component should be between 0 and 255.

        :example:
            ::

                >>> ColorValue.from_rgb(0xA0, 0x1E, 0x9C)
                <ColorValue #A01E9C>

        """

        return cls((r, g, b))

    @classmethod
    def from_hex(cls, h: str, /) -> ColorValue:
        """
        Create a color value from a hex string.

        :example:
            ::

                >>> ColorValue.from_hex('#A01E9C')
                <ColorValue #A01E9C>

        """

        return cls(_parse_hex(h))

    def to_hex(self) -> str | None:
        """
        Return color in hex format with leading ``#``.

        :example:
            ::

                >>> a = ColorValue.from_hex('#A01E9C')
                >>> a.to_hex()
                '#A01E9C'

        """

        rgb = self.to_rgb()
        if rgb is not None:
            return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        else:
            return None

    def to_rgb(self) -> tuple[int, int, int] | None:
        """
        Return RGB components of the color.

        :example:
            ::

                >>> a = ColorValue.from_hex('#A01E9C')
                >>> a.to_rgb()
                (160, 30, 156)

        """

        if isinstance(self.data, tuple):
            return self.data
        else:
            return None

    def darken(self, amount: float, /) -> ColorValue:
        """
        Make this color darker by the given percentage.

        Amount should be between 0 and 1.

        :example:
            ::

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

    def lighten(self, amount: float, /) -> ColorValue:
        """
        Make this color lighter by the given percentage.

        Amount should be between 0 and 1.

        :example:
            ::

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

    def match_luminosity(self, other: ColorValue, /) -> ColorValue:
        """
        Set luminosity of this color equal to one of the other color.

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
    def lerp(*colors: ColorValue) -> _t.Callable[[float], ColorValue]:
        """
        Return a lambda that allows linear interpolation between several colors.

        If either color is a single ANSI escape code, the first color is always returned
        from the lambda.

        :param colors:
            colors of a gradient.
        :returns:
            a callable that allows interpolating between colors: it accepts a float
            value between ``1`` and ``0`` and returns a color.
        :raises:
            :class:`ValueError` if no colors are given.
        :example:
            ::

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
            raise ValueError("lerp expected at least 1 argument, got 0")
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
                    return ColorValue(
                        tuple(int(ca + f * (cb - ca)) for ca, cb in zip(a, b))  # type: ignore
                    )

            return lerp

    def _as_fore(self, color_support: ColorSupport, /) -> str:
        return self._as_code(color_support, fg_bg_prefix="3")

    def _as_back(self, color_support: ColorSupport, /) -> str:
        return self._as_code(color_support, fg_bg_prefix="4")

    def _as_code(self, color_support: ColorSupport, /, fg_bg_prefix: str) -> str:
        if color_support == ColorSupport.NONE:
            return ""  # pragma: no cover
        elif isinstance(self.data, int):
            return f"{fg_bg_prefix}{self.data}"
        elif isinstance(self.data, str):
            return self.data
        elif color_support == ColorSupport.ANSI_TRUE:
            return f"{fg_bg_prefix}8;2;{self.data[0]};{self.data[1]};{self.data[2]}"
        elif color_support == ColorSupport.ANSI_256:
            return f"{fg_bg_prefix}8;5;{_rgb_to_256(*self.data)}"
        else:
            return f"{fg_bg_prefix}{_rgb_to_8(*self.data)}"

    def __repr__(self) -> str:
        if isinstance(self.data, tuple):
            return f"<ColorValue {self.to_hex()}>"
        elif isinstance(self.data, int):
            if 0 <= self.data < len(self._NAMES):
                return f"<{self._NAMES[self.data]}>"
            else:
                return f"<ColorValue {self.data}>"
        else:
            return f"<ColorValue {self.data!r}>"


@dataclass(frozen=True, slots=True)
class Color:
    """
    Data about terminal output style. Contains
    foreground and background color, as well as text styles.

    When converted to an ANSI code and printed, a color completely overwrites a previous
    color that was used by a terminal. This behavior prevents different colors and styles
    bleeding one into another. So, for example, printing :data:`Color.STYLE_BOLD`
    and then :data:`Color.FORE_RED` will result in non-bold red text.

    Colors can be combined before printing, though::

        >>> Color.STYLE_BOLD | Color.FORE_RED  # Bold red
        <Color fore=<RED> bold=True>

    Yuio supports true RGB colors. They are automatically converted
    to 256- or 8-bit colors if needed.

    """

    fore: ColorValue | None = None
    """
    Foreground color.

    """

    back: ColorValue | None = None
    """
    Background color.

    """

    bold: bool | None = None
    """
    If true, render text as bold.

    """

    dim: bool | None = None
    """
    If true, render text as dim.

    """

    italic: bool | None = None
    """
    If true, render text in italic font.

    """

    underline: bool | None = None
    """
    If true, underline the text.

    """

    inverse: bool | None = None
    """
    If true, swap foreground and background.

    """

    blink: bool | None = None
    """
    If true, render blinking text.

    """

    def __or__(self, other: Color, /):
        return Color(
            other.fore if other.fore is not None else self.fore,
            other.back if other.back is not None else self.back,
            other.bold if other.bold is not None else self.bold,
            other.dim if other.dim is not None else self.dim,
            other.italic if other.italic is not None else self.italic,
            other.underline if other.underline is not None else self.underline,
            other.inverse if other.inverse is not None else self.inverse,
            other.blink if other.blink is not None else self.blink,
        )

    def __ior__(self, other: Color, /):
        return self | other

    @classmethod
    def fore_from_rgb(cls, r: int, g: int, b: int, **kwargs) -> Color:
        """
        Create a foreground color value from rgb components.

        Each component should be between 0 and 255.

        :example:
            ::

                >>> Color.fore_from_rgb(0xA0, 0x1E, 0x9C)
                <Color fore=<ColorValue #A01E9C>>

        """

        return cls(fore=ColorValue.from_rgb(r, g, b), **kwargs)

    @classmethod
    def fore_from_hex(cls, h: str, **kwargs) -> Color:
        """
        Create a foreground color value from a hex string.

        :example:
            ::

                >>> Color.fore_from_hex('#A01E9C')
                <Color fore=<ColorValue #A01E9C>>

        """

        return cls(fore=ColorValue.from_hex(h), **kwargs)

    @classmethod
    def back_from_rgb(cls, r: int, g: int, b: int, **kwargs) -> Color:
        """
        Create a background color value from rgb components.

        Each component should be between 0 and 255.

        :example:
            ::

                >>> Color.back_from_rgb(0xA0, 0x1E, 0x9C)
                <Color back=<ColorValue #A01E9C>>

        """

        return cls(back=ColorValue.from_rgb(r, g, b), **kwargs)

    @classmethod
    def back_from_hex(cls, h: str, **kwargs) -> Color:
        """
        Create a background color value from a hex string.

        :example:
            ::

                >>> Color.back_from_hex('#A01E9C')
                <Color back=<ColorValue #A01E9C>>

        """

        return cls(back=ColorValue.from_hex(h), **kwargs)

    @staticmethod
    def lerp(*colors: Color) -> _t.Callable[[float], Color]:
        """
        Return a lambda that allows linear interpolation between several colors.

        If either color is a single ANSI escape code, the first color is always returned
        from the lambda.

        :param colors:
            colors of a gradient.
        :returns:
            a callable that allows interpolating between colors: it accepts a float
            value between ``1`` and ``0`` and returns a color.
        :raises:
            :class:`ValueError` if no colors given.
        :example:
            ::

                >>> a = Color.fore_from_hex('#A01E9C')
                >>> b = Color.fore_from_hex('#22C60C')
                >>> lerp = Color.lerp(a, b)

                >>> lerp(0)
                <Color fore=<ColorValue #A01E9C>>
                >>> lerp(0.5)
                <Color fore=<ColorValue #617254>>
                >>> lerp(1)
                <Color fore=<ColorValue #22C60C>>

        """

        if not colors:
            raise ValueError("lerp expected at least 1 argument, got 0")
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
                return lambda f: dataclasses.replace(
                    colors[0],
                    fore=fore(f),  # type: ignore
                    back=back(f),  # type: ignore
                )
            elif fore_lerp:
                return lambda f: dataclasses.replace(colors[0], fore=fore(f))  # type: ignore
            elif back_lerp:
                return lambda f: dataclasses.replace(colors[0], back=back(f))  # type: ignore
            else:
                return lambda f, /: colors[0]

    def as_code(self, color_support: ColorSupport) -> str:
        """
        Convert this color into an ANSI escape code with respect to the given
        terminal capabilities.

        :param color_support:
            level of color support of a terminal.
        :returns:
            either ANSI escape code for this color or an empty string.

        """

        if color_support == ColorSupport.NONE:
            return ""

        codes = []
        if self.fore:
            codes.append(self.fore._as_fore(color_support))
        if self.back:
            codes.append(self.back._as_back(color_support))
        if self.bold:
            codes.append("1")
        if self.dim:
            codes.append("2")
        if self.italic:
            codes.append("3")
        if self.underline:
            codes.append("4")
        if self.blink:
            codes.append("5")
        if self.inverse:
            codes.append("7")
        if codes:
            return "\x1b[;" + ";".join(codes) + "m"
        else:
            return "\x1b[m"

    def __repr__(self):
        res = "<Color"
        for field in dataclasses.fields(self):
            if (value := getattr(self, field.name)) is not None:
                res += f" {field.name}={value!r}"
        res += ">"
        return res

    NONE: _ClassVar[Color] = dict()  # type: ignore
    """
    No color.

    """

    STYLE_BOLD: _ClassVar[Color] = dict(bold=True)  # type: ignore
    """
    Bold font style.

    """

    STYLE_DIM: _ClassVar[Color] = dict(dim=True)  # type: ignore
    """
    Dim font style.

    """

    STYLE_ITALIC: _ClassVar[Color] = dict(italic=True)  # type: ignore
    """
    Italic font style.

    """

    STYLE_UNDERLINE: _ClassVar[Color] = dict(underline=True)  # type: ignore
    """
    Underline font style.

    """

    STYLE_INVERSE: _ClassVar[Color] = dict(inverse=True)  # type: ignore
    """
    Swaps foreground and background colors.

    """

    STYLE_BLINK: _ClassVar[Color] = dict(blink=True)  # type: ignore
    """
    Makes the text blink.

    """

    STYLE_NORMAL: _ClassVar[Color] = dict(
        bold=False,
        dim=False,
        underline=False,
        italic=False,
        inverse=False,
        blink=False,
    )  # type: ignore
    """
    Normal style.

    """

    FORE_NORMAL: _ClassVar[Color] = dict(fore=ColorValue(9))  # type: ignore
    """
    Normal foreground color.

    """

    FORE_NORMAL_DIM: _ClassVar[Color] = dict(fore=ColorValue("2"))  # type: ignore
    """
    Normal foreground color rendered with dim setting.

    This is an alternative to bright black that works with
    most terminals and color schemes.

    """

    FORE_BLACK: _ClassVar[Color] = dict(fore=ColorValue(0))  # type: ignore
    """
    Black foreground color.

    .. warning::

       Avoid using this color, in most terminals it is the same as background color.
       Instead, use :attr:`~Color.FORE_NORMAL_DIM`.

    """

    FORE_RED: _ClassVar[Color] = dict(fore=ColorValue(1))  # type: ignore
    """
    Red foreground color.

    """

    FORE_GREEN: _ClassVar[Color] = dict(fore=ColorValue(2))  # type: ignore
    """
    Green foreground color.

    """

    FORE_YELLOW: _ClassVar[Color] = dict(fore=ColorValue(3))  # type: ignore
    """
    Yellow foreground color.

    """

    FORE_BLUE: _ClassVar[Color] = dict(fore=ColorValue(4))  # type: ignore
    """
    Blue foreground color.

    """

    FORE_MAGENTA: _ClassVar[Color] = dict(fore=ColorValue(5))  # type: ignore
    """
    Magenta foreground color.

    """

    FORE_CYAN: _ClassVar[Color] = dict(fore=ColorValue(6))  # type: ignore
    """
    Cyan foreground color.

    """

    FORE_WHITE: _ClassVar[Color] = dict(fore=ColorValue(7))  # type: ignore
    """
    White foreground color.

    .. warning::

        Avoid using it. In some terminals, notably in the Mac OS default terminal,
        it is unreadable.

    """

    BACK_NORMAL: _ClassVar[Color] = dict(back=ColorValue(9))  # type: ignore
    """
    Normal background color.

    """

    BACK_BLACK: _ClassVar[Color] = dict(back=ColorValue(0))  # type: ignore
    """
    Black background color.

    """

    BACK_RED: _ClassVar[Color] = dict(back=ColorValue(1))  # type: ignore
    """
    Red background color.

    """

    BACK_GREEN: _ClassVar[Color] = dict(back=ColorValue(2))  # type: ignore
    """
    Green background color.

    """

    BACK_YELLOW: _ClassVar[Color] = dict(back=ColorValue(3))  # type: ignore
    """
    Yellow background color.

    """

    BACK_BLUE: _ClassVar[Color] = dict(back=ColorValue(4))  # type: ignore
    """
    Blue background color.

    """

    BACK_MAGENTA: _ClassVar[Color] = dict(back=ColorValue(5))  # type: ignore
    """
    Magenta background color.

    """

    BACK_CYAN: _ClassVar[Color] = dict(back=ColorValue(6))  # type: ignore
    """
    Cyan background color.

    """

    BACK_WHITE: _ClassVar[Color] = dict(back=ColorValue(7))  # type: ignore
    """
    White background color.

    """


for _n, _v in vars(Color).items():
    if _n == _n.upper():
        setattr(Color, _n, Color(**_v))
del _n, _v  # type: ignore


def _parse_hex(h: str) -> tuple[int, int, int]:
    if not re.match(r"^#[0-9a-fA-F]{6}$", h):
        raise ValueError(f"invalid hex string {h!r}")
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore


class ColorSupport(enum.IntEnum):
    """
    Terminal's capability for coloring output.

    """

    NONE = 0
    """
    yuio.color.Color codes are not supported.

    """

    ANSI = 1
    """
    Only simple 8-bit color codes are supported.

    """

    ANSI_256 = 2
    """
    256-encoded colors are supported.

    """

    ANSI_TRUE = 3
    """
    True colors are supported.

    """

    def __repr__(self) -> str:
        return self.name


def _rgb_to_256(r: int, g: int, b: int) -> int:
    closest_idx = lambda x, vals: min((abs(x - v), i) for i, v in enumerate(vals))[1]
    color_components = [0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF]

    if r == g == b:
        i = closest_idx(r, color_components + [0x08 + 10 * i for i in range(24)])
        if i >= len(color_components):
            return 232 + i - len(color_components)
        r, g, b = i, i, i
    else:
        r, g, b = (closest_idx(x, color_components) for x in (r, g, b))
    return r * 36 + g * 6 + b + 16


def _rgb_to_8(r: int, g: int, b: int) -> int:
    return (
        (1 if r >= 128 else 0)
        | (1 if g >= 128 else 0) << 1
        | (1 if b >= 128 else 0) << 2
    )
