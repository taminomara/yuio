import yuio.app
import yuio.io
import yuio.term
import yuio.theme

class Theme(yuio.theme.DefaultTheme):
    def __init__(self, term: yuio.term.Term):
        super().__init__(term)

        if term.is_unicode:
            decorations = _DECORATIONS_UNICODE
        else:
            decorations = _DECORATIONS_ASCII

        for name, decoration in decorations.items():
            self._set_msg_decoration_if_not_overridden(name, decoration)

_DECORATIONS_UNICODE = {
    "heading/1": "➡️ ",
}
_DECORATIONS_ASCII = {
    "heading/1": "=> "
}

@yuio.app.app
def main():
    yuio.io.info("This is a <c dark_magenta_bg>dark magenta background!</c>")

main.theme = Theme

if __name__ == "__main__":
    main.run()
