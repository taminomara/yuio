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


Base widget
-----------

All widgets are based on the :class:`Widget` class, where they implement
event handlers, layout and rendering routines. Specifically,
:meth:`Widget.layout` and :meth:`Widget.draw` are required to implement
a widget.

.. autoclass:: Widget
   :members:

.. autofunction:: bind

.. autofunction:: help_column

.. autoclass:: Key
   :members:

.. autoclass:: KeyboardEvent
   :members:


Drawing and rendering widgets
-----------------------------

Rendering widgets is done through :class:`RenderContext`, which provides
simple facilities to print characters on screen and manipulate screen cursor.

An important concept here is `Drawing Frames`. Each widget is rendered in its
drawing frame, which has coordinates and dimensions. Widget's :meth:`~Widget.draw`
method uses zero-based coordinates, which are then translated to the frame's
coordinates.

.. autoclass:: RenderContext
   :members:

Stacking widgets together
-------------------------

To get help with drawing multiple widgets and setting their own frames,
you can use the :class:`VerticalLayout` class:

.. autoclass:: VerticalLayout
   :members:

.. autoclass:: VerticalLayoutBuilder
   :members:


Pre-defined widgets
-------------------

.. autoclass:: Line

.. autoclass:: Text

.. autoclass:: Input

.. autoclass:: Choice

.. autoclass:: InputWithCompletion

.. autoclass:: FilterableChoice

.. autoclass:: Help
   :members:

