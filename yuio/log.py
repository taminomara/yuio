# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module implements user-friendly output on top of the python's
standard logging library. It adds several special logging levels
for printing tasks with progress bars and other useful things.

Setup
-----

To init the logging system, call the :func:`setup` function. Ideally,
this function should be called at the very beginning of the program execution,
before any code had a chance to log anything. Calling :func:`setup` function
multiple times completely overrides all previous settings.

By default, :func:`setup` determines logging level and whether ANSI color codes
should be used based on environment variables and the state of the output
stream:

- ``DEBUG``: print debug-level messages,
- ``QUIET``: only print warnings, errors, and input prompts,
- ``NO_COLORS``: disable colored output,
- ``FORCE_COLORS``: enable colored output.

You can override this logic by providing your own arguments
to the :func:`setup` function.

.. autofunction:: setup


Logging messages
----------------

Use logging functions from this module (or from the python's :mod:`logging`
module):

.. autofunction:: debug

.. autofunction:: info

.. autofunction:: warning

.. autofunction:: error

.. autofunction:: exception

.. autofunction:: critical


Coloring the output
-------------------

By default, all log messages are colored according to their level.

If you need inline colors, you can use special tags in your log messages::

    yuio.log.info('Using the <c:code>code</c> tag.')

You can combine multiple colors in the same tag::

    yuio.log.info('<c:bold,green>Success!</c>')

To disable tags processing, pass `no_color_tags` flag
to the logging's `extra` object::

    yuio.log.info(
        'this tag --> <c:color> is printed as-is',
        extra=dict(no_color_tags=True)
    )

List of all tags available by default:

- ``code``: for inline code,
- ``note``: for notes, such as default values in user prompts,
- ``success``, ``failure``: for indicating outcome of the program,
- ``question``, ``critical``, ``error``, ``warning``, ``task``,
  ``task_done``, ``task_error``, ``info``, ``debug``:
  used to color log messages,
- ``bold``, ``dim``: font styles,
- ``red``, ``green``, ``yellow``, ``blue``, ``magenta``, ``cyan``, ``normal``:
  font colors.

You can add more tags or change colors of the existing ones by supplying
the `colors` argument to the :func:`setup` function. This argument
is a mapping from a tag name to a :class:`Color` instance::

    yuio.log.setup(
        colors=dict(
            success=yuio.log.FORE_BLUE | yuio.log.STYLE_BOLD
        )
    )

.. autoclass:: Color

List of all pre-defined codes:

.. autodata:: STYLE_BOLD

.. autodata:: STYLE_DIM

.. autodata:: FORE_NORMAL

.. autodata:: FORE_BLACK

.. autodata:: FORE_RED

.. autodata:: FORE_GREEN

.. autodata:: FORE_YELLOW

.. autodata:: FORE_BLUE

.. autodata:: FORE_MAGENTA

.. autodata:: FORE_CYAN

.. autodata:: FORE_WHITE

.. autodata:: BACK_NORMAL

.. autodata:: BACK_BLACK

.. autodata:: BACK_RED

.. autodata:: BACK_GREEN

.. autodata:: BACK_YELLOW

.. autodata:: BACK_BLUE

.. autodata:: BACK_MAGENTA

.. autodata:: BACK_CYAN

.. autodata:: BACK_WHITE


Indicating progress
-------------------

You can use the :class:`Task` class to indicate status and progress
of some task:

.. autoclass:: Task
   :members:


Querying user input
-------------------

To query some input from a user, there's the :func:`ask` function:

.. autofunction:: ask


