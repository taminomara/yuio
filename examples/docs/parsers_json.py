from typing import Annotated
import yuio.app
import yuio.io
import yuio.parse

@yuio.app.app
def main(data: Annotated[list[int], yuio.parse.Json()]):
    yuio.io.success("Loaded data: `%r`", data)

if __name__ == "__main__":
    main.run()
