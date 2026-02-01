Set FontSize 26

Source "docs/source/_tapes/_config.tape"

Hide
Type "export COLUMNS=68"
Enter
Ctrl+L
Show

Sleep 200ms
Type "python examples/io_tasks_multithreaded.py"
Enter
Wait
Sleep 2s

Hide
Ctrl+L
Show

Sleep 200ms
Type "python examples/io_prompt.py"
Enter
Sleep 1s
Up@500ms 2
Sleep 500ms
Enter
Sleep 500ms
Enter
Sleep 2s

Hide
Ctrl+L
Show

Sleep 200ms
Type "python examples/app unknown-subcommand"
Enter
Sleep 2s
Type "python examples/app --help 2>&1 | less -R"
Enter
Sleep 1s
Down@100ms 5
Sleep 1s
Down@100ms 5
Sleep 1s
Down@100ms 5
Sleep 1s
Down@100ms 5
Sleep 2s
Down@100ms 15
Sleep 2s
Down@100ms 15
Sleep 2s
Type "q"

Hide
Type "python"
Enter
Type "import yuio.io"
Enter
Type "yuio.io.setup()"
Enter
Wait />>>$/
Ctrl+L
Show

Sleep 200ms

Type "yuio.io.heading("
Sleep 250ms
Type "'Yuio: a user-friendly IO library!')"
Sleep 150ms
Enter
Sleep 500ms

Type "yuio.io.info('This is an "
Sleep 100ms
Type "<c bold green>"
Sleep 100ms
Type "info message!</c>')"
Sleep 100ms
Enter
Sleep 500ms

Type "yuio.io.warning('Warning: variable `X` is not defined!')"
Sleep 100ms
Enter
Sleep 500ms

Type "try:"
Enter
Sleep 350ms
Type "raise RuntimeError('fail')"
Enter
Sleep 200ms
Backspace
Type "except "
Sleep 250ms
Type "RuntimeError:"
Enter
Type "yuio.io.error_with_tb("
Sleep 250ms
Type "'Something went wrong!')"
Sleep 100ms
Enter
Sleep 250ms
Enter
Sleep 2s
