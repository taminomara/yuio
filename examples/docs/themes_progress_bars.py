import time
import yuio.io
import yuio.theme
import yuio.app

class Theme(yuio.theme.DefaultTheme):
    spinner_update_rate_ms = 100
    msg_decorations_unicode = {
        # Custom progress bar symbols.
        "progress_bar/start_symbol": "|",
        "progress_bar/end_symbol": "|",
        "progress_bar/done_symbol": "█",
        "progress_bar/pending_symbol": " ",
        "progress_bar/transition_pattern": "█▉▊▋▌▍▎▏ ",
        # Custom spinner sequence.
        "spinner/pattern": "|||/-\\",
    }

@yuio.app.app
def main():
    yuio.io.heading("Custom progress bar")

    with yuio.io.Task("Example task") as task:
        time.sleep(2)
        for i in range(100):
            task.progress(i, 100)
            time.sleep(0.05)

main.theme = Theme

if __name__ == "__main__":
    main.run()
