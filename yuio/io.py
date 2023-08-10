# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module implements user-friendly input and output on top of the python's
standard logging library.

"""
import math
from yuio.widget import RenderContext


"""

TODO!

Configuration
-------------

Yuio configures itself upon import using environment variables:

- ``DEBUG``: print debug-level messages,
- ``FORCE_NO_COLORS``: disable colored output,
- ``FORCE_COLORS``: enable colored output.

You can override this process by calling the :func:`setup` function.

.. autofunction:: setup


Logging messages
----------------

Use logging functions from this module:

.. autofunction:: info

.. autofunction:: warning

.. autofunction:: success

.. autofunction:: error

.. autofunction:: error_with_tb

.. autofunction:: question

.. autofunction:: heading

.. autofunction:: hr

.. autofunction:: br


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

import dataclasses
import enum
import functools
import getpass
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import types
import typing as _t
from logging import LogRecord

import yuio.parse
import yuio.term
import yuio.widget
from yuio.term import Color, Theme, DefaultTheme
from yuio.config import DISABLED, Disabled


T = _t.TypeVar('T')
U = _t.TypeVar('U')
Cb = _t.TypeVar('Cb', bound=_t.Callable[..., None])

_ExcInfo: _t.TypeAlias = _t.Tuple[_t.Optional[_t.Type[BaseException]], _t.Optional[BaseException], _t.Optional[types.TracebackType]]


_HANDLER_IMPL: _t.Optional["_HandlerImpl"] = None
_HANDLER_IMPL_LOCK = threading.Lock()


def _handler() -> "_HandlerImpl":
    global _HANDLER_IMPL
    if _HANDLER_IMPL is None:
        with _HANDLER_IMPL_LOCK:
            if _HANDLER_IMPL is None:
                _HANDLER_IMPL = _HandlerImpl()
    return _HANDLER_IMPL


class UserIoError(IOError):
    """Raised when interaction with user fails.

    """


def setup(
    *,
    term: _t.Optional[yuio.term.Term] = None,
    theme: _t.Optional[Theme] = None,
):
    """Initial setup of the logging facilities.

    :param term:
        terminal that will be used for output.
    :param theme:
        theme that will be used for output.

    """

    global _HANDLER_IMPL
    if _HANDLER_IMPL is None:
        with _HANDLER_IMPL_LOCK:
            if _HANDLER_IMPL is None:
                _HANDLER_IMPL = _HandlerImpl(term, theme)
                return

    _HANDLER_IMPL.setup(term, theme)


def get_term() -> yuio.term.Term:
    """Return current terminal.

    """

    return _handler().term


def get_theme() -> yuio.term.Theme:
    """Return current theme.

    """

    return _handler().theme


def info(msg: str, /, *args, **kwargs):
    """Log an info message.

    """

    _handler().print(msg, args, 'info', **kwargs)


def warning(msg: str, /, *args, **kwargs):
    """Log a warning message.

    """

    _handler().print(msg, args, 'warning', **kwargs)


def success(msg: str, /, *args, **kwargs):
    """Log a success message.

    """

    _handler().print(msg, args, 'success', **kwargs)


def error(msg: str, /, *args, **kwargs):
    """Log an error message.

    """

    _handler().print(msg, args, 'error', **kwargs)


def error_with_tb(msg: str, /, *args, **kwargs):
    """Log an error message and capture the current exception.

    Call this function in the `except` clause of a `try` block
    or in an `__exit__` function of a context manager to attach
    current exception details to the log message.

    """

    kwargs.setdefault('exc_info', True)
    _handler().print(msg, args, 'error', **kwargs)


def question(msg: str, /, *args, **kwargs):
    """Log a message with input prompts and other user communications.

    These messages don't end with newline.

    """

    _handler().print(msg, args, 'question', **kwargs)


def heading(msg: str, /, *args, **kwargs):
    """Log a heading message.

    """

    _handler().print(msg, args, 'heading', **kwargs)


def hr():
    """Print a horizontal ruler.

    """

    msg = '\n' + '┄' * shutil.get_terminal_size().columns + '\n'
    _handler().print(msg, None, 'hr')


