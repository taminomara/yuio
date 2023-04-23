# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module implements user-friendly input and output on top of the python's
standard logging library.

Configuration
-------------

Yuio configures itself upon import using environment variables:

- ``DEBUG``: print debug-level messages,
- ``NO_COLORS``: disable colored output,
- ``FORCE_COLORS``: enable colored output.

You can override this process by calling the :func:`setup` function.

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

.. autofunction:: log

.. autoclass:: LogLevel
   :members:


Coloring the output
-------------------

By default, all log messages are colored according to their level.

If you need inline colors, you can use special tags in your log messages::

    info('Using the <c:code>code</c> tag.')

You can combine multiple colors in the same tag::

    info('<c:bold,green>Success!</c>')

Only tags that appear in the log message itself are processed::

    info('Tags in this message --> %s are printed as-is', '<c:color>')

List of all tags that are available by default:

- ``code``: for inline code,
- ``note``: for notes, such as default values in user prompts,
- ``success``, ``failure``: for indicating outcome of the program,
- ``heading``: for splitting output into sections,
- ``question``, ``critical``, ``error``, ``warning``, ``info``, ``debug``:
  used to color log messages,
- ``task``, ``task_done``, ``task_error``:
  used to color tasks,
- ``bold``, ``b``, ``dim``: font styles,
- ``red``, ``green``, ``yellow``, ``blue``, ``magenta``, ``cyan``:
  font colors.

Custom colors
-------------

Use :func:`setup` function to override existing tag colors or add new tags::

    setup(
        colors=dict(
            success=Color.FORE_BLUE | Color.STYLE_BOLD
        )
    )

This argument is a mapping from a tag name to a :class:`Color` instance:

.. autoclass:: Color
   :members:


Indicating progress
-------------------

You can use the :class:`Task` class to indicate status and progress
of some task:

.. autoclass:: Task
   :members:


Querying user input
-------------------

There are functions to query some input from a user:

.. autofunction:: ask

.. autofunction:: ask_yn

.. autofunction:: wait_for_user

