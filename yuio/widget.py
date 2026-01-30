# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Basic blocks for building interactive elements.

This is a low-level module upon which :mod:`yuio.io` builds
its higher-level abstraction.


Widget basics
-------------

All widgets are are derived from the :class:`Widget` class, where they implement
event handlers, layout and rendering routines. Specifically,
:meth:`Widget.layout` and :meth:`Widget.draw` are required to implement
a widget.

.. autoclass:: Widget
   :members:

.. autoclass:: Result
   :members:

.. autofunction:: bind

.. autoclass:: Key
   :members:

.. autoclass:: KeyboardEvent
   :members:


Drawing and rendering widgets
-----------------------------

Widgets are rendered through :class:`RenderContext`. It provides simple facilities
to print characters on screen and manipulate screen cursor.

.. autoclass:: RenderContext
   :members:


Stacking widgets together
-------------------------

To get help with drawing multiple widgets and setting their own frames,
you can use the :class:`VerticalLayout` class:

.. autoclass:: VerticalLayout

.. autoclass:: VerticalLayoutBuilder
   :members:


Widget help
-----------

Widgets automatically generate help: the help menu is available via the :kbd:`F1` key,
and there's also inline help that is displayed under the widget.

By default, help items are generated from event handler docstrings:
all event handlers that have them will be displayed in the help menu.

You can control which keybindings appear in the help menu and inline help
by supplying `show_in_inline_help` and `show_in_detailed_help` arguments
to the :func:`bind` function.

For even more detailed customization you can decorate an event handler with
the :func:`help` decorator:

.. autofunction:: help

Lastly, you can override :attr:`Widget.help_data` and generate
the :class:`WidgetHelp` yourself:

.. autoclass:: WidgetHelp
   :members:

.. class:: ActionKey

    A single key associated with an action.
    Can be either a hotkey or a string with an arbitrary description.

.. class:: ActionKeys

    A list of keys associated with an action.

.. class:: Action

    An action itself, i.e. a set of hotkeys and a description for them.


Pre-defined widgets
-------------------

.. autoclass:: Line

.. autoclass:: Text

.. autoclass:: Input

.. autoclass:: SecretInput

.. autoclass:: Grid

.. autoclass:: Option
   :members:

.. autoclass:: Choice

.. autoclass:: Multiselect

.. autoclass:: InputWithCompletion

.. autoclass:: Map

.. autoclass:: Apply

.. autoclass:: Task
    :members:
    :private-members:

