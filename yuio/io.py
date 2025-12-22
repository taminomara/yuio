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
to the one from :mod:`logging`. Messages are highlighted using
:ref:`color tags <color-tags>` and formatted using :ref:`%-formatting <percent-format>`:

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

.. autofunction:: hr

.. autofunction:: raw


.. _percent-format:

Formatting the output
---------------------

Messages are formatted using `printf-style formatting`__, similar to :mod:`logging`.

__ https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting

``%s`` and ``%r`` specifiers are handled to respect colors and `rich repr protocol`__.
Additionally, they allow specifying flags to control whether rendered values should
be colorized, and should they be rendered in multiple lines:

__ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

- ``#`` enables colors in repr (i.e. ``%#r``);
- ``+`` splits repr into multiple lines (i.e. ``%+r``, ``%#+r``).

To support colorized formatting, define ``__colorized_str__``
and ``__colorized_repr__`` on your class. See :ref:`pretty-protocol` for implementation
details.

To support rich repr protocol, define function ``__rich_repr__`` on your class.
This method should return an iterable of tuples, as described in Rich__ documentation.

__ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol


.. _color-tags:

Coloring the output
-------------------

By default, all messages are colored according to their level (i.e. which function
you use to print them).

If you need inline colors, you can use special tags in your log messages::

    info("Using the <c code>code</c> tag.")

You can combine multiple colors in the same tag::

    info("<c bold green>Success!</c>")

Only tags that appear in the message itself are processed::

    info("Tags in this message --> %s are printed as-is", "<c color>")

For highlighting inline code, Yuio supports parsing CommonMark's backticks::

    info("Using the `backticks`.")
    info("Using the `` nested `backticks` ``")

List of all tags that are available by default:

-   ``code``, ``note``, ``path``: highlights,
-   ``bold``, ``b``, ``dim``, ``d``, ``italic``, ``i``,
    ``underline``, ``u``, ``inverse``: font style,
-   ``normal``, ``red``, ``green``, ``yellow``, ``blue``,
    ``magenta``, ``cyan``: colors.


Formatting utilities
--------------------

There are several :ref:`formatting utilities <formatting-utilities>` defined
in :mod:`yuio.string` and re-exported in :mod:`yuio.io`. These utilities
perform various formatting tasks when converted to strings, allowing you to lazily
build more complex messages.


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

All of these functions throw an error if something goes wrong:

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

    .. automethod:: hr

    .. automethod:: raw


Python's `logging` and yuio
---------------------------

If you want to direct messages from the :mod:`logging` to Yuio,
you can add a :class:`Handler`:

.. autoclass:: Handler

.. autoclass:: Formatter


Helper types
------------

.. type:: ExcInfo
    :canonical: tuple[type[BaseException] | None, BaseException | None, types.TracebackType | None]

    Exception information as returned by :func:`sys.exc_info`.


Re-imports
----------

.. type:: And
    :no-index:

    Alias of :obj:`yuio.string.And`.

.. type:: ColorizedString
    :no-index:

    Alias of :obj:`yuio.string.ColorizedString`.

.. type:: Format
    :no-index:

    Alias of :obj:`yuio.string.Format`.

.. type:: Hl
    :no-index:

    Alias of :obj:`yuio.string.Hl`.

.. type:: Hr
    :no-index:

    Alias of :obj:`yuio.string.Hr`.

.. type:: Indent
    :no-index:

    Alias of :obj:`yuio.string.Indent`.

.. type:: JoinRepr
    :no-index:

    Alias of :obj:`yuio.string.JoinRepr`.

.. type:: JoinStr
    :no-index:

    Alias of :obj:`yuio.string.JoinStr`.

.. type:: Link
    :no-index:

    Alias of :obj:`yuio.string.Link`.

.. type:: Md
    :no-index:

    Alias of :obj:`yuio.string.Md`.

.. type:: Or
    :no-index:

    Alias of :obj:`yuio.string.Or`.

.. type:: Repr
    :no-index:

    Alias of :obj:`yuio.string.Repr`.

.. type:: Stack
    :no-index:

    Alias of :obj:`yuio.string.Stack`.

.. type:: TypeRepr
    :no-index:

    Alias of :obj:`yuio.string.TypeRepr`.

.. type:: WithBaseColor
    :no-index:

    Alias of :obj:`yuio.string.WithBaseColor`.

.. type:: Wrap
    :no-index:

    Alias of :obj:`yuio.string.Wrap`.


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

import yuio.color
import yuio.md
import yuio.parse
import yuio.string
import yuio.term
import yuio.theme
import yuio.widget
from yuio import _typing as _t
from yuio.string import (
    And,
    ColorizedString,
    Format,
    Hl,
    Hr,
    Indent,
    JoinRepr,
    JoinStr,
    Link,
    Md,
    Or,
    Repr,
    Stack,
    TypeRepr,
    WithBaseColor,
    Wrap,
)
from yuio.util import dedent as _dedent

__all__ = [
    "And",
    "ColorizedString",
    "ExcInfo",
    "Format",
    "Formatter",
    "Handler",
    "Hl",
    "Hr",
    "Indent",
    "JoinRepr",
    "JoinStr",
    "Link",
    "Md",
    "Or",
    "Repr",
    "Stack",
    "SuspendOutput",
    "Task",
    "TypeRepr",
    "UserIoError",
    "WithBaseColor",
    "Wrap",
    "ask",
    "br",
    "detect_editor",
    "edit",
    "error",
    "error_with_tb",
    "failure",
    "failure_with_tb",
    "get_term",
    "get_theme",
    "heading",
    "hl",
    "hr",
    "info",
    "make_repr_context",
    "md",
    "orig_stderr",
    "orig_stdout",
    "raw",
    "restore_streams",
    "setup",
    "streams_wrapped",
    "success",
    "wait_for_user",
    "warning",
    "wrap_streams",
]

T = _t.TypeVar("T")
M = _t.TypeVar("M", default=_t.Never)
S = _t.TypeVar("S", default=str)

ExcInfo: _t.TypeAlias = tuple[
    type[BaseException] | None,
    BaseException | None,
    types.TracebackType | None,
]
"""
Exception information as returned by :func:`sys.exc_info`.

"""


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


class UserIoError(yuio.PrettyException, IOError):
    """
    Raised when interaction with user fails.

    """


def setup(
    *,
    term: yuio.term.Term | None = None,
    theme: (
        yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
    ) = None,
    fallback_theme: (
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
    :param fallback_theme:
        either a theme that will be used when printing to non-tty terminals, i.e. when
        output is redirected to a file.

        If not passed, the global theme is not re-configured; the default is to use
        :class:`yuio.theme.DummyTheme` then.
    :param wrap_stdio:
        if set to :data:`True`, wraps :data:`sys.stdout` and :data:`sys.stderr`
        in a special wrapper that ensures better interaction
        with Yuio's progress bars and widgets.

        .. note::

           If you're working with some other library that wraps :data:`sys.stdout`
           and :data:`sys.stderr`, such as colorama_, initialize it before Yuio.

    .. _colorama: https://github.com/tartley/colorama

    .. warning::

        This operation is not atomic. Call this function before creating new threads
        that use :mod:`yuio.io` or output streams to avoid race conditions.

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

    return _manager().term


def get_theme() -> yuio.theme.Theme:
    """
    Get the global instance of :class:`~yuio.theme.Theme`
    that is used with :mod:`yuio.io`.

    If global setup wasn't performed, this function implicitly performs it.

    :returns:
        Instance of :class:`~yuio.theme.Theme` that's used to format messages and tasks.

    """

    return _manager().theme


def make_repr_context(
    *,
    term: yuio.term.Term | None = None,
    to_stdout: bool = False,
    to_stderr: bool = False,
    theme: yuio.theme.Theme | None = None,
    multiline: bool = False,
    highlighted: bool = False,
    max_depth: int = 5,
    width: int | None = None,
) -> yuio.string.ReprContext:
    """
    Create new :class:`~yuio.string.ReprContext` for the given term and theme.

    :param term:
        terminal where to print this message. If not given, terminal from
        :func:`get_term` is used.
    :param to_stdout:
        shortcut for setting ``term`` to ``stdout``.
    :param to_stderr:
        shortcut for setting ``term`` to ``stderr``.
    :param theme:
        theme used to format the message. If not given, theme from
        :func:`get_theme` is used.
    :param multiline:
        sets initial value for :attr:`ReprContext.multiline`.
    :param highlighted:
        sets initial value for :attr:`ReprContext.highlighted`.
    :param max_depth:
        sets initial value for :attr:`ReprContext.max_depth`.
    :param width:
        sets initial value for :attr:`ReprContext.width`. If not given, uses current
        terminal width or :attr:`Theme.fallback_width` depending on whether
        `term` is attached to a TTY device.

    """

    if (term is not None) + to_stdout + to_stderr > 1:
        raise TypeError("term, to_stdout, to_stderr can't be given together")

    manager = _manager()

    theme = manager.theme
    if term is None:
        if to_stdout:
            term = manager.out_term
        elif to_stderr:
            term = manager.err_term
        else:
            term = manager.term
    if (
        width is None
        and term.ostream_interactive_support >= yuio.term.InteractiveSupport.BACKGROUND
    ):
        width = manager.rc.canvas_width

    return yuio.string.ReprContext(
        term=term,
        theme=theme,
        multiline=multiline,
        highlighted=highlighted,
        max_depth=max_depth,
        width=width,
    )


def wrap_streams():
    """
    Wrap :data:`sys.stdout` and :data:`sys.stderr` so that they honor
    Yuio tasks and widgets. If strings are already wrapped, this function
    has no effect.

    .. note::

        If you're working with some other library that wraps :data:`sys.stdout`
        and :data:`sys.stderr`, such as colorama_, initialize it before Yuio.

    .. seealso::

        :func:`setup`.

    .. _colorama: https://github.com/tartley/colorama

    """

    global _STREAMS_WRAPPED, _ORIG_STDOUT, _ORIG_STDERR

    if _STREAMS_WRAPPED:
        return

    with _IO_LOCK:
        if _STREAMS_WRAPPED:  # pragma: no cover
            return

        if yuio.term._output_is_tty(sys.stdout):
            _ORIG_STDOUT, sys.stdout = sys.stdout, _WrappedOutput(sys.stdout)
        if yuio.term._output_is_tty(sys.stderr):
            _ORIG_STDERR, sys.stderr = sys.stderr, _WrappedOutput(sys.stderr)
        _STREAMS_WRAPPED = True

        atexit.register(restore_streams)


def restore_streams():
    """
    Restore wrapped streams. If streams weren't wrapped, this function
    has no effect.

    .. seealso::

        :func:`wrap_streams`, :func:`setup`

    """

    global _STREAMS_WRAPPED

    if not _STREAMS_WRAPPED:
        return

    with _IO_LOCK:
        if not _STREAMS_WRAPPED:  # pragma: no cover
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
def info(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def info(msg: yuio.string.Colorable, /, **kwargs): ...
def info(msg: yuio.string.Colorable, /, *args, **kwargs):
    """info(msg: typing.LiteralString, /, *args, **kwargs)
    info(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print an info message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "info")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg, **kwargs)


@_t.overload
def warning(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def warning(msg: yuio.string.Colorable, /, **kwargs): ...
def warning(msg: yuio.string.Colorable, /, *args, **kwargs):
    """warning(msg: typing.LiteralString, /, *args, **kwargs)
    warning(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print a warning message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "warning")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg, **kwargs)


@_t.overload
def success(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def success(msg: yuio.string.Colorable, /, **kwargs): ...
def success(msg: yuio.string.Colorable, /, *args, **kwargs):
    """success(msg: typing.LiteralString, /, *args, **kwargs)
    success(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print a success message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "success")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg, **kwargs)


@_t.overload
def error(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def error(msg: yuio.string.Colorable, /, **kwargs): ...
def error(msg: yuio.string.Colorable, /, *args, **kwargs):
    """error(msg: typing.LiteralString, /, *args, **kwargs)
    error(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print an error message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "error")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg, **kwargs)


@_t.overload
def error_with_tb(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def error_with_tb(msg: yuio.string.Colorable, /, **kwargs): ...
def error_with_tb(msg: yuio.string.Colorable, /, *args, **kwargs):
    """error_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
    error_with_tb(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print an error message and capture the current exception.

    Call this function in the ``except`` clause of a ``try`` block
    or in an ``__exit__`` function of a context manager to attach
    current exception details to the log message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "error")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    kwargs.setdefault("exc_info", True)
    raw(msg, **kwargs)


@_t.overload
def failure(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def failure(msg: yuio.string.Colorable, /, **kwargs): ...
def failure(msg: yuio.string.Colorable, /, *args, **kwargs):
    """failure(msg: typing.LiteralString, /, *args, **kwargs)
    failure(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print a failure message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "failure")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg, **kwargs)


@_t.overload
def failure_with_tb(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def failure_with_tb(msg: yuio.string.Colorable, /, **kwargs): ...
def failure_with_tb(msg: yuio.string.Colorable, /, *args, **kwargs):
    """failure_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
    failure_with_tb(msg: ~yuio.string.Colorable, /, **kwargs) ->

    Print a failure message and capture the current exception.

    Call this function in the ``except`` clause of a ``try`` block
    or in an ``__exit__`` function of a context manager to attach
    current exception details to the log message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "failure")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    kwargs.setdefault("exc_info", True)
    raw(msg, **kwargs)


@_t.overload
def heading(msg: _t.LiteralString, /, *args, level: int = 1, **kwargs): ...
@_t.overload
def heading(msg: yuio.string.Colorable, /, *, level: int = 1, **kwargs): ...
def heading(msg: yuio.string.Colorable, /, *args, level: int = 1, **kwargs):
    """heading(msg: typing.LiteralString, /, *args, level: int = 1, **kwargs)
    heading(msg: ~yuio.string.Colorable, /, *, level: int = 1, **kwargs) ->

    Print a heading message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param level:
        level of the heading.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg = yuio.string._to_colorable(msg, args)
    level = kwargs.pop("level", 1)
    kwargs.setdefault("heading", True)
    kwargs.setdefault("tag", f"heading/{level}")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg, **kwargs)


@_t.overload
def md(
    msg: _t.LiteralString,
    /,
    *args,
    dedent: bool = True,
    allow_headings: bool = True,
    **kwargs,
): ...
@_t.overload
def md(msg: str, /, *, dedent: bool = True, allow_headings: bool = True, **kwargs): ...
def md(msg: str, /, *args, dedent: bool = True, allow_headings: bool = True, **kwargs):
    """md(msg: typing.LiteralString, /, *args, dedent: bool = True, allow_headings: bool = True, **kwargs)
    md(msg: str, /, *, dedent: bool = True, allow_headings: bool = True, **kwargs) ->

    Print a markdown-formatted text.

    Yuio supports all CommonMark block markup except tables. Inline markup is limited
    to backticks and color tags. See :mod:`yuio.md` for more info.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param dedent:
        whether to remove leading indent from markdown.
    :param allow_headings:
        whether to render headings as actual headings or as paragraphs.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(
        yuio.string.Md(msg, *args, dedent=dedent, allow_headings=allow_headings),
        **kwargs,
    )


def br(**kwargs):
    """
    Print an empty string.

    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    raw("\n", **kwargs)


@_t.overload
def hr(msg: _t.LiteralString = "", /, *args, weight: int | str = 1, **kwargs): ...
@_t.overload
def hr(msg: yuio.string.Colorable, /, *, weight: int | str = 1, **kwargs): ...
def hr(msg: yuio.string.Colorable = "", /, *args, weight: int | str = 1, **kwargs):
    """hr(msg: typing.LiteralString = "", /, *args, weight: int | str = 1, **kwargs)
    hr(msg: ~yuio.string.Colorable, /, *, weight: int | str = 1, **kwargs) ->

    Print a horizontal ruler.

    :param msg:
        message to print in the middle of the ruler.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param weight:
        weight or style of the ruler:

        -   ``0`` prints no ruler (but still prints centered text),
        -   ``1`` prints normal ruler,
        -   ``2`` prints bold ruler.

        Additional styles can be added through
        :attr:`Theme.msg_decorations <yuio.theme.Theme.msg_decorations>`.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(yuio.string.Hr(yuio.string._to_colorable(msg, args), weight=weight), **kwargs)


@_t.overload
def hl(
    msg: _t.LiteralString,
    /,
    *args,
    syntax: str | yuio.md.SyntaxHighlighter,
    dedent: bool = True,
    **kwargs,
): ...
@_t.overload
def hl(
    msg: str,
    /,
    *,
    syntax: str | yuio.md.SyntaxHighlighter,
    dedent: bool = True,
    **kwargs,
): ...
def hl(
    msg: str,
    /,
    *args,
    syntax: str | yuio.md.SyntaxHighlighter,
    dedent: bool = True,
    **kwargs,
):
    """hl(msg: typing.LiteralString, /, *args, syntax: str | yuio.md.SyntaxHighlighter, dedent: bool = True, **kwargs)
    hl(msg: str, /, *, syntax: str | yuio.md.SyntaxHighlighter, dedent: bool = True, **kwargs) ->

    Print highlighted code. See :mod:`yuio.md` for more info.

    :param msg:
        code to highlight.
    :param args:
        arguments for ``%``-formatting the highlighted code.
    :param syntax:
        name of syntax or a :class:`~yuio.md.SyntaxHighlighter` instance.
    :param dedent:
        whether to remove leading indent from code.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(yuio.string.Hl(msg, *args, syntax=syntax, dedent=dedent), **kwargs)


def raw(
    msg: yuio.string.Colorable,
    /,
    *,
    term: yuio.term.Term | None = None,
    to_stdout: bool = False,
    to_stderr: bool = False,
    theme: yuio.theme.Theme | None = None,
    ignore_suspended: bool = False,
    tag: str | None = None,
    exc_info: ExcInfo | bool | None = None,
    add_newline: bool = False,
    heading: bool = False,
    wrap: bool = False,
):
    """
    Print any :class:`~yuio.string.Colorable`.

    This is a bridge between :mod:`yuio.io` and lower-level
    modules like :mod:`yuio.string`.

    :param msg:
        message to print.
    :param term:
        terminal where to print this message. If not given, terminal from
        :func:`get_term` is used.
    :param to_stdout:
        shortcut for setting ``term`` to ``stdout``.
    :param to_stderr:
        shortcut for setting ``term`` to ``stderr``.
    :param theme:
        theme used to format the message. If not given, theme from
        :func:`get_theme` is used.
    :param ignore_suspended:
        whether to ignore :class:`SuspendOutput` context.
    :param tag:
        tag that will be used to add color and decoration to the message.

        Decoration is looked up by path :samp:`{tag}`
        (see :attr:`Theme.msg_decorations <yuio.theme.Theme.msg_decorations>`),
        and color is looked up by path :samp:`msg/text:{tag}`
        (see :attr:`Theme.colors <yuio.theme.Theme.colors>`).
    :param exc_info:
        either a boolean indicating that the current exception
        should be captured, or a tuple of three elements, as returned
        by :func:`sys.exc_info`.
    :param add_newline:
        adds newline after the message.
    :param heading:
        whether to separate message by extra newlines.

        If :data:`True`, adds extra newline after the message; if this is not the
        first message printed so far, adds another newline before the message.
    :param wrap:
        whether to wrap message before printing it.

    """

    if (term is not None) + to_stdout + to_stderr > 1:
        raise TypeError("term, to_stdout, to_stderr can't be given together")

    manager = _manager()

    ctx = make_repr_context(
        term=term, to_stdout=to_stdout, to_stderr=to_stderr, theme=theme
    )

    if tag and (decoration := ctx.get_msg_decoration(tag)):
        indent = yuio.string.ColorizedString(
            [ctx.get_color(f"msg/decoration:{tag}"), decoration]
        )
        continuation_indent = " " * indent.width
    else:
        indent = ""
        continuation_indent = ""

    if tag:
        msg = yuio.string.WithBaseColor(
            msg, base_color=ctx.get_color(f"msg/text:{tag}")
        )

    if wrap:
        msg = yuio.string.Wrap(
            msg,
            indent=indent,
            continuation_indent=continuation_indent,
        )
    elif indent or continuation_indent:
        msg = yuio.string.Indent(
            msg,
            indent=indent,
            continuation_indent=continuation_indent,
        )

    msg = ctx.str(msg)

    if add_newline:
        msg.append_color(yuio.color.Color.NONE)
        msg.append_str("\n")

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
        highlighter = yuio.md.SyntaxHighlighter.get_highlighter("python-traceback")
        msg += highlighter.highlight(ctx.theme, tb).indent()

    manager.print(
        msg.process_colors(ctx.term.color_support),
        ctx.term,
        ignore_suspended=ignore_suspended,
        heading=heading,
    )


class _AskWidget(yuio.widget.Widget[T], _t.Generic[T]):
    _layout: yuio.widget.VerticalLayout[T]

    def __init__(self, prompt: yuio.string.Colorable, widget: yuio.widget.Widget[T]):
        self._prompt = yuio.widget.Text(prompt)
        self._error: Exception | None = None
        self._inner = widget

    def event(self, e: yuio.widget.KeyboardEvent, /) -> yuio.widget.Result[T] | None:
        try:
            result = self._inner.event(e)
        except yuio.parse.ParsingError as err:
            self._error = err
        else:
            self._error = None
            return result

    def layout(self, rc: yuio.widget.RenderContext, /) -> tuple[int, int]:
        builder = (
            yuio.widget.VerticalLayoutBuilder()
            .add(self._prompt)
            .add(self._inner, receive_events=True)
        )
        if self._error is not None:
            rc.bell()
            error_msg = yuio.string.colorize(
                "<c msg/decoration:error>▲</c> %s",
                yuio.string.Indent(self._error, indent=0, continuation_indent=2),
                default_color="msg/text:error",
                ctx=rc.make_repr_context(),
            )
            builder = builder.add(yuio.widget.Text(error_msg))

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
    def __call__(
        cls: type[ask[S]],
        msg: _t.LiteralString,
        /,
        *args,
        default: M | yuio.Missing = yuio.MISSING,
        default_non_interactive: _t.Any = yuio.MISSING,
        parser: yuio.parse.Parser[S] | None = None,
        input_description: str | None = None,
        default_description: str | None = None,
    ) -> S | M: ...
    @_t.overload
    def __call__(
        cls: type[ask[S]],
        msg: str,
        /,
        *,
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
    """ask[T](msg: typing.LiteralString, /, *args, parser: ~yuio.parse.Parser[T] | None = None, default: U, default_non_interactive: U, input_description: str | None = None, default_description: str | None = None) -> T | U
    ask[T](msg: str, /, *, parser: ~yuio.parse.Parser[T] | None = None, default: U, default_non_interactive: U, input_description: str | None = None, default_description: str | None = None) -> T | U

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
                WARNING = ("Warning",)
                INFO = ("Info",)
                DEBUG = ("Debug",)


            answer = ask[Level]("Choose a logging level", default=Level.INFO)

    """


def _ask(
    msg: _t.LiteralString,
    /,
    *args,
    parser: yuio.parse.Parser[_t.Any],
    default: _t.Any = yuio.MISSING,
    default_non_interactive: _t.Any = yuio.MISSING,
    input_description: str | None = None,
    default_description: str | None = None,
) -> _t.Any:
    ctx = make_repr_context()

    if not ctx.term.can_query_user:
        if default_non_interactive is yuio.MISSING:
            default_non_interactive = default
        if default_non_interactive is yuio.MISSING:
            raise UserIoError("Can't interact with user in non-interactive environment")
        return default_non_interactive

    if default is None and not yuio.parse._is_optional_parser(parser):
        parser = yuio.parse.Optional(parser)

    msg = msg.rstrip()
    if msg.endswith(":"):
        needs_colon = True
        msg = msg[:-1]
    else:
        needs_colon = msg and msg[-1] not in string.punctuation

    base_color = ctx.get_color("msg/text:question")
    prompt = yuio.string.colorize(msg, *args, default_color=base_color, ctx=ctx)

    if not input_description:
        input_description = parser.describe()

    if default is not yuio.MISSING and default_description is None:
        try:
            default_description = parser.describe_value(default)
        except TypeError:
            default_description = str(default)

    if ctx.term.can_run_widgets:
        # Use widget.

        if needs_colon:
            prompt.append_color(base_color)
            prompt.append_str(":")

        if parser.is_secret():
            inner_widget = yuio.parse._secret_widget(
                parser, default, input_description, default_description
            )
        else:
            inner_widget = parser.widget(
                default, input_description, default_description
            )

        widget = _AskWidget(prompt, inner_widget)
        with SuspendOutput() as s:
            try:
                result = widget.run(ctx.term, ctx.theme)
            except (OSError, EOFError) as e:  # pragma: no cover
                raise UserIoError("Unexpected end of input") from e

            if result is yuio.MISSING:
                result = default

            try:
                result_desc = parser.describe_value(result)
            except TypeError:
                result_desc = str(result)

            prompt.append_color(base_color)
            prompt.append_str(" ")
            prompt.append_color(base_color | ctx.get_color("code"))
            prompt.append_str(result_desc)

            s.info(prompt, tag="question", term=ctx.term, theme=ctx.theme)
            return result
    else:
        # Use raw input.

        prompt += base_color
        if input_description:
            prompt += " ("
            prompt += input_description
            prompt += ")"
        if default_description:
            prompt += " ["
            prompt += base_color | ctx.get_color("code")
            prompt += default_description
            prompt += base_color
            prompt += "]"
        prompt += yuio.string.Esc(": " if needs_colon else " ")
        if parser.is_secret():
            do_input = _getpass
        else:
            do_input = _read
        with SuspendOutput() as s:
            while True:
                try:
                    answer = do_input(ctx.term, prompt)
                except (OSError, EOFError) as e:  # pragma: no cover
                    raise UserIoError("Unexpected end of input") from e
                if not answer and default is not yuio.MISSING:
                    return default
                elif not answer:
                    s.error("Input is required.", term=ctx.term, theme=ctx.theme)
                else:
                    try:
                        return parser.parse(answer)
                    except yuio.parse.ParsingError as e:
                        s.error(e, term=ctx.term, theme=ctx.theme)


def _read(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
    info(prompt, add_newline=False, tag="question", term=term, ignore_suspended=True)
    return term.istream.readline().rstrip("\r\n")


def _getpass_fallback(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
    warning("Warning: Password input may be echoed.", term=term, ignore_suspended=True)
    return _read(term, prompt)


if os.name == "posix":
    # Getpass implementation is based on the standard `getpass` module, with a few
    # Yuio-specific modifications.

    def _getpass(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
        import termios

        try:
            fd = term.istream.fileno()
        except (AttributeError, ValueError):
            # We can't control the tty or stdin. Give up and use normal IO.
            return _getpass_fallback(term, prompt)

        result: str | None = None

        try:
            prev_mode = termios.tcgetattr(fd)
            new_mode = prev_mode.copy()
            new_mode[3] &= ~termios.ECHO
            tcsetattr_flags = termios.TCSAFLUSH | getattr(termios, "TCSASOFT", 0)
            try:
                termios.tcsetattr(fd, tcsetattr_flags, new_mode)
                info(
                    prompt,
                    add_newline=False,
                    tag="question",
                    term=term,
                    ignore_suspended=True,
                )
                result = term.istream.readline().rstrip("\r\n")
                term.ostream.write("\n")
                term.ostream.flush()
            finally:
                termios.tcsetattr(fd, tcsetattr_flags, prev_mode)
        except termios.error:
            if result is not None:
                # `readline` succeeded, the final `tcsetattr` failed. Reraise instead
                # of leaving the terminal in an unknown state.
                raise
            else:
                # We can't control the tty or stdin. Give up and use normal IO.
                return _getpass_fallback(term, prompt)

        assert result is not None
        return result

elif os.name == "nt":

    def _getpass(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
        import msvcrt

        info(
            prompt, add_newline=False, tag="question", term=term, ignore_suspended=True
        )

        result = ""
        while 1:
            c = msvcrt.getwch()
            if c == "\0" or c == "\xe0":
                # Read key scan code and ignore it.
                msvcrt.getwch()
                continue
            if c == "\r" or c == "\n":
                break
            if c == "\x03":
                raise KeyboardInterrupt
            if c == "\b":
                if result:
                    msvcrt.putwch("\b")
                    msvcrt.putwch(" ")
                    msvcrt.putwch("\b")
                    result = result[:-1]
            else:
                result = result + c
                msvcrt.putwch("*")
        msvcrt.putwch("\r")
        msvcrt.putwch("\n")

        return result

else:
    _getpass = _getpass_fallback  # pragma: no cover


class _WaitForUserWidget(yuio.widget.Widget[None]):
    def __init__(self, prompt: yuio.string.Colorable):
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
    msg: _t.LiteralString = "Press <c note>enter</c> to continue",
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

    ctx = make_repr_context()

    if not ctx.term.can_query_user:
        return

    prompt = yuio.string.colorize(
        msg.rstrip(), *args, default_color="msg/text:question", ctx=ctx
    )
    prompt += yuio.string.Esc(" ")

    with SuspendOutput() as s:
        try:
            if ctx.term.can_run_widgets:
                _WaitForUserWidget(prompt).run(ctx.term, ctx.theme)
            else:
                s.info(prompt, add_newline=False, tag="question")
                ctx.term.istream.readline()
        except (OSError, EOFError):  # pragma: no cover
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
        if editor := os.environ.get("EDITOR"):
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
        overrides editor.

        On unix, this should be a shell command, file path will be appended to it;
        on windows, this should be an executable path.
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

            message = edit(
                \"""
                    # Please enter the commit message for your changes. Lines starting
                    # with '#' will be ignored, and an empty message aborts the commit.
                \""",
                comment_marker="#",
                dedent=True,
            )

    """

    if dedent:
        text = _dedent(text)

    manager = _manager()
    term = manager.term

    if term.can_run_widgets:
        if editor is None:
            editor = detect_editor(fallbacks)

        if editor is None:
            if os.name == "nt":
                raise UserIoError("Can't find a usable editor")
            else:
                raise UserIoError(
                    "Can't find a usable editor. Ensure that `$VISUAL` and `$EDITOR` "
                    "environment variables contain correct path to an editor executable"
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
                    "Can't use editor `%r`: no such file or directory",
                    editor,
                )

            if res.returncode != 0:
                if res.returncode < 0:
                    import signal

                    try:
                        action = "died with"
                        code = signal.Signals(-res.returncode).name
                    except ValueError:
                        action = "died with unknown signal"
                        code = res.returncode
                else:
                    action = "returned exit code"
                    code = res.returncode
                raise UserIoError(
                    "Editing failed: editor `%r` %s `%s`",
                    editor,
                    action,
                    code,
                )

            if not os.path.exists(filepath):
                raise UserIoError("Editing failed: can't read back edited file")
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
    def info(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def info(self, err: yuio.string.Colorable, /, **kwargs): ...
    def info(self, msg: yuio.string.Colorable, /, *args, **kwargs):
        """info(msg: typing.LiteralString, /, *args, **kwargs)
        info(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log an :func:`info` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        info(msg, *args, **kwargs)

    @_t.overload
    def warning(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def warning(self, err: yuio.string.Colorable, /, **kwargs): ...
    def warning(self, msg: yuio.string.Colorable, /, *args, **kwargs):
        """warning(msg: typing.LiteralString, /, *args, **kwargs)
        warning(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log a :func:`warning` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        warning(msg, *args, **kwargs)

    @_t.overload
    def success(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def success(self, err: yuio.string.Colorable, /, **kwargs): ...
    def success(self, msg: yuio.string.Colorable, /, *args, **kwargs):
        """success(msg: typing.LiteralString, /, *args, **kwargs)
        success(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log a :func:`success` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        success(msg, *args, **kwargs)

    @_t.overload
    def error(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def error(self, err: yuio.string.Colorable, /, **kwargs): ...
    def error(self, msg: yuio.string.Colorable, /, *args, **kwargs):
        """error(msg: typing.LiteralString, /, *args, **kwargs)
        error(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log an :func:`error` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        error(msg, *args, **kwargs)

    @_t.overload
    def error_with_tb(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ): ...
    @_t.overload
    def error_with_tb(
        self,
        msg: yuio.string.Colorable,
        /,
        *,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ): ...
    def error_with_tb(
        self,
        msg: yuio.string.Colorable,
        /,
        *args,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ):
        """error_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
        error_with_tb(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log an :func:`error_with_tb` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        error_with_tb(msg, *args, **kwargs)

    @_t.overload
    def failure(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def failure(self, err: yuio.string.Colorable, /, **kwargs): ...
    def failure(self, msg: yuio.string.Colorable, /, *args, **kwargs):
        """failure(msg: typing.LiteralString, /, *args, **kwargs)
        failure(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log a :func:`failure` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        failure(msg, *args, **kwargs)

    @_t.overload
    def failure_with_tb(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ): ...
    @_t.overload
    def failure_with_tb(
        self,
        msg: yuio.string.Colorable,
        /,
        *,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ): ...
    def failure_with_tb(
        self,
        msg: yuio.string.Colorable,
        /,
        *args,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ):
        """failure_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
        failure_with_tb(msg: ~yuio.string.Colorable, /, **kwargs) ->

        Log a :func:`failure_with_tb` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        failure_with_tb(msg, *args, **kwargs)

    @_t.overload
    def heading(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def heading(self, msg: yuio.string.Colorable, /, **kwargs): ...
    def heading(self, msg: yuio.string.Colorable, /, *args, **kwargs):
        """heading(msg: typing.LiteralString, /, *args, **kwargs)
        heading(msg: ~yuio.string.Colorable, /, **kwargs)

        Log a :func:`heading` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        heading(msg, *args, **kwargs)

    @_t.overload
    def md(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def md(self, msg: str, /, **kwargs): ...
    def md(self, msg: str, /, *args, **kwargs):
        """md(msg: typing.LiteralString, /, *args, dedent: bool = True, allow_headings: bool = True, **kwargs)
        md(msg: str, /, *, dedent: bool = True, allow_headings: bool = True, **kwargs)

        Log an :func:`md` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        md(msg, *args, **kwargs)

    def br(self, **kwargs):
        """br()

        Log a :func:`br` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        br(**kwargs)

    @_t.overload
    def hl(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def hl(self, msg: str, /, **kwargs): ...
    def hl(self, msg: str, /, *args, **kwargs):
        """hl(msg: typing.LiteralString, /, *args, syntax: str | yuio.md.SyntaxHighlighter, dedent: bool = True, **kwargs)
        hl(msg: str, /, *, syntax: str | yuio.md.SyntaxHighlighter, dedent: bool = True, **kwargs)

        Log an :func:`hl` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        hl(msg, *args, **kwargs)

    @_t.overload
    def hr(self, msg: _t.LiteralString = "", /, *args, **kwargs): ...
    @_t.overload
    def hr(self, msg: yuio.string.Colorable, /, **kwargs): ...
    def hr(self, msg: yuio.string.Colorable = "", /, *args, **kwargs):
        """hr(msg: typing.LiteralString = "", /, *args, weight: int | str = 1, **kwargs)
        hr(msg: ~yuio.string.Colorable, /, *, weight: int | str = 1, **kwargs) ->

        Log an :func:`hr` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        hr(msg, *args, **kwargs)

    def raw(self, msg: yuio.string.Colorable, /, **kwargs):
        """
        Log a :func:`raw` message, ignore suspended status.

        """

        kwargs.setdefault("ignore_suspended", True)
        raw(msg, **kwargs)

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
    """Task(msg: typing.LiteralString, /, *args, comment: str | None = None)
    Task(msg: str, /, *, comment: str | None = None)

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

        with Task("Processing input") as t:
            ...
            t.progress(0.3)
            ...

    """

    class _Status(enum.Enum):
        DONE = "done"
        ERROR = "error"
        RUNNING = "running"

    @_t.overload
    def __init__(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        comment: str | None = None,
    ): ...
    @_t.overload
    def __init__(
        self,
        msg: str,
        /,
        *,
        comment: str | None = None,
    ): ...
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

        self._cached_msg: yuio.string.ColorizedString | None = None
        self._cached_comment: yuio.string.ColorizedString | None = None

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
        """progress(progress: float | None, /, *, ndigits: int = 2)
        progress(done: float | int, total: float | int, /, *, unit: str = "", ndigits: int = 0) ->

        Indicate progress of this task.

        If given one argument, it is treated as percentage between ``0`` and ``1``.

        If given two arguments, they are treated as amount of finished work,
        and a total amount of work. In this case, optional argument ``unit``
        can be used to indicate units for the progress.

        If given a single :data:`None`, reset task progress.

        .. note::

            Tasks are updated asynchronously once every ~100ms, so calling this method
            is relatively cheap. It still requires acquiring a global lock, though.

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
                    task.progress_scale(889.25e-3, 1, unit="V")

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
            return n * 10 ** -(3 * magnitude), "munpfazy"[-magnitude - 1]
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

                with Task("Fetching data") as t:
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

                with Task("Fetching data") as t:
                    for url in urls:
                        t.comment("%s", url)
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

    @_t.overload
    def subtask(
        self, msg: _t.LiteralString, /, *args, comment: str | None = None
    ) -> Task: ...
    @_t.overload
    def subtask(self, msg: str, /, *, comment: str | None = None) -> Task: ...
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

        return Task(msg, *args, comment=comment, **{"_parent": self})

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done()
        else:
            self.error()


class Formatter(logging.Formatter):
    """
    Log formatter that uses ``%`` style with colorized string formatting
    and returns a string with ANSI escape characters generated for current
    output terminal.

    Every part of log message is colored with path :samp:`log/{name}:{level}`.
    For example, ``asctime`` in info log line is colored
    with path ``log/asctime:info``.

    In addition to the usual `log record attributes`__, this formatter also
    adds ``%(colMessage)s``, which is similar to ``%(message)s``, but colorized.

    __ https://docs.python.org/3/library/logging.html#logrecord-attributes

    """

    default_format = "%(asctime)s %(name)s %(levelname)s %(colMessage)s"
    default_msec_format = "%s.%03d"

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        validate: bool = True,
        *,
        defaults: _t.Mapping[str, _t.Any] | None = None,
    ):
        fmt = fmt or self.default_format
        super().__init__(
            fmt,
            datefmt,
            style="%",
            validate=validate,
            defaults=defaults,
        )

    def formatMessage(self, record):
        level = record.levelname.lower()

        ctx = make_repr_context()

        if not hasattr(record, "colMessage"):
            msg = str(record.msg)
            if record.args:
                msg = ColorizedString(msg).percent_format(record.args, ctx)
            setattr(record, "colMessage", msg)

        if defaults := self._style._defaults:  # type: ignore
            data = defaults | record.__dict__
        else:
            data = record.__dict__

        data = {
            k: yuio.string.WithBaseColor(v, base_color=f"log/{k}:{level}")
            for k, v in data.items()
        }

        return "".join(
            yuio.string.colorize(
                self._fmt or self.default_format, default_color=f"log:{level}", ctx=ctx
            )
            .percent_format(data, ctx)
            .process_colors(ctx.term.color_support)
        )

    def formatException(self, ei):
        tb = "".join(traceback.format_exception(*ei)).rstrip()
        return self.formatStack(tb)

    def formatStack(self, stack_info):
        manager = _manager()
        theme = manager.theme
        term = manager.term
        highlighter = yuio.md.SyntaxHighlighter.get_highlighter("python-traceback")
        return "".join(
            highlighter.highlight(theme, stack_info)
            .indent()
            .process_colors(term.color_support)
        )


class Handler(logging.Handler):
    """
    A handler that redirects all log messages to Yuio.

    """

    def __init__(self, level: int | str = 0):
        super().__init__(level)
        self.setFormatter(Formatter())

    def emit(self, record: LogRecord):
        manager = _manager()
        manager.print_direct(self.format(record).rstrip() + "\n", manager.term.ostream)


class _IoManager(abc.ABC):
    def __init__(
        self,
        term: yuio.term.Term | None = None,
        theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = None,
        enable_bg_updates: bool = True,
    ):
        self._out_term = yuio.term.get_term_from_stream(
            orig_stdout(), sys.stdin, query_terminal_theme=False
        )
        self._err_term = yuio.term.get_term_from_stream(
            orig_stderr(), sys.stdin, query_terminal_theme=False
        )

        self._term = term or yuio.term.get_term_from_stream(orig_stderr(), sys.stdin)

        self._theme_ctor = theme
        if isinstance(theme, yuio.theme.Theme):
            self._theme = theme
        else:
            self._theme = yuio.theme.load(self._term, theme)
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

    @property
    def term(self):
        return self._term

    @property
    def out_term(self):
        return self._out_term

    @property
    def err_term(self):
        return self._err_term

    @property
    def theme(self):
        return self._theme

    @property
    def rc(self):
        return self._rc

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
                if theme is None:
                    # Refresh theme to reflect changed terminal capabilities.
                    theme = self._theme_ctor
            if theme is not None:
                self._theme_ctor = theme
                if isinstance(theme, yuio.theme.Theme):
                    self._theme = theme
                else:
                    self._theme = yuio.theme.load(self._term, theme)

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

    def print(
        self,
        msg: list[str],
        term: yuio.term.Term,
        *,
        ignore_suspended: bool = False,
        heading: bool = False,
    ):
        with _IO_LOCK:
            if heading and self.theme.separate_headings:
                if self._printed_some_lines:
                    msg.insert(0, "\n")
                msg.append("\n")
            self._emit_lines(msg, term.ostream, ignore_suspended)
            if heading:
                self._printed_some_lines = False

    def print_direct(
        self,
        msg: str,
        stream: _t.TextIO | None = None,
    ):
        with _IO_LOCK:
            self._emit_lines([msg], stream, ignore_suspended=False)

    def print_direct_lines(
        self,
        lines: _t.Iterable[str],
        stream: _t.TextIO | None = None,
    ):
        with _IO_LOCK:
            self._emit_lines(lines, stream, ignore_suspended=False)

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
        while update_rate_ms > 250:
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
            yuio._logger.warning("unequal number of suspends and resumes")
            self._suspended = 0

    def _start_task(self, task: Task):
        if self._term.can_render_widgets:
            self._tasks.append(task)
            self._update_tasks()
        else:
            self._emit_lines(
                self._format_task(task).process_colors(self._term.color_support)
            )

    def _start_subtask(self, parent: Task, task: Task):
        if self._term.can_render_widgets:
            parent._subtasks.append(task)
            self._update_tasks()
        else:
            self._emit_lines(
                self._format_task(task).process_colors(self._term.color_support)
            )

    def _finish_task(self, task: Task, status: Task._Status):
        if task._status != Task._Status.RUNNING:
            yuio._logger.warning("trying to change status of an already stopped task")
            return

        task._status = status
        for subtask in task._subtasks:
            if subtask._status == Task._Status.RUNNING:
                self._finish_task(subtask, status)

        if self._term.can_render_widgets:
            if task in self._tasks:
                self._tasks.remove(task)
                self._emit_lines(
                    self._format_task(task).process_colors(self._term.color_support)
                )
            else:
                self._update_tasks()
        else:
            self._emit_lines(
                self._format_task(task).process_colors(self._term.color_support)
            )

    def _clear_tasks(self):
        if self._term.can_render_widgets and self._tasks_printed:
            self._rc.finalize()
            self._tasks_printed = 0

    def _update_tasks(self, immediate_render: bool = False):
        self._needs_update = True
        if immediate_render or not self._enable_bg_updates:
            self._show_tasks(immediate_render)

    def _show_tasks(self, immediate_render: bool = False):
        if (
            self._term.can_render_widgets
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

    def _format_task(self, task: Task) -> yuio.string.ColorizedString:
        res = yuio.string.ColorizedString()

        ctx = task._status.value

        if decoration := self._theme.get_msg_decoration(
            "task", is_unicode=self._term.is_unicode
        ):
            res += self._theme.get_color(f"task/decoration:{ctx}")
            res += decoration

        res += self._format_task_msg(task)
        res += self._theme.get_color(f"task:{ctx}")
        res += " - "
        res += self._theme.get_color(f"task/progress:{ctx}")
        res += task._status.value
        res += self._theme.get_color(f"task:{ctx}")
        res += "\n"

        res += yuio.color.Color.NONE

        return res

    def _format_task_msg(self, task: Task) -> yuio.string.ColorizedString:
        if task._cached_msg is None:
            msg = yuio.string.colorize(
                task._msg,
                *task._args,
                default_color=f"task/heading:{task._status.value}",
                ctx=yuio.string.ReprContext(
                    term=self._term,
                    theme=self._theme,
                    width=self._rc.width,
                ),
            )
            task._cached_msg = msg
        return task._cached_msg

    def _format_task_comment(self, task: Task) -> yuio.string.ColorizedString | None:
        if task._status is not Task._Status.RUNNING:
            return None
        if task._cached_comment is None and task._comment is not None:
            comment = yuio.string.colorize(
                task._comment,
                *(task._comment_args or ()),
                default_color=f"task/comment:{task._status.value}",
                ctx=yuio.string.ReprContext(
                    term=self._term,
                    theme=self._theme,
                    width=self._rc.width,
                ),
            )
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
        progress_bar_start_symbol = self._theme.get_msg_decoration(
            "progress_bar/start_symbol", is_unicode=self._term.is_unicode
        )
        progress_bar_end_symbol = self._theme.get_msg_decoration(
            "progress_bar/end_symbol", is_unicode=self._term.is_unicode
        )
        total_width = (
            self._theme.progress_bar_width
            - yuio.string.line_width(progress_bar_start_symbol)
            - yuio.string.line_width(progress_bar_end_symbol)
        )
        progress_bar_done_symbol = self._theme.get_msg_decoration(
            "progress_bar/done_symbol", is_unicode=self._term.is_unicode
        )
        progress_bar_pending_symbol = self._theme.get_msg_decoration(
            "progress_bar/pending_symbol", is_unicode=self._term.is_unicode
        )
        if task._status != Task._Status.RUNNING:
            self._rc.set_color_path(f"task/decoration:{task._status.value}")
            self._rc.write(
                self._theme.get_msg_decoration(
                    "spinner/static_symbol", is_unicode=self._term.is_unicode
                )
            )
        elif (
            task._progress is None
            or total_width <= 1
            or not progress_bar_done_symbol
            or not progress_bar_pending_symbol
        ):
            self._rc.set_color_path(f"task/decoration:{task._status.value}")
            spinner_pattern = self._theme.get_msg_decoration(
                "spinner/pattern", is_unicode=self._term.is_unicode
            )
            if spinner_pattern:
                self._rc.write(
                    spinner_pattern[self._spinner_state % len(spinner_pattern)]
                )
        else:
            transition_pattern = self._theme.get_msg_decoration(
                "progress_bar/transition_pattern", is_unicode=self._term.is_unicode
            )

            progress = max(0, min(1, task._progress))
            if transition_pattern:
                done_width = int(total_width * progress)
                transition_factor = 1 - (total_width * progress - done_width)
                transition_width = 1
            else:
                done_width = round(total_width * progress)
                transition_factor = 0
                transition_width = 0

            self._rc.set_color_path(f"task/progressbar:{task._status.value}")
            self._rc.write(progress_bar_start_symbol)

            done_color = yuio.color.Color.lerp(
                self._theme.get_color("task/progressbar/done/start"),
                self._theme.get_color("task/progressbar/done/end"),
            )

            for i in range(0, done_width):
                self._rc.set_color(done_color(i / (total_width - 1)))
                self._rc.write(progress_bar_done_symbol)

            if transition_pattern and done_width < total_width:
                self._rc.set_color(done_color(done_width / (total_width - 1)))
                self._rc.write(
                    transition_pattern[
                        int(len(transition_pattern) * transition_factor - 1)
                    ]
                )

            pending_color = yuio.color.Color.lerp(
                self._theme.get_color("task/progressbar/pending/start"),
                self._theme.get_color("task/progressbar/pending/end"),
            )

            for i in range(done_width + transition_width, total_width):
                self._rc.set_color(pending_color(i / (total_width - 1)))
                self._rc.write(progress_bar_pending_symbol)

            self._rc.set_color_path(f"task/progressbar:{task._status.value}")
            self._rc.write(progress_bar_end_symbol)

        self._rc.set_color_path(f"task:{task._status.value}")
        self._rc.write(" ")


class _WrappedOutput(_t.TextIO):  # pragma: no cover
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
