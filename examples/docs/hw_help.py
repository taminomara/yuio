import pathlib
import yuio.app
import yuio.io

@yuio.app.app(doc_format="md")  # [1]_
def main(
    #: Output file, defaults to printing to `stdout`.  [2]_
    output: pathlib.Path | None = None,
    /,
    *,
    #: Who do we want to greet?
    greeting: str = yuio.app.field(default="world", flags=["-g", "--greeting"]),
):
    """
    This is a program for greeting guests.  [3]_

    """

    ...

    if output:
        output.write_text(f"Hello, {greeting}!\n")
    else:
        yuio.io.info(f"Hello, `%s`!", greeting)

if __name__ == "__main__":
    main.run()
