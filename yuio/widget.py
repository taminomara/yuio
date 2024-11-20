# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Basic blocks for building interactive elements.

This is a low-level API module, upon which :mod:`yuio.io` builds
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

Widgets automatically generate help: the help menu is available via the ``F1`` key,
and there's also inline help that is displayed under the widget.

By default, help items are generated from event handler docstrings:
all event handlers that have them will be displayed in the help menu.

You can control which keybindings appear in the help menu and inline help
by supplying ``show_in_inline_help`` and ``show_in_detailed_help`` arguments
to the :func:`bind` function.

For even more detailed customization you can decorate an event handler with
the :func:`help` decorator:

.. autofunction:: help

Lastly, you can override :attr:`Widget.help_data` and generate
the :class:`WidgetHelp` yourself:

.. autoclass:: WidgetHelp
   :members:

.. autodata:: ActionKey

.. autodata:: ActionKeys

.. autodata:: Action


Pre-defined widgets
-------------------

.. autoclass:: Line

.. autoclass:: Text

.. autoclass:: Input

.. autoclass:: Choice

.. autoclass:: Option

.. autoclass:: InputWithCompletion

.. autoclass:: Map

.. autoclass:: Apply


"""

import abc
import contextlib
import dataclasses
import enum
import functools
import math
import re
import shutil
import string
import sys
from dataclasses import dataclass

import yuio.complete
import yuio.md
import yuio.term
import yuio.theme
from yuio import _typing as _t
from yuio.term import Color as _Color
from yuio.term import ColorizedString as _ColorizedString
from yuio.term import Term as _Term
from yuio.term import line_width as _line_width
from yuio.theme import Theme as _Theme

_SPACE_BETWEEN_COLUMNS = 2
_MIN_COLUMN_WIDTH = 10

_UNPRINTABLE_TRANS = str.maketrans(
    "".join(chr(i) for i in range(32)) + "\x7f", " " * 33
)


T = _t.TypeVar("T")
U = _t.TypeVar("U")
T_co = _t.TypeVar("T_co", covariant=True)


class Key(enum.Enum):
    """Non-character keys."""

    #: `Enter` key.
    ENTER = enum.auto()

    #: `Escape` key.
    ESCAPE = enum.auto()

    #: `Delete` key.
    DELETE = enum.auto()

    #: `Backspace` key.
    BACKSPACE = enum.auto()

    #: `Tab` key.
    TAB = enum.auto()

    #: `Tab` key with `Shift` modifier.
    SHIFT_TAB = enum.auto()

    #: `Home` key.
    HOME = enum.auto()

    #: `End` key.
    END = enum.auto()

    #: `PageUp` key.
    PAGE_UP = enum.auto()

    #: `PageDown` key.
    PAGE_DOWN = enum.auto()

    #: `ArrowUp` key.
    ARROW_UP = enum.auto()

    #: `ArrowDown` key.
    ARROW_DOWN = enum.auto()

    #: `ArrowLeft` key.
    ARROW_LEFT = enum.auto()

    #: `ArrowRight` key.
    ARROW_RIGHT = enum.auto()

    #: `F1` key.
    F1 = enum.auto()

    #: `F2` key.
    F2 = enum.auto()

    #: `F3` key.
    F3 = enum.auto()

    #: `F4` key.
    F4 = enum.auto()

    def __str__(self) -> str:
        return self.name.replace("_", " ").title()


@dataclass(frozen=True, **yuio._with_slots())
class KeyboardEvent:
    """A single keyboard event.

    Note that we don't have separate flag for when `Shift` was pressed with keystroke
    because that results in :attr:`~KeyboardEvent.key` being a capital letter.

    """

    #: Which key was pressed? Can be a single character,
    #: or a :class:`Key` for non-character keys.
    key: _t.Union[Key, str]

    #: Whether a `Ctrl` modifier was pressed with keystroke.
    ctrl: bool = False

    #: Whether an `Alt` (`Option` on macs) modifier was pressed with keystroke.
    alt: bool = False


@_t.final
class RenderContext:
    """A canvas onto which widgets render themselves.

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
    _override_wh: _t.Optional[_t.Tuple[int, int]] = None

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
        self._lines: _t.List[_t.List[str]] = []
        self._colors: _t.List[_t.List[str]] = []
        self._prev_lines: _t.List[_t.List[str]] = []
        self._prev_colors: _t.List[_t.List[str]] = []

        # Rendering status
        self._full_redraw: bool = False
        self._term_x: int = 0
        self._term_y: int = 0
        self._term_color: str = ""
        self._max_term_y: int = 0
        self._out: _t.List[str] = []
        self._bell: bool = False
        self._in_alternative_buffer: bool = False
        self._normal_buffer_term_x: int = 0
        self._normal_buffer_term_y: int = 0

        # Helpers
        self._none_color: str = _Color.NONE.as_code(term)

        # Used for tests and debug
        self._renders: int = 0
        self._bytes_rendered: int = 0
        self._total_bytes_rendered: int = 0

    @property
    def term(self) -> _Term:
        """Terminal where we render the widgets."""

        return self._term

    @property
    def theme(self) -> _Theme:
        """Current color theme."""

        return self._theme

    @contextlib.contextmanager
    def frame(
        self,
        x: int,
        y: int,
        /,
        *,
        width: _t.Optional[int] = None,
        height: _t.Optional[int] = None,
    ):
        """Override drawing frame.

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
                        "very long paragraph which "
                        "potentially can span multiple lines"
                    )

                def layout(self, rc: RenderContext) -> _t.Tuple[int, int]:
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
        """Get width of the current frame."""

        return self._frame_w

    @property
    def height(self) -> int:
        """Get height of the current frame."""

        return self._frame_h

    def set_pos(self, x: int, y: int, /):
        """Set current cursor position within the frame."""

        self._frame_cursor_x = x
        self._frame_cursor_y = y

    def move_pos(self, dx: int, dy: int, /):
        """Move current cursor position by the given amount."""

        self._frame_cursor_x += dx
        self._frame_cursor_y += dy

    def new_line(self):
        """Move cursor to new line within the current frame."""

        self._frame_cursor_x = 0
        self._frame_cursor_y += 1

    def set_final_pos(self, x: int, y: int, /):
        """Set position where the cursor should end up
        after everything has been rendered.

        By default, cursor will end up at the beginning of the last line.
        Components such as :class:`Input` can modify this behavior
        and move the cursor into the correct position.

        """

        self._final_x = x + self._frame_x
        self._final_y = y + self._frame_y

    def set_color_path(self, path: str, /):
        """Set current color by fetching it from the theme by path."""

        self._frame_cursor_color = self._theme.get_color(path).as_code(self._term)

    def set_color(self, color: _Color, /):
        """Set current color."""

        self._frame_cursor_color = color.as_code(self._term)

    def reset_color(self):
        """Set current color to the default color of the terminal."""

        self._frame_cursor_color = self._none_color

    def write(
        self, text: yuio.term.AnyString, /, *, max_width: _t.Optional[int] = None
    ):
        r"""Write string at the current position using the current color.
        Move cursor while printing.

        While the displayed text will not be clipped at frame's borders,
        its width can be limited by passing `max_width`. Note that
        ``rc.write(text, max_width)`` is not the same
        as ``rc.write(text[:max_width])``, because the later case
        doesn't account for double-width characters.

        All whitespace characters in the text, including tabs and newlines,
        will be treated as single spaces. If you need to print multiline text,
        use :meth:`yuio.term.ColorizedString.wrap` and :meth:`~RenderContext.write_text`.

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
            >>> rc.write("Hello,\nworld!")
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

        Notice that ``'\n'`` on the second line was replaced with a space.
        Notice also that the last line wasn't properly clipped.

        """

        if not isinstance(text, _ColorizedString):
            text = _ColorizedString(text)

        x = self._frame_x + self._frame_cursor_x
        y = self._frame_y + self._frame_cursor_y

        self._frame_cursor_x += text.width

        if not 0 <= y < self._height:
            for s in text:
                if isinstance(s, _Color):
                    self._frame_cursor_color = s.as_code(self.term)
            return

        ll = self._lines[y]
        cc = self._colors[y]

        max_x = self._width
        if max_width is not None:
            max_x = min(max_x, x + max_width)

        for s in text:
            if isinstance(s, _Color):
                self._frame_cursor_color = s.as_code(self._term)
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
                self._lines[y][x : x + l] = s[slice_begin:slice_end]
                self._colors[y][x : x + l] = [self._frame_cursor_color] * l
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

                x += 1
                cw -= 1
                if cw:
                    ll[x : x + cw] = [""] * cw
                    cc[x : x + cw] = [self._frame_cursor_color] * cw
                    x += cw

    def write_text(
        self,
        lines: _t.Iterable[yuio.term.AnyString],
        /,
        *,
        max_width: _t.Optional[int] = None,
    ):
        """Write multiple lines.

        Each line is printed using :meth:`~RenderContext.write`,
        so newline characters and tabs within each line are replaced with spaces.
        Use :meth:`yuio.term.ColorizedString.wrap` to properly handle them.

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
        """Ring a terminal bell."""

        self._bell = True

    def prepare(self, *, full_redraw: bool = False, alternative_buffer: bool = False):
        """Reset output canvas and prepare context for a new round of widget formatting."""

        if self._override_wh:
            width, height = self._override_wh
        else:
            size = shutil.get_terminal_size()
            width = size.columns
            height = size.lines

        full_redraw = full_redraw or self._width != width or self._height != height
        if self._in_alternative_buffer != alternative_buffer:
            full_redraw = True
            self._in_alternative_buffer = alternative_buffer
            if alternative_buffer:
                self._out.append("\x1b[m\x1b[?1049h\x1b[2J\x1b[H")
                self._normal_buffer_term_x = self._term_x
                self._normal_buffer_term_y = self._term_y
                self._term_x, self._term_y = 0, 0
                self._term_color = self._none_color
            else:
                self._out.append("\x1b[m\x1b[?1049l")
                self._term_x = self._normal_buffer_term_x
                self._term_y = self._normal_buffer_term_y
                self._term_color = self._none_color

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
            self._prev_lines, self._prev_colors = self._make_empty_canvas()
        else:
            self._prev_lines, self._prev_colors = self._lines, self._colors
        self._lines, self._colors = self._make_empty_canvas()

        # Rendering status
        self._full_redraw = full_redraw

    def clear_screen(self):
        """Clear screen and prepare for a full redraw."""

        self._out.append("\x1b[2J\x1b[1H")
        self._term_x, self._term_y = 0, 0
        self.prepare(full_redraw=True, alternative_buffer=self._in_alternative_buffer)

    def _make_empty_canvas(
        self,
    ) -> _t.Tuple[_t.List[_t.List[str]], _t.List[_t.List[str]]]:
        lines = [l[:] for l in [[" "] * self._width] * self._height]
        colors = [
            c[:] for c in [[self._frame_cursor_color] * self._width] * self._height
        ]
        return lines, colors

    def render(self):
        """Render current canvas onto the terminal."""

        if not self.term.can_move_cursor:
            # For tests. Widgets can't work with dumb terminals
            self._render_dumb()
            return

        if self._bell:
            self._out.append("\a")
            self._bell = False

        if self._full_redraw:
            self._move_term_cursor(0, 0)
            self._out.append("\x1b[J")

        for y in range(self._height):
            line = self._lines[y]

            for x in range(self._width):
                prev_color = self._prev_colors[y][x]
                color = self._colors[y][x]

                if color != prev_color or line[x] != self._prev_lines[y][x]:
                    self._move_term_cursor(x, y)

                    if color != self._term_color:
                        self._out.append(color)
                        self._term_color = color

                    self._out.append(line[x])
                    self._term_x += 1

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
            self._out.append(
                (yuio.term.Color.FORE_BLACK | yuio.term.Color.BACK_CYAN).as_code(
                    self.term
                )
            )
            self._out.append(debug_msg)
            self._out.append(self._term_color)
            self._move_term_cursor(term_x, term_y)

            self._term.ostream.write("".join(self._out))
            self._term.ostream.flush()
            self._out.clear()

    def finalize(self):
        """Erase any rendered widget and move cursor to the initial position."""

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
            [
                # Trim trailing spaces for doctests.
                re.sub(r" +$", "\n", line, flags=re.MULTILINE)
                for line in "".join(self._out).splitlines()
            ]
        )
        self._term.ostream.flush()
        self._out.clear()


