import contextlib
import pathlib

import yuio.app
import yuio.io


@yuio.app.app
def main(
    #: Where to print program's output.
    output: pathlib.Path | None = yuio.app.field(
        default=None,
        flags=["-o", "--output"],
    ),
):
    """
    Demo of advanced output configuration with Yuio.

    # Output configuration and usage examples:

    When `-o` is not given, and `stdout` is not redirected, program's result
    is printed to terminal. Terminal width and color support are detected as usual:

    ```sh
    python examples/cookbook/print_to_file.py
    ```

    When `stdout` is redirected to a file or piped to another program,
    Yuio disables colors and uses fallback width for formatting:

    ```sh
    python examples/cookbook/print_to_file.py | cat
    ```

    When `stdout` is redirected to a file or piped to another program,
    you can enable colors by passing the `--color` flag:

    ```sh
    python examples/cookbook/print_to_file.py --color | cat
    ```

    When output file is given via the `-o` flag, we create a separate repr context,
    setting target terminal width manually:

    ```sh
    python examples/cookbook/print_to_file.py -o output.txt
    cat output.txt
    ```

    """

    with contextlib.ExitStack() as closer:
        if output is None:
            # If output file is not given, print to stdout.
            ctx = yuio.io.make_repr_context(to_stdout=True)
        else:
            # Otherwise, print to output.
            output_stream = closer.enter_context(open(output, "w", encoding="utf-8"))
            ctx = yuio.io.make_repr_context(
                # We can create `repr_context` for a file. Color support will be disabled.
                file=output_stream,
                # We can also override formatting width.
                width=120,
            )

        # Some result that goes to file or to `stdout`.
        result = yuio.io.Stack(
            yuio.io.Hr(),
            yuio.io.Format("Output = %#r", output),
            yuio.io.Format("Term = %#+r", ctx.term),
            yuio.io.Hr(),
        )

        # Print user-facing message to `stderr`.
        yuio.io.success("Result is ready!")

        # Print program result to file or to `stdout`.
        yuio.io.info(result, ctx=ctx)


if __name__ == "__main__":
    main.run()
