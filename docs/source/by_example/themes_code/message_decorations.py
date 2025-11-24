import yuio.io
import yuio.theme
import yuio.app

class Theme(yuio.theme.DefaultTheme):
    msg_decorations = {
        "heading/1": "=> ",
        "info": "-> ",
    }

@yuio.app.app
def main():
    yuio.io.heading("Custom decorations")
    yuio.io.info("This is an info message")

main.theme = Theme

if __name__ == "__main__":
    main.run()