@dataclass(frozen=True, **yuio._with_slots())
class Result(_t.Generic[T_co]):
    """Result of a widget run.

    We have to wrap the return value of event processors into this class.
    Otherwise we won't be able to distinguish between returning `None`
    as result of a ``Widget[None]``, and not returning anything.

    """

    #: Result of a widget run.
    value: T_co


class Widget(abc.ABC, _t.Generic[T_co]):
    """Base class for all interactive console elements.

    Widgets are displayed with their :meth:`~Widget.run` method.
    They always go through the same event loop:

    .. raw:: html
       :file: ../docs/source/_embeds/widget.html


    Widgets run indefinitely until they stop themselves and return a value.
    For example, :class:`Input` will return when user presses `Enter`.
    When widget needs to stop, it can return the :meth:`Result` class
    from its event handler.

    For typing purposes, :class:`Widget` is generic. That is, ``Widget[T]``
    returns `T` from its :meth:`~Widget.run` method. So, :class:`Input`,
    for example, is ``Widget[str]``.

    Some widgets are ``Widget[Never]`` (see :class:`typing.Never`), indicating that
    they don't ever stop. Others are ``Widget[None]``, indicating that they stop,
    but don't return a value.

    """

    __bindings: _t.ClassVar[_t.Dict[KeyboardEvent, _t.Callable[[_t.Any], _t.Any]]]
    __callbacks: _t.ClassVar[_t.List[object]]

    __in_help_menu: bool = False
    __bell: bool = False

    #: Current event that is being processed.
    #: Guaranteed to be not :data:`None` inside event handlers.
    _cur_event: _t.Optional[KeyboardEvent] = None

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
                bindings: _t.List["_Binding"] = cb.__yuio_keybindings__
                cls.__bindings.update((binding.event, cb) for binding in bindings)
                cls.__callbacks.append(cb)

    def event(self, e: KeyboardEvent, /) -> _t.Optional[Result[T_co]]:
        """Handle incoming keyboard event.

        By default, this function dispatches event to handlers registered
        via :func:`bind`. If no handler is found,
        it calls :meth:`~Widget.default_event_handler`.

        """

        self._cur_event = e
        if handler := self.__bindings.get(e):
            return handler(self)
        else:
            return self.default_event_handler(e)

    def default_event_handler(self, e: KeyboardEvent, /) -> _t.Optional[Result[T_co]]:
        """Process any event that wasn't caught by other event handlers."""

    @abc.abstractmethod
    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        """Prepare widget for drawing, and recalculate its dimensions
        according to new frame dimensions.

        Yuio's widgets always take all available width. They should return
        their minimum height that they will definitely take, and their maximum
        height that they can potentially take.

        """

    @abc.abstractmethod
    def draw(self, rc: RenderContext, /):
        """Draw the widget.

        Render context's drawing frame dimensions are guaranteed to be between
        the minimum and the maximum height returned from the last call
        to :meth:`~Widget.layout`.

        """

    @_t.final
    def run(self, term: _Term, theme: _Theme, /) -> T_co:
        """Read user input and run the widget."""

        if not term.is_fully_interactive:
            raise RuntimeError("terminal doesn't support rendering widgets")

        with yuio.term._enter_raw_mode():
            rc = RenderContext(term, theme)

            events = _event_stream()

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
                        # windows doesn't handle C-c for us.
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
    def help_data(self) -> "WidgetHelp":
        """Data for displaying help messages.

        See :func:`help` for more info.

        """

        return self.__help_columns

    @functools.cached_property
    def __help_columns(self) -> "WidgetHelp":
        inline_help: _t.List[Action] = []
        groups: _t.Dict[str, _t.List[Action]] = {}

        for cb in self.__callbacks:
            bindings: _t.List[_Binding] = getattr(cb, "__yuio_keybindings__", [])
            help: _t.Optional[_Help] = getattr(cb, "__yuio_help__", None)
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

    __last_help_data: _t.Optional["WidgetHelp"] = None
    __prepared_inline_help: _t.List[_t.Tuple[_t.List[str], str, str, int]]
    __prepared_groups: _t.Dict[str, _t.List[_t.Tuple[_t.List[str], str, str, int]]]
    __has_help: bool = True
    __width: int = 0
    __height: int = 0
    __menu_content_height: int = 0
    __help_menu_line: int = 0
    __help_menu_search: bool = False
    __help_menu_search_widget: "Input"
    __help_menu_search_layout: _t.Tuple[int, int] = 0, 0
    __key_width: int = 0
    __wrapped_groups: _t.List[
        _t.Tuple[
            str,  # Title
            _t.List[  # Actions
                _t.Tuple[  # Action
                    _t.List[str],  # Keys
                    _t.List[_ColorizedString],  # Wrapped msg
                    int,  # Keys width
                ],
            ],
        ]  # FML this type hint -___-
    ]
    __colorized_inline_help: _t.List[
        _t.Tuple[  # Action
            _t.List[str],  # Keys
            _ColorizedString,  # Title
            int,  # Keys width
        ]
    ]

    def __help_menu_event(self, e: KeyboardEvent, /) -> _t.Optional[Result[T_co]]:
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
            self.__help_menu_search_widget = Input(decoration="/")
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
            self.__prepared_groups = self.__prepare_groups(self.__last_help_data)
            self.__prepared_inline_help = self.__prepare_inline_help(
                self.__last_help_data
            )
            self.__has_help = bool(
                self.__last_help_data.inline_help or self.__last_help_data.groups
            )

        return True

    def __help_menu_layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        if self.__help_menu_search:
            self.__help_menu_search_layout = self.__help_menu_search_widget.layout(rc)

        if not self.__clear_layout_cache(rc):
            return rc.height, rc.height

        self.__key_width = 10
        formatter = yuio.md.MdFormatter(
            rc.theme,
            width=min(rc.width, 90) - self.__key_width - 2,
            allow_headings=False,
        )

        self.__wrapped_groups = []
        for title, actions in self.__prepared_groups.items():
            wrapped_actions: _t.List[
                _t.Tuple[_t.List[str], _t.List[_ColorizedString], int]
            ] = []
            for keys, _, msg, key_width in actions:
                wrapped_actions.append((keys, formatter.format(msg), key_width))
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
                rc.write(":")
                rc.reset_color()
                rc.write(" " * (rc.width - 1))
                rc.set_final_pos(1, 0)

    def __help_menu_layout_inline(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
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
            colorized_title = yuio.md.colorize(
                rc.theme, title, default_color=title_color
            )
            self.__colorized_inline_help.append((keys, colorized_title, key_width))

        return 1, 1

    def __help_menu_draw_inline(self, rc: RenderContext, /):
        if not self.__has_help:
            return

        used_width = _line_width(self._KEY_SYMBOLS[Key.F1]) + 5
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
        rc.write(self._KEY_SYMBOLS[Key.F1])
        rc.move_pos(1, 0)
        rc.set_color_path("menu/text/help_msg:help")
        rc.write("help")

    _ALT = "M-"
    _CTRL = "C-"
    _SHIFT = "S-"

    _KEY_SYMBOLS = {
        Key.ENTER: "ret",
        Key.ESCAPE: "esc",
        Key.DELETE: "del",
        Key.BACKSPACE: "bsp",
        Key.TAB: "tab",
        Key.HOME: "home",
        Key.END: "end",
        Key.PAGE_UP: "pgup",
        Key.PAGE_DOWN: "pgdn",
        Key.ARROW_UP: "↑",
        Key.ARROW_DOWN: "↓",
        Key.ARROW_LEFT: "←",
        Key.ARROW_RIGHT: "→",
        Key.F1: "f1",
        Key.F2: "f2",
        Key.F3: "f3",
        Key.F4: "f4",
        " ": "␣",
    }

    def __prepare_inline_help(
        self, data: "WidgetHelp"
    ) -> _t.List[_t.Tuple[_t.List[str], str, str, int]]:
        return [
            prepared_action
            for action in data.inline_help
            if (prepared_action := self.__prepare_action(action)) and prepared_action[1]
        ]

    def __prepare_groups(
        self, data: "WidgetHelp"
    ) -> _t.Dict[str, _t.List[_t.Tuple[_t.List[str], str, str, int]]]:
        help_data = (
            data.with_action(
                self._KEY_SYMBOLS[Key.F1],
                group="Other Actions",
                long_msg="toggle help menu",
            )
            .with_action(
                self._CTRL + "l",
                group="Other Actions",
                long_msg="refresh screen",
            )
            .with_action(
                "C-...",
                group="Terminology",
                long_msg="means `Ctrl+...`",
            )
            .with_action(
                "M-...",
                group="Terminology",
                long_msg="means `Option+...`"
                if sys.platform == "darwin"
                else "means `Alt+...`",
            )
            .with_action(
                "S-...",
                group="Terminology",
                long_msg="means `Shift+...`",
            )
            .with_action(
                "ret",
                group="Terminology",
                long_msg="means `Return` or `Enter`",
            )
            .with_action(
                "bsp",
                group="Terminology",
                long_msg="means `Backspace`",
            )
        )

        # Make sure unsorted actions go first.
        groups = {"Actions": []}

        groups.update(
            {
                title: prepared_actions
                for title, actions in help_data.groups.items()
                if (
                    prepared_actions := [
                        prepared_action
                        for action in actions
                        if (prepared_action := self.__prepare_action(action))
                        and prepared_action[1]
                    ]
                )
            }
        )

        if not groups["Actions"]:
            del groups["Actions"]

        # Make sure other actions go last.
        if "Other Actions" in groups:
            groups["Other Actions"] = groups.pop("Other Actions")
        if "Terminology" in groups:
            groups["Terminology"] = groups.pop("Terminology")

        return groups

    def __prepare_action(
        self, action: "Action"
    ) -> _t.Optional[_t.Tuple[_t.List[str], str, str, int]]:
        if isinstance(action, tuple):
            action_keys, msg = action
            prepared_keys = self.__prepare_keys(action_keys)
        else:
            prepared_keys = []
            msg = action

        if self.__help_menu_search:
            pattern = self.__help_menu_search_widget.text
            if not any(pattern in key for key in prepared_keys) and pattern not in msg:
                return None

        title = msg.split("\n\n", maxsplit=1)[0]
        return prepared_keys, title, msg, _line_width("/".join(prepared_keys))

    def __prepare_keys(self, action_keys: "ActionKeys") -> _t.List[str]:
        if isinstance(action_keys, (str, Key, KeyboardEvent)):
            return [self.__prepare_key(action_keys)]
        else:
            return [self.__prepare_key(action_key) for action_key in action_keys]

    def __prepare_key(self, action_key: "ActionKey") -> str:
        if isinstance(action_key, str):
            return action_key
        elif isinstance(action_key, KeyboardEvent):
            ctrl, alt, key = action_key.ctrl, action_key.alt, action_key.key
        else:
            ctrl, alt, key = False, False, action_key

        symbol = ""

        if key is Key.SHIFT_TAB:
            symbol += self._SHIFT
            key = Key.TAB
        elif isinstance(key, str) and key.lower() != key:
            symbol += self._SHIFT
            key = key.lower()

        if ctrl:
            symbol += self._CTRL

        if alt:
            symbol += self._ALT

        return symbol + (self._KEY_SYMBOLS.get(key) or str(key))


Widget.__init_subclass__()


@dataclass(frozen=True, **yuio._with_slots())
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
    key: _t.Union[Key, str],
    *,
    ctrl: bool = False,
    alt: bool = False,
    show_in_inline_help: bool = False,
    show_in_detailed_help: bool = True,
) -> _Binding:
    """Register an event handler for a widget.

    Widget's methods can be registered as handlers for keyboard events.
    When a new event comes in, it is checked to match arguments of this decorator.
    If there is a match, the decorated method is called
    instead of the :meth:`Widget.default_event_handler`.

    .. note::

       ``Ctrl+L`` and ``F1`` are always reserved by the widget itself.

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

    e = KeyboardEvent(key=key, ctrl=ctrl, alt=alt)
    return _Binding(e, show_in_inline_help, show_in_detailed_help)


@dataclass(frozen=True, **yuio._with_slots())
class _Help:
    group: str = "Actions"
    inline_msg: _t.Optional[str] = None
    long_msg: _t.Optional[str] = None

    def __call__(self, fn: T, /) -> T:
        h = dataclasses.replace(
            self,
            inline_msg=self.inline_msg
            if self.inline_msg is not None
            else getattr(fn, "__doc__", None),
            long_msg=self.long_msg
            if self.long_msg is not None
            else getattr(fn, "__doc__", None),
        )
        setattr(fn, "__yuio_help__", h)

        return fn


def help(
    *,
    group: str = "Actions",
    inline_msg: _t.Optional[str] = None,
    long_msg: _t.Optional[str] = None,
    msg: _t.Optional[str] = None,
) -> _Help:
    """Set options for how this callback should be displayed.

    This decorator controls automatic generation of help messages for a widget.

    :param group:
        title of a group that this action will appear in when the user opens
        a help menu. Groups appear in order of declaration of their first element.
    :param inline_msg:
        this parameter overrides a message in the inline help. By default,
        it will be taken from a docstring.
    :param inline_msg:
        this parameter overrides a message in the help menu. By default,
        it will be taken from a docstring.
    :param long_msg:
        a shortcut parameter for setting both ``inline_msg`` and ``long_msg``
        at the same time.

    Example::

        class MyWidget(Widget):
            NAVIGATE = "Navigate"

            @bind(Key.TAB)
            @help(group=NAVIGATE)
            def tab(self):
                \"\"\"next item\"\"\"
                ...

            @bind(Key.SHIFT_TAB)
            @help(group=NAVIGATE)
            def shift_tab(self):
                \"\"\"previous item\"\"\"
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


