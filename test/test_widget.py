import io
import string

import pytest

import yuio.color
import yuio.complete
import yuio.string
import yuio.term
import yuio.theme
import yuio.widget

from .conftest import RcCompare, WidgetChecker

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


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
        rc.set_color(yuio.color.Color.FORE_RED)
        rc.write("bar")
        rc.set_color(yuio.color.Color.FORE_GREEN)
        rc.set_pos(0, 1)
        rc.write("baz")
        rc.set_color(yuio.color.Color.FORE_YELLOW)
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
        rc.write(["a", yuio.color.Color.FORE_RED, "b"])
        rc.new_line()
        rc.write(["c", yuio.color.Color.FORE_GREEN, "d"])
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

    def test_write_colorized_string_links(
        self, ostream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write(["a", yuio.string.LinkMarker("A"), "xxx"])
        rc.new_line()
        rc.write(
            ["c", yuio.string.LinkMarker("B"), "d e", yuio.string.LinkMarker(""), "f"]
        )
        rc.render()

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "axxx                ",
                "cd ef               ",
                "                    ",
                "                    ",
                "                    ",
            ],
            None,
            [
                " AAA                ",
                " BBB                ",
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
        rc.set_color(yuio.color.Color.FORE_BLACK)
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
        rc.write_text([["Hello", yuio.color.Color.FORE_RED, ","], "world!"])
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
                "     bbbb           ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        widget_checker.expect_widget_to_continue()

        widget_checker.check(
            yuio.widget.Line(
                yuio.string.ColorizedString(
                    "Text ",
                    yuio.color.Color.FORE_BLUE,
                    "blue",
                )
            )
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
            yuio.widget.Text(
                yuio.string.ColorizedString(
                    "Text ",
                    yuio.color.Color.FORE_BLUE,
                    "blue",
                )
            )
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

    def test_decoration(self, widget_checker: WidgetChecker[yuio.widget.Input], theme):
        theme.set_msg_decoration_unicode("custom_decoration", "//= ")
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

        widget_checker.check(yuio.widget.Input(decoration_path="custom_decoration"))

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

        widget_checker.check(yuio.widget.Input(decoration_path=""))

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
        widget_checker.text(" world")
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
        widget_checker.paste("\t\a:D\n:P")
        widget_checker.expect_screen(
            [
                "> hello, world\\t\\t\\a",
                "  :D :P             ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Input(text="hello", allow_special_characters=True)
        )
        assert result == "hello, world\t\t\a:D :P"

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
        ("text", "pos", "cursor_pos", "events"),
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
        ("text", "pos", "cursor_pos", "event", "end_text", "end_pos", "end_cursor_pos"),
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
        ("text", "pos", "widget_checker"),
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
        widget_checker.check(widget, term, theme, width, height)


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

    def test_decoration(
        self, widget_checker: WidgetChecker[yuio.widget.Grid[str]], theme
    ):
        theme.set_msg_decoration_unicode("custom_decoration", "=/ ")
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
                active_item_decoration_path="custom_decoration",
            )
        )

    def test_long_decoration(
        self, widget_checker: WidgetChecker[yuio.widget.Grid[str]], theme
    ):
        theme.set_msg_decoration_unicode("custom_decoration", "~" * 20)
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
                active_item_decoration_path="custom_decoration",
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
        ("index", "events"),
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
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB, shift=True),
                        3,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB, shift=True),
                        2,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB, shift=True),
                        1,
                    ),
                    (
                        yuio.widget.KeyboardEvent(yuio.widget.Key.TAB, shift=True),
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
        ("index", "events"),
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
        ("key", "index"),
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


class TestChoice:
    def test_empty(self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]):
        widget_checker.expect_screen(
            [
                "No options to displa",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_widget_to_continue()

        widget_checker.check(yuio.widget.Choice([]))

    def test_simple(self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]):
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == 1

    def test_default_index(
        self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]
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
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ],
                default_index=1,
            )
        )

        assert result == 2

    def test_navigate(self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]):
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "  a                 ",
                "> b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == 2

    def test_accept_by_space(
        self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]
    ):
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key(" ")

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == 1

    def test_search(self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]):
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.key("/")
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "/ Filter options... ",
                "f1 help             ",
            ]
        )
        widget_checker.key("a")
        widget_checker.expect_screen(
            [
                "> a                 ",
                "/ a                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key(" ")
        widget_checker.expect_screen(
            [
                "No options to displa",
                "/ a                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key("/")
        widget_checker.expect_screen(
            [
                "No options to displa",
                "/ a /               ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.expect_screen(
            [
                "> a                 ",
                "/ a                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "/ Filter options... ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.text("/a")
        widget_checker.expect_screen(
            [
                "> a                 ",
                "/ a                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ESCAPE)
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "f1 help             ",
                "                    ",
            ]
        )
        widget_checker.text("/a")
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == 1

    def test_navigate_in_search(
        self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]
    ):
        widget_checker.key("/")
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "/ Filter options... ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "  a                 ",
                "> b                 ",
                "  c                 ",
                "/ Filter options... ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ARROW_UP)
        widget_checker.expect_screen(
            [
                "> a                 ",
                "  b                 ",
                "  c                 ",
                "/ Filter options... ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == 1

    def test_filter(self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]):
        widget_checker.text("/1")
        widget_checker.expect_screen(
            [
                "> a                 ",
                "/ 1                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ],
                filter=lambda opt, req: str(opt.value) == req,
            )
        )

        assert result == 1

    def test_mapper(self, widget_checker: WidgetChecker[yuio.widget.Choice[int]]):
        widget_checker.text("/a")
        widget_checker.expect_screen(
            [
                "No options to displa",
                "/ a                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.key("A")
        widget_checker.expect_screen(
            [
                "> a                 ",
                "/ A                 ",
                "f1 help             ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(
            yuio.widget.Choice(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ],
                mapper=lambda opt: opt.display_text.upper(),
            )
        )

        assert result == 1


class TestMultiselect:
    def test_empty(self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]):
        widget_checker.expect_screen(
            [
                "No options to displa",
                "C-d accept • f1 help",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(yuio.widget.Multiselect([]))
        assert result == []

    def test_simple(self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]):
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> ◉ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == [1]

    def test_decorations(
        self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]], theme
    ):
        theme.set_msg_decoration_unicode("menu/choice/decoration/active_item", ">> ")
        theme.set_msg_decoration_unicode("menu/choice/decoration/selected_item", "@@ ")
        theme.set_msg_decoration_unicode("menu/choice/decoration/deselected_item", "-")
        widget_checker.expect_screen(
            [
                ">> -  a             ",
                "   -  b             ",
                "   @@ c             ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c", selected=True),
                ]
            )
        )

        assert result == [3]

    def test_select_many(
        self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]
    ):
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key("c")
        widget_checker.expect_screen(
            [
                "  ◉ a               ",
                "  ○ b               ",
                "> ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == [1, 3]

    def test_navigate(
        self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]
    ):
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "  ◉ a               ",
                "> ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == [1, 2]

    def test_select_by_space(
        self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]
    ):
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key(" ")
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == [1]

    def test_search(self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]):
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.key("/")
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "/ Filter options... ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key("a")
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "/ a                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(" ")
        widget_checker.expect_screen(
            [
                "No options to displa",
                "/ a                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key("/")
        widget_checker.expect_screen(
            [
                "No options to displa",
                "/ a /               ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "/ a                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> ◉ a               ",
                "/ a                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.expect_screen(
            [
                "> ◉ a               ",
                "  ○ b               ",
                "  ○ c               ",
                "/ Filter options... ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "  ◉ a               ",
                "> ○ b               ",
                "  ○ c               ",
                "/ Filter options... ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.expect_screen(
            [
                "  ◉ a               ",
                "> ○ b               ",
                "  ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.text("/c")
        widget_checker.expect_screen(
            [
                "> ○ c               ",
                "/ c                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.ESCAPE)
        widget_checker.expect_screen(
            [
                "  ◉ a               ",
                "  ○ b               ",
                "> ○ c               ",
                "C-d accept • f1 help",
                "                    ",
            ]
        )
        widget_checker.text("/b")
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ]
            )
        )

        assert result == [1, 2]

    def test_filter(self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]):
        widget_checker.text("/1")
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "/ 1                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ],
                filter=lambda opt, req: str(opt.value) == req,
            )
        )

        assert result == [1]

    def test_mapper(self, widget_checker: WidgetChecker[yuio.widget.Multiselect[int]]):
        widget_checker.text("/a")
        widget_checker.expect_screen(
            [
                "No options to displa",
                "/ a                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.BACKSPACE)
        widget_checker.key("A")
        widget_checker.expect_screen(
            [
                "> ○ a               ",
                "/ A                 ",
                "C-d accept • f1 help",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.key("d", ctrl=True)

        result = widget_checker.check(
            yuio.widget.Multiselect(
                [
                    yuio.widget.Option(1, "a"),
                    yuio.widget.Option(2, "b"),
                    yuio.widget.Option(3, "c"),
                ],
                mapper=lambda opt: opt.display_text.upper(),
            )
        )

        assert result == [1]


class TestInputWithCompletion:
    @pytest.fixture
    def widget(self):
        return yuio.widget.InputWithCompletion(
            yuio.complete.Choice(
                [
                    yuio.complete.Option("apple"),
                    yuio.complete.Option("banana"),
                    yuio.complete.Option("bamboo"),
                    yuio.complete.Option("mayweed"),
                ]
            )
        )

    @pytest.fixture
    def widget_list(self):
        return yuio.widget.InputWithCompletion(
            yuio.complete.List(
                yuio.complete.Choice(
                    [
                        yuio.complete.Option("apple"),
                        yuio.complete.Option("banana"),
                        yuio.complete.Option("bamboo"),
                        yuio.complete.Option("mayweed"),
                    ]
                )
            )
        )

    def test_simple(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
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

        widget_checker.check(widget)

    def test_input(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("abc")
        widget_checker.expect_screen(
            [
                "> abc               ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "abc"

    def test_no_completion(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("x")
        widget_checker.expect_screen(
            [
                "> x                 ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> x                 ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "x"

    def test_finish_single_option(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("a")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> apple             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "apple"

    def test_finish_single_option_part(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("b")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("n")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "banana"

    def test_finish_single_option_and_undo(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.text("a")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> apple             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("-", ctrl=True)
        widget_checker.expect_screen(
            [
                "> a                 ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "a"

    def test_complete(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "  bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> bamboo            ",
                "> bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "  bamboo  > banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "banana"

    def test_navigate_completions(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "  bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ARROW_DOWN)
        widget_checker.expect_screen(
            [
                "> bamboo            ",
                "> bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ARROW_RIGHT)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "  bamboo  > banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "banana"

    def test_complete_with_trailing_text(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("xxx")
        widget_checker.key("a", ctrl=True)
        widget_checker.text("ba")
        widget_checker.expect_screen(
            [
                "> baxxx             ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> baxxx             ",
                "  bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> bamboo            ",
                "> bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "  bamboo  > banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "banana"

    def test_cancel(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "  bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ESCAPE)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> bamboo            ",
                "> bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ESCAPE)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "ba"

    def test_undo(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "  bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("-", ctrl=True)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> bamboo            ",
                "> bamboo    banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("-", ctrl=True)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)

        result = widget_checker.check(widget)
        assert result == "ba"

    def test_continue_typing(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "  bamboo  > banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("s")
        widget_checker.expect_screen(
            [
                "> bananas           ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        result = widget_checker.check(widget)
        assert result == "bananas"

    def test_paste(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "  bamboo  > banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.paste("ses")
        widget_checker.expect_screen(
            [
                "> bananases         ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        result = widget_checker.check(widget)
        assert result == "bananases"  # hobbitses!

    def test_continue_typing_and_undo(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        widget_checker.text("ba")
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.key(yuio.widget.Key.TAB)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "  bamboo  > banana  ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("s")
        widget_checker.expect_screen(
            [
                "> bananas           ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("-", ctrl=True)
        widget_checker.expect_screen(
            [
                "> banana            ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("-", ctrl=True)
        widget_checker.expect_screen(
            [
                "> ba                ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key("-", ctrl=True)
        widget_checker.expect_screen(
            [
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
                "                    ",
            ]
        )
        widget_checker.key(yuio.widget.Key.ENTER)
        result = widget_checker.check(widget)
        assert result == ""

    @pytest.mark.skip(reason="TODO")
    def test_rsymbols_on_enter(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        pass

    @pytest.mark.skip(reason="TODO")
    def test_rsymbols_on_typing(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        pass

    @pytest.mark.skip(reason="TODO")
    def test_rsymbols_on_esc(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        pass

    @pytest.mark.skip(reason="TODO")
    def test_rsymbols_on_undo(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        pass

    @pytest.mark.skip(reason="TODO")
    def test_rsymbols_on_paste(
        self,
        widget_checker: WidgetChecker[yuio.widget.InputWithCompletion],
        widget: yuio.widget.InputWithCompletion,
    ):
        pass

    # todo: test arrays


@pytest.mark.parametrize(
    ("keycodes", "expected"),
    [
        # Normal symbols.
        (["a"], [yuio.widget.KeyboardEvent("a")]),
        (["A"], [yuio.widget.KeyboardEvent("A")]),
        (["1"], [yuio.widget.KeyboardEvent("1")]),
        ([" "], [yuio.widget.KeyboardEvent(" ")]),
        (
            ["a", "b", "c"],
            [
                yuio.widget.KeyboardEvent("a"),
                yuio.widget.KeyboardEvent("b"),
                yuio.widget.KeyboardEvent("c"),
            ],
        ),
        # Special symbols.
        (["\t"], [yuio.widget.KeyboardEvent(yuio.widget.Key.TAB)]),
        (["\r"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ENTER)]),
        (["\n"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ENTER)]),
        (["\x7f"], [yuio.widget.KeyboardEvent(yuio.widget.Key.BACKSPACE)]),
        (["\x08"], [yuio.widget.KeyboardEvent(yuio.widget.Key.BACKSPACE)]),
        (["\x1b", ""], [yuio.widget.KeyboardEvent(yuio.widget.Key.ESCAPE)]),
        # Ctrl+letter.
        (["\x01"], [yuio.widget.KeyboardEvent("a", ctrl=True)]),
        (["\x02"], [yuio.widget.KeyboardEvent("b", ctrl=True)]),
        (["\x03"], [yuio.widget.KeyboardEvent("c", ctrl=True)]),
        (["\x04"], [yuio.widget.KeyboardEvent("d", ctrl=True)]),
        (["\x05"], [yuio.widget.KeyboardEvent("e", ctrl=True)]),
        (["\x06"], [yuio.widget.KeyboardEvent("f", ctrl=True)]),
        (["\x07"], [yuio.widget.KeyboardEvent("g", ctrl=True)]),
        (["\x0b"], [yuio.widget.KeyboardEvent("k", ctrl=True)]),
        (["\x0c"], [yuio.widget.KeyboardEvent("l", ctrl=True)]),
        (["\x0e"], [yuio.widget.KeyboardEvent("n", ctrl=True)]),
        (["\x0f"], [yuio.widget.KeyboardEvent("o", ctrl=True)]),
        (["\x10"], [yuio.widget.KeyboardEvent("p", ctrl=True)]),
        (["\x11"], [yuio.widget.KeyboardEvent("q", ctrl=True)]),
        (["\x12"], [yuio.widget.KeyboardEvent("r", ctrl=True)]),
        (["\x13"], [yuio.widget.KeyboardEvent("s", ctrl=True)]),
        (["\x14"], [yuio.widget.KeyboardEvent("t", ctrl=True)]),
        (["\x15"], [yuio.widget.KeyboardEvent("u", ctrl=True)]),
        (["\x16"], [yuio.widget.KeyboardEvent("v", ctrl=True)]),
        (["\x17"], [yuio.widget.KeyboardEvent("w", ctrl=True)]),
        (["\x18"], [yuio.widget.KeyboardEvent("x", ctrl=True)]),
        (["\x19"], [yuio.widget.KeyboardEvent("y", ctrl=True)]),
        (["\x1a"], [yuio.widget.KeyboardEvent("z", ctrl=True)]),
        (["\x1c"], [yuio.widget.KeyboardEvent("4", ctrl=True)]),
        (["\x1d"], [yuio.widget.KeyboardEvent("5", ctrl=True)]),
        (["\x1e"], [yuio.widget.KeyboardEvent("6", ctrl=True)]),
        (["\x1f"], [yuio.widget.KeyboardEvent("7", ctrl=True)]),
        # Alt+letter.
        (["\x1ba"], [yuio.widget.KeyboardEvent("a", alt=True)]),
        (["\x1bA"], [yuio.widget.KeyboardEvent("A", alt=True)]),
        (["\x1b1"], [yuio.widget.KeyboardEvent("1", alt=True)]),
        # Double escape means alt+escape.
        (
            ["\x1b\x1b"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ESCAPE, alt=True)],
        ),
        # Multiple escapes fall back to alt+letter.
        (["\x1b\x1b\x1ba"], [yuio.widget.KeyboardEvent("a", alt=True)]),
        (
            ["\x1b\x1b\x1b"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ESCAPE, alt=True)],
        ),
        # Arrow keys.
        (["\x1b[A"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP)]),
        (["\x1b[B"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN)]),
        (["\x1b[C"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT)]),
        (["\x1b[D"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT)]),
        # Home/End.
        (["\x1b[H"], [yuio.widget.KeyboardEvent(yuio.widget.Key.HOME)]),
        (["\x1b[F"], [yuio.widget.KeyboardEvent(yuio.widget.Key.END)]),
        (["\x1b[1~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.HOME)]),
        (["\x1b[4~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.END)]),
        (["\x1b[7~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.HOME)]),
        (["\x1b[8~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.END)]),
        # Insert/Delete.
        (["\x1b[2~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.INSERT)]),
        (["\x1b[3~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE)]),
        # Page Up/Down.
        (["\x1b[5~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_UP)]),
        (["\x1b[6~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.PAGE_DOWN)]),
        # Function keys.
        (["\x1b[11~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F1)]),
        (["\x1b[12~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F2)]),
        (["\x1b[13~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F3)]),
        (["\x1b[14~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F4)]),
        (["\x1b[15~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F5)]),
        (["\x1b[17~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F6)]),
        (["\x1b[18~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F7)]),
        (["\x1b[19~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F8)]),
        (["\x1b[20~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F9)]),
        (["\x1b[21~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F10)]),
        (["\x1b[23~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F11)]),
        (["\x1b[24~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F12)]),
        # Arrow keys with modifiers.
        (
            ["\x1b[1;2A"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP, shift=True)],
        ),
        (
            ["\x1b[1;3A"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP, alt=True)],
        ),
        (
            ["\x1b[1;4A"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP, alt=True, shift=True)],
        ),
        (
            ["\x1b[1;5A"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP, ctrl=True)],
        ),
        (
            ["\x1b[1;6A"],
            [
                yuio.widget.KeyboardEvent(
                    yuio.widget.Key.ARROW_UP, ctrl=True, shift=True
                )
            ],
        ),
        (
            ["\x1b[1;7A"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP, ctrl=True, alt=True)],
        ),
        (
            ["\x1b[1;8A"],
            [
                yuio.widget.KeyboardEvent(
                    yuio.widget.Key.ARROW_UP, ctrl=True, alt=True, shift=True
                )
            ],
        ),
        (
            ["\x1b[1;5B"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN, ctrl=True)],
        ),
        (
            ["\x1b[1;5C"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT, ctrl=True)],
        ),
        (
            ["\x1b[1;5D"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT, ctrl=True)],
        ),
        (
            ["\x1b[3;5~"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE, ctrl=True)],
        ),
        # SS3 arrow keys.
        (["\x1bOA"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP)]),
        (["\x1bOB"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN)]),
        (["\x1bOC"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_RIGHT)]),
        (["\x1bOD"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_LEFT)]),
        # SS3 function keys.
        (["\x1bOP"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F1)]),
        (["\x1bOQ"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F2)]),
        (["\x1bOR"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F3)]),
        (["\x1bOS"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F4)]),
        # SS3 Home/End.
        (["\x1bOH"], [yuio.widget.KeyboardEvent(yuio.widget.Key.HOME)]),
        (["\x1bOF"], [yuio.widget.KeyboardEvent(yuio.widget.Key.END)]),
        # Shift+Tab (SS3 Z).
        (["\x1bOZ"], [yuio.widget.KeyboardEvent(yuio.widget.Key.TAB, shift=True)]),
        # SS3 Enter.
        (["\x1bOM"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ENTER)]),
        # CSI u format.
        (["\x1b[97u"], [yuio.widget.KeyboardEvent("a")]),
        (["\x1b[97;2u"], [yuio.widget.KeyboardEvent("a", shift=True)]),
        (["\x1b[97;3u"], [yuio.widget.KeyboardEvent("a", alt=True)]),
        (["\x1b[97;5u"], [yuio.widget.KeyboardEvent("a", ctrl=True)]),
        (
            ["\x1b[97;8u"],
            [yuio.widget.KeyboardEvent("a", ctrl=True, alt=True, shift=True)],
        ),
        # CSI 27 format.
        (["\x1b[27;1;27~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ESCAPE)]),
        (["\x1b[27;2;97~"], [yuio.widget.KeyboardEvent("a", shift=True)]),
        (["\x1b[27;3;97~"], [yuio.widget.KeyboardEvent("a", alt=True)]),
        (["\x1b[27;5;97~"], [yuio.widget.KeyboardEvent("a", ctrl=True)]),
        (
            ["\x1b[27;8;97~"],
            [yuio.widget.KeyboardEvent("a", ctrl=True, alt=True, shift=True)],
        ),
        # DCS are ignored.
        (["\x1b]ignored\x1b\\"], []),
        (["\x1b]", "ignored", "\x1b\\"], []),
        (["\x1b]ignored\x9c"], []),
        # 8-bit CSI (0x9b).
        (["\x9bA"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP)]),
        (["\x9bB"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN)]),
        (["\x9b3~"], [yuio.widget.KeyboardEvent(yuio.widget.Key.DELETE)]),
        # 8-bit SS3 (0x8f).
        (["\x8fP"], [yuio.widget.KeyboardEvent(yuio.widget.Key.F1)]),
        (["\x8fA"], [yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP)]),
        # 8-bit DCS (0x90)
        (["\x90ignored\x1b\\"], []),
        # 8-bit SS2 (0x9d)
        (["\x9dignored\x1b\\"], []),
        # ESC [ without continuation gives alt+[.
        (["\x1b["], [yuio.widget.KeyboardEvent("[", alt=True)]),
        # ESC O without continuation gives alt+O, not SS3.
        (["\x1bO"], [yuio.widget.KeyboardEvent("O", alt=True)]),
        # Unicode characters.
        (["é"], [yuio.widget.KeyboardEvent("é")]),
        (["日"], [yuio.widget.KeyboardEvent("日")]),
        (["🎉"], [yuio.widget.KeyboardEvent("🎉")]),
        # High characters (>= 160).
        (["\xa0"], [yuio.widget.KeyboardEvent("\xa0")]),
        (["\xff"], [yuio.widget.KeyboardEvent("\xff")]),
        # Escape sequences come in a single chunk.
        (
            ["", "AB", "\x1b[AA\x1b[BB"],
            [
                yuio.widget.KeyboardEvent("A"),
                yuio.widget.KeyboardEvent("B"),
                yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_UP),
                yuio.widget.KeyboardEvent("A"),
                yuio.widget.KeyboardEvent(yuio.widget.Key.ARROW_DOWN),
                yuio.widget.KeyboardEvent("B"),
            ],
        ),
        # Bracketed paste.
        (
            ["\x1b[200~hello\x1b[201~"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str="hello")],
        ),
        # Bracketed paste - text comes in chunks.
        (
            ["\x1b[200~", "hello", "\x1b[201~"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str="hello")],
        ),
        (
            ["\x1b[200~", "hello ", "world", "\x1b[201~"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str="hello world")],
        ),
        (
            ["\x1b[200~", "line1\nline2", "\x1b[201~"],
            [
                yuio.widget.KeyboardEvent(
                    yuio.widget.Key.PASTE, paste_str="line1\nline2"
                )
            ],
        ),
        (
            ["\x1b[200~", "", "\x1b[201~"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str="")],
        ),
        # Paste with special characters.
        (
            ["\x1b[200~", "tab\there", "\x1b[201~"],
            [yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str="tab\there")],
        ),
        # Paste is followed by other characters.
        (
            ["\x1b[200~", "tab\there", "\x1b[201~AB"],
            [
                yuio.widget.KeyboardEvent(yuio.widget.Key.PASTE, paste_str="tab\there"),
                yuio.widget.KeyboardEvent("A"),
                yuio.widget.KeyboardEvent("B"),
            ],
        ),
    ],
)
def test_event_stream(
    keycodes: list[str],
    expected: list[yuio.widget.KeyboardEvent],
    monkeypatch,
):
    keycode_iter = iter(keycodes)
    monkeypatch.setattr("yuio.term._read_keycode", lambda *_: next(keycode_iter, "$"))

    stream = yuio.widget._event_stream(None, None)  # type: ignore
    for event in expected:
        assert next(stream) == event
    assert next(stream) == yuio.widget.KeyboardEvent("$")