"""

# ruff: noqa: RET503

from __future__ import annotations

import abc
import contextlib
import dataclasses
import enum
import functools
import math
import re
import string
import sys
import time
from dataclasses import dataclass

import yuio.color
import yuio.complete
import yuio.string
import yuio.term
from yuio.color import Color as _Color
from yuio.string import ColorizedString as _ColorizedString
from yuio.string import Esc as _Esc
from yuio.string import line_width as _line_width
from yuio.term import Term as _Term
from yuio.theme import Theme as _Theme
from yuio.util import _UNPRINTABLE_RE, _UNPRINTABLE_RE_WITHOUT_NL, _UNPRINTABLE_TRANS

import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "Action",
    "ActionKey",
    "ActionKeys",
    "Apply",
    "Choice",
    "Empty",
    "Grid",
    "Input",
    "InputWithCompletion",
    "Key",
    "KeyboardEvent",
    "Line",
    "Map",
    "Multiselect",
    "Option",
    "RenderContext",
    "Result",
    "SecretInput",
    "Task",
    "Text",
    "VerticalLayout",
    "VerticalLayoutBuilder",
    "Widget",
    "WidgetHelp",
    "bind",
    "help",
]

_SPACE_BETWEEN_COLUMNS = 2
_MIN_COLUMN_WIDTH = 10


T = _t.TypeVar("T")
U = _t.TypeVar("U")
T_co = _t.TypeVar("T_co", covariant=True)


class Key(enum.Enum):
    """
    Non-character keys.

    """

    ENTER = enum.auto()
    """
    :kbd:`Enter` key.

    """

    ESCAPE = enum.auto()
    """
    :kbd:`Escape` key.

    """

    INSERT = enum.auto()
    """
    :kbd:`Insert` key.

    """

    DELETE = enum.auto()
    """
    :kbd:`Delete` key.

    """

    BACKSPACE = enum.auto()
    """
    :kbd:`Backspace` key.

    """

    TAB = enum.auto()
    """
    :kbd:`Tab` key.

    """

    HOME = enum.auto()
    """
    :kbd:`Home` key.

    """

    END = enum.auto()
    """
    :kbd:`End` key.

    """

    PAGE_UP = enum.auto()
    """
    :kbd:`PageUp` key.

    """

    PAGE_DOWN = enum.auto()
    """
    :kbd:`PageDown` key.

    """

    ARROW_UP = enum.auto()
    """
    :kbd:`ArrowUp` key.

    """

    ARROW_DOWN = enum.auto()
    """
    :kbd:`ArrowDown` key.

    """

    ARROW_LEFT = enum.auto()
    """
    :kbd:`ArrowLeft` key.

    """

    ARROW_RIGHT = enum.auto()
    """
    :kbd:`ArrowRight` key.

    """

    F1 = enum.auto()
    """
    :kbd:`F1` key.

    """

    F2 = enum.auto()
    """
    :kbd:`F2` key.

    """

    F3 = enum.auto()
    """
    :kbd:`F3` key.

    """

    F4 = enum.auto()
    """
    :kbd:`F4` key.

    """

    F5 = enum.auto()
    """
    :kbd:`F5` key.

    """

    F6 = enum.auto()
    """
    :kbd:`F6` key.

    """

    F7 = enum.auto()
    """
    :kbd:`F7` key.

    """

    F8 = enum.auto()
    """
    :kbd:`F8` key.

    """

    F9 = enum.auto()
    """
    :kbd:`F9` key.

    """

    F10 = enum.auto()
    """
    :kbd:`F10` key.

    """

    F11 = enum.auto()
    """
    :kbd:`F11` key.

    """

    F12 = enum.auto()
    """
    :kbd:`F12` key.

    """

    PASTE = enum.auto()
    """
    Triggered when a text is pasted into a terminal.

    """

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True, slots=True)
class KeyboardEvent:
    """
    A single keyboard event.

    .. warning::

        Protocol for interacting with terminals is quite old, and not all terminals
        support all keystroke combinations.

        Use :flag:`python -m yuio.scripts.showkey` to check how your terminal reports
        keystrokes, and how Yuio interprets them.

    """

    key: Key | str
    """
    Which key was pressed? Can be a single character,
    or a :class:`Key` for non-character keys.

    """

    ctrl: bool = False
    """
    Whether a :kbd:`Ctrl` modifier was pressed with keystroke.

    For letter keys modified with control, the letter is always lowercase; if terminal
    supports reporting :kbd:`Shift` being pressed, the :attr:`~KeyboardEvent.shift`
    attribute will be set. This does not affect punctuation keys, though:

    .. skip-next:

    .. code-block:: python

        # `Ctrl+X` was pressed.
        KeyboardEvent("x", ctrl=True)

        # `Ctrl+Shift+X` was pressed. Not all terminals are able
        # to report this correctly, though.
        KeyboardEvent("x", ctrl=True, shift=True)

        # This can't happen.
        KeyboardEvent("X", ctrl=True)

        # `Ctrl+_` was pressed. On most keyboards, the actual keystroke
        # is `Ctrl+Shift+-`, but most terminals can't properly report this.
        KeyboardEvent("_", ctrl=True)

    """

    alt: bool = False
    """
    Whether an :kbd:`Alt` (:kbd:`Option` on macs) modifier was pressed with keystroke.

    """

    shift: bool = False
    """
    Whether a :kbd:`Shift` modifier was pressed with keystroke.

    Note that, when letters are typed with shift, they will not have this flag.
    Instead, their upper case version will be set as :attr:`~KeyboardEvent.key`:

    .. skip-next:

    .. code-block:: python

        KeyboardEvent("x")  # `X` was pressed.
        KeyboardEvent("X")  # `Shift+X` was pressed.

    .. warning::

        Only :kbd:`Shift+Tab` can be reliably reported by all terminals.

    """

    paste_str: str | None = dataclasses.field(default=None, compare=False, kw_only=True)
    """
    If `key` is :attr:`Key.PASTE`, this attribute will contain pasted string.

    """


@_t.final
class RenderContext:
    """
    A canvas onto which widgets render themselves.

    This class represents a canvas with size equal to the available space on the terminal.
    Like a real terminal, it has a character grid and a virtual cursor that can be moved
    around freely.

    Before each render, context's canvas is cleared, and then widgets print themselves onto it.
    When render ends, context compares new canvas with what's been rendered previously,
    and then updates those parts of the real terminal's grid that changed between renders.

    This approach allows simplifying widgets (they don't have to track changes and do conditional
    screen updates themselves), while still minimizing the amount of data that's sent between
    the program and the terminal. It is especially helpful with rendering larger widgets over ssh.

    """

    # For tests.
    _override_wh: tuple[int, int] | None = None

    def __init__(self, term: _Term, theme: _Theme, /):
        self._term: _Term = term
        self._theme: _Theme = theme

        # We have three levels of abstraction here.
        #
        # First, we have the TTY which our process attached to.
        # This TTY has cursor, current color,
        # and different drawing capabilities.
        #
        # Second, we have the canvas. This canvas has same dimensions
        # as the underlying TTY. Canvas' contents and actual TTY contents
        # are synced in `render` function.
        #
        # Finally, we have virtual cursor,
        # and a drawing frame which clips dimensions of a widget.
        #
        #
        # Drawing frame
        # ...................
        # . ┌────────┐      .
        # . │ hello  │      .
        # . │ world  │      .
        # . └────────┘      .
        # ...................
        #         ↓
        # Canvas
        # ┌─────────────────┐
        # │ > hello         │
        # │   world         │
        # │                 │
        # └─────────────────┘
        #         ↓
        # Real terminal
        # ┏━━━━━━━━━━━━━━━━━┯━━━┓
        # ┃ > hello         │   ┃
        # ┃   world         │   ┃
        # ┃                 │   ┃
        # ┠───────────VT100─┤◆◆◆┃
        # ┗█▇█▇█▇█▇█▇█▇█▇█▇█▇█▇█┛

        # Drawing frame and virtual cursor
        self._frame_x: int = 0
        self._frame_y: int = 0
        self._frame_w: int = 0
        self._frame_h: int = 0
        self._frame_cursor_x: int = 0  # relative to _frame_x
        self._frame_cursor_y: int = 0  # relative to _frame_y
        self._frame_cursor_color: str = ""

        # Canvas
        self._width: int = 0
        self._height: int = 0
        self._final_x: int = 0
        self._final_y: int = 0
        self._lines: list[list[str]] = []
        self._colors: list[list[str]] = []
        self._prev_lines: list[list[str]] = []
        self._prev_colors: list[list[str]] = []
        self._prev_urls: list[list[str]] = []

        # Rendering status
        self._full_redraw: bool = False
        self._term_x: int = 0
        self._term_y: int = 0
        self._term_color: str = ""
        self._max_term_y: int = 0
        self._out: list[str] = []
        self._bell: bool = False
        self._in_alternative_buffer: bool = False
        self._normal_buffer_term_x: int = 0
        self._normal_buffer_term_y: int = 0
        self._spinner_state: int = 0

        # Helpers
        self._none_color: str = _Color.NONE.as_code(term.color_support)

        # Used for tests and debug
        self._renders: int = 0
        self._bytes_rendered: int = 0
        self._total_bytes_rendered: int = 0

    @property
    def term(self) -> _Term:
        """
        Terminal where we render the widgets.

        """

        return self._term

    @property
    def theme(self) -> _Theme:
        """
        Current color theme.

        """

        return self._theme

    @property
    def spinner_state(self) -> int:
        """
        A timer that ticks once every
        :attr:`Theme.spinner_update_rate_ms <yuio.theme.Theme.spinner_update_rate_ms>`.

        """

        return self._spinner_state

    @contextlib.contextmanager
    def frame(
        self,
        x: int,
        y: int,
        /,
        *,
        width: int | None = None,
        height: int | None = None,
    ):
        """
        Override drawing frame.

        Widgets are always drawn in the frame's top-left corner,
        and they can take the entire frame size.

        The idea is that, if you want to draw a widget at specific coordinates,
        you make a frame and draw the widget inside said frame.

        When new frame is created, cursor's position and color are reset.
        When frame is dropped, they are restored.
        Therefore, drawing widgets in a frame will not affect current drawing state.

        ..
            >>> term = _Term(sys.stdout, sys.stdin)
            >>> theme = _Theme()
            >>> rc = RenderContext(term, theme)
            >>> rc._override_wh = (20, 5)

        Example::

            >>> rc = RenderContext(term, theme)  # doctest: +SKIP
            >>> rc.prepare()

            >>> # By default, our frame is located at (0, 0)...
            >>> rc.write("+")

            >>> # ...and spans the entire canvas.
            >>> print(rc.width, rc.height)
            20 5

            >>> # Let's write something at (4, 0).
            >>> rc.set_pos(4, 0)
            >>> rc.write("Hello, world!")

            >>> # Now we set our drawing frame to be at (2, 2).
            >>> with rc.frame(2, 2):
            ...     # Out current pos was reset to the frame's top-left corner,
            ...     # which is now (2, 2).
            ...     rc.write("+")
            ...
            ...     # Frame dimensions were automatically reduced.
            ...     print(rc.width, rc.height)
            ...
            ...     # Set pos and all other functions work relative
            ...     # to the current frame, so writing at (4, 0)
            ...     # in the current frame will result in text at (6, 2).
            ...     rc.set_pos(4, 0)
            ...     rc.write("Hello, world!")
            18 3

            >>> rc.render()  # doctest: +NORMALIZE_WHITESPACE
            +   Hello, world!
            <BLANKLINE>
              +   Hello, world!
            <BLANKLINE>
            <BLANKLINE>

        Usually you don't have to think about frames. If you want to stack
        multiple widgets one on top of another, simply use :class:`VerticalLayout`.
        In cases where it's not enough though, you'll have to call
        :meth:`~Widget.layout` for each of the nested widgets, and then manually
        create frames and execute :meth:`~Widget.draw` methods::

            class MyWidget(Widget):
                # Let's say we want to print a text indented by four spaces,
                # and limit its with by 15. And we also want to print a small
                # un-indented heading before it.

                def __init__(self):
                    # This is the text we'll print.
                    self._nested_widget = Text(
                        "very long paragraph which potentially can span multiple lines"
                    )

                def layout(self, rc: RenderContext) -> tuple[int, int]:
                    # The text will be placed at (4, 1), and we'll also limit
                    # its width. So we'll reflect those constrains
                    # by arranging a drawing frame.
                    with rc.frame(4, 1, width=min(rc.width - 4, 15)):
                        min_h, max_h = self._nested_widget.layout(rc)

                    # Our own widget will take as much space as the nested text,
                    # plus one line for our heading.
                    return min_h + 1, max_h + 1

                def draw(self, rc: RenderContext):
                    # Print a small heading.
                    rc.set_color_path("bold")
                    rc.write("Small heading")

                    # And draw our nested widget, controlling its position
                    # via a frame.
                    with rc.frame(4, 1, width=min(rc.width - 4, 15)):
                        self._nested_widget.draw(rc)

        """

        prev_frame_x = self._frame_x
        prev_frame_y = self._frame_y
        prev_frame_w = self._frame_w
        prev_frame_h = self._frame_h
        prev_frame_cursor_x = self._frame_cursor_x
        prev_frame_cursor_y = self._frame_cursor_y
        prev_frame_cursor_color = self._frame_cursor_color

        self._frame_x += x
        self._frame_y += y

        if width is not None:
            self._frame_w = width
        else:
            self._frame_w -= x
        if self._frame_w < 0:
            self._frame_w = 0

        if height is not None:
            self._frame_h = height
        else:
            self._frame_h -= y
        if self._frame_h < 0:
            self._frame_h = 0

        self._frame_cursor_x = 0
        self._frame_cursor_y = 0
        self._frame_cursor_color = self._none_color

        try:
            yield
        finally:
            self._frame_x = prev_frame_x
            self._frame_y = prev_frame_y
            self._frame_w = prev_frame_w
            self._frame_h = prev_frame_h
            self._frame_cursor_x = prev_frame_cursor_x
            self._frame_cursor_y = prev_frame_cursor_y
            self._frame_cursor_color = prev_frame_cursor_color

    @property
    def width(self) -> int:
        """
        Get width of the current frame.

        """

        return self._frame_w

    @property
    def height(self) -> int:
        """
        Get height of the current frame.

        """

        return self._frame_h

    @property
    def canvas_width(self) -> int:
        """
        Get width of the terminal.

        """

        return self._width

    @property
    def canvas_height(self) -> int:
        """
        Get height of the terminal.

        """

        return self._height

    def set_pos(self, x: int, y: int, /):
        """
        Set current cursor position within the frame.

        """

        self._frame_cursor_x = x
        self._frame_cursor_y = y

    def move_pos(self, dx: int, dy: int, /):
        """
        Move current cursor position by the given amount.

        """

        self._frame_cursor_x += dx
        self._frame_cursor_y += dy

    def new_line(self):
        """
        Move cursor to new line within the current frame.

        """

        self._frame_cursor_x = 0
        self._frame_cursor_y += 1

    def set_final_pos(self, x: int, y: int, /):
        """
        Set position where the cursor should end up
        after everything has been rendered.

        By default, cursor will end up at the beginning of the last line.
        Components such as :class:`Input` can modify this behavior
        and move the cursor into the correct position.

        """

        self._final_x = x + self._frame_x
        self._final_y = y + self._frame_y

    def set_color_path(self, path: str, /):
        """
        Set current color by fetching it from the theme by path.

        """

        self._frame_cursor_color = self._theme.get_color(path).as_code(
            self._term.color_support
        )

    def set_color(self, color: _Color, /):
        """
        Set current color.

        """

        self._frame_cursor_color = color.as_code(self._term.color_support)

    def reset_color(self):
        """
        Set current color to the default color of the terminal.

        """

        self._frame_cursor_color = self._none_color

    def get_msg_decoration(self, name: str, /) -> str:
        """
        Get message decoration by name.

        """

        return self.theme.get_msg_decoration(name, is_unicode=self.term.is_unicode)

    def write(self, text: yuio.string.AnyString, /, *, max_width: int | None = None):
        """
        Write string at the current position using the current color.
        Move cursor while printing.

        While the displayed text will not be clipped at frame's borders,
        its width can be limited by passing `max_width`. Note that
        ``rc.write(text, max_width)`` is not the same
        as ``rc.write(text[:max_width])``, because the later case
        doesn't account for double-width characters.

        All whitespace characters in the text, including tabs and newlines,
        will be treated as single spaces. If you need to print multiline text,
        use :meth:`yuio.string.ColorizedString.wrap` and :meth:`~RenderContext.write_text`.

        ..
            >>> term = _Term(sys.stdout, sys.stdin)
            >>> theme = _Theme()
            >>> rc = RenderContext(term, theme)
            >>> rc._override_wh = (20, 5)

        Example::

            >>> rc = RenderContext(term, theme)  # doctest: +SKIP
            >>> rc.prepare()

            >>> rc.write("Hello, world!")
            >>> rc.new_line()
            >>> rc.write("Hello,\\nworld!")
            >>> rc.new_line()
            >>> rc.write(
            ...     "Hello, 🌍!<this text will be clipped>",
            ...     max_width=10
            ... )
            >>> rc.new_line()
            >>> rc.write(
            ...     "Hello, 🌍!<this text will be clipped>"[:10]
            ... )
            >>> rc.new_line()

            >>> rc.render()
            Hello, world!
            Hello, world!
            Hello, 🌍!
            Hello, 🌍!<
            <BLANKLINE>

        Notice that ``"\\n"`` on the second line was replaced with a space.
        Notice also that the last line wasn't properly clipped.

        """

        if not isinstance(text, _ColorizedString):
            text = _ColorizedString(text, _isolate_colors=False)

        x = self._frame_x + self._frame_cursor_x
        y = self._frame_y + self._frame_cursor_y

        max_x = self._width
        if max_width is not None:
            max_x = min(max_x, x + max_width)
            self._frame_cursor_x = min(self._frame_cursor_x + text.width, x + max_width)
        else:
            self._frame_cursor_x = self._frame_cursor_x + text.width

        if not 0 <= y < self._height:
            for s in text:
                if isinstance(s, _Color):
                    self._frame_cursor_color = s.as_code(self._term.color_support)
            return

        ll = self._lines[y]
        cc = self._colors[y]
        uu = self._urls[y]

        url = ""

        for s in text:
            if isinstance(s, _Color):
                self._frame_cursor_color = s.as_code(self._term.color_support)
                continue
            elif s in (yuio.string.NO_WRAP_START, yuio.string.NO_WRAP_END):
                continue
            elif isinstance(s, yuio.string.LinkMarker):
                url = s.url or ""
                continue

            s = s.translate(_UNPRINTABLE_TRANS)

            if s.isascii():
                # Fast track.
                if x + len(s) <= 0:
                    # We're beyond the left terminal border.
                    x += len(s)
                    continue

                slice_begin = 0
                if x < 0:
                    # We're partially beyond the left terminal border.
                    slice_begin = -x
                    x = 0

                if x >= max_x:
                    # We're beyond the right terminal border.
                    x += len(s) - slice_begin
                    continue

                slice_end = len(s)
                if x + len(s) - slice_begin > max_x:
                    # We're partially beyond the right terminal border.
                    slice_end = slice_begin + max_x - x

                l = slice_end - slice_begin
                ll[x : x + l] = s[slice_begin:slice_end]
                cc[x : x + l] = [self._frame_cursor_color] * l
                uu[x : x + l] = [url] * l
                x += l
                continue

            for c in s:
                cw = _line_width(c)
                if x + cw <= 0:
                    # We're beyond the left terminal border.
                    x += cw
                    continue
                elif x < 0:
                    # This character was split in half by the terminal border.
                    ll[: x + cw] = [" "] * (x + cw)
                    cc[: x + cw] = [self._none_color] * (x + cw)
                    uu[: x + cw] = [url] * (x + cw)
                    x += cw
                    continue
                elif cw > 0 and x >= max_x:
                    # We're beyond the right terminal border.
                    x += cw
                    break
                elif x + cw > max_x:
                    # This character was split in half by the terminal border.
                    ll[x:max_x] = " " * (max_x - x)
                    cc[x:max_x] = [self._frame_cursor_color] * (max_x - x)
                    uu[x:max_x] = [url] * (max_x - x)
                    x += cw
                    break

                if cw == 0:
                    # This is a zero-width character.
                    # We'll append it to the previous cell.
                    if x > 0:
                        ll[x - 1] += c
                    continue

                ll[x] = c
                cc[x] = self._frame_cursor_color
                uu[x] = url

                x += 1
                cw -= 1
                if cw:
                    ll[x : x + cw] = [""] * cw
                    cc[x : x + cw] = [self._frame_cursor_color] * cw
                    uu[x : x + cw] = [url] * cw
                    x += cw

    def write_text(
        self,
        lines: _t.Iterable[yuio.string.AnyString],
        /,
        *,
        max_width: int | None = None,
    ):
        """
        Write multiple lines.

        Each line is printed using :meth:`~RenderContext.write`,
        so newline characters and tabs within each line are replaced with spaces.
        Use :meth:`yuio.string.ColorizedString.wrap` to properly handle them.

        After each line, the cursor is moved one line down,
        and back to its original horizontal position.

        ..
            >>> term = _Term(sys.stdout, sys.stdin)
            >>> theme = _Theme()
            >>> rc = RenderContext(term, theme)
            >>> rc._override_wh = (20, 5)

        Example::

            >>> rc = RenderContext(term, theme)  # doctest: +SKIP
            >>> rc.prepare()

            >>> # Cursor is at (0, 0).
            >>> rc.write("+ > ")

            >>> # First line is printed at the cursor's position.
            >>> # All consequent lines are horizontally aligned with first line.
            >>> rc.write_text(["Hello,", "world!"])

            >>> # Cursor is at the last line.
            >>> rc.write("+")

            >>> rc.render()  # doctest: +NORMALIZE_WHITESPACE
            + > Hello,
                world!+
            <BLANKLINE>
            <BLANKLINE>
            <BLANKLINE>

        """

        x = self._frame_cursor_x

        for i, line in enumerate(lines):
            if i > 0:
                self._frame_cursor_x = x
                self._frame_cursor_y += 1

            self.write(line, max_width=max_width)

    def bell(self):
        """
        Ring a terminal bell.

        """

        self._bell = True

    def make_repr_context(
        self,
        *,
        multiline: bool | None = None,
        highlighted: bool | None = None,
        max_depth: int | None = None,
        width: int | None = None,
    ) -> yuio.string.ReprContext:
        """
        Create a new :class:`~yuio.string.ReprContext` for rendering colorized strings
        inside widgets.

        :param multiline:
            sets initial value for
            :attr:`ReprContext.multiline <yuio.string.ReprContext.multiline>`.
        :param highlighted:
            sets initial value for
            :attr:`ReprContext.highlighted <yuio.string.ReprContext.highlighted>`.
        :param max_depth:
            sets initial value for
            :attr:`ReprContext.max_depth <yuio.string.ReprContext.max_depth>`.
        :param width:
            sets initial value for
            :attr:`ReprContext.width <yuio.string.ReprContext.width>`.
            If not given, uses current frame's width.
        :returns:
            a new repr context suitable for rendering colorized strings.

        """

        if width is None:
            width = self._frame_w
        return yuio.string.ReprContext(
            term=self._term,
            theme=self._theme,
            multiline=multiline,
            highlighted=highlighted,
            max_depth=max_depth,
            width=width,
        )

    @functools.cached_property
    def _update_rate_us(self) -> int:
        update_rate_ms = max(self._theme.spinner_update_rate_ms, 1)
        while update_rate_ms < 50:
            update_rate_ms *= 2
        while update_rate_ms > 250:
            update_rate_ms //= 2
        return int(update_rate_ms * 1000)

    def prepare(
        self,
        *,
        full_redraw: bool = False,
        alternative_buffer: bool = False,
        reset_term_pos: bool = False,
    ):
        """
        Reset output canvas and prepare context for a new round of widget formatting.

        """

        if self._override_wh:
            width, height = self._override_wh
        else:
            size = yuio.term.get_tty_size(fallback=(self._theme.fallback_width, 24))
            width = size.columns
            height = size.lines

        full_redraw = full_redraw or self._width != width or self._height != height

        if self._in_alternative_buffer != alternative_buffer:
            full_redraw = True
            self._in_alternative_buffer = alternative_buffer
            if alternative_buffer:
                self._out.append("\x1b[<u\x1b[?1049h\x1b[m\x1b[2J\x1b[H\x1b[>1u")
                self._normal_buffer_term_x = self._term_x
                self._normal_buffer_term_y = self._term_y
                self._term_x, self._term_y = 0, 0
                self._term_color = self._none_color
            else:
                self._out.append("\x1b[<u\x1b[?1049l\x1b[m\x1b[>1u")
                self._term_x = self._normal_buffer_term_x
                self._term_y = self._normal_buffer_term_y
                self._term_color = self._none_color

        if reset_term_pos:
            self._term_x, self._term_y = 0, 0
            full_redraw = True

        # Drawing frame and virtual cursor
        self._frame_x = 0
        self._frame_y = 0
        self._frame_w = width
        self._frame_h = height
        self._frame_cursor_x = 0
        self._frame_cursor_y = 0
        self._frame_cursor_color = self._none_color

        # Canvas
        self._width = width
        self._height = height
        self._final_x = 0
        self._final_y = 0
        if full_redraw:
            self._max_term_y = 0
            self._prev_lines, self._prev_colors, self._prev_urls = (
                self._make_empty_canvas()
            )
        else:
            self._prev_lines = self._lines
            self._prev_colors = self._colors
            self._prev_urls = self._urls
        self._lines, self._colors, self._urls = self._make_empty_canvas()

        # Rendering status
        self._full_redraw = full_redraw

        start_ns = time.monotonic_ns()
        now_us = start_ns // 1000
        now_us -= now_us % self._update_rate_us
        self._spinner_state = now_us // self.theme.spinner_update_rate_ms // 1000

    def clear_screen(self):
        """
        Clear screen and prepare for a full redraw.

        """

        self._out.append("\x1b[2J\x1b[1H")
        self._term_x, self._term_y = 0, 0
        self.prepare(full_redraw=True, alternative_buffer=self._in_alternative_buffer)

    def _make_empty_canvas(
        self,
    ) -> tuple[list[list[str]], list[list[str]], list[list[str]]]:
        lines = [l[:] for l in [[" "] * self._width] * self._height]
        colors = [
            c[:] for c in [[self._frame_cursor_color] * self._width] * self._height
        ]
        urls = [l[:] for l in [[""] * self._width] * self._height]
        return lines, colors, urls

    def render(self):
        """
        Render current canvas onto the terminal.

        """

        if not self.term.ostream_is_tty:
            # For tests. Widgets can't work with dumb terminals
            self._render_dumb()
            return

        if self._bell:
            self._out.append("\a")
            self._bell = False

        if self._full_redraw:
            self._move_term_cursor(0, 0)
            self._out.append("\x1b[J")

        term_url = ""

        for y in range(self._height):
            line = self._lines[y]

            for x in range(self._width):
                prev_color = self._prev_colors[y][x]
                color = self._colors[y][x]
                url = self._urls[y][x]

                if (
                    color != prev_color
                    or line[x] != self._prev_lines[y][x]
                    or url != self._prev_urls[y][x]
                ):
                    self._move_term_cursor(x, y)

                    if color != self._term_color:
                        self._out.append(color)
                        self._term_color = color

                    if url != term_url:
                        self._out.append("\x1b]8;;")
                        self._out.append(url)
                        self._out.append("\x1b\\")
                        term_url = url

                    self._out.append(line[x])
                    self._term_x += 1

        if term_url:
            self._out.append("\x1b]8;;\x1b\\")

        final_x = max(0, min(self._width - 1, self._final_x))
        final_y = max(0, min(self._height - 1, self._final_y))
        self._move_term_cursor(final_x, final_y)

        rendered = "".join(self._out)
        self._term.ostream.write(rendered)
        self._term.ostream.flush()
        self._out.clear()

        if yuio._debug:
            self._renders += 1
            self._bytes_rendered = len(rendered.encode())
            self._total_bytes_rendered += self._bytes_rendered

            debug_msg = f"n={self._renders:>04},r={self._bytes_rendered:>04},t={self._total_bytes_rendered:>04}"
            term_x, term_y = self._term_x, self._term_y
            self._move_term_cursor(self._width - len(debug_msg), 0)
            color = yuio.color.Color.STYLE_INVERSE | yuio.color.Color.FORE_CYAN
            self._out.append(color.as_code(self._term.color_support))
            self._out.append(debug_msg)
            self._out.append(self._term_color)
            self._move_term_cursor(term_x, term_y)

            self._term.ostream.write("".join(self._out))
            self._term.ostream.flush()
            self._out.clear()

    def finalize(self):
        """
        Erase any rendered widget and move cursor to the initial position.

        """

        self.prepare(full_redraw=True)

        self._move_term_cursor(0, 0)
        self._out.append("\x1b[J")
        self._out.append(self._none_color)
        self._term.ostream.write("".join(self._out))
        self._term.ostream.flush()
        self._out.clear()
        self._term_color = self._none_color

    def _move_term_cursor(self, x: int, y: int):
        dy = y - self._term_y
        if y > self._max_term_y:
            self._out.append("\n" * dy)
            self._term_x = 0
        elif dy > 0:
            self._out.append(f"\x1b[{dy}B")
        elif dy < 0:
            self._out.append(f"\x1b[{-dy}A")
        self._term_y = y
        self._max_term_y = max(self._max_term_y, y)

        if x != self._term_x:
            self._out.append(f"\x1b[{x + 1}G")
        self._term_x = x

    def _render_dumb(self):
        prev_printed_color = self._none_color

        for line, colors in zip(self._lines, self._colors):
            for ch, color in zip(line, colors):
                if prev_printed_color != color:
                    self._out.append(color)
                    prev_printed_color = color
                self._out.append(ch)
            self._out.append("\n")

        self._term.ostream.writelines(
            # Trim trailing spaces for doctests.
            re.sub(r" +$", "\n", line, flags=re.MULTILINE)
            for line in "".join(self._out).splitlines()
        )


@dataclass(frozen=True, slots=True)
class Result(_t.Generic[T_co]):
    """
    Result of a widget run.

    We have to wrap the return value of event processors into this class.
    Otherwise we won't be able to distinguish between returning `None`
    as result of a ``Widget[None]``, and not returning anything.

    """

    value: T_co
    """
    Result of a widget run.

    """


class Widget(abc.ABC, _t.Generic[T_co]):
    """
    Base class for all interactive console elements.

    Widgets are displayed with their :meth:`~Widget.run` method.
    They always go through the same event loop:

    .. raw:: html

        <p>
        <pre class="mermaid">
        flowchart TD
        Start([Start]) --> Layout["`layout()`"]
        Layout --> Draw["`draw()`"]
        Draw -->|Wait for keyboard event| Event["`Event()`"]
        Event --> Result{{Returned result?}}
        Result -->|no| Layout
        Result -->|yes| Finish([Finish])
        </pre>
        </p>

    Widgets run indefinitely until they stop themselves and return a value.
    For example, :class:`Input` will return when user presses :kbd:`Enter`.
    When widget needs to stop, it can return the :meth:`Result` class
    from its event handler.

    For typing purposes, :class:`Widget` is generic. That is, ``Widget[T]``
    returns ``T`` from its :meth:`~Widget.run` method. So, :class:`Input`,
    for example, is ``Widget[str]``.

    Some widgets are ``Widget[Never]`` (see :class:`typing.Never`), indicating that
    they don't ever stop. Others are ``Widget[None]``, indicating that they stop,
    but don't return a value.

    """

    __bindings: typing.ClassVar[dict[KeyboardEvent, _t.Callable[[_t.Any], _t.Any]]]
    __callbacks: typing.ClassVar[list[object]]

    __in_help_menu: bool = False
    __bell: bool = False

    _cur_event: KeyboardEvent | None = None
    """
    Current event that is being processed.
    Guaranteed to be not :data:`None` inside event handlers.

    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        cls.__bindings = {}
        cls.__callbacks = []

        event_handler_names = []
        for base in reversed(cls.__mro__):
            for name, cb in base.__dict__.items():
                if (
                    hasattr(cb, "__yuio_keybindings__")
                    and name not in event_handler_names
                ):
                    event_handler_names.append(name)

        for name in event_handler_names:
            cb = getattr(cls, name, None)
            if cb is not None and hasattr(cb, "__yuio_keybindings__"):
                bindings: list[_Binding] = cb.__yuio_keybindings__
                cls.__bindings.update((binding.event, cb) for binding in bindings)
                cls.__callbacks.append(cb)

    def event(self, e: KeyboardEvent, /) -> Result[T_co] | None:
        """
        Handle incoming keyboard event.

        By default, this function dispatches event to handlers registered
        via :func:`bind`. If no handler is found,
        it calls :meth:`~Widget.default_event_handler`.

        """

        self._cur_event = e
        if handler := self.__bindings.get(e):
            return handler(self)
        else:
            return self.default_event_handler(e)

    def default_event_handler(self, e: KeyboardEvent, /) -> Result[T_co] | None:
        """
        Process any event that wasn't caught by other event handlers.

        """

    @abc.abstractmethod
    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        """
        Prepare widget for drawing, and recalculate its dimensions
        according to new frame dimensions.

        Yuio's widgets always take all available width. They should return
        their minimum height that they will definitely take, and their maximum
        height that they can potentially take.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def draw(self, rc: RenderContext, /):
        """
        Draw the widget.

        Render context's drawing frame dimensions are guaranteed to be between
        the minimum and the maximum height returned from the last call
        to :meth:`~Widget.layout`.

        """

        raise NotImplementedError()

    @_t.final
    def run(self, term: _Term, theme: _Theme, /) -> T_co:
        """
        Read user input and run the widget.

        """

        if not term.can_run_widgets:
            raise RuntimeError("terminal doesn't support rendering widgets")

        with yuio.term._enter_raw_mode(
            term.ostream, term.istream, bracketed_paste=True, modify_keyboard=True
        ):
            rc = RenderContext(term, theme)

            events = _event_stream(term.ostream, term.istream)

            try:
                while True:
                    rc.prepare(alternative_buffer=self.__in_help_menu)

                    height = rc.height
                    if self.__in_help_menu:
                        min_h, max_h = self.__help_menu_layout(rc)
                        inline_help_height = 0
                    else:
                        with rc.frame(0, 0):
                            inline_help_height = self.__help_menu_layout_inline(rc)[0]
                        if height > inline_help_height:
                            height -= inline_help_height
                        with rc.frame(0, 0, height=height):
                            min_h, max_h = self.layout(rc)
                        max_h = max(min_h, min(max_h, height))
                    rc.set_final_pos(0, max_h + inline_help_height)
                    if self.__in_help_menu:
                        self.__help_menu_draw(rc)
                    else:
                        with rc.frame(0, 0, height=max_h):
                            self.draw(rc)
                        if max_h < rc.height:
                            with rc.frame(0, max_h, height=rc.height - max_h):
                                self.__help_menu_draw_inline(rc)

                    if self.__bell:
                        rc.bell()
                        self.__bell = False
                    rc.render()

                    try:
                        event = next(events)
                    except StopIteration:
                        assert False, "_event_stream supposed to be infinite"

                    if event == KeyboardEvent("c", ctrl=True):
                        raise KeyboardInterrupt()
                    elif event == KeyboardEvent("l", ctrl=True):
                        rc.clear_screen()
                    elif event == KeyboardEvent(Key.F1) and not self.__in_help_menu:
                        self.__in_help_menu = True
                        self.__help_menu_line = 0
                        self.__last_help_data = None
                    elif self.__in_help_menu:
                        self.__help_menu_event(event)
                    elif result := self.event(event):
                        return result.value
            finally:
                rc.finalize()

    def _bell(self):
        self.__bell = True

    @property
    def help_data(self) -> WidgetHelp:
        """
        Data for displaying help messages.

        See :func:`help` for more info.

        """

        return self.__help_columns

    @functools.cached_property
    def __help_columns(self) -> WidgetHelp:
        inline_help: list[Action] = []
        groups: dict[str, list[Action]] = {}

        for cb in self.__callbacks:
            bindings: list[_Binding] = getattr(cb, "__yuio_keybindings__", [])
            help: _Help | None = getattr(cb, "__yuio_help__", None)
            if not bindings:
                continue
            if help is None:
                help = _Help(
                    "Actions",
                    getattr(cb, "__doc__", None),
                    getattr(cb, "__doc__", None),
                )
            if not help.inline_msg and not help.long_msg:
                continue

            if help.inline_msg:
                inline_bindings = [
                    binding.event
                    for binding in reversed(bindings)
                    if binding.show_in_inline_help
                ]
                if inline_bindings:
                    inline_help.append((inline_bindings, help.inline_msg))

            if help.long_msg:
                menu_bindings = [
                    binding.event
                    for binding in reversed(bindings)
                    if binding.show_in_detailed_help
                ]
                if menu_bindings:
                    groups.setdefault(help.group, []).append(
                        (menu_bindings, help.long_msg)
                    )

        return WidgetHelp(inline_help, groups)

    __last_help_data: WidgetHelp | None = None
    __prepared_inline_help: list[tuple[list[str], str, str, int]]
    __prepared_groups: dict[str, list[tuple[list[str], str, str, int]]]
    __has_help: bool = True
    __width: int = 0
    __height: int = 0
    __menu_content_height: int = 0
    __help_menu_line: int = 0
    __help_menu_search: bool = False
    __help_menu_search_widget: Input
    __help_menu_search_layout: tuple[int, int] = 0, 0
    __key_width: int = 0
    __wrapped_groups: list[
        tuple[
            str,  # Title
            list[  # Actions
                tuple[  # Action
                    list[str],  # Keys
                    list[_ColorizedString],  # Wrapped msg
                    int,  # Keys width
                ],
            ],
        ]  # FML this type hint -___-
    ]
    __colorized_inline_help: list[
        tuple[  # Action
            list[str],  # Keys
            _ColorizedString,  # Title
            int,  # Keys width
        ]
    ]

    def __help_menu_event(self, e: KeyboardEvent, /) -> Result[T_co] | None:
        if not self.__help_menu_search and e in [
            KeyboardEvent(Key.F1),
            KeyboardEvent(Key.ESCAPE),
            KeyboardEvent(Key.ENTER),
            KeyboardEvent("q"),
            KeyboardEvent("q", ctrl=True),
        ]:
            self.__in_help_menu = False
            self.__help_menu_line = 0
            self.__last_help_data = None
        elif e == KeyboardEvent(Key.ARROW_UP):
            self.__help_menu_line += 1
        elif e == KeyboardEvent(Key.HOME):
            self.__help_menu_line = 0
        elif e == KeyboardEvent(Key.PAGE_UP):
            self.__help_menu_line += self.__height
        elif e == KeyboardEvent(Key.END):
            self.__help_menu_line = -self.__menu_content_height
        elif e == KeyboardEvent(Key.ARROW_DOWN):
            self.__help_menu_line -= 1
        elif e == KeyboardEvent(Key.PAGE_DOWN):
            self.__help_menu_line -= self.__height
        elif not self.__help_menu_search and e == KeyboardEvent(" "):
            self.__help_menu_line -= self.__height
        elif not self.__help_menu_search and e == KeyboardEvent("/"):
            self.__help_menu_search = True
            self.__help_menu_search_widget = Input(
                decoration_path="menu/input/decoration_search"
            )
        elif self.__help_menu_search:
            if e == KeyboardEvent(Key.ESCAPE) or (
                e == KeyboardEvent(Key.BACKSPACE)
                and not self.__help_menu_search_widget.text
            ):
                self.__help_menu_search = False
                self.__last_help_data = None
                del self.__help_menu_search_widget
                self.__help_menu_search_layout = 0, 0
            else:
                self.__help_menu_search_widget.event(e)
                self.__last_help_data = None
        self.__help_menu_line = min(
            max(-self.__menu_content_height + self.__height, self.__help_menu_line), 0
        )

    def __clear_layout_cache(self, rc: RenderContext, /) -> bool:
        if self.__width == rc.width and self.__last_help_data == self.help_data:
            return False

        if self.__width != rc.width:
            self.__help_menu_line = 0

        self.__width = rc.width
        self.__height = rc.height

        if self.__last_help_data != self.help_data:
            self.__last_help_data = self.help_data
            self.__prepared_groups = self.__prepare_groups(self.__last_help_data, rc)
            self.__prepared_inline_help = self.__prepare_inline_help(
                self.__last_help_data, rc
            )
            self.__has_help = bool(
                self.__last_help_data.inline_help or self.__last_help_data.groups
            )

        return True

    def __help_menu_layout(self, rc: RenderContext, /) -> tuple[int, int]:
        if self.__help_menu_search:
            self.__help_menu_search_layout = self.__help_menu_search_widget.layout(rc)

        if not self.__clear_layout_cache(rc):
            return rc.height, rc.height

        self.__key_width = 10
        ctx = rc.make_repr_context(
            width=min(rc.width, 90) - self.__key_width - 2,
        )

        self.__wrapped_groups = []
        for title, actions in self.__prepared_groups.items():
            wrapped_actions: list[tuple[list[str], list[_ColorizedString], int]] = []
            for keys, _, msg, key_width in actions:
                lines = yuio.string.colorize(msg, ctx=ctx).wrap(ctx.width)
                wrapped_actions.append((keys, lines, key_width))
            self.__wrapped_groups.append((title, wrapped_actions))

        return rc.height, rc.height

    def __help_menu_draw(self, rc: RenderContext, /):
        y = self.__help_menu_line

        if not self.__wrapped_groups:
            rc.set_color_path("menu/decoration:help_menu")
            rc.write("No actions to display")
            y += 1

        for title, actions in self.__wrapped_groups:
            rc.set_pos(0, y)
            if title:
                rc.set_color_path("menu/text/heading:help_menu")
                rc.write(title)
                y += 2

            for keys, lines, key_width in actions:
                if key_width > self.__key_width:
                    rc.set_pos(0, y)
                    y += 1
                else:
                    rc.set_pos(self.__key_width - key_width, y)
                sep = ""
                for key in keys:
                    rc.set_color_path("menu/text/help_sep:help_menu")
                    rc.write(sep)
                    rc.set_color_path("menu/text/help_key:help_menu")
                    rc.write(key)
                    sep = "/"

                rc.set_pos(0 + self.__key_width + 2, y)
                rc.write_text(lines)
                y += len(lines)

            y += 2

        self.__menu_content_height = y - self.__help_menu_line

        with rc.frame(0, rc.height - max(self.__help_menu_search_layout[0], 1)):
            if self.__help_menu_search:
                rc.write(" " * rc.width)
                rc.set_pos(0, 0)
                self.__help_menu_search_widget.draw(rc)
            else:
                rc.set_color_path("menu/decoration:help_menu")
                rc.write(rc.get_msg_decoration("menu/help/decoration"))
                rc.reset_color()
                rc.write(" " * (rc.width - 1))
                rc.set_final_pos(1, 0)

    def __help_menu_layout_inline(self, rc: RenderContext, /) -> tuple[int, int]:
        if not self.__clear_layout_cache(rc):
            return (1, 1) if self.__has_help else (0, 0)

        if not self.__has_help:
            return 0, 0

        self.__colorized_inline_help = []
        for keys, title, _, key_width in self.__prepared_inline_help:
            if keys:
                title_color = "menu/text/help_msg:help"
            else:
                title_color = "menu/text/help_info:help"
            colorized_title = yuio.string.colorize(
                title,
                default_color=title_color,
                ctx=rc.make_repr_context(),
            )
            self.__colorized_inline_help.append((keys, colorized_title, key_width))

        return 1, 1

    def __help_menu_draw_inline(self, rc: RenderContext, /):
        if not self.__has_help:
            return

        used_width = _line_width(rc.get_msg_decoration("menu/help/key/f1")) + 5
        col_sep = ""

        for keys, title, keys_width in self.__colorized_inline_help:
            action_width = keys_width + bool(keys_width) + title.width + 3
            if used_width + action_width > rc.width:
                break

            rc.set_color_path("menu/text/help_sep:help")
            rc.write(col_sep)

            sep = ""
            for key in keys:
                rc.set_color_path("menu/text/help_sep:help")
                rc.write(sep)
                rc.set_color_path("menu/text/help_key:help")
                rc.write(key)
                sep = "/"

            if keys_width:
                rc.move_pos(1, 0)
            rc.write(title)

            col_sep = " • "

        rc.set_color_path("menu/text/help_sep:help")
        rc.write(col_sep)
        rc.set_color_path("menu/text/help_key:help")
        rc.write(rc.get_msg_decoration("menu/help/key/f1"))
        rc.move_pos(1, 0)
        rc.set_color_path("menu/text/help_msg:help")
        rc.write("help")

    def __prepare_inline_help(
        self, data: WidgetHelp, rc: RenderContext
    ) -> list[tuple[list[str], str, str, int]]:
        return [
            prepared_action
            for action in data.inline_help
            if (prepared_action := self.__prepare_action(action, rc))
            and prepared_action[1]
        ]

    def __prepare_groups(
        self, data: WidgetHelp, rc: RenderContext
    ) -> dict[str, list[tuple[list[str], str, str, int]]]:
        help_data = (
            data.with_action(
                rc.get_msg_decoration("menu/help/key/f1"),
                group="Other Actions",
                long_msg="toggle help menu",
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/ctrl") + "l",
                group="Other Actions",
                long_msg="refresh screen",
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/ctrl") + "c",
                group="Other Actions",
                long_msg="send interrupt signal",
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/ctrl") + "...",
                group="Legend",
                long_msg="means `Ctrl+...`",
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/alt") + "...",
                group="Legend",
                long_msg=(
                    "means `Option+...`"
                    if sys.platform == "darwin"
                    else "means `Alt+...`"
                ),
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/shift") + "...",
                group="Legend",
                long_msg="means `Shift+...`",
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/enter"),
                group="Legend",
                long_msg="means `Return` or `Enter`",
            )
            .with_action(
                rc.get_msg_decoration("menu/help/key/backspace"),
                group="Legend",
                long_msg="means `Backspace`",
            )
        )

        # Make sure unsorted actions go first.
        groups = {"Input Format": [], "Actions": []}

        groups.update(
            {
                title: prepared_actions
                for title, actions in help_data.groups.items()
                if (
                    prepared_actions := [
                        prepared_action
                        for action in actions
                        if (prepared_action := self.__prepare_action(action, rc))
                        and prepared_action[1]
                    ]
                )
            }
        )

        if not groups["Input Format"]:
            del groups["Input Format"]
        if not groups["Actions"]:
            del groups["Actions"]

        # Make sure other actions go last.
        if "Other Actions" in groups:
            groups["Other Actions"] = groups.pop("Other Actions")
        if "Legend" in groups:
            groups["Legend"] = groups.pop("Legend")

        return groups

    def __prepare_action(
        self, action: Action, rc: RenderContext
    ) -> tuple[list[str], str, str, int] | None:
        if isinstance(action, tuple):
            action_keys, msg = action
            prepared_keys = self.__prepare_keys(action_keys, rc)
        else:
            prepared_keys = []
            msg = action

        if self.__help_menu_search:
            pattern = self.__help_menu_search_widget.text
            if not any(pattern in key for key in prepared_keys) and pattern not in msg:
                return None

        title = msg.split("\n\n", maxsplit=1)[0]
        return prepared_keys, title, msg, _line_width("/".join(prepared_keys))

    def __prepare_keys(self, action_keys: ActionKeys, rc: RenderContext) -> list[str]:
        if isinstance(action_keys, (str, Key, KeyboardEvent)):
            return [self.__prepare_key(action_keys, rc)]
        else:
            return [self.__prepare_key(action_key, rc) for action_key in action_keys]

    def __prepare_key(self, action_key: ActionKey, rc: RenderContext) -> str:
        if isinstance(action_key, str):
            return action_key
        elif isinstance(action_key, KeyboardEvent):
            ctrl, alt, shift, key = (
                action_key.ctrl,
                action_key.alt,
                action_key.shift,
                action_key.key,
            )
        else:
            ctrl, alt, shift, key = False, False, False, action_key

        symbol = ""

        if isinstance(key, str):
            if key.lower() != key:
                shift = True
                key = key.lower()
            elif key == " ":
                key = "space"
        else:
            key = key.name.lower()

        if shift:
            symbol += rc.get_msg_decoration("menu/help/key/shift")

        if ctrl:
            symbol += rc.get_msg_decoration("menu/help/key/ctrl")

        if alt:
            symbol += rc.get_msg_decoration("menu/help/key/alt")

        return symbol + (rc.get_msg_decoration(f"menu/help/key/{key}") or key)


Widget.__init_subclass__()


@dataclass(frozen=True, slots=True)
class _Binding:
    event: KeyboardEvent
    show_in_inline_help: bool
    show_in_detailed_help: bool

    def __call__(self, fn: T, /) -> T:
        if not hasattr(fn, "__yuio_keybindings__"):
            setattr(fn, "__yuio_keybindings__", [])
        getattr(fn, "__yuio_keybindings__").append(self)

        return fn


def bind(
    key: Key | str,
    *,
    ctrl: bool = False,
    alt: bool = False,
    shift: bool = False,
    show_in_inline_help: bool = False,
    show_in_detailed_help: bool = True,
) -> _Binding:
    """
    Register an event handler for a widget.

    Widget's methods can be registered as handlers for keyboard events.
    When a new event comes in, it is checked to match arguments of this decorator.
    If there is a match, the decorated method is called
    instead of the :meth:`Widget.default_event_handler`.

    .. note::

       :kbd:`Ctrl+L` and :kbd:`F1` are always reserved by the widget itself.

    If `show_in_help` is :data:`True`, this binding will be shown in the widget's
    inline help. If `show_in_detailed_help` is :data:`True`,
    this binding will be shown in the widget's help menu.

    Example::

        class MyWidget(Widget):
            @bind(Key.ENTER)
            def enter(self):
                # all `ENTER` events go here.
                ...

            def default_event_handler(self, e: KeyboardEvent):
                # all non-`ENTER` events go here (including `ALT+ENTER`).
                ...

    """

    e = KeyboardEvent(key=key, ctrl=ctrl, alt=alt, shift=shift)
    return _Binding(e, show_in_inline_help, show_in_detailed_help)


@dataclass(frozen=True, slots=True)
class _Help:
    group: str = "Actions"
    inline_msg: str | None = None
    long_msg: str | None = None

    def __call__(self, fn: T, /) -> T:
        h = dataclasses.replace(
            self,
            inline_msg=(
                self.inline_msg
                if self.inline_msg is not None
                else getattr(fn, "__doc__", None)
            ),
            long_msg=(
                self.long_msg
                if self.long_msg is not None
                else getattr(fn, "__doc__", None)
            ),
        )
        setattr(fn, "__yuio_help__", h)

        return fn


def help(
    *,
    group: str = "Actions",
    inline_msg: str | None = None,
    long_msg: str | None = None,
    msg: str | None = None,
) -> _Help:
    """
    Set options for how this callback should be displayed.

    This decorator controls automatic generation of help messages for a widget.

    :param group:
        title of a group that this action will appear in when the user opens
        a help menu. Groups appear in order of declaration of their first element.
    :param inline_msg:
        this parameter overrides a message in the inline help. By default,
        it will be taken from a docstring.
    :param long_msg:
        this parameter overrides a message in the help menu. By default,
        it will be taken from a docstring.
    :param msg:
        a shortcut parameter for setting both `inline_msg` and `long_msg`
        at the same time.

    Example::

        class MyWidget(Widget):
            NAVIGATE = "Navigate"

            @bind(Key.TAB)
            @help(group=NAVIGATE)
            def tab(self):
                \"""next item\"""
                ...

            @bind(Key.TAB, shift=True)
            @help(group=NAVIGATE)
            def shift_tab(self):
                \"""previous item\"""
                ...

    """

    if msg is not None and inline_msg is None:
        inline_msg = msg
    if msg is not None and long_msg is None:
        long_msg = msg

    return _Help(
        group,
        inline_msg,
        long_msg,
    )


