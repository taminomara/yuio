import typing as _t

import yuio.io
import yuio.widget
from yuio.widget import Key, RenderContext


# Let's build a simple widget and see how we can configure it
# to automatically render help messages for us.

class ExampleWidget(yuio.widget.Widget[None]):
    def __init__(self):
        self._last_action = "nothing so far"

    # For all actions we'll provide a short docstring.
    # We'll also group actions into columns
    # using `yuio.widget.help_column`.

    @yuio.widget.bind(Key.ARROW_UP)
    @yuio.widget.bind("k")
    @yuio.widget.help_column(0)
    def on_up(self):
        """move up"""
        self._last_action = "Arrow Up / K"

    @yuio.widget.bind(Key.ARROW_DOWN)
    @yuio.widget.bind("j")
    @yuio.widget.help_column(0)
    def on_down(self):
        """move down"""
        self._last_action = "Arrow Down / J"

    @yuio.widget.bind(Key.ARROW_LEFT)
    @yuio.widget.bind("h")
    @yuio.widget.help_column(0)
    def on_left(self):
        """move left"""
        self._last_action = "Arrow Left / H"

    @yuio.widget.bind(Key.ARROW_RIGHT)
    @yuio.widget.bind("l")
    @yuio.widget.help_column(0)
    def on_right(self):
        """move right"""
        self._last_action = "Arrow Right / L"

    @yuio.widget.bind(Key.ENTER)
    @yuio.widget.help_column(1)
    def on_enter(self):
        """accept input"""
        self._last_action = "Enter"

    @yuio.widget.bind('/')
    @yuio.widget.help_column(1)
    def on_slash(self):
        """filter items"""
        self._last_action = "Slash"

    @yuio.widget.bind(Key.ESCAPE)
    @yuio.widget.bind('q')
    @yuio.widget.help_column(1)
    def on_escape(self):
        """close"""
        return yuio.widget.Result(None)

    def layout(self, rc: RenderContext) -> _t.Tuple[int, int]:
        return 1, 1

    def draw(self, rc: yuio.widget.RenderContext):
        rc.write("You've pressed ")
        rc.set_color_path("code")
        rc.write(self._last_action)
        rc.reset_color()
        rc.write(".")


if __name__ == '__main__':
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    widget = ExampleWidget().with_help()

    yuio.io.question("Press hotkeys for actions described below:")
    widget.run(term, theme)
