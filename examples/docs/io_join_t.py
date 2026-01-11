import yuio.app
import yuio.io

@yuio.app.app
def main():
    ALLOWED_VALUES = ["foo", "bar", "baz"]

    yuio.io.info(
        t"Allowed values: {yuio.io.JoinRepr(ALLOWED_VALUES, color='magenta')}",  # [1]_
    )

if __name__ == "__main__":
    main.run()
