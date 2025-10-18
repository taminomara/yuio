import yuio.io
import yuio.widget
from yuio.widget import Key, RenderContext


# Let's build a simple widget and see how we can configure it
# to automatically render help messages for us.
class ExampleWidget(yuio.widget.Widget[None]):
    def __init__(self):
        self._last_action = "nothing so far"

    # For all actions we'll provide a short docstring.
    # We'll also use `show_in_inline_help` to show some of them under the widget.

    @yuio.widget.bind(Key.ARROW_UP)
    @yuio.widget.bind("k")
    def on_up(self):
        """move up"""
        self._last_action = "Arrow Up / K"

    @yuio.widget.bind(Key.ARROW_DOWN)
    @yuio.widget.bind("j")
    def on_down(self):
        """move down"""
        self._last_action = "Arrow Down / J"

    @yuio.widget.bind(Key.ARROW_LEFT)
    @yuio.widget.bind("h")
    def on_left(self):
        """move left"""
        self._last_action = "Arrow Left / H"

    @yuio.widget.bind(Key.ARROW_RIGHT)
    @yuio.widget.bind("l")
    def on_right(self):
        """move right"""
        self._last_action = "Arrow Right / L"

    @yuio.widget.bind(Key.ENTER, show_in_inline_help=True)
    def on_enter(self):
        """accept input"""
        self._last_action = "Enter"

    @yuio.widget.bind("/", show_in_inline_help=True)
    def on_slash(self):
        """filter items"""
        self._last_action = "Slash"

    @yuio.widget.bind(Key.ESCAPE, show_in_inline_help=True)
    @yuio.widget.bind("q", show_in_inline_help=True)
    def on_escape(self):
        """close"""
        return yuio.widget.Result(None)

    def layout(self, rc: RenderContext) -> tuple[int, int]:
        return 1, 1

    def draw(self, rc: yuio.widget.RenderContext):
        rc.write("You've pressed ")
        rc.set_color_path("code")
        rc.write(self._last_action)
        rc.reset_color()
        rc.write(".")

    # Let's further customize our help.

    @property
    def help_data(self) -> yuio.widget.WidgetHelp:
        # Add a custom item to the inline help.
        return super().help_data.with_action(
            Key.ARROW_UP,
            Key.ARROW_DOWN,
            Key.ARROW_LEFT,
            Key.ARROW_RIGHT,
            inline_msg="navigate",
            prepend=True,
        )


if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    widget = ExampleWidget()

    yuio.io.heading("Press hotkeys for actions described below")
    widget.run(term, theme)
