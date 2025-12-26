import yuio.app
import yuio.io

@yuio.app.app
def main(greeting: str = "world"):
    yuio.io.info("Hello, <c bold green>%s</c>!", greeting)
    yuio.io.info("You're running `Yuio %r`", yuio.version)

if __name__ == "__main__":
    main.run()
