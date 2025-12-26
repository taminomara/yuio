# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

import yuio.app
import yuio.io
import yuio.term
import yuio.widget


@yuio.app.app
def main(
    #: When enabled, prints raw input from terminal into stderr.
    raw: bool = yuio.app.field(default=False, flags=["-r", "--raw"]),
    #: When enabled, puts terminal into bracketed paste mode.
    bracketed_paste: bool = True,
    #: When enabled, enables Kitty's key disambiguation protocol.
    modify_keyboard: bool = False,
):
    """
    Debug how Yuio parses escape sequences coming from the terminal.

    """

    # Note: we use stderr as a tty stream even though we write into stdout.
    # This is to allow redirecting stdout to some file while recording keystrokes.
    # In fact, we do exactly this in our tests.
    term = yuio.io.get_term()
    if not term.can_run_widgets:
        raise yuio.app.AppError("Stderr is not interactive")

    yuio.io.info(
        "Printing everything that the terminal sends us. Press `Ctrl+C` to stop."
    )
    with yuio.term._enter_raw_mode(
        term.ostream,
        term.istream,
        bracketed_paste=bracketed_paste,
        modify_keyboard=modify_keyboard,
    ):
        if raw:
            _read_keycode = yuio.term._read_keycode

            def read_keycode(*a, **kw):
                keycode = _read_keycode(*a, **kw)
                yuio.io.info("<c d>Read: %r</c>", keycode, to_stdout=True)
                return keycode

            yuio.term._read_keycode = read_keycode
        for event in yuio.widget._event_stream(term.ostream, term.istream):
            if isinstance(event.key, str):
                r = repr(event.key)
            else:
                r = event.key.name
            if event.alt:
                r = f"Alt+{r}"
            if event.ctrl:
                r = f"Ctrl+{r}"
            if event.shift:
                r = f"Shift+{r}"
            if event.paste_str:
                p = f" {event.paste_str!r}"
            else:
                p = ""
            yuio.io.info("Key: <c b>%s</c>`%s`", r, p, to_stdout=True)
            if event == yuio.widget.KeyboardEvent("c", ctrl=True):
                raise KeyboardInterrupt()


if __name__ == "__main__":
    main.run()
