import pygments.style
import pygments.styles.default
import pygments.token


class Style(pygments.styles.default.DefaultStyle):
    styles = pygments.styles.default.DefaultStyle.styles.copy()
    styles[pygments.token.Generic.Output] = "#909090"
    styles[pygments.token.Generic.Prompt] = "#D0D0D0"
