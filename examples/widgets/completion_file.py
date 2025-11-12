import yuio.complete
import yuio.io
import yuio.widget

if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    completer = yuio.complete.File()

    widget = yuio.widget.InputWithCompletion(completer, placeholder="enter a file path")

    yuio.io.heading("Which file should we nuke today?")
    result = widget.run(term, theme)
    yuio.io.success("You've entered `%r`", result)
