# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module implements user-friendly input and output on top of the python's
standard logging library.

Setup
-----

Yuio configures itself upon import, so you can just start using it.

By default, yuio determines logging level
and whether ANSI color codes should be used
based on state of the output stream
and the following environment variables:

- ``DEBUG``: print debug-level messages,
- ``QUIET``: only print warnings, errors, and input prompts,
- ``NO_COLORS``: disable colored output,
- ``FORCE_COLORS``: enable colored output.

You can change defaults by calling the :func:`setup` function.

.. autofunction:: setup


Logging messages
----------------

Use logging functions from this module:

.. autofunction:: debug

.. autofunction:: info

.. autofunction:: warning

.. autofunction:: error

.. autofunction:: exception

.. autofunction:: critical

.. autofunction:: question


Coloring the output
-------------------

By default, all log messages are colored according to their level.

If you need inline colors, you can use special tags in your log messages::

    info('Using the <c:code>code</c> tag.')

You can combine multiple colors in the same tag::

    info('<c:bold,green>Success!</c>')

To disable tags processing, pass `process_color_tags`
to the logging's `extra` object::

    info(
        'this tag --> <c:color> is printed as-is',
        extra=dict(yuio_process_color_tags=False)
    )

List of all tags that are available by default:

- ``code``: for inline code,
- ``note``: for notes, such as default values in user prompts,
- ``success``, ``failure``: for indicating outcome of the program,
- ``question``, ``critical``, ``error``, ``warning``, ``info``, ``debug``:
  used to color log messages,
- ``task``, ``task_done``, ``task_error``:
  used to color tasks,
- ``bold``, ``b``, ``dim``: font styles,
- ``red``, ``green``, ``yellow``, ``blue``, ``magenta``, ``cyan``, ``normal``:
  font colors.

