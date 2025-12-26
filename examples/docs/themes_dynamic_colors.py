import yuio.app
import yuio.color
import yuio.io
import yuio.term
import yuio.theme

class Theme(yuio.theme.DefaultTheme):
    def __init__(self, term: yuio.term.Term):
        super().__init__(term)

        if not term.terminal_theme:
            return

        background = term.terminal_theme.background
        magenta = term.terminal_theme.magenta

        match term.terminal_theme.lightness:
            case yuio.term.Lightness.LIGHT:
                # Slightly darker than background.
                dark_magenta = magenta.match_luminosity(background.darken(0.2))
            case yuio.term.Lightness.DARK:
                # Slightly lighter than background.
                dark_magenta = magenta.match_luminosity(background.lighten(0.2))
            case _:
                # As dark as background.
                dark_magenta = magenta.match_luminosity(background)

        self._set_color_if_not_overridden(
            "dark_magenta_bg", yuio.color.Color(back=dark_magenta)
        )

@yuio.app.app
def main():
    yuio.io.info("This is a <c dark_magenta_bg>dark magenta background!</c>")

main.theme = Theme

if __name__ == "__main__":
    main.run()
