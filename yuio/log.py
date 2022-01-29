# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""Logging, pretty printing, and user interactions.

This module implements user-friendly output on top of the python's
standard logging library. It adds several special logging levels
for printing tasks with progress bars and other useful things.

Usage:

Init this module using the `setup` function. Preferably, init this in the very
beginning of your main method, before any code had a change to log anything.
You can update the parameters later by calling `setup` second time.

Use either logging functions from this module, or the standard functions
from the `logging` module to emit messages.

Use the `Task` context manager to print on-going tasks and their progress.

Use the `ask` method to request user input.

"""

import logging
import os
import sys
import threading
import typing as _t

__all__ = (
    'USER_IO',
    'CRITICAL',
    'ERROR',
    'WARNING',
    'TASK_BEGIN',
    'TASK_PROGRESS',
    'TASK_DONE',
    'TASK_ERROR',
    'INFO',
    'DEBUG',
    'NOTSET',

    'DEFAULT_FORMATTER',
    'DEFAULT_COLORS',

    'setup',
    'debug',
    'info',
    'warning',
    'error',
    'exception',
    'critical',
    'task_begin',
    'task_progress',
    'task_done',
    'task_error',
    'task_exception',
    'user_io',

    'Task',

    'ask',
)

USER_IO: _t.Final[int] = 100
CRITICAL: _t.Final[int] = 50
ERROR: _t.Final[int] = 40
WARNING: _t.Final[int] = 30
TASK_BEGIN: _t.Final[int] = 24
TASK_PROGRESS: _t.Final[int] = 23
TASK_DONE: _t.Final[int] = 22
TASK_ERROR: _t.Final[int] = 22
INFO: _t.Final[int] = 20
DEBUG: _t.Final[int] = 10
NOTSET: _t.Final[int] = 0

DEFAULT_FORMATTER: _t.Final[logging.Formatter] = logging.Formatter(
    '-> %(message)s'
)

DEFAULT_COLORS: _t.Final[_t.Dict[int, str]] = {
    CRITICAL: '\033[31m',  # red
    ERROR: '\033[31m',  # red
    WARNING: '\033[33m',  # yellow
    INFO: '\033[0m',  # normal
    DEBUG: '\033[2m',  # dim
    NOTSET: '\033[0m',  # normal

    USER_IO: '\033[1m',  # bold
    TASK_BEGIN: '\033[1m',  # bold
    TASK_PROGRESS: '\033[1m',  # bold
    TASK_DONE: '\033[1;32m',  # bold green
    TASK_ERROR: '\033[1;31m',  # bold red
}

T = _t.TypeVar('T')

_HANDLER_LOCK = threading.Lock()
_HANDLER = None


def setup(
    level: _t.Optional[int] = None,
    stream: _t.Any = sys.stderr,
    use_colors: _t.Optional[bool] = None,
    formatter: logging.Formatter = DEFAULT_FORMATTER,
    colors: _t.Dict[int, str] = DEFAULT_COLORS,
):
    """Initial setup of the logging facilities.

    Ideally, this function should be called at the very beginning
    of the program execution.

    Calling this function multiple times completely overrides
    all previous settings.

    :param level:
        log output level. If not given, will use `INFO` or `DEBUG`, depending
        on whether there is a `DEBUG_OUT` environment variable present.
    :param stream:
        a stream where to output messages. Uses `stderr` by default.
    :param use_colors:
        use ANSI escape sequences to color the output. If not given, will
        detect whether the given `stream` is a tty one, and enable colors
        accordingly.
    :param formatter:
        formatter for log messages.
    :param colors:
        mapping from logging level to ANSI escape code with its color.

    """

    global _HANDLER

    with _HANDLER_LOCK:
        if _HANDLER is None:
            _HANDLER = _Handler()

            logger = logging.getLogger()
            logger.addHandler(_HANDLER)
            logger.setLevel(NOTSET)

            logging.addLevelName(USER_IO, "USER_IO")
            logging.addLevelName(TASK_BEGIN, "INFO")
            logging.addLevelName(TASK_PROGRESS, "INFO")
            logging.addLevelName(TASK_DONE, "INFO")
            logging.addLevelName(TASK_ERROR, "INFO")

        if level is None:
            if 'DEBUG_OUT' in os.environ:
                level = DEBUG
            else:
                level = INFO

        _HANDLER.setLevel(level)
        _HANDLER.setFormatter(formatter)
        _HANDLER.setStream(stream)
        _HANDLER.setColors(colors)

        if use_colors is None:
            use_colors = stream.isatty()

        _HANDLER.setUseColors(use_colors)


def debug(msg: str, *args, **kwargs):
    """Log a debug message.

    """

    logging.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    """Log an info message.

    """

    logging.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    """Log a warning message.

    """

    logging.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    """Log an error message.

    """

    logging.error(msg, *args, **kwargs)


def exception(msg: str, *args, exc_info=True, **kwargs):
    """Log an error message and capture the current exception.

    Call this function in the `except` clause of a `try` block
    or in an `__exit__` function of a context manager to attach
    current exception details to the log message.

    """

    logging.exception(msg, *args, exc_info=exc_info, **kwargs)


def critical(msg: str, *args, **kwargs):
    """Log a critical error message.

    """

    logging.critical(msg, *args, **kwargs)


def task_begin(msg: str, *args):
    """Indicate beginning of some task.

    Note: prefer using the `Task` context manager instead of this function.

    """

    logging.log(TASK_BEGIN, msg, *args)


def task_progress(msg: str, *args, progress: float):
    """Indicate progress of some task.

    If this function is called after `task_begin`, the task message will
    be updated with a progress bar. If there were other log messages
    between `task_begin` and call to this function, nothing will happen.

    Note: prefer using the `Task` context manager instead of this function.

    """

    extra = {'progress': progress}
    logging.log(TASK_PROGRESS, msg, *args, extra=extra)


def task_done(msg: str, *args):
    """Indicate that some task is finished successfully.

    Note: prefer using the `Task` context manager instead of this function.

    """

    logging.log(TASK_DONE, msg, *args)


def task_error(msg: str, *args):
    """Indicate that some task is finished with an error.

    Note: prefer using the `Task` context manager instead of this function.

    """

    logging.log(TASK_ERROR, msg, *args)


def task_exception(msg: str, *args):
    """Indicate that some task is finished, capture current exception.

    Note: prefer using the `Task` context manager instead of this function.

    """

    logging.log(TASK_ERROR, msg, *args, exc_info=True)


def user_io(msg: str, *args):
    """Log a message with input prompts and other user communications.

    These messages have high priority, so they will not be filtered
    by log level settings. Thus, it is safe to use them for messages
    that should be shown to a user no matter what.

    """

    logging.log(USER_IO, msg, *args)


class Task:
    """Context manager that automatically reports tasks and their progress.

    This context manager accepts a name of the task being done,
    along with all the usual logging parameters.

    When context is entered, it emits a message that the task is in progress.

    When context is exited, it emits a message that the task has finished.

    If an exception is thrown out of context, it emits a message that the
    task has failed.

    Example::

        with Task('Fetching data') as task:
            for i, url in enumerate(urls):
                url.fetch()
                task.progress(float(i) / len(urls))

    """

    def __init__(self, msg: str, *args):
        if args:
            msg = msg % args
        self._msg = msg

    def begin(self):
        """Emit a message about task being in progress.

        """

        task_begin(self._msg)

    def progress(self, progress: float):
        """Indicate progress of ths task, measured from `0` to `1`.

        """

        task_progress(self._msg, progress=progress)

    def done(self):
        """Emit a message that the task is finished successfully.

        """

        task_done(self._msg)

    def error(self):
        """Emit a message that the task is finished with an error.

        """

        task_error(self._msg)

    def exception(self):
        """Emit a message that the task is finished, capture current exception.

        """

        task_exception(self._msg)

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.done()
        else:
            self.error()


def ask(
    parser: _t.Callable[[str], T],
    msg: str, *args,
    default: _t.Optional[str] = None
) -> T:
    """Ask user to provide an input, then parse it and return a value.

    :param parser:
        how to parse and verify the input.
    :param msg:
        prompt that will be sent to the user.
    :param args:
        arguments for prompt formatting.
    :param default:
        if given, default input will be passed to the parser if user sends
        an empty string.

    """

    if default is not None:
        desc = f' [default={default}]:'
    else:
        desc = ':'
    while True:
        user_io(msg + desc, *args)
        answer = input().strip()
        if not answer and default is not None:
            return parser(default)
        elif not answer:
            user_io('Input is required')
        else:
            try:
                return parser(answer)
            except ValueError as e:
                user_io(f'Error: {e}')


class _Handler(logging.Handler):
    def __init__(self):
        super().__init__()

        self._use_colors: bool = sys.stderr.isatty()
        self._stream: _t.Any = sys.stderr
        self._current_task: _t.Optional[logging.LogRecord] = None
        self._colors = DEFAULT_COLORS

        self.setFormatter(logging.Formatter('-> %(message)s'))

    def setStream(self, stream):
        self._stream = stream

    def setUseColors(self, use_colors: bool):
        self._use_colors = use_colors

    def setColors(self, colors: _t.Dict[int, str]):
        self._colors = colors

    def flush(self):
        self.acquire()
        try:
            self._stream.flush()
        finally:
            self.release()

    def emit(self, record: logging.LogRecord):
        record.message = record.getMessage()

        message = self.format(record)
        is_current_task = (
            record.levelno in (TASK_PROGRESS, TASK_DONE, TASK_ERROR)
            and self._current_task is not None
            and record.message == self._current_task.message
        )

        if record.levelno == TASK_DONE:
            status = 'OK'
            progress = None
        elif record.levelno == TASK_ERROR:
            status = 'ERROR'
            progress = None
        elif record.levelno in (TASK_BEGIN, TASK_PROGRESS):
            status = ''
            progress = getattr(record, 'progress', None)
        else:
            status = None
            progress = None

        if is_current_task:
            # When we're updating current task, the console looks something
            # like this:
            #
            # ```
            # -> Some previous message.
            # -> Some previous message.
            # -> Task description...|
            # ```
            #                       ^ cursor is at the end of the current line
            #
            # If we don't support colors, the only thing we can do is to print
            # task's status after the ellipsis and be done with it.
            #
            # If we support colors, we clear the current line, and redraw
            # the task message completely, including its current status
            # and progress.
            #
            # If the new message is multiline, though, we won't be able
            # to clear it and redraw next time. So we print it with a newline
            # at the end and clear the current task.

            if not self._use_colors and record.levelno == TASK_PROGRESS:
                # There is nothing we can do to indicate progress w/o colors.
                pass
            elif not self._use_colors:
                # Write status after the ellipsis and clear the task.
                self._stream.write(f' {status}\n')
                self._current_task = None
            else:
                # Redraw the current task.
                self._clear_line()
                self._set_color(record.levelno)
                is_multiline = self._print_task(message, status, progress)

                if record.levelno != TASK_PROGRESS or is_multiline:
                    # If new task record is multiline, we won't be able
                    # to redraw it next time, so we need to clear the task.
                    # If the task is finished, we also need to clear it.
                    self._stream.write('\n')
                    self._current_task = None
        elif record.levelno == TASK_PROGRESS:
            # We can't update status of a non-current task, so just ignore it.
            pass
        else:
            if self._current_task is not None:
                # We need to clear current task before printing
                # new log messages.

                if self._use_colors:
                    # If we are using colors, we want to clear progress bar
                    # and leave just a task description with an ellipsis.
                    current_task_message = self.format(self._current_task)
                    self._clear_line()
                    self._set_color(TASK_PROGRESS)
                    self._print_task(current_task_message, '', None)

                self._stream.write('\n')
                self._current_task = None

            self._set_color(record.levelno)
            is_multiline = self._print_task(message, status, progress)

            if record.levelno == TASK_BEGIN and not is_multiline:
                # If we've started a new task, mark is as current.
                # If this task's message is multiline, though,
                # don't mark it as current, and treat it as a regular
                # log message, though, because we can't redraw multiline tasks.
                self._current_task = record
            else:
                self._stream.write('\n')

        self._reset_color()

        self.flush()

    def _print_task(
        self,
        message: str,
        status: _t.Optional[str],
        progress: _t.Optional[float],
    ) -> bool:
        lines = message.split('\n')
        is_multiline = len(lines) > 1

        self._stream.write(lines[0])

        if status is not None:
            # Status is set for any task. If status is an empty line,
            # the task is in progress, so we only need an ellipsis.
            self._stream.write('...')
            if status:
                self._stream.write(' ' + status)

        if progress is not None and not is_multiline:
            # Never print progressbar for multiline messages because
            # we won't be able to update this progress bar in the future.
            self._stream.write(' ')
            self._stream.write(self._make_progress_bar(progress))

        if is_multiline:
            self._stream.write('\n')
            self._stream.write('\n'.join(lines[1:]))

        return is_multiline

    def _clear_line(self):
        if self._use_colors:
            self._stream.write(f'\033[2K\r')

    def _set_color(self, level: int):
        if self._use_colors:
            self._stream.write(self._colors.get(level, ''))

    def _reset_color(self):
        if self._use_colors:
            self._stream.write('\033[0m')

    @staticmethod
    def _make_progress_bar(progress: float):
        if progress < 0:
            progress = 0
        elif progress > 1:
            progress = 1

        done = int(20 * progress)
        infl = 0
        left = 20 - done

        if 0 < done < 20:
            infl = 1
            done -= 1

        return '[' \
               + '=' * done \
               + '>' * infl \
               + ' ' * left \
               + ']' \
               + f' {progress:0.0%}'