"""

import abc
import contextlib
import enum
import functools
import itertools
import math
import re
import shutil
import string
import sys

from dataclasses import dataclass
import typing as _t

import yuio.complete
import yuio.term

from yuio.term import (
    _getch, _kbhit, _set_cbreak,
    line_width as _line_width,
    Term as _Term,
    Color as _Color,
    Theme as _Theme,
    ColorizedString as _ColorizedString,
)


_SPACE_BETWEEN_COLUMNS = 2
_MIN_COLUMN_WIDTH = 10


T = _t.TypeVar('T')
U = _t.TypeVar('U')


class Key(enum.Enum):
    """Non-character keys.

    """

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

    def __str__(self) -> str:
        return self.name.replace('_', ' ').title()


@dataclass(frozen=True, slots=True)
class KeyboardEvent:
    """A single keyboard event.

    Note that we don't have separate flag for when `Shift` was pressed with keystroke
    because that renders different :attr:`~KeyboardEvent.key` value.

    """

    #: Which key was pressed? Can be a single character,
    #: or a :class:`Key` for non-character keys.
    key: _t.Union[str, Key]

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
        self._frame_cursor_color: str = ''

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

        # Helpers
        self._none_color: str = _Color.NONE.as_code(term)

        # Used for tests mostly
        self._override_wh: _t.Optional[_t.Tuple[int, int]] = None

        self._renders: int = 0
        self._bytes_rendered: int = 0
        self._total_bytes_rendered: int = 0

    @property
    def term(self) -> _Term:
        """Terminal where we render the widgets.

        """

        return self._term

    @property
    def theme(self) -> _Theme:
        """Current color theme.

        """

        return self._theme

    @contextlib.contextmanager
    def frame(self, x: int, y: int, /, *, width: _t.Optional[int] = None, height: _t.Optional[int] = None):
        """Override drawing frame.

        Widgets are always drawn in the frame's top-left corner,
        and they can take the entire frame size.

        The idea is that, if you want to draw a widget at specific coordinates,
        you make a frame and draw the widget inside said frame.

        When new frame is created, cursor's position and color are reset.
        When frame is dropped, they are restored.
        Therefore, drawing widgets in a frame will not affect current drawing state.

        ..
            >>> term = _Term(sys.stdout)
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
        """Get width of the current frame.

        """

        return self._frame_w

    @property
    def height(self) -> int:
        """Get height of the current frame.

        """

        return self._frame_h

    def set_pos(self, x: int, y: int, /):
        """Set current cursor position within the frame.

        """

        self._frame_cursor_x = x
        self._frame_cursor_y = y

    def move_pos(self, dx: int, dy: int, /):
        """Move current cursor position by the given amount.

        """

        self._frame_cursor_x += dx
        self._frame_cursor_y += dy

    def new_line(self):
        """Move cursor to new line within the current frame.

        """

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
        """Set current color by fetching it from the theme by path.

        """

        self._frame_cursor_color = self._theme.get_color(path).as_code(self._term)

    def set_color(self, color: _Color, /):
        """Set current color.

        """

        self._frame_cursor_color = color.as_code(self._term)

    def reset_color(self):
        """Set current color to the default color of the terminal.

        """

        self._frame_cursor_color = self._none_color

    def write(self, text: "yuio.term.AnyString", /, *, max_width: _t.Optional[int] = None):
        """Write string at the current position using the current color.
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
            >>> term = _Term(sys.stdout)
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

            >>> rc.render()  # doctest: +NORMALIZE_WHITESPACE
            Hello, world!
            Hello, world!
            Hello, 🌍!
            Hello, 🌍!<
            <BLANKLINE>

        Notice that ``'\\n'`` on the second line was replaced with a space.
        Notice also that the last line wasn't properly clipped.

        """

        y = self._frame_y + self._frame_cursor_y
        if not 0 <= y < self._height:
            return

        s_begin = 0

        x = self._frame_x + self._frame_cursor_x
        if x < 0:
            s_begin -= x
            x = 0
        elif x >= self._width:
            return

        s_end = s_begin + self._width - x
        if max_width is not None:
            s_end = min(max_width, s_end)

        if isinstance(text, str) and text.isascii():
            # Fast track
            ll = text[s_begin:s_end]
            ls = len(ll)
            self._lines[y][x:x + ls] = ll
            self._colors[y][x:x + ls] = [self._frame_cursor_color] * ls
            self._frame_cursor_x = x + ls
            return

        if not isinstance(text, _ColorizedString):
            text = _ColorizedString(text)

        ll = []
        cc = []
        color = self._frame_cursor_color
        i = 0

        for s in text.iter_raw():
            if i >= s_end:
                break
            if isinstance(s, _Color):
                color = s.as_code(self._term)
                continue
            for c in s:  # TODO: iterate by graphemes?
                if i >= s_end:
                    break
                if c.isspace():
                    c = " "
                if _line_width(c) > 1:
                    if s_begin <= i and i + 1 < s_end:
                        ll.append(c)
                        ll.append('')
                        cc.append(color)
                        cc.append(color)
                    elif s_begin <= i + 1 or i < s_end:
                        ll.append('')
                        cc.append(color)
                    i += 2
                else:
                    if s_begin <= i < s_end:
                        ll.append(c)
                        cc.append(color)
                    i += 1

        ls = len(ll)
        self._lines[y][x:x + ls] = ll
        self._colors[y][x:x + ls] = cc
        self._frame_cursor_x = x + ls
        self._frame_cursor_color = color

    def write_text(self, lines: _t.Iterable["yuio.term.AnyString"], /, *, max_width: _t.Optional[int] = None):
        """Write multiple lines.

        Each line is printed using :meth:`~RenderContext.write`,
        so newline characters and tabs within each line are replaced with spaces.
        Use :meth:`yuio.term.ColorizedString.wrap` to properly handle them.

        After each line, the cursor is moved done line down,
        and back to its original horizontal position.
        So, if you write lines at

        ..
            >>> term = _Term(sys.stdout)
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

    def prepare(self, *, full_redraw: bool = False):
        """Reset output canvas and prepare context for a new round of widget formatting.

        """

        if self._override_wh:
            width, height = self._override_wh
        else:
            size = shutil.get_terminal_size()
            width = size.columns
            height = size.lines

        full_redraw = full_redraw or self._width != width or self._height != height

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

    def _make_empty_canvas(self) -> _t.Tuple[_t.List[_t.List[str]],  _t.List[_t.List[str]]]:
        lines = [l[:] for l in [[' '] * self._width] * self._height]
        colors = [c[:] for c in [[self._frame_cursor_color] * self._width] * self._height]
        return lines, colors


    def render(self):
        """Render current canvas onto the terminal.

        """

        if not self.term.can_move_cursor:
            self._render_dumb()  # For tests, mostly. Widgets can't work with dumb terminals
            return

        if self._full_redraw:
            self._move_term_cursor(0, 0, [], True)
            self._out.append('\x1b[J')

        had_color_changes_since_last_print = False

        for y in range(self._height):
            line = self._lines[y]

            for x in range(self._width):
                prev_color = self._prev_colors[y][x]
                color = self._colors[y][x]

                if color != prev_color or line[x] != self._prev_lines[y][x]:
                    self._move_term_cursor(x, y, line, had_color_changes_since_last_print)

                    if color != self._term_color:
                        self._out.append(color)
                        self._term_color = color

                    self._out.append(line[x])
                    self._term_x += 1

                    had_color_changes_since_last_print = False
                else:
                    had_color_changes_since_last_print = had_color_changes_since_last_print or (
                        color != self._term_color
                        and (line[x] != ' ' or ';4' in color or ';4' in self._term_color)
                    )

        final_x = max(0, min(self._width - 1, self._final_x))
        final_y = max(0, min(self._height - 1, self._final_y))
        self._move_term_cursor(final_x, final_y, [], True)

        rendered = ''.join(self._out)
        self._term.stream.write(rendered)
        self._term.stream.flush()
        self._out.clear()

        if yuio._debug:
            self._renders += 1
            self._bytes_rendered = len(rendered.encode())
            self._total_bytes_rendered += self._bytes_rendered

            debug_msg = f"dbg:n={self._renders},r={self._bytes_rendered},t={self._total_bytes_rendered}"
            term_x, term_y = self._term_x, self._term_y
            self._move_term_cursor(self._width - len(debug_msg), self._max_term_y, [], True)
            self._out.append(self._none_color)
            self._out.append(debug_msg)
            self._term_x += len(debug_msg)
            self._out.append(self._term_color)
            self._move_term_cursor(term_x, term_y, [], True)

            self._term.stream.write(''.join(self._out))
            self._term.stream.flush()
            self._out.clear()

    def finalize(self):
        """Erase any rendered widget and move cursor to the initial position.

        """

        self.prepare(full_redraw=True)

        self._move_term_cursor(0, 0, [], True)
        self._out.append('\x1b[J')
        self._out.append(self._none_color)
        self._term.stream.write(''.join(self._out))
        self._term.stream.flush()
        self._out.clear()
        self._term_color = self._none_color

    def _move_term_cursor(self, x: int, y: int, line: _t.List[str], had_color_changes_since_last_print: bool):
        dy = y - self._term_y
        if 0 < dy <= 4 or y > self._max_term_y:
            self._out.append('\n' * dy)
            self._term_x = 0
        elif dy > 4:
            self._out.append(f'\x1b[{dy}B')
        elif dy < 0:
            self._out.append(f'\x1b[{-dy}A')
        self._term_y = y
        self._max_term_y = max(self._max_term_y, y)

        dx = x - self._term_x
        if 0 < dx <= 4 and not had_color_changes_since_last_print:
            self._out.extend(line[self._term_x:x])
        elif dx > 0:
            self._out.append(f'\x1b[{dx}C')
        elif dx < 0:
            self._out.append(f'\x1b[{-dx}D')
        self._term_x = x

    def _render_dumb(self):
        prev_printed_color = self._none_color

        for (line, colors) in zip(self._lines, self._colors):
            for (ch, color) in zip(line, colors):
                if prev_printed_color != color:
                    self._out.append(color)
                    prev_printed_color = color
                self._out.append(ch)
            self._out.append('\n')

        self._term.stream.write(''.join(self._out))
        self._term.stream.flush()
        self._out.clear()


class Widget(abc.ABC, _t.Generic[T]):
    """Base class for all interactive console elements.

    Widgets are displayed with their :meth:`~Widget.run` method.
    They always go through the same event loop:

    .. graphviz::

       digraph G {
           node [ width=2; fixedsize=true; ];

           start [ label=""; shape=doublecircle; width=0.3; ];
           layout [ label="Widget.layout()"; shape=rect; ];
           draw [ label="Widget.draw()"; shape=rect; ];
           wait [ label="<wait for keyboard event>"; shape=plain; fixedsize=false; ];
           event [ label="Widget.event()"; shape=rect; ];
           stop [ label=""; shape=diamond; width=0.5; height=0.5 ];
           end [ label=""; shape=doublecircle; width=0.3; ];

           start -> layout;
           layout -> draw;
           draw:w -> layout:w [ weight=0; style=dashed; ];
           draw -> wait [ arrowhead=none ];
           wait -> event;
           event -> stop;
           stop:e -> layout:e [ weight=0; ];
           stop -> end [ taillabel="called   \\nWidget.stop()   " ];
       }

    Widgets run indefinitely until they stop themselves and return a value.
    For example, :class:`Input` will return when user presses `Enter`.
    When widget needs to stop, it calls the :meth:`~Widget.stop` method,
    which, in turn, raises :class:`Widget.StopWidget`. Then :meth:`~Widget.run`
    catches this exception and returns a value.

    For typing purposes of this process, :class:`Widget` is generic.
    That is, ``Widget[T]`` returns `T` from its :meth:`~Widget.run` method.
    So, :class:`Input`, for example, is ``Widget[str]``.

    Some widgets are ``Widget[Never]`` (see :class:`typing.Never`), indicating that
    they don't ever stop. Others are ``Widget[None]``, indicating that they stop,
    but don't return a value.

    """

    class StopWidget(Exception):
        """Raise this class in an event handler
        to stop widget rendering and return a value.

        Use :meth:`~Widget.stop` method to enable better type checking.

        """

        def __init__(self, value: T):
            self.value: T = value

    def event(self, e: KeyboardEvent, /):
        """Handle incoming keyboard event.

        By default, this function dispatches event
        to handlers registered via :func:`bind`.
        If no handler is found, it calls
        :meth:`~Widget.default_event_handler`.

        """

        if handler := self._event_bindings.get(e):
            handler()
        else:
            self.default_event_handler(e)

    def default_event_handler(self, e: KeyboardEvent, /):
        """Process any event that wasn't handled by other event handlers.

        """

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
        the minimum and the maximum height returned from :meth:`~Widget.layout`.

        """

    @_t.final
    def run(self, term: _Term, theme: _Theme, /) -> T:
        """Read user input and run the widget.

        """

        if not term.is_fully_interactive:
            raise RuntimeError('terminal doesn\'t support rendering widgets')

        with _set_cbreak():
            rc = RenderContext(term, theme)

            events = _event_stream()

            while True:
                rc.prepare()

                min_h, max_h = self.layout(rc)
                max_h = max(min_h, min(max_h, rc.height - 1))
                rc.set_final_pos(0, max_h)
                with rc.frame(0, 0, height=max_h):
                    self.draw(rc)

                rc.render()

                try:
                    self.event(next(events))
                except Widget.StopWidget as sw:
                    rc.finalize()
                    return sw.value
                except StopIteration:
                    assert False, "_event_stream supposed to be infinite"
                except (Exception, KeyboardInterrupt):
                    rc.finalize()
                    raise

    def stop(self, value: T) -> _t.NoReturn:
        """Stop rendering a widget and return a value.

        """

        raise Widget.StopWidget(value)

    @functools.cached_property
    def _event_bindings(self) -> _t.Dict[KeyboardEvent, _t.Callable[[], None]]:
        event_bindings_cache = {}
        for cls in reversed(self.__class__.__mro__):
            for name, cb in cls.__dict__.items():
                if hasattr(cb, '__yuio_keybindings__'):
                    cb = getattr(self, name)
                    event_bindings_cache.update(dict.fromkeys(cb.__yuio_keybindings__, cb))
        return event_bindings_cache

    @functools.cached_property
    def help_widget(self) -> "Help":
        """Help widget that you can show in your :meth:`~Widget.render` method
        to display available hotkeys and actions.

        You can control contents of the help message by overriding
        :attr:`~Widget.help_columns`.

        """

        return Help(self.help_columns)

    @functools.cached_property
    def help_columns(self) -> _t.List["Help.Column"]:
        """Columns for :class:`Help` widget.

        By default, columns are generated using docstrings from all
        event handlers that were registered using :func:`bind`.

        You can control this process by decorating your handlers
        with :func:`help_column`.

        You can also override this property to provide custom help data.
        Use :meth:`Help.combine_columns` to add onto the default value::

            class MyWidget(Widget):
                @functools.cached_property
                def help_columns(self) -> list[Help.Column]:
                    # Add an item to the first column.
                    return Help.combine_columns(
                        super().help_columns,
                        [
                            [
                                ([], "start typing to filter values"),
                            ],
                        ],
                    )

        """

        bindings: _t.Dict[_t.Callable[[], None], _t.List[KeyboardEvent]] = {}
        for e, cb in self._event_bindings.items():
            bindings.setdefault(cb, []).append(e)

        defined_columns: _t.List["Help.Column"] = []
        items: _t.List["Help.Action"] = []
        for cb, events in bindings.items():
            column = getattr(cb, '__yuio_column__', None)
            lines = (cb.__doc__ or '').lstrip().splitlines() or ['']
            help = lines[0]
            if not help:
                continue
            item: "Help.Action" = (list(reversed(events)), help)
            if column is None:
                items.append(item)
            else:
                defined_columns += [[] for _ in range((column + 1) - len(defined_columns))]
                defined_columns[column].append(item)

        if defined_columns and items:
            return defined_columns + [items]
        elif defined_columns:
            return defined_columns
        else:
            return [[item] for item in items]