#: A single key associated with an action.
#: Can be either a hotkey or a string with an arbitrary description.
ActionKey: _t.TypeAlias = _t.Union[Key, KeyboardEvent, str]

#: A list of keys associated with an action.
ActionKeys: _t.TypeAlias = _t.Union[ActionKey, _t.Collection[ActionKey]]

#: An action itself, i.e. a set of hotkeys and a description for them.
Action: _t.TypeAlias = _t.Union[str, _t.Tuple[ActionKeys, str]]


@dataclass(frozen=True, **yuio._with_slots())
class WidgetHelp:
    """Data for automatic help generation.

    .. warning::

       Do not modify contents of this class in-place. This might break layout
       caching in the widget rendering routine, which will cause displaying
       outdated help messages.

       Use the provided helpers to modify contents of this class.

    """

    #: List of actions to show in the inline help.
    inline_help: _t.List[Action] = dataclasses.field(default_factory=list)

    #: Dict of group titles and actions to show in the help menu.
    groups: _t.Dict[str, _t.List[Action]] = dataclasses.field(default_factory=dict)

    def with_action(
        self,
        *bindings: _t.Union[_Binding, ActionKey],
        group: str = "Actions",
        msg: _t.Optional[str] = None,
        inline_msg: _t.Optional[str] = None,
        long_msg: _t.Optional[str] = None,
        prepend: bool = False,
        prepend_group: bool = False,
    ) -> "WidgetHelp":
        """Return a new :class:`WidgetHelp` that has an extra action."""
        return WidgetHelp(self.inline_help.copy(), self.groups.copy()).__add_action(
            *bindings,
            group=group,
            inline_msg=inline_msg,
            long_msg=long_msg,
            prepend=prepend,
            prepend_group=prepend_group,
            msg=msg,
        )

    def merge(self, other: "WidgetHelp", /) -> "WidgetHelp":
        """Merge this help data with another one
        and return a new instance of :class:`WidgetHelp`.

        """
        result = WidgetHelp(self.inline_help.copy(), self.groups.copy())
        result.inline_help.extend(other.inline_help)
        for title, actions in other.groups.items():
            result.groups[title] = result.groups.get(title, []) + actions
        return result

    def without_group(self, title: str, /) -> "WidgetHelp":
        """Return a new :class:`WidgetHelp` that has
        a group with the given title removed.

        """
        result = WidgetHelp(self.inline_help.copy(), self.groups.copy())
        result.groups.pop(title, None)
        return result

    def rename_group(self, title: str, new_title: str, /) -> "WidgetHelp":
        """Return a new :class:`WidgetHelp` that has
        a group with the given title renamed.

        """
        result = WidgetHelp(self.inline_help.copy(), self.groups.copy())
        if group := result.groups.pop(title, None):
            result.groups[new_title] = result.groups.get(new_title, []) + group
        return result

    def __add_action(
        self,
        *bindings: _t.Union[_Binding, ActionKey],
        group: str,
        inline_msg: _t.Optional[str],
        long_msg: _t.Optional[str],
        prepend: bool,
        prepend_group: bool,
        msg: _t.Optional[str],
    ) -> "WidgetHelp":
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
    """Builder for :class:`VerticalLayout` that allows for precise control
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

    if _t.TYPE_CHECKING:

        def __new__(cls) -> "VerticalLayoutBuilder[_t.Never]":
            ...

    def __init__(self):
        self._widgets: _t.List[Widget[_t.Any]] = []
        self._event_receiver: _t.Optional[int] = None

    @_t.overload
    def add(
        self, widget: Widget[_t.Any], /, *, receive_events: _t.Literal[False] = False
    ) -> "VerticalLayoutBuilder[T]":
        ...

    @_t.overload
    def add(
        self, widget: Widget[U], /, *, receive_events: _t.Literal[True]
    ) -> "VerticalLayoutBuilder[U]":
        ...

    def add(self, widget: Widget[_t.Any], /, *, receive_events=False) -> _t.Any:
        """Add a new widget to the bottom of the layout.

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

    def build(self) -> "VerticalLayout[T]":
        layout = VerticalLayout()
        layout._widgets = self._widgets
        layout._event_receiver = self._event_receiver
        return _t.cast(VerticalLayout[T], layout)


