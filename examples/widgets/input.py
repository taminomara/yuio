import yuio.io
import yuio.widget


if __name__ == '__main__':
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    widget = yuio.widget.Input(placeholder='Enter something nice?', decoration='>')

    result = widget.run(term, theme)
    yuio.io.success("You've entered `%r`", result)