def bind(key: _t.Union[str, Key], ctrl: bool = False, alt: bool = False) -> _t.Callable[[T], T]:
    """Register an event handler for a widget.

    Widget's methods can be registered as handlers for keyboard events.
    When a new event comes in, it is checked to match arguments of this decorator.
    If there is a match, the decorated method is called
    instead of the :meth:`Widget.default_event_handler`.

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

    def decorate(f: T) -> T:
        if not hasattr(f, '__yuio_keybindings__'):
            setattr(f, '__yuio_keybindings__', [])
        getattr(f, '__yuio_keybindings__').append(KeyboardEvent(key=key, ctrl=ctrl, alt=alt))
        return f
    return decorate


def help_column(column: int, /) -> _t.Callable[[_t.Callable[[T], None]], _t.Callable[[T], None]]:
    """Set index of help column for a bound event handler.

    This decorator controls automatic generation of help messages for a widget.
    Specifically, it controls column in which an item will be placed,
    allowing to stack multiple event handlers together.
    All bound event handlers that don't have an explicit column index
    will end up after the elements that do.

    Example::

        class MyWidget(Widget):
            @bind(Key.ENTER)
            @help_column(1)
            def enter(self):
                \"\"\"help message\"\"\"
                ...

    """

    def decorate(f: _t.Callable[[T], None]) -> _t.Callable[[T], None]:
        setattr(f, '__yuio_column__', column)
        return f
    return decorate


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

    def __new__(cls) -> "VerticalLayoutBuilder[_t.Never]":
        return super().__new__(cls)

    def __init__(self):
        self._widgets: _t.List[Widget[_t.Any]] = []
        self._event_receiver: _t.Optional[int] = None

    @_t.overload
    def add(self, widget: Widget[_t.Any], /, *, receive_events: _t.Literal[False] = False) -> "VerticalLayoutBuilder[T]": ...
    @_t.overload
    def add(self, widget: Widget[T], /, *, receive_events: _t.Literal[True]) -> "VerticalLayoutBuilder[T]": ...
    @_t.overload
    def add(self, widget: Widget[U], /, *, receive_events: bool) -> "VerticalLayoutBuilder[_t.Union[T, U]]": ...

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

        if receive_events:
            other._event_receiver = len(other._widgets)

        other._widgets.append(widget)

        return other

    def build(self) -> "VerticalLayout[T]":
        layout = VerticalLayout()
        layout._widgets = self._widgets
        layout._event_receiver = self._event_receiver
        return layout  # type: ignore


class VerticalLayout(Widget[T], _t.Generic[T]):
    """Helper class for stacking widgets together.

    You can stack your widgets together, then calculate their layout
    and draw them all at once.

    You can use this class as a helper component inside your own widgets,
    or you can use it as a standalone widget. See :class:`~VerticalLayoutBuilder`
    for an example.

    """

    def __new__(cls, *widgets: Widget[_t.Any]) -> "VerticalLayout[_t.Never]":
        return super().__new__(cls)

    def __init__(self, *widgets: Widget[_t.Any]):
        self._widgets: _t.List[Widget[_t.Any]] = list(widgets)

        self._layouts: _t.List[_t.Tuple[int, int]] = []
        self._min_h: int = 0
        self._max_h: int = 0

        self._event_receiver: _t.Optional[int] = None

    def append(self, widget: Widget[_t.Any], /):
        """Add a widget to the end of the stack.

        """

        self._widgets.append(widget)

    def extend(self, widgets: _t.Iterable[Widget[_t.Any]], /):
        """Add multiple widgets to the end of the stack.

        """

        self._widgets.extend(widgets)

    def event(self, e: KeyboardEvent):
        """Dispatch event to the widget that was added with ``receive_events=True``.

        See :class:`~VerticalLayoutBuilder` for details.

        """

        if self._event_receiver is not None:
            self._widgets[self._event_receiver].event(e)

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        """Calculate layout of the entire stack.

        """

        self._layouts = [widget.layout(rc) for widget in self._widgets]
        assert all(l[0] <= l[1] for l in self._layouts), "incorrect layout"
        self._min_h = sum(l[0] for l in self._layouts)
        self._max_h = sum(l[1] for l in self._layouts)
        return self._min_h, self._max_h

    def draw(self, rc: RenderContext, /):
        """Draw the stack according to the calculated layout and available height.

        """

        assert len(self._widgets) == len(self._layouts), (
            "you need to call `VerticalLayout.layout()` "
            "before `VerticalLayout.draw()`"
        )

        if rc.height <= self._min_h:
            scale = 0.0
        elif rc.height >= self._max_h:
            scale = 1.0
        else:
            scale = (rc.height - self._min_h) / (self._max_h - self._min_h)

        y1 = 0.0
        for widget, (min_h, max_h) in zip(self._widgets, self._layouts):
            y2 = y1 + min_h + scale * (max_h - min_h)

            iy1 = round(y1)
            iy2 = round(y2)

            with rc.frame(0, iy1, height=iy2 - iy1):
                widget.draw(rc)

            y1 = y2

    @property
    def help_columns(self) -> _t.List["Help.Column"]:
        if self._event_receiver is not None:
            return self._widgets[self._event_receiver].help_columns
        else:
            return []


class Line(Widget[_t.Never]):
    """A widget that prints a single line of text.

    """

    @_t.overload
    def __init__(self, line: "yuio.term.AnyString", /): ...

    @_t.overload
    def __init__(self, line: "yuio.term.AnyString", /, *, color: _Color): ...

    @_t.overload
    def __init__(self, line: "yuio.term.AnyString", /, *, color_path: str): ...

    def __init__(
        self,
        line: "yuio.term.AnyString",
        /,
        *,
        color: _t.Optional[_Color] = None,
        color_path: _t.Optional[str] = None,
    ):
        self._line = line
        self._color = color
        self._color_path = color_path

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        return 1, 1

    def draw(self, rc: RenderContext, /):
        if self._color_path is not None:
            rc.set_color_path(self._color_path)
        elif self._color is not None:
            rc.set_color(self._color)

        rc.write(self._line)


class Text(Widget[_t.Never]):
    """A widget that prints wrapped text.

    """

    def __init__(
        self,
        text: "yuio.term.AnyString",
        /,
        *,
        color: _t.Optional[_Color] = None,
        color_path: _t.Optional[str] = None,
    ):
        self._text: "yuio.term.ColorizedString" = _ColorizedString(text)
        self._color = color
        self._color_path = color_path

        self._wrapped_text: _t.Optional[_t.List["yuio.term.ColorizedString"]] = None
        self._wrapped_text_width: int = 0

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        if self._wrapped_text is None or self._wrapped_text_width != rc.width:
            self._wrapped_text = self._text.wrap(rc.width)
            self._wrapped_text_width = rc.width
        height = len(self._wrapped_text)
        return height, height

    def draw(self, rc: RenderContext, /):
        assert self._wrapped_text is not None
        if self._color_path is not None:
            rc.set_color_path(self._color_path)
        elif self._color is not None:
            rc.set_color(self._color)
        rc.write_text(self._wrapped_text)


class Input(Widget[str]):
    """
    An input box.

    .. vhs:: _tapes/widget_input.tape
       :alt: Demonstration of `Input` widget.
       :scale: 40%

    """

    _WORD_SEPARATORS = string.punctuation + string.whitespace

    def __init__(self, *, text: str = '', placeholder: str = '', decoration: str = ''):
        self._text: str = text
        self._pos: int = len(text)
        self._placeholder: str = placeholder
        self._decoration: str = decoration

        self._wrapped_text_width: int = 0
        self._wrapped_text: _t.Optional[_t.List["yuio.term.ColorizedString"]] = None
        self._pos_after_wrap: _t.Optional[_t.Tuple[int, int]] = None

        self._history: _t.List[_t.Tuple[str, int, str]] = [(self._text, self._pos, "sym")]
        self._history_skipped_actions = 0
        self._require_checkpoint: bool = False

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, text: str, /):
        self._text = text
        self._wrapped_text = None
        if self.pos > len(text):
            self.pos = len(text)

    @property
    def pos(self) -> int:
        return self._pos

    @pos.setter
    def pos(self, pos: int, /):
        self._pos = max(0, min(pos, len(self._text)))
        self._pos_after_wrap = None

    def checkpoint(self):
        self._history.append((self.text, self.pos, "usr"))
        self._history_skipped_actions = 0

    def restore_checkpoint(self):
        if self._history[-1][2] == "usr":
            self.undo()

    def _internal_checkpoint(self, action: str, text: str, pos: int):
        prev_text, prev_pos, prev_action = self._history[-1]

        if action == prev_action and not self._require_checkpoint:
            # If we're repeating the same action, and the cursor didn't move
            self._history_skipped_actions += 1
            return
        else:
            prev_skipped_actions = self._history_skipped_actions
            self._history_skipped_actions = 0
            if action == 'sym' and prev_action == 'sep' and prev_skipped_actions == 0:
                self._history[-1] = prev_text, prev_pos, action
                return

        if self.text == prev_text:
            return

        self._history.append((text, pos, action))
        if len(self._history) > 50:
            self._history.pop(0)

        self._require_checkpoint = False

    @bind(Key.ARROW_UP)
    def up(self, /, *, checkpoint: bool = True):
        pos = self.pos
        self.home()
        if self.pos:
            width = _line_width(self.text[self.pos:pos])

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

        self._require_checkpoint |= checkpoint

    @bind(Key.ARROW_DOWN)
    def down(self, /, *, checkpoint: bool = True):
        pos = self.pos
        self.home()
        width = _line_width(self.text[self.pos:pos])
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
        self._require_checkpoint |= checkpoint

    @bind(Key.ARROW_LEFT)
    @bind('b', ctrl=True)
    def left(self, /, *, checkpoint: bool = True):
        self.pos -= 1
        self._require_checkpoint |= checkpoint

    @bind(Key.ARROW_RIGHT)
    @bind('f', ctrl=True)
    def right(self, /, *, checkpoint: bool = True):
        self.pos += 1
        self._require_checkpoint |= checkpoint

    @bind(Key.ARROW_LEFT, alt=True)
    @bind('b', alt=True)
    def left_word(self, /, *, checkpoint: bool = True):
        self.left()
        pos = self.pos
        text = self.text
        while pos and text[pos] in self._WORD_SEPARATORS and text[pos - 1] != '\n':
            pos -= 1
        while pos and text[pos - 1] not in self._WORD_SEPARATORS:
            pos -= 1
        self.pos = pos
        self._require_checkpoint |= checkpoint

    @bind(Key.ARROW_RIGHT, alt=True)
    @bind('f', alt=True)
    def right_word(self, /, *, checkpoint: bool = True):
        self.right()
        pos = self.pos
        text = self.text
        while pos < len(text) and text[pos] in self._WORD_SEPARATORS and text[pos] != '\n':
            pos += 1
        while pos < len(text) and text[pos] not in self._WORD_SEPARATORS:
            pos += 1
        self.pos = pos
        self._require_checkpoint |= checkpoint

    @bind(Key.HOME)
    @bind('a', ctrl=True)
    def home(self, /, *, checkpoint: bool = True):
        self.pos = self.text.rfind('\n', 0, self.pos) + 1
        self._require_checkpoint |= checkpoint

    @bind(Key.END)
    @bind('e', ctrl=True)
    def end(self, /, *, checkpoint: bool = True):
        next_nl = self.text.find('\n', self.pos)
        if next_nl == -1:
            self.pos = len(self.text)
        else:
            self.pos = next_nl
        self._require_checkpoint |= checkpoint

    @bind(Key.BACKSPACE)
    @bind('h', ctrl=True)
    def backspace(self):
        prev_pos = self.pos
        self.left(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint("del", self.text, prev_pos)
            self.text = self.text[:self.pos] + self.text[prev_pos:]

    @bind(Key.DELETE)
    @bind('d', ctrl=True)
    def delete(self):
        prev_pos = self.pos
        self.right(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint("del", self.text, prev_pos)
            self.text = self.text[:prev_pos] + self.text[self.pos:]
            self.pos = prev_pos

    @bind(Key.BACKSPACE, alt=True)
    @bind('w', ctrl=True)
    def backspace_word(self):
        prev_pos = self.pos
        self.left_word(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint("del", self.text, prev_pos)
            self.text = self.text[:self.pos] + self.text[prev_pos:]

    @bind(Key.DELETE, alt=True)
    @bind('d', alt=True)
    def delete_word(self):
        prev_pos = self.pos
        self.right_word(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint("del", self.text, prev_pos)
            self.text = self.text[:prev_pos] + self.text[self.pos:]
            self.pos = prev_pos

    @bind('u', ctrl=True)
    def backspace_home(self):
        prev_pos = self.pos
        self.home(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint("del", self.text, prev_pos)
            self.text = self.text[:self.pos] + self.text[prev_pos:]

    @bind(Key.BACKSPACE, alt=True)
    @bind('k', ctrl=True)
    def delete_end(self):
        prev_pos = self.pos
        self.end(checkpoint=False)
        if prev_pos != self.pos:
            self._internal_checkpoint("del", self.text, prev_pos)
            self.text = self.text[:prev_pos] + self.text[self.pos:]
            self.pos = prev_pos

    @bind(Key.ENTER)
    def enter(self):
        self.alt_enter()

    @bind(Key.ENTER, alt=True)
    def alt_enter(self):
        self.stop(self.text)

    @bind('7', ctrl=True)  # no idea why, but `^_` and `^7` are the same code...
    @bind('-', ctrl=True)
    @bind('_', ctrl=True)
    def undo(self):
        self.text, self.pos, _ = self._history[-1]
        if len(self._history) > 1:
            self._history.pop()

    def default_event_handler(self, e: KeyboardEvent):
        if isinstance(e.key, str) and not e.alt and not e.ctrl:
            self.insert(e.key)

    def insert(self, s: str):
        self._internal_checkpoint(
            "sep" if s in self._WORD_SEPARATORS else "sym",
            self.text,
            self.pos
        )

        self.text = self.text[:self.pos] + s + self.text[self.pos:]
        self.pos += len(s)

    @property
    def _decoration_width(self):
        if self._decoration:
            return _line_width(self._decoration) + 1
        else:
            return 0

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        decoration_width = self._decoration_width
        text_width = rc.width - decoration_width
        if text_width < 2:
            self._wrapped_text_width = max(text_width, 0)
            self._wrapped_text = None
            self._pos_after_wrap = None
            return 0, 0

        if self._wrapped_text is None or self._wrapped_text_width != text_width:
            self._wrapped_text_width = text_width

            if self._text:
                self._wrapped_text = _ColorizedString([
                    rc.theme.get_color('menu/input/text'), self._text
                ]).wrap(text_width, preserve_spaces=True)
                self._pos_after_wrap = None
            else:
                self._wrapped_text = _ColorizedString([
                    rc.theme.get_color('menu/input/placeholder'), self._placeholder
                ]).wrap(text_width)
                self._pos_after_wrap = (decoration_width, 0)

        if self._pos_after_wrap is None:
            total_len = 0
            for y, line in enumerate(self._wrapped_text):
                if total_len + len(line) >= self._pos:
                    x = _line_width(str(line)[:self._pos - total_len])
                    if x >= text_width:
                        self._pos_after_wrap = (decoration_width, y + 1)
                    else:
                        self._pos_after_wrap = (decoration_width + x, y)
                    break
                total_len += len(line) + len(line.explicit_newline)
            else:
                self._pos_after_wrap = (decoration_width, len(self._wrapped_text))

        height = max(len(self._wrapped_text), self._pos_after_wrap[1])
        return height, height

    def draw(self, rc: RenderContext, /):
        if self._decoration:
            rc.set_color_path('menu/input/decoration')
            rc.write(self._decoration)
            rc.move_pos(1, 0)

        if self._wrapped_text is not None:
            rc.write_text(self._wrapped_text)

        if self._pos_after_wrap is not None:
            rc.set_final_pos(*self._pos_after_wrap)


@dataclass(frozen=True, slots=True)
class Option(_t.Generic[T]):
    """
    An option for the :class:`Choice` widget.

    """

    #: Option's value that will be returned from widget.
    value: T

    #: What should be displayed in the autocomplete list.
    display_text: str

    #: Prefix that will be displayed before :attr:`~Option.display_text`.
    display_text_prefix: str = ''

    #: Suffix that will be displayed after :attr:`~Option.display_text`.
    display_text_suffix: str = ''

    #: Option's short comment.
    comment: _t.Optional[str] = None

    #: Option's color tag.
    #:
    #: This color tag will be used to display option.
    #: Specifically, color for the option will be looked up py path
    #: ``'menu/choice/{status}/{element}/{color_tag}'``.
    color_tag: _t.Optional[str] = None


class Choice(Widget[T]):
    """
    Allows choosing from pre-defined options.

    .. vhs:: _tapes/widget_choice.tape
       :alt: Demonstration of `Choice` widget.
       :scale: 40%

    """

    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        decoration: str = '>',
        default_index: _t.Optional[int] = 0,
    ):
        self._options: _t.List[Option[T]]
        self._current_idx: _t.Optional[int]

        self._column_width: int
        self._num_rows: int
        self._num_columns: int

        self._decoration = decoration

        self.set_options(options)
        self.set_index(default_index)

    @property
    def _page_size(self) -> int:
        return self._num_rows * self._num_columns

    def set_index(self, idx: _t.Optional[int]):
        if idx is None or not self._options:
            self._current_idx = None
        elif self._options:
            self._current_idx = idx % len(self._options) if idx is not None else 0

    def get_index(self) -> _t.Optional[int]:
        return self._current_idx

    def get_option(self) -> _t.Optional[Option[T]]:
        if self._options and self._current_idx is not None:
            return self._options[self._current_idx]

    def has_options(self) -> bool:
        return bool(self._options)

    def set_options(self, options: _t.List[Option[T]], /, default_index: _t.Optional[int] = 0):
        self._options = options
        self._column_width = max(0, _MIN_COLUMN_WIDTH, *map(self._get_option_width, options))
        self.set_index(default_index)

    @bind(Key.ARROW_UP)
    @bind('k')
    @bind(Key.SHIFT_TAB)
    def prev_item(self):
        if not self._options:
            return

        if self._current_idx is None:
            self._current_idx = len(self._options) - 1
        else:
            self._current_idx = (self._current_idx - 1) % len(self._options)

    @bind(Key.ARROW_DOWN)
    @bind('j')
    @bind(Key.TAB)
    def next_item(self):
        if not self._options:
            return

        if self._current_idx is None:
            self._current_idx = 0
        else:
            self._current_idx = (self._current_idx + 1) % len(self._options)

    @bind(Key.ARROW_LEFT)
    @bind('h')
    def prev_column(self):
        if not self._options or self._current_idx is None:
            return

        total_data_size_with_tail = self._num_rows * math.ceil(len(self._options) / self._num_rows)

        self._current_idx = (self._current_idx - self._num_rows) % total_data_size_with_tail
        if self._current_idx >= len(self._options):
            self._current_idx = len(self._options) - 1

    @bind(Key.ARROW_RIGHT)
    @bind('l')
    def next_column(self):
        if not self._options or self._current_idx is None:
            return

        total_data_size_with_tail = self._num_rows * math.ceil(len(self._options) / self._num_rows)

        self._current_idx = (self._current_idx + self._num_rows) % total_data_size_with_tail
        if self._current_idx >= len(self._options):
            self._current_idx = len(self._options) - 1

    @bind(Key.PAGE_DOWN)
    def next_page(self):
        if not self._options or self._current_idx is None:
            return

        self._current_idx -= self._current_idx % self._page_size
        self._current_idx += self._page_size
        if self._current_idx > len(self._options):
            self._current_idx = 0

    @bind(Key.PAGE_UP)
    def prev_page(self):
        if not self._options or self._current_idx is None:
            return

        self._current_idx -= self._current_idx % self._page_size
        self._current_idx -= 1
        if self._current_idx < 0:
            self._current_idx = len(self._options) - 1

    @bind(Key.HOME)
    def home(self):
        if not self._options or self._current_idx is None:
            return

        self._current_idx = 0

    @bind(Key.END)
    def end(self):
        if not self._options or self._current_idx is None:
            return

        self._current_idx = len(self._options) - 1

    @bind(Key.ENTER)
    def enter(self):
        if self._options and self._current_idx is not None:
            self.stop(self._options[self._current_idx].value)

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        self._column_width = max(1, min(self._column_width, rc.width))
        self._num_columns = num_columns = max(1, rc.width // self._column_width)
        self._num_rows = max(1, math.ceil(len(self._options) / num_columns))

        return 1, self._num_rows

    def draw(self, rc: RenderContext, /):
        # Adjust for the actual available height.
        self._num_rows = min(self._num_rows, rc.height)

        column_width = self._column_width
        num_rows = self._num_rows
        page_size = self._page_size

        page_start_index = 0
        if page_size and self._current_idx is not None:
            page_start_index = self._current_idx - self._current_idx % page_size
        page = self._options[page_start_index:page_start_index + page_size]

        for i, option in enumerate(page):
            x = i // num_rows
            y = i % num_rows

            rc.set_pos(x * column_width, y)

            is_current = i + page_start_index == self._current_idx
            self._render_option(rc, column_width - _SPACE_BETWEEN_COLUMNS, option, is_current)

    def _get_option_width(self, option: Option):
        return (
            _SPACE_BETWEEN_COLUMNS
            + (_line_width(self._decoration) + 1 if self._decoration else 0)
            + (_line_width(option.display_text_prefix))
            + (_line_width(option.display_text))
            + (_line_width(option.display_text_suffix))
            + (3 if option.comment else 0)
            + (_line_width(option.comment) if option.comment else 0)
        )

    def _render_option(self, rc: RenderContext, width: int, option: Option, is_active: bool):
        left_prefix_width = _line_width(option.display_text_prefix)
        left_main_width = _line_width(option.display_text)
        left_suffix_width = _line_width(option.display_text_suffix)
        left_width = left_prefix_width + left_main_width + left_suffix_width
        left_decoration_width = _line_width(self._decoration) + 1 if self._decoration else 0

        right = option.comment or ''
        right_width = _line_width(right)
        right_decoration_width = 3 if right else 0

        total_width = left_decoration_width + left_width + right_decoration_width + right_width

        if total_width > width:
            right_width = max(right_width - (total_width - width), 0)
            if right_width == 0:
                right = ''
                right_decoration_width = 0
            total_width = left_decoration_width + left_width + right_decoration_width + right_width

        if total_width > width:
            left_width = max(left_width - (total_width - width), 3)
            total_width = left_decoration_width + left_width + left_decoration_width + left_width

        if total_width > width or total_width == 0:
            return

        if is_active:
            status_tag = 'active'
        else:
            status_tag = 'normal'

        if self._decoration and is_active:
            rc.set_color_path(f'menu/choice/{status_tag}/decoration/{option.color_tag}')
            rc.write(self._decoration)
            rc.set_color_path(f'menu/choice/{status_tag}/plain_text/{option.color_tag}')
            rc.write(' ')
        elif self._decoration:
            rc.set_color_path(f'menu/choice/{status_tag}/plain_text/{option.color_tag}')
            rc.write(' ' * left_decoration_width)

        rc.set_color_path(f'menu/choice/{status_tag}/prefix/{option.color_tag}')
        rc.write(option.display_text_prefix, max_width=left_width)
        rc.set_color_path(f'menu/choice/{status_tag}/text/{option.color_tag}')
        rc.write(option.display_text, max_width=left_width - left_prefix_width)
        rc.set_color_path(f'menu/choice/{status_tag}/suffix/{option.color_tag}')
        rc.write(option.display_text_suffix, max_width=left_width - left_prefix_width - left_main_width)
        rc.set_color_path(f'menu/choice/{status_tag}/plain_text/{option.color_tag}')
        rc.write(' ' * (width - left_decoration_width - left_width - right_decoration_width - right_width))

        if right:
            rc.set_color_path(f'menu/choice/{status_tag}/plain_text/{option.color_tag}')
            rc.write(' [')
            rc.set_color_path(f'menu/choice/{status_tag}/comment/{option.color_tag}')
            rc.write(right, max_width=right_width)
            rc.set_color_path(f'menu/choice/{status_tag}/plain_text/{option.color_tag}')
            rc.write(']')

    @functools.cached_property
    def help_columns(self) -> _t.List["Help.Column"]:
        return [
            [
                (
                    [
                        Key.ARROW_UP,
                        Key.ARROW_DOWN,
                        Key.ARROW_LEFT,
                        Key.ARROW_RIGHT,
                    ],
                    "choose option",
                )
            ],
            [
                (
                    Key.ENTER,
                    "accept",
                )
            ]
        ]


class InputWithCompletion(Widget[str]):
    """
    An input box with tab completion.

    .. vhs:: _tapes/widget_completion.tape
       :alt: Demonstration of `InputWithCompletion` widget.
       :scale: 40%

    """
    def __init__(self, completer: yuio.complete.Completer, /, *, placeholder: str = '', decoration: str = '/', completion_item_decoration: str = '>'):
        self._completer = completer

        self._input = Input(placeholder=placeholder, decoration=decoration)
        self._choice = Choice[yuio.complete.Completion]([], decoration=completion_item_decoration)
        self._choice_active = False

        self._prev_text: str = ''
        self._prev_pos: int = 0

        self._layout: VerticalLayout
        self._rsuffix: _t.Optional[yuio.complete.Completion] = None

    @bind(Key.ENTER)
    def enter(self):
        if self._choice_active and (option := self._choice.get_option()):
            self._set_input_state_from_completion(option.value)
            self._deactivate_completion()
        else:
            self._drop_rsuffix()
            self.stop(self._input.text)

    @bind(Key.ESCAPE)
    def escape(self):
        self._drop_rsuffix()
        if self._choice_active:
            self._input.restore_checkpoint()
            self._deactivate_completion()

    @bind(Key.TAB)
    def tab(self):
        if self._choice_active:
            self._choice.next_item()
            if option := self._choice.get_option():
                self._set_input_state_from_completion(option.value)
            return

        self._input.checkpoint()

        completion = self._completer.complete(self._input.text, self._input.pos)
        if len(completion) == 1:
            self._set_input_state_from_completion(completion[0])
        else:
            self._choice.set_options(
                [
                    Option(c, c.completion, c.dprefix, c.dsuffix, c.comment, c.group_color_tag)
                    for c in completion
                ],
                default_index=None,
            )
            self._activate_completion()

    def default_event_handler(self, e: KeyboardEvent):
        if self._choice_active and e.key in (Key.ARROW_UP, Key.ARROW_DOWN, Key.TAB, Key.SHIFT_TAB, Key.PAGE_UP, Key.PAGE_DOWN):
            self._dispatch_completion_event(e)
        elif self._choice_active and self._choice.get_index() is not None and e.key in (Key.ARROW_RIGHT, Key.ARROW_LEFT):
            self._dispatch_completion_event(e)
        else:
            self._dispatch_input_event(e)

    def _activate_completion(self):
        self._choice_active = True

    def _deactivate_completion(self):
        self._choice_active = False

    def _set_input_state_from_completion(self, completion: yuio.complete.Completion, set_rsuffix: bool = True):
        prefix = completion.iprefix + completion.completion
        if set_rsuffix:
            prefix += completion.rsuffix
            self._rsuffix = completion
        else:
            self._rsuffix = None
        self._input.text = prefix + completion.isuffix
        self._input.pos = len(prefix)

    def _dispatch_completion_event(self, e: KeyboardEvent):
        self._rsuffix = None
        self._choice.event(e)
        if option := self._choice.get_option():
            self._set_input_state_from_completion(option.value)

    def _dispatch_input_event(self, e: KeyboardEvent):
        if self._rsuffix:
            # We need to drop current rsuffix in some cases:
            if not e.ctrl and not e.alt and isinstance(e.key, str):
                # When user prints something...
                if e.key in self._rsuffix.rsymbols:
                    # ...that is in `rsymbols`...
                    self._drop_rsuffix()
            elif e in [
                KeyboardEvent(Key.ARROW_UP),
                KeyboardEvent(Key.ARROW_DOWN),
                KeyboardEvent(Key.ARROW_LEFT),
                KeyboardEvent('b', ctrl=True),
                KeyboardEvent(Key.ARROW_RIGHT),
                KeyboardEvent('f', ctrl=True),
                KeyboardEvent(Key.ARROW_LEFT, alt=True),
                KeyboardEvent('b', alt=True),
                KeyboardEvent(Key.ARROW_RIGHT, alt=True),
                KeyboardEvent('f', alt=True),
                KeyboardEvent(Key.HOME),
                KeyboardEvent('a', ctrl=True),
                KeyboardEvent(Key.END),
                KeyboardEvent('e', ctrl=True),
            ]:
                # ...or when user moves cursor.
                self._drop_rsuffix()
        self._input.event(e)
        self._deactivate_completion()

    def _drop_rsuffix(self):
        if self._rsuffix:
            rsuffix = self._rsuffix.rsuffix
            if self._input.text[:self._input.pos].endswith(rsuffix):
                self._set_input_state_from_completion(self._rsuffix, set_rsuffix=False)

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        self._layout = VerticalLayout()
        self._layout.append(self._input)
        if self._choice_active:
            self._layout.append(self._choice)
        return self._layout.layout(rc)

    def draw(self, rc: RenderContext, /):
        self._layout.draw(rc)


class FilterableChoice(Widget[Option[T]]):
    """Allows choosing from pre-defined options, with search functionality.

    """

    @_t.overload
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text or str(x.value),
        default_index: int = 0,
    ): ...

    @_t.overload
    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        filter: _t.Callable[[Option[T], str], bool],
        default_index: int = 0,
    ): ...

    def __init__(
        self,
        options: _t.List[Option[T]],
        /,
        *,
        mapper: _t.Callable[[Option[T]], str] = lambda x: x.display_text or str(x.value),
        filter: _t.Optional[_t.Callable[[Option[T], str], bool]] = None,
        default_index: int = 0,
    ):
        self._options = options

        if filter is None:
            filter = lambda x, q: mapper(x).lstrip().startswith(q)

        self._filter = filter

        self._default_index = default_index

        self._input = Input(placeholder='Filter options...', decoration='/')
        self._choice = Choice[T]([])
        self._no_options_text = Line('No options to display', color_path='menu/input/decoration')

        self._enable_search = False

        self._layout: VerticalLayout

    @bind(Key.ESCAPE)
    def esc(self):
        """select default"""
        self._input.text = ""
        self._update_completion()
        self._enable_search = False

    @bind('/')
    def search(self):
        """search options"""
        if not self._enable_search:
            self._enable_search = True
        else:
            self._input.event(KeyboardEvent('/'))
            self._update_completion()

    def default_event_handler(self, e: KeyboardEvent):
        if not self._enable_search or e.key in (
            Key.ARROW_UP, Key.SHIFT_TAB, Key.ARROW_DOWN, Key.TAB, Key.ARROW_LEFT,
            Key.ARROW_RIGHT, Key.PAGE_DOWN, Key.PAGE_UP, Key.HOME, Key.END, Key.ENTER
        ):
            self._choice.event(e)
        else:
            self._input.event(e)
            self._update_completion()

    def _update_completion(self):
        query = self._input.text

        index = 0
        options = []
        for i, option in enumerate(self._options):
            if self._filter(option, query):
                if i == self._default_index:
                    index = len(options)
                options.append(option)

        self._choice.set_options(options)
        self._choice.set_index(index)

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        self._layout = VerticalLayout()

        if self._choice.has_options():
            self._layout.append(self._choice)
        else:
            self._layout.append(self._no_options_text)
        if self._enable_search:
            self._layout.append(self._input)
        else:
            self._layout.append(self.help_widget)

        return self._layout.layout(rc)

    def draw(self, rc: RenderContext, /):
        self._layout.draw(rc)


class Help(Widget[_t.Never]):
    """Displays help messages.

    .. vhs:: _tapes/widget_help.tape
       :alt: Demonstration of `Help` widget.
       :scale: 40%

    """

    #: A single key associated with an action.
    #: Can be either a hotkey or a string with an arbitrary description.
    ActionKey: _t.TypeAlias = _t.Union[Key, KeyboardEvent, str]

    #: A list of keys associated with an action.
    ActionKeys: _t.TypeAlias = _t.Union["Help.ActionKey", _t.List["Help.ActionKey"]]

    #: An action itself, i.e. a set of hotkeys and a description for them.
    Action: _t.TypeAlias = _t.Union[str, _t.Tuple["Help.ActionKeys", str]]

    #: A single column of actions.
    Column: _t.TypeAlias = _t.List["Help.Action"]

    _ALT = '⎇'
    _CTRL = '⌃'
    _SHIFT = '⇧'

    _KEY_SYMBOLS = {
        Key.ENTER: '⏎',
        Key.ESCAPE: '⎋',
        Key.DELETE: '⌦',
        Key.BACKSPACE: '⌫',
        Key.TAB: '⇥',
        Key.HOME: '↖︎',
        Key.END: '↘︎',
        Key.PAGE_UP: '⇞',
        Key.PAGE_DOWN: '⇟',
        Key.ARROW_UP: '↑',
        Key.ARROW_DOWN: '↓',
        Key.ARROW_LEFT: '←',
        Key.ARROW_RIGHT: '→',
        ' ': '␣',
    }

    def __init__(self, columns: _t.Collection["Help.Column"], /):
        self._columns = [self._prepare_column(column) for column in columns]
        self._keys_column_width = [self._get_action_keys_width(column) for column in self._columns]
        self._helps_column_width = [self._get_helps_width(column) for column in self._columns]

        self._separate = all(len(column) == 1 for column in self._columns)\

    @classmethod
    def add_help_to(cls, widget: Widget[T]) -> Widget[T]:
        """Wraps the given widget into a vertical layout, adding help message right after.

        """

        return VerticalLayoutBuilder().add(widget, receive_events=True).add(widget.help_widget).build()

    def _prepare_column(self, column: "Help.Column") -> _t.List[_t.Tuple[_t.List[str], str, int]]:
        return [self._prepare_action(action) for action in column]

    def _prepare_action(self, action: "Help.Action") -> _t.Tuple[_t.List[str], str, int]:
        if isinstance(action, tuple):
            action_keys, help = action
            prepared_keys = self._prepare_keys(action_keys)
            prepared_help = str(help)
            return prepared_keys, prepared_help, _line_width('/'.join(prepared_keys))
        else:
            return [], str(action), 0

    def _prepare_keys(self, action_keys: "Help.ActionKeys") -> _t.List[str]:
        if isinstance(action_keys, list):
            return [self._prepare_key(action_key) for action_key in action_keys]
        else:
            return [self._prepare_key(action_keys)]

    def _prepare_key(self, action_key: "Help.ActionKey") -> str:
        if isinstance(action_key, KeyboardEvent):
            ctrl, alt, key = action_key.ctrl, action_key.alt, action_key.key
        else:
            ctrl, alt, key = False, False, action_key

        symbol = ''

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

    def _get_action_keys_width(self, column: _t.List[_t.Tuple[_t.List[str], str, int]]) -> int:
        return max(width for _, _, width in column) if column else 0

    def _get_helps_width(self, column: _t.List[_t.Tuple[_t.List[str], str, int]]) -> int:
        return max(_line_width(help) for _, help, _ in column) if column else 0

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        x = 0
        y = 0
        col_sep_width = 0
        max_col_height = 0

        for column, keys_column_width, helps_column_width in zip(
            self._columns,
            self._keys_column_width,
            self._helps_column_width
        ):
            column_width = keys_column_width + helps_column_width
            if keys_column_width:
                column_width += 1  # space between them
            if x + col_sep_width + column_width > rc.width:
                    # break line
                    y += max_col_height
                    x = 0
                    col_sep_width = 0
                    max_col_height = 0

            x += col_sep_width + column_width

            col_sep_width = 3
            max_col_height = max(max_col_height, len(column))

        y += max_col_height

        return y, y

    def draw(self, rc: RenderContext, /):
        x = 0
        y = 0
        col_sep = ''
        col_sep_width = 0
        max_col_height = 0

        for column, keys_column_width, helps_column_width in zip(
            self._columns,
            self._keys_column_width,
            self._helps_column_width
        ):
            column_width = keys_column_width + helps_column_width
            if keys_column_width:
                column_width += 1  # space between them
            if x + col_sep_width + column_width > rc.width:
                    # break line
                    y += max_col_height
                    x = 0
                    col_sep = ''
                    col_sep_width = 0
                    max_col_height = 0

            rc.set_pos(x, y)

            if col_sep_width:
                rc.set_color_path('menu/help/plain_text')
                rc.write(col_sep)
                x += col_sep_width

            dy = 0
            for keys, help, keys_width in column:
                rc.set_pos(x, y + dy)
                dy += 1

                rc.move_pos(keys_column_width - keys_width, 0)
                sep = ''
                for key in keys:
                    rc.set_color_path('menu/help/text')
                    rc.write(sep)
                    rc.set_color_path('menu/help/key')
                    rc.write(key)
                    sep = '/'

                if keys_column_width:
                    rc.move_pos(1, 0)
                rc.set_color_path('menu/help/text')
                rc.write(help)

            x += column_width

            col_sep = ' • ' if self._separate else '   '
            col_sep_width = 3
            max_col_height = max(max_col_height, len(column))

    @staticmethod
    def combine_columns(*columns: _t.List["Help.Column"]) -> _t.List["Help.Column"]:
        """Given multiple column lists, stack column contents on top of each other.

        Example::

            >>> Help.combine_columns(
            ...     [["a1"], ["b1"]],
            ...     [["a2"], ["b2"], ["c2"]],
            ... )
            [['a1', 'a2'], ['b1', 'b2'], ['c2']]

        """
        return [list(itertools.chain(*column_parts)) for column_parts in itertools.zip_longest(*columns, fillvalue=[])]

    def _draw_action(self, rc: RenderContext, action: _t.Tuple[_t.List[str], str], x: int, y: int, action_keys_width: int):
        keys, help = action

        rc.set_pos(x, y)
        sep = ''
        for key in keys:
            rc.set_color_path('menu/help/text')
            rc.write(sep)
            rc.set_color_path('menu/help/key')
            rc.write(key)
            sep = '/'

        rc.set_pos(x + action_keys_width, y)
        rc.set_color_path('menu/help/text')
        rc.write(help)


def _event_stream() -> _t.Iterator[KeyboardEvent]:
    while True:
        key = _getch()
        while _kbhit():
            key += _getch()
        key = key.decode(sys.__stdin__.encoding, 'replace')

        # Esc key
        if key == '\x1b':
            yield KeyboardEvent(Key.ESCAPE)
        elif key == '\x1b\x1b':
            yield KeyboardEvent(Key.ESCAPE, alt=True)

        # CSI
        elif key == '\x1b[':
            yield KeyboardEvent('[', alt=True)
        elif key.startswith('\x1b['):
            yield from _parse_csi(key[2:])
        elif key.startswith('\x1b\x1b['):
            yield from _parse_csi(key[3:], alt=True)

        # SS2
        elif key == '\x1bN':
            yield KeyboardEvent('N', alt=True)
        elif key.startswith('\x1bN'):
            pass
        elif key.startswith('\x1b\x1bN'):
            pass

        # SS3
        elif key == '\x1bO':
            yield KeyboardEvent('O', alt=True)
        elif key.startswith('\x1bO'):
            pass
        elif key.startswith('\x1b\x1bO'):
            pass

        # DSC
        elif key == '\x1bP':
            yield KeyboardEvent('P', alt=True)
        elif key.startswith('\x1bP'):
            pass
        elif key.startswith('\x1b\x1bP'):
            pass

        # Alt + Key
        elif key.startswith('\x1b'):
            yield from _parse_char(key[1:], alt=True)

        # Just normal keypress
        else:
            yield from _parse_char(key)

_CSI_CODES = {
    '1': Key.HOME,
    '3': Key.DELETE,
    '4': Key.END,
    '5': Key.PAGE_UP,
    '6': Key.PAGE_DOWN,
    '7': Key.HOME,
    '8': Key.END,
    'A': Key.ARROW_UP,
    'B': Key.ARROW_DOWN,
    'C': Key.ARROW_RIGHT,
    'D': Key.ARROW_LEFT,
    'F': Key.END,
    'H': Key.HOME,
    'Z': Key.SHIFT_TAB,
}

def _parse_csi(csi: str, ctrl: bool = False, alt: bool = False) -> _t.Iterable[KeyboardEvent]:
    if match := re.match(r'^(?P<code>\d+)?(?:;(?P<modifier>\d+))?~$', csi):
        code = match.group('code') or '1'
        modifier = int(match.group('modifier') or '1') - 1
    elif match := re.match(r'^(?:\d+;)?(?P<modifier>\d+)?(?P<code>[A-Z])$', csi):
        code = match.group('code') or '1'
        modifier = int(match.group('modifier') or '1') - 1
    else:
        return

    alt |= bool(modifier & 2)
    ctrl |= bool(modifier & 4)

    if (key := _CSI_CODES.get(code)) is not None:
        yield KeyboardEvent(key, ctrl, alt)

def _parse_char(char: str, ctrl: bool = False, alt: bool = False) -> _t.Iterable[KeyboardEvent]:
    if char == '\t':
        yield KeyboardEvent(Key.TAB, ctrl, alt)
    elif char == '\n':
        yield KeyboardEvent(Key.ENTER, ctrl, alt)
    elif char == '\x7f':
        yield KeyboardEvent(Key.BACKSPACE, ctrl, alt)
    elif len(char) == 1 and '\x01' <= char <= '\x1A':
        yield KeyboardEvent(chr(ord(char) - 0x1 + ord('a')), True, alt)
    elif len(char) == 1 and '\x0C' <= char <= '\x1F':
        yield KeyboardEvent(chr(ord(char) - 0x1C + ord('4')), True, alt)
    elif (len(char) == 1 and (char in string.printable or ord(char) >= 160)) or len(char) > 1:
        yield KeyboardEvent(char, ctrl, alt)
