# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module implements user-friendly console input and output.

Configuration
-------------

Yuio configures itself upon import using environment variables:

- ``FORCE_NO_COLORS``: disable colored output,
- ``FORCE_COLORS``: enable colored output.

The only thing it doesn't do automatically is wrapping :data:`sys.stdout`
and :data:`sys.stderr` into safe proxies. The :mod:`yuio.app` CLI builder
will do it for you, though, so you don't need to worry about it.

.. autofunction:: setup

To introspect the current state of Yuio's initialization, use the following functions:

.. autofunction:: get_term

.. autofunction:: get_theme

.. autofunction:: wrap_streams

.. autofunction:: restore_streams

.. autofunction:: streams_wrapped

.. autofunction:: orig_stderr

.. autofunction:: orig_stdout


Printing messages
-----------------

To print messages for the user, use these functions:

.. autofunction:: info

.. autofunction:: warning

.. autofunction:: success

.. autofunction:: error

.. autofunction:: error_with_tb

.. autofunction:: heading

.. autofunction:: md

.. autofunction:: br

.. autofunction:: raw


Coloring the output
-------------------

By default, all messages are colored according to their level.

If you need inline colors, you can use special tags in your log messages::

    info('Using the <c code>code</c> tag.')

You can combine multiple colors in the same tag::

    info('<c bold green>Success!</c>')

Only tags that appear in the message itself are processed::

    info('Tags in this message --> %s are printed as-is', '<c color>')

For highlighting inline code, Yuio supports parsing CommonMark's backticks::

    info('Using the `backticks`.')
    info('Using the `` nested `backticks` ``, like they do on GitHub!')

List of all tags that are available by default:

- ``code``, ``note``: highlights,
- ``bold``, ``b``, ``dim``, ``d``: font style,
- ``normal``, ``black``, ``red``, ``green``, ``yellow``, ``blue``,
  ``magenta``, ``cyan``, ``white``: colors.


Customizing colors and using themes
-----------------------------------

The :func:`setup` function accepts a :class:`~yuio.theme.Theme` class.
You can subclass it and supply custom colors, see :mod:`yuio.theme`
for more info.


Indicating progress
-------------------

You can use the :class:`Task` class to indicate status and progress
of some task:

.. autoclass:: Task


   .. automethod:: progress

   .. automethod:: progress_size

   .. automethod:: progress_scale

   .. automethod:: iter

   .. automethod:: comment

   .. automethod:: done

   .. automethod:: error

   .. automethod:: subtask


Querying user input
-------------------

If you need to get something from the user, :func:`ask` is the way to do it.

.. autofunction:: ask

.. autofunction:: wait_for_user

You can also prompt the user to edit something with the :func:`edit` function:

.. autofunction:: edit

.. autofunction:: detect_editor

All of these functions throw a error if something goes wrong:

.. autoclass:: UserIoError


Suspending the output
---------------------

You can temporarily disable printing of tasks and messages
using the :class:`SuspendLogging` context manager.

.. autoclass:: SuspendLogging

   .. automethod:: resume

   .. automethod:: info

   .. automethod:: warning

   .. automethod:: success

   .. automethod:: error

   .. automethod:: error_with_tb

   .. automethod:: heading

   .. automethod:: md

   .. automethod:: br

   .. automethod:: raw


Python's `logging` and yuio
---------------------------

If you want to direct messages from the :mod:`logging` to Yuio,
you can add a :class:`Handler`:

.. autoclass:: Handler

