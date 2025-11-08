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

To print messages for the user, there are functions with an interface similar
to the one from :mod:`logging`:

.. autofunction:: info

.. autofunction:: warning

.. autofunction:: success

.. autofunction:: failure

.. autofunction:: failure_with_tb

.. autofunction:: error

.. autofunction:: error_with_tb

.. autofunction:: heading

.. autofunction:: md

.. autofunction:: hl

.. autofunction:: br

.. autofunction:: raw

.. autofunction:: out


.. _color-tags:

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

- ``code``, ``note``, ``path``: highlights,
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

.. autoclass:: Task(msg: str, /, *args, comment: str | None = None)

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
using the :class:`SuspendOutput` context manager.

.. autoclass:: SuspendOutput

    .. automethod:: resume

    .. automethod:: info

    .. automethod:: warning

    .. automethod:: success

    .. automethod:: failure

    .. automethod:: failure_with_tb

    .. automethod:: error

    .. automethod:: error_with_tb

    .. automethod:: heading

    .. automethod:: md

    .. automethod:: hl

    .. automethod:: br

    .. automethod:: raw

    .. automethod:: out


Python's `logging` and yuio
---------------------------

If you want to direct messages from the :mod:`logging` to Yuio,
you can add a :class:`Handler`:

.. autoclass:: Handler

"""

from __future__ import annotations

import abc
import atexit
import enum
import functools
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

import yuio.md
import yuio.parse
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _typing as _t

__all__ = [
    "UserIoError",
    "setup",
    "get_term",
    "get_theme",
    "wrap_streams",
    "restore_streams",
    "streams_wrapped",
    "orig_stderr",
    "orig_stdout",
    "info",
    "warning",
    "success",
    "error",
    "error_with_tb",
    "failure",
    "failure_with_tb",
    "heading",
    "md",
    "hl",
    "br",
    "raw",
    "out",
    "ask",
    "wait_for_user",
    "detect_editor",
    "edit",
    "SuspendOutput",
    "Task",
    "Handler",
]

T = _t.TypeVar("T")
M = _t.TypeVar("M", default=_t.Never)
S = _t.TypeVar("S", default=str)

_ExcInfo: _t.TypeAlias = tuple[
    type[BaseException] | None,
    BaseException | None,
    types.TracebackType | None,
]


_IO_LOCK = threading.Lock()
_IO_MANAGER: _IoManager | None = None
_STREAMS_WRAPPED: bool = False
_ORIG_STDERR: _t.TextIO | None = None
_ORIG_STDOUT: _t.TextIO | None = None


def _manager() -> _IoManager:
    global _IO_MANAGER

    if _IO_MANAGER is None:
        with _IO_LOCK:
            if _IO_MANAGER is None:
                _IO_MANAGER = _IoManager()
    return _IO_MANAGER


def _manager_data() -> tuple[yuio.term.Term, yuio.theme.Theme, int]:
    global _IO_MANAGER

    with _IO_LOCK:
        if _IO_MANAGER is None:
            _IO_MANAGER = _IoManager()
        return _IO_MANAGER._term, _IO_MANAGER._theme, _IO_MANAGER._rc.canvas_width


class UserIoError(IOError):
    """
    Raised when interaction with user fails.

    """


def setup(
    *,
    term: yuio.term.Term | None = None,
    theme: (
        yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
    ) = None,
    wrap_stdio: bool = True,
):
    """
    Initial setup of the logging facilities.

    :param term:
        terminal that will be used for output.

        If not passed, the global terminal is not re-configured;
        the default is to use a term attached to :data:`sys.stderr`.
    :param theme:
        either a theme that will be used for output, or a theme constructor that takes
        a :class:`~yuio.term.Term` and returns a theme.

        If not passed, the global theme is not re-configured; the default is to use
        :class:`yuio.theme.DefaultTheme` then.
    :param wrap_stdio:
        if set to :data:`True`, wraps :data:`sys.stdout` and :data:`sys.stderr`
        in a special wrapper that ensures better interaction
        with Yuio's progress bars and widgets.

        .. note::

           If you're working with some other library that wraps :data:`sys.stdout`
           and :data:`sys.stderr`, such as colorama_, initialize it before Yuio.

    .. _colorama: https://github.com/tartley/colorama

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


def get_term() -> yuio.term.Term:
    """
    Get the global instance of :class:`~yuio.term.Term` that is used
    with :mod:`yuio.io`.

    If global setup wasn't performed, this function implicitly performs it.

    :returns:
        Instance of :class:`~yuio.term.Term` that's used to print messages and tasks.

    """

    return _manager_data()[0]


def get_theme() -> yuio.theme.Theme:
    """
    Get the global instance of :class:`~yuio.theme.Theme`
    that is used with :mod:`yuio.io`.

    If global setup wasn't performed, this function implicitly performs it.

    :returns:
        Instance of :class:`~yuio.theme.Theme` that's used to format messages and tasks.

    """

    return _manager_data()[1]


def wrap_streams():
    """
    Wrap :data:`sys.stdout` and :data:`sys.stderr` so that they honor
    Yuio tasks and widgets.

    .. note::

        If you're working with some other library that wraps :data:`sys.stdout`
        and :data:`sys.stderr`, such as colorama_, initialize it before Yuio.

    See :func:`setup`.

    .. _colorama: https://github.com/tartley/colorama

    """

    global _STREAMS_WRAPPED, _ORIG_STDOUT, _ORIG_STDERR

    with _IO_LOCK:
        if _STREAMS_WRAPPED:
            return

        if yuio.term._is_interactive_output(sys.stdout):
            _ORIG_STDOUT, sys.stdout = sys.stdout, _WrappedOutput(sys.stdout)
        if yuio.term._is_interactive_output(sys.stderr):
            _ORIG_STDERR, sys.stderr = sys.stderr, _WrappedOutput(sys.stderr)
        _STREAMS_WRAPPED = True

        atexit.register(restore_streams)


def restore_streams():
    """
    Restore wrapped streams. If streams weren't wrapped, does nothing.

    See :func:`wrap_streams` and :func:`setup`.

    """

    global _STREAMS_WRAPPED

    with _IO_LOCK:
        if not _STREAMS_WRAPPED:
            return

        if _ORIG_STDOUT is not None:
            sys.stdout = _ORIG_STDOUT
        if _ORIG_STDERR is not None:
            sys.stderr = _ORIG_STDERR
        _STREAMS_WRAPPED = False


def streams_wrapped() -> bool:
    """
    Check if :data:`sys.stdout` and :data:`sys.stderr` are wrapped.
    See :func:`setup`.

    :returns:
        :data:`True` is streams are currently wrapped, :data:`False` otherwise.

    """

    with _IO_LOCK:
        return _STREAMS_WRAPPED


def orig_stderr() -> _t.TextIO:
    """
    Return the original :data:`sys.stderr` before wrapping.

    """

    return _ORIG_STDERR or sys.stderr


