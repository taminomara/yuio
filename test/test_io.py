import io

import pytest

import yuio.io
import yuio.parse
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _t

from .conftest import IOMocker, RcCompare


@pytest.fixture(autouse=True)
def setup(
    term: yuio.term.Term, theme: yuio.theme.Theme, monkeypatch: pytest.MonkeyPatch
):
    theme.set_color("code", "magenta")
    theme.set_color("msg/decoration", "magenta")
    theme.set_color("msg/text:heading", "bold")
    theme.set_color("msg/text:question", "blue")
    theme.set_color("msg/text:error", "red")
    theme.set_color("msg/text:warning", "yellow")
    theme.set_color("msg/text:success", "green")
    theme.set_color("msg/text:info", "cyan")
    theme.progress_bar_width = 5

    io_manager = yuio.io._IoManager(term, theme, enable_bg_updates=False)
    monkeypatch.setattr("yuio.io._IO_MANAGER", io_manager)
    io_manager.formatter.width = 20

    yield

    io_manager.stop()


class TestSetup:
    @pytest.mark.xfail(reason="TODO")
    def test_simple(self):
        pass

    @pytest.mark.xfail(reason="TODO")
    def test_term(self):
        pass

    @pytest.mark.xfail(reason="TODO")
    def test_theme(self):
        pass

    @pytest.mark.xfail(reason="TODO")
    def test_theme_callable(self):
        pass

    @pytest.mark.xfail(reason="TODO")
    def test_term_theme(self):
        pass

    @pytest.mark.xfail(reason="TODO")
    def test_term_theme_callable(self):
        pass


class TestMessage:
    def test_info(self, ostream: io.StringIO):
        yuio.io.info("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
            ],
            [
                "cccccccc            ",
            ],
        )

    def test_info_wrap(self, ostream: io.StringIO):
        yuio.io.info("foo bar baz foo bar baz foo bar baz!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar baz foo bar ",
                "baz foo bar baz!    ",
            ],
            [
                "ccccccccccccccccccc ",
                "cccccccccccccccc    ",
            ],
        )

    def test_info_args(self, ostream: io.StringIO):
        yuio.io.info("%s %s!", "foo", "bar")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
            ],
            [
                "cccccccc            ",
            ],
        )

    def test_info_color_tags(self, ostream: io.StringIO):
        yuio.io.info("`%s` <c bold>%s</c>!", "<c green>foo</c>", "bar")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "<c green>foo</c> bar",
                "!                   ",
            ],
            [
                "mmmmmmmmmmmmmmmmcCCC",
                "c                   ",
            ],
        )

    def test_warning(self, ostream: io.StringIO):
        yuio.io.warning("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
            ],
            [
                "yyyyyyyy            ",
            ],
        )

    def test_error(self, ostream: io.StringIO):
        yuio.io.error("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
            ],
            [
                "rrrrrrrr            ",
            ],
        )

    def test_error_with_tb(self, ostream: io.StringIO, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(
            "traceback.format_exception", lambda ty, val, tb: [f"{ty.__name__}: {val}"]
        )

        try:
            raise RuntimeError("something happened")
        except RuntimeError:
            yuio.io.error_with_tb("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
                "  RuntimeError: some",
                "thing happened      ",
            ],
            [
                "rrrrrrrr            ",
                "                    ",
                "                    ",
            ],
        )

    def test_error_with_tb_manual(
        self, ostream: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "traceback.format_exception", lambda ty, val, tb: [f"{ty.__name__}: {val}"]
        )

        try:
            raise RuntimeError("something happened")
        except RuntimeError as e:
            yuio.io.error_with_tb("foo bar!", exc_info=(TypeError, e, e.__traceback__))
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
                "  TypeError: somethi",
                "ng happened         ",
            ],
            [
                "rrrrrrrr            ",
                "                    ",
                "                    ",
            ],
        )

    def test_success(self, ostream: io.StringIO):
        yuio.io.success("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
            ],
            [
                "gggggggg            ",
            ],
        )

    def test_heading(self, ostream: io.StringIO):
        yuio.io.heading("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "⣿ foo bar!          ",
            ],
            [
                "mmBBBBBBBB          ",
            ],
        )

    def test_md(self, ostream: io.StringIO):
        yuio.io.md("# Foo!\n\n- bar\n- baz")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "⣿ Foo!              ",
                "                    ",
                "•   bar             ",
                "                    ",
                "•   baz             ",
            ],
            [
                "mmBBBB              ",
                "                    ",
                "mmmm                ",
                "                    ",
                "mmmm                ",
            ],
        )

    def test_br(self, ostream: io.StringIO):
        yuio.io.info("foo")
        yuio.io.br()
        yuio.io.info("bar")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo                 ",
                "                    ",
                "bar                 ",
            ],
            [
                "ccc                 ",
                "                    ",
                "ccc                 ",
            ],
        )

    def test_raw(self, ostream: io.StringIO):
        yuio.io.raw(
            yuio.term.ColorizedString(["foo, ", yuio.term.Color.FORE_RED, "bar"])
        )

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo, bar            ",
            ],
            [
                "     rrr            ",
            ],
        )


