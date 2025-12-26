import yuio.app
import yuio.io

@yuio.app.app
def main(greeting: str = "world"):
    yuio.io.md("""
        # Dear %s,

        - You can use `` `backticks` `` with all functions from `yuio.io`.
        - You can also use CommonMark block markup with `yuio.io.md`.
        - For example, check out this fork bomb:

          ```sh
          :(){ :|:& };:  # <- don't paste this in bash!
          ```
    """, greeting)

if __name__ == "__main__":
    main.run()