ActionKey: _t.TypeAlias = Key | KeyboardEvent | str
"""
A single key associated with an action.
Can be either a hotkey or a string with an arbitrary description.
/
"""


ActionKeys: _t.TypeAlias = ActionKey | _t.Collection[ActionKey]
"""
A list of keys associated with an action.

"""


Action: _t.TypeAlias = str | tuple[ActionKeys, str]
"""
An action itself, i.e. a set of hotkeys and a description for them.

"""


@dataclass(frozen=True, slots=True)
class WidgetHelp:
    """
    Data for automatic help generation.

    .. warning::

       Do not modify contents of this class in-place. This might break layout
       caching in the widget rendering routine, which will cause displaying
       outdated help messages.

       Use the provided helpers to modify contents of this class.

    """

    inline_help: list[Action] = dataclasses.field(default_factory=list)
    """
    List of actions to show in the inline help.

    """

    groups: dict[str, list[Action]] = dataclasses.field(default_factory=dict)
    """
    Dict of group titles and actions to show in the help menu.

    """

    def with_action(
        self,
        *bindings: _Binding | ActionKey,
        group: str = "Actions",
        msg: str | None = None,
        inline_msg: str | None = None,
        long_msg: str | None = None,
        prepend: bool = False,
        prepend_group: bool = False,
    ) -> WidgetHelp:
        """
        Return a new :class:`WidgetHelp` that has an extra action.

        :param bindings:
            keys that trigger an action.
        :param group:
            title of a group that this action will appear in when the user opens
            a help menu. Groups appear in order of declaration of their first element.
        :param inline_msg:
            this parameter overrides a message in the inline help. By default,
            it will be taken from a docstring.
        :param long_msg:
            this parameter overrides a message in the help menu. By default,
            it will be taken from a docstring.
        :param msg:
            a shortcut parameter for setting both `inline_msg` and `long_msg`
            at the same time.
        :param prepend:
            if :data:`True`, action will be added to the beginning of its group.
        :param prepend_group:
            if :data:`True`, group will be added to the beginning of the help menu.

        """

        return WidgetHelp(self.inline_help.copy(), self.groups.copy()).__add_action(
            *bindings,
            group=group,
            inline_msg=inline_msg,
            long_msg=long_msg,
            prepend=prepend,
            prepend_group=prepend_group,
            msg=msg,
        )

    def merge(self, other: WidgetHelp, /) -> WidgetHelp:
        """
        Merge this help data with another one and return
        a new instance of :class:`WidgetHelp`.

        :param other:
            other :class:`WidgetHelp` for merging.

        """

        result = WidgetHelp(self.inline_help.copy(), self.groups.copy())
        result.inline_help.extend(other.inline_help)
        for title, actions in other.groups.items():
            result.groups[title] = result.groups.get(title, []) + actions
        return result

    def without_group(self, title: str, /) -> WidgetHelp:
        """
        Return a new :class:`WidgetHelp` that has a group with the given title removed.

        :param title:
            title to remove.

        """

        result = WidgetHelp(self.inline_help.copy(), self.groups.copy())
        result.groups.pop(title, None)
        return result

    def rename_group(self, title: str, new_title: str, /) -> WidgetHelp:
        """
        Return a new :class:`WidgetHelp` that has a group with the given title renamed.

        :param title:
            title to replace.
        :param new_title:
            new title.

        """

        result = WidgetHelp(self.inline_help.copy(), self.groups.copy())
        if group := result.groups.pop(title, None):
            result.groups[new_title] = result.groups.get(new_title, []) + group
        return result

    def __add_action(
        self,
        *bindings: _Binding | ActionKey,
        group: str,
        inline_msg: str | None,
        long_msg: str | None,
        prepend: bool,
        prepend_group: bool,
        msg: str | None,
    ) -> WidgetHelp:
        settings = help(
            group=group,
            inline_msg=inline_msg,
            long_msg=long_msg,
            msg=msg,
        )

        if settings.inline_msg:
            inline_keys: ActionKeys = [
                binding.event if isinstance(binding, _Binding) else binding
                for binding in bindings
                if not isinstance(binding, _Binding) or binding.show_in_inline_help
            ]
            if prepend:
                self.inline_help.insert(0, (inline_keys, settings.inline_msg))
            else:
                self.inline_help.append((inline_keys, settings.inline_msg))

        if settings.long_msg:
            menu_keys: ActionKeys = [
                binding.event if isinstance(binding, _Binding) else binding
                for binding in bindings
                if not isinstance(binding, _Binding) or binding.show_in_detailed_help
            ]
            if prepend_group and settings.group not in self.groups:
                # Re-create self.groups with a new group as a first element.
                groups = {settings.group: [], **self.groups}
                self.groups.clear()
                self.groups.update(groups)
            if prepend:
                self.groups[settings.group] = [
                    (menu_keys, settings.long_msg)
                ] + self.groups.get(settings.group, [])
            else:
                self.groups[settings.group] = self.groups.get(settings.group, []) + [
                    (menu_keys, settings.long_msg)
                ]

        return self


