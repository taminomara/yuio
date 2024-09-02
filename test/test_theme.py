import dataclasses

import pytest

import yuio.term
import yuio.theme


class TestColors:
    def test_get_color(self):
        t = yuio.theme.Theme()

        assert t.get_color("code") == yuio.term.Color.FORE_MAGENTA
        assert t.get_color("note") == yuio.term.Color.FORE_GREEN
        assert t.get_color("bold") == yuio.term.Color.STYLE_BOLD
        assert t.get_color("b") == yuio.term.Color.STYLE_BOLD
        assert t.get_color("dim") == yuio.term.Color.STYLE_DIM
        assert t.get_color("d") == yuio.term.Color.STYLE_DIM
        assert t.get_color("normal") == yuio.term.Color.FORE_NORMAL
        assert t.get_color("red") == yuio.term.Color.FORE_RED
        assert t.get_color("green") == yuio.term.Color.FORE_GREEN
        assert t.get_color("yellow") == yuio.term.Color.FORE_YELLOW
        assert t.get_color("blue") == yuio.term.Color.FORE_BLUE
        assert t.get_color("magenta") == yuio.term.Color.FORE_MAGENTA
        assert t.get_color("cyan") == yuio.term.Color.FORE_CYAN

    def test_to_color(self):
        t = yuio.theme.Theme()

        assert t.to_color(None) == yuio.term.Color.NONE
        assert t.to_color("blue") == yuio.term.Color.FORE_BLUE
        assert t.to_color(yuio.term.Color.FORE_MAGENTA) == yuio.term.Color.FORE_MAGENTA

    def test_color_paths(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.term.Color.STYLE_BOLD,
                "x/y": yuio.term.Color.FORE_RED,
                "x/z": yuio.term.Color.FORE_GREEN,
                "y/y": yuio.term.Color.FORE_BLUE,
            }

        a = A()

        assert a.get_color("x") == yuio.term.Color.STYLE_BOLD
        assert (
            a.get_color("x/y") == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        )
        assert (
            a.get_color("x/z")
            == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_GREEN
        )
        assert a.get_color("y/y") == yuio.term.Color.FORE_BLUE

    def test_color_redirect(self):
        class A(yuio.theme.Theme):
            colors = {
                "t_r": yuio.term.Color.FORE_RED,
                "t_g": yuio.term.Color.FORE_GREEN,
                "t_b": yuio.term.Color.STYLE_BOLD,
                "t_d": yuio.term.Color.STYLE_DIM,
                "x": "t_b",
                "x/y": "t_r",
                "y": "t_d",
                "y/y": "x/y",
                "z": ["x/y", "y/y", yuio.term.Color.BACK_CYAN],
            }

        a = A()

        assert a.get_color("x") == yuio.term.Color.STYLE_BOLD
        assert (
            a.get_color("x/y") == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        )
        assert a.get_color("y") == yuio.term.Color.STYLE_DIM
        assert (
            a.get_color("y/y")
            == yuio.term.Color.STYLE_DIM
            | yuio.term.Color.STYLE_BOLD
            | yuio.term.Color.FORE_RED
        )
        assert (
            a.get_color("z")
            == yuio.term.Color.STYLE_DIM
            | yuio.term.Color.STYLE_BOLD
            | yuio.term.Color.FORE_RED
            | yuio.term.Color.BACK_CYAN
        )

    def test_color_ctx(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.term.Color.STYLE_BOLD,
                "x:y": yuio.term.Color.FORE_RED,
                "x:y/z": yuio.term.Color.STYLE_DIM,
                "x:a": yuio.term.Color.FORE_GREEN,
                "q/q": yuio.term.Color.FORE_BLUE,
            }

        a = A()

        assert a.get_color("x") == yuio.term.Color.STYLE_BOLD
        assert (
            a.get_color("x:y") == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        )
        assert (
            a.get_color("x:a")
            == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_GREEN
        )
        assert (
            a.get_color("x/a/q:y")
            == yuio.term.Color.STYLE_BOLD | yuio.term.Color.FORE_RED
        )
        assert (
            a.get_color("x:y/z")
            == yuio.term.Color.STYLE_BOLD
            | yuio.term.Color.FORE_RED
            | yuio.term.Color.STYLE_DIM
        )
        assert a.get_color("q/q") == yuio.term.Color.FORE_BLUE
        assert a.get_color("q/q:y") == yuio.term.Color.FORE_BLUE