"""

import getpass
import logging
import os
import re
import sys
import threading
import typing as _t
from dataclasses import dataclass

import yuio.parse

QUESTION = 100
CRITICAL = 50
ERROR = 40
WARNING = 30
TASK_BEGIN = 24
TASK_PROGRESS = 23
TASK_DONE = 22
TASK_ERROR = 21
INFO = 20
DEBUG = 10
NOTSET = 0


@dataclass(frozen=True)
class Color:
    """ANSI color code.

    See the list of all available codes
    at `Wikipedia <https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_(Select_Graphic_Rendition)_parameters>`_.

    Example::

        # 31 is a color code for red
        BOLD_RED = Color(fore=31, bold=True)

    You can combine multiple colors::

        BOLD_RED = FORE_RED | STYLE_BOLD

    """

    # Note: other font styles besides bold and dim are not implemented
    # because their support in terminals is limited.

    fore: _t.Optional[int] = None
    back: _t.Optional[int] = None
    bold: bool = False
    dim: bool = False

    def __or__(self, other: 'Color'):
        return Color(
            other.fore if other.fore is not None else self.fore,
            other.back if other.back is not None else self.back,
            self.bold or other.bold,
            self.dim or other.dim,
        )

    def __str__(self):
        codes = ['0']
        if self.fore is not None:
            codes.append(str(self.fore))
        if self.back is not None:
            codes.append(str(self.back))
        if self.bold:
            codes.append('1')
        if self.dim:
            codes.append('2')
        return '\033[' + ';'.join(codes) + 'm'


#: Bold font style.
STYLE_BOLD = Color(bold=True)
#: Dim font style.
STYLE_DIM = Color(dim=True)

#: Normal foreground color.
FORE_NORMAL = Color(fore=39)
#: Black foreground color.
FORE_BLACK = Color(fore=30)
#: Red foreground color.
FORE_RED = Color(fore=31)
#: Green foreground color.
FORE_GREEN = Color(fore=32)
#: Yellow foreground color.
FORE_YELLOW = Color(fore=33)
#: Blue foreground color.
FORE_BLUE = Color(fore=34)
#: Magenta foreground color.
FORE_MAGENTA = Color(fore=35)
#: Cyan foreground color.
FORE_CYAN = Color(fore=36)
#: White foreground color.
FORE_WHITE = Color(fore=37)

#: Normal background color.
BACK_NORMAL = Color(back=49)
#: Black background color.
BACK_BLACK = Color(back=40)
#: Red background color.
BACK_RED = Color(back=41)
#: Green background color.
BACK_GREEN = Color(back=42)
#: Yellow background color.
BACK_YELLOW = Color(back=43)
#: Blue background color.
BACK_BLUE = Color(back=44)
#: Magenta background color.
BACK_MAGENTA = Color(back=45)
#: Cyan background color.
BACK_CYAN = Color(back=46)
#: White background color.
BACK_WHITE = Color(back=47)

DEFAULT_FORMATTER = logging.Formatter(
    '%(message)s'
)

DEFAULT_COLORS = {
    'code': FORE_MAGENTA,
    'note': FORE_GREEN,
    'success': FORE_GREEN | STYLE_BOLD,
    'failure': FORE_RED | STYLE_BOLD,

    'question': FORE_BLUE,
    'critical': FORE_WHITE | BACK_RED,
    'error': FORE_RED,
    'warning': FORE_YELLOW,
    'task': FORE_BLUE,
    'task_done': FORE_BLUE,
    'task_error': FORE_RED,
    'info': FORE_NORMAL,
    'debug': STYLE_DIM,

    'bold': STYLE_BOLD,
    'dim': STYLE_DIM,
    'red': FORE_RED,
    'green': FORE_GREEN,
    'yellow': FORE_YELLOW,
    'blue': FORE_BLUE,
    'magenta': FORE_MAGENTA,
    'cyan': FORE_CYAN,
    'normal': FORE_NORMAL,
}

T = _t.TypeVar('T')

_HANDLER_LOCK = threading.Lock()
_HANDLER = None


def setup(
    level: _t.Optional[int] = None,
    stream: _t.Any = sys.stderr,
    use_colors: _t.Optional[bool] = None,
    formatter: logging.Formatter = DEFAULT_FORMATTER,
    colors: _t.Optional[_t.Dict[str, Color]] = None,
):
    """Initial setup of the logging facilities.

    :param level:
        log output level. If not given, will check ``DEBUG`` and ``QUIET``
        environment variables to determine an appropriate logging level.
    :param stream:
        a stream where to output messages. Uses `stderr` by default.
    :param use_colors:
        use ANSI escape sequences to color the output. If not given, will
        check ``NO_COLORS`` and ``FORCE_COLORS`` environment variables,
        and also if the given `stream` is a tty one.
    :param formatter:
        formatter for log messages.
    :param colors:
        mapping from tag name or logging level name to a :class:`Color`.
        Logging level names and tag names are all lowercase.

    """

    global _HANDLER

    with _HANDLER_LOCK:
        if _HANDLER is None:
            _HANDLER = _Handler()

            logger = logging.getLogger()
            logger.addHandler(_HANDLER)
            logger.setLevel(NOTSET)

            logging.addLevelName(QUESTION, "QUESTION")
            logging.addLevelName(TASK_BEGIN, "TASK")
            logging.addLevelName(TASK_PROGRESS, "TASK")
            logging.addLevelName(TASK_DONE, "TASK_DONE")
            logging.addLevelName(TASK_ERROR, "TASK_ERROR")

        if level is None:
            if 'DEBUG' in os.environ:
                level = DEBUG
            elif 'QUIET' in os.environ:
                level = WARNING
            else:
                level = INFO

        _HANDLER.setLevel(level)
        _HANDLER.setFormatter(formatter)
        _HANDLER.setStream(stream)

        full_colors = DEFAULT_COLORS.copy()
        if colors is not None:
            full_colors.update(colors)

        _HANDLER.setColors(full_colors)

        if use_colors is None:
            if 'NO_COLORS' in os.environ:
                use_colors = False
            elif 'FORCE_COLORS' in os.environ:
                use_colors = True
            else:
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

    Note: prefer using the :class:`Task` context manager
    instead of this function.

    """

    logging.log(TASK_BEGIN, msg, *args)


