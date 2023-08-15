import yuio.io
import yuio.widget


if __name__ == '__main__':
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    options = [
        yuio.widget.Option(
            display_text="a coloring book",
            value="I'll bring you five :3"
        ),
        yuio.widget.Option(
            display_text="a comic",
            value="Which series do you like?"
        ),
        yuio.widget.Option(
            display_text="release of Half-Life 3",
            value="Be realistic..."
        ),
        yuio.widget.Option(
            display_text="a dragon!",
            value="What color do you want your dragon to be?"
        ),
        yuio.widget.Option(
            display_text="gender euphoria 👉👈",
            value="Aww :3 you're loved and valid, remember that 💖"
        ),
    ]

    widget = yuio.widget.Help.add_help_to(yuio.widget.Choice(options))

    yuio.io.question("What should Santa bring you this year?")
    result = widget.run(term, theme)
    yuio.io.success("%s", result)