class TestInheritance:
    def test_simple_inheritance(self):
        class A(yuio.theme.Theme):
            colors = {
                "t_a": yuio.term.Color.FORE_RED,
                "t_ab": yuio.term.Color.FORE_GREEN,
                "t_abc": yuio.term.Color.FORE_BLUE,
            }

        class B(yuio.theme.Theme):
            colors = {
                "t_b": yuio.term.Color.FORE_CYAN,
                "t_ab": yuio.term.Color.FORE_MAGENTA,
                "t_abc": yuio.term.Color.FORE_YELLOW,
            }

        class C(A, B):
            colors = {
                "t_c": yuio.term.Color.FORE_BLACK,
                "t_abc": yuio.term.Color.FORE_WHITE,
            }

        c = C()

        assert C.colors["t_a"] == yuio.term.Color.FORE_RED
        assert C.colors["t_b"] == yuio.term.Color.FORE_CYAN
        assert C.colors["t_c"] == yuio.term.Color.FORE_BLACK
        assert C.colors["t_ab"] == yuio.term.Color.FORE_GREEN
        assert C.colors["t_abc"] == yuio.term.Color.FORE_WHITE

        assert c.get_color("t_a") == yuio.term.Color.FORE_RED
        assert c.get_color("t_b") == yuio.term.Color.FORE_CYAN
        assert c.get_color("t_c") == yuio.term.Color.FORE_BLACK
        assert c.get_color("t_ab") == yuio.term.Color.FORE_GREEN
        assert c.get_color("t_abc") == yuio.term.Color.FORE_WHITE

    def test_color_overrides(self):
        class A(yuio.theme.Theme):
            colors = {
                "t_a": yuio.term.Color.FORE_RED,
                "t_b": yuio.term.Color.FORE_GREEN,
                "t_b_2": yuio.term.Color.FORE_MAGENTA,
            }

            def __init__(self):
                super().__init__()

                self._set_color_if_not_overridden("t_a", yuio.term.Color.BACK_RED)
                self._set_color_if_not_overridden("t_b", yuio.term.Color.BACK_GREEN)
                self.set_color("t_b_2", yuio.term.Color.BACK_MAGENTA)

        class B(A):
            colors = {
                "t_b": yuio.term.Color.FORE_CYAN,
                "t_b_2": yuio.term.Color.FORE_CYAN,
            }

        a = A()
        b = B()

        assert A.colors["t_a"] == yuio.term.Color.FORE_RED
        assert A.colors["t_b"] == yuio.term.Color.FORE_GREEN
        assert A.colors["t_b_2"] == yuio.term.Color.FORE_MAGENTA

        assert a.get_color("t_a") == yuio.term.Color.BACK_RED
        assert a.get_color("t_b") == yuio.term.Color.BACK_GREEN
        assert a.get_color("t_b_2") == yuio.term.Color.BACK_MAGENTA

        assert B.colors["t_a"] == yuio.term.Color.FORE_RED
        assert B.colors["t_b"] == yuio.term.Color.FORE_CYAN
        assert B.colors["t_b_2"] == yuio.term.Color.FORE_CYAN

        assert b.get_color("t_a") == yuio.term.Color.BACK_RED
        assert b.get_color("t_b") == yuio.term.Color.FORE_CYAN
        assert b.get_color("t_b_2") == yuio.term.Color.BACK_MAGENTA

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


class TestSetAttrs:
    def test_set_color(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.term.Color.STYLE_BOLD,
            }

        a = A()

        assert a.get_color("x") == yuio.term.Color.STYLE_BOLD
        assert a.get_color("x/y") == yuio.term.Color.STYLE_BOLD
        assert a.get_color("z") == yuio.term.Color.NONE

        a.set_color("x", yuio.term.Color.FORE_RED)
        a.set_color("z", yuio.term.Color.FORE_BLUE)

        assert a.get_color("x") == yuio.term.Color.FORE_RED
        assert a.get_color("x/y") == yuio.term.Color.FORE_RED
        assert a.get_color("z") == yuio.term.Color.FORE_BLUE

    def test_set_color_if_not_overridden(self):
        class A(yuio.theme.Theme):
            colors = {
                "x": yuio.term.Color.STYLE_BOLD,
            }

        a = A()

        with pytest.raises(RuntimeError):
            a._set_color_if_not_overridden("x", yuio.term.Color.FORE_RED)

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