"""

import abc
import atexit
import enum
import functools
import getpass
import logging
import math
import os
import re
import shutil
import string
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import types
from logging import LogRecord

import yuio.complete
import yuio.md
import yuio.parse
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _t
from yuio.term import Color, Term
from yuio.theme import Theme
from yuio.widget import RenderContext

T = _t.TypeVar("T")
U = _t.TypeVar("U")
Cb = _t.TypeVar("Cb", bound=_t.Callable[..., None])

_ExcInfo: _t.TypeAlias = _t.Tuple[
    _t.Optional[_t.Type[BaseException]],
    _t.Optional[BaseException],
    _t.Optional[types.TracebackType],
]


_IO_LOCK = threading.Lock()
_IO_MANAGER: _t.Optional["_IoManager"] = None
_STREAMS_WRAPPED: bool = False
_ORIG_STDERR: _t.Optional[_t.TextIO] = None
_ORIG_STDOUT: _t.Optional[_t.TextIO] = None
_IO_MANAGER: _t.Optional["_IoManager"] = None


def _manager() -> "_IoManager":
    global _IO_MANAGER

    if _IO_MANAGER is None:
        with _IO_LOCK:
            if _IO_MANAGER is None:
                _IO_MANAGER = _IoManager()
    return _IO_MANAGER


def setup(
    *,
    term: _t.Optional[Term] = None,
    theme: _t.Union[Theme, _t.Callable[[Term], Theme], None] = None,
    wrap_stdio: bool = True,
):
    """Initial setup of the logging facilities.

    :param term:
        terminal that will be used for output.

        If not passed, the global terminal is not set up;
        the default is to use a term attached to :data:`sys.stderr`.
    :param theme:
        either a theme that will be used for output, or a theme constructor that takes
        a :class:`~yuio.term.Term` and returns a theme.

        If not passed, the global theme is not set up; the default is to use
        :class:`yuio.term.DefaultTheme` then.
    :param wrap_stdio:
        if set to :data:`True`, wraps :data:`sys.stdout` and :data:`sys.stderr`
        in a special wrapper that ensures better interaction
        with Yuio's progress bars and widgets.

        .. note::

           If you're working with some other library that wraps :data:`sys.stdout`
           and :data:`sys.stderr`, such as :mod:`colorama`, initialize it before Yuio.

    """

    global _IO_MANAGER

    if not (manager := _IO_MANAGER):
        with _IO_LOCK:
            if not (manager := _IO_MANAGER):
                _IO_MANAGER = _IoManager(term, theme)
    if manager is not None:
        manager.setup(term, theme)

    if wrap_stdio:
        wrap_streams()


def get_term() -> Term:
    """Get the global instance of :class:`~yuio.term.Term` that is used
    with :mod:`yuio.io`.

    If global setup wasn't performed, this function implicitly performs it.

    """

    return _manager().term


def get_theme() -> Theme:
    """Get the global instance of :class:`~yuio.term.Theme`
    that is used with :mod:`yuio.io`.

    If global setup wasn't performed, this function implicitly performs it.

    """

    return _manager().theme


def wrap_streams():
    """Wrap :data:`sys.stdout` and :data:`sys.stderr` so that they honor
    Yuio tasks and widgets.

    .. note::

        If you're working with some other library that wraps :data:`sys.stdout`
        and :data:`sys.stderr`, such as :mod:`colorama`, initialize it before Yuio.

    See :func:`setup`.

    """

    global _STREAMS_WRAPPED, _ORIG_STDOUT, _ORIG_STDERR

    if _STREAMS_WRAPPED:
        return

    if yuio.term._is_interactive_output(sys.stdout):
        _ORIG_STDOUT, sys.stdout = sys.stdout, _WrappedOutput(sys.stdout)
    if yuio.term._is_interactive_output(sys.stderr):
        _ORIG_STDERR, sys.stderr = sys.stderr, _WrappedOutput(sys.stderr)
    _STREAMS_WRAPPED = True

    atexit.register(restore_streams)


def restore_streams():
    """Restore wrapped streams.

    See :func:`wrap_streams` and :func:`setup`.

    """

    global _STREAMS_WRAPPED

    if not _STREAMS_WRAPPED:
        return

    with _IO_LOCK:
        if _ORIG_STDOUT is not None:
            sys.stdout = _ORIG_STDOUT
        if _ORIG_STDERR is not None:
            sys.stderr = _ORIG_STDERR
        _STREAMS_WRAPPED = False


def streams_wrapped() -> bool:
    """Check if :data:`sys.stdout` and :data:`sys.stderr` are wrapped.
    See :func:`setup`.

    """

    return _STREAMS_WRAPPED


def orig_stderr() -> _t.TextIO:
    """Return the original :data:`sys.stderr` before wrapping."""

    return _ORIG_STDERR or sys.stderr


def orig_stdout() -> _t.TextIO:
    """Return the original :data:`sys.stdout` before wrapping."""

    return _ORIG_STDOUT or sys.stdout


class UserIoError(IOError):
    """Raised when interaction with user fails."""


def info(msg: str, /, *args, **kwargs):
    """Print an info message."""

    _manager().print_msg(msg, args, "info", **kwargs)


def warning(msg: str, /, *args, **kwargs):
    """Print a warning message."""

    _manager().print_msg(msg, args, "warning", **kwargs)


def success(msg: str, /, *args, **kwargs):
    """Print a success message."""

    _manager().print_msg(msg, args, "success", **kwargs)


def error(msg: str, /, *args, **kwargs):
    """Print an error message."""

    _manager().print_msg(msg, args, "error", **kwargs)


def error_with_tb(msg: str, /, *args, **kwargs):
    """Print an error message and capture the current exception.

    Call this function in the `except` clause of a `try` block
    or in an `__exit__` function of a context manager to attach
    current exception details to the log message.

    :param: exc_info
        either a boolean indicating that the current exception
        should be captured (default is :data:`True`), or a tuple
        of three elements, as returned by :func:`sys.exc_info`.

    """

    kwargs.setdefault("exc_info", True)
    _manager().print_msg(msg, args, "error", **kwargs)


def heading(msg: str, /, *args, **kwargs):
    """Print a heading message."""

    kwargs.setdefault("heading", True)
    _manager().print_msg(msg, args, "heading/1", **kwargs)


def md(msg: str, /, *args, **kwargs):
    """Print a markdown-formatted text.

    Yuio supports all CommonMark block markup. Inline markup is limited
    to backticks and color tags.

    See :mod:`yuio.md` for more info.

    """

    _manager().print_md(msg, args, **kwargs)


def br(**kwargs):
    """Print an empty string."""

    _manager().print_direct("\n", **kwargs)


def raw(msg: yuio.term.ColorizedString, /, **kwargs):
    """Print a :class:`~yuio.term.ColorizedString`.

    This is a bridge between :mod:`yuio.io` and lower-level
    modules like :mod:`yuio.term`.

    In most cases, you won't need this function. The only exception
    is when you need to build a :class:`~yuio.term.ColorizedString`
    yourself.

    """

    _manager().print_raw(msg, **kwargs)


class _AskWidget(yuio.widget.Widget[T], _t.Generic[T]):
    _layout: yuio.widget.VerticalLayout[T]

    def __init__(
        self, prompt: yuio.term.ColorizedString, widget: yuio.widget.Widget[T]
    ):
        self._prompt = yuio.widget.Text(prompt)
        self._error_msg: _t.Optional[str] = None
        self._inner = widget

    def event(
        self, e: yuio.widget.KeyboardEvent, /
    ) -> _t.Optional[yuio.widget.Result[T]]:
        try:
            result = self._inner.event(e)
        except yuio.parse.ParsingError as err:
            self._error_msg = f"Error: {err}."
        else:
            self._error_msg = None
            return result

    def layout(self, rc: RenderContext, /) -> _t.Tuple[int, int]:
        builder = (
            yuio.widget.VerticalLayoutBuilder()
            .add(self._prompt, receive_events=True)
            .add(self._inner, receive_events=True)
        )
        if self._error_msg is not None:
            rc.bell()
            error_text = yuio.term.ColorizedString(
                [
                    rc.theme.get_color("msg/decoration:error"),
                    rc.theme.msg_decorations.get("error", "▲ "),
                    rc.theme.get_color("msg/text:error"),
                    self._error_msg,
                    yuio.term.Color.NONE,
                ]
            )
            builder = builder.add(yuio.widget.Text(error_text))

        self._layout = builder.build()
        return self._layout.layout(rc)

    def draw(self, rc: RenderContext, /):
        self._layout.draw(rc)

    @functools.cached_property
    def help_columns(self) -> _t.List["yuio.widget.Help.Column"]:
        return self._inner.help_columns


class _Ask(_t.Generic[T]):
    def __init__(self, parser: yuio.parse.Parser[T]):
        self._parser: yuio.parse.Parser[T] = parser

    def __getitem__(self, ty: _t.Type[U]) -> "_Ask[U]":
        # eval type
        container = type("_container", (), {"__annotations__": {"ty": ty}})
        annotations = _t.get_type_hints(container)
        return _Ask(yuio.parse.from_type_hint(annotations["ty"]))

    @_t.overload
    def __call__(
        self,
        msg: str,
        /,
        *args,
        default: _t.Union[T, yuio.Missing] = yuio.MISSING,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> T:
        ...

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
    ) -> _t.Optional[T]:
        ...

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
    ) -> _t.Optional[U]:
        ...

    @_t.overload
    def __call__(
        self,
        msg: str,
        /,
        *args,
        parser: yuio.parse.Parser[U],
        default: _t.Union[U, yuio.Missing] = yuio.MISSING,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> U:
        ...

    def __call__(
        self,
        msg: str,
        /,
        *args,
        parser: _t.Optional[yuio.parse.Parser[_t.Any]] = None,
        default: _t.Any = yuio.MISSING,
        input_description: _t.Optional[str] = None,
        default_description: _t.Optional[str] = None,
        secure_input: bool = False,
    ) -> _t.Any:
        manager = _manager()

        term, formatter, theme = manager.term, manager.formatter, manager.theme

        if sys.stdin is None or not sys.stdin.readable():
            if default is not yuio.MISSING:
                return default
            else:
                raise UserIoError(
                    "can't interact with user in non-interactive environment"
                )

        if parser is None:
            parser = self._parser
        if default is None and not yuio.parse._is_optional_parser(parser):
            parser = yuio.parse.Optional(parser)

        msg = msg.rstrip()
        if msg.endswith(":"):
            needs_colon = True
            msg = msg[:-1]
        else:
            needs_colon = msg and not msg[-1] in string.punctuation

        prompt = formatter.colorize(msg, default_color="msg/text:question")
        if args:
            prompt = prompt % args

        if default is yuio.MISSING:
            default_description = ""
        elif not secure_input:
            if default_description is None:
                default_description = parser.describe_value(default)
            if default_description is None:
                default_description = str(default)
        elif default_description is None:
            default_description = ""

        if not secure_input and get_term().is_fully_interactive:
            # Use widget.

            if input_description:
                prompt += (
                    formatter.colorize(" (%s)", default_color="msg/text:question")
                    % input_description
                )

            widget = _AskWidget(prompt, parser.widget(default, default_description))
            with SuspendLogging() as s:
                try:
                    result = widget.run(term, theme)
                except (IOError, OSError, EOFError) as e:
                    raise UserIoError("unexpected end of input") from e

                confirmation = prompt + (
                    formatter.colorize(" `%s`\n") % parser.describe_value_or_def(result)
                )

                s.raw(confirmation)
                return result
        else:
            # Use `input()`.

            if not input_description:
                input_description = parser.describe()
            if input_description:
                prompt += (
                    formatter.colorize(" (%s)", default_color="msg/text:question")
                    % input_description
                )
            if default_description:
                prompt += (
                    formatter.colorize(" [`%s`]", default_color="msg/text:question")
                    % default_description
                )
            prompt += formatter.colorize(
                ": " if needs_colon else " ", default_color="msg/text:question"
            )
            prompt_s = "".join(prompt.process_colors(term))
            with SuspendLogging() as s:
                while True:
                    try:
                        if secure_input:
                            answer = getpass.getpass(prompt_s)
                        else:
                            answer = input(prompt_s)
                    except (IOError, OSError, EOFError) as e:
                        raise UserIoError("unexpected end of input") from None
                    if not answer and default is not yuio.MISSING:
                        return default
                    elif not answer:
                        s.error("Input is required.")
                    else:
                        try:
                            return parser.parse(answer)
                        except yuio.parse.ParsingError as e:
                            if secure_input:
                                s.error("Error: invalid value.")
                            else:
                                s.error(f"Error: %s.", e)


ask: _Ask[str] = _Ask[str](yuio.parse.Str())
"""Ask user to provide an input, parse it and return a value.

