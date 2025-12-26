import yuio.app
import yuio.io
import yuio.parse

@yuio.app.app
def main():
    parser = yuio.parse.Gt(yuio.parse.Int(), 0)
    result = yuio.io.ask("Choose a number", parser=parser)
    yuio.io.success("You chose `%s`", result)

if __name__ == "__main__":
    main.run()
