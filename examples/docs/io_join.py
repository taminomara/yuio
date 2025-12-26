import yuio.app
import yuio.io

@yuio.app.app
def main():
    ALLOWED_VALUES = ["foo", "bar", "baz"]

    yuio.io.info(
        "Allowed values: %s",
        yuio.io.JoinRepr(ALLOWED_VALUES, color="magenta"),
    )

if __name__ == "__main__":
    main.run()
