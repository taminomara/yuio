import io

import yuio.term
import yuio.theme
import yuio.widget

from .conftest import RcCompare


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

    def test_write_zero_width(
        self, sstream: io.StringIO, rc: yuio.widget.RenderContext
    ):
        rc.write("x\u0306y")
        rc.set_pos(-1, 1)
        rc.write("a\u0306b")
        rc.set_pos(18, 1)
        rc.write("c\u0306d")
        rc.render()

        assert sstream.getvalue() == (
            "\x1b[J\x1b[mx\u0306y"  # first write
            "\nb"  # second write
            "\x1b[19Gc\u0306"  # third write
            "\x1b[1A\x1b[1G"  # setting cursor final position
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
