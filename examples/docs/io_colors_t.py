import yuio.io

if __name__ == "__main__":
    yuio.io.info(
        "Color tags are similar to XML: "
        "<c bold green>this text is bold and green</c>"  # [1]_
    )

    yuio.io.info(
        "Backticks work like in Markdown: "
        "`this is an escaped code, tags like <c red> don't work here.`"
    )

    yuio.io.info(
        "You can escape backticks and other punctuation: "
        "\\`\\<c red> this is normal text \\</c>\\`."
    )

    value = "this string contains <c red>color tags</c>"
    yuio.io.info(
        t"Interpolated values aren't processed: {value}",
    )