class TestAsk:
    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Hello?              ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("Hii~")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Hello?") == "Hii~"

    def test_empty(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Hello?              ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)
        io_mocker.expect_screen(
            [
                "Hello?              ",
                ">                   ",
                "▲ Error: input is   ",
                "required.           ",
                "f1 help             ",
            ],
        )
        io_mocker.text("123")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Hello?") == "123"

    def test_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "What's your deal?   ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("meow =^..^=")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("What's your %s?", "deal") == "meow =^..^="

    def test_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter something:    ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("123")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Enter something") == "123"

    def test_dont_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter something:    ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("123")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Enter something:") == "123"

    def test_default(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q?                  ",
                "> {default}         ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default="{default}") == "{default}"

    def test_default_overridden(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q?                  ",
                "> {default}         ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("foo!")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default="{default}") == "foo!"

    def test_default_optional(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q?                  ",
                "> <none>            ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default=None) is None

    def test_default_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q:                  ",
                "> {default}         ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q", default="{default}") == "{default}"

    def test_default_dont_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q:                  ",
                "> {default}         ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q:", default="{default}") == "{default}"

    def test_input_description(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q:                  ",
                ">                   ",
                "<text> • f1 help    ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.F1)
        io_mocker.expect_screen(
            [
                "Input Format        ",
                "                    ",
                "            <text>  ",
                "                    ",
                ":                   ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ESCAPE)
        io_mocker.text("123")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q:", input_description="<text>") == "123"

    def test_default_description(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q:                  ",
                "> <default>         ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert (
                yuio.io.ask("Q:", default="{default}", default_description="<default>")
                == "{default}"
            )

    def test_parser(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Are you there?      ",
                "> no        yes     ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.TAB)
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Are you there?", parser=yuio.parse.Bool())

    def test_type_hint(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Are you there?      ",
                "> no        yes     ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.TAB)
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask[bool]("Are you there?")

    def test_type_hint_and_parser(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter some numbers: ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("123 456")
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask[bool](
                "Enter some numbers", parser=yuio.parse.List(yuio.parse.Int())
            ) == [123, 456]


class TestAskNonInteractive:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            interactive_support=yuio.term.InteractiveSupport.MOVE_CURSOR,
        )

    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Hello?              ",
            ],
        )
        io_mocker.expect_istream_readline("Hii~")

        with io_mocker.mock():
            assert yuio.io.ask("Hello?") == "Hii~"

    def test_empty(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Hello?              ",
            ],
        )
        io_mocker.expect_istream_readline("\n")
        io_mocker.expect_screen(
            [
                "Hello?              ",
                "Input is required.  ",
                "Hello?              ",
            ],
        )
        io_mocker.expect_istream_readline("Hii~\n")

        with io_mocker.mock():
            assert yuio.io.ask("Hello?") == "Hii~"

    def test_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "What's your deal?   ",
            ],
        )
        io_mocker.expect_istream_readline("meow =^..^=\n")

        with io_mocker.mock():
            assert yuio.io.ask("What's your %s?", "deal") == "meow =^..^="

    def test_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter something:    ",
            ],
        )
        io_mocker.expect_istream_readline("123\n")

        with io_mocker.mock():
            assert yuio.io.ask("Enter something") == "123"

    def test_dont_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter something:    ",
            ],
        )
        io_mocker.expect_istream_readline("123\n")

        with io_mocker.mock():
            assert yuio.io.ask("Enter something:") == "123"

    def test_default(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q? [{default}]      ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default="{default}") == "{default}"

    def test_default_overridden(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q? [{default}]      ",
            ],
        )
        io_mocker.expect_istream_readline("foo!\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default="{default}") == "foo!"

    def test_default_optional(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q? [<none>]         ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default=None) is None

    def test_default_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q [{default}]:      ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q", default="{default}") == "{default}"

    def test_default_dont_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q [{default}]:      ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q:", default="{default}") == "{default}"

    def test_input_description(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q (<text>):         ",
            ],
        )
        io_mocker.expect_istream_readline("123\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q:", input_description="<text>") == "123"

    def test_default_description(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q [<default>]:      ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert (
                yuio.io.ask("Q:", default="{default}", default_description="<default>")
                == "{default}"
            )

    def test_parser(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Are you there? (yes|",
                "no)                 ",
            ],
        )
        io_mocker.expect_istream_readline("what?\n")
        io_mocker.expect_screen(
            [
                "Are you there? (yes|",
                "no) what?           ",
                "Error: could not    ",
                "parse value 'what?',",
                "enter either 'yes'  ",
                "or 'no'.            ",
                "Are you there? (yes|",
                "no)                 ",
            ],
        )
        io_mocker.expect_istream_readline("y\n")

        with io_mocker.mock():
            assert yuio.io.ask("Are you there?", parser=yuio.parse.Bool())

    def test_parser(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Are you there? (yes|",
                "no)                 ",
            ],
        )
        io_mocker.expect_istream_readline("what?\n")
        io_mocker.expect_screen(
            [
                "Are you there? (yes|",
                "no) what?           ",
                "Error: could not    ",
                "parse value 'what?',",
                "enter either 'yes'  ",
                "or 'no'.            ",
                "Are you there? (yes|",
                "no)                 ",
            ],
        )
        io_mocker.expect_istream_readline("y\n")

        with io_mocker.mock():
            assert yuio.io.ask[bool]("Are you there?")

    def test_type_hint_and_parser(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter some numbers (",
                "int[ int[ ...]]):   ",
            ],
        )
        io_mocker.expect_istream_readline("123 456\n")

        with io_mocker.mock():
            assert yuio.io.ask[bool](
                "Enter some numbers", parser=yuio.parse.List(yuio.parse.Int())
            ) == [123, 456]


class TestAskUnreadable:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        istream.readable = lambda: False
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            interactive_support=yuio.term.InteractiveSupport.NONE,
        )

    def test_default(self, io_mocker: IOMocker):
        with io_mocker.mock():
            assert yuio.io.ask("Meow?", default="Meow!") == "Meow!"

    def test_no_default(self, io_mocker: IOMocker):
        with io_mocker.mock():
            with pytest.raises(
                yuio.io.UserIoError, match="non-interactive environment"
            ):
                yuio.io.ask("Meow?")


