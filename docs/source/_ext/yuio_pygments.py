import pygments.token
import pygments.style
import pygments.styles.default

class Style(pygments.styles.default.DefaultStyle):
    styles = pygments.styles.default.DefaultStyle.styles.copy()
    styles[pygments.token.Generic.Output] = '#999'
    styles[pygments.token.Generic.Prompt] = '#999'
