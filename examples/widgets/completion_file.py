import yuio.complete
import yuio.io
import yuio.widget

if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    completer = yuio.complete.File()

    widget = yuio.widget.InputWithCompletion(completer, placeholder="enter a file path")

    result = (
        widget.with_title("Which file should we nuke today?")
        .with_help()
        .run(term, theme)
    )
    yuio.io.success(f"You've entered `%r`", result)
