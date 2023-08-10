import typing as _t

import yuio.term
import yuio.widget
from yuio.widget import Key, RenderContext


class ExampleWidget(yuio.widget.Widget[None]):
    _last_action = "nothing so far"

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
        self.stop(None)

    def layout(self, rc: RenderContext) -> _t.Tuple[int, int]:
        return 1, 1

    def draw(self, rc: yuio.widget.RenderContext):
        rc.write("You've pressed ")
        rc.set_color_path("code")
        rc.write(self._last_action)


if __name__ == '__main__':
    term = yuio.term.get_stderr_info()
    theme = yuio.term.DefaultTheme(term)

    widget = ExampleWidget()
    widget_with_help = yuio.widget.VerticalLayoutBuilder() \
        .add(widget, receive_events=True) \
        .add(widget.help_widget) \
        .build()

    widget_with_help.run(term, theme)
