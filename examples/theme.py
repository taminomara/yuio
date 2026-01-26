import time

import yuio.io
import yuio.theme


class BlockProgressTheme(yuio.theme.DefaultTheme):
    # Make spinner faster.
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

    colors = {
        # Custom accent colors.
        "accent_color": "red",
        "accent_color_2": "magenta",
        # By default, color of the first level heading is `accent_color`;
        # Reset it to `heading_color`.
        "msg/text:heading/1": "heading_color",
        # Decoration and progress bar for tasks.
        "msg/decoration:task": "accent_color",
        "task/progressbar/done/start": "term/bright_yellow",
        "task/progressbar/done/end": "term/bright_red",
    }


if __name__ == "__main__":
    yuio.io.setup(theme=BlockProgressTheme)

    yuio.io.heading("Theme with custom colors and decorations")

    with yuio.io.Task("Doing something") as task:
        time.sleep(4)

        for progress in range(0, 101):
            task.progress(progress / 100)
            time.sleep(0.05)