terminal_colors_dark = yuio.term.TerminalColors(
    background=yuio.term.ColorValue.from_hex("#00240A"),
    foreground=yuio.term.ColorValue.from_hex("#FFCFCF"),
    black=yuio.term.ColorValue.from_hex("#000000"),
    red=yuio.term.ColorValue.from_hex("#FF0000"),
    green=yuio.term.ColorValue.from_hex("#00FF00"),
    yellow=yuio.term.ColorValue.from_hex("#FFFF00"),
    blue=yuio.term.ColorValue.from_hex("#0000FF"),
    magenta=yuio.term.ColorValue.from_hex("#FF00FF"),
    cyan=yuio.term.ColorValue.from_hex("#00FFFF"),
    white=yuio.term.ColorValue.from_hex("#FFFFFF"),
    lightness=yuio.term.Lightness.DARK,
)

terminal_colors_light = dataclasses.replace(
    terminal_colors_dark,
    background=yuio.term.ColorValue.from_hex("#FFCFCF"),
    foreground=yuio.term.ColorValue.from_hex("#00240A"),
    lightness=yuio.term.Lightness.LIGHT,
)

terminal_colors_unknown = dataclasses.replace(
    terminal_colors_dark,
    lightness=yuio.term.Lightness.UNKNOWN,
)


class TestDefaultTheme:
    def test_no_color_overrides(self):
        term = yuio.term.Term(None)  # type: ignore
        theme = yuio.theme.DefaultTheme(term)
        assert (
            theme.get_color("low_priority_color_a") == yuio.term.Color.FORE_NORMAL_DIM
        )
        assert (
            theme.get_color("low_priority_color_b") == yuio.term.Color.FORE_NORMAL_DIM
        )

    def test_no_color_overrides_unknown_lightness(self):
        term = yuio.term.Term(
            None,  # type: ignore
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            terminal_colors=terminal_colors_unknown,
        )
        theme = yuio.theme.DefaultTheme(term)
        assert (
            theme.get_color("low_priority_color_a") == yuio.term.Color.FORE_NORMAL_DIM
        )
        assert (
            theme.get_color("low_priority_color_b") == yuio.term.Color.FORE_NORMAL_DIM
        )
        assert theme.get_color(
            "task/progressbar/done/start"
        ) == yuio.term.Color.fore_from_hex("#0000FF")
        assert theme.get_color(
            "task/progressbar/done/end"
        ) == yuio.term.Color.fore_from_hex("#FF00FF")

    def test_dark_theme(self):
        term = yuio.term.Term(
            None,  # type: ignore
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            terminal_colors=terminal_colors_dark,
        )
        theme = yuio.theme.DefaultTheme(term)
        assert theme.get_color("low_priority_color_a") == yuio.term.Color.fore_from_hex(
            "#655151"
        )
        assert theme.get_color("low_priority_color_b") == yuio.term.Color.fore_from_hex(
            "#5A4949"
        )
        assert theme.get_color(
            "task/progressbar/done/start"
        ) == yuio.term.Color.fore_from_hex("#0000FF")
        assert theme.get_color(
            "task/progressbar/done/end"
        ) == yuio.term.Color.fore_from_hex("#FF00FF")

    def test_light_theme(self):
        term = yuio.term.Term(
            None,  # type: ignore
            color_support=yuio.term.ColorSupport.ANSI_TRUE,
            terminal_colors=terminal_colors_light,
        )
        theme = yuio.theme.DefaultTheme(term)
        assert theme.get_color("low_priority_color_a") == yuio.term.Color.fore_from_hex(
            "#00B231"
        )
        assert theme.get_color("low_priority_color_b") == yuio.term.Color.fore_from_hex(
            "#00BF35"
        )
        assert theme.get_color(
            "task/progressbar/done/start"
        ) == yuio.term.Color.fore_from_hex("#0000FF")
        assert theme.get_color(
            "task/progressbar/done/end"
        ) == yuio.term.Color.fore_from_hex("#FF00FF")
