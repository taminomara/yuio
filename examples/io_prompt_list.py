import yuio.io

if __name__ == "__main__":
    yuio.io.info(
        "Enter some ints separated by spaces. "
        "Try entering invalid ints and see error messages."
    )

    value = yuio.io.ask[list[int]]("Enter numbers")

    yuio.io.success("You've entered %#r.", value)
