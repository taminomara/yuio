import yuio.complete
import yuio.io
import yuio.widget

if __name__ == '__main__':
    yuio.io.heading("Demonstration for `yuio.widget.InputWithCompletion`")
    yuio.io.info("You can use `tab` to invoke autocompletion.")
    yuio.io.info("When autocompleting lists, separators are automatically added")
    yuio.io.info("after each completion. They are removed if you don't print")
    yuio.io.info("the next list item. This is similar to how ZSH completes lists.")
    yuio.io.br()

    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    completer = yuio.complete.List(
        yuio.complete.Choice([
            yuio.complete.CompletionChoice('eggs'),
            yuio.complete.CompletionChoice('bacon'),
            yuio.complete.CompletionChoice('salad'),
            yuio.complete.CompletionChoice('hashbrown'),
            yuio.complete.CompletionChoice('sausages'),
            yuio.complete.CompletionChoice('granola'),
            yuio.complete.CompletionChoice('oatmeal'),
        ]),
    )
    widget = yuio.widget.InputWithCompletion(
        completer, placeholder="you can enter multiple items separated by space"
    )

    yuio.io.question("Choose what you'd like for breakfast:")
    result = widget.run(term, theme)
    yuio.io.success(f"You've entered %r", result)
