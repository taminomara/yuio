import yuio.io
import yuio.widget

if __name__ == "__main__":
    term = yuio.io.get_term()
    theme = yuio.io.get_theme()

    options = [
        yuio.widget.Option(display_text="GameBoy", value="GameBoy"),
        yuio.widget.Option(display_text="Wii", value="Wii"),
        yuio.widget.Option(display_text="PlayStation2", value="PlayStation2"),
        yuio.widget.Option(
            display_text="PlayStationPortable", value="PlayStationPortable"
        ),
        yuio.widget.Option(display_text="XboxOne", value="XboxOne"),
        yuio.widget.Option(display_text="MegaDrive/Genesis", value="MegaDrive/Genesis"),
        yuio.widget.Option(display_text="Atari2600", value="Atari2600"),
    ]

    widget = yuio.widget.Multiselect(options)

    yuio.io.heading("Choose consoles that you like")
    result = widget.run(term, theme)
    yuio.io.info("You selected `%#r`", result)
