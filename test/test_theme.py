import dataclasses
import pathlib
import textwrap
import warnings

import pytest

import yuio.color
import yuio.term
import yuio.theme


class TestColors:
    def test_get_color(self, theme):
        assert theme.get_color("code") == yuio.color.Color.FORE_MAGENTA
        assert theme.get_color("note") == yuio.color.Color.FORE_CYAN
        assert theme.get_color("bold") == yuio.color.Color.STYLE_BOLD
        assert theme.get_color("b") == yuio.color.Color.STYLE_BOLD
        assert theme.get_color("dim") == yuio.color.Color.STYLE_DIM
        assert theme.get_color("d") == yuio.color.Color.STYLE_DIM
        assert theme.get_color("normal") == yuio.color.Color.FORE_NORMAL
        assert theme.get_color("red") == yuio.color.Color.FORE_RED
        assert theme.get_color("green") == yuio.color.Color.FORE_GREEN
        assert theme.get_color("yellow") == yuio.color.Color.FORE_YELLOW
        assert theme.get_color("blue") == yuio.color.Color.FORE_BLUE
        assert theme.get_color("magenta") == yuio.color.Color.FORE_MAGENTA
        assert theme.get_color("cyan") == yuio.color.Color.FORE_CYAN
        assert theme.get_color("#ff0000") == yuio.color.Color(
            fore=yuio.color.ColorValue.from_rgb(0xFF, 0x00, 0x00)
        )
        assert theme.get_color("bg#ff0000") == yuio.color.Color(
            back=yuio.color.ColorValue.from_rgb(0xFF, 0x00, 0x00)
        )
        assert theme.get_color("#00ff00 bg#ff0000") == yuio.color.Color(
            fore=yuio.color.ColorValue.from_rgb(0x00, 0xFF, 0x00),
            back=yuio.color.ColorValue.from_rgb(0xFF, 0x00, 0x00),
        )
        with pytest.warns(yuio.theme.ThemeWarning, match=r"#ffxxyy"):
            assert theme.get_color("#ffxxyy") == yuio.color.Color.NONE
        with pytest.warns(yuio.theme.ThemeWarning, match=r"bg#ffxxyy"):
            assert theme.get_color("bg#ffxxyy") == yuio.color.Color.NONE

    def test_to_color(self, theme):
        assert theme.to_color(None) == yuio.color.Color.NONE
        assert theme.to_color("blue") == yuio.color.Color.FORE_BLUE
        assert (
            theme.to_color(yuio.color.Color.FORE_MAGENTA)
            == yuio.color.Color.FORE_MAGENTA
        )

    def test_color_paths(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.color.Color.STYLE_BOLD,
                "x/y": yuio.color.Color.FORE_RED,
                "x/z": yuio.color.Color.FORE_GREEN,
                "y/y": yuio.color.Color.FORE_BLUE,
            }

        a = A()

        assert a.get_color("x") == yuio.color.Color.STYLE_BOLD
        assert (
            a.get_color("x/y")
            == yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_RED
        )
        assert (
            a.get_color("x/z")
            == yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_GREEN
        )
        assert a.get_color("y/y") == yuio.color.Color.FORE_BLUE

    def test_color_redirect(self):
        class A(yuio.theme.Theme):
            colors = {
                "t_r": yuio.color.Color.FORE_RED,
                "t_g": yuio.color.Color.FORE_GREEN,
                "t_b": yuio.color.Color.STYLE_BOLD,
                "t_d": yuio.color.Color.STYLE_DIM,
                "b": yuio.color.Color.BACK_CYAN,
                "x": "t_b",
                "x/y": "t_r",
                "y": "t_d",
                "y/y": "x/y",
                "z": "x/y y/y b",
            }

        a = A()

        assert a.get_color("x") == yuio.color.Color.STYLE_BOLD
        assert (
            a.get_color("x/y")
            == yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_RED
        )
        assert a.get_color("y") == yuio.color.Color.STYLE_DIM
        assert (
            a.get_color("y/y")
            == yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.FORE_RED
        )
        assert (
            a.get_color("z")
            == yuio.color.Color.STYLE_DIM
            | yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.FORE_RED
            | yuio.color.Color.BACK_CYAN
        )

    def test_color_ctx(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.color.Color.STYLE_BOLD,
                "x:y": yuio.color.Color.FORE_RED,
                "x:y/z": yuio.color.Color.STYLE_DIM,
                "x:a": yuio.color.Color.FORE_GREEN,
                "q/q": yuio.color.Color.FORE_BLUE,
            }

        a = A()

        assert a.get_color("x") == yuio.color.Color.STYLE_BOLD
        assert (
            a.get_color("x:y")
            == yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_RED
        )
        assert (
            a.get_color("x:a")
            == yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_GREEN
        )
        assert (
            a.get_color("x/a/q:y")
            == yuio.color.Color.STYLE_BOLD | yuio.color.Color.FORE_RED
        )
        assert (
            a.get_color("x:y/z")
            == yuio.color.Color.STYLE_BOLD
            | yuio.color.Color.FORE_RED
            | yuio.color.Color.STYLE_DIM
        )
        assert a.get_color("q/q") == yuio.color.Color.FORE_BLUE
        assert a.get_color("q/q:y") == yuio.color.Color.FORE_BLUE