If `stdin` is not readable, return default if one is present,
or raise a :class:`UserIoError`.

.. vhs:: _tapes/questions.tape
   :alt: Demonstration of the `ask` function.
   :scale: 40%

:func:`ask` accepts generic parameters, which determine how input is parsed.
For example, if you're asking for an enum element,
Yuio will show user a choice widget.

You can also supply a custom :class:`~yuio.parse.Parser`,
which will determine the widget that is displayed to the user,
the way auto completions work, etc.

Example::

    class Level(enum.Enum):
        WARNING = "Warning",
        INFO = "Info",
        DEBUG = "Debug",

    answer = ask[Level]('Choose a logging level', default=Level.INFO)

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


def wait_for_user(
    msg: str = "Press <c note>enter</c> to continue",
    /,
    *args,
):
    """A simple function to wait for user to press enter.

    If `stdin` is not readable, does not do anything.

    """

    if sys.stdin is None or not sys.stdin.readable():
        return

    if msg and not msg[-1].isspace():
        msg += " "

    formatter = _manager().formatter
    term = get_term()

    prompt = formatter.colorize(msg, default_color="msg/text:question")
    if args:
        msg %= args
    prompt_s = "".join(prompt.process_colors(term))

    with SuspendLogging():
        try:
            input(prompt_s)
        except (IOError, OSError, EOFError):
            return


