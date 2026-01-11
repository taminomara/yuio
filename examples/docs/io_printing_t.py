import yuio.app
import yuio.io

@yuio.app.app
def main():
    yuio.io.heading("Message colors")

    yuio.io.success("Success message is bold green")
    yuio.io.failure("Failure message is bold red")
    yuio.io.info("Info message is default color")
    yuio.io.warning("Warning message is yellow")
    yuio.io.error("Error message is red")

    yuio.io.info(t"Messages can have `{['formatted', 'content']!r}`")

if __name__ == "__main__":
    main.run()
