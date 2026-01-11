import yuio.app
import yuio.io  # [1]_

@yuio.app.app()
def main(greeting: str = "world"):
    yuio.io.info("Hello, <c bold green>%s</c>!", greeting)  # [2]_
    yuio.io.info("You're running `Yuio %r`", yuio.version)  # [3]_

if __name__ == "__main__":
    main.run()
