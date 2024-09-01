import pathlib
import yuio.app
import yuio.io

@yuio.app.app
def main(
    greeting: str = yuio.app.field("world", flags=["-g", "--greeting"]),
    output: pathlib.Path | None = yuio.app.positional(None),
):
    if output:
        output.write_text(f"Hello, {greeting}!\n")
    else:
        yuio.io.info(f"Hello, `%s`!", greeting)

if __name__ == "__main__":
    main.run()