You can prompt user to edit something with the :func:`edit` function:

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

   io[shape=plain label=<
     <TABLE BORDER="1" CELLBORDER="0" CELLSPACING="1">
       <TR>
         <TD>io</TD>
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
   yuio -> io [style=dashed label="propagate=False"]
   io -> {default, exec, question};
   root -> "...";

``yuio.io`` collects everything that should be printed on the screen
and passes it to a handler. It has its propagation disabled,
so yuio's messages never reach the root logger. This means that you can set up
other loggers and handlers without yuio interfering.

If you want to direct yuio messages somewhere else (i.e to a file),
either add a handler to ``yuio.io`` or enable propagation for it.

Since messages and questions from :mod:`yuio.exec` are logged to
``yuio.io.question`` and ``yuio.io.exec``,
you can filter them out from your handlers or the root logger.

If you want to direct messages from some other logger into yuio,
you can add a :class:`Handler`:

.. autoclass:: Handler

"""

import atexit
import enum
import functools
import getpass
import logging
import os
import queue
import re
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import typing as _t
from dataclasses import dataclass
from logging import LogRecord

import yuio.parse
from yuio.config import DISABLED, Disabled


T = _t.TypeVar('T')
_PROGRESS = _t.Union[None, int, float, _t.Tuple[int, int], _t.Tuple[int, int, int]]


class UserIoError(IOError):
    """Raised when interaction with user fails.

    """


class LogLevel(int):
    """Logging levels for the :func:`log` function.

    """

    #: Used for displaying questions to users.
    QUESTION: 'LogLevel' = lambda: LogLevel(100)  # type: ignore

    #: Used for critical errors that cause a program to crash.
    CRITICAL: 'LogLevel' = lambda: LogLevel(logging.CRITICAL)  # type: ignore

    #: Used for unhandled errors.
    ERROR: 'LogLevel' = lambda: LogLevel(logging.ERROR)  # type: ignore

    #: Used for conditions that may cause concern.
    WARNING: 'LogLevel' = lambda: LogLevel(logging.WARNING)  # type: ignore

    #: Used for info messages and normal user interactions.
    INFO: 'LogLevel' = lambda: LogLevel(logging.INFO)  # type: ignore

    #: Used for logging debug info.
    DEBUG: 'LogLevel' = lambda: LogLevel(logging.DEBUG)  # type: ignore

    #: The smallest possible log level.
    NOTSET: 'LogLevel' = lambda: LogLevel(logging.NOTSET)  # type: ignore

for _n, _v in vars(LogLevel).items():
    if _n == _n.upper():
        setattr(LogLevel, _n, _v())
del _n, _v  # type: ignore


@dataclass(frozen=True)
class Color:
    """ANSI color code.

    You can combine multiple colors::

        BOLD_RED = Color.FORE_RED | Color.STYLE_BOLD

    """

    # Note: other font styles besides bold and dim are not implemented
    # because their support in terminals is limited.

    fore: _t.Optional[str] = None
    back: _t.Optional[str] = None
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
        if (s := getattr(self, '_cached', None)) is None:
            codes = ['0']
            if self.fore is not None:
                codes.append(self.fore)
            if self.back is not None:
                codes.append(self.back)
            if self.bold:
                codes.append('1')
            if self.dim:
                codes.append('2')
            s = '\033[' + ';'.join(codes) + 'm'
            object.__setattr__(self, '_cached', s)
        return s

    def __add__(self, rhs: _t.Any):
        if isinstance(rhs, str):
            return str(self) + rhs
        return NotImplemented

    def __radd__(self, lhs: _t.Any):
        if isinstance(lhs, str):
            return lhs + str(self)
        return NotImplemented

    NONE: _t.ClassVar['Color'] = lambda: Color()  # type: ignore

    #: Bold font style.
    STYLE_BOLD: _t.ClassVar['Color'] = lambda: Color(bold=True)  # type: ignore
    #: Dim font style.
    STYLE_DIM: _t.ClassVar['Color'] = lambda: Color(dim=True)  # type: ignore

    #: Normal foreground color.
    FORE_NORMAL: _t.ClassVar['Color'] = lambda: Color(fore='39')  # type: ignore
    #: Black foreground color.
    FORE_BLACK: _t.ClassVar['Color'] = lambda: Color(fore='30')  # type: ignore
    #: Red foreground color.
    FORE_RED: _t.ClassVar['Color'] = lambda: Color(fore='31')  # type: ignore
    #: Green foreground color.
    FORE_GREEN: _t.ClassVar['Color'] = lambda: Color(fore='32')  # type: ignore
    #: Yellow foreground color.
    FORE_YELLOW: _t.ClassVar['Color'] = lambda: Color(fore='33')  # type: ignore
    #: Blue foreground color.
    FORE_BLUE: _t.ClassVar['Color'] = lambda: Color(fore='34')  # type: ignore
    #: Magenta foreground color.
    FORE_MAGENTA: _t.ClassVar['Color'] = lambda: Color(fore='35')  # type: ignore
    #: Cyan foreground color.
    FORE_CYAN: _t.ClassVar['Color'] = lambda: Color(fore='36')  # type: ignore
    #: White foreground color.
    FORE_WHITE: _t.ClassVar['Color'] = lambda: Color(fore='37')  # type: ignore

    #: Normal background color.
    BACK_NORMAL: _t.ClassVar['Color'] = lambda: Color(back='49')  # type: ignore
    #: Black background color.
    BACK_BLACK: _t.ClassVar['Color'] = lambda: Color(back='40')  # type: ignore
    #: Red background color.
    BACK_RED: _t.ClassVar['Color'] = lambda: Color(back='41')  # type: ignore
    #: Green background color.
    BACK_GREEN: _t.ClassVar['Color'] = lambda: Color(back='42')  # type: ignore
    #: Yellow background color.
    BACK_YELLOW: _t.ClassVar['Color'] = lambda: Color(back='43')  # type: ignore
    #: Blue background color.
    BACK_BLUE: _t.ClassVar['Color'] = lambda: Color(back='44')  # type: ignore
    #: Magenta background color.
    BACK_MAGENTA: _t.ClassVar['Color'] = lambda: Color(back='45')  # type: ignore
    #: Cyan background color.
    BACK_CYAN: _t.ClassVar['Color'] = lambda: Color(back='46')  # type: ignore
    #: White background color.
    BACK_WHITE: _t.ClassVar['Color'] = lambda: Color(back='47')  # type: ignore

for _n, _v in vars(Color).items():
    if _n == _n.upper():
        setattr(Color, _n, _v())
del _n, _v  # type: ignore

DEFAULT_COLORS = {
    'code': Color.FORE_MAGENTA,
    'note': Color.FORE_GREEN,
    'success': Color.FORE_GREEN | Color.STYLE_BOLD,
    'failure': Color.FORE_RED | Color.STYLE_BOLD,
    'heading': Color.FORE_BLUE,

    'question': Color.FORE_BLUE,
    'critical': Color.FORE_WHITE | Color.BACK_RED,
    'error': Color.FORE_RED,
    'warning': Color.FORE_YELLOW,
    'info': Color.NONE,
    'debug': Color.STYLE_DIM,

    'rich_log_default_level_color': Color.FORE_CYAN,
    'rich_log_asctime': Color.STYLE_DIM,
    'rich_log_logger': Color.STYLE_DIM,

    'task': Color.FORE_BLUE,
    'task_done': Color.FORE_GREEN,
    'task_error': Color.FORE_RED,

    'bold': Color.STYLE_BOLD,
    'b': Color.STYLE_BOLD,
    'dim': Color.STYLE_DIM,
    'd': Color.STYLE_DIM,

    'red': Color.FORE_RED,
    'green': Color.FORE_GREEN,
    'yellow': Color.FORE_YELLOW,
    'blue': Color.FORE_BLUE,
    'magenta': Color.FORE_MAGENTA,
    'cyan': Color.FORE_CYAN,

    'cli_flag': Color.FORE_GREEN,
    'cli_default': Color.FORE_NORMAL,
    'cli_section': Color.FORE_BLUE,
}

# Data flow:
#
#  _MSG_LOGGER ──────→╮
#                     ├─→ _MSG_HANDLER ──→ _MSG_HANDLER_IMPL ──→ sys.stderr
#  _QUESTION_LOGGER ─→╯
#
#  (passing LogRecord to impl)             (formatting)          (output)

_MSG_HANDLER_IMPL: '_HandlerImpl'

_MSG_HANDLER: 'Handler'

_MSG_LOGGER: logging.Logger
_QUESTION_LOGGER: logging.Logger


def setup(
    level: _t.Optional[LogLevel] = None,
    stream: _t.Optional[_t.TextIO] = None,
    *,
    use_colors: _t.Optional[bool] = None,
    colors: _t.Optional[_t.Dict[str, Color]] = None,
):
    """Initial setup of the logging facilities.

    :param level:
        log output level.
    :param stream:
        a stream where to output messages. Uses :data:`~sys.stderr` by default.
        Setting a stream disables colored output, unless `use_colors` is given.
    :param use_colors:
        use ANSI escape sequences to color the output.
    :param colors:
        mapping from tag name or logging level name to a :class:`Color`.
        Logging level names and tag names are all lowercase.

    """

    if level is not None:
        _MSG_HANDLER.setLevel(level)
    if stream is not None:
        _MSG_HANDLER_IMPL.stream = stream
        _MSG_HANDLER_IMPL.use_colors = False
    if use_colors is not None:
        _MSG_HANDLER_IMPL.use_colors = use_colors
    if colors is not None:
        for color in colors:
            if not re.match(r'^[a-z0-9_]+$', color):
                raise RuntimeError(
                    f'invalid tag {color!r}: tag names should consist of '
                    'lowercase letters, digits, and underscore symbols')
        _MSG_HANDLER_IMPL.colors = dict(DEFAULT_COLORS, **colors)


def log(level: LogLevel, msg: str, /, *args, **kwargs):
    """Log a message.

    """

    _MSG_LOGGER.log(level, msg, *args, **kwargs)


def debug(msg: str, /, *args, **kwargs):
    """Log a debug message.

    """

    log(LogLevel.DEBUG, msg, *args, **kwargs)


def info(msg: str, /, *args, **kwargs):
    """Log an info message.

    """

    log(LogLevel.INFO, msg, *args, **kwargs)


def warning(msg: str, /, *args, **kwargs):
    """Log a warning message.

    """

    log(LogLevel.WARNING, msg, *args, **kwargs)


def error(msg: str, /, *args, **kwargs):
    """Log an error message.

    """

    log(LogLevel.ERROR, msg, *args, **kwargs)


def exception(msg: str, /, *args, exc_info=True, **kwargs):
    """Log an error message and capture the current exception.

    Call this function in the `except` clause of a `try` block
    or in an `__exit__` function of a context manager to attach
    current exception details to the log message.

    """

    log(LogLevel.ERROR, msg, *args, exc_info=exc_info, **kwargs)


def critical(msg: str, /, *args, **kwargs):
    """Log a critical error message.

    """

    log(LogLevel.CRITICAL, msg, *args, **kwargs)


def question(msg: str, /, *args, **kwargs):
    """Log a message with input prompts and other user communications.

    These messages don't end with newline. They also have high priority,
    so they will not be filtered by log level settings.

    """

    extra = kwargs.setdefault('extra', {})
    extra.setdefault('yuio_add_newline', False)
    _QUESTION_LOGGER.log(LogLevel.QUESTION, msg, *args, **kwargs)


def is_interactive() -> bool:
    """Check if we're running in an interactive environment.

    """

    return _MSG_HANDLER_IMPL.stream.isatty() \
        and os.environ.get('TERM', None) != 'dumb'


@_t.overload
def ask(
    msg: str,
    /,
    *args,
    default: _t.Optional[str] = None,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    secure_input: bool = False,
) -> str: ...


@_t.overload
def ask(
    msg: str,
    /,
    *args,
    parser: _t.Union[yuio.parse.Parser[T], _t.Type[T]],
    default: _t.Union[T, Disabled] = DISABLED,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    secure_input: bool = False,
) -> T: ...


@_t.overload
def ask(
    msg: str,
    /,
    *args,
    parser: _t.Union[yuio.parse.Parser[T], _t.Type[T]],
    default: None,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    secure_input: bool = False,
) -> _t.Optional[T]: ...


def ask(
    msg: str,
    /,
    *args,
    parser: _t.Union[yuio.parse.Parser, _t.Type] = yuio.parse.Str(),
    default: _t.Any = DISABLED,
    input_description: _t.Optional[str] = None,
    default_description: _t.Optional[str] = None,
    secure_input: bool = False,
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
        prompt to display to user.
    :param args:
        arguments for prompt formatting.
    :param parser:
        parser to use to parse user input. See :mod:`yuio.parse` for more
        info. Can also accept a type hint and turn it into a parser.
    :param default:
        default value to return if user input is empty.
    :param input_description:
        description of the expected input, like ``'yes/no'`` for boolean
        inputs.
    :param default_description:
        description of the `default` value.
    :param secure_input:
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

    if not isinstance(parser, yuio.parse.Parser):
        parser = yuio.parse.from_type_hint(parser)
    if default is None and not isinstance(parser, yuio.parse.Optional):
        parser = yuio.parse.Optional(parser)

    desc = ''

    if input_description is None:
        input_description = parser.describe()
    if input_description:
        desc += f' ({input_description})'

    if default is not DISABLED:
        if default_description is None:
            default_description = parser.describe_value(default)
        if default_description is None:
            default_description = str(default)
        if default_description:
            desc += f' [<c:note>{default_description}</c>]'

    msg += desc.replace('%', '%%')

    if not msg.endswith((':', ': ')):
        msg += ':'
    if not msg.endswith(' '):
        msg += ' '

    with SuspendLogging() as s:
        while True:
            s.question(msg, *args)
            try:
                if secure_input:
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
                    return parser.parse(answer)
                except yuio.parse.ParsingError as e:
                    if secure_input:
                        s.error('Error: invalid value.')
                    else:
                        s.error(f'Error: {e}.')


@_t.overload
def ask_yn(
    msg: str,
    /,
    *args,
    default: _t.Union[bool, Disabled] = DISABLED,
) -> bool: ...


@_t.overload
def ask_yn(
    msg: str,
    /,
    *args,
    default: None,
) -> _t.Optional[bool]: ...


def ask_yn(
    msg: str,
    /,
    *args,
    default: _t.Union[bool, None, Disabled] = DISABLED,
) -> _t.Any:
    """Shortcut to :func:`ask` for asking yes/no questions.

    """

    return ask(msg, *args, parser=yuio.parse.Bool(), default=default)


def wait_for_user(
    msg: str = 'Press <c:note>enter</c> to continue',
    /,
    *args,
):
    """A simple function to wait for user to press enter.

    """

    if not is_interactive():
        return

    with SuspendLogging() as s:
        s.question(msg + '\n', *args)
        input()


def detect_editor() -> _t.Optional[str]:
    """Detect the user's preferred editor.

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
            r'^\s*' + re.escape(comment_marker) + r'.*?(\n|\Z)',
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
        _MSG_HANDLER_IMPL.suspend()

    def resume(self):
        """Manually resume the logging process.

        """

        if not self._resumed:
            _MSG_HANDLER_IMPL.resume()
            self._resumed = True

    @staticmethod
    def log(level: LogLevel, msg: str, /, *args, **kwargs):
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


class Task:
    """A class for indicating progress of some task.

    You can have multiple tasks at the same time,
    create subtasks, set task's progress or add a comment about
    what's currently being done within a task.

    This class can be used as a context manager::

        with Task('Processing input') as t:
            ...
            t.progress(0.3)
            ...

    This will output the following:

    .. code-block:: text

       Processing input [---->          ] 30%

    """

    class _Status(enum.Enum):
        RUNNING = enum.auto()
        DONE = enum.auto()
        ERROR = enum.auto()

    def __init__(self, msg: str, /, *args, parent: _t.Optional['Task'] = None):
        # Task properties should not be written to directly.
        # Instead, task should be sent to a handler for modification.
        # This ensures thread safety, because handler has a lock.
        # See handler's implementation details.
        self._msg: str = msg
        self._args: tuple = args
        self._progress: _PROGRESS = None
        self._comment: _t.Optional[str] = None
        self._comment_args: _t.Optional[tuple] = None
        self._status: Task._Status = Task._Status.RUNNING
        self._subtasks: _t.List[Task] = []

        self._cached_msg = None

        if parent is None:
            _MSG_HANDLER_IMPL.reg_task(self)
        else:
            _MSG_HANDLER_IMPL.reg_subtask(parent, self)

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

        _MSG_HANDLER_IMPL.set_progress(self, progress)

    def iter(self, collection: _t.Collection[T]) -> _t.Iterable[T]:
        """Helper for updating progress automatically
        while iterating over a collection.

        For example::

            with Task('Fetching data') as t:
                for url in t.iter(urls):
                    ...

        This will output the following:

        .. code-block:: text

           Fetching data [---->          ] (3 / 10)

        """

        if len(collection) <= 100:
            return _IterTask(collection, self)
        else:
            # updating progress bar 100 times is slow...
            return _IterTaskLong(collection, self)

    def comment(self, comment: _t.Optional[str], /, *args):
        """Set a comment for a task.

        Comment is displayed after the progress.

        For example::

            with Task('Fetching data') as t:
                for url in urls:
                    t.comment(url)
                    ...

        This will output the following:

        .. code-block:: text

           Fetching data - https://google.com

        """

        _MSG_HANDLER_IMPL.set_comment(self, comment, args)

    def done(self):
        """Indicate that this task has finished successfully.

        """

        _MSG_HANDLER_IMPL.set_status(self, Task._Status.DONE)

    def error(self):
        """Indicate that this task has finished with an error.

        """

        _MSG_HANDLER_IMPL.set_status(self, Task._Status.ERROR)

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

    """

    def __init__(
        self,
        level: LogLevel = LogLevel.NOTSET,
        /,
        *,
        process_color_tags: bool = False,
        rich_log_line: bool = True,
    ) -> None:
        super().__init__(level)

        self._process_color_tags = process_color_tags
        self._rich_log_line = rich_log_line

    def createLock(self) -> None:
        self.lock = None

    def emit(self, record: LogRecord) -> None:
        _MSG_HANDLER_IMPL.emit(record, self._process_color_tags, self._rich_log_line)
        _MSG_HANDLER_IMPL.suspend()


Cb = _t.TypeVar('Cb', bound=_t.Callable[..., None])


def _handler_impl_interface(wait_till_done: bool = False) -> _t.Callable[[Cb], Cb]:
    def decorator(func: Cb) -> Cb:
        if wait_till_done:
            @functools.wraps(func)
            def wrapped_decorator(self: '_HandlerImpl', *args, **kwargs):
                event = threading.Event()
                self._messages.put((func, self, args, kwargs, event))
                event.wait()
        else:
            @functools.wraps(func)
            def wrapped_decorator(self: '_HandlerImpl', *args, **kwargs):
                self._messages.put((func, self, args, kwargs, None))

        return _t.cast(Cb, wrapped_decorator)

    return decorator


class _HandlerImpl:
    """A worker that reads messages from a queue and prints them to a stream.

    This worker lives in a separate daemon thread, so keyboard interrupts
    do not affect it.

    """

    def __init__(self):
        self.stream: _t.TextIO = sys.stderr
        self.colors: _t.Dict[str, Color] = DEFAULT_COLORS

        self.use_colors: bool = self.stream.isatty()
        if 'NO_COLORS' in os.environ:
            self.use_colors = False
        elif 'FORCE_COLORS' in os.environ:
            self.use_colors = True

        self._tasks: _t.List[Task] = []

        self._tasks_shown: int = 0

        self._suspended: int = 0
        self._suspended_lines: _t.List[str] = []

        self._messages = queue.SimpleQueue()

        self._thread = threading.Thread(target=self._worker, name='yuio_io_thread').start()

    def _worker(self):
        atexit.register(lambda: self._messages.put(None))

        while True:
            try:
                try:
                    message = self._messages.get(timeout=0.25)
                except queue.Empty:
                    if self.use_colors:
                        self._redraw()
                    continue

                if message is None:
                    return

                f, _self, args, kwargs, event = message
                try:
                    f(_self, *args, **kwargs)
                finally:
                    if event is not None:
                        event.set()
            except Exception:
                msg = (
                    f'-----BEGIN YUIO CRITICAL MESSAGE-----\n'
                    f'CRITICAL: YUIO LOGGER ENCOUNTERED AN ERROR.\n'
                    f'PLEASE, SEND TRACEBACK AND ANY ADDITIONAL INTO TO YUIO DEVELOPERS.\n'
                    f'{traceback.format_exc()}\n'
                    f'-----END YUIO CRITICAL MESSAGE-----\n'
                )
                self.stream.write(msg)
                self.stream.flush()

    @_handler_impl_interface()
    def emit(
        self,
        record: logging.LogRecord,
        process_color_tags: bool,
        rich_log_line: bool,
    ):
        line = self._format_record(record, process_color_tags, rich_log_line)
        if self._suspended:
            if getattr(record, 'yuio_ignore_suspended', False):
                self.stream.write(line)
            else:
                self._suspended_lines.append(line)
        elif self.use_colors:
            self._undraw()
            self.stream.write(line)
            self._draw()
        else:
            self.stream.write(line)
        self.stream.flush()

    @_handler_impl_interface()
    def reg_task(self, task: Task):
        self._tasks.append(task)
        self._display_task_status_change(task)

    @_handler_impl_interface()
    def reg_subtask(self, parent: Task, task: Task):
        parent._subtasks.append(task)
        self._display_task_status_change(task)

    @_handler_impl_interface()
    def set_progress(self, task: Task, progress: _PROGRESS):
        task._progress = progress
        task._cached_msg = None

        if self.use_colors:
            self._redraw()

    @_handler_impl_interface()
    def set_comment(self, task: Task, comment: _t.Optional[str], args):
        task._comment = comment
        task._comment_args = args
        task._cached_msg = None

        if self.use_colors and not self._suspended:
            self._redraw()

    @_handler_impl_interface()
    def set_status(self, task: Task, status: Task._Status):
        task._status = status
        task._cached_msg = None

        self._display_task_status_change(task)

    @_handler_impl_interface(wait_till_done=True)
    def suspend(self):
        self._suspended += 1

        if self._suspended == 1:
            self._undraw()
            self.stream.flush()

    @_handler_impl_interface(wait_till_done=True)
    def resume(self):
        self._suspended -= 1

        if self._suspended == 0:
            for line in self._suspended_lines:
                self.stream.write(line)

            self._suspended_lines.clear()

            if self.use_colors:
                self._cleanup_tasks()
                self._draw()

        if self._suspended < 0:
            raise RuntimeError('unequal number of suspends and resumes')

    def _display_task_status_change(self, task: Task):
        if self.use_colors:
            if not self._suspended:
                self._redraw()
        elif self._suspended:
            self._suspended_lines.append(self._format_task(task))
        else:
            self.stream.write(self._format_task(task))
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
            self.stream.write(f'\033[{self._tasks_shown}F\033[J')
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
                self.stream.write(self._format_task(task))
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

            self.stream.write(self._format_task(task, indent))
            self._tasks_shown += 1

            indent += 1
            tasks.extend(
                [(subtask, indent) for subtask in reversed(task._subtasks)]
            )

        self.stream.flush()

    def _format_task(self, task: Task, indent: int = 0) -> str:
        # Format a task with respect to `_use_colors`.

        if task._status == Task._Status.DONE:
            color = self.colors['task_done']
            status = self._colorize(': OK', color)
        elif task._status == Task._Status.ERROR:
            color = self.colors['task_error']
            status = self._colorize(': ERROR', color)
        else:
            if task._cached_msg is not None:
                return task._cached_msg

            color = self.colors['task']
            if self.use_colors:
                status = ''
                if task._progress is not None:
                    status += ' ' + self._make_progress_bar(task._progress)
                if task._comment is not None:
                    status += ' - ' + str(task._comment)
                status = self._colorize(status, color)
                if task._comment is not None and task._comment_args:
                    status = status % task._comment_args
            else:
                status = self._colorize('...', color)

        msg = self._colorize('  ' * indent + str(task._msg), color)
        if task._args:
            msg = msg % task._args

        return msg + status + '\n'

    def _format_record(self, record: logging.LogRecord, process_color_tags: bool, rich_log_line: bool) -> str:
        # Format a record with respect to `_use_colors`.

        process_color_tags = getattr(record, 'yuio_process_color_tags', process_color_tags)

        if rich_log_line:
            color = Color.NONE
            tb_color = color

            fmt = '<c:rich_log_asctime>%s</c> '

            asctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
            if self.use_colors:
                asctime_color = self._get_color('rich_log_asctime')
                asctime = f'{asctime_color}{asctime}{Color.NONE}'

            logger = record.name
            if self.use_colors:
                logger_color = self._get_color('rich_log_logger')
                logger = f'{logger_color}{logger}{Color.NONE}'

            levelname = record.levelname
            if levelname in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
                levelname = levelname[:4]
            if self.use_colors:
                levelname_color = self._get_color(record.levelname.lower())
                tb_color = levelname_color
                if levelname_color == Color.NONE:
                    levelname_color = self._get_color('rich_log_default_level_color')
                levelname = f'{levelname_color}{levelname}{Color.NONE}'

            msg = f'{asctime} {logger} {levelname} {record.msg}'
        else:
            color = self._get_color(record.levelname.lower())
            tb_color = color
            msg = self._colorize(str(record.msg), color, process_color_tags)

        if record.args:
            msg = msg % record.args

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = ''.join(traceback.format_exception(*record.exc_info))
        if record.exc_text:
            msg += '\n' + textwrap.indent(self._colorize_tb(record.exc_text, tb_color), '    ')
        if record.stack_info:
            msg += '\n' + textwrap.indent(self._colorize_tb(record.stack_info, tb_color), '    ')

        if getattr(record, 'yuio_add_newline', True):
            msg += '\n'

        return msg

    _TAG_RE = re.compile(r'<c:(?P<name>[a-z0-9, _]+)>|</c>')

    def _colorize(self, msg: str, default_color: Color, process_color_tags: bool = True):
        # Colorize a message, process color tags if necessary.
        # Respect `_use_colors`.

        default_color = Color.FORE_NORMAL | Color.BACK_NORMAL | default_color

        if not process_color_tags:
            if self.use_colors:
                return default_color + msg + Color.NONE
            else:
                return msg

        if not self.use_colors:
            return self._TAG_RE.sub('', msg)

        out = []
        last_pos = 0
        stack = [default_color]

        out.append(default_color)

        for tag in self._TAG_RE.finditer(msg):
            out.append(msg[last_pos:tag.start()])
            last_pos = tag.end()

            if name := tag.group('name'):
                color = stack[-1]
                for sub_name in name.split(','):
                    sub_name = sub_name.strip()
                    color = color | self._get_color(sub_name)
                out.append(color)
                stack.append(color)
            elif len(stack) > 1:
                stack.pop()
                out.append(stack[-1])

        out.append(msg[last_pos:])

        out.append(Color.NONE)

        return ''.join(out)

    _TB_RE = re.compile(r'^(?P<indent>[ |+]*)(Stack|Traceback|Exception Group Traceback) \(most recent call last\):$', re.MULTILINE)
    _TB_LINE_FILE = re.compile(r'^[ |+]*File (?P<file>"[^"]*"), line (?P<line>\d+)(?:, in (?P<loc>.*))?$')
    _TB_LINE_HIGHLIGHT = re.compile(r'^[ |+^~-]*$')
    _SITE_PACKAGES = os.sep + 'site-packages' + os.sep

    def _colorize_tb(self, tb: str, default_color: Color):
        default_color = Color.FORE_NORMAL | Color.BACK_NORMAL | default_color

        if not self.use_colors:
            return tb

        out = []

        out.append(default_color)

        default_color_b = default_color | Color.STYLE_BOLD
        default_color_n = default_color | self.colors['note']

        default_color_d = default_color | Color.STYLE_DIM
        default_color_d_b = default_color_d | Color.STYLE_BOLD
        default_color_d_n = default_color_d | self.colors['note']

        base, bold, note = default_color, default_color_b, default_color_n

        indent = None
        for line in tb.splitlines(keepends=True):
            if indent and line.startswith(indent):
                if match := self._TB_LINE_FILE.match(line):
                    f, l, lc = match.group('file', 'line', 'loc')
                    if self._SITE_PACKAGES in f:
                        base, bold, note = default_color_d, default_color_d_b, default_color_d_n
                    else:
                        base, bold, note = default_color, default_color_b, default_color_n
                    if lc:
                        out.append(f'{base}{indent}File {note}{f}{base}, line {note}{l}{base}, in {note}{lc}{base}\n')
                    else:
                        out.append(f'{base}{indent}File {note}{f}{base}, line {note}{l}{base}\n')
                elif match := self._TB_LINE_HIGHLIGHT.match(line):
                    out.append(line)
                else:
                    out.append(indent)
                    out.append(bold)
                    out.append(line[len(indent):])
                    out.append(base)
                continue
            elif match := self._TB_RE.match(line):
                indent = match.group('indent').replace('+', '|') + '  '
            elif indent:
                indent = None
                base, bold, note = default_color, default_color_b, default_color_n
                out.append(base)

            out.append(line)

        out.append(Color.NONE)

        return ''.join(out)

    def _make_progress_bar(self, progress: _PROGRESS) -> str:
        width = 15

        progress_indicator = ''

        done_percentage = 0.0
        inflight_percentage = 0.0
        adjust_inflight = True

        if isinstance(progress, tuple):
            if len(progress) == 2:
                done_percentage = float(progress[0]) / float(progress[1])
                progress_indicator = f'{progress[0]} / {progress[1]}'
            elif len(progress) == 3:
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

    def _get_color(self, tag: str) -> Color:
        return self.colors.get(tag, Color.NONE)


logging.addLevelName(LogLevel.QUESTION, 'question')

_MSG_HANDLER_IMPL = _HandlerImpl()

_MSG_HANDLER = Handler(process_color_tags=True, rich_log_line=False)

_ROOT_LOGGER = logging.getLogger('yuio.io')
_ROOT_LOGGER.setLevel(1)
_ROOT_LOGGER.propagate = False
_ROOT_LOGGER.addHandler(_MSG_HANDLER)

_MSG_LOGGER = logging.getLogger('yuio.io.default')
_QUESTION_LOGGER = logging.getLogger('yuio.io.question')


if 'DEBUG' in os.environ:
    _MSG_LOGGER.setLevel(LogLevel.DEBUG)
