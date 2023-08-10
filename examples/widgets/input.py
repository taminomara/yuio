import yuio.term
import yuio.widget


if __name__ == '__main__':
    term = yuio.term.get_stderr_info()
    theme = yuio.term.DefaultTheme(term)

    widget = yuio.widget.Input(placeholder='Enter something', decoration='>')

    result = widget.run(term, theme)
    print(f"You've entered {result!r}")
