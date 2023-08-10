import sys

import yuio.complete
import yuio.widget
import yuio.term
import contextlib


devnull = open('/dev/null', 'w')


yuio.widget._set_cbreak = contextlib.nullcontext


class MockRc(yuio.widget.RenderContext):
    def __init__(self, term, theme):
        super().__init__(term, theme)
        self._override_wh = (200, 200)
yuio.widget.RenderContext = MockRc


def _mock_event_stream():
    for _ in range(500):
        yield yuio.widget.KeyboardEvent(yuio.widget.Key.TAB)
yuio.widget._event_stream = _mock_event_stream



term = yuio.term.Term(devnull, yuio.term.ColorSupport.ANSI_TRUE, yuio.term.InteractiveSupport.FULL)
completer = yuio.complete.Choice([yuio.complete.CompletionChoice(f"comp{i}") for i in range(1000)])
widget = yuio.widget.InputWithCompletion(completer)
try:
    widget.run(term, yuio.term.DefaultTheme(term))
except AssertionError:
    pass