class TestInheritance:
    def test_simple_inheritance(self):
        class A(yuio.theme.Theme):
            colors = {
                "t_a": yuio.color.Color.FORE_RED,
                "t_ab": yuio.color.Color.FORE_GREEN,
                "t_abc": yuio.color.Color.FORE_BLUE,
            }

        class B(yuio.theme.Theme):
            colors = {
                "t_b": yuio.color.Color.FORE_CYAN,
                "t_ab": yuio.color.Color.FORE_MAGENTA,
                "t_abc": yuio.color.Color.FORE_YELLOW,
            }

        class C(A, B):
            colors = {
                "t_c": yuio.color.Color.FORE_BLACK,
                "t_abc": yuio.color.Color.FORE_WHITE,
            }

        c = C()

        assert C.colors["t_a"] == yuio.color.Color.FORE_RED
        assert C.colors["t_b"] == yuio.color.Color.FORE_CYAN
        assert C.colors["t_c"] == yuio.color.Color.FORE_BLACK
        assert C.colors["t_ab"] == yuio.color.Color.FORE_GREEN
        assert C.colors["t_abc"] == yuio.color.Color.FORE_WHITE

        assert c.get_color("t_a") == yuio.color.Color.FORE_RED
        assert c.get_color("t_b") == yuio.color.Color.FORE_CYAN
        assert c.get_color("t_c") == yuio.color.Color.FORE_BLACK
        assert c.get_color("t_ab") == yuio.color.Color.FORE_GREEN
        assert c.get_color("t_abc") == yuio.color.Color.FORE_WHITE

    def test_color_overrides(self):
        class A(yuio.theme.Theme):
            colors = {
                "t_a": yuio.color.Color.FORE_RED,
                "t_b": yuio.color.Color.FORE_GREEN,
                "t_b_2": yuio.color.Color.FORE_MAGENTA,
            }

            def __init__(self):
                super().__init__()

                self._set_color_if_not_overridden("t_a", yuio.color.Color.BACK_RED)
                self._set_color_if_not_overridden("t_b", yuio.color.Color.BACK_GREEN)
                self.set_color("t_b_2", yuio.color.Color.BACK_MAGENTA)

        class B(A):
            colors = {
                "t_b": yuio.color.Color.FORE_CYAN,
                "t_b_2": yuio.color.Color.FORE_CYAN,
            }

        a = A()
        b = B()

        assert A.colors["t_a"] == yuio.color.Color.FORE_RED
        assert A.colors["t_b"] == yuio.color.Color.FORE_GREEN
        assert A.colors["t_b_2"] == yuio.color.Color.FORE_MAGENTA

        assert a.get_color("t_a") == yuio.color.Color.BACK_RED
        assert a.get_color("t_b") == yuio.color.Color.BACK_GREEN
        assert a.get_color("t_b_2") == yuio.color.Color.BACK_MAGENTA

        assert B.colors["t_a"] == yuio.color.Color.FORE_RED
        assert B.colors["t_b"] == yuio.color.Color.FORE_CYAN
        assert B.colors["t_b_2"] == yuio.color.Color.FORE_CYAN

        assert b.get_color("t_a") == yuio.color.Color.BACK_RED
        assert b.get_color("t_b") == yuio.color.Color.FORE_CYAN
        assert b.get_color("t_b_2") == yuio.color.Color.BACK_MAGENTA

    def test_decoration_overrides(self):
        class A(yuio.theme.Theme):
            msg_decorations = {
                "t_a": "a",
                "t_b": "a",
                "t_b_2": "a",
            }

            def __init__(self):
                super().__init__()

                self._set_msg_decoration_if_not_overridden("t_a", "a2")
                self._set_msg_decoration_if_not_overridden("t_b", "a2")
                self.set_msg_decoration("t_b_2", "a2")

        class B(A):
            msg_decorations = {
                "t_b": "b",
                "t_b_2": "b",
            }

        a = A()
        b = B()

        assert A.msg_decorations["t_a"] == "a"
        assert A.msg_decorations["t_b"] == "a"
        assert A.msg_decorations["t_b_2"] == "a"

        assert a.msg_decorations["t_a"] == "a2"
        assert a.msg_decorations["t_b"] == "a2"
        assert a.msg_decorations["t_b_2"] == "a2"

        assert B.msg_decorations["t_a"] == "a"
        assert B.msg_decorations["t_b"] == "b"
        assert B.msg_decorations["t_b_2"] == "b"

        assert b.msg_decorations["t_a"] == "a2"
        assert b.msg_decorations["t_b"] == "b"
        assert b.msg_decorations["t_b_2"] == "a2"


