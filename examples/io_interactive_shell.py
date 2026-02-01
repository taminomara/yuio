import yuio.io

if __name__ == "__main__":
    yuio.io.heading("Interactive shell showcase")

    yuio.io.md(
        """
        This script launches your preferred shell and gives you control over it.
        When you exit, it continues execution.

        For example, imagine a script that bumps package version, commits it,
        and creates a release. You might want to give user a chance to inspect
        repository state before commit by running `yuio.io.shell`.
        """
    )
    yuio.io.br()
    yuio.io.wait_for_user()

    yuio.io.hr()
    yuio.io.success(
        "Starting an interactive shell. Press <c kbd>Ctrl+D</c> to exit and proceed."
    )
    result = yuio.io.shell(prompt_marker="(yuio shell example)")
    yuio.io.hr()
    yuio.io.success("Continuing execution...")
