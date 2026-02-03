import pathlib  # [1]_
import yuio.app
import yuio.io

@yuio.app.app()
def main(
    output: pathlib.Path | None = None,  # [2]_
    /,  # [3]_
    *,
    greeting: str = yuio.app.field(default="world", flags=["-g", "--greeting"]),  # [4]_
):
    if output:
        output.write_text(f"Hello, {greeting}!\n")
    else:
        yuio.io.info(f"Hello, `%s`!", greeting)

if __name__ == "__main__":
    main.run()
