import contextlib
import pathlib

import yuio.app
import yuio.io
import yuio.term


@yuio.app.app
def main(
    #: Where to print program's output.
    output: pathlib.Path | None = yuio.app.field(
        default=None,
        flags=["-o", "--output"],
    ),
):
    with contextlib.ExitStack() as closer:
        if output is None:
            # If output file is not given, print to stdout.
            ch = yuio.io.MessageChannel(to_stdout=True)
        else:
            # Otherwise, print to output.
            output_stream = closer.enter_context(open(output, "w", encoding="utf-8"))
            ch = yuio.io.MessageChannel(
                # We can create `MessageChannel` for a file.
                # Color support will be disabled.
                term=yuio.term.get_term_from_stream(output_stream),
                # We can also override formatting width and other options.
                width=120,
            )

        # Some result that goes to file or to `stdout`.
        result = yuio.io.Stack(
            yuio.io.Hr(),
            yuio.io.Format("Output = %#r", output),
            yuio.io.Format("Term = %#+r", ch.make_repr_context().term),
            yuio.io.Hr(),
        )

        # Print user-facing message to `stderr`.
        yuio.io.success("Result is ready!")

        # Print program result to file or to `stdout`.
        ch.info(result)


if __name__ == "__main__":
    main.run()
