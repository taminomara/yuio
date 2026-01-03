import time
import yuio.io
import yuio.theme
import yuio.app

class Theme(yuio.theme.DefaultTheme):
    colors = {
        "accent_color": "red",
        "task/progressbar/done/start": "term/bright_yellow",
        "task/progressbar/done/end": "term/bright_red",
    }

@yuio.app.app
def main():
    yuio.io.heading("Custom accent colors")

    with yuio.io.Task("Example task") as task:
        for i in range(100):
            task.progress(i, 100)
            time.sleep(0.05)

main.theme = Theme

if __name__ == "__main__":
    main.run()
