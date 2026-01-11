import yuio.app
import yuio.io

@yuio.app.app
def main():
    yuio.io.rst("""
        Greetings!
        ----------

        -   You can use *inline formatting*, ``backticks``,
            and :py:class:`interpreted text <yuio.md.MdParser>`.
        -   Hyperlinks `also work`__!
        -   You can also use some common directives, though not all of them:

            .. warning::

                Oh, and tables are not supported, at least for now.

        -   Plus, there's syntax highlighting. For example, check out this fork bomb:

            .. code-block:: sh

                :(){ :|:& };:  # <- don't paste this in bash!

        __ https://yuio.readthedocs.io/
    """)

if __name__ == "__main__":
    main.run()
