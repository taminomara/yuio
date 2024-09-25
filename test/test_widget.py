import io

import pytest

import yuio.term
import yuio.theme
import yuio.widget
from yuio import _t

from .conftest import KeyboardEventStream, RcCompare


class TestRenderContext:
    def test_write(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar!             ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_wide(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("a👻b")
        rc.write(".")
        rc.new_line()
        rc.write("👻👻")
        rc.write(".")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "a👻b.               ",
                "👻👻.               ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_wide_split_wide_char(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(-1, 0)
        rc.write("👻x👻y")
        rc.write(".")
        rc.set_pos(16, 1)
        rc.write("👻z👻")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                " x👻y.              ",
                "                👻z ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_newlines(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!\nfoo\tbar!")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar! foo bar!    ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_newlines_wide(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write("foobar!\n👻\tbar!")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar! 👻 bar!     ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_zero_width(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write("x\u0306y\u0306")
        rc.set_pos(-1, 1)
        rc.write("a\u0306b\u0306")
        rc.set_pos(19, 1)
        rc.write("c\u0306d\u0306")
        rc.render()

        assert sstream.getvalue() == (
            "\x1b[J\x1b[mx\u0306y\u0306"  # first write
            "\nb\u0306"  # second write
            "\x1b[20Gc\u0306"  # third write
            "\x1b[1A\x1b[1G"  # setting cursor final position
        )

    def test_write_beyond_borders(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.move_pos(-1, 0)
        rc.write("123456678901234566789012345667890")
        rc.new_line()
        rc.write("123456678901234566789012345667890")
        rc.new_line()
        rc.move_pos(1, 0)
        rc.write("123456678901234566789012345667890")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "23456678901234566789",
                "12345667890123456678",
                " 1234566789012345667",
                "                    ",
                "                    ",
            ]
        )

    def test_write_beyond_borders_wide(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.move_pos(-1, 0)
        rc.write("12345667890👻1234566789012345667890")
        rc.new_line()
        rc.write("12345667890👻1234566789012345667890")
        rc.new_line()
        rc.move_pos(1, 0)
        rc.write("12345667890👻1234566789012345667890")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "2345667890👻12345667",
                "12345667890👻1234566",
                " 12345667890👻123456",
                "                    ",
                "                    ",
            ]
        )

    def test_set_pos(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.set_pos(5, 2)
        rc.write("foobar!")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                "                    ",
                "     foobar!        ",
                "                    ",
                "                    ",
            ]
        )

    def test_move_pos(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!")
        rc.move_pos(3, 1)
        rc.write("quxduo!")
        rc.move_pos(-4, -1)
        rc.write("xyz")
        rc.move_pos(3, 0)
        rc.write("123")
        rc.move_pos(-5, 2)
        rc.write("qqq")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar!      xyz   1",
                "          quxduo!   ",
                "                 qqq",
                "                    ",
                "                    ",
            ]
        )

    def test_new_line(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!")
        rc.new_line()
        rc.write("quxduo!")
        rc.new_line()
        rc.new_line()
        rc.new_line()
        rc.write("xxx")
        rc.new_line()
        rc.write("yyy")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar!             ",
                "quxduo!             ",
                "                    ",
                "                    ",
                "xxx                 ",
            ]
        )

    def test_set_pos_and_write_out_of_bounds(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(-2, 0)
        rc.write("foobar!")
        rc.set_pos(0, -2)
        rc.write("123")
        rc.set_pos(18, 1)
        rc.write("456")
        rc.set_pos(0, 6)
        rc.write("789")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "obar!               ",
                "                  45",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_max_width(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!", max_width=3)
        rc.set_pos(-3, 1)
        rc.write("123456", max_width=5)
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foo                 ",
                "45                  ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_max_width_wide(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write("boo👻", max_width=3)
        rc.new_line()
        rc.write("bo👻o", max_width=3)
        rc.new_line()
        rc.write("👻boo", max_width=3)
        rc.set_pos(-2, 3)
        rc.write("👻boo", max_width=4)
        rc.new_line()
        rc.write("👻boo", max_width=10)
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "boo                 ",
                "bo                  ",
                "👻b                 ",
                "bo                  ",
                "👻boo               ",
            ]
        )

    def test_set_color_path(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foo")
        rc.set_color_path("red")
        rc.write("bar")
        rc.set_color_path("green")
        rc.set_pos(0, 1)
        rc.write("baz")
        rc.set_color_path("yellow")
        rc.move_pos(2, 0)
        rc.write("qux")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar              ",
                "baz  qux            ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "   rrr              ",
                "ggg  yyy            ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

    def test_set_color(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foo")
        rc.set_color(yuio.term.Color.FORE_RED)
        rc.write("bar")
        rc.set_color(yuio.term.Color.FORE_GREEN)
        rc.set_pos(0, 1)
        rc.write("baz")
        rc.set_color(yuio.term.Color.FORE_YELLOW)
        rc.move_pos(2, 0)
        rc.write("qux")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "foobar              ",
                "baz  qux            ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "   rrr              ",
                "ggg  yyy            ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

    def test_write_colorized_string(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write(["a", yuio.term.Color.FORE_RED, "b"])
        rc.new_line()
        rc.write(["c", yuio.term.Color.FORE_GREEN, "d"])
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "ab                  ",
                "cd                  ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                " r                  ",
                "rg                  ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

    def test_fill_no_frame(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        assert rc.width == 20
        assert rc.height == 5

        for x in range(rc.width):
            for y in range(rc.height):
                rc.set_pos(x, y)
                rc.write(".")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "....................",
                "....................",
                "....................",
                "....................",
                "....................",
            ]
        )

    def test_fill_frame(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        with rc.frame(4, 1, width=5, height=2):
            assert rc.width == 5
            assert rc.height == 2
            for x in range(rc.width):
                for y in range(rc.height):
                    rc.set_pos(x, y)
                    rc.write(".")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                "    .....           ",
                "    .....           ",
                "                    ",
                "                    ",
            ]
        )

    def test_frame_write(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.set_pos(1, 1)
        rc.set_color(yuio.term.Color.FORE_BLACK)
        with rc.frame(4, 1, width=5, height=2):
            assert rc._frame_cursor_x == 0
            assert rc._frame_cursor_y == 0
            rc.write("Hi")
            rc.write("!")
        assert rc._frame_cursor_x == 1
        assert rc._frame_cursor_y == 1
        rc.write("@")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                " @  Hi!             ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "                    ",
                " B                  ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

    def test_frame_write_out_of_bounds(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        with rc.frame(4, 1, width=5, height=2):
            rc.write("Hi there")
            rc.write("!")
            rc.set_pos(-1, -1)
            rc.write("@")
            rc.write("#")
            rc.move_pos(5, 0)
            rc.write("1")
            rc.write("2")
            rc.set_pos(0, 3)
            rc.write("3")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "   @#     12        ",
                "    Hi there!       ",
                "                    ",
                "                    ",
                "    3               ",
            ]
        )

    def test_vertical_cursor_movement(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(0, 4)
        rc.write("11")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                "                    ",
                "                    ",
                "                    ",
                "11                  ",
            ]
        )

        s = sstream.getvalue()
        l = len(s)

        # We can move the cursor down by using a CSI code or by printing '\n's.
        #
        # Suppose that our terminal is 5 lines high, the cursor was at the 3 line when
        # we started displaying a widget, and we want to move down 3 lines.
        # If we use a CSI code, the cursor will move down 2 lines
        # and hit the terminal border. So, we need to print '\n's instead,
        # so that the terminal could scroll its screen.
        assert s == "\x1b[J\n\n\n\n\x1b[m11\x1b[4A\x1b[1G"

        rc.prepare()
        rc.set_pos(0, 4)
        rc.write("22")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                "                    ",
                "                    ",
                "                    ",
                "22                  ",
            ]
        )

        s = sstream.getvalue()[l:]
        l += len(s)

        # Now we know that the terminal won't scroll,
        # so we can use a CSI code to move down 5 lines at once.
        assert s == "\x1b[4B22\x1b[4A\x1b[1G"

    def test_write_text(self, sstream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.set_pos(1, 1)
        rc.write_text(["Hello,", "world!"])
        rc.write("+")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                " Hello,             ",
                " world!+            ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_text_colors(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(1, 1)
        rc.set_color_path("green")
        rc.write_text([["Hello", yuio.term.Color.FORE_RED, ","], "world!"])
        rc.write("+")
        rc.render()

        assert RcCompare.from_commands(sstream.getvalue()) == RcCompare(
            [
                "                    ",
                " Hello,             ",
                " world!+            ",
                "                    ",
                "                    ",
            ],
            [
                "                    ",
                " gggggr             ",
                " rrrrrrr            ",
                "                    ",
                "                    ",
            ],
        )


class TestLine:
    def test_simple(self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Line]):
        keyboard_event_stream.expect_screen(
            [
                "Text                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Line("Text"))

    def test_long(self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Line]):
        keyboard_event_stream.expect_screen(
            [
                "Text 1 2 3 4 5 6 7 8",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Line("Text 1 2 3 4 5 6 7 8 9 0"))

    def test_color_simple(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Line]
    ):
        keyboard_event_stream.expect_screen(
            [
                "Text                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "rrrr                ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Line("Text", color="red"))

    def test_colorized_string(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Line]
    ):
        keyboard_event_stream.expect_screen(
            [
                "Text blue           ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "rrrrrbbbb           ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(
            yuio.widget.Line(["Text ", yuio.term.Color.FORE_BLUE, "blue"], color="red")
        )


class TestText:
    def test_simple(self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Text]):
        keyboard_event_stream.expect_screen(
            [
                "Text                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Text("Text"))

    def test_multiline(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Text]
    ):
        keyboard_event_stream.expect_screen(
            [
                "Text 1              ",
                "Text 2              ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Text("Text 1\nText 2"))

    def test_long(self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Text]):
        keyboard_event_stream.expect_screen(
            [
                "Text 1 2 3 4 5 6 7 8",
                "9 0                 ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Text("Text 1 2 3 4 5 6 7 8 9 0"))

    def test_colorized_string(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Text]
    ):
        keyboard_event_stream.expect_screen(
            [
                "Text blue           ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "     bbbb           ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(
            yuio.widget.Text(["Text ", yuio.term.Color.FORE_BLUE, "blue"])
        )


class TestInput:
    def test_simple(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Input]
    ):
        keyboard_event_stream.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Input())

    def test_placeholder(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Input]
    ):
        keyboard_event_stream.expect_screen(
            [
                "> type something    ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.text("foo bar")
        keyboard_event_stream.expect_screen(
            [
                "> foo bar           ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Input(placeholder="type something"))

    def test_decoration(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Input]
    ):
        keyboard_event_stream.expect_screen(
            [
                "//=                 ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.expect_widget_to_continue()

        keyboard_event_stream.check(yuio.widget.Input(decoration="//="))

    def test_single_line(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Input]
    ):
        keyboard_event_stream.expect_screen(
            [
                "> hello             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.text(", world")
        keyboard_event_stream.expect_screen(
            [
                "> hello, world      ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.key(yuio.widget.Key.ENTER)

        result = keyboard_event_stream.check(yuio.widget.Input(text="hello"))
        assert result == "hello, world"

    def test_multiple_lines(
        self, keyboard_event_stream: KeyboardEventStream[yuio.widget.Input]
    ):
        keyboard_event_stream.expect_screen(
            [
                "> hello             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.text(",")
        keyboard_event_stream.expect_screen(
            [
                "> hello,            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.key(yuio.widget.Key.ENTER)
        keyboard_event_stream.expect_screen(
            [
                "> hello,            ",
                "                    ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.text("world")
        keyboard_event_stream.expect_screen(
            [
                "> hello,            ",
                "  world             ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        keyboard_event_stream.key(yuio.widget.Key.ENTER, alt=True)

        result = keyboard_event_stream.check(
            yuio.widget.Input(text="hello", allow_multiline=True)
        )
        assert result == "hello,\nworld"

    @pytest.mark.parametrize(
        "text,pos,cursor_pos,events",
        [
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("b", ctrl=True),
                        6,
                        (6 + 2, 0),
                    ),
                ],
            ),
            (
                "f\nx",
                3,
                (1 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        2,
                        (0 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        1,
                        (1 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        0,
                        (0 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("f", ctrl=True),
                        8,
                        (8 + 2, 0),
                    ),
                ],
            ),
            (
                "f\nx",
                0,
                (0 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        1,
                        (1 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        2,
                        (0 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        3,
                        (1 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        3,
                        (1 + 2, 1),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("b", alt=True),
                        4,
                        (4 + 2, 0),
                    ),
                ],
            ),
            (
                "foo   bar baz",
                13,
                (13 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        10,
                        (10 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        6,
                        (6 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        0,
                        (0 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo  \n  bar  \nbaz\n  qux\nduo",
                27,
                (3 + 2, 4),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        24,
                        (0 + 2, 4),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        20,
                        (2 + 2, 3),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        18,
                        (0 + 2, 3),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        14,
                        (0 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        8,
                        (2 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        6,
                        (0 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        0,
                        (0 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar",
                4,
                (4 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar",
                5,
                (5 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        4,
                        (4 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar",
                6,
                (6 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, alt=True),
                        4,
                        (4 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("f", alt=True),
                        11,
                        (11 + 2, 0),
                    ),
                ],
            ),
            (
                "foo   bar baz",
                0,
                (0 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        3,
                        (3 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        9,
                        (9 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        13,
                        (13 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        13,
                        (13 + 2, 0),
                    ),
                ],
            ),
            (
                "foo  \n  bar  \nbaz\n  qux\nduo",
                0,
                (0 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        3,
                        (3 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        5,
                        (5 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        11,
                        (5 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        13,
                        (7 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        17,
                        (3 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        23,
                        (5 + 2, 3),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        27,
                        (3 + 2, 4),
                    ),
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        27,
                        (3 + 2, 4),
                    ),
                ],
            ),
            (
                "foo bar",
                3,
                (3 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        7,
                        (7 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar",
                2,
                (2 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        3,
                        (3 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar",
                1,
                (1 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(
                            yuio.widget.Key.ARROW_RIGHT, alt=True
                        ),
                        3,
                        (3 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("a", ctrl=True),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar\nqux duo\nbrown fox",
                11,
                (3 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        8,
                        (0 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        8,
                        (0 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        7,
                        (7 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        0,
                        (0 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("e", ctrl=True),
                        15,
                        (15 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        15,
                        (15 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar\nqux duo\nbrown fox",
                11,
                (3 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        15,
                        (7 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        15,
                        (7 + 2, 1),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        16,
                        (0 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        25,
                        (9 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        25,
                        (9 + 2, 2),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("p", ctrl=True),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar\nqux duo\nbrown fox",
                11,
                (3 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        3,
                        (3 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                        (0 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "😊 bar\nqux 🙃\nbrown fox",
                9,
                (3 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        2,
                        (3 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                        (0 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                        (0 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent("n", ctrl=True),
                        15,
                        (15 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar qux duo",
                7,
                (7 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        15,
                        (15 + 2, 0),
                    ),
                ],
            ),
            (
                "foo bar\nqux duo\nbrown fox",
                11,
                (3 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        19,
                        (3 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        25,
                        (9 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        25,
                        (9 + 2, 2),
                    ),
                ],
            ),
            (
                "foo bar\nqux 🙃\n😊own fox",
                11,
                (3 + 2, 1),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        16,
                        (3 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        22,
                        (9 + 2, 2),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        22,
                        (9 + 2, 2),
                    ),
                ],
            ),
        ],
    )
    def test_move(
        self,
        keyboard_event_stream: KeyboardEventStream[yuio.widget.Input],
        text: str,
        pos: int,
        cursor_pos: _t.Tuple[int, int],
        events: _t.List[_t.Tuple[yuio.widget.KeyboardEvent, int, _t.Tuple[int, int]]],
    ):
        widget = yuio.widget.Input(text=text, pos=pos)

        keyboard_event_stream.expect_screen(
            cursor_x=cursor_pos[0], cursor_y=cursor_pos[1]
        )
        for event, end_pos, (end_x, end_y) in events:
            keyboard_event_stream.keyboard_event(event)
            keyboard_event_stream.expect_eq(lambda widget: widget.pos, end_pos)
            keyboard_event_stream.expect_screen(cursor_x=end_x, cursor_y=end_y)
        keyboard_event_stream.expect_widget_to_continue()
        keyboard_event_stream.check(widget)

    @pytest.mark.parametrize("undo_method", ["undo", "yank"])
    @pytest.mark.parametrize(
        "text,pos,cursor_pos,event,end_text,end_pos,end_cursor_pos",
        [
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent("h", ctrl=True),
                "fobar",
                2,
                (2 + 2, 0),
            ),
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent(yuio.widget.Key.BACKSPACE),
                "fobar",
                2,
                (2 + 2, 0),
            ),
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE),
                "fooar",
                3,
                (3 + 2, 0),
            ),
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent("w", ctrl=True),
                "bar",
                0,
                (0 + 2, 0),
            ),
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent(yuio.widget.Key.BACKSPACE, alt=True),
                "bar",
                0,
                (0 + 2, 0),
            ),
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent("d", alt=True),
                "foo",
                3,
                (3 + 2, 0),
            ),
            (
                "foobar",
                3,
                (3 + 2, 0),
                yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE, alt=True),
                "foo",
                3,
                (3 + 2, 0),
            ),
            (
                "foo\nbar qux\nduo",
                7,
                (3 + 2, 1),
                yuio.widget.KeyboardEvent("u", ctrl=True),
                "foo\n qux\nduo",
                4,
                (0 + 2, 1),
            ),
            (
                "foo\nbar qux\nduo",
                7,
                (3 + 2, 1),
                yuio.widget.KeyboardEvent("k", ctrl=True),
                "foo\nbar\nduo",
                7,
                (3 + 2, 1),
            ),
        ],
    )
    def test_modify(
        self,
        keyboard_event_stream: KeyboardEventStream[yuio.widget.Input],
        undo_method: _t.Literal["undo", "yank"],
        text: str,
        pos: int,
        cursor_pos: _t.Tuple[int, int],
        event: yuio.widget.KeyboardEvent,
        end_text: str,
        end_pos: int,
        end_cursor_pos: _t.Tuple[int, int],
    ):
        no_yank = undo_method == "yank" and event in [
            yuio.widget.KeyboardEvent("h", ctrl=True),
            yuio.widget.KeyboardEvent(yuio.widget.Key.BACKSPACE),
            yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE),
        ]

        widget = yuio.widget.Input(text=text, pos=pos)

        keyboard_event_stream.expect_screen(
            cursor_x=cursor_pos[0], cursor_y=cursor_pos[1]
        )
        keyboard_event_stream.keyboard_event(event)
        keyboard_event_stream.expect_eq(lambda widget: widget.text, end_text)
        keyboard_event_stream.expect_eq(lambda widget: widget.pos, end_pos)
        keyboard_event_stream.expect_screen(
            cursor_x=end_cursor_pos[0], cursor_y=end_cursor_pos[1]
        )
        if undo_method == "undo":
            keyboard_event_stream.key("-", ctrl=True)
            keyboard_event_stream.expect_eq(lambda widget: widget.text, text)
            keyboard_event_stream.expect_eq(lambda widget: widget.pos, pos)
            keyboard_event_stream.expect_screen(
                cursor_x=cursor_pos[0], cursor_y=cursor_pos[1]
            )
        else:
            keyboard_event_stream.key("y", ctrl=True)
            if no_yank:
                keyboard_event_stream.expect_eq(lambda widget: widget.text, end_text)
            else:
                keyboard_event_stream.expect_eq(lambda widget: widget.text, text)
        keyboard_event_stream.expect_widget_to_continue()
        keyboard_event_stream.check(widget)

    @pytest.mark.parametrize(
        "text,pos,keyboard_event_stream",
        [
            # Undo single char
            (
                "foobar",
                3,
                (
                    KeyboardEventStream[yuio.widget.Input]()
                    .text("X")
                    .expect_eq(lambda widget: widget.text, "fooXbar")
                    .expect_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "foobar")
                    .expect_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars
            (
                "foobar",
                3,
                (
                    KeyboardEventStream[yuio.widget.Input]()
                    .text("XYZ")
                    .expect_eq(lambda widget: widget.text, "fooXYZbar")
                    .expect_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "foobar")
                    .expect_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with whitespaces
            (
                "foobar",
                3,
                (
                    KeyboardEventStream[yuio.widget.Input]()
                    .text("X Y Z")
                    .expect_eq(lambda widget: widget.text, "fooX Y Zbar")
                    .expect_eq(lambda widget: widget.pos, 8)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooX Ybar")
                    .expect_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooXbar")
                    .expect_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "foobar")
                    .expect_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with multiple whitespaces
            (
                "foobar",
                3,
                (
                    KeyboardEventStream[yuio.widget.Input]()
                    .text("X  Y Z")
                    .expect_eq(lambda widget: widget.text, "fooX  Y Zbar")
                    .expect_eq(lambda widget: widget.pos, 9)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooX  Ybar")
                    .expect_eq(lambda widget: widget.pos, 7)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooX  bar")
                    .expect_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooXbar")
                    .expect_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "foobar")
                    .expect_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with position change
            (
                "foobar",
                3,
                (
                    KeyboardEventStream[yuio.widget.Input]()
                    .text("XY")
                    .key(yuio.widget.Key.ARROW_LEFT)
                    .text("AB")
                    .expect_eq(lambda widget: widget.text, "fooXABYbar")
                    .expect_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooXYbar")
                    .expect_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "foobar")
                    .expect_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with deletions
            (
                "foobar",
                3,
                (
                    KeyboardEventStream[yuio.widget.Input]()
                    .text("XY")
                    .key(yuio.widget.Key.DELETE)
                    .text("AB")
                    .key(yuio.widget.Key.BACKSPACE)
                    .expect_eq(lambda widget: widget.text, "fooXYAar")
                    .expect_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooXYABar")
                    .expect_eq(lambda widget: widget.pos, 7)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooXYar")
                    .expect_eq(lambda widget: widget.pos, 5)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "fooXYbar")
                    .expect_eq(lambda widget: widget.pos, 5)
                    .key("-", ctrl=True)
                    .expect_eq(lambda widget: widget.text, "foobar")
                    .expect_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
        ],
    )
    def test_undo(
        self,
        sstream: io.StringIO,
        term: yuio.term.Term,
        theme: yuio.theme.Theme,
        text: str,
        pos: int,
        keyboard_event_stream: KeyboardEventStream[yuio.widget.Input],
    ):
        widget = yuio.widget.Input(text=text, pos=pos)
        keyboard_event_stream.check(widget, sstream, term, theme)