def orig_stdout() -> _t.TextIO:
    """
    Return the original :data:`sys.stdout` before wrapping.

    """

    return _ORIG_STDOUT or sys.stdout


@_t.overload
def info(msg: str, /, *args, **kwargs): ...
@_t.overload
def info(err: Exception, /, **kwargs): ...
def info(msg: str | Exception, /, *args, **kwargs):
    """info(msg: str, /, *args)
    info(err: Exception, /)

    Print an info message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param err:
        you can pass an error object to this function,
        in which case it will print an error message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "info")
    _manager().print_msg(msg, args, **kwargs)


@_t.overload
def warning(msg: str, /, *args, **kwargs): ...
@_t.overload
def warning(err: Exception, /, **kwargs): ...
def warning(msg: str | Exception, /, *args, **kwargs):
    """warning(msg: str, /, *args)
    warning(err: Exception, /)

    Print a warning message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param err:
        you can pass an error object to this function,
        in which case it will print an error message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "warning")
    _manager().print_msg(msg, args, **kwargs)


@_t.overload
def success(msg: str, /, *args, **kwargs): ...
@_t.overload
def success(err: Exception, /, **kwargs): ...
def success(msg: str | Exception, /, *args, **kwargs):
    """success(msg: str, /, *args)
    success(err: Exception, /)

    Print a success message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param err:
        you can pass an error object to this function,
        in which case it will print an error message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "success")
    _manager().print_msg(msg, args, **kwargs)


@_t.overload
def error(msg: str, /, *args, **kwargs): ...
@_t.overload
def error(err: Exception, /, **kwargs): ...
def error(msg: str | Exception, /, *args, **kwargs):
    """error(msg: str, /, *args)
    error(err: Exception, /)

    Print an error message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param err:
        you can pass an error object to this function,
        in which case it will print an error message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "error")
    _manager().print_msg(msg, args, **kwargs)


def error_with_tb(
    msg: str, /, *args, exc_info: _ExcInfo | bool | None = True, **kwargs
):
    """error_with_tb(msg: str, /, *args, exc_info: tuple[type[BaseException] | None, BaseException | None, ~types.TracebackType | None] | bool | None = True)

    Print an error message and capture the current exception.

    Call this function in the ``except`` clause of a ``try`` block
    or in an ``__exit__`` function of a context manager to attach
    current exception details to the log message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param exc_info:
        either a boolean indicating that the current exception
        should be captured (default is :data:`True`), or a tuple
        of three elements, as returned by :func:`sys.exc_info`.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "error")
    _manager().print_msg(msg, args, exc_info=exc_info, **kwargs)


@_t.overload
def failure(msg: str, /, *args, **kwargs): ...
@_t.overload
def failure(err: Exception, /, **kwargs): ...
def failure(msg: str | Exception, /, *args, **kwargs):
    """failure(msg: str, /, *args)
    failure(err: Exception, /)

    Print a failure message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param err:
        you can pass an error object to this function,
        in which case it will print an error message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "failure")
    _manager().print_msg(msg, args, **kwargs)


def failure_with_tb(
    msg: str, /, *args, exc_info: _ExcInfo | bool | None = True, **kwargs
):
    """failure_with_tb(msg: str, /, *args, exc_info: tuple[type[BaseException] | None, BaseException | None, ~types.TracebackType | None] | bool | None = True)

    Print a failure message and capture the current exception.

    Call this function in the ``except`` clause of a ``try`` block
    or in an ``__exit__`` function of a context manager to attach
    current exception details to the log message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param exc_info:
        either a boolean indicating that the current exception
        should be captured (default is :data:`True`), or a tuple
        of three elements, as returned by :func:`sys.exc_info`.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("tag", "failure")
    _manager().print_msg(msg, args, exc_info=exc_info, **kwargs)


def heading(msg: str, /, *args, **kwargs):
    """heading(msg: str, /, *args)

    Print a heading message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("heading", True)
    kwargs.setdefault("tag", "heading/1")
    _manager().print_msg(msg, args, **kwargs)


def md(msg: str, /, *args, **kwargs):
    """md(msg: str, /, *args)

    Print a markdown-formatted text.

    Yuio supports all CommonMark block markup except tables. Inline markup is limited
    to backticks and color tags. See :mod:`yuio.md` for more info.

    :param msg:
        message to print. The leading indentation from the message will be removed,
        so this function can be used with triple quote literals.
    :param args:
        arguments for ``%``\\ -formatting the message.

    """

    msg, args = yuio._to_msg(msg, args)
    _term, theme, width = _manager_data()
    formatter = yuio.md.MdFormatter(theme, width=width)
    res = yuio.term.ColorizedString()
    for line in formatter.format(msg):
        res += line
        res += "\n"
    if args:
        res %= args

    raw(res, **kwargs)


def br(**kwargs):
    """br()

    Print an empty string.

    """

    _manager().print_direct("\n", **kwargs)


def hl(msg: str, /, *args, syntax: str | yuio.md.SyntaxHighlighter, **kwargs):
    """hl(msg: str, /, *args, syntax: str | yuio.md.SyntaxHighlighter)

    Print highlighted code. See :mod:`yuio.md` for more info.

    :param msg:
        code to highlight. The leading indentation from the code will be removed,
        so this function can be used with triple quote literals.
    :param args:
        arguments for ``%``\\ -formatting the code.
    :param syntax:
        syntax name or :class:`~yuio.md.SyntaxHighlighter` class.

    """

    msg, args = yuio._to_msg(msg, args)
    if isinstance(syntax, str):
        syntax = yuio.md.SyntaxHighlighter.get_highlighter(syntax)
    highlighted = syntax.highlight(get_theme(), yuio.dedent(msg))
    if args:
        highlighted %= args
    raw(highlighted, **kwargs)


def raw(msg: yuio.term.ColorizedString, /, **kwargs):
    """raw(msg: yuio.term.ColorizedString, /)

    Print a :class:`~yuio.term.ColorizedString`.

    This is a bridge between :mod:`yuio.io` and lower-level
    modules like :mod:`yuio.term`.

    In most cases, you won't need this function. The only exception
    is when you need to build a :class:`~yuio.term.ColorizedString`
    yourself.

    :param msg:
        message to print.

    """

    _manager().print_raw(msg, **kwargs)


@_t.overload
def out(msg: str, /, *args, **kwargs): ...
@_t.overload
def out(err: Exception, /, **kwargs): ...
def out(msg: str | Exception, /, *args, **kwargs):
    """out(msg: str, /, *args)
    out(err: Exception, /)

    Like :func:`info`, but sends output to ``stdout`` instead of ``stderr``.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param err:
        you can pass an error object to this function,
        in which case it will print an error message.

    """

    msg, args = yuio._to_msg(msg, args)
    kwargs.setdefault("to_stdout", True)
    info(msg, *args, **kwargs)