class TestBrokenTheme:
    class RecursiveTheme(yuio.theme.Theme):
        colors = {
            "a": "b",
            "b": "c",
            "c": "a",
        }

    class ThemeEmptyKey(yuio.theme.Theme):
        colors = {
            "": "bold",
        }

    class ThemeEmptyValue(yuio.theme.Theme):
        colors = {
            "bold": "",
        }

    def test_recursion(self):
        theme = self.RecursiveTheme()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", yuio.theme.RecursiveThemeWarning)
            assert theme.get_color("a") == yuio.color.Color.NONE

    def test_warnings(self):
        theme = self.RecursiveTheme()
        with warnings.catch_warnings():
            warnings.simplefilter("error", yuio.theme.RecursiveThemeWarning)
            with pytest.raises(yuio.theme.RecursiveThemeWarning):
                theme.get_color("a")

    def test_check(self):
        theme = self.RecursiveTheme()
        with pytest.raises(yuio.theme.RecursiveThemeWarning):
            theme.check()

    def test_empty_key(self):
        theme = self.ThemeEmptyKey()
        with pytest.warns(
            yuio.theme.ThemeWarning, match=r"colors map contains an empty key"
        ):
            theme.check()

    def test_empty_value(self):
        theme = self.ThemeEmptyValue()
        with pytest.warns(
            yuio.theme.ThemeWarning, match=r"color value for path 'bold' is empty"
        ):
            theme.check()


