import yuio.complete
import yuio.io
import yuio.widget

if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    completer = yuio.complete.List(
        yuio.complete.Choice(
            [
                yuio.complete.CompletionChoice("eggs"),
                yuio.complete.CompletionChoice("bacon"),
                yuio.complete.CompletionChoice("salad"),
                yuio.complete.CompletionChoice("hashbrown"),
                yuio.complete.CompletionChoice("sausages"),
                yuio.complete.CompletionChoice("granola"),
                yuio.complete.CompletionChoice("oatmeal"),
            ]
        ),
    )

    widget = yuio.widget.InputWithCompletion(
        completer, placeholder="you can enter multiple items separated by space"
    )

    yuio.io.question("Choose what you'd like for breakfast:")
    result = widget.with_help().run(term, theme)
    yuio.io.success(f"You've entered `%r`", result)
