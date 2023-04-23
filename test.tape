Output examples/demo.webm

Require python

Set Shell "bash"
Set WindowBar "Colorful"
Set BorderRadius 10
Set Margin 20
Set MarginFill "#674EFF"
# Set PlaybackSpeed 0.5
# Set TypingSpeed 25ms

Hide
Type "python"
Enter
Type "import yuio.io"
Enter
Type "yuio.io.setup(level=yuio.io.LogLevel.DEBUG)"
Enter
Ctrl+L
Show

Sleep 500ms

Type "yuio.io.info("
Sleep 250ms
Type "'<c:heading><c:b>Yuio:</c> user-friendly IO library!</c>')"
Sleep 150ms
Enter
Sleep 2s

Type "yuio.io.debug('This is a debug message!')"
Sleep 100ms
Enter
Sleep 4s

Type "yuio.io.info('This is an info message!')"
Sleep 100ms
Enter
Sleep 4s

Type "yuio.io.warning('Setting <c:code>X</c> is not defined!')"
Sleep 100ms
Enter
Sleep 4s

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
Type "yuio.io.exception("
Sleep 250ms
Type "'Something went wrong.')"
Sleep 100ms
Enter
Sleep 250ms
Enter
Sleep 4s

Sleep 4s

# Sleep 4s
# Type "python ./examples/io_tasks_multithreaded.py"
# Enter
# Sleep 11s
