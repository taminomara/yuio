import yuio.io
import yuio.theme
import yuio.app

class Theme(yuio.theme.DefaultTheme):
    colors = {
        "custom_tag": "bold magenta inverse"
    }

@yuio.app.app
def main():
    yuio.io.info("This is a <c custom_tag>custom color tag!</c>")

main.theme = Theme

if __name__ == "__main__":
    main.run()