def br():
    """Print an empty line.

    """

    _handler().print('', None, '')


class _Ask(_t.Generic[T]):
    def __init__(self, parser: yuio.parse.Parser[T]):
        self._parser: yuio.parse.Parser[T] = parser

    def __getitem__(self, ty: _t.Type[U]) -> '_Ask[U]':
        # eval type
        container = type("_container", (), {"__annotations__": {"ty": ty}})
        annotations = _t.get_type_hints(container, include_extras=True)
        return _Ask(yuio.parse.from_type_hint(annotations["ty"]))

    @_t.overload
    def __call__(
        self,
        msg: str,
        /,
        *args,
        default: _t.Union[T, "Disabled"] = DISABLED,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> T: ...

    @_t.overload
    def __call__(
        self,
        msg: str,
        /,
        *args,
        default: None,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> _t.Optional[T]: ...

    @_t.overload
    def __call__(
        self,
        msg: str,
        /,
        *args,
        parser: yuio.parse.Parser[U],
        default: _t.Union[U, "Disabled"] = DISABLED,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> U: ...

    @_t.overload
    def __call__(
        self,
        msg: str,
        /,
        *args,
        parser: yuio.parse.Parser[U],
        default: None,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> _t.Optional[U]: ...

    def __call__(
        self,
        msg: str,
        /,
        *args,
        parser: _t.Union[yuio.parse.Parser, None] = None,
        default: _t.Any = DISABLED,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> _t.Any:
        if sys.stdin is None or not sys.stdin.readable():
            if default is not DISABLED:
                return default
            else:
                raise UserIoError(
                    'can\'t interact with user in non-interactive environment'
                )

        if parser is None:
            parser = self._parser
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


ask: _Ask[str] = _Ask[str](yuio.parse.Str())
"""Ask user to provide an input, parse it and return a value.

If `stdin` is not readable, return default if one is present,
or raises a :class:`UserIoError`.

Accepts generic parameters, which determine input parser.

Example::

    answer = ask[bool]('Do you want a choco bar?', default=True)

:param msg:
    prompt to display to user.
:param args:
    arguments for prompt formatting.
:param parser:
    parser to use to parse user input. See :mod:`yuio.parse` for more info.
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


@_t.overload
def ask_yn(
    msg: str,
    /,
    *args,
    default: _t.Union[bool, "Disabled"] = DISABLED,
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
    default: _t.Union[bool, None, "Disabled"] = DISABLED,
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

    If `stdin` is not readable, does not do anything.

    """

    if sys.stdin is None or not sys.stdin.readable():
        return

    with SuspendLogging() as s:
        s.question(msg, *args)
        try:
            input()
        except EOFError:
            return


def detect_editor() -> _t.Optional[str]:
    """Detect the user's preferred editor.

    This function checks the ``EDITOR`` environment variable.
    If it's not found, it checks whether ``nano`` or ``vi``
    are available. Otherwise, it returns `None`.

    """

    if editor := os.environ.get('EDITOR'):
        return editor
    elif editor := shutil.which('nano'):
        return editor
    elif editor := shutil.which('vi'):
        return editor
    elif editor := shutil.which('notepad'):
        return editor
    else:
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

    if _handler().term.is_fully_interactive:
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
        _handler().suspend()

    def resume(self):
        """Manually resume the logging process.

        """

        if not self._resumed:
            _handler().resume()
            self._resumed = True

    @staticmethod
    def info(msg: str, /, *args, **kwargs):
        """Log an :func:`info` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        info(msg, *args, **kwargs)


    @staticmethod
    def warning(msg: str, /, *args, **kwargs):
        """Log a :func:`warning` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        warning(msg, *args, **kwargs)


    @staticmethod
    def success(msg: str, /, *args, **kwargs):
        """Log a :func:`success` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        success(msg, *args, **kwargs)


    @staticmethod
    def error(msg: str, /, *args, **kwargs):
        """Log an :func:`error` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        error(msg, *args, **kwargs)

    @staticmethod
    def error_with_tb(msg: str, /, *args, **kwargs):
        """Log an :func:`error_with_tb` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        error_with_tb(msg, *args, **kwargs)

    @staticmethod
    def question(msg: str, /, *args, **kwargs):
        """Log a :func:`question` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        question(msg, *args, **kwargs)


    @staticmethod
    def heading(msg: str, /, *args, **kwargs):
        """Log a :func:`heading` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        heading(msg, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.resume()


class Group:
    """A context manager for printing grouped messages.

    It prints a group's heading

    """

    def __init__(self, msg: str, /, *args):
        _handler().print(msg, args, 'group')
        _handler().indent()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _handler().dedent()


class _IterTask(_t.Generic[T]):
    def __init__(self, collection: _t.Collection[T], task: 'Task'):
        self._iter = iter(collection)
        self._task = task

        self._i = 0
        self._len = len(collection)

    def __next__(self) -> T:
        self._task.progress(self._i, self._len)
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
        RUNNING = "running"
        DONE = "done"
        ERROR = "error"

    def __init__(self, msg: str, /, *args, _parent: _t.Optional['Task'] = None):
        # Task properties should not be written to directly.
        # Instead, task should be sent to a handler for modification.
        # This ensures thread safety, because handler has a lock.
        # See handler's implementation details.

        self._msg: str = msg
        self._args: tuple = args
        self._comment: _t.Optional[str] = None
        self._comment_args: _t.Optional[tuple] = None
        self._status: Task._Status = Task._Status.RUNNING
        self._progress: _t.Optional[float] = None
        self._progress_done: _t.Optional[str] = None
        self._progress_total: _t.Optional[str] = None
        self._subtasks: _t.List[Task] = []

        self._cached_msg: _t.Optional[yuio.term.ColorizedString] = None
        self._cached_comment: _t.Optional[yuio.term.ColorizedString] = None

        if _parent is None:
            _handler().start_task(self)
        else:
            _handler().start_subtask(_parent, self)

    @_t.overload
    def progress(self, progress: _t.Optional[float], /, *, ndigits: int = 2): ...

    @_t.overload
    def progress(self, done: float, total: _t.Optional[float], /, *, unit: str = "", ndigits: int = 0): ...

    def progress(self, *args: _t.Optional[float], unit: str = "", ndigits: _t.Optional[int] = None):
        """Indicate progress of this task.

        If given one argument, it is treated as percentage between `0` and `1`.

        If given two arguments, they are treated as amount of finished work,
        and a total amount of work. In this case, optional argument `unit`
        can be used to indicate units, in which amount is calculated::

            >>> with Task("Loading cargo") as task:
            ...     task.progress(13, 150, unit="Kg")
            Loading cargo - 13/150Kg

        """

        progress = None

        if len(args) == 1:
            progress = done = args[0]
            total = None
            if ndigits is None:
                ndigits = 2
        elif len(args) == 2:
            done, total = args
            if ndigits is None:
                ndigits = 0
        else:
            raise ValueError(
                f"Task.progress() takes between one and two arguments "
                f"({len(args)} given)"
            )

        if done is None:
            _handler().set_progress(self, None, None, None)
            return

        if len(args) == 1:
            done *= 100
            unit = "%"

        done_str = "%.*f" % (ndigits, done)
        if total is None:
            _handler().set_progress(self, progress, done_str + unit, None)
        else:
            total_str = "%.*f" % (ndigits, total)
            progress = done / total
            _handler().set_progress(self, progress, done_str, total_str + unit)

    def progress_size(
        self,
        done: _t.Union[float, int],
        total: _t.Union[float, int],
        /,
        *,
        ndigits: int = 2,
    ):
        """Indicate progress of this task using human-readable 1024-based size units.

        Example::

            >>> with Task("Downloading a file") as task:
            ...     task.progress_size(31.05 * 2**20, 150 * 2**20)
            Downloading a file - 31.05/150.00M

        """

        progress = done / total
        done, done_unit = self._size(done)
        total, total_unit = self._size(total)

        if done_unit == total_unit:
            done_unit = ""

        _handler().set_progress(
            self,
            progress,
            "%.*f%s" % (ndigits, done, done_unit),
            "%.*f%s" % (ndigits, total, total_unit)
        )

    @staticmethod
    def _size(n):
        for unit in "BKMGTP":
            if n < 1024:
                return n, unit
            n /= 1024
        return n, "P"

    def progress_scale(
            self,
            done: _t.Union[float, int],
            total: _t.Union[float, int],
            /,
            *,
            unit: str = "",
            ndigits: int = 2,
        ):
        """Indicate progress of this task while scaling numbers in accordance
        with SI system.

        Example::

            >>> with Task("Charging a capacitor") as task:
            ...     task.progress_scale(1.25E-6, 10E-6, unit="F")
            Charging a capacitor - 1.35µF/10.00µF

        """

        progress = done / total
        done, done_unit = self._unit(done)
        total, total_unit = self._unit(total)

        if unit:
            done_unit += unit
            total_unit += unit

        _handler().set_progress(
            self,
            progress,
            "%.*f%s" % (ndigits, done, done_unit),
            "%.*f%s" % (ndigits, total, total_unit)
        )

    @staticmethod
    def _unit(n: float) -> _t.Tuple[float, str]:
        if math.fabs(n) < 1e-33:
            return 0, ""
        magnitude = max(-8, min(8, int(math.log10(math.fabs(n)) // 3)))
        if magnitude < 0:
            return n * 10 ** -(3 * magnitude), "mµnpfazy"[-magnitude - 1]
        elif magnitude > 0:
            return n / 10 ** (3 * magnitude), "kMGTPEZY"[magnitude - 1]
        else:
            return n, ""

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

        _handler().set_comment(self, comment, args)

    def done(self):
        """Indicate that this task has finished successfully.

        """

        _handler().finish_task(self, Task._Status.DONE)

    def error(self):
        """Indicate that this task has finished with an error.

        """

        _handler().finish_task(self, Task._Status.ERROR)

    def subtask(self, msg: str, /, *args) -> 'Task':
        """Create a subtask within this task.

        """

        return Task(msg, *args, _parent=self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done()
        else:
            self.error()


class Handler(logging.Handler):
    """A handler that redirects all log messages to yuio.

    """

    def createLock(self) -> None:
        self.lock = None

    def emit(self, record: LogRecord) -> None:
        _handler().emit(record)


class _HandlerImpl:
    def __init__(
        self,
        term: _t.Optional[yuio.term.Term] = None,
        theme: _t.Optional[Theme] = None,
    ):
        term = term or yuio.term.get_stderr_info()
        theme = theme or DefaultTheme(term)

        self._rc = yuio.widget.RenderContext(term, theme)

        self._indent = 0

        self._suspended: int = 0
        self._suspended_lines: _t.List[yuio.term.ColorizedString] = []

        self._tasks: _t.List[Task] = []
        self._tasks_printed = 0
        self._spinner_state = 0
        self._needs_update = False
        self._last_update_time_us = 0

        self._lock = threading.Lock()

        self._renders = 0

        threading.Thread(target=self._bg_update, name='yuio_io_thread', daemon=True).start()

    @property
    def term(self) -> yuio.term.Term:
        return self._rc.term

    @property
    def theme(self) -> yuio.term.Theme:
        return self._rc.theme

    @functools.cached_property
    def update_rate_us(self) -> int:
        update_rate_ms = max(self.theme.spinner_update_rate_ms, 1)
        while update_rate_ms < 50:
            update_rate_ms *= 2
        while update_rate_ms > 100:
            update_rate_ms /= 2
        return int(update_rate_ms * 1000)

    @property
    def spinner_update_rate_us(self) -> int:
        return self.theme.spinner_update_rate_ms * 1000

    def _bg_update(self):
        while True:
            try:
                update_rate_us = self.update_rate_us

                while True:
                    now_us = time.monotonic_ns() // 1000
                    sleep_us = update_rate_us - now_us % update_rate_us
                    time.sleep(sleep_us / 1_000_000)

                    with self._lock:
                        self._show_tasks()
                        update_rate_us = self.update_rate_us
            except Exception:
                yuio._logger.critical("exception in bg updater", exc_info=True)

    def setup(
        self,
        term: _t.Optional[yuio.term.Term] = None,
        theme: _t.Optional[Theme] = None,
    ):
        with self._lock:
            term = term or self.term
            theme = theme or self.theme

            self._clear_tasks()
            self._rc = yuio.widget.RenderContext(term, theme)
            del self.update_rate_us
            self._update_tasks()

    def indent(self):
        with self._lock:
            self._indent += 1

    def dedent(self):
        with self._lock:
            self._indent -= 1

            if self._indent < 0:
                self._indent = 0
                yuio._logger.error('unequal number of indents and dedents')

    def print(
        self,
        msg: str,
        args: _t.Optional[tuple],
        m_tag: str,
        /,
        *,
        exc_info: _t.Union["_ExcInfo", bool, None] = None,
        ignore_suspended: bool = False,
    ):
        if exc_info is True:
            exc_info = sys.exc_info()
        elif exc_info is False or exc_info is None:
            exc_info = None
        elif isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
        elif not isinstance(exc_info, tuple) or len(exc_info) != 3:
            raise ValueError(f"invalid exc_info {exc_info!r}")

        with self._lock:
            line = self._format_line(msg, args, m_tag, exc_info)
            self._emit(line, ignore_suspended)

    def emit(
        self,
        record: logging.LogRecord,
    ):
        with self._lock:
            line = self._format_record(record)
            self._emit(line)

    def start_task(self, task: Task):
        with self._lock:
            self._start_task(task)

    def start_subtask(self, parent: Task, task: Task):
        with self._lock:
            self._start_subtask(parent, task)

    def finish_task(self, task: Task, status: Task._Status):
        with self._lock:
            self._finish_task(task, status)

    def set_progress(self, task: Task, progress: _t.Optional[float], done: _t.Optional[str], total: _t.Optional[str]):
        with self._lock:
            task._progress = progress
            task._progress_done = done
            task._progress_total = total
            self._update_tasks()

    def set_comment(self, task: Task, comment: _t.Optional[str], args):
        with self._lock:
            task._comment = comment
            task._comment_args = args
            task._cached_comment = None
            self._update_tasks()

    def suspend(self):
        with self._lock:
            self._suspend()

    def resume(self):
        with self._lock:
            self._resume()

    # Implementation.
    # These functions are always called under a lock.

    def _emit(self, msg: yuio.term.ColorizedString, ignore_suspended: bool = False):
        if self._suspended and not ignore_suspended:
            self._suspended_lines.append(msg)
        else:
            self._clear_tasks()
            msg.write_to(self.term)
            self._update_tasks(immediate_update=True)

        self._printed_some_lines = True

    def _suspend(self):
        self._suspended += 1

        if self._suspended == 1 and self.term.can_move_cursor:
            # We're entering the suspended state, and some tasks may be displayed.
            # We need to hide them then.
            self._clear_tasks()

    def _resume(self):
        self._suspended -= 1

        if self._suspended == 0:
            # We're exiting the suspended state, so dump all stashed lines...
            for line in self._suspended_lines:
                line.write_to(self.term)
            self._suspended_lines.clear()

            # And we need to print tasks that we've hidden in `_suspend`.
            self._update_tasks()

        if self._suspended < 0:
            yuio._logger.debug('unequal number of suspends and resumes')
            self._suspended = 0

    def _start_task(self, task: Task):
        if self.term.can_move_cursor:
            self._tasks.append(task)
            self._update_tasks()
        else:
            self._emit(self._format_task(task))

    def _start_subtask(self, parent: Task, task: Task):
        if self.term.can_move_cursor:
            parent._subtasks.append(task)
            self._update_tasks()
        else:
            self._emit(self._format_task(task))

    def _finish_task(self, task: Task, status: Task._Status):
        if task._status != Task._Status.RUNNING:
            yuio._logger.debug('trying to change status of an already stopped task')
            return

        task._status = status

        if self.term.can_move_cursor:
            if task in self._tasks:
                self._tasks.remove(task)
            self._update_tasks(immediate_update=True)
        else:
            self._emit(self._format_task(task))

    def _clear_tasks(self):
        if self.term.can_move_cursor and self._tasks_printed:
            self._rc.finalize()
            self._tasks_printed = 0

    def _update_tasks(self, immediate_update: bool = False):
        self._needs_update = True
        if immediate_update:
            self._show_tasks(immediate_update)

    def _show_tasks(self, immediate_update: bool = False):
        if self.term.can_move_cursor and (self._tasks or self._tasks_printed):
            now_us = time.monotonic_ns() // 1000
            now_us -= now_us % self.update_rate_us

            if not immediate_update:
                next_update_us = self._last_update_time_us + self.update_rate_us
                if now_us < next_update_us:
                    # Hard-limit update rate by `update_rate_ms`.
                    return
                next_spinner_update_us = self._last_update_time_us + self.spinner_update_rate_us
                if not self._needs_update and now_us < next_spinner_update_us:
                    # Tasks didn't change, and spinner state didn't change either,
                    # so we can skip this update.
                    return

            self._last_update_time_us = now_us
            self._spinner_state = now_us // self.spinner_update_rate_us
            self._tasks_printed = 0
            self._needs_update = False

            self._rc.prepare()
            for task in self._tasks:
                self._draw_task(task, 0)
            self._renders += 1
            self._rc.set_final_pos(0, self._tasks_printed)
            self._rc.render()

    def _format_line(
        self,
        msg: str,
        args: _t.Optional[tuple],
        m_tag: str,
        exc_info: _t.Union["_ExcInfo", bool, None] = None,
    ) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        if self._indent:
            res += '  ' * self._indent

        if decoration := self.theme.msg_decorations.get(m_tag):
            res += self.theme.get_color(f'msg/{m_tag}/decoration')
            res += decoration
            res += Color.NONE
            res += ' '

        col_msg = self.theme.colorize(msg, default_color=f'msg/{m_tag}/text')
        if args:
            col_msg %= args
        res += col_msg
        res += "\n"

        if exc_info is not None:
            res += self._format_tb(
                ''.join(traceback.format_exception(*exc_info)), '  ' * (self._indent + 1))

        return res

    def _format_record(self, record: logging.LogRecord) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        plain_text_color = self.theme.get_color('log/plain_text')

        asctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        logger = record.name
        level = record.levelname
        if level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            level = level[:4]
        message = record.getMessage()

        res += self.theme.get_color(f'log/asctime')
        res += asctime
        res += plain_text_color
        res += ' '

        res += self.theme.get_color(f'log/logger')
        res += logger
        res += plain_text_color
        res += ' '

        res += self.theme.get_color(f'log/level/{record.levelname.lower()}')
        res += level
        res += plain_text_color
        res += ' '

        res += self.theme.get_color(f'log/message')
        res += message
        res += plain_text_color
        res += '\n'

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = ''.join(traceback.format_exception(*record.exc_info))
            res += self._format_tb(record.exc_text, '  ')
        if record.stack_info:
            res += self._format_tb(record.stack_info, '  ')

        res += Color.NONE

        return res

    class _StackParsingState(enum.Enum):
        PLAIN_TEXT = enum.auto()
        STACK = enum.auto()
        MESSAGE = enum.auto()

    class _StackColors:
        def __init__(self, theme: Theme, s_tag: str):
            self.file_color = theme.get_color(f'tb/frame/{s_tag}/file')
            self.file_path_color = theme.get_color(f'tb/frame/{s_tag}/file/path')
            self.file_line_color = theme.get_color(f'tb/frame/{s_tag}/file/line')
            self.file_module_color = theme.get_color(f'tb/frame/{s_tag}/file/module')
            self.code_color = theme.get_color(f'tb/frame/{s_tag}/code')
            self.highlight_color = theme.get_color(f'tb/frame/{s_tag}/highlight')

    _TB_RE = re.compile(r'^(?P<indent>[ |+]*)(Stack|Traceback|Exception Group Traceback) \(most recent call last\):$')
    _TB_MSG_RE = re.compile(r'^(?P<indent>[ |+]*)[A-Za-z_][A-Za-z0-9_]*($|:.*$)')
    _TB_LINE_FILE = re.compile(r'^[ |+]*File (?P<file>"[^"]*"), line (?P<line>\d+)(?:, in (?P<loc>.*))?$')
    _TB_LINE_HIGHLIGHT = re.compile(r'^[ |+^~-]*$')
    _SITE_PACKAGES = os.sep + 'lib' + os.sep + 'site-packages' + os.sep
    _LIB_PYTHON = os.sep + 'lib' + os.sep + 'python'

    def _format_tb(self, tb: str, indent: str) -> yuio.term.ColorizedString:
        if not self.term.can_move_cursor:
            if indent:
                tb = textwrap.indent(tb, indent)
            return yuio.term.ColorizedString(tb)

        plain_text_color = self.theme.get_color('tb/plain_text')
        heading_color = self.theme.get_color('tb/heading')
        message_color = self.theme.get_color('tb/message')

        stack_normal_colors = self._StackColors(self.theme, 'usr')
        stack_lib_colors = self._StackColors(self.theme, 'lib')
        stack_colors = stack_normal_colors

        res = yuio.term.ColorizedString()

        state: _HandlerImpl._StackParsingState = _HandlerImpl._StackParsingState.PLAIN_TEXT
        stack_indent = ''
        message_indent = ''

        for line in tb.splitlines(keepends=True):
            if state is _HandlerImpl._StackParsingState.STACK:
                if line.startswith(stack_indent):
                    # We're still in the stack.
                    if match := self._TB_LINE_FILE.match(line):
                        file, line, loc = match.group('file', 'line', 'loc')

                        if self._SITE_PACKAGES in file or self._LIB_PYTHON in file:
                            stack_colors = stack_lib_colors
                        else:
                            stack_colors = stack_normal_colors

                        res += plain_text_color
                        res += indent
                        res += stack_indent
                        res += stack_colors.file_color
                        res += 'File '
                        res += stack_colors.file_path_color
                        res += file
                        res += stack_colors.file_color
                        res += ', line '
                        res += stack_colors.file_line_color
                        res += line
                        res += stack_colors.file_color

                        if loc:
                            res += ', in '
                            res += stack_colors.file_module_color
                            res += loc
                            res += stack_colors.file_color

                        res += '\n'
                    elif match := self._TB_LINE_HIGHLIGHT.match(line):
                        res += plain_text_color
                        res += indent
                        res += stack_indent
                        res += stack_colors.highlight_color
                        res += line[len(stack_indent):]
                    else:
                        res += plain_text_color
                        res += indent
                        res += stack_indent
                        res += stack_colors.code_color
                        res += line[len(stack_indent):]
                    continue
                else:
                    # Stack has ended, this line is actually a message.
                    state = _HandlerImpl._StackParsingState.MESSAGE

            if state is _HandlerImpl._StackParsingState.MESSAGE:
                if line and line != '\n' and line.startswith(message_indent):
                    # We're still in the message.
                    res += plain_text_color
                    res += indent
                    res += message_indent
                    res += message_color
                    res += line[len(message_indent):]
                    continue
                else:
                    # Message has ended, this line is actually a plain text.
                    state = _HandlerImpl._StackParsingState.PLAIN_TEXT

            if state is _HandlerImpl._StackParsingState.PLAIN_TEXT:
                if match := self._TB_RE.match(line):
                    # Plain text has ended, this is actually a heading.
                    message_indent = match.group('indent').replace('+', '|')
                    stack_indent = message_indent + '  '

                    res += plain_text_color
                    res += indent
                    res += message_indent
                    res += heading_color
                    res += line[len(message_indent):]

                    state = _HandlerImpl._StackParsingState.STACK
                    continue
                elif match := self._TB_MSG_RE.match(line):
                    # Plain text has ended, this is an error message (without a traceback).
                    message_indent = match.group('indent').replace('+', '|')
                    stack_indent = message_indent + '  '

                    res += plain_text_color
                    res += indent
                    res += message_indent
                    res += message_color
                    res += line[len(message_indent):]

                    state = _HandlerImpl._StackParsingState.MESSAGE
                    continue
                else:
                    # We're still in plain text.
                    res += plain_text_color
                    res += indent
                    res += line
                    continue

        res += Color.NONE

        return res

    def _format_task(self, task: Task) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        if decoration := self.theme.msg_decorations.get("task"):
            res += self.theme.get_color(f"task/decoration/{task._status.value}")
            res += decoration
            res += self.theme.get_color("task/plain_text")
            res += " "

        res += self._format_task_msg(task)
        res += self.theme.get_color("task/plain_text")
        res += " - "
        res += self.theme.get_color("task/progress")
        res += task._status.value
        res += self.theme.get_color("task/plain_text")
        res += "\n"

        return res

    def _format_task_msg(self, task: Task) -> yuio.term.ColorizedString:
        if task._cached_msg is None:
            msg = self.theme.colorize(task._msg, default_color="task/heading")
            if task._args:
                msg %= task._args
            task._cached_msg = msg
        return task._cached_msg

    def _format_task_comment(self, task: Task) -> _t.Optional[yuio.term.ColorizedString]:
        if task._cached_comment is None and task._comment is not None:
            comment = self.theme.colorize(task._comment, default_color="task/comment")
            if task._comment_args:
                comment %= task._comment_args
            task._cached_comment = comment
        return task._cached_comment

    def _draw_task(self, task: Task, indent: int):
        self._tasks_printed += 1
        self._rc.move_pos(indent * 2, 0)
        self._draw_task_progressbar(task)
        self._rc.write(self._format_task_msg(task))
        self._draw_task_progress(task)
        if comment := self._format_task_comment(task):
            self._rc.set_color_path("task/plain_text")
            self._rc.write(' - ')
            self._rc.write(comment)
        self._rc.new_line()

        for subtask in task._subtasks:
            self._draw_task(subtask, indent + 1)

    def _draw_task_progress(self, task: Task):
        if task._progress_done is None:
            return None

        self._rc.set_color_path("task/plain_text")
        self._rc.write(' - ')

        if task._status in (Task._Status.DONE, Task._Status.ERROR):
            self._rc.set_color_path(f'task/progress')
            self._rc.write(task._status.name.lower())
        else:
            self._rc.set_color_path('task/progress')
            self._rc.write(task._progress_done)
            if task._progress_total is not None:
                self._rc.set_color_path("task/plain_text")
                self._rc.write('/')
                self._rc.set_color_path('task/progress')
                self._rc.write(task._progress_total)

    def _draw_task_progressbar(self, task: Task):
        if task._status != Task._Status.RUNNING:
            self._rc.set_color_path(f"task/decoration/{task._status.value}")
            self._rc.write(self.theme.spinner_static_symbol)
        elif task._progress is None:
            self._rc.set_color_path(f"task/decoration/{task._status.value}")
            self._rc.write(self.theme.spinner_pattern[self._spinner_state % len(self.theme.spinner_pattern)])
        else:
            done_width = round(max(0, min(1, task._progress)) * self.theme.progress_bar_width)
            pending_width = self.theme.progress_bar_width - done_width
            self._rc.set_color_path("task/progressbar")
            self._rc.write(self.theme.progress_bar_start_symbol)
            self._rc.set_color_path("task/progressbar/done")
            self._rc.write(self.theme.progress_bar_done_symbol * done_width)
            self._rc.set_color_path("task/progressbar/pending")
            self._rc.write(self.theme.progress_bar_pending_symbol * pending_width)
            self._rc.set_color_path("task/progressbar")
            self._rc.write(self.theme.progress_bar_end_symbol)
        self._rc.set_color_path("task/plain_text")
        self._rc.write(" ")
