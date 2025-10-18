import io
import string

import pytest

import yuio.term
import yuio.theme
import yuio.widget
from yuio import _t

from .conftest import RcCompare, WidgetChecker


class TestRenderContext:
    def test_write(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foobar!             ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_wide(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("a👻b")
        rc.write(".")
        rc.new_line()
        rc.write("👻👻")
        rc.write(".")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "a👻b.               ",
                "👻👻.               ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_wide_split_wide_char(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(-1, 0)
        rc.write("👻x👻y")
        rc.write(".")
        rc.set_pos(16, 1)
        rc.write("👻z👻")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                " x👻y.              ",
                "                👻z ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_newlines(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!\nfoo\tbar!")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foobar! foo bar!    ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_newlines_wide(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write("foobar!\n👻\tbar!")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foobar! 👻 bar!     ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_zero_width(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write("x\u0306y\u0306")
        rc.set_pos(-1, 1)
        rc.write("a\u0306b\u0306")
        rc.set_pos(19, 1)
        rc.write("c\u0306d\u0306")
        rc.render()

        assert ostream.getvalue() == (
            "\x1b[J\x1b[mx\u0306y\u0306"  # first write
            "\nb\u0306"  # second write
            "\x1b[20Gc\u0306"  # third write
            "\x1b[1A\x1b[1G"  # setting cursor final position
        )

    def test_write_beyond_borders(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.move_pos(-1, 0)
        rc.write("123456678901234566789012345667890")
        rc.new_line()
        rc.write("123456678901234566789012345667890")
        rc.new_line()
        rc.move_pos(1, 0)
        rc.write("123456678901234566789012345667890")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "23456678901234566789",
                "12345667890123456678",
                " 1234566789012345667",
                "                    ",
                "                    ",
            ]
        )

    def test_write_beyond_borders_wide(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.move_pos(-1, 0)
        rc.write("12345667890👻1234566789012345667890")
        rc.new_line()
        rc.write("12345667890👻1234566789012345667890")
        rc.new_line()
        rc.move_pos(1, 0)
        rc.write("12345667890👻1234566789012345667890")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "2345667890👻12345667",
                "12345667890👻1234566",
                " 12345667890👻123456",
                "                    ",
                "                    ",
            ]
        )

    def test_set_pos(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.set_pos(5, 2)
        rc.write("foobar!")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "                    ",
                "                    ",
                "     foobar!        ",
                "                    ",
                "                    ",
            ]
        )

    def test_move_pos(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foobar!      xyz   1",
                "          quxduo!   ",
                "                 qqq",
                "                    ",
                "                    ",
            ]
        )

    def test_new_line(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foobar!             ",
                "quxduo!             ",
                "                    ",
                "                    ",
                "xxx                 ",
            ]
        )

    def test_set_pos_and_write_out_of_bounds(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "obar!               ",
                "                  45",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_max_width(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.write("foobar!", max_width=3)
        rc.set_pos(-3, 1)
        rc.write("123456", max_width=5)
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo                 ",
                "45                  ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_max_width_wide(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "boo                 ",
                "bo                  ",
                "👻b                 ",
                "bo                  ",
                "👻boo               ",
            ]
        )

    def test_set_color_path(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
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

    def test_set_color(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
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
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write(["a", yuio.term.Color.FORE_RED, "b"])
        rc.new_line()
        rc.write(["c", yuio.term.Color.FORE_GREEN, "d"])
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
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

    def test_fill_no_frame(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        assert rc.width == 20
        assert rc.height == 5

        for x in range(rc.width):
            for y in range(rc.height):
                rc.set_pos(x, y)
                rc.write(".")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "....................",
                "....................",
                "....................",
                "....................",
                "....................",
            ]
        )

    def test_fill_frame(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        with rc.frame(4, 1, width=5, height=2):
            assert rc.width == 5
            assert rc.height == 2
            for x in range(rc.width):
                for y in range(rc.height):
                    rc.set_pos(x, y)
                    rc.write(".")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "                    ",
                "    .....           ",
                "    .....           ",
                "                    ",
                "                    ",
            ]
        )

    def test_frame_write(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "                    ",
                " @  Hi!             ",
                "                    ",
                "                    ",
                "                    ",
            ],
            [
                "                    ",
                " k                  ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

    def test_frame_write_out_of_bounds(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "   @#     12        ",
                "    Hi there!       ",
                "                    ",
                "                    ",
                "    3               ",
            ]
        )

    def test_vertical_cursor_movement(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(0, 4)
        rc.write("11")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "                    ",
                "                    ",
                "                    ",
                "                    ",
                "11                  ",
            ]
        )

        s = ostream.getvalue()
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

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "                    ",
                "                    ",
                "                    ",
                "                    ",
                "22                  ",
            ]
        )

        s = ostream.getvalue()[l:]
        l += len(s)

        # Now we know that the terminal won't scroll,
        # so we can use a CSI code to move down 5 lines at once.
        assert s == "\x1b[4B22\x1b[4A\x1b[1G"

    def test_write_text(self, ostream: io.StringIO, rc: yuio.widget.RenderContext):
        rc.set_pos(1, 1)
        rc.write_text(["Hello,", "world!"])
        rc.write("+")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "                    ",
                " Hello,             ",
                " world!+            ",
                "                    ",
                "                    ",
            ]
        )

    def test_write_text_colors(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.set_pos(1, 1)
        rc.set_color_path("green")
        rc.write_text([["Hello", yuio.term.Color.FORE_RED, ","], "world!"])
        rc.write("+")
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
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
    def test_simple(self, widget_checker: WidgetChecker[yuio.widget.Line]):
        widget_checker.expect_screen(
            [
                "Text                ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Line("Text"))

    def test_long(self, widget_checker: WidgetChecker[yuio.widget.Line]):
        widget_checker.expect_screen(
            [
                "Text 1 2 3 4 5 6 7 8",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Line("Text 1 2 3 4 5 6 7 8 9 0"))

    def test_color_simple(self, widget_checker: WidgetChecker[yuio.widget.Line]):
        widget_checker.expect_screen(
            [
                "Text                ",
                "                    ",
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
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Line("Text", color="red"))

    def test_colorized_string(self, widget_checker: WidgetChecker[yuio.widget.Line]):
        widget_checker.expect_screen(
            [
                "Text blue           ",
                "                    ",
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
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Line(["Text ", yuio.term.Color.FORE_BLUE, "blue"], color="red")
        )


class TestText:
    def test_simple(self, widget_checker: WidgetChecker[yuio.widget.Text]):
        widget_checker.expect_screen(
            [
                "Text                ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Text("Text"))

    def test_multiline(self, widget_checker: WidgetChecker[yuio.widget.Text]):
        widget_checker.expect_screen(
            [
                "Text 1              ",
                "Text 2              ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Text("Text 1\nText 2"))

    def test_long(self, widget_checker: WidgetChecker[yuio.widget.Text]):
        widget_checker.expect_screen(
            [
                "Text 1 2 3 4 5 6 7 8",
                "9 0                 ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Text("Text 1 2 3 4 5 6 7 8 9 0"))

    def test_colorized_string(self, widget_checker: WidgetChecker[yuio.widget.Text]):
        widget_checker.expect_screen(
            [
                "Text blue           ",
                "                    ",
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
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Text(["Text ", yuio.term.Color.FORE_BLUE, "blue"])
        )


class TestInput:
    def test_simple(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input())

    def test_placeholder(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "> type something    ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("foo bar")
        widget_checker.expect_screen(
            [
                "> foo bar           ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input(placeholder="type something"))

    def test_decoration(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "//=                 ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input(decoration="//="))

    def test_no_decoration(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "                    ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("foo bar")
        widget_checker.expect_screen(
            [
                "foo bar             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input(decoration=""))

    def test_single_line(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "> hello             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text(", world")
        widget_checker.expect_screen(
            [
                "> hello, world      ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.paste("\t\n:P")
        widget_checker.expect_screen(
            [
                "> hello, world   :P ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(yuio.widget.Input(text="hello"))
        assert result == "hello, world   :P"

    def test_multiple_lines(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "> hello             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text(",")
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "                    ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("world")
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "  world             ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.paste("\t:D\n:P")
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "  world  :D         ",
                "  :P                ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER, alt=True)

        result = widget_checker.check(
            yuio.widget.Input(text="hello", allow_multiline=True)
        )
        assert result == "hello,\nworld  :D\n:P"

    def test_special_characters(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "> hello             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text(",")
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "                    ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("world")
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "  world             ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.paste("\t\a:D\n:P")
        widget_checker.expect_screen(
            [
                "> hello,            ",
                "  world\\t\\t\\a:D     ",
                "  :P                ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER, alt=True)

        result = widget_checker.check(
            yuio.widget.Input(text="hello", allow_special_characters=True)
        )
        assert result == "hello,\nworld\t\t\a:D\n:P"

    def test_long_word_break(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "> xxxxxxxxxxxxxxxxxx",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input(text="xxxxxxxxxxxxxxxxxx", pos=0))

    def test_long_word_break_cursor_at_the_end(
        self, widget_checker: WidgetChecker[yuio.widget.Input]
    ):
        widget_checker.expect_screen(
            [
                "> xxxxxxxxxxxxxxxxxx",
                "                    ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input(text="xxxxxxxxxxxxxxxxxx", pos=18))

    def test_longer_word_break(self, widget_checker: WidgetChecker[yuio.widget.Input]):
        widget_checker.expect_screen(
            [
                "> xxxxxxxxxxxxxxxxxx",
                "  xx                ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Input(text="xxxxxxxxxxxxxxxxxxxx"))

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
            (
                "xx\ayy",
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
                        (2 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        3,
                        (4 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        4,
                        (5 + 2, 0),
                    ),
                ],
            ),
            (
                "\ayy",
                0,
                (0 + 2, 0),
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        1,
                        (2 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        2,
                        (3 + 2, 0),
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        3,
                        (4 + 2, 0),
                    ),
                ],
            ),
        ],
    )
    def test_move(
        self,
        widget_checker: WidgetChecker[yuio.widget.Input],
        text: str,
        pos: int,
        cursor_pos: tuple[int, int],
        events: list[tuple[yuio.widget.KeyboardEvent, int, tuple[int, int]]],
    ):
        widget = yuio.widget.Input(text=text, pos=pos)

        widget_checker.expect_screen(cursor_x=cursor_pos[0], cursor_y=cursor_pos[1])
        for event, end_pos, (end_x, end_y) in events:
            widget_checker.keyboard_event(event)
            widget_checker.expect_widget_eq(lambda widget: widget.pos, end_pos)
            widget_checker.expect_screen(cursor_x=end_x, cursor_y=end_y)
        widget_checker.expect_widget_to_continue()
        widget_checker.check(widget)

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
        widget_checker: WidgetChecker[yuio.widget.Input],
        undo_method: _t.Literal["undo", "yank"],
        text: str,
        pos: int,
        cursor_pos: tuple[int, int],
        event: yuio.widget.KeyboardEvent,
        end_text: str,
        end_pos: int,
        end_cursor_pos: tuple[int, int],
    ):
        no_yank = undo_method == "yank" and event in [
            yuio.widget.KeyboardEvent("h", ctrl=True),
            yuio.widget.KeyboardEvent(yuio.widget.Key.BACKSPACE),
            yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE),
        ]

        widget = yuio.widget.Input(text=text, pos=pos)

        widget_checker.expect_screen(cursor_x=cursor_pos[0], cursor_y=cursor_pos[1])
        widget_checker.keyboard_event(event)
        widget_checker.expect_widget_eq(lambda widget: widget.text, end_text)
        widget_checker.expect_widget_eq(lambda widget: widget.pos, end_pos)
        widget_checker.expect_screen(
            cursor_x=end_cursor_pos[0], cursor_y=end_cursor_pos[1]
        )
        if undo_method == "undo":
            widget_checker.key("-", ctrl=True)
            widget_checker.expect_widget_eq(lambda widget: widget.text, text)
            widget_checker.expect_widget_eq(lambda widget: widget.pos, pos)
            widget_checker.expect_screen(cursor_x=cursor_pos[0], cursor_y=cursor_pos[1])
        else:
            widget_checker.key("y", ctrl=True)
            if no_yank:
                widget_checker.expect_widget_eq(lambda widget: widget.text, end_text)
            else:
                widget_checker.expect_widget_eq(lambda widget: widget.text, text)
        widget_checker.expect_widget_to_continue()
        widget_checker.check(widget)

    @pytest.mark.parametrize(
        "text,pos,widget_checker",
        [
            # Undo single char
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("X")
                    .expect_widget_eq(lambda widget: widget.text, "fooXbar")
                    .expect_widget_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("XYZ")
                    .expect_widget_eq(lambda widget: widget.text, "fooXYZbar")
                    .expect_widget_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with whitespaces
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("X Y Z")
                    .expect_widget_eq(lambda widget: widget.text, "fooX Y Zbar")
                    .expect_widget_eq(lambda widget: widget.pos, 8)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooX Ybar")
                    .expect_widget_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXbar")
                    .expect_widget_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with multiple whitespaces
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("X  Y Z")
                    .expect_widget_eq(lambda widget: widget.text, "fooX  Y Zbar")
                    .expect_widget_eq(lambda widget: widget.pos, 9)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooX  Ybar")
                    .expect_widget_eq(lambda widget: widget.pos, 7)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooX  bar")
                    .expect_widget_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXbar")
                    .expect_widget_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with position change
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("XY")
                    .key(yuio.widget.Key.ARROW_LEFT)
                    .text("AB")
                    .expect_widget_eq(lambda widget: widget.text, "fooXABYbar")
                    .expect_widget_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXYbar")
                    .expect_widget_eq(lambda widget: widget.pos, 4)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo multiple chars with deletions
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("XY")
                    .key(yuio.widget.Key.DELETE)
                    .text("AB")
                    .key(yuio.widget.Key.BACKSPACE)
                    .expect_widget_eq(lambda widget: widget.text, "fooXYAar")
                    .expect_widget_eq(lambda widget: widget.pos, 6)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXYABar")
                    .expect_widget_eq(lambda widget: widget.pos, 7)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXYar")
                    .expect_widget_eq(lambda widget: widget.pos, 5)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXYbar")
                    .expect_widget_eq(lambda widget: widget.pos, 5)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
            # Undo paste
            (
                "foobar",
                3,
                (
                    WidgetChecker[yuio.widget.Input]()
                    .text("XY")
                    .paste("AB")
                    .expect_widget_eq(lambda widget: widget.text, "fooXYABbar")
                    .expect_widget_eq(lambda widget: widget.pos, 7)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "fooXYbar")
                    .expect_widget_eq(lambda widget: widget.pos, 5)
                    .key("-", ctrl=True)
                    .expect_widget_eq(lambda widget: widget.text, "foobar")
                    .expect_widget_eq(lambda widget: widget.pos, 3)
                    .expect_widget_to_continue()
                ),
            ),
        ],
    )
    def test_undo(
        self,
        ostream: io.StringIO,
        term: yuio.term.Term,
        theme: yuio.theme.Theme,
        text: str,
        pos: int,
        widget_checker: WidgetChecker[yuio.widget.Input],
        width: int,
        height: int,
    ):
        widget = yuio.widget.Input(text=text, pos=pos)
        widget_checker.check(widget, ostream, term, theme, width, height)


class TestGrid:
    def test_empty(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        widget_checker.expect_screen(
            [
                "No options to displa",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_eq(
            yuio.widget.Grid.get_options,
            [],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Grid([]))

    def test_simple(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_eq(
            yuio.widget.Grid.get_options,
            [
                yuio.widget.Option("a", "a"),
                yuio.widget.Option("b", "b"),
                yuio.widget.Option("c", "c"),
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "a"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ]
            )
        )

    def test_row(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        widget_checker.expect_screen(
            [
                "> a         c       ",
                "  b                 ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "a"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ],
                min_rows=0,
            )
        )

    def test_long_option(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        widget_checker.expect_screen(
            [
                "> xxxxxxxxxxxxxxxxxx",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "xxxxxxxxxxxxxxxxxxxx"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ]
            )
        )

    def test_decoration(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        widget_checker.expect_screen(
            [
                "=/ a                ",
                "   b                ",
                "   c                ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "a"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ],
                decoration="=/",
            )
        )

    def test_long_decoration(
        self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]
    ):
        widget_checker.expect_screen(
            [
                "~~~~~~~~~~~~~~~~~~~~",
                "                    ",
                "                    ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "a"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ],
                decoration="~" * 20,
            )
        )

    def test_default_index(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        widget_checker.expect_screen(
            [
                "  a                 ",
                "> b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "a"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ],
                default_index=1,
            )
        )

    def test_default_index_wrap(
        self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]
    ):
        widget_checker.expect_screen(
            [
                "  a                 ",
                "> b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("a", "a"),
                    yuio.widget.Option("b", "b"),
                    yuio.widget.Option("c", "c"),
                ],
                default_index=4,
            )
        )

    def test_screens(self, widget_checker: WidgetChecker[yuio.widget.Grid[str]]):
        def set_index(i: int):
            def inner(w: yuio.widget.Grid[str]):
                print(i)
                w.index = i

            return inner

        widget_checker.expect_screen(
            [
                "> 1         4       ",
                "  2         5       ",
                "  3         6       ",
                "Page 1 of 3         ",
                "f1 help             ",
            ]
        )
        widget_checker.call(set_index(6))
        widget_checker.refresh()
        widget_checker.expect_screen(
            [
                "> 7         10      ",
                "  8         11      ",
                "  9         12      ",
                "Page 2 of 3         ",
                "f1 help             ",
            ]
        )
        widget_checker.call(set_index(9))
        widget_checker.refresh()
        widget_checker.expect_screen(
            [
                "  7       > 10      ",
                "  8         11      ",
                "  9         12      ",
                "Page 2 of 3         ",
                "f1 help             ",
            ]
        )
        widget_checker.call(set_index(12))
        widget_checker.refresh()
        widget_checker.expect_screen(
            [
                "> 13                ",
                "  14                ",
                "                    ",
                "Page 3 of 3         ",
                "f1 help             ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option("1", "1"),
                    yuio.widget.Option("2", "2"),
                    yuio.widget.Option("3", "3"),
                    yuio.widget.Option("4", "4"),
                    yuio.widget.Option("5", "5"),
                    yuio.widget.Option("6", "6"),
                    yuio.widget.Option("7", "7"),
                    yuio.widget.Option("8", "8"),
                    yuio.widget.Option("9", "9"),
                    yuio.widget.Option("10", "10"),
                    yuio.widget.Option("11", "11"),
                    yuio.widget.Option("12", "12"),
                    yuio.widget.Option("13", "13"),
                    yuio.widget.Option("14", "14"),
                ],
            )
        )

    def test_comment(self, widget_checker: WidgetChecker[yuio.widget.Grid[int]]):
        widget_checker.expect_screen(
            [
                "> 0        [comment]",
                "  1 [loooooonggggg1]",
                "  loooooonggggg12345",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Grid(
                [
                    yuio.widget.Option(value=0, display_text="0", comment="comment"),
                    yuio.widget.Option(
                        value=1, display_text="1", comment="loooooonggggg123456789"
                    ),
                    yuio.widget.Option(
                        value=2, display_text="loooooonggggg123456789", comment="hi"
                    ),
                ]
            )
        )

    def test_access_empty(self):
        grid = yuio.widget.Grid([])

        assert not grid.has_options()
        assert grid.index is None
        assert grid.get_option() is None

    def test_access(self):
        a = yuio.widget.Option("a", "a")
        b = yuio.widget.Option("b", "b")
        c = yuio.widget.Option("c", "c")

        grid = yuio.widget.Grid([a, b, c])

        assert grid.has_options()

        assert grid.index == 0
        assert grid.get_option() is a

        grid.next_item()

        assert grid.index == 1
        assert grid.get_option() is b

        grid.index = 2
        assert grid.index == 2
        assert grid.get_option() is c

        grid.index = 3
        assert grid.index == 0
        assert grid.get_option() is a

        grid.set_options([])
        assert not grid.has_options()
        assert grid.index is None
        assert grid.get_option() is None

        grid.set_options([a, b])

        assert grid.has_options()

        assert grid.index == 0
        assert grid.get_option() is a

        grid.index = 3
        assert grid.index == 1
        assert grid.get_option() is b

    @pytest.mark.parametrize(
        "index,events",
        [
            (
                0,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        1,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        2,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        4,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        2,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        1,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                        1,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                        2,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                        4,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.SHIFT_TAB),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.SHIFT_TAB),
                        2,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.SHIFT_TAB),
                        1,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.SHIFT_TAB),
                        0,
                    ),
                ],
            ),
            (
                5,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        6,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        7,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        8,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        7,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        6,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        5,
                    ),
                ],
            ),
            (
                9,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        0,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        1,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        9,
                    ),
                ],
            ),
            (
                0,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        6,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        9,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        0,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        9,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        6,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        0,
                    ),
                ],
            ),
            (
                2,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        5,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        8,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        1,
                    ),
                ],
            ),
            (
                2,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        7,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        4,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        1,
                    ),
                ],
            ),
            (
                0,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                        6,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                        0,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        10,
                    ),
                ],
            ),
            (
                0,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        5,
                    ),
                ],
            ),
            (
                2,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                        6,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                        0,
                    ),
                ],
            ),
            (
                2,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        5,
                    ),
                ],
            ),
            (
                2,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        10,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        5,
                    ),
                ],
            ),
            (
                10,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        5,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        10,
                    ),
                ],
            ),
            (
                5,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        0,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        10,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                        0,
                    ),
                ],
            ),
            (
                None,
                [
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                        0,
                    ),
                ],
            ),
        ],
    )
    def test_move(
        self,
        widget_checker: WidgetChecker[yuio.widget.Grid[int]],
        index: int | None,
        events: list[tuple[yuio.widget.KeyboardEvent, int | None]],
    ):
        widget = yuio.widget.Grid(
            [
                yuio.widget.Option(0, "0"),
                yuio.widget.Option(1, "1"),
                yuio.widget.Option(2, "2"),
                yuio.widget.Option(3, "3"),
                yuio.widget.Option(4, "4"),
                yuio.widget.Option(5, "5"),
                yuio.widget.Option(6, "6"),
                yuio.widget.Option(7, "7"),
                yuio.widget.Option(8, "8"),
                yuio.widget.Option(9, "9"),
                yuio.widget.Option(10, "10"),
            ],
            default_index=index,
        )

        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            index,
        )
        if index is not None:
            widget_checker.expect_widget_eq(
                lambda widget: widget.get_option().value,  # pyright:ignore[reportOptionalMemberAccess]
                index,
            )
        else:
            widget_checker.expect_widget_eq(
                lambda widget: widget.get_option(),
                None,
            )
        for event, index in events:
            widget_checker.keyboard_event(event)
            widget_checker.expect_widget_eq(
                lambda widget: widget.index,
                index,
            )
            if index is not None:
                widget_checker.expect_widget_eq(
                    lambda widget: widget.get_option().value,  # pyright:ignore[reportOptionalMemberAccess]
                    index,
                )
            else:
                widget_checker.expect_widget_eq(
                    lambda widget: widget.get_option(),
                    None,
                )
        widget_checker.expect_widget_to_continue()
        widget_checker.check(widget)

    @pytest.mark.parametrize(
        "index,events",
        [
            (
                0,
                [
                    yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                ],
            ),
            (
                None,
                [
                    yuio.widget.KeyboardEvent(yuio.widget.Key.TAB),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.HOME),
                    yuio.widget.KeyboardEvent(yuio.widget.Key.END),
                ],
            ),
        ],
    )
    def test_move_empty(
        self,
        widget_checker: WidgetChecker[yuio.widget.Grid[int]],
        index: int | None,
        events: list[yuio.widget.KeyboardEvent],
    ):
        widget = yuio.widget.Grid([], default_index=index)

        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            None,
        )
        widget_checker.expect_widget_eq(
            lambda widget: widget.get_option(),
            None,
        )
        for event in events:
            widget_checker.keyboard_event(event)
            widget_checker.expect_widget_eq(
                lambda widget: widget.index,
                None,
            )
            widget_checker.expect_widget_eq(
                lambda widget: widget.get_option(),
                None,
            )
        widget_checker.expect_widget_to_continue()
        widget_checker.check(widget)

    @pytest.mark.parametrize(
        "key,index",
        [
            *((k, i) for i, k in enumerate(string.digits)),
            *((k, i + 10) for i, k in enumerate(string.ascii_lowercase)),
            *((k, i + 10) for i, k in enumerate(string.ascii_uppercase)),
        ],
    )
    def test_quick_select(
        self,
        widget_checker: WidgetChecker[yuio.widget.Grid[None]],
        key: str,
        index: int,
    ):
        widget = yuio.widget.Grid(
            [
                *(yuio.widget.Option(None, k) for k in string.digits),
                *(yuio.widget.Option(None, k) for k in string.ascii_letters),
            ],
            default_index=None,
        )

        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            None,
        )
        widget_checker.key(key)
        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            index,
        )
        widget_checker.expect_widget_to_continue()
        widget_checker.check(widget)

    def test_quick_select_repeat(
        self,
        widget_checker: WidgetChecker[yuio.widget.Grid[None]],
    ):
        widget = yuio.widget.Grid(
            [
                yuio.widget.Option(None, "q"),
                yuio.widget.Option(None, "a"),
                yuio.widget.Option(None, "b"),
                yuio.widget.Option(None, "a"),
            ],
            default_index=None,
        )

        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            None,
        )
        widget_checker.key("a")
        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            1,
        )
        widget_checker.key("a")
        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            3,
        )
        widget_checker.key("a")
        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            1,
        )
        widget_checker.key("q")
        widget_checker.expect_widget_eq(
            lambda widget: widget.index,
            0,
        )
        widget_checker.expect_widget_to_continue()
        widget_checker.check(widget)
