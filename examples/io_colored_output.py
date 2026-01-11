import json

import yuio.color
import yuio.io

if __name__ == "__main__":
    yuio.io.hr(weight=2)
    yuio.io.hr("<c bold>✨ COLOR PRINTING DEMO ✨</c>", weight=0)
    yuio.io.hr(weight=2)

    yuio.io.heading("Message colors")
    yuio.io.success("Success message is bold green.")
    yuio.io.failure("Failure message is bold red.")
    yuio.io.info("Info message is default color.")
    yuio.io.warning("Warning message is yellow.")
    yuio.io.error("Error message is red.")

    yuio.io.heading("Color tags")
    yuio.io.info("This text is <c red bold>rad!</c>")
    yuio.io.warning("File <c code>example.txt</c> does not exist.")

    yuio.io.heading("Links")
    yuio.io.info(
        "Visit %s.",
        yuio.io.Link("example link", url="https://example.com"),
    )
    yuio.io.info(
        "Or %s in a text editor.",
        yuio.io.Link.from_path("open this example", path=__file__),
    )
    yuio.io.info(
        "Note: if your terminal doesn't support hyperlinks, "
        "run this example with `--no-color` to see them."
    )

    yuio.io.heading("Exceptions")
    try:
        json.loads("{ nah, this is not a valid JSON 😕 }")
    except:
        yuio.io.error_with_tb("Something went horribly wrong!")

    yuio.io.heading("Markdown")
    yuio.io.md(
        """
        - You can use `` `backticks` `` with all functions from `yuio.io`.
        - You can also use CommonMark block markup with `yuio.io.md`.
        - For example, check out this fork bomb:

          ```sh
          :(){ :|:& };:  # <- don't paste this in bash!
          ```
        """
    )

    yuio.io.heading("Code highlighting")
    yuio.io.hl(
        """
        {
            "config": "~/.config.json",
            "syntax": "json"
        }
        """,
        syntax="json",
    )

    yuio.io.heading("Low level API")
    yuio.io.raw(
        yuio.io.Stack(
            yuio.io.Hr(
                "low level API start",
                weight=0,
                left_middle=">",
                left_end=" ",
                right_start=" ",
                right_middle="<",
            ),
            yuio.io.Wrap(
                yuio.io.Format(
                    "Some paragraph that will be wrapped to 40 symbols.\n\n"
                    "This part uses `yuio.io`, `yuio.string`, `yuio.theme` and other "
                    "low-level modules. You can do some %s things with them!",
                    yuio.io.ColorizedString(
                        yuio.color.Color.STYLE_INVERSE
                        | yuio.color.Color.STYLE_BLINK
                        | yuio.color.Color.FORE_MAGENTA,
                        "advanced",
                    ),
                ),
                width=40,
                indent=yuio.io.ColorizedString(
                    yuio.io.get_theme().get_color("msg/decoration"),
                    "> ",
                ),
            ),
            yuio.io.Hr(
                "low level API end",
                weight=0,
                left_middle=">",
                left_end=" ",
                right_start=" ",
                right_middle="<",
            ),
        ),
        add_newline=True,
    )
