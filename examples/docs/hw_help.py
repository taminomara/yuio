import pathlib
import yuio.app
import yuio.io

@yuio.app.app
def main(
    #: Who do we want to greet?
    greeting: str = yuio.app.field(default="world", flags=["-g", "--greeting"]),
    #: Output file, defaults to printing to `stdout`.
    output: pathlib.Path | None = yuio.app.positional(default=None),
):
    """This is a program for greeting guests."""
    ...

    if output:
        output.write_text(f"Hello, {greeting}!\n")
    else:
        yuio.io.info(f"Hello, `%s`!", greeting)

if __name__ == "__main__":
    main.run()