class VerticalLayout(Widget[T], _t.Generic[T]):
    """Helper class for stacking widgets together.

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

    if _t.TYPE_CHECKING:

        def __new__(cls, *widgets: Widget[object]) -> "VerticalLayout[_t.Never]":
            ...

    def __init__(self, *widgets: Widget[object]):
        self._widgets: _t.List[Widget[object]] = list(widgets)
        self._event_receiver: _t.Optional[int] = None

        self.__layouts: _t.List[_t.Tuple[int, int]] = []
        self.__min_h: int = 0
        self.__max_h: int = 0

    def append(self, widget: Widget[_t.Any], /):
        """Add a widget to the end of the stack."""

        if isinstance(widget, VerticalLayout):
            self._widgets.extend(widget._widgets)
        else:
            self._widgets.append(widget)

    def extend(self, widgets: _t.Iterable[Widget[_t.Any]], /):
        """Add multiple widgets to the end of the stack."""

        for widget in widgets:
            self.append(widget)

    def event(self, e: KeyboardEvent) -> _t.Optional[Result[T]]:
        """Dispatch event to the widget that was added with ``receive_events=True``.

        See :class:`~VerticalLayoutBuilder` for details.

        """

        if self._event_receiver is not None:
            return _t.cast(
                _t.Optional[Result[T]], self._widgets[self._event_receiver].event(e)
            )

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        """Calculate layout of the entire stack."""

        self.__layouts = [widget.layout(rc) for widget in self._widgets]
        assert all(l[0] <= l[1] for l in self.__layouts), "incorrect layout"
        self.__min_h = sum(l[0] for l in self.__layouts)
        self.__max_h = sum(l[1] for l in self.__layouts)
        return self.__min_h, self.__max_h

    def draw(self, rc: RenderContext, /):
        """Draw the stack according to the calculated layout and available height."""

        assert len(self._widgets) == len(self.__layouts), (
            "you need to call `VerticalLayout.layout()` "
            "before `VerticalLayout.draw()`"
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


class Line(Widget[_t.Never]):
    """A widget that prints a single line of text."""

    def __init__(
        self,
        text: yuio.term.AnyString,
        /,
        *,
        color: _t.Union[_Color, str, None] = None,
    ):
        self.__text = _ColorizedString(text)
        self.__color = color

    @property
    def text(self) -> yuio.term.ColorizedString:
        """Currently displayed text."""
        return self.__text

    @text.setter
    def text(self, text: yuio.term.AnyString, /):
        self.__text = _ColorizedString(text)

    @property
    def color(self) -> _t.Union[_Color, str, None]:
        """Color of the currently displayed text."""
        return self.__color

    @color.setter
    def color(self, color: _t.Union[_Color, str, None], /):
        self.__color = color

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        return 1, 1

    def draw(self, rc: RenderContext, /):
        if self.__color is not None:
            if isinstance(self.__color, str):
                rc.set_color_path(self.__color)
            else:
                rc.set_color(self.__color)

        rc.write(self.__text)


class Text(Widget[_t.Never]):
    """A widget that prints wrapped text."""

    def __init__(
        self,
        text: yuio.term.AnyString,
        /,
    ):
        self.__text = _ColorizedString(text)
        self.__wrapped_text: _t.Optional[_t.List["yuio.term.ColorizedString"]] = None
        self.__wrapped_text_width: int = 0

    @property
    def text(self) -> yuio.term.ColorizedString:
        """Currently displayed text."""
        return self.__text

    @text.setter
    def text(self, text: yuio.term.AnyString, /):
        self.__text = _ColorizedString(text)
        self.__wrapped_text = None
        self.__wrapped_text_width = 0

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        if self.__wrapped_text is None or self.__wrapped_text_width != rc.width:
            self.__wrapped_text = self.__text.wrap(
                rc.width,
                break_long_nowrap_words=True,
            )
            self.__wrapped_text_width = rc.width
        height = len(self.__wrapped_text)
        return height, height

    def draw(self, rc: RenderContext, /):
        assert self.__wrapped_text is not None
        rc.write_text(self.__wrapped_text)


class Input(Widget[str]):
    """
    An input box.

    .. vhs:: _tapes/widget_input.tape
       :alt: Demonstration of `Input` widget.
       :scale: 40%

    """

    # Characters that count as word separators, used when navigating input text
    # via hotkeys.
    _WORD_SEPARATORS = string.punctuation + string.whitespace

    class _CheckpointType(enum.Enum):
        """Types of entries in the history buffer."""

        #: User-initiated checkpoint.
        USR = enum.auto()

        #: Checkpoint before a symbol was inserted.
        SYM = enum.auto()

        #: Checkpoint before a space was inserted.
        SEP = enum.auto()

        #: Checkpoint before something was deleted.
        DEL = enum.auto()

    def __init__(
        self,
        *,
        text: str = "",
        pos: _t.Optional[int] = None,
        placeholder: str = "",
        decoration: str = ">",
        allow_multiline: bool = False,
    ):
        self.__text: str = text
        self.__pos: int = len(text) if pos is None else max(0, min(pos, len(text)))
        self.__placeholder: str = placeholder
        self.__decoration: str = decoration
        self.__allow_multiline: bool = allow_multiline

        self.__wrapped_text_width: int = 0
        self.__wrapped_text: _t.Optional[_t.List["yuio.term.ColorizedString"]] = None
        self.__pos_after_wrap: _t.Optional[_t.Tuple[int, int]] = None

        # We keep track of edit history by saving input text
        # and cursor position in this list.
        self.__history: _t.List[_t.Tuple[str, int, Input._CheckpointType]] = [
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

    @property
    def text(self) -> str:
        """Current text in the input box."""
        return self.__text

    @text.setter
    def text(self, text: str, /):
        self.__text = text
        self.__wrapped_text = None
        if self.pos > len(text):
            self.pos = len(text)

    @property
    def pos(self) -> int:
        """Current cursor position, measured in code points before the cursor.

        That is, if the text is `"quick brown fox"` with cursor right before the word
        "brown", then :attr:`~Input.pos` is equal to `len("quick ")`.

        """
        return self.__pos

    @pos.setter
    def pos(self, pos: int, /):
        self.__pos = max(0, min(pos, len(self.__text)))
        self.__pos_after_wrap = None

    def checkpoint(self):
        """Manually create an entry in the history buffer."""
        self.__history.append((self.text, self.pos, Input._CheckpointType.USR))
        self.__history_skipped_actions = 0

    def restore_checkpoint(self):
        """Restore the last manually created checkpoint."""
        if self.__history[-1][2] is Input._CheckpointType.USR:
            self.undo()

    def _internal_checkpoint(
        self, action: "Input._CheckpointType", text: str, pos: int
    ):
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
    def enter(self) -> _t.Optional[Result[str]]:
        if self.__allow_multiline:
            self.insert("\n")
        else:
            return self.alt_enter()

    @bind(Key.ENTER, alt=True)
    @bind("d", ctrl=True)
    def alt_enter(self) -> _t.Optional[Result[str]]:
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

    # M-y alternative because C-y sends
    @bind("y", ctrl=True)
    @bind("y", alt=True)
    @help(group=_MODIFY)
    def yank(self):
        """yank (paste the last deleted text)"""
        if self.__yanked_text:
            self.insert(self.__yanked_text)
        else:
            self._bell()

    # the actual shortcut is `C-7`, the rest produce the same code...
    @bind("7", ctrl=True, show_in_detailed_help=False)
    @bind("_", ctrl=True, show_in_detailed_help=False)
    @bind("-", ctrl=True)
    @bind("?", ctrl=True)
    @help(group=_MODIFY)
    def undo(self):
        """undo"""
        self.text, self.pos, _ = self.__history[-1]
        if len(self.__history) > 1:
            self.__history.pop()
        else:
            self._bell()

    def default_event_handler(self, e: KeyboardEvent):
        if isinstance(e.key, str) and not e.alt and not e.ctrl:
            self.insert(e.key)

    def insert(self, s: str):
        self._internal_checkpoint(
            Input._CheckpointType.SEP
            if s in self._WORD_SEPARATORS
            else Input._CheckpointType.SYM,
            self.text,
            self.pos,
        )

        self.text = self.text[: self.pos] + s + self.text[self.pos :]
        self.pos += len(s)

    @property
    def _decoration_width(self):
        if self.__decoration:
            return _line_width(self.__decoration) + 1
        else:
            return 0

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        decoration_width = self._decoration_width
        text_width = rc.width - decoration_width
        if text_width < 2:
            self.__wrapped_text_width = max(text_width, 0)
            self.__wrapped_text = None
            self.__pos_after_wrap = None
            return 0, 0

        if self.__wrapped_text is None or self.__wrapped_text_width != text_width:
            self.__wrapped_text_width = text_width

            if self.__text:
                self.__wrapped_text = _ColorizedString(
                    [rc.theme.get_color("menu/text:input"), self.__text]
                ).wrap(
                    text_width,
                    preserve_spaces=True,
                    break_long_nowrap_words=True,
                )
                self.__pos_after_wrap = None
            else:
                self.__wrapped_text = _ColorizedString(
                    [rc.theme.get_color("menu/placeholder:input"), self.__placeholder]
                ).wrap(
                    text_width,
                    preserve_newlines=False,
                    break_long_nowrap_words=True,
                )
                self.__pos_after_wrap = (decoration_width, 0)

        if self.__pos_after_wrap is None:
            total_len = 0
            for y, line in enumerate(self.__wrapped_text):
                if total_len + len(line) >= self.__pos:
                    x = _line_width(str(line)[: self.__pos - total_len])
                    if x >= text_width:
                        self.__pos_after_wrap = (decoration_width, y + 1)
                    else:
                        self.__pos_after_wrap = (decoration_width + x, y)
                    break
                total_len += len(line) + len(line.explicit_newline)
            else:
                self.__pos_after_wrap = (decoration_width, len(self.__wrapped_text))

        height = max(len(self.__wrapped_text), self.__pos_after_wrap[1])
        return height, height

    def draw(self, rc: RenderContext, /):
        if self.__decoration:
            rc.set_color_path("menu/decoration:input")
            rc.write(self.__decoration)
            rc.move_pos(1, 0)

        if self.__wrapped_text is not None:
            rc.write_text(self.__wrapped_text)

        if self.__pos_after_wrap is not None:
            rc.set_final_pos(*self.__pos_after_wrap)

    @property
    def help_data(self) -> WidgetHelp:
        if self.__allow_multiline:
            return (
                super()
                .help_data.with_action(
                    KeyboardEvent(Key.ENTER, alt=True),
                    KeyboardEvent("d", ctrl=True),
                    msg="accept",
                    prepend=True,
                )
                .with_action(
                    KeyboardEvent(Key.ENTER),
                    group=self._MODIFY,
                    long_msg="new line",
                    prepend=True,
                )
            )
        else:
            return super().help_data


@dataclass(**yuio._with_slots())
class Option(_t.Generic[T_co]):
    """
    An option for the :class:`Grid` and :class:`Choice` widgets.

    """

    #: Option's value that will be returned from widget.
    value: T_co

    #: What should be displayed in the autocomplete list.
    display_text: str

    #: Prefix that will be displayed before :attr:`~Option.display_text`.
    display_text_prefix: str = ""

    #: Suffix that will be displayed after :attr:`~Option.display_text`.
    display_text_suffix: str = ""

    #: Option's short comment.
    comment: _t.Optional[str] = None

    #: Option's color tag.
    #:
    #: This color tag will be used to display option.
    #: Specifically, color for the option will be looked up py path
    #: ``'menu/choice/{status}/{element}/{color_tag}'``.
    color_tag: _t.Optional[str] = None


class Grid(Widget[_t.Never], _t.Generic[T]):
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        decoration: str = ">",
        default_index: _t.Optional[int] = 0,
        min_rows: _t.Optional[int] = 5,
        enable_quick_select: bool = False,
    ):
        self.__options: _t.List[Option[T]]
        self.__index: _t.Optional[int]
        self.__min_rows: _t.Optional[int] = min_rows
        self.__enable_quick_select: bool = enable_quick_select
        self.__column_width: int
        self.__num_rows: int
        self.__num_columns: int

        self.__decoration = decoration

        self.set_options(options)
        self.index = default_index

    @property
    def _page_size(self) -> int:
        return self.__num_rows * self.__num_columns

    @property
    def index(self) -> _t.Optional[int]:
        """Index of the currently selected option."""

        return self.__index

    @index.setter
    def index(self, idx: _t.Optional[int]):
        if idx is None or not self.__options:
            self.__index = None
        elif self.__options:
            self.__index = idx % len(self.__options)

    def get_option(self) -> _t.Optional[Option[T]]:
        """
        Get the currently selected option,
        or `None` if there are no options selected.

        """

        if self.__options and self.__index is not None:
            return self.__options[self.__index]

    def has_options(self) -> bool:
        """Return :data:`True` if the options list is not empty."""

        return bool(self.__options)

    def get_options(self) -> _t.Sequence[Option[T]]:
        """Get all options."""

        return self.__options

    def set_options(
        self,
        options: _t.List[Option[T]],
        /,
        default_index: _t.Optional[int] = 0,
        enable_quick_select: _t.Optional[bool] = None,
    ):
        """Set a new list of options."""

        self.__options = options
        if enable_quick_select is not None:
            self.__enable_quick_select = enable_quick_select
        self.__column_width = max(
            0, _MIN_COLUMN_WIDTH, *map(self._get_option_width, options)
        )
        self.index = default_index

    _NAVIGATE = "Navigate"

    @bind(Key.ARROW_UP)
    @bind("k")
    @bind(Key.SHIFT_TAB)
    @help(group=_NAVIGATE)
    def prev_item(self):
        """previous item"""
        if not self.__options:
            return

        if self.__index is None:
            self.__index = len(self.__options) - 1
        else:
            self.__index = (self.__index - 1) % len(self.__options)

    @bind(Key.ARROW_DOWN)
    @bind("j")
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
    @bind("h")
    @help(group=_NAVIGATE)
    def prev_column(self):
        """previous column"""
        if not self.__options or self.__index is None:
            return

        total_data_size_with_tail = self.__num_rows * math.ceil(
            len(self.__options) / self.__num_rows
        )

        self.__index = (self.__index - self.__num_rows) % total_data_size_with_tail
        if self.__index >= len(self.__options):
            self.__index = len(self.__options) - 1

    @bind(Key.ARROW_RIGHT)
    @bind("l")
    @help(group=_NAVIGATE)
    def next_column(self):
        """next column"""
        if not self.__options or self.__index is None:
            return

        total_data_size_with_tail = self.__num_rows * math.ceil(
            len(self.__options) / self.__num_rows
        )

        self.__index = (self.__index + self.__num_rows) % total_data_size_with_tail
        if self.__index >= len(self.__options):
            self.__index = len(self.__options) - 1

    @bind(Key.PAGE_UP)
    @help(group=_NAVIGATE)
    def prev_page(self):
        """previous page"""
        if not self.__options or self.__index is None:
            return

        self.__index -= self.__index % self._page_size
        self.__index -= 1
        if self.__index < 0:
            self.__index = len(self.__options) - 1

    @bind(Key.PAGE_DOWN)
    @help(group=_NAVIGATE)
    def next_page(self):
        """next page"""
        if not self.__options or self.__index is None:
            return

        self.__index -= self.__index % self._page_size
        self.__index += self._page_size
        if self.__index > len(self.__options):
            self.__index = 0

    @bind(Key.HOME)
    @help(group=_NAVIGATE)
    def home(self):
        """first page"""
        if not self.__options or self.__index is None:
            return

        self.__index = 0

    @bind(Key.END)
    @help(group=_NAVIGATE)
    def end(self):
        """last page"""
        if not self.__options or self.__index is None:
            return

        self.__index = len(self.__options) - 1

    def default_event_handler(self, e: KeyboardEvent):
        if self.__enable_quick_select and e.key in [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
        ]:
            index = int(e.key) - 1
            if index < len(self.__options):
                self.__index = index

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        self.__column_width = max(1, min(self.__column_width, rc.width))
        self.__num_columns = num_columns = max(1, rc.width // self.__column_width)
        self.__num_rows = max(
            1,
            min(self.__min_rows or 1, len(self.__options)),
            math.ceil(len(self.__options) / num_columns),
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

        for i, option in enumerate(page):
            x = i // num_rows
            y = i % num_rows

            rc.set_pos(x * column_width, y)

            index = i + page_start_index
            is_current = index == self.__index
            self._render_option(
                rc, column_width - _SPACE_BETWEEN_COLUMNS, option, is_current, index
            )

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

    def _get_option_width(self, option: Option[object]):
        return (
            _SPACE_BETWEEN_COLUMNS
            + (_line_width(self.__decoration) + 1 if self.__decoration else 0)
            + (3 if self.__enable_quick_select else 0)
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
        index: int,
    ):
        left_prefix_width = _line_width(option.display_text_prefix)
        left_main_width = _line_width(option.display_text)
        left_suffix_width = _line_width(option.display_text_suffix)
        left_width = left_prefix_width + left_main_width + left_suffix_width
        left_decoration_width = (
            _line_width(self.__decoration) + 1 if self.__decoration else 0
        )
        quick_select_width = 3 if (self.__enable_quick_select) else 0

        right = option.comment or ""
        right_width = _line_width(right)
        right_decoration_width = 3 if right else 0

        total_width = (
            left_decoration_width
            + quick_select_width
            + left_width
            + right_decoration_width
            + right_width
        )

        if total_width > width:
            right_width = max(right_width - (total_width - width), 0)
            if right_width == 0:
                right = ""
                right_decoration_width = 0
            total_width = (
                left_decoration_width
                + quick_select_width
                + left_width
                + right_decoration_width
                + right_width
            )

        if total_width > width:
            left_width = max(left_width - (total_width - width), 3)
            total_width = (
                left_decoration_width
                + quick_select_width
                + left_width
                + left_decoration_width
                + left_width
            )

        if total_width > width or total_width == 0:
            return

        if is_active:
            status_tag = "active"
        else:
            status_tag = "normal"

        if self.__enable_quick_select and index < 9:
            rc.set_color_path(
                f"menu/decoration/quick-select:choice/{status_tag}/{option.color_tag}"
            )
            rc.write(f"{index + 1}.")
            rc.set_color_path(f"menu/text:choice/{status_tag}/{option.color_tag}")
            rc.write(" ")
        elif self.__enable_quick_select:
            rc.set_color_path(f"menu/text:choice/{status_tag}/{option.color_tag}")
            rc.write("   ")

        if self.__decoration and is_active:
            rc.set_color_path(f"menu/decoration:choice/{status_tag}/{option.color_tag}")
            rc.write(self.__decoration)
            rc.set_color_path(f"menu/text:choice/{status_tag}/{option.color_tag}")
            rc.write(" ")
        elif self.__decoration:
            rc.set_color_path(f"menu/text:choice/{status_tag}/{option.color_tag}")
            rc.write(" " * left_decoration_width)

        rc.set_color_path(f"menu/text/prefix:choice/{status_tag}/{option.color_tag}")
        rc.write(option.display_text_prefix, max_width=left_width)
        rc.set_color_path(f"menu/text:choice/{status_tag}/{option.color_tag}")
        rc.write(option.display_text, max_width=left_width - left_prefix_width)
        rc.set_color_path(f"menu/text/suffix:choice/{status_tag}/{option.color_tag}")
        rc.write(
            option.display_text_suffix,
            max_width=left_width - left_prefix_width - left_main_width,
        )
        rc.set_color_path(f"menu/text:choice/{status_tag}/{option.color_tag}")
        rc.write(
            " "
            * (
                width
                - left_decoration_width
                - quick_select_width
                - left_width
                - right_decoration_width
                - right_width
            )
        )

        if right:
            rc.set_color_path(
                f"menu/text/comment/decoration:choice/{status_tag}/{option.color_tag}"
            )
            rc.write(" [")
            rc.set_color_path(
                f"menu/text/comment:choice/{status_tag}/{option.color_tag}"
            )
            rc.write(right, max_width=right_width)
            rc.set_color_path(
                f"menu/text/comment/decoration:choice/{status_tag}/{option.color_tag}"
            )
            rc.write("]")

    @property
    def help_data(self) -> "WidgetHelp":
        help_data = super().help_data
        if self.__enable_quick_select:
            return help_data.with_action(
                "1..9",
                long_msg="quick select",
            )
        else:
            return help_data


class Choice(Widget[T], _t.Generic[T]):
    """
    Allows choosing from pre-defined options.

    .. vhs:: _tapes/widget_choice.tape
       :alt: Demonstration of `Choice` widget.
       :scale: 40%

    """

    @_t.overload
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
        default_index: int = 0,
    ):
        ...

    @_t.overload
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        filter: _t.Callable[[Option[T], str], bool],
        default_index: int = 0,
    ):
        ...

    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
        filter: _t.Optional[_t.Callable[[Option[T], str], bool]] = None,
        default_index: int = 0,
    ):
        self.__options = options

        if filter is None:
            filter = lambda x, q: mapper(x).lstrip().startswith(q)

        self.__filter = filter

        self.__default_index = default_index

        self.__input = Input(placeholder="Filter options...", decoration="/")
        self.__grid = Grid[T]([], enable_quick_select=True)

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
    def enter(self) -> _t.Optional[Result[T]]:
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

    def default_event_handler(self, e: KeyboardEvent) -> _t.Optional[Result[T]]:
        if not self.__enable_search and e == KeyboardEvent(" "):
            return self.enter()
        if not self.__enable_search or e.key in (
            Key.ARROW_UP,
            Key.SHIFT_TAB,
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

        self.__grid.set_options(options, enable_quick_select=not query)
        self.__grid.index = index

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
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


class Multiselect(Widget[_t.List[T]], _t.Generic[T]):
    @_t.overload
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
    ):
        ...

    @_t.overload
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        filter: _t.Callable[[Option[T], str], bool],
    ):
        ...

    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text
        or str(x.value),
        filter: _t.Optional[_t.Callable[[Option[T], str], bool]] = None,
    ):
        self.__options = [
            _t.cast(
                Option[_t.Tuple[T, bool]],
                dataclasses.replace(
                    option,
                    value=(option.value, False),
                    display_text_prefix="- " + option.display_text_prefix,
                    color_tag=None,
                ),
            )
            for option in options
        ]

        if filter is None:
            filter = lambda x, q: mapper(x).lstrip().startswith(q)

        self.__filter = filter

        self.__input = Input(placeholder="Filter options...", decoration="/")
        self.__grid = Grid[_t.Tuple[T, bool]]([], enable_quick_select=True)

        self.__enable_search = False

        self.__layout: VerticalLayout[_t.Never]

        self.__update_completion()

    @bind(Key.ENTER)
    @bind(" ")
    def select(self):
        """select"""
        if self.__enable_search and self._cur_event == KeyboardEvent(" "):
            self.__input.event(KeyboardEvent(" "))
        option = self.__grid.get_option()
        if option is not None:
            option.value = (option.value[0], not option.value[1])
            option.display_text_prefix = (
                "*" if option.value[1] else "-"
            ) + option.display_text_prefix[1:]
            option.color_tag = "selected" if option.value[1] else None
        self.__update_completion()

    @bind(Key.ENTER, alt=True)
    @bind("d", ctrl=True, show_in_inline_help=True)
    def enter(self) -> _t.Optional[Result[_t.List[T]]]:
        """accept"""
        return Result(
            [option.value[0] for option in self.__grid.get_options() if option.value[1]]
        )

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

    def default_event_handler(
        self, e: KeyboardEvent
    ) -> _t.Optional[Result[_t.List[T]]]:
        if not self.__enable_search or e.key in (
            Key.ARROW_UP,
            Key.SHIFT_TAB,
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
            if not query or self.__filter(
                _t.cast(Option[T], dataclasses.replace(option, value=option.value[0])),
                query,
            ):
                if option is cur_option:
                    index = len(options)
                options.append(option)

        self.__grid.set_options(options, enable_quick_select=not query)
        self.__grid.index = index

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
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

    .. vhs:: _tapes/widget_completion.tape
       :alt: Demonstration of `InputWithCompletion` widget.
       :scale: 40%

    """

    def __init__(
        self,
        completer: yuio.complete.Completer,
        /,
        *,
        placeholder: str = "",
        decoration: str = ">",
        completion_item_decoration: str = ">",
    ):
        self.__completer = completer

        self.__input = Input(placeholder=placeholder, decoration=decoration)
        self.__grid = Grid[yuio.complete.Completion](
            [], decoration=completion_item_decoration, min_rows=None
        )
        self.__grid_active = False

        self.__layout: VerticalLayout[_t.Never]
        self.__rsuffix: _t.Optional[yuio.complete.Completion] = None

    @bind(Key.ENTER)
    @bind("d", ctrl=True)
    @help(inline_msg="accept")
    def enter(self) -> _t.Optional[Result[str]]:
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
                        c.dprefix,
                        c.dsuffix,
                        c.comment,
                        c.group_color_tag,
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
            Key.SHIFT_TAB,
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
            if not e.ctrl and not e.alt and isinstance(e.key, str):
                # When user prints something...
                if e.key in self.__rsuffix.rsymbols:
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
        self.__input.event(e)
        self._deactivate_completion()

    def _drop_rsuffix(self):
        if self.__rsuffix:
            rsuffix = self.__rsuffix.rsuffix
            if self.__input.text[: self.__input.pos].endswith(rsuffix):
                self._set_input_state_from_completion(self.__rsuffix, set_rsuffix=False)

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
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
            super()
            .help_data.merge(
                self.__grid.help_data.rename_group(
                    Grid._NAVIGATE, "Navigate Completions"
                )
            )
            .merge(
                self.__input.help_data.without_group("Actions")
                .rename_group(Input._NAVIGATE, "Navigate Input")
                .rename_group(Input._MODIFY, "Modify Input")
            )
        )


