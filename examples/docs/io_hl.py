import yuio.app
import yuio.io

@yuio.app.app
def main():
    yuio.io.hl(
        """
        {
            "version": "1.0.0",
            "pre-release": false,
            "post-release": false,
        }
        """,
        syntax="json",  # [1]_
    )

if __name__ == "__main__":
    main.run()