def task_progress(msg: str, *args, progress: float):
    """Indicate progress of some task.

    If this function is called after :func:`task_begin`, the task message will
    be updated with a progress bar. If there were other log messages
    between :meth:`task_begin` and call to this function, nothing will happen.

    Note: prefer using the :class:`Task` context manager
    instead of this function.

    """

    extra = {'progress': progress}
    logging.log(TASK_PROGRESS, msg, *args, extra=extra)


def task_done(msg: str, *args):
    """Indicate that some task is finished successfully.

    Note: prefer using the :class:`Task` context manager
    instead of this function.

    """

    logging.log(TASK_DONE, msg, *args)


def task_error(msg: str, *args):
    """Indicate that some task is finished with an error.

    Note: prefer using the :class:`Task` context manager
    instead of this function.

    """

    logging.log(TASK_ERROR, msg, *args)


def task_exception(msg: str, *args):
    """Indicate that some task is finished, capture current exception.

    Note: prefer using the :class:`Task` context manager
    instead of this function.

    """

    logging.log(TASK_ERROR, msg, *args, exc_info=True)


def question(msg: str, *args):
    """Log a message with input prompts and other user communications.

    These messages don't end with newline. They also have high priority,
    so they will not be filtered by log level settings.

    """

    logging.log(QUESTION, msg, *args)


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

    This will output the following:

    .. code-block:: text

       Fetching data... [=====>              ] 30%

    Note that you don't have to use it in a context::

        task = Task('Fetching data')
        task.begin()

        for i, url in enumerate(urls):
            url.fetch()
            task.progress(float(i) / len(urls))

        task.done()

    In this case, however, it's up to you to catch and report errors.

    """

    def __init__(self, msg: str, *args):
        if args:
            msg = msg % args
        self._msg = msg

        self._started = False
        self._finished = False

    def begin(self):
        """Emit a message about task being in progress.

        """

        if not self._started:
            task_begin(self._msg)
            self._started = True

    def progress(self, progress: float):
        """Indicate progress of ths task, measured from ``0`` to ``1``.

        """

        if self._started and not self._finished:
            task_progress(self._msg, progress=progress)

    def done(self):
        """Emit a message that the task is finished successfully.

        """

        if self._started and not self._finished:
            task_done(self._msg)
            self._finished = True

    def error(self):
        """Emit a message that the task is finished with an error.

        """

        if self._started and not self._finished:
            task_error(self._msg)
            self._finished = True

    def exception(self):
        """Emit a message that the task is finished, capture current exception.

        """

        if self._started and not self._finished:
            task_exception(self._msg)
            self._finished = True

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.done()
        else:
            self.error()


@_t.overload
def ask(
    msg: str,
    *args,
    default: _t.Optional[str] = None,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    hidden: bool = False,
) -> str: ...


@_t.overload
def ask(
    msg: str,
    *args,
    parser: yuio.parse.Parser[T],
    default: _t.Optional[T] = None,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    hidden: bool = False,
) -> T: ...


def ask(
    msg,
    *args,
    parser=None,
    default=None,
    input_description=None,
    default_description=None,
    hidden=False,
):
    """Ask user to provide an input, then parse it and return a value.

    Example::

        answer = ask(
            'Do you want a choco bar?',
            parser=yuio.parse.Bool(),
            default=True,
        )

    :param msg:
        prompt that will be sent to the user.
    :param args:
        arguments for prompt formatting.
    :param parser:
        how to parse and verify the input. See :mod:`yuio.parse` for more
        info.
    :param default:
        if given, this value will be returned if no input is provided.
    :param input_description:
        a string that describes expected input, like ``'yes/no'`` for boolean
        inputs. By default, inferred from the given parser.
    :param default_description:
        a string that describes the `default` value. By default,
        inferred from the given parser and `repr` of the default value.
    :param hidden:
        if enabled, treats input as password, and uses secure input methods.
        This option also hides errors from the parser, because they may contain
        user input.

    """

    if parser is None:
        parser = str

    desc = ''

    if input_description is None and hasattr(parser, 'describe'):
        input_description = getattr(parser, 'describe')()
    if input_description:
        desc += f' ({input_description})'

    if default is not None:
        if default_description is None and hasattr(parser, 'describe_value'):
            default_description = getattr(parser, 'describe_value')(default)
        if default_description is None:
            default_description = str(default)
        if default_description:
            desc += f' [<c:note>{default_description}</c>]'

    if desc:
        desc += ': '
    else:
        desc = ' '

    if args:
        msg = msg % args
    msg = msg + desc

    while True:
        question(msg)
        if hidden:
            answer = getpass.getpass(prompt='')
        else:
            answer = input()
        if not answer and default is not None:
            return default
        elif not answer:
            error('Input is required.')
        else:
            try:
                return parser(answer)
            except Exception as e:
                if hidden:
                    error('Error: invalid value.')
                else:
                    error(f'Error: {e}.')


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

    def setColors(self, colors: _t.Dict[str, Color]):
        self._colors = colors

    def flush(self):
        self.acquire()
        try:
            self._stream.flush()
        finally:
            self.release()

    def emit(self, record: logging.LogRecord):
        record.message = record.getMessage()

        message = self._colorize(self.format(record), record)
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
                is_multiline = self._print_task(message, status, progress)

                if record.levelno != TASK_PROGRESS or is_multiline:
                    # If new task record is multiline, we won't be able
                    # to redraw it next time, so we need to clear the task.
                    # If the task is finished, we also need to clear it.
                    self._stream.write('\n')
                    self._current_task = None
        elif record.levelno == TASK_PROGRESS:
            # We can't update status of a non-current task, so just ignore it.
            return
        else:
            if self._current_task is not None:
                # We need to clear current task before printing
                # new log messages.

                if self._use_colors:
                    # If we are using colors, we want to clear progress bar
                    # and leave just a task description with an ellipsis.
                    current_task_message = self._colorize(
                        self.format(self._current_task),
                        self._current_task)
                    self._clear_line()
                    self._print_task(current_task_message, '', None)

                self._stream.write('\n')
                self._current_task = None
                self._reset_color()

            is_multiline = self._print_task(message, status, progress)

            if record.levelno == TASK_BEGIN and not is_multiline:
                # If we've started a new task, mark is as current.
                # If this task's message is multiline, though,
                # don't mark it as current, and treat it as a regular
                # log message, though, because we can't redraw multiline tasks.
                self._current_task = record
            elif record.levelno != QUESTION:
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

    def _reset_color(self):
        if self._use_colors:
            self._stream.write(str(Color()))

    _TAG_RE = re.compile(r'<c:(?P<name>[a-z0-9, _-]+)>|</c>')

    def _colorize(self, msg: str, record: logging.LogRecord):
        if getattr(record, 'no_color_tags', False):
            return msg

        if not self._use_colors:
            return self._TAG_RE.sub('', msg)

        default_color = self._colors.get(record.levelname.lower(), Color())
        default_color = FORE_NORMAL | BACK_NORMAL | default_color

        out = ''
        last_pos = 0
        stack = [default_color]

        out += str(default_color)

        for tag in self._TAG_RE.finditer(msg):
            out += msg[last_pos:tag.span()[0]]
            last_pos = tag.span()[1]

            name = tag.group('name')
            if name:
                color = stack[-1]
                for sub_name in name.split(','):
                    sub_name = sub_name.strip()
                    color = color | self._colors.get(sub_name, Color())
                out += str(color)
                stack.append(color)
            elif len(stack) > 1:
                stack.pop()
                out += str(stack[-1])

        out += msg[last_pos:]

        return out

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
