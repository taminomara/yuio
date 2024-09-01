import yuio.app
import yuio.io

@yuio.app.app
def main(greeting: str = "world"):
    yuio.io.info(f"Hello, <c bold green>%s</c>!", greeting)

if __name__ == "__main__":
    main.run()
