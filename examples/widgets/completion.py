import yuio.complete
import yuio.io
import yuio.widget

if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    completer = yuio.complete.List(
        yuio.complete.Choice(
            [
                yuio.complete.Option("eggs"),
                yuio.complete.Option("bacon"),
                yuio.complete.Option("salad"),
                yuio.complete.Option("hashbrown"),
                yuio.complete.Option("sausages"),
                yuio.complete.Option("granola"),
                yuio.complete.Option("oatmeal"),
            ]
        ),
    )

    widget = (
        yuio.widget.InputWithCompletion(
            completer, placeholder="you can enter multiple items separated by space"
        )
        .with_title("Choose what you'd like for breakfast:")
        .with_help()
    )

    result = widget.with_help().run(term, theme)
    yuio.io.success(f"You've entered `%r`", result)
