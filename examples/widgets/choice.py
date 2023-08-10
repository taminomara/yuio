import yuio.term
import yuio.widget


if __name__ == '__main__':
    term = yuio.term.get_stderr_info()
    theme = yuio.term.DefaultTheme(term)

    options = [
        yuio.widget.Option(1, "a coloring book"),
        yuio.widget.Option(2, "a comic"),
        yuio.widget.Option(3, "release of Half-Life 3"),
        yuio.widget.Option(4, "a dragon!"),
        yuio.widget.Option(5, "gender euphoria 👉👈"),
    ]

    widget = yuio.widget.Choice(options)

    print("What should Santa bring you this year?")
    result = widget.run(term, theme)
    print(f"You've chosen option #{result!r}")