class Map(Widget[T], _t.Generic[T, U]):
    """A wrapper that maps result of the given widget using the given function.

    ..
        >>> class Input(Widget):
        ...     def event(self, e): return Result("10")
        ...     def layout(self, rc): return 0, 0
        ...     def draw(self, rc): pass
        >>> class Map(Map):
        ...     def run(self, term, theme): return self.event(None).value
        >>> term, theme = None, None

    Example::

        >>> # Run `Input` widget, then parse user input as `int`.
        >>> int_input = Map(Input(), int)
        >>> int_input.run(term, theme)
        10

    """

    def __init__(self, inner: Widget[U], fn: _t.Callable[[U], T], /):
        self.__inner = inner
        self.__fn = fn

    def event(self, e: KeyboardEvent, /) -> _t.Optional[Result[T]]:
        if result := self.__inner.event(e):
            return Result(self.__fn(result.value))

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        return self.__inner.layout(rc)

    def draw(self, rc: RenderContext, /):
        self.__inner.draw(rc)

    @property
    def help_data(self) -> WidgetHelp:
        return self.__inner.help_data


class Apply(Map[T, T], _t.Generic[T]):
    """A wrapper that applies the given function to the result of a wrapped widget.

    ..
        >>> class Input(Widget):
        ...     def event(self, e): return Result("foobar!")
        ...     def layout(self, rc): return 0, 0
        ...     def draw(self, rc): pass
        >>> class Apply(Apply):
        ...     def run(self, term, theme): return self.event(None).value
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


def _event_stream() -> _t.Iterator[KeyboardEvent]:
    while True:
        key = yuio.term._read_keycode()

        # Esc key
        if key == "\x1b":
            yield KeyboardEvent(Key.ESCAPE)
        elif key == "\x1b\x1b":
            yield KeyboardEvent(Key.ESCAPE, alt=True)

        # CSI
        elif key == "\x1b[":
            yield KeyboardEvent("[", alt=True)
        elif key.startswith("\x1b["):
            yield from _parse_csi(key[2:])
        elif key.startswith("\x1b\x1b["):
            yield from _parse_csi(key[3:], alt=True)

        # SS2
        elif key == "\x1bN":
            yield KeyboardEvent("N", alt=True)
        elif key.startswith("\x1bN"):
            yield from _parse_csi(key[2:])
        elif key.startswith("\x1b\x1bN"):
            yield from _parse_csi(key[3:], alt=True)

        # SS3
        elif key == "\x1bO":
            yield KeyboardEvent("O", alt=True)
        elif key.startswith("\x1bO"):
            yield from _parse_csi(key[2:])
        elif key.startswith("\x1b\x1bO"):
            yield from _parse_csi(key[3:], alt=True)

        # DSC
        elif key == "\x1bP":
            yield KeyboardEvent("P", alt=True)
        elif key.startswith("\x1bP"):
            yield from _parse_csi(key[2:])
        elif key.startswith("\x1b\x1bP"):
            yield from _parse_csi(key[3:], alt=True)

        # Alt + Key
        elif key.startswith("\x1b"):
            yield from _parse_char(key[1:], alt=True)

        # Just normal keypress
        else:
            yield from _parse_char(key)


_CSI_CODES = {
    "1": Key.HOME,
    "3": Key.DELETE,
    "4": Key.END,
    "5": Key.PAGE_UP,
    "6": Key.PAGE_DOWN,
    "7": Key.HOME,
    "8": Key.END,
    "A": Key.ARROW_UP,
    "B": Key.ARROW_DOWN,
    "C": Key.ARROW_RIGHT,
    "D": Key.ARROW_LEFT,
    "F": Key.END,
    "H": Key.HOME,
    "Z": Key.SHIFT_TAB,
    "P": Key.F1,
    "Q": Key.F2,
    "R": Key.F3,
    "S": Key.F4,
}


def _parse_csi(
    csi: str, ctrl: bool = False, alt: bool = False
) -> _t.Iterable[KeyboardEvent]:
    if match := re.match(r"^(?P<code>\d+)?(?:;(?P<modifier>\d+))?~$", csi):
        code = match.group("code") or "1"
        modifier = int(match.group("modifier") or "1") - 1
    elif match := re.match(r"^(?:\d+;)?(?P<modifier>\d+)?(?P<code>[A-Z0-9]+)$", csi):
        code = match.group("code") or "1"
        modifier = int(match.group("modifier") or "1") - 1
    else:
        return

    alt |= bool(modifier & 2)
    ctrl |= bool(modifier & 4)

    if (key := _CSI_CODES.get(code)) is not None:
        yield KeyboardEvent(key, ctrl, alt)


def _parse_char(
    char: str, ctrl: bool = False, alt: bool = False
) -> _t.Iterable[KeyboardEvent]:
    if char == "\t":
        yield KeyboardEvent(Key.TAB, ctrl, alt)
    elif char in "\r\n":
        yield KeyboardEvent(Key.ENTER, ctrl, alt)
    elif char == "\x7f":
        yield KeyboardEvent(Key.BACKSPACE, ctrl, alt)
    elif len(char) == 1 and "\x01" <= char <= "\x1A":
        yield KeyboardEvent(chr(ord(char) - 0x1 + ord("a")), True, alt)
    elif len(char) == 1 and "\x0C" <= char <= "\x1F":
        yield KeyboardEvent(chr(ord(char) - 0x1C + ord("4")), True, alt)
    elif (len(char) == 1 and (char in string.printable or ord(char) >= 160)) or len(
        char
    ) > 1:
        yield KeyboardEvent(char, ctrl, alt)
