import yuio.app
import yuio.io

@yuio.app.app
def main():
    greeting = yuio.io.edit(
        "# Please, edit the greeting:\n"
        "Hello, world!",
        comment_marker="#"
    )

    yuio.io.info("Greeting: `%s`", greeting)

if __name__ == "__main__":
    main.run()
