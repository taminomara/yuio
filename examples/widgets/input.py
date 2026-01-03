import yuio.io
import yuio.widget

if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    widget = yuio.widget.Input(
        placeholder="Enter something nice?",
        allow_multiline=True,
        allow_special_characters=True,
    )

    result = widget.run(term, theme)
    yuio.io.success("You've entered `%r`", result)
