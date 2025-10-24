import yuio.app
import yuio.parse
import yuio.io

@yuio.app.app
def main(
    param: list[str] = yuio.app.positional(
        parser=yuio.parse.Json(yuio.parse.List(yuio.parse.Str()))
    )
):
    yuio.io.info("Parsed parameter: `%r`", param)

if __name__ == "__main__":
    main.run()