class TestSetAttrs:
    def test_set_color(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.color.Color.STYLE_BOLD,
            }

        a = A()

        assert a.get_color("x") == yuio.color.Color.STYLE_BOLD
        assert a.get_color("x/y") == yuio.color.Color.STYLE_BOLD
        assert a.get_color("z") == yuio.color.Color.NONE

        a.set_color("x", yuio.color.Color.FORE_RED)
        a.set_color("z", yuio.color.Color.FORE_BLUE)

        assert a.get_color("x") == yuio.color.Color.FORE_RED
        assert a.get_color("x/y") == yuio.color.Color.FORE_RED
        assert a.get_color("z") == yuio.color.Color.FORE_BLUE

    def test_set_color_if_not_overridden(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.color.Color.STYLE_BOLD,
            }

        a = A()

        with pytest.raises(RuntimeError):
            a._set_color_if_not_overridden("x", yuio.color.Color.FORE_RED)

    def test_set_msg_decoration(self):
        class A(yuio.theme.Theme):
            msg_decorations = {
                "x": "a",
            }

        a = A()

        assert a.msg_decorations["x"] == "a"

        a.set_msg_decoration("x", "b")

        assert a.msg_decorations["x"] == "b"

    def test_set_msg_decoration_if_not_overridden(self):
        class A(yuio.theme.Theme):
            msg_decorations = {
                "x": "a",
            }

        a = A()

        with pytest.raises(RuntimeError):
            a._set_msg_decoration_if_not_overridden("x", "b")


terminal_theme_dark = yuio.term.TerminalTheme(
    background=yuio.color.ColorValue.from_hex("#00240A"),
    foreground=yuio.color.ColorValue.from_hex("#FFCFCF"),
    black=yuio.color.ColorValue.from_hex("#000000"),
    red=yuio.color.ColorValue.from_hex("#FF0000"),
    green=yuio.color.ColorValue.from_hex("#00FF00"),
    yellow=yuio.color.ColorValue.from_hex("#FFFF00"),
    blue=yuio.color.ColorValue.from_hex("#0000FF"),
    magenta=yuio.color.ColorValue.from_hex("#FF00FF"),
    cyan=yuio.color.ColorValue.from_hex("#00FFFF"),
    white=yuio.color.ColorValue.from_hex("#FFFFFF"),
    lightness=yuio.term.Lightness.DARK,
)

terminal_theme_light = dataclasses.replace(
    terminal_theme_dark,
    background=yuio.color.ColorValue.from_hex("#FFCFCF"),
    foreground=yuio.color.ColorValue.from_hex("#00240A"),
    lightness=yuio.term.Lightness.LIGHT,
)

terminal_theme_unknown = dataclasses.replace(
    terminal_theme_dark,
    lightness=yuio.term.Lightness.UNKNOWN,
)


class TestDefaultTheme:
    def test_no_color_overrides(self):
        term = yuio.term.Term(None, None)  # type: ignore
        theme = yuio.theme.DefaultTheme(term)
        assert (
            theme.get_color("low_priority_color_a") == yuio.color.Color.FORE_NORMAL_DIM
        )
        assert (
            theme.get_color("low_priority_color_b") == yuio.color.Color.FORE_NORMAL_DIM
        )

    def test_no_color_overrides_unknown_lightness(self):
        term = yuio.term.Term(
            None,  # type: ignore
            None,  # type: ignore
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            terminal_theme=terminal_theme_unknown,
        )
        theme = yuio.theme.DefaultTheme(term)
        assert (
            theme.get_color("low_priority_color_a") == yuio.color.Color.FORE_NORMAL_DIM
        )
        assert (
            theme.get_color("low_priority_color_b") == yuio.color.Color.FORE_NORMAL_DIM
        )
        assert theme.get_color(
            "task/progressbar/done/start"
        ) == yuio.color.Color.fore_from_hex("#0000FF")
        assert theme.get_color(
            "task/progressbar/done/end"
        ) == yuio.color.Color.fore_from_hex("#FF00FF")

    def test_dark_theme(self):
        term = yuio.term.Term(
            None,  # type: ignore
            None,  # type: ignore
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            terminal_theme=terminal_theme_dark,
        )
        theme = yuio.theme.DefaultTheme(term)
        assert theme.get_color(
            "low_priority_color_a"
        ) == yuio.color.Color.fore_from_hex("#655151")
        assert theme.get_color(
            "low_priority_color_b"
        ) == yuio.color.Color.fore_from_hex("#5A4949")
        assert theme.get_color(
            "task/progressbar/done/start"
        ) == yuio.color.Color.fore_from_hex("#0000FF")
        assert theme.get_color(
            "task/progressbar/done/end"
        ) == yuio.color.Color.fore_from_hex("#FF00FF")

    def test_light_theme(self):
        term = yuio.term.Term(
            None,  # type: ignore
            None,  # type: ignore
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            terminal_theme=terminal_theme_light,
        )
        theme = yuio.theme.DefaultTheme(term)
        assert theme.get_color(
            "low_priority_color_a"
        ) == yuio.color.Color.fore_from_hex("#00B231")
        assert theme.get_color(
            "low_priority_color_b"
        ) == yuio.color.Color.fore_from_hex("#00BF35")
        assert theme.get_color(
            "task/progressbar/done/start"
        ) == yuio.color.Color.fore_from_hex("#0000FF")
        assert theme.get_color(
            "task/progressbar/done/end"
        ) == yuio.color.Color.fore_from_hex("#FF00FF")

    def test_check(self):
        theme = yuio.theme.DefaultTheme(
            yuio.term.Term(
                None,  # type: ignore
                None,  # type: ignore
            )
        )

        theme.check()