@_t.final
class VerticalLayoutBuilder(_t.Generic[T]):
    """
    Builder for :class:`VerticalLayout` that allows for precise control
    of keyboard events.

    By default, :class:`VerticalLayout` does not handle incoming keyboard events.
    However, you can create :class:`VerticalLayout` that forwards all keyboard events
    to a particular widget within the stack::

        widget = VerticalLayout.builder() \\
            .add(Line("Enter something:")) \\
            .add(Input(), receive_events=True) \\
            .build()

        result = widget.run(term, theme)

    """

    if TYPE_CHECKING:

        def __new__(cls) -> VerticalLayoutBuilder[_t.Never]: ...

    def __init__(self):
        self._widgets: list[Widget[_t.Any]] = []
        self._event_receiver: int | None = None

    @_t.overload
    def add(
        self, widget: Widget[_t.Any], /, *, receive_events: _t.Literal[False] = False
    ) -> VerticalLayoutBuilder[T]: ...

    @_t.overload
    def add(
        self, widget: Widget[U], /, *, receive_events: _t.Literal[True]
    ) -> VerticalLayoutBuilder[U]: ...

    def add(self, widget: Widget[_t.Any], /, *, receive_events=False) -> _t.Any:
        """
        Add a new widget to the bottom of the layout.

        If `receive_events` is `True`, all incoming events will be forwarded
        to the added widget. Only the latest widget added with ``receive_events=True``
        will receive events.

        This method does not mutate the builder, but instead returns a new one.
        Use it with method chaining.

        """

        other = VerticalLayoutBuilder()

        other._widgets = self._widgets.copy()
        other._event_receiver = self._event_receiver

        if isinstance(widget, VerticalLayout):
            if receive_events and widget._event_receiver is not None:
                other._event_receiver = len(other._widgets) + widget._event_receiver
            elif receive_events:
                other._event_receiver = None
            other._widgets.extend(widget._widgets)
        else:
            if receive_events:
                other._event_receiver = len(other._widgets)
            other._widgets.append(widget)

        return other

    def build(self) -> VerticalLayout[T]:
        layout = VerticalLayout()
        layout._widgets = self._widgets
        layout._event_receiver = self._event_receiver
        return _t.cast(VerticalLayout[T], layout)


class VerticalLayout(Widget[T], _t.Generic[T]):
    """
    Helper class for stacking widgets together.

    You can stack your widgets together, then calculate their layout
    and draw them all at once.

    You can use this class as a helper component inside your own widgets,
    or you can use it as a standalone widget. See :class:`~VerticalLayoutBuilder`
    for an example.

    .. automethod:: append

    .. automethod:: extend

    .. automethod:: event

    .. automethod:: layout

    .. automethod:: draw

    """

    if TYPE_CHECKING:

        def __new__(cls, *widgets: Widget[object]) -> VerticalLayout[_t.Never]: ...

    def __init__(self, *widgets: Widget[object]):
        self._widgets: list[Widget[object]] = list(widgets)
        self._event_receiver: int | None = None

        self.__layouts: list[tuple[int, int]] = []
        self.__min_h: int = 0
        self.__max_h: int = 0

    def append(self, widget: Widget[_t.Any], /):
        """
        Add a widget to the end of the stack.

        """

        if isinstance(widget, VerticalLayout):
            self._widgets.extend(widget._widgets)
        else:
            self._widgets.append(widget)

    def extend(self, widgets: _t.Iterable[Widget[_t.Any]], /):
        """
        Add multiple widgets to the end of the stack.

        """

        for widget in widgets:
            self.append(widget)

    def event(self, e: KeyboardEvent) -> Result[T] | None:
        """
        Dispatch event to the widget that was added with ``receive_events=True``.

        See :class:`~VerticalLayoutBuilder` for details.

        """

        if self._event_receiver is not None:
            return _t.cast(
                Result[T] | None, self._widgets[self._event_receiver].event(e)
            )

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        """
        Calculate layout of the entire stack.

        """

        self.__layouts = [widget.layout(rc) for widget in self._widgets]
        assert all(l[0] <= l[1] for l in self.__layouts), "incorrect layout"
        self.__min_h = sum(l[0] for l in self.__layouts)
        self.__max_h = sum(l[1] for l in self.__layouts)
        return self.__min_h, self.__max_h

    def draw(self, rc: RenderContext, /):
        """
        Draw the stack according to the calculated layout and available height.

        """

        assert len(self._widgets) == len(self.__layouts), (
            "you need to call `VerticalLayout.layout()` before `VerticalLayout.draw()`"
        )

        if rc.height <= self.__min_h:
            scale = 0.0
        elif rc.height >= self.__max_h:
            scale = 1.0
        else:
            scale = (rc.height - self.__min_h) / (self.__max_h - self.__min_h)

        y1 = 0.0
        for widget, (min_h, max_h) in zip(self._widgets, self.__layouts):
            y2 = y1 + min_h + scale * (max_h - min_h)

            iy1 = round(y1)
            iy2 = round(y2)

            with rc.frame(0, iy1, height=iy2 - iy1):
                widget.draw(rc)

            y1 = y2

    @property
    def help_data(self) -> WidgetHelp:
        if self._event_receiver is not None:
            return self._widgets[self._event_receiver].help_data
        else:
            return WidgetHelp()


class Empty(Widget[_t.Never]):
    """
    An empty widget with no size.

    """

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        return 0, 0

    def draw(self, rc: RenderContext, /):
        pass


class Line(Widget[_t.Never]):
    """
    A widget that prints a single line of text.

    """

    def __init__(
        self,
        text: yuio.string.Colorable,
        /,
    ):
        self.__text = text
        self.__colorized_text = None

    @property
    def text(self) -> yuio.string.Colorable:
        """
        Currently displayed text.

        """

        return self.__text

    @text.setter
    def text(self, text: yuio.string.Colorable, /):
        self.__text = text
        self.__colorized_text = None

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        return 1, 1

    def draw(self, rc: RenderContext, /):
        if self.__colorized_text is None:
            self.__colorized_text = rc.make_repr_context().str(self.__text)

        rc.write(self.__colorized_text)


class Text(Widget[_t.Never]):
    """
    A widget that prints wrapped text.

    """

    def __init__(
        self,
        text: yuio.string.Colorable,
        /,
    ):
        self.__text = text
        self.__wrapped_text: list[_ColorizedString] | None = None
        self.__wrapped_text_width: int = 0

    @property
    def text(self) -> yuio.string.Colorable:
        """
        Currently displayed text.

        """

        return self.__text

    @text.setter
    def text(self, text: yuio.string.Colorable, /):
        self.__text = text
        self.__wrapped_text = None
        self.__wrapped_text_width = 0

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        if self.__wrapped_text is None or self.__wrapped_text_width != rc.width:
            colorized_text = rc.make_repr_context().str(self.__text)
            self.__wrapped_text = colorized_text.wrap(
                rc.width,
                break_long_nowrap_words=True,
            )
            self.__wrapped_text_width = rc.width
        height = len(self.__wrapped_text)
        return height, height

    def draw(self, rc: RenderContext, /):
        assert self.__wrapped_text is not None
        rc.write_text(self.__wrapped_text)


_CHAR_NAMES = {
    "\u0000": "<NUL>",
    "\u0001": "<SOH>",
    "\u0002": "<STX>",
    "\u0003": "<ETX>",
    "\u0004": "<EOT>",
    "\u0005": "<ENQ>",
    "\u0006": "<ACK>",
    "\u0007": "\\a",
    "\u0008": "\\b",
    "\u0009": "\\t",
    "\u000b": "\\v",
    "\u000c": "\\f",
    "\u000d": "\\r",
    "\u000e": "<SO>",
    "\u000f": "<SI>",
    "\u0010": "<DLE>",
    "\u0011": "<DC1>",
    "\u0012": "<DC2>",
    "\u0013": "<DC3>",
    "\u0014": "<DC4>",
    "\u0015": "<NAK>",
    "\u0016": "<SYN>",
    "\u0017": "<ETB>",
    "\u0018": "<CAN>",
    "\u0019": "<EM>",
    "\u001a": "<SUB>",
    "\u001b": "<ESC>",
    "\u001c": "<FS>",
    "\u001d": "<GS>",
    "\u001e": "<RS>",
    "\u001f": "<US>",
    "\u007f": "<DEL>",
    "\u0080": "<PAD>",
    "\u0081": "<HOP>",
    "\u0082": "<BPH>",
    "\u0083": "<NBH>",
    "\u0084": "<IND>",
    "\u0085": "<NEL>",
    "\u0086": "<SSA>",
    "\u0087": "<ESA>",
    "\u0088": "<HTS>",
    "\u0089": "<HTJ>",
    "\u008a": "<VTS>",
    "\u008b": "<PLD>",
    "\u008c": "<PLU>",
    "\u008d": "<RI>",
    "\u008e": "<SS2>",
    "\u008f": "<SS3>",
    "\u0090": "<DCS>",
    "\u0091": "<PU1>",
    "\u0092": "<PU2>",
    "\u0093": "<STS>",
    "\u0094": "<CCH>",
    "\u0095": "<MW>",
    "\u0096": "<SPA>",
    "\u0097": "<EPA>",
    "\u0098": "<SOS>",
    "\u0099": "<SGCI>",
    "\u009a": "<SCI>",
    "\u009b": "<CSI>",
    "\u009c": "<ST>",
    "\u009d": "<OSC>",
    "\u009e": "<PM>",
    "\u009f": "<APC>",
    "\u00a0": "<NBSP>",
    "\u00ad": "<SHY>",
}