class _AskWidget(yuio.widget.Widget[T], _t.Generic[T]):
    _layout: yuio.widget.VerticalLayout[T]

    def __init__(
        self, prompt: yuio.term.ColorizedString, widget: yuio.widget.Widget[T]
    ):
        self._prompt = yuio.widget.Text(prompt)
        self._error_msg: str | None = None
        self._error_msg_args: tuple[_t.Any] | None = None
        self._inner = widget

    def event(self, e: yuio.widget.KeyboardEvent, /) -> yuio.widget.Result[T] | None:
        try:
            result = self._inner.event(e)
        except yuio.parse.ParsingError as err:
            self._error_msg = err.msg
            self._error_msg_args = err.args
        else:
            self._error_msg = None
            self._error_msg_args = None
            return result

    def layout(self, rc: yuio.widget.RenderContext, /) -> tuple[int, int]:
        builder = (
            yuio.widget.VerticalLayoutBuilder()
            .add(self._prompt)
            .add(self._inner, receive_events=True)
        )
        if self._error_msg is not None:
            rc.bell()
            error_msg = yuio.md.colorize(
                rc.theme,
                self._error_msg.replace("\n", "\n  "),
                default_color="msg/text:error",
            )
            if self._error_msg_args:
                error_msg %= self._error_msg_args
            error_text = (
                yuio.term.ColorizedString(
                    [
                        rc.theme.get_color("msg/decoration:error"),
                        rc.theme.msg_decorations.get("error", "▲ "),
                    ]
                )
                + error_msg
            )
            builder = builder.add(yuio.widget.Text(error_text))

        self._layout = builder.build()
        return self._layout.layout(rc)

    def draw(self, rc: yuio.widget.RenderContext, /):
        self._layout.draw(rc)

    @property
    def help_data(self) -> yuio.widget.WidgetHelp:
        return self._inner.help_data


class _AskMeta(type):
    __hint = None

    @_t.overload
    def __call__(  # pyright: ignore[reportInconsistentOverload]
        cls: type[ask[S]],
        msg: str,
        /,
        *args,
        default: M | yuio.Missing = yuio.MISSING,
        default_non_interactive: _t.Any = yuio.MISSING,
        parser: yuio.parse.Parser[S] | None = None,
        input_description: str | None = None,
        default_description: str | None = None,
    ) -> S | M: ...

    def __call__(cls, *args, **kwargs):
        if "parser" not in kwargs:
            hint = cls.__hint
            if hint is None:
                hint = str
            kwargs["parser"] = yuio.parse.from_type_hint(hint)
        return _ask(*args, **kwargs)

    def __getitem(cls, ty):
        return _AskMeta("ask", (), {"_AskMeta__hint": ty})

    # A dirty hack to hide `__getitem__` from type checkers. `ask` should look like
    # an ordinary class with overloaded `__new__` for the magic to work.
    locals()["__getitem__"] = __getitem

    def __repr__(cls) -> str:
        if cls.__hint is None:
            return cls.__name__
        else:
            return f"{cls.__name__}[{_t.type_repr(cls.__hint)}]"


@_t.final
class ask(_t.Generic[S], metaclass=_AskMeta):
    """ask(msg: str, /, *args, input_description: str | None = None) -> str
    ask[T](msg: str, /, *args, parser: ~yuio.parse.Parser[T], input_description: str | None = None) -> T
    ask[T](msg: str, /, *args, parser: ~yuio.parse.Parser[T] | None = None, default: U, default_non_interactive: U, input_description: str | None = None, default_description: str | None = None) -> T | U

    Ask user to provide an input, parse it and return a value.

    If ``stdin`` is not readable, return default if one is present,
    or raise a :class:`UserIoError`.

    .. vhs:: /_tapes/questions.tape
        :alt: Demonstration of the `ask` function.
        :scale: 40%

    :func:`ask` accepts generic parameters, which determine how input is parsed.
    For example, if you're asking for an enum element,
    Yuio will show user a choice widget.

    You can also supply a custom :class:`~yuio.parse.Parser`,
    which will determine the widget that is displayed to the user,
    the way auto completions work, etc.

    :param msg:
        prompt to display to user.
    :param args:
        arguments for ``%``\\ - formatting the prompt.
    :param parser:
        parser to use to parse user input. See :mod:`yuio.parse` for more info.
    :param default:
        default value to return if user input is empty.
    :param default_non_interactive:
        default value returned if input stream is not readable. If not given,
        ``default`` is used instead. This is handy when you want to ask user if they
        want to continue with ``default`` set to :data:`False`,
        but ``default_non_interactive`` set to :data:`True`.
    :param input_description:
        description of the expected input, like ``"yes/no"`` for boolean
        inputs.
    :param default_description:
        description of the `default` value.
    :returns:
        parsed user input.
    :example:
        .. code-block:: python

            class Level(enum.Enum):
                WARNING = "Warning",
                INFO = "Info",
                DEBUG = "Debug",

            answer = ask[Level]('Choose a logging level', default=Level.INFO)

    """


def _ask(
    msg: str,
    /,
    *args,
    parser: yuio.parse.Parser[_t.Any],
    default: _t.Any = yuio.MISSING,
    default_non_interactive: _t.Any = yuio.MISSING,
    input_description: str | None = None,
    default_description: str | None = None,
) -> _t.Any:
    term, theme, _ = _manager_data()

    if not term.istream.readable():
        if default_non_interactive is yuio.MISSING:
            default_non_interactive = default
        if default_non_interactive is yuio.MISSING:
            raise UserIoError("can't interact with user in non-interactive environment")
        return default_non_interactive

    if default is None and not yuio.parse._is_optional_parser(parser):
        parser = yuio.parse.Optional(parser)

    msg = msg.rstrip()
    if msg.endswith(":"):
        needs_colon = True
        msg = msg[:-1]
    else:
        needs_colon = msg and not msg[-1] in string.punctuation

    prompt = yuio.md.colorize(theme, msg, default_color="msg/text:question")
    if args:
        prompt = prompt % args

    if not input_description:
        input_description = parser.describe()

    if default is not yuio.MISSING:
        if default_description is None:
            try:
                default_description = parser.describe_value(default)
            except TypeError:
                pass
        if default_description is None:
            default_description = str(default)

    if get_term().is_fully_interactive:
        # Use widget.

        if needs_colon:
            prompt += yuio.md.colorize(theme, ":", default_color="msg/text:question")

        widget = _AskWidget(
            prompt, parser.widget(default, input_description, default_description)
        )
        with SuspendOutput() as s:
            try:
                result = widget.run(term, theme)
            except (OSError, EOFError) as e:
                raise UserIoError("unexpected end of input") from e

            if result is yuio.MISSING:
                result = default

            try:
                result_desc = parser.describe_value_or_def(result)
            except TypeError:
                result_desc = str(result)

            confirmation = prompt + (yuio.md.colorize(theme, " `%s`\n") % result_desc)

            s.raw(confirmation)
            return result
    else:
        # Use raw input.

        if input_description:
            prompt += (
                yuio.md.colorize(theme, " (%s)", default_color="msg/text:question")
                % input_description
            )
        if default_description:
            prompt += (
                yuio.md.colorize(theme, " [`%s`]", default_color="msg/text:question")
                % default_description
            )
        prompt += yuio.md.colorize(
            theme, ": " if needs_colon else " ", default_color="msg/text:question"
        )
        with SuspendOutput() as s:
            while True:
                try:
                    s.raw(prompt)
                    answer = term.istream.readline().strip()
                except (OSError, EOFError) as e:
                    raise UserIoError("unexpected end of input") from None
                if not answer and default is not yuio.MISSING:
                    return default
                elif not answer:
                    s.error("Input is required.")
                else:
                    try:
                        return parser.parse(answer)
                    except yuio.parse.ParsingError as e:
                        s.error("Error: " + e.msg, *e.args)


