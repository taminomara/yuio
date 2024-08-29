import yuio.io

if __name__ == "__main__":
    yuio.io.heading("Message colors")

    yuio.io.info("Info message is default color.")
    yuio.io.success("Success message is green.")
    yuio.io.warning("Warning message is yellow.")
    yuio.io.error("Error message is red.")

    yuio.io.heading("Exceptions")

    try:
        import json

        json.loads("{ nah, this is not a valid json 😕 }")
    except:
        yuio.io.error_with_tb("Something went horribly wrong!")

    yuio.io.heading("Color tags")

    yuio.io.info("This text is <c red bold>rad!</c>")
    yuio.io.warning("File <c code>example.txt</c> does not exist.")