_ESC_RE = re.compile(r"([" + re.escape("".join(map(str, _CHAR_NAMES))) + "])")


def _replace_special_symbols(text: str, esc_color: _Color, n_color: _Color):
    raw: list[_Color | str] = [n_color]
    i = 0
    for match in _ESC_RE.finditer(text):
        if s := text[i : match.start()]:
            raw.append(s)
        raw.append(esc_color)
        raw.append(_Esc(_CHAR_NAMES[match.group(1)]))
        raw.append(n_color)
        i = match.end()
    if i < len(text):
        raw.append(text[i:])
    return raw


def _find_cursor_pos(text: list[_ColorizedString], text_width: int, offset: int):
    total_len = 0
    if not offset:
        return (0, 0)
    for y, line in enumerate(text):
        x = 0
        for part in line:
            if isinstance(part, _Esc):
                l = 1
                dx = len(part)
            elif isinstance(part, str):
                l = len(part)
                dx = _line_width(part)
            else:
                continue
            if total_len + l >= offset:
                if isinstance(part, _Esc):
                    x += dx
                else:
                    x += _line_width(part[: offset - total_len])
                if x >= text_width:
                    return (0, y + 1)
                else:
                    return (0 + x, y)
                break
            x += dx
            total_len += l
        total_len += len(line.explicit_newline)
        if total_len >= offset:
            return (0, y + 1)
    assert False