You can add more tags or change colors of the existing ones by supplying
the `colors` argument to the :func:`setup` function. This argument
is a mapping from a tag name to a :class:`Color` instance::

    setup(
        colors=dict(
            success=FORE_BLUE | STYLE_BOLD
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

You can prompt user to edit something with the :func:`edit` function.
Note that this function doesn't add any header with an explanation
to the given text, so you will need to do it yourself:

.. autofunction:: edit

There are some helper functions and classes:

.. autofunction:: is_interactive

.. autofunction:: detect_editor

.. autoclass:: UserIoError
   :members:

Suspending logging
------------------

You can temporarily disable logging and printing tasks
using the :class:`SuspendLogging` context manager.

.. autoclass:: SuspendLogging
   :members:

Python's `logging` and yuio
---------------------------

Yuio uses :mod:`logging` to pass messages to the renderer.
It sets up the following logger hierarchy:

.. digraph:: logger_hierarchy
   :caption: Logger hierarchy

   rankdir="LR"

   node[shape=rect]

   edge[dir=back]

   msg[shape=plain label=<
     <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="1">
       <TR>
         <TD>msg</TD>
       </TR>
       <TR>
         <TD>
           <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">
             <TR>
               <TD><FONT POINT-SIZE="10.0">yuio.io.Handler</FONT></TD>
             </TR>
           </TABLE>
         </TD>
       </TR>
     </TABLE>
   >]

   root -> yuio
   yuio -> msg [style=dashed label="propagate=False"]
   msg -> {exec, question};
   root -> "...";

``yuio.msg`` collects everything that should be printed on the screen
and passes it to a handler. It has its propagation disabled,
so yuio's messages never reach the root logger. This means that you can set up
other loggers and handlers without yuio interfering.

If you want to direct yuio messages somewhere else (i.e to a file),
either add a handler to ``yuio.msg`` or enable propagation for it.

Since messages and questions from :mod:`yuio.exec` are logged to
``yuio.msg.question`` and ``yuio.msg.exec``,
you can filter them out from your handlers or the root logger.

If you want to direct messages from some other logger into yuio,
you can add a :class:`Handler`:

.. autoclass:: Handler

"""

import enum
import getpass
import logging
import os
import re
import string
import subprocess
import tempfile
import threading
import typing as _t
from dataclasses import dataclass
from logging import LogRecord

import sys

import yuio.parse
from yuio._utils import Disabled, DISABLED

T = _t.TypeVar('T')
_PROGRESS = _t.Union[None, int, float, _t.Tuple[int, int], _t.Tuple[int, int, int]]


class UserIoError(IOError):
    """Raised when interaction with user fails.

    """


QUESTION = 100
CRITICAL = logging.CRITICAL
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
DEBUG = logging.DEBUG
NOTSET = logging.NOTSET


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

    def __or__(self, other: 'Color', /):
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
    'task_done': FORE_GREEN,
    'task_error': FORE_RED,
    'info': FORE_NORMAL,
    'debug': STYLE_DIM,

    'bold': STYLE_BOLD,
    'b': STYLE_BOLD,
    'dim': STYLE_DIM,
    'red': FORE_RED,
    'green': FORE_GREEN,
    'yellow': FORE_YELLOW,
    'blue': FORE_BLUE,
    'magenta': FORE_MAGENTA,
    'cyan': FORE_CYAN,
    'normal': FORE_NORMAL,

    'cli-flag': FORE_GREEN,
    'cli-default': FORE_MAGENTA,
    'cli-section': FORE_BLUE,
}


_MSG_LOGGER: logging.Logger
_MSG_HANDLER: 'Handler'

_QUESTION_LOGGER: logging.Logger

_HANDLER_IMPL: '_HandlerImpl'


def setup(
    level: _t.Optional[int] = None,
    stream: _t.IO = sys.stderr,
    *,
    use_colors: _t.Optional[bool] = None,
    formatter: _t.Optional[logging.Formatter] = DEFAULT_FORMATTER,
    colors: _t.Optional[_t.Dict[str, Color]] = None,
):
    """Initial setup of the logging facilities.

    This function should be called

    :param level:
        log output level. If not given, will check ``DEBUG`` and ``QUIET``
        environment variables to determine an appropriate logging level.
    :param stream:
        a stream where to output messages. Uses `stderr` by default.
    :param formatter:
        formatter for log messages.
    :param use_colors:
        use ANSI escape sequences to color the output. If not given, will
        check ``NO_COLORS`` and ``FORCE_COLORS`` environment variables,
        and also if the given `stderr` is a tty stream.
    :param colors:
        mapping from tag name or logging level name to a :class:`Color`.
        Logging level names and tag names are all lowercase.

    """

    if level is None:
        if 'DEBUG' in os.environ:
            level = DEBUG
        elif 'QUIET' in os.environ:
            level = WARNING
        else:
            level = INFO

    if use_colors is None:
        if 'NO_COLORS' in os.environ:
            use_colors = False
        elif 'FORCE_COLORS' in os.environ:
            use_colors = True
        else:
            use_colors = stream.isatty()

    if colors is None:
        colors = DEFAULT_COLORS
    else:
        colors = dict(DEFAULT_COLORS, **colors)

    _MSG_HANDLER.setLevel(level)
    _MSG_HANDLER.setFormatter(formatter)
    _HANDLER_IMPL.setup(stream, use_colors, colors)


def log(level: int, msg: str, /, *args, **kwargs):
    """Log a debug message.

    """

    kwargs.setdefault('extra', {}).setdefault('yuio_process_color_tags', True)
    _MSG_LOGGER.log(level, msg, *args, **kwargs)


def debug(msg: str, /, *args, **kwargs):
    """Log a debug message.

    """

    log(DEBUG, msg, *args, **kwargs)


def info(msg: str, /, *args, **kwargs):
    """Log an info message.

    """

    log(INFO, msg, *args, **kwargs)


def warning(msg: str, /, *args, **kwargs):
    """Log a warning message.

    """

    log(WARNING, msg, *args, **kwargs)


def error(msg: str, /, *args, **kwargs):
    """Log an error message.

    """

    log(ERROR, msg, *args, **kwargs)


def exception(msg: str, /, *args, exc_info=True, **kwargs):
    """Log an error message and capture the current exception.

    Call this function in the `except` clause of a `try` block
    or in an `__exit__` function of a context manager to attach
    current exception details to the log message.

    """

    log(ERROR, msg, *args, exc_info=exc_info, **kwargs)


def critical(msg: str, /, *args, **kwargs):
    """Log a critical error message.

    """

    log(CRITICAL, msg, *args, **kwargs)


def question(msg: str, /, *args, **kwargs):
    """Log a message with input prompts and other user communications.

    These messages don't end with newline. They also have high priority,
    so they will not be filtered by log level settings.

    """

    extra = kwargs.setdefault('extra', {})
    extra.setdefault('yuio_add_newline', False)
    extra.setdefault('yuio_process_color_tags', True)
    _QUESTION_LOGGER.log(QUESTION, msg, *args, **kwargs)


def is_interactive() -> bool:
    """Check if we're running in an interactive environment.

    """

    return _HANDLER_IMPL._stream.isatty() \
           and os.environ.get('TERM', None) != 'dumb' \
           and 'NON_INTERACTIVE' not in os.environ \
           and 'CI' not in os.environ


@_t.overload
def ask(
    msg: str,
    /,
    *args,
    default: _t.Optional[str] = None,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    hidden: bool = False,
) -> str: ...


@_t.overload
def ask(
    msg: str,
    /,
    *args,
    parser: yuio.parse.Parser[T],
    default: _t.Union[T, Disabled] = DISABLED,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    hidden: bool = False,
) -> T: ...


@_t.overload
def ask(
    msg: str,
    /,
    *args,
    parser: yuio.parse.Parser[T],
    default: None,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    hidden: bool = False,
) -> _t.Optional[T]: ...


def ask(
    msg: str,
    /,
    *args,
    parser: _t.Optional[yuio.parse.Parser[T]] = None,
    default: _t.Any = DISABLED,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    hidden: bool = False,
) -> _t.Any:
    """Ask user to provide an input, parse it and return a value.

    If launched in a non-interactive environment, returns the default
    if one is present, or raises a :class:`UserIoError`.

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

    if not is_interactive():
        if default is not DISABLED:
            return default
        else:
            raise UserIoError(
                'can\'t interact with user in non-interactive environment'
            )

    if parser is None:
        parser = _t.cast(yuio.parse.Parser[T], str)

    desc = ''

    if input_description is None and hasattr(parser, 'describe'):
        input_description = getattr(parser, 'describe')()
    if input_description:
        desc += f' ({input_description})'

    if default is not DISABLED:
        if default_description is None and hasattr(parser, 'describe_value'):
            default_description = getattr(parser, 'describe_value')(default)
        if default_description is None:
            default_description = str(default)
        if default_description:
            desc += f' [<c:note>{default_description}</c>]'

    if args:
        msg = msg % args

    msg += desc

    if desc or not msg.endswith(tuple(string.punctuation)):
        msg += ': '
    else:
        msg += ' '

    with SuspendLogging() as s:
        while True:
            s.question(msg)
            try:
                if hidden:
                    answer = getpass.getpass(prompt='')
                else:
                    answer = input()
            except EOFError:
                raise UserIoError('unexpected end of input') from None
            if not answer and default is not DISABLED:
                return default
            elif not answer:
                s.error('Input is required.')
            else:
                try:
                    return parser(answer)
                except Exception as e:
                    if hidden:
                        s.error('Error: invalid value.')
                    else:
                        s.error(f'Error: {e}.')


def detect_editor() -> _t.Optional[str]:
    """Detect an editor executable.

    This function checks the ``EDITOR`` environment variable.
    If it's not found, it checks whether ``nano`` or ``vi``
    are available. Otherwise, it returns `None`.

    """

    if sys.platform == 'win':
        return 'notepad'

    if os.environ.get('EDITOR'):
        return os.environ['EDITOR']

    def check_editor(name):
        return subprocess.run(
            ['which', name], stdout=subprocess.DEVNULL
        ).returncode == 0

    # if check_editor('code'):
    #     return 'code -nw'
    # if check_editor('subl'):
    #     return 'subl -nw'
    if check_editor('nano'):
        return 'nano'
    if check_editor('vi'):
        return 'vi'

    return None


def edit(
    text: str,
    /,
    *,
    comment_marker: _t.Optional[str] = '#',
    editor: _t.Optional[str] = None,
) -> str:
    """Ask user to edit some text.

    This function creates a temporary file with the given text
    and opens it in an editor. After editing is done, it strips away
    all lines that start with `comment_marker`, if one is given.

    If editor is not available or returns a non-zero exit code,
    a :class:`UserIoError` is raised.

    If launched in a non-interactive environment, returns the text
    unedited (comments are still removed, though).

    """

    if is_interactive():
        if editor is None:
            editor = detect_editor()

        if editor is None:
            raise UserIoError(
                'can\'t detect an editor, ensure that the $EDITOR '
                'environment variable contains '
                'a correct path to an editor executable'
            )

        filepath = tempfile.mktemp()
        with open(filepath, 'w') as file:
            file.write(text)

        try:
            try:
                with SuspendLogging():
                    res = subprocess.run(f'{editor} "{filepath}"', shell=True)
            except FileNotFoundError:
                raise UserIoError(
                    'can\'t use this editor, ensure that the $EDITOR '
                    'environment variable contains '
                    'a correct path to an editor executable'
                )

            if res.returncode != 0:
                raise UserIoError(
                    'editing failed'
                )

            with open(filepath, 'r') as file:
                text = file.read()
        finally:
            os.remove(filepath)

    if comment_marker is not None:
        text = re.sub(
            r'^\s*' + re.escape(comment_marker) + r'.*?\n',
            '',
            text,
            flags=re.MULTILINE
        )

    return text.strip()


class SuspendLogging:
    """A context manager for pausing log output.

    This is handy for when you need to take control over the output stream.
    For example, the :func:`ask` function uses this class internally.

    """

    def __init__(self):
        self._resumed = False
        _HANDLER_IMPL.suspend()

    def resume(self):
        """Manually resume the logging process.

        """

        if not self._resumed:
            _HANDLER_IMPL.resume()
            self._resumed = True

    @staticmethod
    def log(level: int, msg: str, /, *args, **kwargs):
        """Log a message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        log(level, msg, *args, **kwargs)

    @staticmethod
    def debug(msg: str, /, *args, **kwargs):
        """Log a :func:`debug` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        debug(msg, *args, **kwargs)

    @staticmethod
    def info(msg: str, /, *args, **kwargs):
        """Log a :func:`info` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg: str, /, *args, **kwargs):
        """Log a :func:`warning` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        warning(msg, *args, **kwargs)

    @staticmethod
    def error(msg: str, /, *args, **kwargs):
        """Log a :func:`error` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        error(msg, *args, **kwargs)

    @staticmethod
    def exception(msg: str, /, *args, exc_info=True, **kwargs):
        """Log a :func:`exception` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        error(msg, *args, exc_info, **kwargs)

    @staticmethod
    def critical(msg: str, /, *args, **kwargs):
        """Log a :func:`critical` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        critical(msg, *args, **kwargs)

    @staticmethod
    def question(msg: str, /, *args, **kwargs):
        """Log a :func:`question` message, ignore suspended status.

        """

        kwargs.setdefault('extra', {}).setdefault('yuio_ignore_suspended', True)
        question(msg, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.resume()


class _IterTask(_t.Generic[T]):
    def __init__(self, collection: _t.Collection[T], task: 'Task'):
        self._iter = iter(collection)
        self._task = task

        self._i = 0
        self._len = len(collection)

    def __next__(self) -> T:
        self._task.progress((self._i, self._len))
        if self._i < self._len:
            self._i += 1
        return self._iter.__next__()

    def __iter__(self) -> '_IterTask[T]':
        return self

    def __enter__(self):
        self._task.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._task.__exit__(exc_type, exc_val, exc_tb)


class _IterTaskLong(_t.Generic[T]):
    def __init__(self, collection: _t.Collection[T], task: 'Task'):
        self._iter = iter(collection)
        self._task = task

        self._i = 0
        self._len = len(collection)
        self._p = -1

    def __next__(self) -> T:
        p = self._i * 100 // self._len
        if p > self._p:
            self._task.progress(p / 100)
            self._p = p
        if self._i < self._len:
            self._i += 1
        return self._iter.__next__()

    def __iter__(self) -> '_IterTaskLong[T]':
        return self

    def __enter__(self):
        self._task.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self._task.__exit__(exc_type, exc_val, exc_tb)


class Task:
    """A class for indicating progress of some task.

    You can have multiple tasks at the same time,
    create subtasks, set task's progress or add a comment about
    what's currently being done within a task.

    This class can be used as a context manager::

        with task('Fetching data') as t:
            data = requests.get(url)

    This will output the following:

    .. code-block:: text

       Fetching data [---->          ] (3 / 10) - https://google.com

    """

    class _Status(enum.Enum):
        RUNNING = enum.auto()
        DONE = enum.auto()
        ERROR = enum.auto()

    def __init__(self, msg: str, /, *args, parent: _t.Optional['Task'] = None):
        # These should not be written to directly.
        # Instead, task should be sent to a handler for modification.
        # This ensures thread safety, because handler has a lock.
        # See handler's implementation details.
        if args:
            msg = msg % args

        self._msg: str = msg
        self._progress: _PROGRESS = None
        self._comment: _t.Optional[str] = None
        self._status: Task._Status = Task._Status.RUNNING
        self._subtasks: _t.List[Task] = []

        if parent is None:
            _HANDLER_IMPL.reg_task(self)
        else:
            _HANDLER_IMPL.reg_subtask(parent, self)

    def progress(self, progress: _PROGRESS, /):
        """Indicate progress of ths task.

        :param progress:
            Progress of the task. Could be one of three things:

            - a floating point number between ``0`` and ``1``;
            - a tuple of two ints, first is the number of completed jobs,
              and second is the total number of jobs;
            - a tuple of three ints, first is the number of completed jobs,
              second is the number of in-progress jobs, and the third
              is the total number of jobs.

        """

        _HANDLER_IMPL.set_progress(self, progress)

    def iter(self, collection: _t.Collection[T]) -> _t.Iterable[T]:
        """Helper for updating progress automatically
        while iterating over a collection.

        For example::

            with Task('Fetching data') as t:
                for url in t.iter(urls):
                    url.fetch()

        This will output the following:

        .. code-block:: text

           Fetching data [---->          ] (3 / 10)

        """

        if len(collection) <= 100:
            return _IterTask(collection, self)
        else:
            # updating progress bar 100 times is slow...
            return _IterTaskLong(collection, self)

    def comment(self, comment: _t.Optional[str], /):
        """Set a comment for a task.

        Comment is displayed after the progress.

        """

        _HANDLER_IMPL.set_comment(self, comment)

    def done(self):
        """Indicate that this task has finished successfully.

        """

        _HANDLER_IMPL.set_status(self, Task._Status.DONE)

    def error(self):
        """Indicate that this task has finished with an error.

        """

        _HANDLER_IMPL.set_status(self, Task._Status.ERROR)

    def subtask(self, msg: str, /, *args) -> 'Task':
        """Create a subtask within this task.

        """

        return Task(msg, *args, parent=self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is None:
            self.done()
        else:
            self.error()


class Handler(logging.Handler):
    """A handler that redirects all log messages to yuio.

    Note that formatters set up via the :func:`setup` function
    do not affect this handler.

    """

    def createLock(self) -> None:
        self.lock = None

    def emit(self, record: LogRecord) -> None:
        _HANDLER_IMPL.emit(self.format(record), record)


class _HandlerImpl:
    """A worker that reads messages from a queue and prints them to a stream.

    This worker lives in a separate daemon thread, so keyboard interrupts
    do not affect it.

    """

    def __init__(self):
        self._stream = sys.stderr
        self._colors: _t.Dict[str, Color] = DEFAULT_COLORS
        self._use_colors: bool = self._stream.isatty()

        self._tasks: _t.List[Task] = []

        self._tasks_shown: int = 0

        self._suspended: int = 0
        self._suspended_lines: _t.List[str] = []

        self.lock = threading.Lock()

    def setup(
        self,
        stream: _t.IO,
        use_colors: bool,
        colors: _t.Dict[str, Color],
    ):
        with self.lock:
            self._stream = stream
            self._use_colors = use_colors
            self._colors = colors

    def flush(self) -> None:
        self._stream.flush()

    def emit(self, msg, record: logging.LogRecord):
        with self.lock:
            line = self._format_record(msg, record)
            if self._suspended:
                if getattr(record, 'yuio_ignore_suspended', False):
                    self._stream.write(line)
                else:
                    self._suspended_lines.append(line)
            elif self._use_colors:
                self._undraw()
                self._stream.write(line)
                self._draw()
            else:
                self._stream.write(line)
            self._stream.flush()

    def reg_task(self, task: Task):
        with self.lock:
            self._tasks.append(task)
            self._display_task_status_change(task)

    def reg_subtask(self, parent: Task, task: Task):
        with self.lock:
            parent._subtasks.append(task)
            self._display_task_status_change(task)

    def set_progress(self, task: Task, progress: _PROGRESS):
        with self.lock:
            task._progress = progress

            if self._use_colors:
                self._redraw()

    def set_comment(self, task: Task, comment: _t.Optional[str]):
        with self.lock:
            task._comment = comment

            if self._use_colors and not self._suspended:
                self._redraw()

    def set_status(self, task: Task, status: Task._Status):
        with self.lock:
            task._status = status
            self._display_task_status_change(task)

    def suspend(self):
        with self.lock:
            self._suspended += 1

            if self._suspended == 1:
                self._undraw()
                self._stream.flush()

    def resume(self):
        with self.lock:
            self._suspended -= 1

            if self._suspended == 0:
                for line in self._suspended_lines:
                    self._stream.write(line)

                self._suspended_lines.clear()

                if self._use_colors:
                    self._cleanup_tasks()
                    self._draw()

            if self._suspended < 0:
                raise RuntimeError('unequal number of suspends and resumes')

    def _display_task_status_change(self, task: Task):
        if self._use_colors:
            if not self._suspended:
                self._redraw()
        elif self._suspended:
            self._suspended_lines.append(self._format_task(task))
        else:
            self._stream.write(self._format_task(task))
            if task._status != Task._Status.RUNNING and task in self._tasks:
                self._tasks.remove(task)

    # Private functions, called from internal API

    def _redraw(self):
        # Update currently printed tasks to their current status.
        # Must not be called while output is suspended or when not using colors.

        self._undraw()
        self._cleanup_tasks()
        self._draw()

    def _undraw(self):
        # Clear drawn tasks from the screen.
        # Must not be called while output is suspended or when not using colors.

        if self._tasks_shown > 0:
            self._stream.write(f'\033[{self._tasks_shown}F\033[J')
            self._tasks_shown = 0

    def _cleanup_tasks(self):
        # Clean up finished tasks.
        # Must not be called while output is suspended or when not using colors.
        # Must be called after `_undraw`.

        new_tasks = []
        for task in self._tasks:
            if task._status == Task._Status.RUNNING:
                new_tasks.append(task)
            else:
                self._stream.write(self._format_task(task))
        self._tasks = new_tasks

    def _draw(self):
        # Draw current tasks.
        # Must not be called while output is suspended.
        # Must be called after `_undraw` or `_cleanup_tasks`.

        tasks: _t.List[_t.Tuple[Task, int]] = [
            (task, 0) for task in reversed(self._tasks)
        ]

        while tasks:
            task, indent = tasks.pop()

            self._stream.write(self._format_task(task, indent))
            self._tasks_shown += 1

            indent += 1
            tasks.extend(
                [(subtask, indent) for subtask in reversed(task._subtasks)]
            )

        self._stream.flush()

    def _format_task(self, task: Task, indent: int = 0) -> str:
        # Format a task with respect to `_use_colors`.

        if task._status == Task._Status.DONE:
            color = self._colors['task_done']
            status = ': OK'
        elif task._status == Task._Status.ERROR:
            color = self._colors['task_error']
            status = ': ERROR'
        else:
            color = self._colors['task']
            if (
                self._use_colors
                and task._progress is None
                and task._comment is not None
            ):
                status = ' - ' + task._comment + '...'
            elif task._progress is None or not self._use_colors:
                status = '...'
            else:
                status = ' ' + self._make_progress_bar(task._progress)
                if task._comment is not None:
                    status += ' - ' + task._comment

        return self._colorize('  ' * indent + task._msg + status, color) + '\n'

    def _format_record(self, msg: str, record: logging.LogRecord) -> str:
        # Format a record with respect to `_use_colors`.

        color = self._colors.get(record.levelname.lower(), Color())
        process_color_tags = getattr(record, 'yuio_process_color_tags', False)
        if getattr(record, 'yuio_add_newline', True):
            msg += '\n'
        return self._colorize(msg, color, process_color_tags)

    _TAG_RE = re.compile(r'<c:(?P<name>[a-z0-9, _-]+)>|</c>')

    def _colorize(self, msg: str, default_color: Color, process_color_tags: bool = True):
        # Colorize a message, process color tags if necessary.
        # Respect `_use_colors`.

        default_color = FORE_NORMAL | BACK_NORMAL | default_color

        if not process_color_tags:
            if self._use_colors:
                return str(default_color) + msg + str(Color())
            else:
                return msg
        elif not self._use_colors:
            return self._TAG_RE.sub('', msg)

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

        out += str(Color())

        return out

    def _make_progress_bar(self, progress: _PROGRESS) -> str:
        width = 15

        progress_indicator = ''

        done_percentage = 0.0
        inflight_percentage = 0.0
        adjust_inflight = True

        if isinstance(progress, tuple):
            if len(progress) == 2:
                progress = _t.cast(_t.Tuple[int, int], progress)
                done_percentage = float(progress[0]) / float(progress[1])
                progress_indicator = f'{progress[0]} / {progress[1]}'
            elif len(progress) == 3:
                progress = _t.cast(_t.Tuple[int, int, int], progress)
                done_percentage = float(progress[0]) / float(progress[2])
                inflight_percentage = float(progress[1]) / float(progress[2])
                progress_indicator = f'{progress[0]} / {progress[1]} / {progress[2]}'
                adjust_inflight = False
        elif isinstance(progress, (float, int)):
            done_percentage = float(progress)

        if done_percentage < 0:
            done_percentage = 0.0
        elif done_percentage > 1:
            done_percentage = 1.0

        if inflight_percentage < 0:
            inflight_percentage = 0.0
        elif inflight_percentage > 1:
            inflight_percentage = 1.0

        if done_percentage + inflight_percentage > 1:
            inflight_percentage = 1.0 - done_percentage

        done = int(width * done_percentage)
        inflight = int(width * inflight_percentage)

        if adjust_inflight and inflight == 0 and 0 < done < width:
            inflight = 1
            done -= 1

        left = width - done - inflight

        if not progress_indicator:
            progress_indicator = f'{done_percentage:0.0%}'

        return '[' \
               + '-' * done \
               + '>' * inflight \
               + ' ' * left \
               + ']' \
               + f' {progress_indicator}'


logging.addLevelName(QUESTION, 'question')

_HANDLER_IMPL = _HandlerImpl()

_MSG_HANDLER = Handler()

_MSG_LOGGER = logging.getLogger('yuio.msg')
_MSG_LOGGER.propagate = False
_MSG_LOGGER.setLevel(1)  # ignore logging level of the root logger
_MSG_LOGGER.addHandler(_MSG_HANDLER)

_QUESTION_LOGGER = logging.getLogger('yuio.msg.question')

setup()
