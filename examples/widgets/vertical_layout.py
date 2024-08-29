from typing import NoReturn, Optional, Tuple

import yuio.io
import yuio.term
import yuio.widget
from yuio.widget import KeyboardEvent, RenderContext, VerticalLayout, Widget


# Let's build a simple widget that displays an input box with a heading
# and a caption that will only show when entered text is long enough.
# For this, we'll use `yuio.widget.Line` and `yuio.widget.Input`,
# and we'll stack them together using `yuio.widget.VerticalLayout`.
class InputWithHeading(Widget[str]):
    def __init__(self):
        self._heading = yuio.widget.Line("Enter something:", color="bold")
        self._input = yuio.widget.Input()

        # We will init this attribute in the `layout` function.
        # We use `NoReturn`, because we don't use `VerticalLayout`s
        # event handling capabilities in this example.
        self._layout: VerticalLayout[NoReturn]

    def event(self, e: KeyboardEvent) -> Optional[yuio.widget.Result[str]]:
        # Simply forward all events to the input box.
        # We won't use `VerticalLayout`s event handling capabilities in this example.
        return self._input.event(e)

    def layout(self, rc: RenderContext) -> Tuple[int, int]:
        # First two widgets will always show...
        self._layout = VerticalLayout(self._heading, self._input)

        # ...and the third one will only show if entered text is long enough.
        if yuio.term.line_width(self._input.text) > 15:
            self._layout.append(yuio.widget.Line("Wow that's long!", color="blue"))

        return self._layout.layout(rc)

    def draw(self, rc: RenderContext):
        # Rendering a layout is easy.
        return self._layout.draw(rc)


if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    widget = InputWithHeading()

    result = widget.run(term, theme)
    yuio.io.success(f"You've entered `%r`", result)