class Input(Widget[str]):
    """
    An input box.

    .. vhs:: /_tapes/widget_input.tape
       :alt: Demonstration of `Input` widget.
       :scale: 40%

    .. note::

        :class:`Input` is not optimized to handle long texts or long editing sessions.
        It's best used to get relatively short answers from users
        with :func:`yuio.io.ask`. If you need to edit large text, especially multiline,
        consider using :func:`yuio.io.edit` instead.

    :param text:
        initial text.
    :param pos:
        initial cursor position, calculated as an offset from beginning of the text.
        Should be ``0 <= pos <= len(text)``.
    :param placeholder:
        placeholder text, shown when input is empty.
    :param decoration_path:
        path that will be used to look up decoration printed before the input box.
    :param allow_multiline:
        if `True`, :kbd:`Enter` key makes a new line, otherwise it accepts input.
        In this mode, newlines in pasted text are also preserved.
    :param allow_special_characters:
        If `True`, special characters like tabs or escape symbols are preserved
        and not replaced with whitespaces.

    """

    # Characters that count as word separators, used when navigating input text
    # via hotkeys.
    _WORD_SEPARATORS = string.punctuation + string.whitespace

    # Character that replaces newlines and unprintable characters when
    # `allow_multiline`/`allow_special_characters` is `False`.
    _UNPRINTABLE_SUBSTITUTOR = " "

    class _CheckpointType(enum.Enum):
        """
        Types of entries in the history buffer.

        """

        USR = enum.auto()
        """
        User-initiated checkpoint.

        """

        SYM = enum.auto()
        """
        Checkpoint before a symbol was inserted.

        """

        SEP = enum.auto()
        """
        Checkpoint before a space was inserted.

        """

        DEL = enum.auto()
        """
        Checkpoint before something was deleted.

        """

    def __init__(
        self,
        *,
        text: str = "",
        pos: int | None = None,
        placeholder: str = "",
        decoration_path: str = "menu/input/decoration",
        allow_multiline: bool = False,
        allow_special_characters: bool = False,
    ):
        self.__text: str = text
        self.__pos: int = len(text) if pos is None else max(0, min(pos, len(text)))
        self.__placeholder: str = placeholder
        self.__decoration_path: str = decoration_path
        self.__allow_multiline: bool = allow_multiline
        self.__allow_special_characters: bool = allow_special_characters

        self.__wrapped_text_width: int = 0
        self.__wrapped_text: list[_ColorizedString] | None = None
        self.__pos_after_wrap: tuple[int, int] | None = None

        # We keep track of edit history by saving input text
        # and cursor position in this list.
        self.__history: list[tuple[str, int, Input._CheckpointType]] = [
            (self.__text, self.__pos, Input._CheckpointType.SYM)
        ]
        # Sometimes we don't record all actions. For example, entering multiple spaces
        # one after the other, or entering multiple symbols one after the other,
        # will only generate one checkpoint. We keep track of how many items
        # were skipped this way since the last checkpoint.
        self.__history_skipped_actions = 0
        # After we move a cursor, the logic with skipping checkpoints
        # should be momentarily disabled. This avoids inconsistencies in situations
        # where we've typed a word, moved the cursor, then typed another word.
        self.__require_checkpoint: bool = False

        # All delete operations save deleted text here. Pressing `C-y` pastes deleted
        # text at the position of the cursor.
        self.__yanked_text: str = ""

        self.__err_region: tuple[int, int] | None = None

    @property
    def text(self) -> str:
        """
        Current text in the input box.

        """
        return self.__text

    @text.setter
    def text(self, text: str, /):
        self.__text = text
        self.__wrapped_text = None
        if self.pos > len(text):
            self.pos = len(text)
        self.__err_region = None

    @property
    def pos(self) -> int:
        """
        Current cursor position, measured in code points before the cursor.

        That is, if the text is `"quick brown fox"` with cursor right before the word
        "brown", then :attr:`~Input.pos` is equal to `len("quick ")`.

        """
        return self.__pos

    @pos.setter
    def pos(self, pos: int, /):
        self.__pos = max(0, min(pos, len(self.__text)))
        self.__pos_after_wrap = None

    @property
    def err_region(self) -> tuple[int, int] | None:
        return self.__err_region

    @err_region.setter
    def err_region(self, err_region: tuple[int, int] | None, /):
        self.__err_region = err_region
        self.__wrapped_text = None

    def checkpoint(self):
        """
        Manually create an entry in the history buffer.

        """
        self.__history.append((self.text, self.pos, Input._CheckpointType.USR))
        self.__history_skipped_actions = 0

    def restore_checkpoint(self):
        """
        Restore the last manually created checkpoint.

        """
        if self.__history[-1][2] is Input._CheckpointType.USR:
            self.undo()

    def _internal_checkpoint(self, action: Input._CheckpointType, text: str, pos: int):
        prev_text, prev_pos, prev_action = self.__history[-1]

        if action == prev_action and not self.__require_checkpoint:
            # If we're repeating the same action, don't create a checkpoint.
            # I.e. if we're typing a word, we don't want to create checkpoints
            # for every letter.
            self.__history_skipped_actions += 1
            return

        prev_skipped_actions = self.__history_skipped_actions
        self.__history_skipped_actions = 0

        if (
            action == Input._CheckpointType.SYM
            and prev_action == Input._CheckpointType.SEP
            and prev_skipped_actions == 0
            and not self.__require_checkpoint
        ):
            # If we're inserting a symbol after we've typed a single space,
            # we only want one checkpoint for both space and symbols.
            # Thus, we simply change the type of the last checkpoint.
            self.__history[-1] = prev_text, prev_pos, action
            return

        if text == prev_text and pos == prev_pos:
            # This could happen when user presses backspace while the cursor
            # is at the text's beginning. We don't want to create
            # a checkpoint for this.
            return

        self.__history.append((text, pos, action))
        if len(self.__history) > 50:
            self.__history.pop(0)

        self.__require_checkpoint = False

    @bind(Key.ENTER)
    def enter(self) -> Result[str] | None:
        if self.__allow_multiline:
            self.insert("\n")
        else:
            return self.alt_enter()

    @bind(Key.ENTER, alt=True)
    @bind("d", ctrl=True)
    def alt_enter(self) -> Result[str] | None:
        return Result(self.text)

    _NAVIGATE = "Navigate"

    @bind(Key.ARROW_UP)
    @bind("p", ctrl=True)
    @help(group=_NAVIGATE)
    def up(self, /, *, checkpoint: bool = True):
        """up"""
        pos = self.pos
        self.home()
        if self.pos:
            width = _line_width(self.text[self.pos : pos])

            self.left()
            self.home()

            pos = self.pos
            text = self.text
            cur_width = 0
            while pos < len(text) and text[pos] != "\n":
                if cur_width >= width:
                    break
                cur_width += _line_width(text[pos])
                pos += 1

            self.pos = pos

        self.__require_checkpoint |= checkpoint

    @bind(Key.ARROW_DOWN)
    @bind("n", ctrl=True)
    @help(group=_NAVIGATE)
    def down(self, /, *, checkpoint: bool = True):
        """down"""
        pos = self.pos
        self.home()
        width = _line_width(self.text[self.pos : pos])
        self.end()

        if self.pos < len(self.text):
            self.right()

            pos = self.pos
            text = self.text
            cur_width = 0
            while pos < len(text) and text[pos] != "\n":
                if cur_width >= width:
                    break
                cur_width += _line_width(text[pos])
                pos += 1

            self.pos = pos

        self.__require_checkpoint |= checkpoint

    @bind(Key.ARROW_LEFT)
    @bind("b", ctrl=True)
    @help(group=_NAVIGATE)
    def left(self, /, *, checkpoint: bool = True):
        """left"""
        self.pos -= 1
        self.__require_checkpoint |= checkpoint

    @bind(Key.ARROW_RIGHT)
    @bind("f", ctrl=True)
    @help(group=_NAVIGATE)
    def right(self, /, *, checkpoint: bool = True):
        """right"""
        self.pos += 1
        self.__require_checkpoint |= checkpoint

    @bind(Key.ARROW_LEFT, alt=True)
    @bind("b", alt=True)
    @help(group=_NAVIGATE)
    def left_word(self, /, *, checkpoint: bool = True):
        """left one word"""
        pos = self.pos
        text = self.text
        if pos:
            pos -= 1
        while pos and text[pos] in self._WORD_SEPARATORS and text[pos - 1] != "\n":
            pos -= 1
        while pos and text[pos - 1] not in self._WORD_SEPARATORS:
            pos -= 1
        self.pos = pos
        self.__require_checkpoint |= checkpoint

    @bind(Key.ARROW_RIGHT, alt=True)
    @bind("f", alt=True)
    @help(group=_NAVIGATE)
    def right_word(self, /, *, checkpoint: bool = True):
        """right one word"""
        pos = self.pos
        text = self.text
        if pos < len(text) and text[pos] == "\n":
            pos += 1
        while (
            pos < len(text) and text[pos] in self._WORD_SEPARATORS and text[pos] != "\n"
        ):
            pos += 1
        while pos < len(text) and text[pos] not in self._WORD_SEPARATORS:
            pos += 1
        self.pos = pos
        self.__require_checkpoint |= checkpoint

    @bind(Key.HOME)
    @bind("a", ctrl=True)
    @help(group=_NAVIGATE)
    def home(self, /, *, checkpoint: bool = True):
        """to line start"""
        self.pos = self.text.rfind("\n", 0, self.pos) + 1
        self.__require_checkpoint |= checkpoint

    @bind(Key.END)
    @bind("e", ctrl=True)
    @help(group=_NAVIGATE)
    def end(self, /, *, checkpoint: bool = True):
        """to line end"""
        next_nl = self.text.find("\n", self.pos)
        if next_nl == -1:
            self.pos = len(self.text)
        else:
            self.pos = next_nl
        self.__require_checkpoint |= checkpoint

    @bind("g", ctrl=True)
    def go_to_err(self, /, *, checkpoint: bool = True):
        if not self.__err_region:
            return
        if self.pos == self.__err_region[1]:
            self.pos = self.__err_region[0]
        else:
            self.pos = self.__err_region[1]
        self.__require_checkpoint |= checkpoint

    _MODIFY = "Modify"

    @bind(Key.BACKSPACE)
    @bind("h", ctrl=True)
    @help(group=_MODIFY)
    def backspace(self):
        """backspace"""
        prev_pos = self.pos
        self.left(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint(Input._CheckpointType.DEL, self.text, prev_pos)
            self.text = self.text[: self.pos] + self.text[prev_pos:]
        else:
            self._bell()

    @bind(Key.DELETE)
    @help(group=_MODIFY)
    def delete(self):
        """delete"""
        prev_pos = self.pos
        self.right(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint(Input._CheckpointType.DEL, self.text, prev_pos)
            self.text = self.text[:prev_pos] + self.text[self.pos :]
            self.pos = prev_pos
        else:
            self._bell()

    @bind(Key.BACKSPACE, alt=True)
    @bind("w", ctrl=True)
    @help(group=_MODIFY)
    def backspace_word(self):
        """backspace one word"""
        prev_pos = self.pos
        self.left_word(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint(Input._CheckpointType.DEL, self.text, prev_pos)
            self.__yanked_text = self.text[self.pos : prev_pos]
            self.text = self.text[: self.pos] + self.text[prev_pos:]
        else:
            self._bell()

    @bind(Key.DELETE, alt=True)
    @bind("d", alt=True)
    @help(group=_MODIFY)
    def delete_word(self):
        """delete one word"""
        prev_pos = self.pos
        self.right_word(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint(Input._CheckpointType.DEL, self.text, prev_pos)
            self.__yanked_text = self.text[prev_pos : self.pos]
            self.text = self.text[:prev_pos] + self.text[self.pos :]
            self.pos = prev_pos
        else:
            self._bell()

    @bind("u", ctrl=True)
    @help(group=_MODIFY)
    def backspace_home(self):
        """backspace to the beginning of a line"""
        prev_pos = self.pos
        self.home(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint(Input._CheckpointType.DEL, self.text, prev_pos)
            self.__yanked_text = self.text[self.pos : prev_pos]
            self.text = self.text[: self.pos] + self.text[prev_pos:]
        else:
            self._bell()

    @bind("k", ctrl=True)
    @help(group=_MODIFY)
    def delete_end(self):
        """delete to the ending of a line"""
        prev_pos = self.pos
        self.end(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint(Input._CheckpointType.DEL, self.text, prev_pos)
            self.__yanked_text = self.text[prev_pos : self.pos]
            self.text = self.text[:prev_pos] + self.text[self.pos :]
            self.pos = prev_pos
        else:
            self._bell()

    @bind("y", ctrl=True)
    @help(group=_MODIFY)
    def yank(self):
        """yank (paste the last deleted text)"""
        if self.__yanked_text:
            self.__require_checkpoint = True
            self.insert(self.__yanked_text)
        else:
            self._bell()

    # the actual shortcut is `C-7`, the rest produce the same code...
    @bind("7", ctrl=True, show_in_detailed_help=False)
    @bind("-", ctrl=True, shift=True, show_in_detailed_help=False)
    @bind("?", ctrl=True, show_in_detailed_help=False)
    @bind("-", ctrl=True)
    @bind("z", ctrl=True)
    @help(group=_MODIFY)
    def undo(self):
        """undo"""
        self.text, self.pos, _ = self.__history[-1]
        if len(self.__history) > 1:
            self.__history.pop()
        else:
            self._bell()

    def default_event_handler(self, e: KeyboardEvent):
        if e.key is Key.PASTE:
            self.__require_checkpoint = True
            s = e.paste_str or ""
            if self.__allow_special_characters and self.__allow_multiline:
                pass
            elif self.__allow_multiline:
                s = re.sub(_UNPRINTABLE_RE_WITHOUT_NL, self._UNPRINTABLE_SUBSTITUTOR, s)
            elif self.__allow_special_characters:
                s = s.replace("\n", self._UNPRINTABLE_SUBSTITUTOR)
            else:
                s = re.sub(_UNPRINTABLE_RE, self._UNPRINTABLE_SUBSTITUTOR, s)
            self.insert(s)
        elif e.key is Key.TAB:
            if self.__allow_special_characters:
                self.insert("\t")
            else:
                self.insert(self._UNPRINTABLE_SUBSTITUTOR)
        elif isinstance(e.key, str) and not e.alt and not e.ctrl:
            self.insert(e.key)

    def insert(self, s: str):
        if not s:
            return

        self._internal_checkpoint(
            (
                Input._CheckpointType.SEP
                if s in self._WORD_SEPARATORS
                else Input._CheckpointType.SYM
            ),
            self.text,
            self.pos,
        )

        self.text = self.text[: self.pos] + s + self.text[self.pos :]
        self.pos += len(s)

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        decoration = rc.get_msg_decoration(self.__decoration_path)
        decoration_width = _line_width(decoration)
        text_width = rc.width - decoration_width
        if text_width < 2:
            self.__wrapped_text_width = max(text_width, 0)
            self.__wrapped_text = None
            self.__pos_after_wrap = None
            return 0, 0

        if self.__wrapped_text is None or self.__wrapped_text_width != text_width:
            self.__wrapped_text_width = text_width

            # Note: don't use wrap with overflow here
            # or we won't be able to find the cursor position!
            if self.__text:
                self.__wrapped_text = self._prepare_display_text(
                    self.__text,
                    rc.theme.get_color("menu/text/esc:input"),
                    rc.theme.get_color("menu/text:input"),
                    rc.theme.get_color("menu/text/error:input"),
                ).wrap(
                    text_width,
                    preserve_spaces=True,
                    break_long_nowrap_words=True,
                )
                self.__pos_after_wrap = None
            else:
                self.__wrapped_text = _ColorizedString(
                    rc.theme.get_color("menu/text/placeholder:input"),
                    self.__placeholder,
                ).wrap(
                    text_width,
                    preserve_newlines=False,
                    break_long_nowrap_words=True,
                )
                self.__pos_after_wrap = (decoration_width, 0)

        if self.__pos_after_wrap is None:
            x, y = _find_cursor_pos(self.__wrapped_text, text_width, self.__pos)
            self.__pos_after_wrap = (decoration_width + x, y)

        height = max(len(self.__wrapped_text), self.__pos_after_wrap[1] + 1)
        return height, height

    def draw(self, rc: RenderContext, /):
        if decoration := rc.get_msg_decoration(self.__decoration_path):
            rc.set_color_path("menu/decoration:input")
            rc.write(decoration)

        if self.__wrapped_text is not None:
            rc.write_text(self.__wrapped_text)

        if self.__pos_after_wrap is not None:
            rc.set_final_pos(*self.__pos_after_wrap)

    def _prepare_display_text(
        self, text: str, esc_color: _Color, n_color: _Color, err_color: _Color
    ) -> _ColorizedString:
        res = _ColorizedString()
        if self.__err_region:
            start, end = self.__err_region
            res += _replace_special_symbols(text[:start], esc_color, n_color)
            res += _replace_special_symbols(text[start:end], esc_color, err_color)
            res += _replace_special_symbols(text[end:], esc_color, n_color)
        else:
            res += _replace_special_symbols(text, esc_color, n_color)
        return res

    @property
    def help_data(self) -> WidgetHelp:
        help_data = super().help_data

        if self.__allow_multiline:
            help_data = help_data.with_action(
                KeyboardEvent(Key.ENTER, alt=True),
                KeyboardEvent("d", ctrl=True),
                msg="accept",
                prepend=True,
            ).with_action(
                KeyboardEvent(Key.ENTER),
                group=self._MODIFY,
                long_msg="new line",
                prepend=True,
            )

        if self.__err_region:
            help_data = help_data.with_action(
                KeyboardEvent("g", ctrl=True),
                group=self._NAVIGATE,
                msg="go to error",
                prepend=True,
            )

        return help_data


class SecretInput(Input):
    """
    An input box that shows stars instead of entered symbols.

    :param text:
        initial text.
    :param pos:
        initial cursor position, calculated as an offset from beginning of the text.
        Should be ``0 <= pos <= len(text)``.
    :param placeholder:
        placeholder text, shown when input is empty.
    :param decoration:
        decoration printed before the input box.

    """

    _WORD_SEPARATORS = ""
    _UNPRINTABLE_SUBSTITUTOR = ""

    def __init__(
        self,
        *,
        text: str = "",
        pos: int | None = None,
        placeholder: str = "",
        decoration_path: str = "menu/input/decoration",
    ):
        super().__init__(
            text=text,
            pos=pos,
            placeholder=placeholder,
            decoration_path=decoration_path,
            allow_multiline=False,
            allow_special_characters=False,
        )

    def _prepare_display_text(
        self, text: str, esc_color: _Color, n_color: _Color, err_color: _Color
    ) -> _ColorizedString:
        return _ColorizedString("*" * len(text))


@dataclass(slots=True)
class Option(_t.Generic[T_co]):
    """
    An option for the :class:`Grid` and :class:`Choice` widgets.

    """

    def __post_init__(self):
        if self.color_tag is None:
            object.__setattr__(self, "color_tag", "none")

    value: T_co
    """
    Option's value that will be returned from widget.

    """

    display_text: str
    """
    What should be displayed in the autocomplete list.

    """

    display_text_prefix: str = dataclasses.field(default="", kw_only=True)
    """
    Prefix that will be displayed before :attr:`~Option.display_text`.

    """

    display_text_suffix: str = dataclasses.field(default="", kw_only=True)
    """
    Suffix that will be displayed after :attr:`~Option.display_text`.

    """

    comment: str | None = dataclasses.field(default=None, kw_only=True)
    """
    Option's short comment.

    """

    color_tag: str | None = dataclasses.field(default=None, kw_only=True)
    """
    Option's color tag.

    This color tag will be used to display option.
    Specifically, color for the option will be looked up py path
    :samp:``menu/{element}:choice/{status}/{color_tag}``.

    """

    selected: bool = dataclasses.field(default=False, kw_only=True)
    """
    For multi-choice widgets, whether this option is chosen or not.

    """


class Grid(Widget[_t.Never], _t.Generic[T]):
    """
    A helper widget that shows up in :class:`Choice` and :class:`InputWithCompletion`.

    .. note::

        On its own, :class:`Grid` doesn't return when you press :kbd:`Enter`
        or :kbd:`Ctrl+D`. It's meant to be used as part of another widget.

    :param options:
        list of options displayed in the grid.
    :param decoration:
        decoration printed before the selected option.
    :param default_index:
        index of the initially selected option.
    :param min_rows:
        minimum number of rows that the grid should occupy before it starts
        splitting options into columns. This option is ignored if there isn't enough
        space on the screen.

    """

    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        active_item_decoration_path: str = "menu/choice/decoration/active_item",
        selected_item_decoration_path: str = "",
        deselected_item_decoration_path: str = "",
        default_index: int | None = 0,
        min_rows: int | None = 5,
    ):
        self.__options: list[Option[T]]
        self.__index: int | None
        self.__min_rows: int | None = min_rows
        self.__max_column_width: int | None
        self.__column_width: int
        self.__num_rows: int
        self.__num_columns: int

        self.__active_item_decoration_path = active_item_decoration_path
        self.__selected_item_decoration_path = selected_item_decoration_path
        self.__deselected_item_decoration_path = deselected_item_decoration_path

        self.set_options(options)
        self.index = default_index

    @property
    def _page_size(self) -> int:
        return self.__num_rows * self.__num_columns

    @property
    def index(self) -> int | None:
        """
        Index of the currently selected option.

        """

        return self.__index

    @index.setter
    def index(self, idx: int | None):
        if idx is None or not self.__options:
            self.__index = None
        elif self.__options:
            self.__index = idx % len(self.__options)

    def get_option(self) -> Option[T] | None:
        """
        Get the currently selected option,
        or `None` if there are no options selected.

        """

        if self.__options and self.__index is not None:
            return self.__options[self.__index]

    def has_options(self) -> bool:
        """
        Return :data:`True` if the options list is not empty.

        """

        return bool(self.__options)

    def get_options(self) -> _t.Sequence[Option[T]]:
        """
        Get all options.

        """

        return self.__options

    def set_options(
        self,
        options: list[Option[T]],
        /,
        default_index: int | None = 0,
    ):
        """
        Set a new list of options.

        """

        self.__options = options
        self.__max_column_width = None
        self.index = default_index

    _NAVIGATE = "Navigate"

    @bind(Key.ARROW_UP)
    @bind(Key.TAB, shift=True)
    @help(group=_NAVIGATE)
    def prev_item(self):
        """previous item"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            self.__index = (self.__index - 1) % len(self.__options)

    @bind(Key.ARROW_DOWN)
    @bind(Key.TAB)
    @help(group=_NAVIGATE)
    def next_item(self):
        """next item"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            self.__index = (self.__index + 1) % len(self.__options)

    @bind(Key.ARROW_LEFT)
    @help(group=_NAVIGATE)
    def prev_column(self):
        """previous column"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            total_grid_capacity = self.__num_rows * math.ceil(
                len(self.__options) / self.__num_rows
            )

            self.__index = (self.__index - self.__num_rows) % total_grid_capacity
            if self.__index >= len(self.__options):
                self.__index = len(self.__options) - 1

    @bind(Key.ARROW_RIGHT)
    @help(group=_NAVIGATE)
    def next_column(self):
        """next column"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            total_grid_capacity = self.__num_rows * math.ceil(
                len(self.__options) / self.__num_rows
            )

            self.__index = (self.__index + self.__num_rows) % total_grid_capacity
            if self.__index >= len(self.__options):
                self.__index = len(self.__options) - 1

    @bind(Key.PAGE_UP)
    @help(group=_NAVIGATE)
    def prev_page(self):
        """previous page"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            self.__index -= self.__index % self._page_size
            self.__index -= 1
            if self.__index < 0:
                self.__index = len(self.__options) - 1

    @bind(Key.PAGE_DOWN)
    @help(group=_NAVIGATE)
    def next_page(self):
        """next page"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            self.__index -= self.__index % self._page_size
            self.__index += self._page_size
            if self.__index > len(self.__options):
                self.__index = 0

    @bind(Key.HOME)
    @help(group=_NAVIGATE)
    def home(self):
        """first page"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            self.__index = 0

    @bind(Key.END)
    @help(group=_NAVIGATE)
    def end(self):
        """last page"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = 0
        else:
            self.__index = len(self.__options) - 1

    def default_event_handler(self, e: KeyboardEvent):
        if isinstance(e.key, str):
            key = e.key.casefold()
            if (
                self.__options
                and self.__index is not None
                and self.__options[self.__index].display_text.casefold().startswith(key)
            ):
                start = self.__index + 1
            else:
                start = 0
            for i in range(start, start + len(self.__options)):
                index = i % len(self.__options)
                if self.__options[index].display_text.casefold().startswith(key):
                    self.__index = index
                    break

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        active_item_decoration = rc.get_msg_decoration(
            self.__active_item_decoration_path
        )
        selected_item_decoration = rc.get_msg_decoration(
            self.__selected_item_decoration_path
        )
        deselected_item_decoration = rc.get_msg_decoration(
            self.__deselected_item_decoration_path
        )

        decoration_width = _line_width(active_item_decoration) + max(
            _line_width(selected_item_decoration),
            _line_width(deselected_item_decoration),
        )

        if self.__max_column_width is None:
            self.__max_column_width = max(
                0,
                _MIN_COLUMN_WIDTH,
                *(
                    self._get_option_width(option, decoration_width)
                    for option in self.__options
                ),
            )
        self.__column_width = max(1, min(self.__max_column_width, rc.width))
        self.__num_columns = num_columns = max(1, rc.width // self.__column_width)
        self.__num_rows = max(
            1,
            min(self.__min_rows or 1, len(self.__options)),
            min(math.ceil(len(self.__options) / num_columns), rc.height),
        )

        additional_space = 0
        pages = math.ceil(len(self.__options) / self._page_size)
        if pages > 1:
            additional_space = 1

        return 1 + additional_space, self.__num_rows + additional_space

    def draw(self, rc: RenderContext, /):
        if not self.__options:
            rc.set_color_path("menu/decoration:choice")
            rc.write("No options to display")
            return

        # Adjust for the actual available height.
        self.__num_rows = max(1, min(self.__num_rows, rc.height))
        pages = math.ceil(len(self.__options) / self._page_size)
        if pages > 1 and self.__num_rows > 1:
            self.__num_rows -= 1

        column_width = self.__column_width
        num_rows = self.__num_rows
        page_size = self._page_size

        page_start_index = 0
        if page_size and self.__index is not None:
            page_start_index = self.__index - self.__index % page_size
        page = self.__options[page_start_index : page_start_index + page_size]

        if self.__num_columns > 1:
            available_column_width = column_width - _SPACE_BETWEEN_COLUMNS
        else:
            available_column_width = column_width

        for i, option in enumerate(page):
            x = i // num_rows
            y = i % num_rows

            rc.set_pos(x * column_width, y)

            index = i + page_start_index
            is_current = index == self.__index
            self._render_option(rc, available_column_width, option, is_current)

        pages = math.ceil(len(self.__options) / self._page_size)
        if pages > 1:
            page = (self.index or 0) // self._page_size + 1
            rc.set_pos(0, num_rows)
            rc.set_color_path("menu/text:choice/status_line")
            rc.write("Page ")
            rc.set_color_path("menu/text:choice/status_line/number")
            rc.write(f"{page}")
            rc.set_color_path("menu/text:choice/status_line")
            rc.write(" of ")
            rc.set_color_path("menu/text:choice/status_line/number")
            rc.write(f"{pages}")

    def _get_option_width(self, option: Option[object], decoration_width: int):
        return (
            _SPACE_BETWEEN_COLUMNS
            + decoration_width
            + (_line_width(option.display_text_prefix))
            + (_line_width(option.display_text))
            + (_line_width(option.display_text_suffix))
            + (3 if option.comment else 0)
            + (_line_width(option.comment) if option.comment else 0)
        )

    def _render_option(
        self,
        rc: RenderContext,
        width: int,
        option: Option[object],
        is_active: bool,
    ):
        active_item_decoration = rc.get_msg_decoration(
            self.__active_item_decoration_path
        )
        active_item_decoration_width = _line_width(active_item_decoration)
        selected_item_decoration = rc.get_msg_decoration(
            self.__selected_item_decoration_path
        )
        selected_item_decoration_width = _line_width(selected_item_decoration)
        deselected_item_decoration = rc.get_msg_decoration(
            self.__deselected_item_decoration_path
        )
        deselected_item_decoration_width = _line_width(deselected_item_decoration)
        item_selection_decoration_width = max(
            selected_item_decoration_width, deselected_item_decoration_width
        )

        left_prefix_width = _line_width(option.display_text_prefix)
        left_main_width = _line_width(option.display_text)
        left_suffix_width = _line_width(option.display_text_suffix)
        left_width = left_prefix_width + left_main_width + left_suffix_width
        left_decoration_width = (
            active_item_decoration_width + item_selection_decoration_width
        )

        right = option.comment or ""
        right_width = _line_width(right)
        right_decoration_width = 3 if right else 0

        total_width = (
            left_decoration_width + left_width + right_decoration_width + right_width
        )

        if total_width > width:
            right_width = max(right_width - (total_width - width), 0)
            if right_width == 0:
                right = ""
                right_decoration_width = 0
            total_width = (
                left_decoration_width
                + left_width
                + right_decoration_width
                + right_width
            )

        if total_width > width:
            left_width = max(left_width - (total_width - width), 3)
            total_width = left_decoration_width + left_width

        if is_active:
            status_tag = "active"
        else:
            status_tag = "normal"

        if option.selected:
            color_tag = "selected"
        else:
            color_tag = option.color_tag

        if is_active:
            rc.set_color_path(f"menu/decoration:choice/{status_tag}/{color_tag}")
            rc.write(active_item_decoration)
        else:
            rc.set_color_path(f"menu/text:choice/{status_tag}/{color_tag}")
            rc.write(" " * active_item_decoration_width)

        if option.selected:
            rc.set_color_path(f"menu/decoration:choice/{status_tag}/{color_tag}")
            rc.write(selected_item_decoration)
            rc.write(
                " " * (item_selection_decoration_width - selected_item_decoration_width)
            )
        else:
            rc.set_color_path(f"menu/decoration:choice/{status_tag}/{color_tag}")
            rc.write(deselected_item_decoration)
            rc.write(
                " "
                * (item_selection_decoration_width - deselected_item_decoration_width)
            )

        rc.set_color_path(f"menu/text/prefix:choice/{status_tag}/{color_tag}")
        rc.write(option.display_text_prefix, max_width=left_width)
        rc.set_color_path(f"menu/text:choice/{status_tag}/{color_tag}")
        rc.write(option.display_text, max_width=left_width - left_prefix_width)
        rc.set_color_path(f"menu/text/suffix:choice/{status_tag}/{color_tag}")
        rc.write(
            option.display_text_suffix,
            max_width=left_width - left_prefix_width - left_main_width,
        )
        rc.set_color_path(f"menu/text:choice/{status_tag}/{color_tag}")
        rc.write(
            " "
            * (
                width
                - left_decoration_width
                - left_width
                - right_decoration_width
                - right_width
            )
        )

        if right:
            rc.set_color_path(
                f"menu/decoration/comment:choice/{status_tag}/{color_tag}"
            )
            rc.write(" [")
            rc.set_color_path(f"menu/text/comment:choice/{status_tag}/{color_tag}")
            rc.write(right, max_width=right_width)
            rc.set_color_path(
                f"menu/decoration/comment:choice/{status_tag}/{color_tag}"
            )
            rc.write("]")

    @property
    def help_data(self) -> WidgetHelp:
        return super().help_data.with_action(
            "1..9",
            "a..z",
            long_msg="quick select",
        )


class Choice(Widget[T], _t.Generic[T]):
    """
    Allows choosing from pre-defined options.

    .. vhs:: /_tapes/widget_choice.tape
       :alt: Demonstration of `Choice` widget.
       :scale: 40%

    :param options:
        list of choice options.
    :param mapper:
        maps option to a text that will be used for filtering. By default,
        uses :attr:`Option.display_text`. This argument is ignored
        if a custom `filter` is given.
    :param filter:
        customizes behavior of list filtering. The default filter extracts text
        from an option using the `mapper`, and checks if it starts with the search
        query.
    :param default_index:
        index of the initially selected option.

    """

    @_t.overload
    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: (
            x.display_text or str(x.value)
        ),
        default_index: int = 0,
        search_bar_decoration_path: str = "menu/input/decoration_search",
        active_item_decoration_path: str = "menu/choice/decoration/active_item",
    ): ...

    @_t.overload
    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        filter: _t.Callable[[Option[T], str], bool],
        default_index: int = 0,
        search_bar_decoration_path: str = "menu/input/decoration_search",
        active_item_decoration_path: str = "menu/choice/decoration/active_item",
    ): ...

    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
        filter: _t.Callable[[Option[T], str], bool] | None = None,
        default_index: int = 0,
        search_bar_decoration_path: str = "menu/input/decoration_search",
        active_item_decoration_path: str = "menu/choice/decoration/active_item",
    ):
        self.__options = options

        if filter is None:
            filter = lambda x, q: mapper(x).lstrip().startswith(q)

        self.__filter = filter

        self.__default_index = default_index

        self.__input = Input(
            placeholder="Filter options...", decoration_path=search_bar_decoration_path
        )
        self.__grid = Grid[T](
            [], active_item_decoration_path=active_item_decoration_path
        )

        self.__enable_search = False

        self.__layout: VerticalLayout[_t.Never]

        self.__update_completion()

    @bind("/")
    def search(self):
        """search"""
        if not self.__enable_search:
            self.__enable_search = True
        else:
            self.__input.event(KeyboardEvent("/"))
            self.__update_completion()

    @bind(Key.ENTER)
    @bind(Key.ENTER, alt=True, show_in_detailed_help=False)
    @bind("d", ctrl=True)
    def enter(self) -> Result[T] | None:
        """select"""
        option = self.__grid.get_option()
        if option is not None:
            return Result(option.value)
        else:
            self._bell()

    @bind(Key.ESCAPE)
    def esc(self):
        self.__input.text = ""
        self.__update_completion()
        self.__enable_search = False

    def default_event_handler(self, e: KeyboardEvent) -> Result[T] | None:
        if not self.__enable_search and e == KeyboardEvent(" "):
            return self.enter()
        if not self.__enable_search or e.key in (
            Key.ARROW_UP,
            Key.ARROW_DOWN,
            Key.TAB,
            Key.ARROW_LEFT,
            Key.ARROW_RIGHT,
            Key.PAGE_DOWN,
            Key.PAGE_UP,
            Key.HOME,
            Key.END,
        ):
            self.__grid.event(e)
        elif e == KeyboardEvent(Key.BACKSPACE) and not self.__input.text:
            self.__enable_search = False
        else:
            self.__input.event(e)
            self.__update_completion()

    def __update_completion(self):
        query = self.__input.text

        index = 0
        options = []
        cur_option = self.__grid.get_option()
        for i, option in enumerate(self.__options):
            if not query or self.__filter(option, query):
                if option is cur_option or (
                    cur_option is None and i == self.__default_index
                ):
                    index = len(options)
                options.append(option)

        self.__grid.set_options(options)
        self.__grid.index = index

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        self.__layout = VerticalLayout()
        self.__layout.append(self.__grid)

        if self.__enable_search:
            self.__layout.append(self.__input)

        return self.__layout.layout(rc)

    def draw(self, rc: RenderContext, /):
        self.__layout.draw(rc)

    @property
    def help_data(self) -> WidgetHelp:
        return super().help_data.merge(self.__grid.help_data)


class Multiselect(Widget[list[T]], _t.Generic[T]):
    """
    Like :class:`Choice`, but allows selecting multiple items.

    .. vhs:: /_tapes/widget_multiselect.tape
       :alt: Demonstration of `Multiselect` widget.
       :scale: 40%

    :param options:
        list of choice options.
    :param mapper:
        maps option to a text that will be used for filtering. By default,
        uses :attr:`Option.display_text`. This argument is ignored
        if a custom `filter` is given.
    :param filter:
        customizes behavior of list filtering. The default filter extracts text
        from an option using the `mapper`, and checks if it starts with the search
        query.
    :param default_index:
        index of the initially selected option.

    """

    @_t.overload
    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
    ): ...

    @_t.overload
    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        filter: _t.Callable[[Option[T], str], bool],
    ): ...

    def __init__(
        self,
        options: list[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
        filter: _t.Callable[[Option[T], str], bool] | None = None,
        search_bar_decoration_path: str = "menu/input/decoration_search",
        active_item_decoration_path: str = "menu/choice/decoration/active_item",
        selected_item_decoration_path: str = "menu/choice/decoration/selected_item",
        deselected_item_decoration_path: str = "menu/choice/decoration/deselected_item",
    ):
        self.__options = options

        if filter is None:
            filter = lambda x, q: mapper(x).lstrip().startswith(q)

        self.__filter = filter

        self.__input = Input(
            placeholder="Filter options...", decoration_path=search_bar_decoration_path
        )
        self.__grid = Grid[tuple[T, bool]](
            [],
            active_item_decoration_path=active_item_decoration_path,
            selected_item_decoration_path=selected_item_decoration_path,
            deselected_item_decoration_path=deselected_item_decoration_path,
        )

        self.__enable_search = False

        self.__layout: VerticalLayout[_t.Never]

        self.__update_completion()

    @bind(Key.ENTER)
    @bind(" ")
    def select(self):
        """select"""
        if self.__enable_search and self._cur_event == KeyboardEvent(" "):
            self.__input.event(KeyboardEvent(" "))
            self.__update_completion()
            return
        option = self.__grid.get_option()
        if option is not None:
            option.selected = not option.selected
        self.__update_completion()

    @bind(Key.ENTER, alt=True)
    @bind("d", ctrl=True, show_in_inline_help=True)
    def enter(self) -> Result[list[T]] | None:
        """accept"""
        return Result([option.value for option in self.__options if option.selected])

    @bind("/")
    def search(self):
        """search"""
        if not self.__enable_search:
            self.__enable_search = True
        else:
            self.__input.event(KeyboardEvent("/"))
            self.__update_completion()

    @bind(Key.ESCAPE)
    def esc(self):
        """exit search"""
        self.__input.text = ""
        self.__update_completion()
        self.__enable_search = False

    def default_event_handler(self, e: KeyboardEvent) -> Result[list[T]] | None:
        if not self.__enable_search or e.key in (
            Key.ARROW_UP,
            Key.ARROW_DOWN,
            Key.TAB,
            Key.ARROW_LEFT,
            Key.ARROW_RIGHT,
            Key.PAGE_DOWN,
            Key.PAGE_UP,
            Key.HOME,
            Key.END,
        ):
            self.__grid.event(e)
        elif e == KeyboardEvent(Key.BACKSPACE) and not self.__input.text:
            self.__enable_search = False
        else:
            self.__input.event(e)
            self.__update_completion()

    def __update_completion(self):
        query = self.__input.text

        index = 0
        options = []
        cur_option = self.__grid.get_option()
        for option in self.__options:
            if not query or self.__filter(option, query):
                if option is cur_option:
                    index = len(options)
                options.append(option)

        self.__grid.set_options(options)
        self.__grid.index = index

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        self.__layout = VerticalLayout()
        self.__layout.append(self.__grid)

        if self.__enable_search:
            self.__layout.append(self.__input)

        return self.__layout.layout(rc)

    def draw(self, rc: RenderContext, /):
        self.__layout.draw(rc)

    @property
    def help_data(self) -> WidgetHelp:
        return super().help_data.merge(self.__grid.help_data)


class InputWithCompletion(Widget[str]):
    """
    An input box with tab completion.

    .. vhs:: /_tapes/widget_completion.tape
       :alt: Demonstration of `InputWithCompletion` widget.
       :scale: 40%

    """

    def __init__(
        self,
        completer: yuio.complete.Completer,
        /,
        *,
        placeholder: str = "",
        decoration_path: str = "menu/input/decoration",
        active_item_decoration_path: str = "menu/choice/decoration/active_item",
    ):
        self.__completer = completer

        self.__input = Input(placeholder=placeholder, decoration_path=decoration_path)
        self.__grid = Grid[yuio.complete.Completion](
            [], active_item_decoration_path=active_item_decoration_path, min_rows=None
        )
        self.__grid_active = False

        self.__layout: VerticalLayout[_t.Never]
        self.__rsuffix: yuio.complete.Completion | None = None

    @property
    def text(self) -> str:
        """
        Current text in the input box.

        """

        return self.__input.text

    @property
    def pos(self) -> int:
        """
        Current cursor position, measured in code points before the cursor.

        That is, if the text is `"quick brown fox"` with cursor right before the word
        "brown", then :attr:`~Input.pos` is equal to `len("quick ")`.

        """

        return self.__input.pos

    @property
    def err_region(self) -> tuple[int, int] | None:
        return self.__input.err_region

    @err_region.setter
    def err_region(self, err_region: tuple[int, int] | None, /):
        self.__input.err_region = err_region

    @bind(Key.ENTER)
    @bind("d", ctrl=True)
    @help(inline_msg="accept")
    def enter(self) -> Result[str] | None:
        """accept / select completion"""
        if self.__grid_active and (option := self.__grid.get_option()):
            self._set_input_state_from_completion(option.value)
            self._deactivate_completion()
        else:
            self._drop_rsuffix()
            return Result(self.__input.text)

    @bind(Key.TAB)
    def tab(self):
        """autocomplete"""
        if self.__grid_active:
            self.__grid.next_item()
            if option := self.__grid.get_option():
                self._set_input_state_from_completion(option.value)
            return

        completion = self.__completer.complete(self.__input.text, self.__input.pos)
        if len(completion) == 1:
            self.__input.checkpoint()
            self._set_input_state_from_completion(completion[0])
        elif completion:
            self.__input.checkpoint()
            self.__grid.set_options(
                [
                    Option(
                        c,
                        c.completion,
                        display_text_prefix=c.dprefix,
                        display_text_suffix=c.dsuffix,
                        comment=c.comment,
                        color_tag=c.group_color_tag,
                    )
                    for c in completion
                ],
                default_index=None,
            )
            self._activate_completion()
        else:
            self._bell()

    @bind(Key.ESCAPE)
    def escape(self):
        """close autocomplete"""
        self._drop_rsuffix()
        if self.__grid_active:
            self.__input.restore_checkpoint()
            self._deactivate_completion()

    def default_event_handler(self, e: KeyboardEvent):
        if self.__grid_active and e.key in (
            Key.ARROW_UP,
            Key.ARROW_DOWN,
            Key.TAB,
            Key.PAGE_UP,
            Key.PAGE_DOWN,
            Key.HOME,
            Key.END,
        ):
            self._dispatch_completion_event(e)
        elif (
            self.__grid_active
            and self.__grid.index is not None
            and e.key in (Key.ARROW_RIGHT, Key.ARROW_LEFT)
        ):
            self._dispatch_completion_event(e)
        else:
            self._dispatch_input_event(e)

    def _activate_completion(self):
        self.__grid_active = True

    def _deactivate_completion(self):
        self.__grid_active = False

    def _set_input_state_from_completion(
        self, completion: yuio.complete.Completion, set_rsuffix: bool = True
    ):
        prefix = completion.iprefix + completion.completion
        if set_rsuffix:
            prefix += completion.rsuffix
            self.__rsuffix = completion
        else:
            self.__rsuffix = None
        self.__input.text = prefix + completion.isuffix
        self.__input.pos = len(prefix)

    def _dispatch_completion_event(self, e: KeyboardEvent):
        self.__rsuffix = None
        self.__grid.event(e)
        if option := self.__grid.get_option():
            self._set_input_state_from_completion(option.value)

    def _dispatch_input_event(self, e: KeyboardEvent):
        if self.__rsuffix:
            # We need to drop current rsuffix in some cases:
            if (not e.ctrl and not e.alt and isinstance(e.key, str)) or (
                e.key is Key.PASTE and e.paste_str
            ):
                text = e.key if e.key is not Key.PASTE else e.paste_str
                # When user prints something...
                if text and text[0] in self.__rsuffix.rsymbols:
                    # ...that is in `rsymbols`...
                    self._drop_rsuffix()
            elif e in [
                KeyboardEvent(Key.ARROW_UP),
                KeyboardEvent(Key.ARROW_DOWN),
                KeyboardEvent(Key.ARROW_LEFT),
                KeyboardEvent("b", ctrl=True),
                KeyboardEvent(Key.ARROW_RIGHT),
                KeyboardEvent("f", ctrl=True),
                KeyboardEvent(Key.ARROW_LEFT, alt=True),
                KeyboardEvent("b", alt=True),
                KeyboardEvent(Key.ARROW_RIGHT, alt=True),
                KeyboardEvent("f", alt=True),
                KeyboardEvent(Key.HOME),
                KeyboardEvent("a", ctrl=True),
                KeyboardEvent(Key.END),
                KeyboardEvent("e", ctrl=True),
            ]:
                # ...or when user moves cursor.
                self._drop_rsuffix()
        self.__rsuffix = None
        self.__input.event(e)
        self._deactivate_completion()

    def _drop_rsuffix(self):
        if self.__rsuffix:
            rsuffix = self.__rsuffix.rsuffix
            if self.__input.text[: self.__input.pos].endswith(rsuffix):
                self._set_input_state_from_completion(self.__rsuffix, set_rsuffix=False)

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        self.__layout = VerticalLayout()
        self.__layout.append(self.__input)
        if self.__grid_active:
            self.__layout.append(self.__grid)
        return self.__layout.layout(rc)

    def draw(self, rc: RenderContext, /):
        self.__layout.draw(rc)

    @property
    def help_data(self) -> WidgetHelp:
        return (
            (super().help_data)
            .merge(
                (self.__grid.help_data)
                .without_group("Actions")
                .rename_group(Grid._NAVIGATE, "Navigate Completions")
            )
            .merge(
                (self.__input.help_data)
                .without_group("Actions")
                .rename_group(Input._NAVIGATE, "Navigate Input")
                .rename_group(Input._MODIFY, "Modify Input")
            )
        )


class Map(Widget[T], _t.Generic[T, U]):
    """
    A wrapper that maps result of the given widget using the given function.

    ..
        >>> class Input(Widget):
        ...     def event(self, e):
        ...         return Result("10")
        ...
        ...     def layout(self, rc):
        ...         return 0, 0
        ...
        ...     def draw(self, rc):
        ...         pass
        >>> class Map(Map):
        ...     def run(self, term, theme):
        ...         return self.event(None).value
        >>> term, theme = None, None

    Example::

        >>> # Run `Input` widget, then parse user input as `int`.
        >>> int_input = Map(Input(), int)
        >>> int_input.run(term, theme)
        10

    """

    def __init__(self, inner: Widget[U], fn: _t.Callable[[U], T], /):
        self._inner = inner
        self._fn = fn

    def event(self, e: KeyboardEvent, /) -> Result[T] | None:
        if result := self._inner.event(e):
            return Result(self._fn(result.value))

    def layout(self, rc: RenderContext, /) -> tuple[int, int]:
        return self._inner.layout(rc)

    def draw(self, rc: RenderContext, /):
        self._inner.draw(rc)

    @property
    def help_data(self) -> WidgetHelp:
        return self._inner.help_data


class Apply(Map[T, T], _t.Generic[T]):
    """
    A wrapper that applies the given function to the result of a wrapped widget.

    ..
        >>> class Input(Widget):
        ...     def event(self, e):
        ...         return Result("foobar!")
        ...
        ...     def layout(self, rc):
        ...         return 0, 0
        ...
        ...     def draw(self, rc):
        ...         pass
        >>> class Apply(Apply):
        ...     def run(self, term, theme):
        ...         return self.event(None).value
        >>> term, theme = None, None

    Example::

        >>> # Run `Input` widget, then print its output before returning
        >>> print_output = Apply(Input(), print)
        >>> result = print_output.run(term, theme)
        foobar!
        >>> result
        'foobar!'

    """

    def __init__(self, inner: Widget[T], fn: _t.Callable[[T], None], /):
        def mapper(x: T) -> T:
            fn(x)
            return x

        super().__init__(inner, mapper)


class Task(Widget[_t.Never]):
    """
    Widget that's used to render :class:`~yuio.io.Task`\\ s.

    """

    class Status(enum.Enum):
        """
        Task status.

        """

        DONE = "done"
        """
        Task has finished successfully.

        """

        ERROR = "error"
        """
        Task has finished with an error.

        """

        RUNNING = "running"
        """
        Task is running.

        """

        PENDING = "pending"
        """
        Task is waiting to start.

        """

    def __init__(
        self,
        msg: str,
        /,
        *args,
        comment: str | None = None,
    ) -> None:
        super().__init__()

        self._msg: str = msg
        self._args: tuple[object, ...] = args
        self._comment: str | None = comment
        self._comment_args: tuple[object, ...] | None = None
        self._progress: float | None = None
        self._progress_done: str | None = None
        self._progress_total: str | None = None

        self.status: Task.Status = Task.Status.PENDING

        self._cached_msg: yuio.string.ColorizedString | None = None
        self._cached_comment: yuio.string.ColorizedString | None = None

    @_t.overload
    def progress(self, progress: float | None, /, *, ndigits: int = 2): ...

    @_t.overload
    def progress(
        self,
        done: float | int,
        total: float | int,
        /,
        *,
        unit: str = "",
        ndigits: int = 0,
    ): ...

    def progress(
        self,
        *args: float | int | None,
        unit: str = "",
        ndigits: int | None = None,
    ):
        """
        See :meth:`~yuio.io.Task.progress`.

        """

        progress = None

        if len(args) == 1:
            progress = done = args[0]
            total = None
            if ndigits is None:
                ndigits = 2
        elif len(args) == 2:
            done, total = args
            if ndigits is None:
                ndigits = (
                    2 if isinstance(done, float) or isinstance(total, float) else 0
                )
        else:
            raise ValueError(
                f"Task.progress() takes between one and two arguments "
                f"({len(args)} given)"
            )

        if done is None:
            self._progress = None
            self._progress_done = None
            self._progress_total = None
            return

        if len(args) == 1:
            done *= 100
            unit = "%"

        done_str = "%.*f" % (ndigits, done)
        if total is None:
            self._progress = progress
            self._progress_done = done_str + unit
            self._progress_total = None
        else:
            total_str = "%.*f" % (ndigits, total)
            self._progress = done / total if total else 0
            self._progress_done = done_str
            self._progress_total = total_str + unit

    def progress_size(
        self,
        done: float | int,
        total: float | int,
        /,
        *,
        ndigits: int = 2,
    ):
        """
        See :meth:`~yuio.io.Task.progress_size`.

        """

        progress = done / total
        done, done_unit = self.__size(done)
        total, total_unit = self.__size(total)

        if done_unit == total_unit:
            done_unit = ""

        self._progress = progress
        self._progress_done = "%.*f%s" % (ndigits, done, done_unit)
        self._progress_total = "%.*f%s" % (ndigits, total, total_unit)

    @staticmethod
    def __size(n):
        for unit in "BKMGT":
            if n < 1024:
                return n, unit
            n /= 1024
        return n, "P"

    def progress_scale(
        self,
        done: float | int,
        total: float | int,
        /,
        *,
        unit: str = "",
        ndigits: int = 2,
    ):
        """
        See :meth:`~yuio.io.Task.progress_scale`.

        """

        progress = done / total
        done, done_unit = self.__unit(done)
        total, total_unit = self.__unit(total)

        if unit:
            done_unit += unit
            total_unit += unit

        self._progress = progress
        self._progress_done = "%.*f%s" % (ndigits, done, done_unit)
        self._progress_total = "%.*f%s" % (ndigits, total, total_unit)

    @staticmethod
    def __unit(n: float) -> tuple[float, str]:
        if math.fabs(n) < 1e-33:
            return 0, ""
        magnitude = max(-8, min(8, int(math.log10(math.fabs(n)) // 3)))
        if magnitude < 0:
            return n * 10 ** -(3 * magnitude), "munpfazy"[-magnitude - 1]
        elif magnitude > 0:
            return n / 10 ** (3 * magnitude), "KMGTPEZY"[magnitude - 1]
        else:
            return n, ""

    def comment(self, comment: str | None, /, *args):
        """
        See :meth:`~yuio.io.Task.comment`.

        """

        self._comment = comment
        self._comment_args = args
        self._cached_comment = None

    def layout(self, rc: RenderContext) -> tuple[int, int]:
        return 1, 1  # Tasks are always one line high.

    def draw(self, rc: RenderContext):
        return self._draw_task(rc)

    def _format_task(self, ctx: yuio.string.ReprContext) -> yuio.string.ColorizedString:
        """
        Format this task for printing to the log.

        """

        res = yuio.string.ColorizedString()

        status = self.status.value

        if decoration := ctx.get_msg_decoration("task"):
            res += ctx.get_color(f"task/decoration:{status}")
            res += decoration

        res += self._format_task_msg(ctx)
        res += ctx.get_color(f"task:{status}")
        res += " - "
        res += ctx.get_color(f"task/progress:{status}")
        res += self.status.value
        res += ctx.get_color(f"task:{status}")

        return res

    def _format_task_msg(
        self, ctx: yuio.string.ReprContext
    ) -> yuio.string.ColorizedString:
        """
        Format task's message.

        """

        if self._cached_msg is None:
            msg = yuio.string.colorize(
                self._msg,
                *self._args,
                default_color=f"task/heading:{self.status.value}",
                ctx=ctx,
            )
            self._cached_msg = msg
        return self._cached_msg

    def _format_task_comment(
        self, rc: RenderContext
    ) -> yuio.string.ColorizedString | None:
        """
        Format task's comment.

        """

        if self.status is not Task.Status.RUNNING:
            return None
        if self._cached_comment is None and self._comment is not None:
            comment = yuio.string.colorize(
                self._comment,
                *(self._comment_args or ()),
                default_color=f"task/comment:{self.status.value}",
                ctx=rc.make_repr_context(),
            )
            self._cached_comment = comment
        return self._cached_comment

    def _draw_task(self, rc: RenderContext):
        """
        Draw task.

        """

        self._draw_task_progressbar(rc)
        rc.write(self._format_task_msg(rc.make_repr_context()))
        self._draw_task_progress(rc)
        if comment := self._format_task_comment(rc):
            rc.set_color_path(f"task:{self.status.value}")
            rc.write(" - ")
            rc.write(comment)

    def _draw_task_progress(self, rc: RenderContext):
        """
        Draw number that indicates task's progress.

        """

        if self.status is not Task.Status.RUNNING:
            rc.set_color_path(f"task:{self.status.value}")
            rc.write(" - ")
            rc.set_color_path(f"task/progress:{self.status.value}")
            rc.write(self.status.value)
        elif self._progress_done is not None:
            rc.set_color_path(f"task:{self.status.value}")
            rc.write(" - ")
            rc.set_color_path(f"task/progress:{self.status.value}")
            rc.write(self._progress_done)
            if self._progress_total is not None:
                rc.set_color_path(f"task:{self.status.value}")
                rc.write("/")
                rc.set_color_path(f"task/progress:{self.status.value}")
                rc.write(self._progress_total)

    def _draw_task_progressbar(self, rc: RenderContext):
        """
        Draw task's progressbar.

        """

        progress_bar_start_symbol = rc.theme.get_msg_decoration(
            "progress_bar/start_symbol", is_unicode=rc.term.is_unicode
        )
        progress_bar_end_symbol = rc.theme.get_msg_decoration(
            "progress_bar/end_symbol", is_unicode=rc.term.is_unicode
        )
        total_width = (
            rc.theme.progress_bar_width
            - yuio.string.line_width(progress_bar_start_symbol)
            - yuio.string.line_width(progress_bar_end_symbol)
        )
        progress_bar_done_symbol = rc.theme.get_msg_decoration(
            "progress_bar/done_symbol", is_unicode=rc.term.is_unicode
        )
        progress_bar_pending_symbol = rc.theme.get_msg_decoration(
            "progress_bar/pending_symbol", is_unicode=rc.term.is_unicode
        )
        if self.status != Task.Status.RUNNING:
            rc.set_color_path(f"task/decoration:{self.status.value}")
            rc.write(
                rc.theme.get_msg_decoration(
                    "spinner/static_symbol", is_unicode=rc.term.is_unicode
                )
            )
        elif (
            self._progress is None
            or total_width <= 1
            or not progress_bar_done_symbol
            or not progress_bar_pending_symbol
        ):
            rc.set_color_path(f"task/decoration:{self.status.value}")
            spinner_pattern = rc.theme.get_msg_decoration(
                "spinner/pattern", is_unicode=rc.term.is_unicode
            )
            if spinner_pattern:
                rc.write(spinner_pattern[rc.spinner_state % len(spinner_pattern)])
        else:
            transition_pattern = rc.theme.get_msg_decoration(
                "progress_bar/transition_pattern", is_unicode=rc.term.is_unicode
            )

            progress = max(0, min(1, self._progress))
            if transition_pattern:
                done_width = int(total_width * progress)
                transition_factor = 1 - (total_width * progress - done_width)
                transition_width = 1
            else:
                done_width = round(total_width * progress)
                transition_factor = 0
                transition_width = 0

            rc.set_color_path(f"task/progressbar:{self.status.value}")
            rc.write(progress_bar_start_symbol)

            done_color = yuio.color.Color.lerp(
                rc.theme.get_color("task/progressbar/done/start"),
                rc.theme.get_color("task/progressbar/done/end"),
            )

            for i in range(0, done_width):
                rc.set_color(done_color(i / (total_width - 1)))
                rc.write(progress_bar_done_symbol)

            if transition_pattern and done_width < total_width:
                rc.set_color(done_color(done_width / (total_width - 1)))
                rc.write(
                    transition_pattern[
                        int(len(transition_pattern) * transition_factor - 1)
                    ]
                )

            pending_color = yuio.color.Color.lerp(
                rc.theme.get_color("task/progressbar/pending/start"),
                rc.theme.get_color("task/progressbar/pending/end"),
            )

            for i in range(done_width + transition_width, total_width):
                rc.set_color(pending_color(i / (total_width - 1)))
                rc.write(progress_bar_pending_symbol)

            rc.set_color_path(f"task/progressbar:{self.status.value}")
            rc.write(progress_bar_end_symbol)

        rc.set_color_path(f"task:{self.status.value}")
        rc.write(" ")

    def __colorized_str__(self, ctx: yuio.string.ReprContext) -> _ColorizedString:
        return self._format_task(ctx)


@dataclass(slots=True)
class _EventStreamState:
    ostream: _t.TextIO
    istream: _t.TextIO
    key: str = ""
    index: int = 0

    def load(self):
        key = ""
        while not key:
            key = yuio.term._read_keycode(self.ostream, self.istream)
        self.key = key
        self.index = 0

    def next(self):
        ch = self.peek()
        self.index += 1
        return ch

    def peek(self):
        if self.index >= len(self.key):
            return ""
        else:
            return self.key[self.index]

    def tail(self):
        return self.key[self.index :]


def _event_stream(ostream: _t.TextIO, istream: _t.TextIO) -> _t.Iterator[KeyboardEvent]:
    # Implementation is heavily inspired by libtermkey by Paul Evans, MIT license,
    # with some additions for modern protocols.
    # See https://sw.kovidgoyal.net/kitty/keyboard-protocol/.

    state = _EventStreamState(ostream, istream)
    while True:
        ch = state.next()
        if not ch:
            state.load()
            ch = state.next()
        if ch == "\x1b":
            alt = False
            ch = state.next()
            while ch == "\x1b":
                alt = True
                ch = state.next()
            if not ch:
                yield KeyboardEvent(Key.ESCAPE, alt=alt)
            elif ch == "[":
                yield from _parse_csi(state, alt)
            elif ch in "N]":
                _parse_dcs(state)
            elif ch == "O":
                yield from _parse_ss3(state, alt)
            else:
                yield from _parse_char(ch, alt=True)
        elif ch == "\x9b":
            # CSI
            yield from _parse_csi(state, False)
        elif ch in "\x90\x9d":
            # DCS or SS2
            _parse_dcs(state)
        elif ch == "\x8f":
            # SS3
            yield from _parse_ss3(state, False)
        else:
            # Char
            yield from _parse_char(ch)


def _parse_ss3(state: _EventStreamState, alt: bool = False):
    ch = state.next()
    if not ch:
        yield KeyboardEvent("O", alt=True)
    else:
        yield from _parse_ss3_key(ch, alt=alt)


def _parse_dcs(state: _EventStreamState):
    while True:
        ch = state.next()
        if ch == "\x9c":
            break
        elif ch == "\x1b" and state.peek() == "\\":
            state.next()
            break
        elif not ch:
            state.load()


def _parse_csi(state: _EventStreamState, alt: bool = False):
    buffer = ""
    while state.peek() and not (0x40 <= ord(state.peek()) <= 0x80):
        buffer += state.next()
    cmd = state.next()
    if not cmd:
        yield KeyboardEvent("[", alt=True)
        return
    if buffer.startswith(("?", "<", ">", "=")):
        # Some command response, ignore.
        return  # pragma: no cover
    args = buffer.split(";")

    shift = ctrl = False
    if len(args) > 1:
        try:
            modifiers = int(args[1]) - 1
        except ValueError:  # pragma: no cover
            pass
        else:
            shift = bool(modifiers & 1)
            alt |= bool(modifiers & 2)
            ctrl = bool(modifiers & 4)

    if cmd == "~":
        if args[0] == "27":
            try:
                ch = chr(int(args[2]))
            except (ValueError, KeyError):  # pragma: no cover
                pass
            else:
                yield from _parse_char(ch, ctrl=ctrl, alt=alt, shift=shift)
        elif args[0] == "200":
            yield KeyboardEvent(Key.PASTE, paste_str=_read_pasted_content(state))
        elif key := _CSI_CODES.get(args[0]):
            yield KeyboardEvent(key, ctrl=ctrl, alt=alt, shift=shift)
    elif cmd == "u":
        try:
            ch = chr(int(args[0]))
        except ValueError:  # pragma: no cover
            pass
        else:
            yield from _parse_char(ch, ctrl=ctrl, alt=alt, shift=shift)
    elif cmd in "mMyR":
        # Some command response, ignore.
        pass  # pragma: no cover
    else:
        yield from _parse_ss3_key(cmd, ctrl=ctrl, alt=alt, shift=shift)


def _parse_ss3_key(
    cmd: str, ctrl: bool = False, alt: bool = False, shift: bool = False
):
    if key := _SS3_CODES.get(cmd):
        if cmd == "Z":
            shift = True
        yield KeyboardEvent(key, ctrl=ctrl, alt=alt, shift=shift)


_SS3_CODES = {
    "A": Key.ARROW_UP,
    "B": Key.ARROW_DOWN,
    "C": Key.ARROW_RIGHT,
    "D": Key.ARROW_LEFT,
    "E": Key.HOME,
    "F": Key.END,
    "H": Key.HOME,
    "Z": Key.TAB,
    "P": Key.F1,
    "Q": Key.F2,
    "R": Key.F3,
    "S": Key.F4,
    "M": Key.ENTER,
    " ": " ",
    "I": Key.TAB,
    "X": "=",
    "j": "*",
    "k": "+",
    "l": ",",
    "m": "-",
    "n": ".",
    "o": "/",
    "p": "0",
    "q": "1",
    "r": "2",
    "s": "3",
    "t": "4",
    "u": "5",
    "v": "6",
    "w": "7",
    "x": "8",
    "y": "9",
}


_CSI_CODES = {
    "1": Key.HOME,
    "2": Key.INSERT,
    "3": Key.DELETE,
    "4": Key.END,
    "5": Key.PAGE_UP,
    "6": Key.PAGE_DOWN,
    "7": Key.HOME,
    "8": Key.END,
    "11": Key.F1,
    "12": Key.F2,
    "13": Key.F3,
    "14": Key.F4,
    "15": Key.F5,
    "17": Key.F6,
    "18": Key.F7,
    "19": Key.F8,
    "20": Key.F9,
    "21": Key.F10,
    "23": Key.F11,
    "24": Key.F12,
    "200": Key.PASTE,
}


def _parse_char(
    ch: str, ctrl: bool = False, alt: bool = False, shift: bool = False
) -> _t.Iterable[KeyboardEvent]:
    if ch == "\t":
        yield KeyboardEvent(Key.TAB, ctrl, alt, shift)
    elif ch in "\r\n":
        yield KeyboardEvent(Key.ENTER, ctrl, alt, shift)
    elif ch == "\x08":
        yield KeyboardEvent(Key.BACKSPACE, ctrl, alt, shift)
    elif ch == "\x1b":
        yield KeyboardEvent(Key.ESCAPE, ctrl, alt, shift)
    elif ch == "\x7f":
        yield KeyboardEvent(Key.BACKSPACE, ctrl, alt, shift)
    elif "\x00" <= ch <= "\x1a":
        yield KeyboardEvent(chr(ord(ch) + ord("a") - 0x01), True, alt, shift)
    elif "\x1c" <= ch <= "\x1f":
        yield KeyboardEvent(chr(ord(ch) + ord("4") - 0x1C), True, alt, shift)
    elif ch in string.printable or ord(ch) >= 160:
        yield KeyboardEvent(ch, ctrl, alt, shift)


def _read_pasted_content(state: _EventStreamState) -> str:
    buf = ""
    while True:
        index = state.tail().find("\x1b[201~")
        if index == -1:
            buf += state.tail()
        else:
            buf += state.tail()[:index]
            state.index += index
            return buf
        state.load()
