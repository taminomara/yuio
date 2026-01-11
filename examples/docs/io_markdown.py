import yuio.app
import yuio.io

@yuio.app.app
def main():
    yuio.io.md("""
        # Greetings!

        -   You can use *inline formatting*, `backticks`,
            and {py:class}`MySt roles <yuio.md.MdParser>`.
        -   Hyperlinks [also work]!
        -   You can also use CommonMark block markup and MyST directives:

            ```{warning}
            Tables are not supported, though.
            ```
        -   Plus, there's syntax highlighting. For example, check out this fork bomb:

            ```sh
            :(){ :|:& };:  # <- don't paste this in bash!
            ```

        [also work]: https://yuio.readthedocs.io/
    """)

if __name__ == "__main__":
    main.run()