def detect_editor() -> _t.Optional[str]:
    """Detect the user's preferred editor.

    This function checks the ``EDITOR`` environment variable.
    If it's not found, it checks whether ``nano`` or ``vi``
    are available. Otherwise, it returns `None`.

    """

    if editor := os.environ.get("EDITOR"):
        return editor
    elif editor := shutil.which("nano"):
        return editor
    elif editor := shutil.which("vi"):
        return editor
    elif editor := shutil.which("notepad.exe"):
        return editor
    else:
        return None


def edit(
    text: str,
    /,
    *,
    comment_marker: _t.Optional[str] = "#",
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

    if _manager().term.is_fully_interactive:
        if editor is None:
            editor = detect_editor()

        if editor is None:
            raise UserIoError(
                "can't detect an editor, ensure that the $EDITOR "
                "environment variable contains "
                "a correct path to an editor executable"
            )

        filepath = tempfile.mktemp()
        try:
            with open(filepath, "w") as file:
                file.write(text)

            try:
                with SuspendLogging():
                    res = subprocess.run(f'{editor} "{filepath}"', shell=True)
            except FileNotFoundError:
                raise UserIoError(
                    "can't use this editor, ensure that the $EDITOR "
                    "environment variable contains "
                    "a correct path to an editor executable"
                )

            if res.returncode != 0:
                raise UserIoError("editing failed")

            with open(filepath, "r") as file:
                text = file.read()
        finally:
            os.remove(filepath)

    if comment_marker is not None:
        text = re.sub(
            r"^\s*" + re.escape(comment_marker) + r".*$", "", text, flags=re.MULTILINE
        )

    return text.strip()


class SuspendLogging:
    """A context manager for pausing log output.

    This is handy for when you need to take control over the output stream.
    For example, the :func:`ask` function uses this class internally.

    This context manager also suspends all prints that go to :data:`sys.stdout`
    and :data:`sys.stderr` if they were wrapped (see :func:`setup`).
    To print through them, use :data:`sys.__stdout__` and :data:`sys.__stderr__`.

    """

    def __init__(self):
        self._resumed = False
        _manager().suspend()

    def resume(self):
        """Manually resume the logging process."""

        if not self._resumed:
            _manager().resume()
            self._resumed = True

    @staticmethod
    def info(msg: str, /, *args, **kwargs):
        """Log an :func:`info` message, ignore suspended status."""

        kwargs.setdefault("ignore_suspended", True)
        info(msg, *args, **kwargs)

    @staticmethod
    def warning(msg: str, /, *args, **kwargs):
        """Log a :func:`warning` message, ignore suspended status."""

        kwargs.setdefault("ignore_suspended", True)
        warning(msg, *args, **kwargs)

    @staticmethod
    def success(msg: str, /, *args, **kwargs):
        """Log a :func:`success` message, ignore suspended status."""

        kwargs.setdefault("ignore_suspended", True)
        success(msg, *args, **kwargs)

    @staticmethod
    def error(msg: str, /, *args, **kwargs):
        """Log an :func:`error` message, ignore suspended status."""

        kwargs.setdefault("ignore_suspended", True)
        error(msg, *args, **kwargs)

    @staticmethod
    def error_with_tb(msg: str, /, *args, **kwargs):
        """Log an :func:`error_with_tb` message, ignore suspended status."""

        kwargs.setdefault("ignore_suspended", True)
        error_with_tb(msg, *args, **kwargs)

    @staticmethod
    def heading(msg: str, /, *args, **kwargs):
        """Log a :func:`heading` message, ignore suspended status."""

        kwargs.setdefault("ignore_suspended", True)
        heading(msg, *args, **kwargs)

    @staticmethod
    def md(msg: str, /, *args, **kwargs):
        """Log a markdown-formatted text."""

        kwargs.setdefault("ignore_suspended", True)
        md(msg, *args, **kwargs)

    @staticmethod
    def br(**kwargs):
        """Log an empty string."""

        kwargs.setdefault("ignore_suspended", True)
        br(**kwargs)

    @staticmethod
    def raw(msg: yuio.term.ColorizedString, **kwargs):
        """Log a :class:`~yuio.term.ColorizedString`."""

        kwargs.setdefault("ignore_suspended", True)
        raw(msg, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.resume()


class _IterTask(_t.Generic[T]):
    def __init__(self, collection: _t.Collection[T], task: "Task"):
        self._iter = iter(collection)
        self._task = task

        self._i = 0
        self._len = len(collection)

    def __next__(self) -> T:
        self._task.progress(self._i, self._len)
        if self._i < self._len:
            self._i += 1
        return self._iter.__next__()

    def __iter__(self) -> "_IterTask[T]":
        return self


class Task:
    """A class for indicating progress of some task.

    You can have multiple tasks at the same time,
    create subtasks, set task's progress or add a comment about
    what's currently being done within a task.

    .. vhs:: _tapes/tasks_multithreaded.tape
       :alt: Demonstration of the `Task` class.
       :scale: 40%

    This class can be used as a context manager::

        with Task('Processing input') as t:
            ...
            t.progress(0.3)
            ...

    """

    class _Status(enum.Enum):
        RUNNING = "running"
        DONE = "done"
        ERROR = "error"

    def __init__(self, msg: str, /, *args, _parent: "_t.Optional[Task]" = None):
        # Task properties should not be written to directly.
        # Instead, task should be sent to a handler for modification.
        # This ensures thread safety, because handler has a lock.
        # See handler's implementation details.

        self._msg: str = msg
        self._args: _t.Tuple[object, ...] = args
        self._comment: _t.Optional[str] = None
        self._comment_args: _t.Optional[_t.Tuple[object, ...]] = None
        self._status: Task._Status = Task._Status.RUNNING
        self._progress: _t.Optional[float] = None
        self._progress_done: _t.Optional[str] = None
        self._progress_total: _t.Optional[str] = None
        self._subtasks: _t.List[Task] = []

        self._cached_msg: _t.Optional[yuio.term.ColorizedString] = None
        self._cached_comment: _t.Optional[yuio.term.ColorizedString] = None

        if _parent is None:
            _manager().start_task(self)
        else:
            _manager().start_subtask(_parent, self)

    @_t.overload
    def progress(self, progress: _t.Optional[float], /, *, ndigits: int = 2):
        ...

    @_t.overload
    def progress(
        self,
        done: float,
        total: _t.Optional[float],
        /,
        *,
        unit: str = "",
        ndigits: int = 0,
    ):
        ...

    def progress(
        self,
        *args: _t.Optional[float],
        unit: str = "",
        ndigits: _t.Optional[int] = None,
    ):
        """Indicate progress of this task.

        If given one argument, it is treated as percentage between `0` and `1`.

        If given two arguments, they are treated as amount of finished work,
        and a total amount of work. In this case, optional argument `unit`
        can be used to indicate units, in which amount is calculated::

            with Task("Loading cargo") as task:
                task.progress(110, 150, unit="Kg")

        This will print the following:

        .. code-block:: text

           ■■■■■■■■■■■□□□□ Loading cargo - 110/150Kg

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
            _manager().set_task_progress(self, None, None, None)
            return

        if len(args) == 1:
            done *= 100
            unit = "%"

        done_str = "%.*f" % (ndigits, done)
        if total is None:
            _manager().set_task_progress(self, progress, done_str + unit, None)
        else:
            total_str = "%.*f" % (ndigits, total)
            progress = done / total
            _manager().set_task_progress(self, progress, done_str, total_str + unit)

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

            with Task("Downloading a file") as task:
                task.progress_size(31.05 * 2**20, 150 * 2**20)

        This will print:

        .. code-block:: text

           ■■■□□□□□□□□□□□□ Downloading a file - 31.05/150.00M

        """

        progress = done / total
        done, done_unit = self._size(done)
        total, total_unit = self._size(total)

        if done_unit == total_unit:
            done_unit = ""

        _manager().set_task_progress(
            self,
            progress,
            "%.*f%s" % (ndigits, done, done_unit),
            "%.*f%s" % (ndigits, total, total_unit),
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
            ...     task.progress_scale(889.25E-3, 1, unit="V")


        This will print:

        .. code-block:: text

           ■■■■■■■■■■■■■□□ Charging a capacitor - 889.25mV/1.00V

        """

        progress = done / total
        done, done_unit = self._unit(done)
        total, total_unit = self._unit(total)

        if unit:
            done_unit += unit
            total_unit += unit

        _manager().set_task_progress(
            self,
            progress,
            "%.*f%s" % (ndigits, done, done_unit),
            "%.*f%s" % (ndigits, total, total_unit),
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

           ■■■■■□□□□□□□□□□ Fetching data - 1/3

        """

        return _IterTask(collection, self)

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

           ⣿ Fetching data - https://google.com

        """

        _manager().set_task_comment(self, comment, args)

    def done(self):
        """Indicate that this task has finished successfully."""

        _manager().finish_task(self, Task._Status.DONE)

    def error(self):
        """Indicate that this task has finished with an error."""

        _manager().finish_task(self, Task._Status.ERROR)

    def subtask(self, msg: str, /, *args) -> "Task":
        """Create a subtask within this task."""

        return Task(msg, *args, _parent=self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done()
        else:
            self.error()


class Handler(logging.Handler):
    """A handler that redirects all log messages to yuio."""

    def createLock(self) -> None:
        self.lock = None

    def emit(self, record: LogRecord) -> None:
        _manager().print_rec(record)


class _IoManager(abc.ABC):
    term: Term
    theme: Theme

    def __init__(
        self,
        term: _t.Optional[Term] = None,
        theme: _t.Union[Theme, _t.Callable[[Term], Theme], None] = None,
    ):
        self.term = term or yuio.term.get_term_from_stream(sys.stderr)
        if theme is None:
            self.theme = yuio.theme.load(self.term)
        elif isinstance(theme, Theme):
            self.theme = theme
        else:
            self.theme = theme(self.term)
        self.formatter = yuio.md.MdFormatter(self.theme)
        self._rc = yuio.widget.RenderContext(self.term, self.theme)

        self._indent = 0
        self._needs_padding: bool = False

        self._suspended: int = 0
        self._suspended_lines: _t.List[_t.Tuple[_t.List[str], _t.TextIO]] = []

        self._tasks: _t.List[Task] = []
        self._tasks_printed = 0
        self._spinner_state = 0
        self._needs_update = False
        self._last_update_time_us = 0
        self._printed_some_lines = False

        self._renders = 0

        threading.Thread(
            target=self._bg_update, name="yuio_io_thread", daemon=True
        ).start()

        atexit.register(self._atexit)

    def setup(
        self,
        term: _t.Optional[Term] = None,
        theme: _t.Union[Theme, _t.Callable[[Term], Theme], None] = None,
    ):
        self._clear_tasks()

        if term is not None:
            self.term = term
        if theme is not None:
            if not isinstance(theme, Theme):
                theme = theme(self.term)
            self.theme = self.formatter.theme = theme

        self._rc = yuio.widget.RenderContext(self.term, self.theme)
        self.__dict__.pop("update_rate_us", None)
        self._update_tasks()

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

                    with _IO_LOCK:
                        self._show_tasks()
                        update_rate_us = self.update_rate_us
            except Exception:
                yuio._logger.critical("exception in bg updater", exc_info=True)

    def _atexit(self):
        with _IO_LOCK:
            self._show_tasks(immediate_render=True)

    def print_msg(
        self,
        msg: str,
        args: _t.Optional[_t.Tuple[object, ...]],
        tag: str,
        /,
        *,
        exc_info: _t.Union[_ExcInfo, bool, None] = None,
        ignore_suspended: bool = False,
        heading: bool = False,
    ):
        with _IO_LOCK:
            col_msg = self._format_msg(
                msg, args, tag, exc_info=exc_info, heading=heading
            )
            self._emit_lines(col_msg.process_colors(self.term), None, ignore_suspended)

    def print_md(
        self,
        msg: str,
        args: _t.Optional[_t.Tuple[object, ...]],
        /,
        *,
        ignore_suspended: bool = False,
    ):
        with _IO_LOCK:
            col_md = self._format_md(msg, args)
            self._emit_lines(col_md.process_colors(self.term), None, ignore_suspended)

    def print_rec(
        self,
        record: logging.LogRecord,
    ):
        with _IO_LOCK:
            col_rec = self._format_rec(record)
            self._emit_lines(col_rec.process_colors(self.term))

    def print_raw(
        self,
        msg: yuio.term.ColorizedString,
        /,
        *,
        ignore_suspended: bool = False,
    ):
        with _IO_LOCK:
            self._emit_lines(msg.process_colors(self.term), None, ignore_suspended)

    def print_direct(
        self,
        msg: str,
        stream: _t.Optional[_t.TextIO] = None,
        /,
        *,
        ignore_suspended: bool = False,
    ):
        with _IO_LOCK:
            self._emit_lines([msg], stream, ignore_suspended)

    def print_direct_lines(
        self,
        lines: _t.Iterable[str],
        stream: _t.Optional[_t.TextIO] = None,
        /,
        *,
        ignore_suspended: bool = False,
    ):
        with _IO_LOCK:
            self._emit_lines(lines, stream, ignore_suspended)

    def start_task(self, task: Task):
        with _IO_LOCK:
            self._start_task(task)

    def start_subtask(self, parent: Task, task: Task):
        with _IO_LOCK:
            self._start_subtask(parent, task)

    def finish_task(self, task: Task, status: Task._Status):
        with _IO_LOCK:
            self._finish_task(task, status)

    def set_task_progress(
        self,
        task: Task,
        progress: _t.Optional[float],
        done: _t.Optional[str],
        total: _t.Optional[str],
    ):
        with _IO_LOCK:
            task._progress = progress
            task._progress_done = done
            task._progress_total = total
            self._update_tasks()

    def set_task_comment(self, task: Task, comment: _t.Optional[str], args):
        with _IO_LOCK:
            task._comment = comment
            task._comment_args = args
            task._cached_comment = None
            self._update_tasks()

    def suspend(self):
        with _IO_LOCK:
            self._suspend()

    def resume(self):
        with _IO_LOCK:
            self._resume()

    # Implementation.
    # These functions are always called under a lock.

    def _emit_lines(
        self,
        lines: _t.Iterable[str],
        stream: _t.Optional[_t.TextIO] = None,
        ignore_suspended: bool = False,
    ):
        stream = stream or self.term.stream
        if self._suspended and not ignore_suspended:
            self._suspended_lines.append((list(lines), stream))
        else:
            self._clear_tasks()
            stream.writelines(lines)
            self._update_tasks(immediate_render=True)
            stream.flush()

        self._printed_some_lines = True

    def _suspend(self):
        self._suspended += 1

        if self._suspended == 1:
            self._clear_tasks()

    def _resume(self):
        self._suspended -= 1

        if self._suspended == 0:
            for lines, stream in self._suspended_lines:
                stream.writelines(lines)
            self._suspended_lines.clear()

            self._update_tasks()

        if self._suspended < 0:
            yuio._logger.debug("unequal number of suspends and resumes")
            self._suspended = 0

    def _start_task(self, task: Task):
        if self.term.can_move_cursor:
            self._tasks.append(task)
            self._update_tasks()
        else:
            self._emit_lines(self._format_task(task).process_colors(self.term))

    def _start_subtask(self, parent: Task, task: Task):
        if self.term.can_move_cursor:
            parent._subtasks.append(task)
            self._update_tasks()
        else:
            self._emit_lines(self._format_task(task).process_colors(self.term))

    def _finish_task(self, task: Task, status: Task._Status):
        if task._status != Task._Status.RUNNING:
            yuio._logger.debug("trying to change status of an already stopped task")
            return

        task._status = status

        if self.term.can_move_cursor:
            if task in self._tasks:
                self._tasks.remove(task)
                self._emit_lines(self._format_task(task).process_colors(self.term))
            else:
                self._update_tasks()
        else:
            self._emit_lines(self._format_task(task).process_colors(self.term))

    def _clear_tasks(self):
        if self.term.can_move_cursor and self._tasks_printed:
            self._rc.finalize()
            self._tasks_printed = 0

    def _update_tasks(self, immediate_render: bool = False):
        self._needs_update = True
        if immediate_render:
            self._show_tasks(immediate_render)

    def _show_tasks(self, immediate_render: bool = False):
        if self.term.can_move_cursor and (self._tasks or self._tasks_printed):
            now_us = time.monotonic_ns() // 1000
            now_us -= now_us % self.update_rate_us

            if not immediate_render:
                next_update_us = self._last_update_time_us + self.update_rate_us
                if now_us < next_update_us:
                    # Hard-limit update rate by `update_rate_ms`.
                    return
                next_spinner_update_us = (
                    self._last_update_time_us + self.spinner_update_rate_us
                )
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

    def _format_msg(
        self,
        msg: str,
        args: _t.Optional[_t.Tuple[object, ...]],
        tag: str,
        /,
        *,
        exc_info: _t.Union[_ExcInfo, bool, None] = None,
        heading: bool = False,
    ) -> yuio.term.ColorizedString:
        decoration = self.theme.msg_decorations.get(tag, "")
        if decoration:
            first_line_indent = yuio.term.ColorizedString(
                [self.theme.get_color(f"msg/decoration:{tag}"), decoration]
            )
            continuation_indent = " " * first_line_indent.width
        else:
            first_line_indent = ""
            continuation_indent = ""

        res = yuio.term.ColorizedString()

        if heading and self._printed_some_lines:
            res += "\n\n"

        col_msg = self.formatter.colorize(msg, default_color=f"msg/text:{tag}")
        if args:
            col_msg %= args
        for line in col_msg.wrap(
            self.formatter.width,
            first_line_indent=first_line_indent,
            continuation_indent=continuation_indent,
            break_on_hyphens=False,
            preserve_spaces=True,
        ):
            res += line
            res += "\n"

        if exc_info is True:
            exc_info = sys.exc_info()
        elif exc_info is False or exc_info is None:
            exc_info = None
        elif isinstance(exc_info, BaseException):
            exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
        elif not isinstance(exc_info, tuple) or len(exc_info) != 3:
            raise ValueError(f"invalid exc_info {exc_info!r}")
        if exc_info is not None:
            tb = "".join(traceback.format_exception(*exc_info))
            res += self._format_tb(tb, "  ")

        if heading:
            res += "\n"

        res += Color.NONE

        return res

    def _format_md(self, md: str, args) -> yuio.term.ColorizedString:
        res = self.formatter.format(md)
        if args:
            res %= args
        return res

    def _format_rec(self, record: logging.LogRecord) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        asctime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))

        logger = record.name
        level = record.levelname
        if level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            level = level[:4]
        message = record.getMessage()

        ctx = record.levelname.lower()

        res += self.theme.get_color(f"log/asctime:{ctx}")
        res += asctime
        res += " "

        res += self.theme.get_color(f"log/logger:{ctx}")
        res += logger
        res += " "

        res += self.theme.get_color(f"log/level:{ctx}")
        res += level
        res += " "

        res += self.theme.get_color(f"log/message:{ctx}")
        res += message
        res += "\n"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = "".join(traceback.format_exception(*record.exc_info))
            res += self._format_tb(record.exc_text, "  ")
        if record.stack_info:
            res += self._format_tb(record.stack_info, "  ")

        res += Color.NONE

        return res

    def _format_tb(self, tb: str, indent: str) -> yuio.term.ColorizedString:
        highlighter = yuio.md.SyntaxHighlighter.get_highlighter("python-traceback")
        return highlighter.highlight(self.theme, tb).indent(indent, indent)

    def _format_task(self, task: Task) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        ctx = task._status.value

        if decoration := self.theme.msg_decorations.get("task"):
            res += self.theme.get_color(f"task/decoration:{ctx}")
            res += decoration

        res += self._format_task_msg(task)
        res += self.theme.get_color(f"task:{ctx}")
        res += " - "
        res += self.theme.get_color(f"task/progress:{ctx}")
        res += task._status.value
        res += self.theme.get_color(f"task:{ctx}")
        res += "\n"

        res += Color.NONE

        return res

    def _format_task_msg(self, task: Task) -> yuio.term.ColorizedString:
        if task._cached_msg is None:
            msg = self.formatter.colorize(
                task._msg, default_color=f"task/heading:{task._status.value}"
            )
            if task._args:
                msg %= task._args
            task._cached_msg = msg
        return task._cached_msg

    def _format_task_comment(
        self, task: Task
    ) -> _t.Optional[yuio.term.ColorizedString]:
        if task._cached_comment is None and task._comment is not None:
            comment = self.formatter.colorize(
                task._comment, default_color=f"task/comment:{task._status.value}"
            )
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
            self._rc.set_color_path(f"task:{task._status.value}")
            self._rc.write(" - ")
            self._rc.write(comment)
        self._rc.new_line()

        for subtask in task._subtasks:
            self._draw_task(subtask, indent + 1)

    def _draw_task_progress(self, task: Task):
        if task._progress_done is None:
            return None

        self._rc.set_color_path(f"task:{task._status.value}")
        self._rc.write(" - ")

        if task._status in (Task._Status.DONE, Task._Status.ERROR):
            self._rc.set_color_path(f"task/progress:{task._status.value}")
            self._rc.write(task._status.name.lower())
        else:
            self._rc.set_color_path(f"task/progress:{task._status.value}")
            self._rc.write(task._progress_done)
            if task._progress_total is not None:
                self._rc.set_color_path(f"task:{task._status.value}")
                self._rc.write("/")
                self._rc.set_color_path(f"task/progress:{task._status.value}")
                self._rc.write(task._progress_total)

    def _draw_task_progressbar(self, task: Task):
        if task._status != Task._Status.RUNNING:
            self._rc.set_color_path(f"task/decoration:{task._status.value}")
            self._rc.write(self.theme.spinner_static_symbol)
        elif task._progress is None:
            self._rc.set_color_path(f"task/decoration:{task._status.value}")
            if self.theme.spinner_pattern:
                self._rc.write(
                    self.theme.spinner_pattern[
                        self._spinner_state % len(self.theme.spinner_pattern)
                    ]
                )
        else:
            total_width = self.theme.progress_bar_width
            done_width = round(max(0, min(1, task._progress)) * total_width)

            self._rc.set_color_path(f"task/progressbar:{task._status.value}")
            self._rc.write(self.theme.progress_bar_start_symbol)

            done_color = Color.lerp(
                self.theme.get_color("task/progressbar/done/start"),
                self.theme.get_color("task/progressbar/done/end"),
            )

            for i in range(0, done_width):
                self._rc.set_color(done_color((i + i / total_width) / total_width))
                self._rc.write(self.theme.progress_bar_done_symbol)

            pending_color = Color.lerp(
                self.theme.get_color("task/progressbar/pending/start"),
                self.theme.get_color("task/progressbar/pending/end"),
            )

            for i in range(done_width, total_width):
                self._rc.set_color(pending_color((i + i / total_width) / total_width))
                self._rc.write(self.theme.progress_bar_pending_symbol)

            self._rc.set_color_path(f"task/progressbar:{task._status.value}")
            self._rc.write(self.theme.progress_bar_end_symbol)

        self._rc.set_color_path(f"task:{task._status.value}")
        self._rc.write(" ")


class _WrappedOutput(_t.TextIO):
    def __init__(self, wrapped: _t.TextIO):
        self.__wrapped = wrapped

    @property
    def mode(self) -> str:
        return self.__wrapped.mode

    @property
    def name(self) -> str:
        return self.__wrapped.name

    def close(self):
        self.__wrapped.close()

    @property
    def closed(self) -> bool:
        return self.__wrapped.closed

    def fileno(self) -> int:
        return self.__wrapped.fileno()

    def flush(self):
        self.__wrapped.flush()

    def isatty(self) -> bool:
        return self.__wrapped.isatty()

    def writable(self) -> bool:
        return self.__wrapped.writable()

    def write(self, s: str, /) -> int:
        _manager().print_direct(s, self.__wrapped)
        return len(s)

    def writelines(self, lines: _t.Iterable[str], /):
        _manager().print_direct_lines(lines, self.__wrapped)

    def __enter__(self) -> _t.TextIO:
        return self.__wrapped.__enter__()

    def __exit__(self, type, value, traceback):
        self.__wrapped.__exit__(type, value, traceback)

    @property
    def buffer(self) -> _t.BinaryIO:
        return self.__wrapped.buffer

    @property
    def encoding(self) -> str:
        return self.__wrapped.encoding

    @property
    def errors(self) -> _t.Optional[str]:
        return self.__wrapped.errors

    @property
    def line_buffering(self) -> int:
        return self.__wrapped.line_buffering

    @property
    def newlines(self) -> _t.Any:
        return self.__wrapped.newlines