class _WaitForUserWidget(yuio.widget.Widget[None]):
    def __init__(self, prompt: yuio.term.ColorizedString):
        self._prompt = yuio.widget.Text(prompt)

    def layout(self, rc: yuio.widget.RenderContext, /) -> tuple[int, int]:
        return self._prompt.layout(rc)

    def draw(self, rc: yuio.widget.RenderContext, /):
        return self._prompt.draw(rc)

    @yuio.widget.bind(yuio.widget.Key.ENTER)
    @yuio.widget.bind(yuio.widget.Key.ESCAPE)
    @yuio.widget.bind("d", ctrl=True)
    @yuio.widget.bind(" ")
    def exit(self):
        return yuio.widget.Result(None)


def wait_for_user(
    msg: str = "Press <c note>enter</c> to continue",
    /,
    *args,
):
    """
    A simple function to wait for user to press enter.

    If ``stdin`` is not readable, does not do anything.

    :param msg:
        prompt to display to user.
    :param args:
        arguments for ``%``\\ - formatting the prompt.

    """

    term, theme, _ = _manager_data()

    if not term.istream.readable():
        return

    if msg and not msg[-1].isspace():
        msg += " "

    term = get_term()

    prompt = yuio.md.colorize(theme, msg, default_color="msg/text:question")
    if args:
        prompt %= args

    with SuspendOutput() as s:
        try:
            if term.is_fully_interactive:
                _WaitForUserWidget(prompt).run(term, theme)
            else:
                s.raw(prompt)
                term.istream.readline()
        except (OSError, EOFError):
            return


def detect_editor(fallbacks: list[str] | None = None) -> str | None:
    """
    Detect the user's preferred editor.

    This function checks the ``VISUAL`` and ``EDITOR`` environment variables.
    If they're not set, it checks if any of the fallback editors are available.
    If none can be found, it returns :data:`None`.

    :param fallbacks:
        list of fallback editors to try. By default, we try "nano", "vim", "vi",
        "msedit", "edit", "notepad", "gedit".
    :returns:
        on Windows, returns an executable name; on unix, may return a shell command
        or an executable name.

    """

    if os.name != "nt":
        if editor := os.environ.get("VISUAL"):
            return editor
        elif editor := os.environ.get("EDITOR"):
            return editor

    if fallbacks is None:
        fallbacks = ["nano", "vim", "vi", "msedit", "edit", "notepad", "gedit"]
    for fallback in fallbacks:
        if shutil.which(fallback):
            return fallback
    return None


def edit(
    text: str,
    /,
    *,
    comment_marker: str | None = None,
    editor: str | None = None,
    file_ext: str = ".txt",
    fallbacks: list[str] | None = None,
    dedent: bool = False,
) -> str:
    """
    Ask user to edit some text.

    This function creates a temporary file with the given text
    and opens it in an editor. After editing is done, it strips away
    all lines that start with ``comment_marker``, if one is given.

    If editor is not available or returns a non-zero exit code,
    a :class:`UserIoError` is raised.

    If launched in a non-interactive environment, returns the text
    unedited (comments are still removed, though).

    :param text:
        text to edit.
    :param comment_marker:
        lines starting with this marker will be removed from the output after edit.
    :param editor:
        overrides shell command for editor.
    :param file_ext:
        extension for the temporary file, can be used to enable syntax highlighting
        in editors that support it.
    :param fallbacks:
        list of fallback editors to try, see :func:`detect_editor` for details.
    :param dedent:
        remove leading indentation from text before opening an editor.
    :returns:
        an edited string with comments removed.
    :example:
        .. code-block:: python

            message = yuio.io.edit(
                \"\"\"
                    # Please enter the commit message for your changes. Lines starting
                    # with '#' will be ignored, and an empty message aborts the commit.
                \"\"\",
                comment_marker="#",
                dedent=True,
            )

    """

    if dedent:
        text = yuio.dedent(text)

    term, _, _ = _manager_data()

    if term.is_fully_interactive:
        if editor is None:
            editor = detect_editor(fallbacks)

        if editor is None:
            raise UserIoError(
                "can't detect an editor, ensure that the $EDITOR "
                "environment variable contains "
                "a correct path to an editor executable"
            )

        fd, filepath = tempfile.mkstemp(text=True, suffix=file_ext)
        try:
            with open(fd, "w") as file:
                file.write(text)

            if os.name == "nt":
                # Windows doesn't use $VISUAL/$EDITOR, so shell execution is not needed.
                # Plus, quoting arguments for CMD.exe is hard af.
                args = [editor, filepath]
                shell = False
            else:
                # $VISUAL/$EDITOR can include flags, so we need to use shell instead.
                try:
                    from shlex import quote
                except ImportError:
                    from pipes import quote
                args = f"{editor} {quote(filepath)}"
                shell = True

            try:
                with SuspendOutput():
                    res = subprocess.run(args, shell=shell)
            except FileNotFoundError:
                raise UserIoError(
                    f"can't use editor {editor!r}, ensure that the $VISUAL and $EDITOR "
                    "environment variables contain correct shell commands"
                )

            if res.returncode != 0:
                raise UserIoError(
                    f"editing failed: editor {editor!r} "
                    f"returned exit code {res.returncode}"
                )

            if not os.path.exists(filepath):
                raise UserIoError(f"editing failed: can't read back edited file")
            else:
                with open(filepath) as file:
                    text = file.read()
        finally:
            try:
                os.remove(filepath)
            except OSError:
                pass

    if comment_marker is not None:
        text = re.sub(
            r"^\s*" + re.escape(comment_marker) + r".*(\n|$)",
            "",
            text,
            flags=re.MULTILINE,
        )

    return text