class TestLoad:
    @pytest.fixture(autouse=True)
    def setup_theme_file(self, tmp_path: pathlib.Path):
        self.ok = tmp_path / "ok.json"
        self.ok.write_text(
            textwrap.dedent("""
            {
                "progress_bar_width": 25,
                "spinner_update_rate_ms": 100,
                "colors": {
                    "red": "#ff5555",
                    "green": "#55ff55",
                    "bold_red": "bold red"
                },
                "msg_decorations": {
                    "heading/1": "=> "
                }
            }
        """)
        )

        self.include = tmp_path / "include.json"
        self.include.write_text(
            textwrap.dedent("""
            {
                "include": "ok.json",
                "colors": {
                    "red": "#ff0000"
                }
            }
        """)
        )

        self.invalid = tmp_path / "invalid.json"
        self.invalid.write_text(
            textwrap.dedent("""
            {
                "progress_bar_width": -1
            }
        """)
        )

        self.broken = tmp_path / "broken.json"
        self.broken.write_text(
            textwrap.dedent("""
            broken json
        """)
        )

    def test_ok(self, term, monkeypatch):
        monkeypatch.setenv("YUIO_THEME_PATH", str(self.ok))
        theme = yuio.theme.load(term)

        assert theme.progress_bar_width == 25
        assert theme.spinner_update_rate_ms == 100
        assert theme.get_color("red") == yuio.color.Color.fore_from_rgb(
            0xFF, 0x55, 0x55
        )
        assert theme.get_color("green") == yuio.color.Color.fore_from_rgb(
            0x55, 0xFF, 0x55
        )
        assert theme.get_color("bold_red") == yuio.color.Color.fore_from_rgb(
            0xFF, 0x55, 0x55, bold=True
        )
        assert theme.msg_decorations["heading/1"] == "=> "

    def test_include(self, term, monkeypatch):
        monkeypatch.setenv("YUIO_THEME_PATH", str(self.include))
        theme = yuio.theme.load(term)

        assert theme.progress_bar_width == 25
        assert theme.spinner_update_rate_ms == 100
        assert theme.get_color("red") == yuio.color.Color.fore_from_rgb(
            0xFF, 0x00, 0x00
        )
        assert theme.get_color("green") == yuio.color.Color.fore_from_rgb(
            0x55, 0xFF, 0x55
        )
        assert theme.get_color("bold_red") == yuio.color.Color.fore_from_rgb(
            0xFF, 0x00, 0x00, bold=True
        )
        assert theme.msg_decorations["heading/1"] == "=> "

    def test_invalid(self, term, monkeypatch):
        monkeypatch.setenv("YUIO_THEME_PATH", str(self.invalid))
        with pytest.warns(yuio.theme.ThemeWarning):
            theme = yuio.theme.load(term)
        assert theme.progress_bar_width == 15

    def test_broken(self, term, monkeypatch):
        monkeypatch.setenv("YUIO_THEME_PATH", str(self.invalid))
        with pytest.warns(yuio.theme.ThemeWarning):
            theme = yuio.theme.load(term)
        assert theme.progress_bar_width == 15
