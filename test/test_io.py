import io
import sys

import pytest

import yuio.io
import yuio.parse
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _t

from .conftest import IOMocker, RcCompare


@pytest.fixture()
def enable_bg_updates() -> bool:
    return False


@pytest.fixture(autouse=True)
def setup(
    term: yuio.term.Term,
    theme: yuio.theme.Theme,
    monkeypatch: pytest.MonkeyPatch,
    enable_bg_updates: bool,
    width: int,
):
    theme.spinner_pattern = "⣿"
    theme.set_color("code", "magenta")
    theme.set_color("msg/decoration", "magenta")
    theme.set_color("msg/text:heading", "bold")
    theme.set_color("msg/text:question", "blue")
    theme.set_color("msg/text:error", "red")
    theme.set_color("msg/text:warning", "yellow")
    theme.set_color("msg/text:success", "green")
    theme.set_color("msg/text:info", "cyan")
    theme.progress_bar_width = 5

    io_manager = yuio.io._IoManager(term, theme, enable_bg_updates=enable_bg_updates)
    monkeypatch.setattr("yuio.io._IO_MANAGER", io_manager)
    io_manager.formatter.width = width

    yield

    io_manager.stop()


class TestSetup:
    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io._IO_MANAGER", None)

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

    @pytest.mark.xfail(reason="TODO")
    def test_wrap_streams(self):
        pass

    @pytest.mark.xfail(reason="TODO")
    def test_wrap_streams_non_interactive(self):
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
                "mm########          ",
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
                "mm####              ",
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
    # no space after 'edited' because on windows,
    # cmd.exe adds space to the output (wtf?)
    _EDITOR = "echo edited>>"

    def test_simple(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: self._EDITOR)
        assert yuio.io.edit("foobar") == "foobaredited\n"

    def test_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: None)
        assert yuio.io.edit("foobar", editor=self._EDITOR) == "foobaredited\n"

    def test_editor_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: "exit 1; cat")
        with pytest.raises(yuio.io.UserIoError, match="editing failed"):
            assert yuio.io.edit("foobar")

    def test_no_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: None)
        with pytest.raises(yuio.io.UserIoError, match="can't detect an editor"):
            assert yuio.io.edit("foobar")

    def test_comments(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: self._EDITOR)
        assert yuio.io.edit("# foo\n  # bar\nbaz #") == "baz #edited\n"
        assert yuio.io.edit("foo\n#") == "foo\n"

    def test_comments_custom_marker(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: self._EDITOR)
        assert (
            yuio.io.edit("// foo\n  # bar\nbaz //", comment_marker="//")
            == "  # bar\nbaz //edited\n"
        )
        assert yuio.io.edit("foo\n//", comment_marker="//") == "foo\n"

    def test_comments_custom_marker_special_symbols(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("yuio.io.detect_editor", lambda: self._EDITOR)
        assert yuio.io.edit("a\nb\n[ab]", comment_marker="[ab]") == "a\nb\n"


class TestTask:
    @pytest.fixture()
    def width(self):
        return 40

    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task"):
                io_mocker.mark()

    def test_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task 1                                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task 1 - done                         ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task `%s`", 1):
                io_mocker.mark()

    def test_print_while_in_task(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task 1                                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "hello world!                            ",
                "⣿ task 1                                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "hello world!                            ",
                "> task 1 - done                         ",
                "hello world 2!                          ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task `%s`", 1):
                io_mocker.mark()
                yuio.io.info("hello world!")
                io_mocker.mark()
            yuio.io.info("hello world 2!")

    def test_error_in_task(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - error                          ",
            ]
        )

        with io_mocker.mock():
            with pytest.raises(RuntimeError, match="eh..."):
                with yuio.io.Task("task"):
                    io_mocker.mark()
                    raise RuntimeError("eh...")

    def test_manual_error(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - error                          ",
            ]
        )

        with io_mocker.mock():
            task = yuio.io.Task("task")
            io_mocker.mark()
            task.error()

    def test_manual_done(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            task = yuio.io.Task("task")
            io_mocker.mark()
            task.done()

    def test_comment(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "⣿ task - yaaay!                         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.comment("yaaay!")
                io_mocker.mark()

    def test_comment_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "⣿ task - yaaay 1!                       ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.comment("yaaay `%s`!", 1)
                io_mocker.mark()

    def test_comment_format_chached(self, io_mocker: IOMocker):
        class Fmt:
            i = 0

            def __str__(self):
                self.i += 1
                return str(self.i)

        fmt = Fmt()

        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "⣿ task - yaaay 1!                       ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "■■□□□ task - 50.00% - yaaay 1!          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "■■□□□ task - 50.00% - yaaay 2!          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.comment("yaaay `%s`!", fmt)
                io_mocker.mark()
                task.progress(0.5)
                io_mocker.mark()
                task.comment("yaaay `%s`!", fmt)
                io_mocker.mark()

    @pytest.mark.parametrize(
        "args,kwargs,comment,expected",
        [
            (
                (0.3,),
                {},
                None,
                [
                    "■■□□□ task - 30.00%                     ",
                ],
            ),
            (
                (0.3,),
                {"unit": "whatever"},
                None,
                [
                    "■■□□□ task - 30.00%                     ",
                ],
            ),
            (
                (0.3,),
                {"ndigits": 0},
                None,
                [
                    "■■□□□ task - 30%                        ",
                ],
            ),
            (
                (11, 15),
                {},
                None,
                [
                    "■■■■□ task - 11/15                      ",
                ],
            ),
            (
                (10.5, 15),
                {},
                None,
                [
                    "■■■■□ task - 10.50/15.00                ",
                ],
            ),
            (
                (11, 15.0),
                {},
                None,
                [
                    "■■■■□ task - 11.00/15.00                ",
                ],
            ),
            (
                (10.5, 15),
                {"unit": "Kg"},
                None,
                [
                    "■■■■□ task - 10.50/15.00Kg              ",
                ],
            ),
            (
                (10.5, 15),
                {"ndigits": 3},
                None,
                [
                    "■■■■□ task - 10.500/15.000              ",
                ],
            ),
            (
                (10.5, 15),
                {"ndigits": 3, "unit": "Kg"},
                None,
                [
                    "■■■■□ task - 10.500/15.000Kg            ",
                ],
            ),
            (
                (0.3,),
                {},
                "comment!",
                [
                    "■■□□□ task - 30.00% - comment!          ",
                ],
            ),
            (
                (0.3,),
                {"unit": "whatever"},
                "comment!",
                [
                    "■■□□□ task - 30.00% - comment!          ",
                ],
            ),
            (
                (0.3,),
                {"ndigits": 0},
                "comment!",
                [
                    "■■□□□ task - 30% - comment!             ",
                ],
            ),
            (
                (11, 15),
                {},
                "comment!",
                [
                    "■■■■□ task - 11/15 - comment!           ",
                ],
            ),
            (
                (10.5, 15),
                {},
                "comment!",
                [
                    "■■■■□ task - 10.50/15.00 - comment!     ",
                ],
            ),
            (
                (10.5, 15),
                {"unit": "Kg"},
                "comment!",
                [
                    "■■■■□ task - 10.50/15.00Kg - comment!   ",
                ],
            ),
            (
                (10.5, 15),
                {"ndigits": 3},
                "comment!",
                [
                    "■■■■□ task - 10.500/15.000 - comment!   ",
                ],
            ),
            (
                (10.5, 15),
                {"ndigits": 3, "unit": "Kg"},
                "comment!",
                [
                    "■■■■□ task - 10.500/15.000Kg - comment! ",
                ],
            ),
        ],
    )
    def test_progress(self, io_mocker: IOMocker, args, kwargs, comment, expected):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(expected)
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.progress(*args, **kwargs)
                if comment:
                    task.comment(comment)
                io_mocker.mark()

    @pytest.mark.parametrize(
        "args,kwargs,expected",
        [
            (
                (50, 100),
                {},
                [
                    "■■□□□ task - 50.00/100.00B              ",
                ],
            ),
            (
                (0.50, 1),
                {},
                [
                    "■■□□□ task - 0.50/1.00B                 ",
                ],
            ),
            (
                (50, 100 * 1024),
                {},
                [
                    "□□□□□ task - 50.00B/100.00K             ",
                ],
            ),
            (
                (50, 100 * 1024 + 100),
                {},
                [
                    "□□□□□ task - 50.00B/100.10K             ",
                ],
            ),
            (
                (50 * 1024, 100 * 1024),
                {},
                [
                    "■■□□□ task - 50.00/100.00K              ",
                ],
            ),
            (
                (50 * 1024, 100.1 * 1024),
                {},
                [
                    "■■□□□ task - 50.00/100.10K              ",
                ],
            ),
            (
                (50, 100.501 * 1024 * 1024),
                {},
                [
                    "□□□□□ task - 50.00B/100.50M             ",
                ],
            ),
            (
                (50, 100.501 * 1024 * 1024),
                {"ndigits": 4},
                [
                    "□□□□□ task - 50.0000B/100.5010M         ",
                ],
            ),
            (
                (1 * 1024 * 1024 * 1024, 100.5 * 1024 * 1024 * 1024),
                {},
                [
                    "□□□□□ task - 1.00/100.50G               ",
                ],
            ),
            (
                (1 * 1024 * 1024 * 1024, 5000 * 1024 * 1024 * 1024 * 1024 * 1024),
                {},
                [
                    "□□□□□ task - 1.00G/5000.00P             ",
                ],
            ),
        ],
    )
    def test_progress_size(self, io_mocker: IOMocker, args, kwargs, expected):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(expected)
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.progress_size(*args, **kwargs)
                io_mocker.mark()

    @pytest.mark.parametrize(
        "args,kwargs,expected",
        [
            (
                (50, 100),
                {},
                [
                    "■■□□□ task - 50.00/100.00               ",
                ],
            ),
            (
                (50000, 100000),
                {},
                [
                    "■■□□□ task - 50.00K/100.00K             ",
                ],
            ),
            (
                (0.01052, 0.1),
                {},
                [
                    "■□□□□ task - 10.52m/100.00m             ",
                ],
            ),
            (
                (0.000000000000000000000001, 1000000000000000000000000),
                {},
                [
                    "□□□□□ task - 1.00y/1.00Y                ",
                ],
            ),
            (
                (0.0000000000000000000000001, 1000200000000000000000000000),
                {},
                [
                    "□□□□□ task - 0.10y/1000.20Y             ",
                ],
            ),
            (
                (50, 100),
                {"unit": "V"},
                [
                    "■■□□□ task - 50.00V/100.00V             ",
                ],
            ),
            (
                (0.00050, 0.001001),
                {"unit": "V"},
                [
                    "■■□□□ task - 500.00µV/1.00mV            ",
                ],
            ),
            (
                (0.00050, 0.001001),
                {"ndigits": 4},
                [
                    "■■□□□ task - 500.0000µ/1.0010m          ",
                ],
            ),
        ],
    )
    def test_progress_scale(self, io_mocker: IOMocker, args, kwargs, expected):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(expected)
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.progress_scale(*args, **kwargs)
                io_mocker.mark()

    def test_reset_progress(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "■■□□□ task - 2/5                        ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.progress(2, 5)
                io_mocker.mark()
                task.progress(None)
                io_mocker.mark()

    @pytest.mark.parametrize(
        "kwargs,expected_format",
        [
            ({}, "{}/{}"),
            ({"ndigits": 2}, "{}.00/{}.00"),
            ({"unit": "x"}, "{}/{}x"),
            ({"unit": "y", "ndigits": 1}, "{}.0/{}.0y"),
        ],
    )
    def test_iter(self, io_mocker: IOMocker, kwargs, expected_format: str):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"□□□□□ task - {expected_format.format(0, 5):<27}",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"■□□□□ task - {expected_format.format(1, 5):<27}",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"■■□□□ task - {expected_format.format(2, 5):<27}",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"■■■□□ task - {expected_format.format(3, 5):<27}",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"■■■■□ task - {expected_format.format(4, 5):<27}",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"■■■■■ task - {expected_format.format(5, 5):<27}",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                f"> task - done                           ",
            ]
        )

        elems = [1, 2, "A", "B", object()]

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                for i, elem in enumerate(task.iter(elems, **kwargs)):
                    assert elem is elems[i]
                    io_mocker.mark()
                io_mocker.mark()

    def test_multiple_tasks(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ T1                                    ",
                "⣿ T2                                    ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "■■□□□ T1 - 2/5                          ",
                "■■■■□ T2 - 4/5                          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "■■□□□ T1 - 2/5                          ",
                "■■■■□ T2 - 4/5                          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "> T2 - done                             ",
                "■■□□□ T1 - 2/5                          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "> T2 - done                             ",
                "bar                                     ",
                "■■□□□ T1 - 2/5                          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "> T2 - done                             ",
                "bar                                     ",
                "> T1 - done                             ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "> T2 - done                             ",
                "bar                                     ",
                "> T1 - done                             ",
                "baz                                     ",
            ]
        )

        with io_mocker.mock():
            t1 = yuio.io.Task("T1")
            t2 = yuio.io.Task("T2")
            io_mocker.mark()
            t1.progress(2, 5)
            t2.progress(4, 5)
            io_mocker.mark()
            yuio.io.info("foo")
            io_mocker.mark()
            t2.done()
            io_mocker.mark()
            yuio.io.info("bar")
            io_mocker.mark()
            t1.done()
            io_mocker.mark()
            yuio.io.info("baz")

    def test_subtask(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ T1                                    ",
                "  ⣿ T1.1                                ",
                "  ⣿ T1.2                                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "⣿ T1                                    ",
                "  ⣿ T1.1                                ",
                "  ⣿ T1.2 - done                         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "⣿ T1                                    ",
                "  ⣿ T1.1                                ",
                "  ⣿ T1.2 - done                         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "⣿ T1                                    ",
                "  ■■□□□ T1.1 - 2/5                      ",
                "  ⣿ T1.2 - done                         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "> T1 - done                             ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "> T1 - done                             ",
                "bar                                     ",
            ]
        )

        with io_mocker.mock():
            t1 = yuio.io.Task("T1")
            t11 = t1.subtask("T1.1")
            t12 = t1.subtask("T1.2")
            io_mocker.mark()
            t12.done()
            io_mocker.mark()
            yuio.io.info("foo")
            io_mocker.mark()
            t11.progress(2, 5)
            io_mocker.mark()
            t1.done()
            io_mocker.mark()
            yuio.io.info("bar")

    def test_progressbar_decoration(self, theme: yuio.theme.Theme, io_mocker: IOMocker):
        theme.progress_bar_start_symbol = "["
        theme.progress_bar_end_symbol = "]"
        theme.progress_bar_done_symbol = ">"
        theme.progress_bar_pending_symbol = "."

        io_mocker.expect_screen(
            [
                "[>>...] Task - 2/5                      ",
            ]
        )
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("Task") as task:
                task.progress(2, 5)
                io_mocker.mark()