class TestWaitForUser:
    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Press enter to      ",
                "continue            ",
            ]
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            yuio.io.wait_for_user()

    def test_msg(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Slam that Enter     ",
                "button!             ",
            ]
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            yuio.io.wait_for_user("Slam that Enter button!")

    def test_msg_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Slam that Enter     ",
                "button!             ",
            ]
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            yuio.io.wait_for_user("Slam that %s button!", "Enter")


class TestWaitForUserNonInteractive:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            interactive_support=yuio.term.InteractiveSupport.MOVE_CURSOR,
        )

    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Press enter to conti",
                "nue                 ",
            ]
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            yuio.io.wait_for_user()

    def test_add_space(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Press enter to conti",
                "nue                 ",
            ]
        )
        io_mocker.expect_istream_readline(".\n")
        io_mocker.expect_screen(
            [
                "Press enter to conti",
                "nue .               ",
            ]
        )

        with io_mocker.mock():
            yuio.io.wait_for_user()

    def test_dont_add_space(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Ends with space     ",
            ]
        )
        io_mocker.expect_istream_readline(".\n")
        io_mocker.expect_screen(
            [
                "Ends with space .   ",
            ]
        )

        with io_mocker.mock():
            yuio.io.wait_for_user("Ends with space ")

    def test_msg(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Slam that Enter butt",
                "on!                 ",
            ]
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            yuio.io.wait_for_user("Slam that Enter button!")

    def test_msg_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Slam that Enter butt",
                "on!                 ",
            ]
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            yuio.io.wait_for_user("Slam that %s button!", "Enter")


class TestWaitForUserUnreadable:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        istream.readable = lambda: False
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            interactive_support=yuio.term.InteractiveSupport.NONE,
        )

    def test_wait(self, io_mocker: IOMocker):
        io_mocker.expect_screen([])
        with io_mocker.mock():
            yuio.io.wait_for_user()


class TestDetectEditor:
    def test_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("EDITOR", "foobar")
        assert yuio.io.detect_editor() == "foobar"

    @pytest.mark.parametrize("editor", ["vi", "nano", "notepad.exe"])
    def test_which(self, editor: str, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("shutil.which", lambda exc: exc if exc == editor else None)
        assert yuio.io.detect_editor() == editor

    def test_fail(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setattr("shutil.which", lambda exc: None)
        assert yuio.io.detect_editor() is None


class TestEdit:
    def test_simple(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: "printf ' edited' >> ")
        assert yuio.io.edit("foobar") == "foobar edited"

    def test_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: None)
        assert yuio.io.edit("foobar", editor="printf ' edited' >> ") == "foobar edited"

    def test_editor_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: "exit 1; cat")
        with pytest.raises(yuio.io.UserIoError, match="editing failed"):
            assert yuio.io.edit("foobar")

    def test_no_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: None)
        with pytest.raises(yuio.io.UserIoError, match="can't detect an editor"):
            assert yuio.io.edit("foobar")

    def test_comments(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: "printf ' edited' >> ")
        assert yuio.io.edit("# foo\n  # bar\nbaz #") == "baz # edited"
        assert yuio.io.edit("foo\n#") == "foo\n"

    def test_comments_custom_marker(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: "printf ' edited' >> ")
        assert (
            yuio.io.edit("// foo\n  # bar\nbaz //", comment_marker="//")
            == "  # bar\nbaz // edited"
        )
        assert yuio.io.edit("foo\n//", comment_marker="//") == "foo\n"

    def test_comments_custom_marker_special_symbols(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: "printf ' edited' >> ")
        assert yuio.io.edit("a\nb\n[ab]", comment_marker="[ab]") == "a\nb\n"
