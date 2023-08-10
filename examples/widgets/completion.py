import yuio.complete
import yuio.term
import yuio.widget

if __name__ == '__main__':
    term = yuio.term.get_stderr_info()
    theme = yuio.term.DefaultTheme(term)

    completer = yuio.complete.List(
        # yuio.complete.Choice([
        #     yuio.complete.CompletionChoice('eggs'),
        #     yuio.complete.CompletionChoice('bacon'),
        #     yuio.complete.CompletionChoice('salad'),
        #     yuio.complete.CompletionChoice('hashbrown'),
        #     yuio.complete.CompletionChoice('sausages'),
        #     yuio.complete.CompletionChoice('granola'),
        #     yuio.complete.CompletionChoice('oatmeal'),
        # ]),
        yuio.complete.File(),
        delimiter=":"
    )

    widget = yuio.widget.InputWithCompletion(
        completer, placeholder="you can enter multiple items separated by space"
    )

    print("Choose what you'd like for breakfast:")
    result = widget.run(term, theme)
    print(f"You've entered {result!r}")
