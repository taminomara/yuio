Require python

Set Shell "bash"
Set WindowBar "Colorful"
Set BorderRadius 10

Hide
Type "python"
Enter
Type "import yuio.io"
Enter
Type "yuio.io.setup()"
Enter
Ctrl+L
Show

Sleep 500ms

Type "yuio.io.heading("
Sleep 250ms
Type "'Yuio: a user-friendly IO library!')"
Sleep 150ms
Enter
Sleep 1s

Type "yuio.io.info('This is an "
Sleep 100ms
Type "<c bold>"
Sleep 100ms
Type "info message!</c>')"
Sleep 100ms
Enter
Sleep 1s

Type "yuio.io.warning('Warning: variable `X` is not defined!')"
Sleep 100ms
Enter
Sleep 1s

Type "try:"
Enter
Sleep 350ms
Space 4
Type "raise RuntimeError('fail')"
Enter
Sleep 300ms
Type "except "
Sleep 250ms
Type "RuntimeError:"
Enter
Space 4
Type "yuio.io.error_with_tb("
Sleep 250ms
Type "'Something went wrong!')"
Sleep 100ms
Enter
Sleep 250ms
Enter
Sleep 4s

Ctrl+D
Ctrl+L

Sleep 1s
Type "python ./examples/tasks_multithreaded.py"
Enter
Sleep 12s
Sleep 4s

Ctrl+L

Sleep 1s
Type "python ./examples/io_questions.py"
Enter
Sleep 1s
Up@500ms 2
Sleep 1s
Enter
Sleep 1s
Enter
Sleep 4s