class TestSuspendOutput:
    @pytest.fixture()
    def wrap_streams(self) -> bool:
        return True

    @pytest.mark.parametrize(
        "meth,args,expected",
        [
            (
                "warning",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "success",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "error",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "error_with_tb",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "heading",
                ("Bar.",),
                [
                    "                    ",
                    "                    ",
                    "⣿ Bar.              ",
                    "                    ",
                ],
            ),
            (
                "md",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "br",
                (),
                [
                    "                    ",
                ],
            ),
            (
                "raw",
                (yuio.term.ColorizedString("Bar."),),
                [
                    "Bar.                ",
                ],
            ),
        ],
    )
    def test_simple(self, io_mocker: IOMocker, meth, args, expected):
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                *expected,
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            with yuio.io.SuspendOutput():
                io_mocker.mark()
                getattr(yuio.io, meth)(*args)
                io_mocker.mark()

    @pytest.mark.parametrize(
        "meth",
        [
            lambda s: sys.stderr.write(s + "\n"),
            lambda s: sys.stdout.write(s + "\n"),
            lambda s: print(s),
        ],
    )
    def test_streams(self, io_mocker: IOMocker, meth):
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "Bar.                ",
            ]
        )

        with io_mocker.mock(wrap_streams=True):
            yuio.io.info("Foo.")
            with yuio.io.SuspendOutput():
                io_mocker.mark()
                meth("Bar.")
                io_mocker.mark()

    @pytest.mark.parametrize(
        "meth,args,expected",
        [
            (
                "warning",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "success",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "error",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "error_with_tb",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "heading",
                ("Bar.",),
                [
                    "                    ",
                    "                    ",
                    "⣿ Bar.              ",
                    "                    ",
                ],
            ),
            (
                "md",
                ("Bar.",),
                [
                    "Bar.                ",
                ],
            ),
            (
                "br",
                (),
                [
                    "                    ",
                ],
            ),
            (
                "raw",
                (yuio.term.ColorizedString("Bar.\n"),),
                [
                    "Bar.                ",
                ],
            ),
        ],
    )
    def test_ignore(self, io_mocker: IOMocker, meth, args, expected):
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                *expected,
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                *expected,
                *expected,
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            with yuio.io.SuspendOutput() as o:
                io_mocker.mark()
                getattr(yuio.io, meth)(*args)
                getattr(o, meth)(*args)
                io_mocker.mark()

    def test_task(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "> Task - done       ",
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            io_mocker.mark()
            with yuio.io.SuspendOutput():
                task = yuio.io.Task("Task")
                io_mocker.mark()
                task.done()
                io_mocker.mark()

    def test_task_start_before_suspended(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "⣿ Task              ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "⣿ Task              ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "> Task - done       ",
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            task = yuio.io.Task("Task")
            io_mocker.mark()
            with yuio.io.SuspendOutput():
                io_mocker.mark()
            io_mocker.mark()
            task.done()

    def test_task_finish_while_suspended(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "⣿ Task              ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                "> Task - done       ",
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            task = yuio.io.Task("Task")
            io_mocker.mark()
            with yuio.io.SuspendOutput():
                io_mocker.mark()
                task.done()
                io_mocker.mark()
