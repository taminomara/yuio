import io
import sys
import textwrap

import pytest

import yuio.io
import yuio.parse
import yuio.string
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _t

from .conftest import IOMocker, RcCompare


class TestSetup:
    @pytest.fixture(autouse=True)
    def setup_io_fresh(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io._IO_MANAGER", None)

        yield

        yuio.io.restore_streams()
        if yuio.io._IO_MANAGER is not None:
            yuio.io._IO_MANAGER.stop()
            yuio.io._IO_MANAGER = None

    def test_implicit(self, monkeypatch: pytest.MonkeyPatch):
        stdout = io.StringIO()
        monkeypatch.setattr("sys.stdout", stdout)

        stderr = io.StringIO()
        monkeypatch.setattr("sys.stderr", stderr)

        stdin = io.StringIO()
        monkeypatch.setattr("sys.stdin", stdin)

        assert yuio.io.get_term().ostream is stderr
        assert yuio.io.get_term().istream is stdin

        assert yuio.io.orig_stderr() is stderr
        assert sys.stderr is stderr
        assert sys.stdin is stdin
        assert not yuio.io.streams_wrapped()

        yuio.io.info("Foo bar!")

        assert stderr.getvalue() == "Foo bar!\n"

    def test_term(self, term):
        yuio.io.setup(term=term)
        assert yuio.io.get_term() is term
        assert isinstance(yuio.io.get_theme(), yuio.theme.DefaultTheme)

    def test_theme(self, term):
        theme = yuio.theme.DefaultTheme(term)
        yuio.io.setup(theme=theme)
        assert yuio.io.get_theme() is theme

    def test_theme_callable(self, term):
        n_called = 0
        current_theme = None
        current_term = None

        def theme(term):
            nonlocal n_called, current_theme, current_term
            n_called += 1
            current_theme = yuio.theme.Theme()
            current_term = term
            return current_theme

        yuio.io.setup(theme=theme)
        assert n_called == 1
        assert yuio.io.get_theme() is current_theme
        assert yuio.io.get_term() is current_term

        yuio.io.setup(theme=theme)
        assert n_called == 2
        assert yuio.io.get_theme() is current_theme
        assert yuio.io.get_term() is current_term

        yuio.io.setup(term=term)
        assert n_called == 3
        assert current_term is term
        assert yuio.io.get_theme() is current_theme
        assert yuio.io.get_term() is current_term

    def test_wrap_streams(self, monkeypatch: pytest.MonkeyPatch, ostream):
        monkeypatch.setattr("sys.stdout", ostream)
        monkeypatch.setattr("sys.stderr", ostream)

        yuio.io.setup(wrap_stdio=True)

        assert yuio.io.streams_wrapped()
        assert sys.stdout is not ostream
        assert getattr(sys.stdout, "_YuioOutputWrapper__wrapped") is ostream
        assert yuio.io.orig_stderr() is ostream
        assert sys.stderr is not ostream
        assert getattr(sys.stderr, "_YuioOutputWrapper__wrapped") is ostream
        assert yuio.io.orig_stdout() is ostream

        yuio.io.restore_streams()
        assert not yuio.io.streams_wrapped()
        assert sys.stdout is ostream
        assert sys.stderr is ostream
        assert yuio.io.orig_stdout() is ostream
        assert yuio.io.orig_stderr() is ostream

        yuio.io.restore_streams()
        assert not yuio.io.streams_wrapped()
        assert sys.stdout is ostream
        assert sys.stderr is ostream
        assert yuio.io.orig_stdout() is ostream
        assert yuio.io.orig_stderr() is ostream

    def test_wrap_streams_not_tty(self, monkeypatch: pytest.MonkeyPatch, ostream):
        monkeypatch.setattr(ostream, "isatty", lambda: False)
        monkeypatch.setattr("sys.stdout", ostream)
        monkeypatch.setattr("sys.stderr", ostream)

        yuio.io.setup(wrap_stdio=True)

        assert yuio.io.streams_wrapped()
        assert sys.stdout is ostream
        assert yuio.io.orig_stderr() is ostream
        assert sys.stderr is ostream
        assert yuio.io.orig_stdout() is ostream

        yuio.io.restore_streams()
        assert not yuio.io.streams_wrapped()
        assert sys.stdout is ostream
        assert sys.stderr is ostream
        assert yuio.io.orig_stdout() is ostream
        assert yuio.io.orig_stderr() is ostream

        yuio.io.restore_streams()
        assert not yuio.io.streams_wrapped()
        assert sys.stdout is ostream
        assert sys.stderr is ostream
        assert yuio.io.orig_stdout() is ostream
        assert yuio.io.orig_stderr() is ostream


MESSAGE_CASES = [
    (
        "info",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "warning",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "success",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "failure",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "failure_with_tb",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "error",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "error_with_tb",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "heading",
        ("Bar.",),
        {},
        [
            "                    ",
            "⣿ Bar.              ",
            "                    ",
        ],
    ),
    (
        "md",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "rst",
        ("Bar.",),
        {},
        [
            "Bar.                ",
        ],
    ),
    (
        "hl",
        ('{"foo": 10}',),
        {"syntax": "json"},
        [
            '{"foo": 10}         ',
        ],
    ),
    (
        "br",
        (),
        {},
        [
            "                    ",
        ],
    ),
    (
        "hr",
        (),
        {},
        [
            "────────────────────",
        ],
    ),
    (
        "raw",
        (yuio.string.ColorizedString("Bar."),),
        {},
        [
            "Bar.                ",
        ],
    ),
]


class TestMessage:
    @pytest.mark.parametrize(("meth", "args", "kwargs", "expected"), MESSAGE_CASES)
    def test_simple(self, io_mocker: IOMocker, meth, args, kwargs, expected):
        io_mocker.expect_screen(
            [
                "Foo.                ",
                *expected,
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            getattr(yuio.io, meth)(*args, **kwargs)

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
                "cccccccccccccccccccc",
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

    def test_failure(self, ostream: io.StringIO):
        yuio.io.failure("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
            ],
            [
                "RRRRRRRR            ",
            ],
        )

    def test_failure_with_tb(
        self, ostream: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "traceback.format_exception", lambda ty, val, tb: [f"{ty.__name__}: {val}"]
        )

        try:
            raise RuntimeError("something happened")
        except RuntimeError:
            yuio.io.failure_with_tb("foo bar!")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
                "  RuntimeError: some",
                "thing happened      ",
            ],
            [
                "RRRRRRRR            ",
                "                    ",
                "                    ",
            ],
        )

    def test_failure_with_tb_manual(
        self, ostream: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "traceback.format_exception", lambda ty, val, tb: [f"{ty.__name__}: {val}"]
        )

        try:
            raise RuntimeError("something happened")
        except RuntimeError as e:
            yuio.io.failure_with_tb(
                "foo bar!", exc_info=(TypeError, e, e.__traceback__)
            )
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
                "  TypeError: somethi",
                "ng happened         ",
            ],
            [
                "RRRRRRRR            ",
                "                    ",
                "                    ",
            ],
        )

    def test_failure_with_tb_manual_2(
        self, ostream: io.StringIO, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "traceback.format_exception", lambda ty, val, tb: [f"{ty.__name__}: {val}"]
        )

        try:
            raise RuntimeError("something happened")
        except RuntimeError as e:
            yuio.io.failure_with_tb("foo bar!", exc_info=e)
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "foo bar!            ",
                "  RuntimeError: some",
                "thing happened      ",
            ],
            [
                "RRRRRRRR            ",
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
        yuio.io.heading("foo bar 2!")
        yuio.io.heading("foo bar 3!", wrap=False)
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "⣿ foo bar!          ",
                "                    ",
                "⣿ foo bar 2!        ",
                "                    ",
                "⣿ foo bar 3!        ",
                "                    ",
            ],
            [
                "mm########          ",
                "                    ",
                "mm##########        ",
                "                    ",
                "mm##########        ",
                "                    ",
            ],
        )

    def test_md(self, ostream: io.StringIO):
        yuio.io.md("# Foo!\n\n- bar\n- baz")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "⣿ Foo!              ",
                "                    ",
                "•   bar             ",
                "•   baz             ",
            ],
            [
                "mmCCCC              ",
                "                    ",
                "mmmmccc             ",
                "mmmmccc             ",
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

    def test_hr(self, ostream: io.StringIO):
        yuio.io.hr()
        yuio.io.hr(weight=2)
        yuio.io.hr("foo")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                "────────────────────",
                "━━━━━━━━━━━━━━━━━━━━",
                "───────╴foo╶────────",
            ],
            [
                "mmmmmmmmmmmmmmmmmmmm",
                "mmmmmmmmmmmmmmmmmmmm",
                "mmmmmmmmcccmmmmmmmmm",
            ],
        )

    def test_hl(self, ostream):
        yuio.io.hl('{"foo": true}', syntax="json")
        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(
            [
                '{"foo": true}       ',
            ],
            [
                "ccccccccccccc       ",
            ],
        )

    def test_raw_err(self, term):
        with pytest.raises(
            TypeError, match=r"term, to_stdout, and to_stderr can't be given together"
        ):
            yuio.io.raw("asd", term=term, to_stdout=True, to_stderr=True)

        with pytest.raises(ValueError, match=r"invalid exc_info"):
            yuio.io.raw("asd", exc_info=(1, 2, 3, 4))  # type: ignore


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
                "▲ Input is required ",
                "f1 help             ",
                "                    ",
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

    def test_default_other_type(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Q?                  ",
                "> 10                ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default=10) == 10

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
                "> no                ",
                "  yes               ",
                "f1 help             ",
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
                "> no                ",
                "  yes               ",
                "f1 help             ",
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
                "Enter some numbers",
                parser=yuio.parse.List(yuio.parse.Int()),  # type: ignore
            ) == [123, 456]

    def test_secret(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter password:     ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("123 456")
        io_mocker.expect_screen(
            [
                "Enter password:     ",
                "> *******           ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "123 456"
            )

    def test_error_highlighting(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Enter some numbers: ",
                ">                   ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.text("123 xxx 456")
        io_mocker.key(yuio.widget.Key.ENTER)
        io_mocker.expect_screen(
            [
                "Enter some numbers: ",
                "> 123 xxx 456       ",
                "▲ Can't parse 'xxx' ",
                "as int              ",
                "f1 help             ",
            ],
            [
                "bbbbbbbbbbbbbbbbbbb ",
                "      RRR           ",
                "mrrrrrrrrrrrrrmmmmm ",
                "rrrmmm              ",
                "                    ",
            ],
        )
        io_mocker.key("g", ctrl=True)
        io_mocker.key("w", ctrl=True)
        io_mocker.expect_screen(
            [
                "Enter some numbers: ",
                "> 123  456          ",
                "f1 help             ",
                "                    ",
                "                    ",
            ],
            [
                "bbbbbbbbbbbbbbbbbbb ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.key(yuio.widget.Key.ENTER)

        with io_mocker.mock():
            assert yuio.io.ask[list[int]]("Enter some numbers") == [123, 456]


class TestAskNoColor:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.NONE,
            ostream_is_tty=True,
            istream_is_tty=True,
            is_unicode=True,
        )

    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Hello?            ",
            ],
        )
        io_mocker.expect_istream_readline("Hii~")

        with io_mocker.mock():
            assert yuio.io.ask("Hello?") == "Hii~"

    def test_empty(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Hello?            ",
            ],
        )
        io_mocker.expect_istream_readline("\n")
        io_mocker.expect_screen(
            [
                "> Hello?            ",
                "Input is required.  ",
                "> Hello?            ",
            ],
        )
        io_mocker.expect_istream_readline("Hii~\n")

        with io_mocker.mock():
            assert yuio.io.ask("Hello?") == "Hii~"

    def test_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> What's your deal? ",
            ],
        )
        io_mocker.expect_istream_readline("meow =^..^=\n")

        with io_mocker.mock():
            assert yuio.io.ask("What's your %s?", "deal") == "meow =^..^="

    def test_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Enter something:  ",
            ],
        )
        io_mocker.expect_istream_readline("123\n")

        with io_mocker.mock():
            assert yuio.io.ask("Enter something") == "123"

    def test_dont_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Enter something:  ",
            ],
        )
        io_mocker.expect_istream_readline("123\n")

        with io_mocker.mock():
            assert yuio.io.ask("Enter something:") == "123"

    def test_default(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q? [{default}]    ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default="{default}") == "{default}"

    def test_default_overridden(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q? [{default}]    ",
            ],
        )
        io_mocker.expect_istream_readline("foo!\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default="{default}") == "foo!"

    def test_default_optional(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q? [<none>]       ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default=None) is None

    def test_default_other_type(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q? [10]           ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q?", default=10) == 10

    def test_default_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q [{default}]:    ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q", default="{default}") == "{default}"

    def test_default_dont_add_colon(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q [{default}]:    ",
            ],
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q:", default="{default}") == "{default}"

    def test_input_description(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q (<text>):       ",
            ],
        )
        io_mocker.expect_istream_readline("123\n")

        with io_mocker.mock():
            assert yuio.io.ask("Q:", input_description="<text>") == "123"

    def test_default_description(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Q [<default>]:    ",
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
                "> Are you there? (  ",
                "  {yes|no})         ",
            ],
        )
        io_mocker.expect_istream_readline("what?\n")
        io_mocker.expect_screen(
            [
                "> Are you there? (  ",
                "  {yes|no}) what?   ",
                "Can't parse 'what?' ",
                "as bool, should be  ",
                "yes, no, true, or   ",
                "false               ",
                "> Are you there? (  ",
                "  {yes|no})         ",
            ],
        )
        io_mocker.expect_istream_readline("y\n")

        with io_mocker.mock():
            assert yuio.io.ask("Are you there?", parser=yuio.parse.Bool())

    def test_parser_hint(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Are you there? (  ",
                "  {yes|no})         ",
            ],
        )
        io_mocker.expect_istream_readline("what?\n")
        io_mocker.expect_screen(
            [
                "> Are you there? (  ",
                "  {yes|no}) what?   ",
                "Can't parse 'what?' ",
                "as bool, should be  ",
                "yes, no, true, or   ",
                "false               ",
                "> Are you there? (  ",
                "  {yes|no})         ",
            ],
        )
        io_mocker.expect_istream_readline("y\n")

        with io_mocker.mock():
            assert yuio.io.ask[bool]("Are you there?")

    def test_type_hint_and_parser(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Enter some numbers",
                "   (<int>[ <int>[   ",
                "  ...]]):           ",
            ],
        )
        io_mocker.expect_istream_readline("123 456\n")

        with io_mocker.mock():
            assert yuio.io.ask[bool](
                "Enter some numbers",
                parser=yuio.parse.List(yuio.parse.Int()),  # type: ignore
            ) == [123, 456]

    @pytest.mark.linux
    @pytest.mark.darwin
    def test_secret_fallback(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "Warning: Password   ",
                "input may be echoed.",
                "> Enter password:   ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.expect_istream_readline("123 456\n")

        with io_mocker.mock():
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "123 456"
            )

    @pytest.mark.linux
    @pytest.mark.darwin
    def test_secret_unix(
        self, io_mocker: IOMocker, istream, monkeypatch: pytest.MonkeyPatch
    ):
        import termios

        def fileno():
            return 123

        mode = orig_mode = [0, 0, termios.ECHO, 0, 0, 0, []]

        def tcgetattr(fd):
            assert fd == 123
            return mode[:]

        def tcsetattr(fd, flags, new_mode):
            assert fd == 123
            nonlocal mode
            mode = new_mode[:]

        monkeypatch.setattr(istream, "fileno", fileno)
        monkeypatch.setattr(termios, "tcgetattr", tcgetattr)
        monkeypatch.setattr(termios, "tcsetattr", tcsetattr)

        io_mocker.expect_screen(
            [
                "> Enter password:   ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.expect_eq(lambda: mode[3], 0)
        io_mocker.expect_istream_readline("123 456\n", echo=False)
        io_mocker.expect_mark()
        io_mocker.expect_eq(lambda: mode, orig_mode)
        io_mocker.expect_screen(
            [
                "> Enter password:   ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

        with io_mocker.mock():
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "123 456"
            )
            io_mocker.mark()

    @pytest.mark.linux
    @pytest.mark.darwin
    def test_secret_unix_fallback_if_termios_throws(
        self, io_mocker: IOMocker, istream, monkeypatch: pytest.MonkeyPatch
    ):
        import termios

        def fileno():
            return 123

        def tcgetattr(fd):
            assert fd == 123
            return [0, 0, termios.ECHO, 0, 0, 0, []]

        def tcsetattr(fd, flags, new_mode):
            assert fd == 123
            raise termios.error("error")

        monkeypatch.setattr(istream, "fileno", fileno)
        monkeypatch.setattr(termios, "tcgetattr", tcgetattr)
        monkeypatch.setattr(termios, "tcsetattr", tcsetattr)

        io_mocker.expect_screen(
            [
                "Warning: Password   ",
                "input may be echoed.",
                "> Enter password:   ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.expect_istream_readline("123 456\n", echo=False)

        with io_mocker.mock():
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "123 456"
            )

    @pytest.mark.linux
    @pytest.mark.darwin
    def test_secret_unix_raise_if_termios_throws_after_readline(
        self, io_mocker: IOMocker, istream, monkeypatch: pytest.MonkeyPatch
    ):
        import termios

        def fileno():
            return 123

        mode = orig_mode = [0, 0, termios.ECHO, 0, 0, 0, []]
        n_calls = 0

        def tcgetattr(fd):
            assert fd == 123
            return mode[:]

        def tcsetattr(fd, flags, new_mode):
            assert fd == 123
            nonlocal mode, n_calls
            mode = new_mode[:]
            if n_calls == 1:
                raise termios.error("error")
            n_calls += 1

        monkeypatch.setattr(istream, "fileno", fileno)
        monkeypatch.setattr(termios, "tcgetattr", tcgetattr)
        monkeypatch.setattr(termios, "tcsetattr", tcsetattr)

        io_mocker.expect_screen(
            [
                "> Enter password:   ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )
        io_mocker.expect_eq(lambda: mode[3], 0)
        io_mocker.expect_istream_readline("123 456\n", echo=False)

        with io_mocker.mock(), pytest.raises(termios.error, match=r"^error$"):
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "123 456"
            )

        assert mode == orig_mode

    @pytest.mark.windows
    def test_secret_windows(self, io_mocker: IOMocker, monkeypatch: pytest.MonkeyPatch):
        import msvcrt

        input_str = "X\b\b\basX\bd\0\0dsa\r\n"
        output_str = ""
        input_index = 0

        def getwch():
            nonlocal input_index
            assert input_index < len(input_str)
            c = input_str[input_index]
            input_index += 1
            return c

        def putwch(c):
            nonlocal output_str
            output_str += c

        monkeypatch.setattr(msvcrt, "getwch", getwch)
        monkeypatch.setattr(msvcrt, "putwch", putwch)

        io_mocker.expect_screen(
            [
                "> Enter password:   ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

        with io_mocker.mock():
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "asddsa"
            )

        assert output_str == "*\b \b***\b \b****\r\n"

    @pytest.mark.windows
    def test_secret_windows_keyboard_interrupt(
        self, io_mocker: IOMocker, monkeypatch: pytest.MonkeyPatch
    ):
        import msvcrt

        input_str = "abc\003"
        output_str = ""
        input_index = 0

        def getwch():
            nonlocal input_index
            assert input_index < len(input_str)
            c = input_str[input_index]
            input_index += 1
            return c

        def putwch(c):
            nonlocal output_str
            output_str += c

        monkeypatch.setattr(msvcrt, "getwch", getwch)
        monkeypatch.setattr(msvcrt, "putwch", putwch)

        io_mocker.expect_screen(
            [
                "> Enter password:   ",
                "                    ",
                "                    ",
                "                    ",
                "                    ",
            ],
        )

        with io_mocker.mock(), pytest.raises(KeyboardInterrupt):
            assert (
                yuio.io.ask[yuio.parse.SecretString]("Enter password").data == "asddsa"
            )

        assert output_str == "***"


class TestAskNonInteractive:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        istream.readable = lambda: False
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            ostream_is_tty=False,
            istream_is_tty=False,
            is_unicode=True,
        )

    def test_default(self, io_mocker: IOMocker):
        with io_mocker.mock():
            assert yuio.io.ask("Meow?", default="Meow!") == "Meow!"

    def test_default_non_interactive(self, io_mocker: IOMocker):
        with io_mocker.mock():
            assert (
                yuio.io.ask("Meow?", default="Meow!", default_non_interactive="Boop!")
                == "Boop!"
            )

    def test_no_default(self, io_mocker: IOMocker):
        with io_mocker.mock():
            with pytest.raises(
                yuio.io.UserIoError, match=r"non-interactive environment"
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


class TestWaitForUserNoColor:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.NONE,
            ostream_is_tty=True,
            istream_is_tty=True,
            is_unicode=True,
        )

    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Press enter to    ",
                "  continue          ",
            ]
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            yuio.io.wait_for_user()

    def test_add_space(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Press enter to    ",
                "  continue          ",
            ]
        )
        io_mocker.expect_istream_readline(".\n")
        io_mocker.expect_screen(
            [
                "> Press enter to    ",
                "  continue .        ",
            ]
        )

        with io_mocker.mock():
            yuio.io.wait_for_user()

    def test_strip_end(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Ends with spaces  ",
            ]
        )
        io_mocker.expect_istream_readline(".\n")
        io_mocker.expect_screen(
            [
                "> Ends with spaces .",
            ]
        )

        with io_mocker.mock():
            yuio.io.wait_for_user("Ends with spaces   ")

    def test_msg(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Slam that Enter   ",
                "  button!           ",
            ]
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            yuio.io.wait_for_user("Slam that Enter button!")

    def test_msg_format(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "> Slam that Enter   ",
                "  button!           ",
            ]
        )
        io_mocker.expect_istream_readline("\n")

        with io_mocker.mock():
            yuio.io.wait_for_user("Slam that %s button!", "Enter")


class TestWaitForUserNonInteractive:
    @pytest.fixture
    def term(self, ostream: io.StringIO, istream: _t.TextIO) -> yuio.term.Term:
        istream.readable = lambda: False
        return yuio.term.Term(
            ostream,
            istream,
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            ostream_is_tty=False,
            istream_is_tty=False,
            is_unicode=True,
        )

    def test_wait(self, io_mocker: IOMocker):
        io_mocker.expect_screen([])
        with io_mocker.mock():
            yuio.io.wait_for_user()


class TestDetectEditor:
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.delenv("VISUAL", raising=False)
        return

    @pytest.mark.linux
    @pytest.mark.darwin
    def test_env_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("EDITOR", "foobar")
        assert yuio.io.detect_editor() == "foobar"

    @pytest.mark.linux
    @pytest.mark.darwin
    def test_env_visual(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("EDITOR", "foobar")
        monkeypatch.setenv("VISUAL", "visual")
        assert yuio.io.detect_editor() == "visual"

    @pytest.mark.windows
    def test_env_windows(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("EDITOR", "foobar")
        monkeypatch.setenv("VISUAL", "visual")
        monkeypatch.setattr(
            "shutil.which", lambda exc: exc if exc == "notepad" else None
        )
        assert yuio.io.detect_editor() == "notepad"

    @pytest.mark.parametrize(
        "editor",
        [
            "vi",
            "nano",
            "notepad",
        ],
    )
    def test_which(self, editor: str, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("shutil.which", lambda exc: exc if exc == editor else None)
        assert yuio.io.detect_editor() == editor

    def test_fail(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("shutil.which", lambda exc: None)
        assert yuio.io.detect_editor() is None

    def test_fallbacks(self, monkeypatch: pytest.MonkeyPatch):
        seen = []
        monkeypatch.setattr("shutil.which", lambda exc: (seen.append(exc), None)[1])
        assert yuio.io.detect_editor(fallbacks=["fallback 1", "fallback 2"]) is None
        assert seen == ["fallback 1", "fallback 2"]


@pytest.mark.linux
@pytest.mark.darwin
class TestEditUnix:
    _EDITOR = "echo ' edited' >>"

    def test_simple(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: self._EDITOR)
        assert yuio.io.edit("foobar") == "foobar edited\n"

    def test_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: None)
        assert yuio.io.edit("foobar", editor=self._EDITOR) == "foobar edited\n"

    def test_editor_error(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: "exit 1; cat")
        with pytest.raises(yuio.io.UserIoError, match=r"returned exit code 1"):
            assert yuio.io.edit("foobar")

    def test_editor_signal(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: "kill -9 $$; cat")
        with pytest.raises(yuio.io.UserIoError, match=r"died with SIGKILL"):
            assert yuio.io.edit("foobar")

    def test_no_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: None)
        with pytest.raises(yuio.io.UserIoError, match=r"Can't find a usable editor"):
            assert yuio.io.edit("foobar")

    def test_comments(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: self._EDITOR)
        assert (
            yuio.io.edit("# foo\n  # bar\nbaz #", comment_marker="#")
            == "baz # edited\n"
        )
        assert yuio.io.edit("foo\n#", comment_marker="#") == "foo\n"

    def test_comments_long_marker(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: self._EDITOR)
        assert (
            yuio.io.edit("// foo\n  # bar\nbaz //", comment_marker="//")
            == "  # bar\nbaz // edited\n"
        )
        assert yuio.io.edit("foo\n//", comment_marker="//") == "foo\n"

    def test_comments_long_marker_special_symbols(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: self._EDITOR)
        assert yuio.io.edit("a\nb\n[ab]", comment_marker="[ab]") == "a\nb\n"

    def test_file_removed(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: "rm")
        with pytest.raises(yuio.io.UserIoError, match=r"can't read back edited file"):
            yuio.io.edit("foo")


@pytest.mark.linux
class TestEditLinux:
    def test_editor_unknown_signal(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: "kill -60 $$; cat")
        with pytest.raises(yuio.io.UserIoError, match=r"died with unknown signal -60"):
            assert yuio.io.edit("foobar")


@pytest.mark.windows
class TestEditWindows:
    SCRIPT = textwrap.dedent(
        """
        @echo off
        echo Edited content> %1
        """
    )

    def test_edit(self, tmp_path, monkeypatch):
        script = tmp_path / "edit.bat"
        script.write_text(self.SCRIPT)

        monkeypatch.setattr("yuio.io.detect_editor", lambda _: str(script))
        assert yuio.io.edit("foo").strip() == "Edited content"

    def test_no_editor(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("yuio.io.detect_editor", lambda _: None)
        with pytest.raises(yuio.io.UserIoError, match=r"Can't find a usable editor"):
            assert yuio.io.edit("foobar")

    def test_editor_not_found(self):
        with pytest.raises(yuio.io.UserIoError, match=r"no such file or directory"):
            yuio.io.edit("foo", editor="/foo/bar")


class TestTask:
    @pytest.fixture
    def width(self):
        return 40

    def test_simple(self, io_mocker: IOMocker):
        io_mocker.expect_screen(
            [
                "⣿ task                                  ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen([])

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
        io_mocker.expect_screen([])

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
        io_mocker.expect_screen([])

        with io_mocker.mock():
            with pytest.raises(RuntimeError, match=r"eh..."):
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
        io_mocker.expect_screen([])

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
        io_mocker.expect_screen([])

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
        io_mocker.expect_screen([])

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
        io_mocker.expect_screen([])

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
        io_mocker.expect_screen([])

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
        ("args", "kwargs", "comment", "expected"),
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
        ("args", "kwargs", "expected"),
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
        ("args", "kwargs", "expected"),
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
                    "■■□□□ task - 500.00uV/1.00mV            ",
                ],
            ),
            (
                (0.00050, 0.001001),
                {"ndigits": 4},
                [
                    "■■□□□ task - 500.0000u/1.0010m          ",
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
        ("kwargs", "expected_format"),
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
        io_mocker.expect_screen([])

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
                "■■□□□ T1 - 2/5                          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "bar                                     ",
                "■■□□□ T1 - 2/5                          ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "bar                                     ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
                "bar                                     ",
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
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "foo                                     ",
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
        theme.set_msg_decoration_unicode("progress_bar/start_symbol", "[")
        theme.set_msg_decoration_unicode("progress_bar/end_symbol", "]")
        theme.set_msg_decoration_unicode("progress_bar/done_symbol", ">")
        theme.set_msg_decoration_unicode("progress_bar/pending_symbol", ".")
        theme.set_msg_decoration_unicode("progress_bar/transition_pattern", "")
        theme.progress_bar_width = 17

        io_mocker.expect_screen(
            [
                "[>>>>>>.........] Task - 40.00%         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "[>>>>>>.........] Task - 41.00%         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "[>>>>>>>........] Task - 45.00%         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "[>>>>>>>>.......] Task - 50.00%         ",
            ]
        )
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("Task") as task:
                task.progress(0.40)
                io_mocker.mark()
                task.progress(0.41)
                io_mocker.mark()
                task.progress(0.45)
                io_mocker.mark()
                task.progress(0.50)
                io_mocker.mark()

    def test_progressbar_decoration_transition(
        self, theme: yuio.theme.Theme, io_mocker: IOMocker
    ):
        theme.set_msg_decoration_unicode("progress_bar/start_symbol", "[")
        theme.set_msg_decoration_unicode("progress_bar/end_symbol", "]")
        theme.set_msg_decoration_unicode("progress_bar/done_symbol", ">")
        theme.set_msg_decoration_unicode("progress_bar/pending_symbol", ".")
        theme.set_msg_decoration_unicode(
            "progress_bar/transition_pattern", "9876543210"
        )
        theme.progress_bar_width = 17

        io_mocker.expect_screen(
            [
                "[>>>>>>0........] Task - 40.00%         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "[>>>>>>2........] Task - 41.00%         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "[>>>>>>8........] Task - 45.00%         ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "[>>>>>>>5.......] Task - 50.00%         ",
            ]
        )
        io_mocker.expect_mark()

        with io_mocker.mock():
            with yuio.io.Task("Task") as task:
                task.progress(0.40)
                io_mocker.mark()
                task.progress(0.41)
                io_mocker.mark()
                task.progress(0.45)
                io_mocker.mark()
                task.progress(0.50)
                io_mocker.mark()

    @pytest.mark.parametrize(
        ("tasks", "expected", "height"),
        [
            (
                [
                    ("T1", 1, None, []),
                    ("T2", 1, None, []),
                    ("T3", 1, None, []),
                    ("T4", 1, None, []),
                    ("T5", 1, None, []),
                ],
                [
                    "+5 more                                 ",
                ],
                1,
            ),
            (
                [
                    ("T1", 1, None, []),
                    ("T2", 1, None, []),
                    ("T3", 1, None, []),
                    ("T4", 1, None, []),
                    ("T5", 1, None, []),
                ],
                [
                    "+2 more                                 ",
                    "⣿ T3                                    ",
                    "⣿ T4                                    ",
                    "⣿ T5                                    ",
                ],
                4,
            ),
            (
                [
                    ("T1", None, None, []),
                    ("T2", None, None, []),
                    ("T3", None, yuio.io.Task.Status.DONE, []),
                    ("T4", None, yuio.io.Task.Status.DONE, []),
                    ("T5", None, None, []),
                ],
                [
                    "⣿ T1                                    ",
                    "⣿ T2                                    ",
                    "+2 more                                 ",
                    "⣿ T5                                    ",
                ],
                4,
            ),
            (
                [
                    ("T1", 2, None, []),
                    ("T2", 1, None, []),
                    ("T3", 1, None, []),
                    ("T4", 1, None, []),
                    ("T5", 1, None, []),
                ],
                [
                    "⣿ T1                                    ",
                    "+2 more                                 ",
                    "⣿ T4                                    ",
                    "⣿ T5                                    ",
                ],
                4,
            ),
            (
                [
                    ("T1", 2, None, []),
                    ("T2", 1, None, []),
                    ("T3", 1, None, []),
                    ("T4", 2, None, []),
                    ("T5", 1, None, []),
                    ("T6", 1, None, []),
                ],
                [
                    "⣿ T1                                    ",
                    "+2 more                                 ",
                    "⣿ T4                                    ",
                    "+2 more                                 ",
                ],
                4,
            ),
            (
                [
                    ("T1", 2, None, []),
                    ("T2", 1, None, []),
                    ("T3", 1, None, []),
                    ("T4", 2, None, []),
                    ("T5", 1, None, []),
                    ("T6", 1, None, []),
                ],
                [
                    "+3 more                                 ",
                    "⣿ T4                                    ",
                    "+2 more                                 ",
                ],
                3,
            ),
            (
                [
                    (
                        "T1",
                        1,
                        None,
                        [
                            (
                                "T2",
                                1,
                                None,
                                [
                                    ("T3", 1, None, []),
                                    ("T4", 1, None, []),
                                ],
                            ),
                        ],
                    ),
                ],
                [
                    "⣿ T1                                    ",
                    "  ⣿ T2                                  ",
                    "    +2 more                             ",
                ],
                3,
            ),
            (
                [
                    (
                        "T1",
                        1,
                        None,
                        [
                            (
                                "T2",
                                1,
                                None,
                                [
                                    ("T3", 1, None, []),
                                    ("T4", 1, None, []),
                                ],
                            ),
                        ],
                    ),
                ],
                [
                    "⣿ T1                                    ",
                    "  +3 more                               ",
                ],
                2,
            ),
            (
                [
                    (
                        "T1",
                        1,
                        None,
                        [
                            (
                                "T2",
                                1,
                                None,
                                [
                                    ("T3", 1, None, []),
                                    ("T4", 1, None, []),
                                ],
                            ),
                            ("T5", 1, None, []),
                        ],
                    ),
                ],
                [
                    "⣿ T1                                    ",
                    "  ⣿ T2                                  ",
                    "    +2 more                             ",
                    "  ⣿ T5                                  ",
                ],
                4,
            ),
        ],
    )
    def test_tasks_collapsed(self, tasks, expected, io_mocker):
        def create_task(msg, priority, status, children, parent=None):
            task = yuio.io.Task(
                msg, parent=parent, initial_status=status or yuio.io.Task.Status.RUNNING
            )
            if priority is not None:
                task._get_priority = lambda: priority
            for msg, priority, status, children in children:
                create_task(msg, priority, status, children, parent=task)

        io_mocker.expect_screen(expected)
        io_mocker.expect_mark()
        with io_mocker.mock():
            for msg, priority, status, children in tasks:
                create_task(msg, priority, status, children)
            io_mocker.mark()


class TestTaskBackground:
    is_foreground = False

    @pytest.fixture
    def width(self):
        return 40

    @pytest.fixture(autouse=True)
    def setup_is_foreground(self, monkeypatch: pytest.MonkeyPatch):
        def is_foreground(*_, **__):
            return self.is_foreground

        monkeypatch.setattr("yuio.term._is_foreground", is_foreground)

    def test_background(self, io_mocker):
        io_mocker.expect_screen(
            [
                "> task - running                        ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.progress(0.5)
                io_mocker.mark()

    def test_background_switch(self, io_mocker):
        io_mocker.expect_screen(
            [
                "> task - running                        ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "■■□□□ task - 50.00%                     ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "■■□□□ task - 50.00%                     ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "■■□□□ task - 50.00%                     ",
                "> task - done                           ",
            ]
        )

        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                task.progress(0.5)
                io_mocker.mark()
                self.is_foreground = True
                task.progress(0.5)
                io_mocker.mark()
                self.is_foreground = False
                task.progress(0.5)
                io_mocker.mark()

    def test_background_switch_with_subtasks(self, io_mocker):
        io_mocker.expect_screen(
            [
                "> task - running                        ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "> a - running                           ",
                "> b - running                           ",
                "> c - running                           ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "> a - running                           ",
                "> b - running                           ",
                "> c - running                           ",
                "⣿ task                                  ",
                "  ⣿ a - comment                         ",
                "  ⣿ b                                   ",
                "  ⣿ c                                   ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "> a - running                           ",
                "> b - running                           ",
                "> c - running                           ",
                "⣿ task                                  ",
                "  ⣿ a - done                            ",
                "  ⣿ b                                   ",
                "  ⣿ c                                   ",
                "> b - done                              ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "> a - running                           ",
                "> b - running                           ",
                "> c - running                           ",
                "⣿ task                                  ",
                "  ⣿ a - done                            ",
                "  ⣿ b                                   ",
                "  ⣿ c                                   ",
                "> b - done                              ",
                "⣿ task                                  ",
                "  ⣿ a - done                            ",
                "  ⣿ b - done                            ",
                "  ⣿ c - done                            ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "> task - running                        ",
                "> a - running                           ",
                "> b - running                           ",
                "> c - running                           ",
                "⣿ task                                  ",
                "  ⣿ a - done                            ",
                "  ⣿ b                                   ",
                "  ⣿ c                                   ",
                "> b - done                              ",
                "⣿ task                                  ",
                "  ⣿ a - done                            ",
                "  ⣿ b - done                            ",
                "  ⣿ c - done                            ",
                "> task - done                           ",
            ]
        )
        with io_mocker.mock():
            with yuio.io.Task("task") as task:
                io_mocker.mark()
                a = task.subtask("a")
                b = task.subtask("b")
                c = task.subtask("c")
                io_mocker.mark()
                self.is_foreground = True
                a.comment("comment")
                io_mocker.mark()
                a.done()
                self.is_foreground = False
                b.done()
                io_mocker.mark()
                self.is_foreground = True
                c.done()
                io_mocker.mark()
                self.is_foreground = False


class TestMessageChannel:
    @pytest.mark.parametrize("enabled", [True, False])
    @pytest.mark.parametrize(("meth", "args", "kwargs", "expected"), MESSAGE_CASES)
    def test_enable_disable(
        self, io_mocker: IOMocker, meth, args, kwargs, enabled, expected
    ):
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )
        io_mocker.expect_mark()
        io_mocker.expect_screen(
            [
                "Foo.                ",
                *(expected if enabled else []),
            ]
        )

        with io_mocker.mock():
            yuio.io.info("Foo.")
            ch = yuio.io.MessageChannel()
            ch.enabled = enabled
            io_mocker.mark()
            getattr(ch, meth)(*args, **kwargs)

    @pytest.mark.parametrize(("meth", "args", "kwargs", "expected"), MESSAGE_CASES)
    def test_redirect(self, io_mocker: IOMocker, meth, args, kwargs, expected, width):
        io_mocker.expect_screen(
            [
                "Foo.                ",
            ]
        )

        ostream = io.StringIO()
        new_term = yuio.term.Term(ostream, ostream, is_unicode=True)

        with io_mocker.mock():
            yuio.io.info("Foo.")
            ch = yuio.io.MessageChannel(term=new_term, width=width)
            getattr(ch, meth)(*args, **kwargs)

        assert RcCompare.from_commands(ostream.getvalue()) == RcCompare(expected)


class TestSuspendOutput:
    @pytest.mark.parametrize(("meth", "args", "kwargs", "expected"), MESSAGE_CASES)
    def test_simple(self, io_mocker: IOMocker, meth, args, kwargs, expected):
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
                getattr(yuio.io, meth)(*args, **kwargs)
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
        ("meth", "args", "expected"),
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
                (yuio.string.ColorizedString("Bar.\n"),),
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


class TestLog:
    @pytest.fixture(autouse=True)
    def setup_logger(self):
        import logging

        self.logger = logging.getLogger("yuio.test.test_log")
        self.logger.setLevel(logging.DEBUG)
        handler = yuio.io.Handler()
        self.logger.addHandler(handler)

        yield

        self.logger.removeHandler(handler)

    def test_simple(self, ostream: io.StringIO):
        self.logger.debug("debug")
        self.logger.info("info")
        self.logger.warning("warning")
        self.logger.error("error")
        self.logger.critical("critical")

        value = ostream.getvalue()
        assert "yuio.test.test_log DEBUG debug" in value
        assert "yuio.test.test_log INFO info" in value
        assert "yuio.test.test_log WARNING warning" in value
        assert "yuio.test.test_log ERROR error" in value
        assert "yuio.test.test_log CRITICAL critical" in value

    def test_tb(self, ostream: io.StringIO):
        self.logger.debug("debug")
        try:
            raise RuntimeError("oh no!")
        except RuntimeError:
            self.logger.exception("something went wrong")

        value = ostream.getvalue()
        assert "something went wrong" in value
        assert "oh no!" in value

    def test_stack(self, ostream: io.StringIO):
        self.logger.info("hi there!", stack_info=True)

        value = ostream.getvalue()
        assert "hi there!" in value
        assert 'self.logger.info("hi there!", stack_info=True)' in value

    def test_colors(self, theme: yuio.theme.Theme, io_mocker: IOMocker):
        self.logger.handlers[0].setFormatter(
            yuio.io.Formatter(
                "%(name)s %(levelname)s %(add_data)d %(add_data_2)s %(colMessage)s",
                defaults={
                    "add_data": 10,
                    "add_data_2": "asd",
                },
            )
        )
        theme.set_color("log", "yellow")
        theme.set_color("log:info", "cyan")
        theme.set_color("log/add_data:info", "red")
        theme.set_color("log/name:info", "green")
        theme.set_color("log/levelname:info", "blue")
        theme.set_color("log/colMessage:info", "magenta")

        io_mocker.expect_screen(
            [
                "yuio.test.test_log I",
                "NFO 10 asd msg arg  ",
                "yuio.test.test_log E",
                "RROR 10 asd m2 `arg`",
            ],
            [
                "ggggggggggggggggggcb",
                "bbbcrrcccccmmmmmmm  ",
                "yyyyyyyyyyyyyyyyyyyy",
                "yyyyyyyyyyyyyyyyYYYy",
            ],
        )

        with io_mocker.mock():
            self.logger.info("msg %s", "arg")
            self.logger.error(
                "m2 `%s`", yuio.io.WithBaseColor("arg", base_color="bold")
            )