class SuspendOutput:
    """
    A context manager for pausing output.

    This is handy for when you need to take control over the output stream.
    For example, the :func:`ask` function uses this class internally.

    This context manager also suspends all prints that go to :data:`sys.stdout`
    and :data:`sys.stderr` if they were wrapped (see :func:`setup`).
    To print through them, use :func:`orig_stderr` and :func:`orig_stdout`.

    """

    def __init__(self):
        self._resumed = False
        _manager().suspend()

    def resume(self):
        """
        Manually resume the logging process.

        """

        if not self._resumed:
            _manager().resume()
            self._resumed = True

    @_t.overload
    @staticmethod
    def info(msg: str, /, *args, **kwargs): ...
    @_t.overload
    @staticmethod
    def info(err: Exception, /, **kwargs): ...
    @staticmethod
    def info(msg: str | Exception, /, *args, **kwargs):
        """info(msg: str, /, *args)
        info(err: Exception, /)

        Log an :func:`info` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        info(msg, *args, **kwargs)

    @_t.overload
    @staticmethod
    def warning(msg: str, /, *args, **kwargs): ...
    @_t.overload
    @staticmethod
    def warning(err: Exception, /, **kwargs): ...
    @staticmethod
    def warning(msg: str | Exception, /, *args, **kwargs):
        """warning(msg: str, /, *args)
        warning(err: Exception, /)

        Log a :func:`warning` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        warning(msg, *args, **kwargs)

    @_t.overload
    @staticmethod
    def success(msg: str, /, *args, **kwargs): ...
    @_t.overload
    @staticmethod
    def success(err: Exception, /, **kwargs): ...
    @staticmethod
    def success(msg: str | Exception, /, *args, **kwargs):
        """success(msg: str, /, *args)
        success(err: Exception, /)

        Log a :func:`success` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        success(msg, *args, **kwargs)

    @_t.overload
    @staticmethod
    def error(msg: str, /, *args, **kwargs): ...
    @_t.overload
    @staticmethod
    def error(err: Exception, /, **kwargs): ...
    @staticmethod
    def error(msg: str | Exception, /, *args, **kwargs):
        """error(msg: str, /, *args)
        error(err: Exception, /)

        Log an :func:`error` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        error(msg, *args, **kwargs)

    @staticmethod
    def error_with_tb(msg: str, /, *args, **kwargs):
        """error_with_tb(msg: str, /, *args, exc_info: tuple[type[BaseException] | None, BaseException | None, ~types.TracebackType | None] | bool | None = True)

        Log an :func:`error_with_tb` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        error_with_tb(msg, *args, **kwargs)

    @_t.overload
    @staticmethod
    def failure(msg: str, /, *args, **kwargs): ...
    @_t.overload
    @staticmethod
    def failure(err: Exception, /, **kwargs): ...
    @staticmethod
    def failure(msg: str | Exception, /, *args, **kwargs):
        """failure(msg: str, /, *args)
        failure(err: Exception, /)

        Log a :func:`failure` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        failure(msg, *args, **kwargs)

    @staticmethod
    def failure_with_tb(msg: str, /, *args, **kwargs):
        """failure_with_tb(msg: str, /, *args, exc_info: tuple[type[BaseException] | None, BaseException | None, ~types.TracebackType | None] | bool | None = True)

        Log a :func:`failure_with_tb` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        failure_with_tb(msg, *args, **kwargs)

    @staticmethod
    def heading(msg: str, /, *args, **kwargs):
        """heading(msg: str, /, *args)

        Log a :func:`heading` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        heading(msg, *args, **kwargs)

    @staticmethod
    def md(msg: str, /, *args, **kwargs):
        """md(msg: str, /, *args)

        Log an :func:`md` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        md(msg, *args, **kwargs)

    @staticmethod
    def br(**kwargs):
        """br()

        Log a :func:`br` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        br(**kwargs)

    @staticmethod
    def hl(msg: str, /, *args, syntax: str | yuio.md.SyntaxHighlighter, **kwargs):
        """hl(msg: str, /, *args, syntax: str | yuio.md.SyntaxHighlighter)

        Log an :func:`md` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        hl(msg, *args, syntax=syntax, **kwargs)

    @staticmethod
    def raw(msg: yuio.term.ColorizedString, **kwargs):
        """raw(msg: yuio.term.ColorizedString, /)

        Log a :func:`raw` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        raw(msg, **kwargs)

    @_t.overload
    @staticmethod
    def out(msg: str, /, *args, **kwargs): ...
    @_t.overload
    @staticmethod
    def out(err: Exception, /, **kwargs): ...
    @staticmethod
    def out(msg: str | Exception, /, *args, **kwargs):
        """out(msg: str, /, *args)
        out(err: Exception, /)

        Log an :func:`out` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        out(msg, *args, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.resume()


class _IterTask(_t.Generic[T]):
    def __init__(
        self, collection: _t.Collection[T], task: Task, unit: str, ndigits: int
    ):
        self._iter = iter(collection)
        self._task = task
        self._unit = unit
        self._ndigits = ndigits

        self._i = 0
        self._len = len(collection)

    def __next__(self) -> T:
        self._task.progress(self._i, self._len, unit=self._unit, ndigits=self._ndigits)
        if self._i < self._len:
            self._i += 1
        return self._iter.__next__()

    def __iter__(self) -> _IterTask[T]:
        return self


class Task:
    """
    A class for indicating progress of some task.

    :param msg:
        task heading.
    :param args:
        arguments for ``%``\\ -formatting the task heading.
    :param comment:
        comment for the task. Can be specified after creation
        via the :meth:`~Task.comment` method.

    You can have multiple tasks at the same time,
    create subtasks, set task's progress or add a comment about
    what's currently being done within a task.

    .. vhs:: /_tapes/tasks_multithreaded.tape
       :alt: Demonstration of the `Task` class.
       :scale: 40%

    This class can be used as a context manager::

        with Task('Processing input') as t:
            ...
            t.progress(0.3)
            ...

    """

    class _Status(enum.Enum):
        DONE = "done"
        ERROR = "error"
        RUNNING = "running"

    def __init__(
        self,
        msg: str,
        /,
        *args,
        _parent: Task | None = None,
        comment: str | None = None,
    ):
        # Task properties should not be written to directly.
        # Instead, task should be sent to a handler for modification.
        # This ensures thread safety, because handler has a lock.
        # See handler's implementation details.

        self._msg: str = msg
        self._args: tuple[object, ...] = args
        self._comment: str | None = comment
        self._comment_args: tuple[object, ...] | None = None
        self._status: Task._Status = Task._Status.RUNNING
        self._progress: float | None = None
        self._progress_done: str | None = None
        self._progress_total: str | None = None
        self._subtasks: list[Task] = []

        self._cached_msg: yuio.term.ColorizedString | None = None
        self._cached_comment: yuio.term.ColorizedString | None = None

        if _parent is None:
            _manager().start_task(self)
        else:
            _manager().start_subtask(_parent, self)

    @_t.overload
    def progress(self, progress: float | None, /, *, ndigits: int = 2): ...

    @_t.overload
    def progress(
        self,
        done: float | int,
        total: float | int,
        /,
        *,
        unit: str = "",
        ndigits: int = 0,
    ): ...

    def progress(
        self,
        *args: float | int | None,
        unit: str = "",
        ndigits: int | None = None,
    ):
        """
        progress(progress: float | None, /, *, ndigits: int = 2)
        progress(done: float | int, total: float | int, /, *, unit: str = "", ndigits: int = 0) ->

        Indicate progress of this task.

        If given one argument, it is treated as percentage between ``0`` and ``1``.

        If given two arguments, they are treated as amount of finished work,
        and a total amount of work. In this case, optional argument ``unit``
        can be used to indicate units, in which amount is calculated.

        If given a single :data:`None`, reset task progress.

        :param progress:
            a percentage between ``0`` and ``1``, or :data:`None`
            to reset task progress.
        :param done:
            amount of finished work, should be less than or equal to ``total``.
        :param total:
            total amount of work.
        :param unit:
            unit for measuring progress. Only displayed when progress is given
            as ``done`` and ``total``.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. code-block:: python

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
                ndigits = (
                    2 if isinstance(done, float) or isinstance(total, float) else 0
                )
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
            progress = done / total if total else 0
            _manager().set_task_progress(self, progress, done_str, total_str + unit)

    def progress_size(
        self,
        done: float | int,
        total: float | int,
        /,
        *,
        ndigits: int = 2,
    ):
        """
        Indicate progress of this task using human-readable 1024-based size units.

        :param done:
            amount of processed data.
        :param total:
            total amount of data.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. code-block:: python

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
        for unit in "BKMGT":
            if n < 1024:
                return n, unit
            n /= 1024
        return n, "P"

    def progress_scale(
        self,
        done: float | int,
        total: float | int,
        /,
        *,
        unit: str = "",
        ndigits: int = 2,
    ):
        """
        Indicate progress of this task while scaling numbers in accordance
        with SI system.

        :param done:
            amount of finished work, should be less than or equal to ``total``.
        :param total:
            total amount of work.
        :param unit:
            unit for measuring progress.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. code-block:: python

                with Task("Charging a capacitor") as task:
                    task.progress_scale(889.25E-3, 1, unit="V")

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
    def _unit(n: float) -> tuple[float, str]:
        if math.fabs(n) < 1e-33:
            return 0, ""
        magnitude = max(-8, min(8, int(math.log10(math.fabs(n)) // 3)))
        if magnitude < 0:
            return n * 10 ** -(3 * magnitude), "mµnpfazy"[-magnitude - 1]
        elif magnitude > 0:
            return n / 10 ** (3 * magnitude), "KMGTPEZY"[magnitude - 1]
        else:
            return n, ""

    def iter(
        self,
        collection: _t.Collection[T],
        /,
        *,
        unit: str = "",
        ndigits: int = 0,
    ) -> _t.Iterable[T]:
        """
        Helper for updating progress automatically
        while iterating over a collection.

        :param collection:
            an iterable collection. Should support returning its length.
        :param total:
            total amount of work.
        :param unit:
            unit for measuring progress.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. invisible-code-block: python

                urls = []

            .. code-block:: python

                with Task('Fetching data') as t:
                    for url in t.iter(urls):
                        ...

            This will output the following:

            .. code-block:: text

                ■■■■■□□□□□□□□□□ Fetching data - 1/3

        """

        return _IterTask(collection, self, unit, ndigits)

    def comment(self, comment: str | None, /, *args):
        """
        Set a comment for a task.

        Comment is displayed after the progress.

        :param comment:
            comment to display beside task progress.
        :param args:
            arguments for ``%``\\ -formatting comment.
        :example:
            .. invisible-code-block: python

                urls = []

            .. code-block:: python

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
        """
        Indicate that this task has finished successfully.

        """

        _manager().finish_task(self, Task._Status.DONE)

    def error(self):
        """
        Indicate that this task has finished with an error.

        """

        _manager().finish_task(self, Task._Status.ERROR)

    def subtask(self, msg: str, /, *args, comment: str | None = None) -> Task:
        """
        Create a subtask within this task.

        :param msg:
            subtask heading.
        :param args:
            arguments for ``%``\\ -formatting the subtask heading.
        :param comment:
            comment for the task. Can be specified after creation
            via the :meth:`~Task.comment` method.
        :returns:
            a new :class:`Task` that will be displayed as a sub-task of this task.

        """

        return Task(msg, *args, _parent=self, comment=comment)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done()
        else:
            self.error()


class Handler(logging.Handler):
    """
    A handler that redirects all log messages to Yuio.

    """

    def emit(self, record: LogRecord):
        _manager().print_rec(record)


class _IoManager(abc.ABC):
    def __init__(
        self,
        term: yuio.term.Term | None = None,
        theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = None,
        enable_bg_updates: bool = True,
    ):
        self.out_term = yuio.term.get_term_from_stream(
            orig_stdout(), sys.stdin, query_terminal_colors=False
        )
        self._term = term or yuio.term.get_term_from_stream(orig_stderr(), sys.stdin)
        if theme is None:
            self._theme = yuio.theme.load(self._term)
        elif isinstance(theme, yuio.theme.Theme):
            self._theme = theme
        else:
            self._theme = theme(self._term)
        self._rc = yuio.widget.RenderContext(self._term, self._theme)
        self._rc.prepare()

        self._suspended: int = 0
        self._suspended_lines: list[tuple[list[str], _t.TextIO]] = []

        self._tasks: list[Task] = []
        self._tasks_printed = 0
        self._spinner_state = 0
        self._needs_update = False
        self._last_update_time_us = 0
        self._printed_some_lines = False

        self._renders = 0

        self._stop = False
        self._stop_condition = threading.Condition(_IO_LOCK)
        self._thread: threading.Thread | None = None

        self._enable_bg_updates = enable_bg_updates
        if enable_bg_updates:
            self._thread = threading.Thread(
                target=self._bg_update, name="yuio_io_task_refresh", daemon=True
            )
            self._thread.start()

            atexit.register(self.stop)

    def setup(
        self,
        term: yuio.term.Term | None = None,
        theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = None,
    ):
        with _IO_LOCK:
            self._clear_tasks()

            if term is not None:
                self._term = term
            if theme is not None:
                if not isinstance(theme, yuio.theme.Theme):
                    theme = theme(self._term)
                self._theme = theme

            self._rc = yuio.widget.RenderContext(self._term, self._theme)
            self._rc.prepare()
            self.__dict__.pop("_update_rate_us", None)
            self._update_tasks()

    def _bg_update(self):
        while True:
            try:
                with _IO_LOCK:
                    while True:
                        update_rate_us = self._update_rate_us
                        now_us = time.monotonic_ns() // 1_000
                        sleep_us = update_rate_us - now_us % update_rate_us

                        if self._stop_condition.wait_for(
                            lambda: self._stop, timeout=sleep_us / 1_000_000
                        ):
                            return

                        self._show_tasks()
            except Exception:
                yuio._logger.critical("exception in bg updater", exc_info=True)

    def stop(self):
        with _IO_LOCK:
            atexit.unregister(self.stop)

            self._stop = True
            self._stop_condition.notify()
            self._show_tasks(immediate_render=True)

        if self._thread:
            self._thread.join()

    def print_msg(
        self,
        msg: str,
        args: tuple[object, ...] | None,
        /,
        *,
        tag: str,
        exc_info: _ExcInfo | bool | None = None,
        ignore_suspended: bool = False,
        heading: bool = False,
        term: yuio.term.Term | None = None,
        to_stdout: bool = False,
    ):
        with _IO_LOCK:
            if term is None:
                term = self.out_term if to_stdout else self._term
            col_msg = self._format_msg(
                msg, args, tag, exc_info=exc_info, heading=heading
            )
            self._emit_lines(
                col_msg.process_colors(term), term.ostream, ignore_suspended
            )

    def print_rec(
        self,
        record: logging.LogRecord,
    ):
        with _IO_LOCK:
            col_rec = self._format_rec(record)
            self._emit_lines(col_rec.process_colors(self._term))

    def print_raw(
        self,
        msg: yuio.term.ColorizedString,
        /,
        *,
        ignore_suspended: bool = False,
        term: yuio.term.Term | None = None,
        to_stdout: bool = False,
    ):
        with _IO_LOCK:
            if term is None:
                term = self.out_term if to_stdout else self._term
            self._emit_lines(msg.process_colors(term), term.ostream, ignore_suspended)

    def print_direct(
        self,
        msg: str,
        stream: _t.TextIO | None = None,
        /,
        *,
        ignore_suspended: bool = False,
        term: yuio.term.Term | None = None,
        to_stdout: bool = False,
    ):
        with _IO_LOCK:
            if stream is None:
                term = self.out_term if to_stdout else self._term
                stream = term.ostream
            self._emit_lines([msg], stream, ignore_suspended)

    def print_direct_lines(
        self,
        lines: _t.Iterable[str],
        stream: _t.TextIO | None = None,
        /,
        *,
        ignore_suspended: bool = False,
        term: yuio.term.Term | None = None,
        to_stdout: bool = False,
    ):
        with _IO_LOCK:
            if stream is None:
                term = self.out_term if to_stdout else self._term
                stream = term.ostream
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
        progress: float | None,
        done: str | None,
        total: str | None,
    ):
        with _IO_LOCK:
            task._progress = progress
            task._progress_done = done
            task._progress_total = total
            self._update_tasks()

    def set_task_comment(self, task: Task, comment: str | None, args):
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

    @functools.cached_property
    def _update_rate_us(self) -> int:
        update_rate_ms = max(self._theme.spinner_update_rate_ms, 1)
        while update_rate_ms < 50:
            update_rate_ms *= 2
        while update_rate_ms > 100:
            update_rate_ms /= 2
        return int(update_rate_ms * 1000)

    @property
    def _spinner_update_rate_us(self) -> int:
        return self._theme.spinner_update_rate_ms * 1000

    def _emit_lines(
        self,
        lines: _t.Iterable[str],
        stream: _t.TextIO | None = None,
        ignore_suspended: bool = False,
    ):
        stream = stream or self._term.ostream
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
            if self._suspended_lines:
                self._printed_some_lines = True
            self._suspended_lines.clear()

            self._update_tasks()

        if self._suspended < 0:
            yuio._logger.debug("unequal number of suspends and resumes")
            self._suspended = 0

    def _start_task(self, task: Task):
        if self._term.can_move_cursor:
            self._tasks.append(task)
            self._update_tasks()
        else:
            self._emit_lines(self._format_task(task).process_colors(self._term))

    def _start_subtask(self, parent: Task, task: Task):
        if self._term.can_move_cursor:
            parent._subtasks.append(task)
            self._update_tasks()
        else:
            self._emit_lines(self._format_task(task).process_colors(self._term))

    def _finish_task(self, task: Task, status: Task._Status):
        if task._status != Task._Status.RUNNING:
            yuio._logger.debug("trying to change status of an already stopped task")
            return

        task._status = status
        for subtask in task._subtasks:
            if subtask._status == Task._Status.RUNNING:
                self._finish_task(subtask, status)

        if self._term.can_move_cursor:
            if task in self._tasks:
                self._tasks.remove(task)
                self._emit_lines(self._format_task(task).process_colors(self._term))
            else:
                self._update_tasks()
        else:
            self._emit_lines(self._format_task(task).process_colors(self._term))

    def _clear_tasks(self):
        if self._term.can_move_cursor and self._tasks_printed:
            self._rc.finalize()
            self._tasks_printed = 0

    def _update_tasks(self, immediate_render: bool = False):
        self._needs_update = True
        if immediate_render or not self._enable_bg_updates:
            self._show_tasks(immediate_render)

    def _show_tasks(self, immediate_render: bool = False):
        if (
            self._term.can_move_cursor
            and not self._suspended
            and (self._tasks or self._tasks_printed)
        ):
            now_us = time.monotonic_ns() // 1000
            now_us -= now_us % self._update_rate_us

            if not immediate_render and self._enable_bg_updates:
                next_update_us = self._last_update_time_us + self._update_rate_us
                if now_us < next_update_us:
                    # Hard-limit update rate by `update_rate_ms`.
                    return
                next_spinner_update_us = (
                    self._last_update_time_us + self._spinner_update_rate_us
                )
                if not self._needs_update and now_us < next_spinner_update_us:
                    # Tasks didn't change, and spinner state didn't change either,
                    # so we can skip this update.
                    return

            self._last_update_time_us = now_us
            self._spinner_state = now_us // self._spinner_update_rate_us
            self._tasks_printed = 0
            self._needs_update = False

            self._prepare_for_rendering_tasks()
            for task in self._tasks:
                self._draw_task(task, 0)
            self._renders += 1
            self._rc.set_final_pos(0, self._tasks_printed)
            self._rc.render()

    def _prepare_for_rendering_tasks(self):
        self._rc.prepare()

        self.n_tasks = dict.fromkeys(Task._Status, 0)
        self.displayed_tasks = dict.fromkeys(Task._Status, 0)

        stack = self._tasks.copy()
        while stack:
            task = stack.pop()
            self.n_tasks[task._status] += 1
            stack.extend(task._subtasks)

        self.display_tasks = self.n_tasks.copy()
        total_tasks = sum(self.display_tasks.values())
        height = self._rc.height
        if total_tasks > height:
            height -= 1  # account for '+x more' message
            for status in Task._Status:
                to_hide = min(total_tasks - height, self.display_tasks[status])
                self.display_tasks[status] -= to_hide
                total_tasks -= to_hide
                if total_tasks <= height:
                    break

    def _format_msg(
        self,
        msg: str,
        args: tuple[object, ...] | None,
        tag: str,
        /,
        *,
        exc_info: _ExcInfo | bool | None = None,
        heading: bool = False,
    ) -> yuio.term.ColorizedString:
        decoration = self._theme.msg_decorations.get(tag, "")
        if decoration:
            first_line_indent = yuio.term.ColorizedString(
                [self._theme.get_color(f"msg/decoration:{tag}"), decoration]
            )
            continuation_indent = " " * first_line_indent.width
        else:
            first_line_indent = ""
            continuation_indent = ""

        res = yuio.term.ColorizedString()

        if heading and self._printed_some_lines:
            res += "\n"

        col_msg = yuio.md.colorize(self._theme, msg, default_color=f"msg/text:{tag}")
        if args:
            col_msg %= args
        for line in col_msg.wrap(
            self._rc.canvas_width,
            first_line_indent=first_line_indent,
            continuation_indent=continuation_indent,
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
        if exc_info is not None and exc_info != (None, None, None):
            tb = "".join(traceback.format_exception(*exc_info))
            res += self._format_tb(tb, "  ")

        if heading:
            res += "\n"

        res += yuio.term.Color.NONE

        return res

    def _format_rec(self, record: logging.LogRecord) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        asctime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record.created))

        logger = record.name
        level = record.levelname
        message = record.getMessage()

        ctx = record.levelname.lower()

        res += self._theme.get_color(f"log/asctime:{ctx}")
        res += asctime
        res += " "

        res += self._theme.get_color(f"log/logger:{ctx}")
        res += logger
        res += " "

        res += self._theme.get_color(f"log/level:{ctx}")
        res += level
        res += " "

        res += self._theme.get_color(f"log/message:{ctx}")
        res += message
        res += "\n"

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = "".join(traceback.format_exception(*record.exc_info))
            res += self._format_tb(record.exc_text, "  ")
        if record.stack_info:
            res += self._format_tb(record.stack_info, "  ")

        res += yuio.term.Color.NONE

        return res

    def _format_tb(self, tb: str, indent: str) -> yuio.term.ColorizedString:
        highlighter = yuio.md.SyntaxHighlighter.get_highlighter("python-traceback")
        return highlighter.highlight(self._theme, tb).indent(indent, indent)

    def _format_task(self, task: Task) -> yuio.term.ColorizedString:
        res = yuio.term.ColorizedString()

        ctx = task._status.value

        if decoration := self._theme.msg_decorations.get("task"):
            res += self._theme.get_color(f"task/decoration:{ctx}")
            res += decoration

        res += self._format_task_msg(task)
        res += self._theme.get_color(f"task:{ctx}")
        res += " - "
        res += self._theme.get_color(f"task/progress:{ctx}")
        res += task._status.value
        res += self._theme.get_color(f"task:{ctx}")
        res += "\n"

        res += yuio.term.Color.NONE

        return res

    def _format_task_msg(self, task: Task) -> yuio.term.ColorizedString:
        if task._cached_msg is None:
            msg = yuio.md.colorize(
                self._theme,
                task._msg,
                default_color=f"task/heading:{task._status.value}",
            )
            if task._args:
                msg %= task._args
            task._cached_msg = msg
        return task._cached_msg

    def _format_task_comment(self, task: Task) -> yuio.term.ColorizedString | None:
        if task._status is not Task._Status.RUNNING:
            return None
        if task._cached_comment is None and task._comment is not None:
            comment = yuio.md.colorize(
                self._theme,
                task._comment,
                default_color=f"task/comment:{task._status.value}",
            )
            if task._comment_args:
                comment %= task._comment_args
            task._cached_comment = comment
        return task._cached_comment

    def _draw_task(self, task: Task, indent: int):
        self.displayed_tasks[task._status] += 1

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
        if task._status in (Task._Status.DONE, Task._Status.ERROR):
            self._rc.set_color_path(f"task:{task._status.value}")
            self._rc.write(" - ")
            self._rc.set_color_path(f"task/progress:{task._status.value}")
            self._rc.write(task._status.name.lower())
        elif task._progress_done is not None:
            self._rc.set_color_path(f"task:{task._status.value}")
            self._rc.write(" - ")
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
            self._rc.write(self._theme.spinner_static_symbol)
        elif (
            task._progress is None
            or self._theme.progress_bar_width <= 1
            or not self._theme.progress_bar_done_symbol
            or not self._theme.progress_bar_pending_symbol
        ):
            self._rc.set_color_path(f"task/decoration:{task._status.value}")
            if self._theme.spinner_pattern:
                self._rc.write(
                    self._theme.spinner_pattern[
                        self._spinner_state % len(self._theme.spinner_pattern)
                    ]
                )
        else:
            total_width = self._theme.progress_bar_width
            done_width = round(max(0, min(1, task._progress)) * total_width)

            self._rc.set_color_path(f"task/progressbar:{task._status.value}")
            self._rc.write(self._theme.progress_bar_start_symbol)

            done_color = yuio.term.Color.lerp(
                self._theme.get_color("task/progressbar/done/start"),
                self._theme.get_color("task/progressbar/done/end"),
            )

            for i in range(0, done_width):
                self._rc.set_color(done_color(i / (total_width - 1)))
                self._rc.write(self._theme.progress_bar_done_symbol)

            pending_color = yuio.term.Color.lerp(
                self._theme.get_color("task/progressbar/pending/start"),
                self._theme.get_color("task/progressbar/pending/end"),
            )

            for i in range(done_width, total_width):
                self._rc.set_color(pending_color(i / (total_width - 1)))
                self._rc.write(self._theme.progress_bar_pending_symbol)

            self._rc.set_color_path(f"task/progressbar:{task._status.value}")
            self._rc.write(self._theme.progress_bar_end_symbol)

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

    def readable(self) -> bool:
        return self.__wrapped.readable()

    def read(self, n: int = -1) -> str:
        return self.__wrapped.read(n)

    def readline(self, limit: int = -1) -> str:
        return self.__wrapped.readline(limit)

    def readlines(self, hint: int = -1) -> list[str]:
        return self.__wrapped.readlines(hint)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self.__wrapped.seek(offset, whence)

    def seekable(self) -> bool:
        return self.__wrapped.seekable()

    def tell(self) -> int:
        return self.__wrapped.tell()

    def truncate(self, size: int | None = None) -> int:
        return self.__wrapped.truncate(size)

    def __enter__(self) -> _t.TextIO:
        return self.__wrapped.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__wrapped.__exit__(exc_type, exc_val, exc_tb)

    @property
    def buffer(self) -> _t.BinaryIO:
        return self.__wrapped.buffer

    @property
    def encoding(self) -> str:
        return self.__wrapped.encoding

    @property
    def errors(self) -> str | None:
        return self.__wrapped.errors

    @property
    def line_buffering(self) -> int:
        return self.__wrapped.line_buffering

    @property
    def newlines(self) -> _t.Any:
        return self.__wrapped.newlines
