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

- :cli:env:`FORCE_NO_COLOR`: disable colored output,
- :cli:env:`FORCE_COLOR`: enable colored output.

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
:ref:`color tags <color-tags>` and formatted using either
:ref:`%-formatting or template strings <percent-format>`.

.. autofunction:: info

.. autofunction:: warning

.. autofunction:: success

.. autofunction:: failure

.. autofunction:: failure_with_tb

.. autofunction:: error

.. autofunction:: error_with_tb

.. autofunction:: heading

.. autofunction:: md

.. autofunction:: rst

.. autofunction:: hl

.. autofunction:: br

.. autofunction:: hr

.. autofunction:: raw


.. _percent-format:

Formatting the output
---------------------

Yuio supports `printf-style formatting`__, similar to :mod:`logging`. If you're using
Python 3.14 or later, you can also use `template strings`__.

__ https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
__ https://docs.python.org/3/library/string.html#template-strings

.. invisible-code-block: python

    config = ...

.. tab-set::
    :sync-group: formatting-method

    .. tab-item:: Printf-style formatting
        :sync: printf

        ``%s`` and ``%r`` specifiers are handled to respect colors and `rich repr protocol`__.
        Additionally, they allow specifying flags to control whether rendered values should
        be highlighted, and should they be rendered in multiple lines:

        __ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

        -   ``#`` enables colors in repr (i.e. ``%#r``);
        -   ``+`` splits repr into multiple lines (i.e. ``%+r``, ``%#+r``).

        .. code-block:: python

            yuio.io.info("Loaded config: %#+r", config)

    .. tab-item:: Template strings
        :sync: template

        When formatting template strings, default format specification is extended
        to respect colors and `rich repr protocol`__. Additionally, it allows
        specifying flags to control whether rendered values should be highlighted,
        and should they be rendered in multiple lines:

        __ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol

        -   ``#`` enables colors in repr (i.e. ``{var:#}``);
        -   ``+`` splits repr into multiple lines (i.e. ``{var:+}``, ``{var:#+}``);
        -   unless explicit conversion is given (i.e. ``!s``, ``!r``, or ``!a``),
            this format specification applies to objects that don't define
            custom ``__format__`` method;
        -   full format specification is available :ref:`here <t-string-spec>`.

        .. code-block:: python

            yuio.io.info(t"Loaded config: {config!r:#+}")

        .. note::

            The formatting algorithm is as follows:

            1.  if formatting conversion is specified (i.e. ``!s``, ``!r``, or ``!a``),
                the object is passed to
                :meth:`ReprContext.convert() <yuio.string.ReprContext.convert>`;
            2.  otherwise, if object defines custom ``__format__`` method,
                this method is used;
            3.  otherwise, we fall back to
                :meth:`ReprContext.convert() <yuio.string.ReprContext.convert>`
                with assumed conversion flag ``"s"``.

To support highlighted formatting, define ``__colorized_str__``
or ``__colorized_repr__`` on your class. See :ref:`pretty-protocol` for implementation
details.

To support rich repr protocol, define function ``__rich_repr__`` on your class.
This method should return an iterable of tuples, as described in Rich__ documentation.

__ https://rich.readthedocs.io/en/stable/pretty.html#rich-repr-protocol


.. _color-tags:

Coloring the output
-------------------

By default, all messages are colored according to their level (i.e. which function
you use to print them).

If you need inline colors, you can use special tags in your log messages:

.. code-block:: python

    yuio.io.info("Using the <c code>code</c> tag.")

You can combine multiple colors in the same tag:

.. code-block:: python

    yuio.io.info("<c bold green>Success!</c>")

Only tags that appear in the message itself are processed:

.. tab-set::
    :sync-group: formatting-method

    .. tab-item:: Printf-style formatting
        :sync: printf

        .. code-block:: python

            yuio.io.info("Tags in this message --> %s are printed as-is", "<c color>")

    .. tab-item:: Template strings
        :sync: template

        .. code-block:: python

            value = "<c color>"
            yuio.io.info(t"Tags in this message --> {value} are printed as-is")

For highlighting inline code, Yuio supports parsing CommonMark's backticks:

.. code-block:: python

    yuio.io.info("Using the `backticks`.")
    yuio.io.info("Using the `` nested `backticks` ``")

Any punctuation symbol can be escaped with backslash:

.. code-block:: python

    yuio.io.info("\\`\\<c red> this is normal text \\</c>\\`.")

See full list of tags in :ref:`yuio.theme <common-tags>`.


Message channels
----------------

.. autoclass:: MessageChannel
    :members:


Formatting utilities
--------------------

There are several :ref:`formatting utilities <formatting-utilities>` defined
in :mod:`yuio.string` and re-exported in :mod:`yuio.io`. These utilities
perform various formatting tasks when converted to strings, allowing you to lazily
build more complex messages.


Indicating progress
-------------------

You can use the :class:`Task` class to indicate status and progress
of some task.

.. autoclass:: TaskBase
    :members:

.. autoclass:: Task
    :members:


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
    :members:


Python's `logging` and yuio
---------------------------

If you want to direct messages from the :mod:`logging` to Yuio,
you can add a :class:`Handler`:

.. autoclass:: Handler

.. autoclass:: Formatter


Helpers
-------

.. autofunction:: make_repr_context

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

.. type:: Rst
    :no-index:

    Alias of :obj:`yuio.string.Rst`.

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
import functools
import logging
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
import yuio.hl
import yuio.parse
import yuio.string
import yuio.term
import yuio.theme
import yuio.widget
from yuio._dist.dsu import DisjointSet as _DisjointSet
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
    Rst,
    Stack,
    TypeRepr,
    WithBaseColor,
    Wrap,
)
from yuio.util import dedent as _dedent

import yuio._typing_ext as _tx
from typing import TYPE_CHECKING
from typing import ClassVar as _ClassVar

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

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
    "MessageChannel",
    "Or",
    "Repr",
    "Rst",
    "Stack",
    "SuspendOutput",
    "Task",
    "TaskBase",
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
    "rst",
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


_IO_LOCK = threading.RLock()
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
    multiline: bool | None = None,
    highlighted: bool | None = None,
    max_depth: int | None = None,
    width: int | None = None,
) -> yuio.string.ReprContext:
    """
    Create new :class:`~yuio.string.ReprContext` for the given term and theme.

    .. warning::

        :class:`~yuio.string.ReprContext`\\ s are not thread safe. As such,
        you shouldn't create them for long term use.

    :param term:
        terminal where to print this message. If not given, terminal from
        :func:`get_term` is used.
    :param to_stdout:
        shortcut for setting `term` to ``stdout``.
    :param to_stderr:
        shortcut for setting `term` to ``stderr``.
    :param theme:
        theme used to format the message. If not given, theme from
        :func:`get_theme` is used.
    :param multiline:
        sets initial value for
        :attr:`ReprContext.multiline <yuio.string.ReprContext.multiline>`.
        Default is :data:`False`.
    :param highlighted:
        sets initial value for
        :attr:`ReprContext.highlighted <yuio.string.ReprContext.highlighted>`.
        Default is :data:`False`.
    :param max_depth:
        sets initial value for
        :attr:`ReprContext.max_depth <yuio.string.ReprContext.max_depth>`.
        Default is :data:`False`.
    :param width:
        sets initial value for
        :attr:`ReprContext.width <yuio.string.ReprContext.width>`.
        If not given, uses current terminal width or
        :attr:`Theme.fallback_width <yuio.theme.Theme.fallback_width>`
        depending on whether `term` is attached to a TTY device and whether colors
        are supported by the target terminal.

    """

    if (term is not None) + to_stdout + to_stderr > 1:
        names = []
        if term is not None:
            names.append("term")
        if to_stdout:
            names.append("to_stdout")
        if to_stderr:
            names.append("to_stderr")
        raise TypeError(f"{And(names)} can't be given together")

    manager = _manager()

    theme = manager.theme
    if term is None:
        if to_stdout:
            term = manager.out_term
        elif to_stderr:
            term = manager.err_term
        else:
            term = manager.term
    if width is None and (term.ostream_is_tty or term.supports_colors):
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
            _ORIG_STDOUT, sys.stdout = sys.stdout, _YuioOutputWrapper(sys.stdout)
        if yuio.term._output_is_tty(sys.stderr):
            _ORIG_STDERR, sys.stderr = sys.stderr, _YuioOutputWrapper(sys.stderr)
        _STREAMS_WRAPPED = True

        atexit.register(restore_streams)


def restore_streams():
    """
    Restore wrapped streams. If streams weren't wrapped, this function
    has no effect.

    .. seealso::

        :func:`wrap_streams`, :func:`setup`

    """

    global _STREAMS_WRAPPED, _ORIG_STDOUT, _ORIG_STDERR

    if not _STREAMS_WRAPPED:
        return

    with _IO_LOCK:
        if not _STREAMS_WRAPPED:  # pragma: no cover
            return

        if _ORIG_STDOUT is not None:
            sys.stdout = _ORIG_STDOUT
            _ORIG_STDOUT = None
        if _ORIG_STDERR is not None:
            sys.stderr = _ORIG_STDERR
            _ORIG_STDERR = None
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
def info(msg: yuio.string.ToColorable, /, **kwargs): ...
def info(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """info(msg: typing.LiteralString, /, *args, **kwargs)
    info(msg: ~string.templatelib.Template, /, **kwargs) ->
    info(msg: ~yuio.string.ToColorable, /, **kwargs) ->

    Print an info message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "info")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def warning(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def warning(msg: yuio.string.ToColorable, /, **kwargs): ...
def warning(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """warning(msg: typing.LiteralString, /, *args, **kwargs)
    warning(msg: ~string.templatelib.Template, /, **kwargs) ->
    warning(msg: ~yuio.string.ToColorable, /, **kwargs) ->

    Print a warning message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "warning")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def success(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def success(msg: yuio.string.ToColorable, /, **kwargs): ...
def success(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """success(msg: typing.LiteralString, /, *args, **kwargs)
    success(msg: ~string.templatelib.Template, /, **kwargs) ->
    success(msg: ~yuio.string.ToColorable, /, **kwargs) ->

    Print a success message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "success")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def error(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def error(msg: yuio.string.ToColorable, /, **kwargs): ...
def error(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """error(msg: typing.LiteralString, /, *args, **kwargs)
    error(msg: ~string.templatelib.Template, /, **kwargs) ->
    error(msg: ~yuio.string.ToColorable, /, **kwargs) ->

    Print an error message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "error")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def error_with_tb(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def error_with_tb(msg: yuio.string.ToColorable, /, **kwargs): ...
def error_with_tb(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """error_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
    error_with_tb(msg: ~string.templatelib.Template, /, **kwargs) ->
    error_with_tb(msg: ~yuio.string.ToColorable, /, **kwargs) ->

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

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "error")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    kwargs.setdefault("exc_info", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def failure(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def failure(msg: yuio.string.ToColorable, /, **kwargs): ...
def failure(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """failure(msg: typing.LiteralString, /, *args, **kwargs)
    failure(msg: ~string.templatelib.Template, /, **kwargs) ->
    failure(msg: ~yuio.string.ToColorable, /, **kwargs) ->

    Print a failure message.

    :param msg:
        message to print.
    :param args:
        arguments for ``%``\\ -formatting the message.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "failure")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def failure_with_tb(msg: _t.LiteralString, /, *args, **kwargs): ...
@_t.overload
def failure_with_tb(msg: yuio.string.ToColorable, /, **kwargs): ...
def failure_with_tb(msg: yuio.string.ToColorable, /, *args, **kwargs):
    """failure_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
    failure_with_tb(msg: ~string.templatelib.Template, /, **kwargs) ->
    failure_with_tb(msg: ~yuio.string.ToColorable, /, **kwargs) ->

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

    msg_colorable = yuio.string._to_colorable(msg, args)
    kwargs.setdefault("tag", "failure")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    kwargs.setdefault("exc_info", True)
    raw(msg_colorable, **kwargs)


@_t.overload
def heading(msg: _t.LiteralString, /, *args, level: int = 1, **kwargs): ...
@_t.overload
def heading(msg: yuio.string.ToColorable, /, *, level: int = 1, **kwargs): ...
def heading(msg: yuio.string.ToColorable, /, *args, level: int = 1, **kwargs):
    """heading(msg: typing.LiteralString, /, *args, level: int = 1, **kwargs)
    heading(msg: ~string.templatelib.Template, /, *, level: int = 1, **kwargs) ->
    heading(msg: ~yuio.string.ToColorable, /, *, level: int = 1, **kwargs) ->

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

    msg_colorable = yuio.string._to_colorable(msg, args)
    level = kwargs.pop("level", 1)
    kwargs.setdefault("heading", True)
    kwargs.setdefault("tag", f"heading/{level}")
    kwargs.setdefault("wrap", True)
    kwargs.setdefault("add_newline", True)
    raw(msg_colorable, **kwargs)


def md(msg: str, /, *, dedent: bool = True, allow_headings: bool = True, **kwargs):
    """
    Print a markdown-formatted text.

    Yuio supports all CommonMark block markup except tables.
    See :mod:`yuio.md` for more info.

    :param msg:
        message to print.
    :param dedent:
        whether to remove leading indent from `msg`.
    :param allow_headings:
        whether to render headings as actual headings or as paragraphs.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(
        yuio.string.Md(msg, dedent=dedent, allow_headings=allow_headings),
        **kwargs,
    )


def rst(msg: str, /, *, dedent: bool = True, allow_headings: bool = True, **kwargs):
    """
    Print a RST-formatted text.

    Yuio supports all RST block markup except tables and field lists.
    See :mod:`yuio.rst` for more info.

    :param msg:
        message to print.
    :param dedent:
        whether to remove leading indent from `msg`.
    :param allow_headings:
        whether to render headings as actual headings or as paragraphs.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(
        yuio.string.Rst(msg, dedent=dedent, allow_headings=allow_headings),
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
def hr(msg: yuio.string.ToColorable, /, *, weight: int | str = 1, **kwargs): ...
def hr(msg: yuio.string.ToColorable = "", /, *args, weight: int | str = 1, **kwargs):
    """hr(msg: typing.LiteralString = "", /, *args, weight: int | str = 1, **kwargs)
    hr(msg: ~string.templatelib.Template, /, *, weight: int | str = 1, **kwargs) ->
    hr(msg: ~yuio.string.ToColorable, /, *, weight: int | str = 1, **kwargs) ->

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
        :attr:`Theme.msg_decorations <yuio.theme.Theme.msg_decorations_unicode>`.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(yuio.string.Hr(yuio.string._to_colorable(msg, args), weight=weight), **kwargs)


@_t.overload
def hl(
    msg: _t.LiteralString,
    /,
    *args,
    syntax: str,
    dedent: bool = True,
    **kwargs,
): ...
@_t.overload
def hl(
    msg: str,
    /,
    *,
    syntax: str,
    dedent: bool = True,
    **kwargs,
): ...
def hl(
    msg: str,
    /,
    *args,
    syntax: str,
    dedent: bool = True,
    **kwargs,
):
    """hl(msg: typing.LiteralString, /, *args, syntax: str, dedent: bool = True, **kwargs)
    hl(msg: str, /, *, syntax: str, dedent: bool = True, **kwargs) ->

    Print highlighted code. See :mod:`yuio.hl` for more info.

    :param msg:
        code to highlight.
    :param args:
        arguments for ``%``-formatting the highlighted code.
    :param syntax:
        name of syntax or a :class:`~yuio.hl.SyntaxHighlighter` instance.
    :param dedent:
        whether to remove leading indent from `msg`.
    :param kwargs:
        any additional keyword arguments will be passed to :func:`raw`.

    """

    info(yuio.string.Hl(msg, *args, syntax=syntax, dedent=dedent), **kwargs)


def raw(
    msg: yuio.string.Colorable,
    /,
    *,
    ignore_suspended: bool = False,
    tag: str | None = None,
    exc_info: ExcInfo | bool | None = None,
    add_newline: bool = False,
    heading: bool = False,
    wrap: bool = False,
    ctx: yuio.string.ReprContext | None = None,
    term: yuio.term.Term | None = None,
    to_stdout: bool = False,
    to_stderr: bool = False,
    theme: yuio.theme.Theme | None = None,
    multiline: bool | None = None,
    highlighted: bool | None = None,
    max_depth: int | None = None,
    width: int | None = None,
):
    """
    Print any :class:`~yuio.string.ToColorable`.

    This is a bridge between :mod:`yuio.io` and lower-level
    modules like :mod:`yuio.string`.

    :param msg:
        message to print.
    :param ignore_suspended:
        whether to ignore :class:`SuspendOutput` context.
    :param tag:
        tag that will be used to add color and decoration to the message.

        Decoration is looked up by path :samp:`{tag}`
        (see :attr:`Theme.msg_decorations <yuio.theme.Theme.msg_decorations_unicode>`),
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
    :param ctx:
        :class:`~yuio.string.ReprContext` that should be used for formatting
        and printing the message.
    :param term:
        if `ctx` is not given, sets terminal where to print this message. Default is
        to use :func:`get_term`.
    :param to_stdout:
        shortcut for setting `term` to ``stdout``.
    :param to_stderr:
        shortcut for setting `term` to ``stderr``.
    :param theme:
        if `ctx` is not given, sets theme used to format the message. Default is
        to use :func:`get_theme`.
    :param multiline:
        if `ctx` is not given, sets initial value for
        :attr:`ReprContext.multiline <yuio.string.ReprContext.multiline>`.
        Default is :data:`False`.
    :param highlighted:
        if `ctx` is not given, sets initial value for
        :attr:`ReprContext.highlighted <yuio.string.ReprContext.highlighted>`.
        Default is :data:`False`.
    :param max_depth:
        if `ctx` is not given, sets initial value for
        :attr:`ReprContext.max_depth <yuio.string.ReprContext.max_depth>`.
        Default is :data:`False`.
    :param width:
        if `ctx` is not given, sets initial value for
        :attr:`ReprContext.width <yuio.string.ReprContext.width>`.
        If not given, uses current terminal width
        or :attr:`Theme.fallback_width <yuio.theme.Theme.fallback_width>`
        if terminal width can't be established.

    """

    if (ctx is not None) + (term is not None) + to_stdout + to_stderr > 1:
        names = []
        if ctx is not None:
            names.append("ctx")
        if term is not None:
            names.append("term")
        if to_stdout:
            names.append("to_stdout")
        if to_stderr:
            names.append("to_stderr")
        raise TypeError(f"{And(names)} can't be given together")

    manager = _manager()

    if ctx is None:
        ctx = make_repr_context(
            term=term,
            to_stdout=to_stdout,
            to_stderr=to_stderr,
            theme=theme,
            multiline=multiline,
            highlighted=highlighted,
            max_depth=max_depth,
            width=width,
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
            preserve_spaces=True,
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
        highlighter, syntax_name = yuio.hl.get_highlighter("python-traceback")
        msg += highlighter.highlight(tb, theme=ctx.theme, syntax=syntax_name).indent()

    manager.print(
        msg.as_code(ctx.term.color_support),
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
            return f"{cls.__name__}[{_tx.type_repr(cls.__hint)}]"


@_t.final
class ask(_t.Generic[S], metaclass=_AskMeta):
    """ask[T](msg: typing.LiteralString, /, *args, parser: ~yuio.parse.Parser[T] | None = None, default: U, default_non_interactive: U, input_description: str | None = None, default_description: str | None = None) -> T | U
    ask[T](msg: str, /, *, parser: ~yuio.parse.Parser[T] | None = None, default: U, default_non_interactive: U, input_description: str | None = None, default_description: str | None = None) -> T | U

    Ask user to provide an input, parse it and return a value.

    If current terminal is not interactive, return default if one is present,
    or raise a :class:`UserIoError`.

    .. vhs:: /_tapes/questions.tape
        :alt: Demonstration of the `ask` function.
        :scale: 40%

    :func:`ask` accepts generic parameters, which determine how input is parsed.
    For example, if you're asking for an enum element,
    Yuio will show user a choice widget.

    You can also supply a custom :class:`~yuio.parse.Parser`,
    which will determine the widget that is displayed to the user,
    the way autocompletion works, etc.

    .. note::

        :func:`ask` is designed to interact with users, not to read data. It uses
        ``/dev/tty`` on Unix, and console API on Windows, so it will read from
        an actual TTY even if ``stdin`` is redirected.

        When designing your program, make sure that users have alternative means
        to provide values: use configs or CLI arguments, allow passing passwords
        via environment variables, etc.

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
        `default` is used instead. This is handy when you want to ask user if they
        want to continue with `default` set to :data:`False`,
        but `default_non_interactive` set to :data:`True`.
    :param input_description:
        description of the expected input, like ``"yes/no"`` for boolean
        inputs.
    :param default_description:
        description of the `default` value.
    :returns:
        parsed user input.
    :raises:
        raises :class:`UserIoError` if we're not in interactive environment, and there
        is no default to return.
    :example:
        .. invisible-code-block: python

            import enum

        .. code-block:: python

            class Level(enum.Enum):
                WARNING = "Warning"
                INFO = "Info"
                DEBUG = "Debug"


            answer = yuio.io.ask[Level]("Choose a logging level", default=Level.INFO)

    """

    if TYPE_CHECKING:

        @_t.overload
        def __new__(
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
        def __new__(
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
        def __new__(cls: _t.Any, *_, **__) -> _t.Any: ...


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
    ctx = make_repr_context(term=yuio.term.get_tty())

    if not _can_query_user(ctx.term):
        # TTY is not available.
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

    if not yuio.term._is_foreground(ctx.term.ostream):
        warning(
            "User input is requested in background process, use `fg %s` to resume",
            os.getpid(),
            ctx=ctx,
        )
        yuio.term._pause()

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

            s.info(prompt, tag="question", ctx=ctx)
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
                    s.error("Input is required.", ctx=ctx)
                else:
                    try:
                        return parser.parse(answer)
                    except yuio.parse.ParsingError as e:
                        s.error(e, ctx=ctx)


if os.name == "posix":
    # Getpass implementation is based on the standard `getpass` module, with a few
    # Yuio-specific modifications.

    def _getpass_fallback(
        term: yuio.term.Term, prompt: yuio.string.ColorizedString
    ) -> str:
        warning(
            "Warning: Password input may be echoed.", term=term, ignore_suspended=True
        )
        return _read(term, prompt)

    def _read(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
        info(
            prompt, add_newline=False, tag="question", term=term, ignore_suspended=True
        )
        return term.istream.readline().rstrip("\r\n")

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

    def _do_read(
        term: yuio.term.Term, prompt: yuio.string.ColorizedString, echo: bool
    ) -> str:
        import msvcrt

        if term.ostream_is_tty:
            info(
                prompt,
                add_newline=False,
                tag="question",
                term=term,
                ignore_suspended=True,
            )
        else:
            for c in str(prompt):
                msvcrt.putwch(c)

        if term.ostream_is_tty and echo:
            return term.istream.readline().rstrip("\r\n")
        else:
            result = ""
            while True:
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
                    if echo:
                        msvcrt.putwch(c)
                    else:
                        msvcrt.putwch("*")
            msvcrt.putwch("\r")
            msvcrt.putwch("\n")

        return result

    def _read(term: yuio.term.Term, prompt: yuio.string.ColorizedString):
        return _do_read(term, prompt, echo=True)

    def _getpass(term: yuio.term.Term, prompt: yuio.string.ColorizedString):
        return _do_read(term, prompt, echo=False)

else:

    def _getpass(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
        warning(
            "Warning: Password input may be echoed.", term=term, ignore_suspended=True
        )
        return _read(term, prompt)

    def _read(term: yuio.term.Term, prompt: yuio.string.ColorizedString) -> str:
        info(
            prompt, add_newline=False, tag="question", term=term, ignore_suspended=True
        )
        return term.istream.readline().rstrip("\r\n")


def _can_query_user(term: yuio.term.Term):
    return (
        # We're attached to a TTY.
        term.is_tty
        # On Windows, there is no way to bring a process to foreground (AFAIK?).
        # Thus, we need to check if there's a console window.
        and (os.name != "nt" or yuio.term._is_foreground(None))
    )


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

    If current terminal is not interactive, this functions has no effect.

    :param msg:
        prompt to display to user.
    :param args:
        arguments for ``%``\\ - formatting the prompt.

    """

    ctx = make_repr_context(term=yuio.term.get_tty())

    if not _can_query_user(ctx.term):
        # TTY is not available.
        return

    if not yuio.term._is_foreground(ctx.term.ostream):
        if os.name == "nt":
            # AFAIK there's no way to bring job to foreground in Windows.
            return

        warning(
            "User input is requested in background process, use `fg %s` to resume",
            os.getpid(),
            ctx=ctx,
        )
        yuio.term._pause()

    prompt = yuio.string.colorize(
        msg.rstrip(), *args, default_color="msg/text:question", ctx=ctx
    )
    prompt += yuio.string.Esc(" ")

    with SuspendOutput():
        try:
            if ctx.term.can_run_widgets:
                _WaitForUserWidget(prompt).run(ctx.term, ctx.theme)
            else:
                _read(ctx.term, prompt)
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
        on Windows, returns an executable name; on Unix, may return a shell command
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
    all lines that start with `comment_marker`, if one is given.

    :param text:
        text to edit.
    :param comment_marker:
        lines starting with this marker will be removed from the output after edit.
    :param editor:
        overrides editor.

        On Unix, this should be a shell command, file path will be appended to it;
        on Windows, this should be an executable path.
    :param file_ext:
        extension for the temporary file, can be used to enable syntax highlighting
        in editors that support it.
    :param fallbacks:
        list of fallback editors to try, see :func:`detect_editor` for details.
    :param dedent:
        remove leading indentation from text before opening an editor.
    :returns:
        an edited string with comments removed.
    :raises:
        If editor is not available, returns a non-zero exit code, or launched in
        a non-interactive environment, a :class:`UserIoError` is raised.

        Also raises :class:`UserIoError` if ``stdin`` or ``stderr`` is piped
        or redirected to a file (virtually no editors can work when this happens).
    :example:
        .. skip: next

        .. code-block:: python

            message = yuio.io.edit(
                \"""
                    # Please enter the commit message for your changes. Lines starting
                    # with '#' will be ignored, and an empty message aborts the commit.
                \""",
                comment_marker="#",
                dedent=True,
            )

    """

    term = yuio.term.get_tty()

    if not _can_query_user(term):
        raise UserIoError("Can't run editor in non-interactive environment")

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

    if dedent:
        text = _dedent(text)

    if not yuio.term._is_foreground(term.ostream):
        warning(
            "Background process is waiting for user, use `fg %s` to resume",
            os.getpid(),
            term=term,
        )
        yuio.term._pause()

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
            from shlex import quote

            args = f"{editor} {quote(filepath)}"
            shell = True

        try:
            with SuspendOutput():
                res = subprocess.run(
                    args,
                    shell=shell,
                    stdin=term.istream.fileno(),
                    stdout=term.ostream.fileno(),
                )
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


class MessageChannel:
    """
    Message channels are similar to logging adapters: they allow adding additional
    arguments for calls to :func:`raw` and other message functions.

    This is useful when you need to control destination for messages, but don't want
    to override global settings via :func:`setup`. One example for them is described
    in :ref:`cookbook-print-to-file`.

    .. dropdown:: Protected members

        .. autoattribute:: _msg_kwargs

        .. automethod:: _update_kwargs

        .. automethod:: _is_enabled

    """

    enabled: bool
    """
    Message channel can be disabled, in which case messages are not printed.

    """

    _msg_kwargs: dict[str, _t.Any]
    """
    Keyword arguments that will be added to every message.

    """

    if _t.TYPE_CHECKING:

        def __init__(
            self,
            *,
            ignore_suspended: bool = False,
            term: yuio.term.Term | None = None,
            to_stdout: bool = False,
            to_stderr: bool = False,
            theme: yuio.theme.Theme | None = None,
            multiline: bool | None = None,
            highlighted: bool | None = None,
            max_depth: int | None = None,
            width: int | None = None,
        ): ...
    else:

        def __init__(self, **kwargs):
            self._msg_kwargs: dict[str, _t.Any] = kwargs
            self.enabled: bool = True

    def _update_kwargs(self, kwargs: dict[str, _t.Any]):
        """
        A hook that updates method's `kwargs` before calling its implementation.

        """

        for name, option in self._msg_kwargs.items():
            kwargs.setdefault(name, option)

    def _is_enabled(self):
        """
        A hook that check if the message should be printed. By default, returns value
        of :attr:`~MessageChannel.enabled`.

        """

        return self.enabled

    @_t.overload
    def info(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def info(self, err: yuio.string.ToColorable, /, **kwargs): ...
    def info(self, msg: yuio.string.ToColorable, /, *args, **kwargs):
        """info(msg: typing.LiteralString, /, *args, **kwargs)
        info(msg: ~string.templatelib.Template, /, **kwargs) ->
        info(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print an :func:`info` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        info(msg, *args, **kwargs)

    @_t.overload
    def warning(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def warning(self, err: yuio.string.ToColorable, /, **kwargs): ...
    def warning(self, msg: yuio.string.ToColorable, /, *args, **kwargs):
        """warning(msg: typing.LiteralString, /, *args, **kwargs)
        warning(msg: ~string.templatelib.Template, /, **kwargs) ->
        warning(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print a :func:`warning` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        warning(msg, *args, **kwargs)

    @_t.overload
    def success(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def success(self, err: yuio.string.ToColorable, /, **kwargs): ...
    def success(self, msg: yuio.string.ToColorable, /, *args, **kwargs):
        """success(msg: typing.LiteralString, /, *args, **kwargs)
        success(msg: ~string.templatelib.Template, /, **kwargs) ->
        success(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print a :func:`success` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        success(msg, *args, **kwargs)

    @_t.overload
    def error(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def error(self, err: yuio.string.ToColorable, /, **kwargs): ...
    def error(self, msg: yuio.string.ToColorable, /, *args, **kwargs):
        """error(msg: typing.LiteralString, /, *args, **kwargs)
        error(msg: ~string.templatelib.Template, /, **kwargs) ->
        error(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print an :func:`error` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
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
        msg: yuio.string.ToColorable,
        /,
        *,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ): ...
    def error_with_tb(
        self,
        msg: yuio.string.ToColorable,
        /,
        *args,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ):
        """error_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
        error_with_tb(msg: ~string.templatelib.Template, /, **kwargs) ->
        error_with_tb(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print an :func:`error_with_tb` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        error_with_tb(msg, *args, **kwargs)

    @_t.overload
    def failure(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def failure(self, err: yuio.string.ToColorable, /, **kwargs): ...
    def failure(self, msg: yuio.string.ToColorable, /, *args, **kwargs):
        """failure(msg: typing.LiteralString, /, *args, **kwargs)
        failure(msg: ~string.templatelib.Template, /, **kwargs) ->
        failure(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print a :func:`failure` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
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
        msg: yuio.string.ToColorable,
        /,
        *,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ): ...
    def failure_with_tb(
        self,
        msg: yuio.string.ToColorable,
        /,
        *args,
        exc_info: ExcInfo | bool | None = True,
        **kwargs,
    ):
        """failure_with_tb(msg: typing.LiteralString, /, *args, **kwargs)
        failure_with_tb(msg: ~string.templatelib.Template, /, **kwargs) ->
        failure_with_tb(msg: ~yuio.string.ToColorable, /, **kwargs) ->

        Print a :func:`failure_with_tb` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        failure_with_tb(msg, *args, **kwargs)

    @_t.overload
    def heading(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def heading(self, msg: yuio.string.ToColorable, /, **kwargs): ...
    def heading(self, msg: yuio.string.ToColorable, /, *args, **kwargs):
        """heading(msg: typing.LiteralString, /, *args, **kwargs)
        heading(msg: ~string.templatelib.Template, /, **kwargs)
        heading(msg: ~yuio.string.ToColorable, /, **kwargs)

        Print a :func:`heading` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        heading(msg, *args, **kwargs)

    def md(self, msg: str, /, **kwargs):
        """
        Print an :func:`md` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        md(msg, **kwargs)

    def rst(self, msg: str, /, **kwargs):
        """
        Print an :func:`rst` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        rst(msg, **kwargs)

    def br(self, **kwargs):
        """br()

        Print a :func:`br` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        br(**kwargs)

    @_t.overload
    def hl(self, msg: _t.LiteralString, /, *args, **kwargs): ...
    @_t.overload
    def hl(self, msg: str, /, **kwargs): ...
    def hl(self, msg: str, /, *args, **kwargs):
        """hl(msg: typing.LiteralString, /, *args, syntax: str, dedent: bool = True, **kwargs)
        hl(msg: str, /, *, syntax: str, dedent: bool = True, **kwargs)

        Print an :func:`hl` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        hl(msg, *args, **kwargs)

    @_t.overload
    def hr(self, msg: _t.LiteralString = "", /, *args, **kwargs): ...
    @_t.overload
    def hr(self, msg: yuio.string.ToColorable, /, **kwargs): ...
    def hr(self, msg: yuio.string.ToColorable = "", /, *args, **kwargs):
        """hr(msg: typing.LiteralString = "", /, *args, weight: int | str = 1, **kwargs)
        hr(msg: ~string.templatelib.Template, /, *, weight: int | str = 1, **kwargs) ->
        hr(msg: ~yuio.string.ToColorable, /, *, weight: int | str = 1, **kwargs) ->

        Print an :func:`hr` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        hr(msg, *args, **kwargs)

    def raw(self, msg: yuio.string.Colorable, /, **kwargs):
        """
        Print a :func:`raw` message.

        """

        if not self._is_enabled():
            return

        self._update_kwargs(kwargs)
        raw(msg, **kwargs)

    def make_repr_context(self) -> yuio.string.ReprContext:
        """
        Make a :class:`~yuio.string.ReprContext` using settings
        from :attr:`~MessageChannel._msg_kwargs`.

        """

        return make_repr_context(
            term=self._msg_kwargs.get("term"),
            to_stdout=self._msg_kwargs.get("to_stdout", False),
            to_stderr=self._msg_kwargs.get("to_stderr", False),
            theme=self._msg_kwargs.get("theme"),
            multiline=self._msg_kwargs.get("multiline"),
            highlighted=self._msg_kwargs.get("highlighted"),
            max_depth=self._msg_kwargs.get("max_depth"),
            width=self._msg_kwargs.get("width"),
        )


class SuspendOutput(MessageChannel):
    """
    A context manager for pausing output.

    This is handy for when you need to take control over the output stream.
    For example, the :func:`ask` function uses this class internally.

    This context manager also suspends all prints that go to :data:`sys.stdout`
    and :data:`sys.stderr` if they were wrapped (see :func:`setup`).
    To print through them, use :func:`orig_stderr` and :func:`orig_stdout`.

    Each instance of this class is a :class:`MessageChannel`; calls to its printing
    methods bypass output suppression:

    .. code-block:: python

        with SuspendOutput() as out:
            print("Suspended")  # [1]_
            out.info("Not suspended")  # [2]_

    .. code-annotations::

        1. This message is suspended; it will be printed when output is resumed.
        2. This message bypasses suspension; it will be printed immediately.

    """

    def __init__(self, initial_channel: MessageChannel | None = None, /):
        super().__init__()

        if initial_channel is not None:
            self._msg_kwargs.update(initial_channel._msg_kwargs)
        self._msg_kwargs["ignore_suspended"] = True

        self._resumed = False
        _manager().suspend()

    def resume(self):
        """
        Manually resume the logging process.

        """

        if not self._resumed:
            _manager().resume()
            self._resumed = True

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


class TaskBase:
    """
    Base class for tasks and other objects that you might show to the user.

    Example of a custom task can be found in :ref:`cookbook <cookbook-custom-tasks>`.

    .. dropdown:: Protected members

        .. autoproperty:: _lock

        .. automethod:: _get_widget

        .. automethod:: _get_priority

        .. automethod:: _request_update

        .. automethod:: _widgets_are_displayed

        .. automethod:: _get_parent

        .. automethod:: _is_toplevel

        .. automethod:: _get_children

    """

    def __init__(self):
        self.__parent: TaskBase | None = None
        self.__children: list[TaskBase] = []

    def attach(self, parent: TaskBase | None):
        """
        Attach this task and all of its children to the task tree.

        :param parent:
            parent task in the tree. Pass :data:`None` to attach to root.

        """

        with self._lock:
            if parent is None:
                parent = _manager().tasks_root
            if self.__parent is not None:
                self.__parent.__children.remove(self)
            self.__parent = parent
            parent.__children.append(self)
            self._request_update()

    def detach(self):
        """
        Remove this task and all of its children from the task tree.

        """

        with self._lock:
            if self.__parent is not None:
                self.__parent.__children.remove(self)
                self.__parent = None
                self._request_update()

    @property
    def _lock(self):
        """
        Global IO lock.

        All protected methods, as well as state mutations, should happen
        under this lock.

        """

        return _IO_LOCK

    @abc.abstractmethod
    def _get_widget(self) -> yuio.widget.Widget[_t.Never]:
        """
        This method should return widget that renders the task.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        """

        raise NotImplementedError()

    @abc.abstractmethod
    def _get_priority(self) -> int:
        """
        This method should return priority that will be used to hide non-important
        tasks when there is not enough space to show all of them.

        Default priority is ``1``, priority for finished tasks is ``0``.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        """

        raise NotImplementedError()

    def _request_update(self, *, immediate_render: bool = False):
        """
        Indicate that task's state has changed, and update is necessary.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        :param immediate_render:
            by default, tasks are updated lazily from a background thread; set this
            parameter to :data:`True` to redraw them immediately from this thread.

        """

        _manager()._update_tasks(immediate_render)

    def _widgets_are_displayed(self) -> bool:
        """
        Return :data:`True` if we're in an interactive foreground process which
        renders tasks.

        If this function returns :data:`False`, you should print log messages about
        task status instead of relying on task's widget being presented to the user.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        """

        return _manager()._should_draw_interactive_tasks()

    def _get_parent(self) -> TaskBase | None:
        """
        Get parent task.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        """

        return self.__parent

    def _is_toplevel(self) -> bool:
        """
        Check if this task is attached to the first level of the tree.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        """

        return self._get_parent() is _manager().tasks_root

    def _get_children(self) -> _t.Sequence[TaskBase]:
        """
        Get child tasks.

        .. warning::

            This method should be called under :attr:`~TaskBase._lock`.

        """

        return self.__children


class _TasksRoot(TaskBase):
    _widget = yuio.widget.Empty()

    def _get_widget(self) -> yuio.widget.Widget[_t.Never]:
        return self._widget

    def _get_priority(self) -> int:
        return 0


class Task(TaskBase):
    """Task(msg: typing.LiteralString, /, *args, comment: str | None = None, parent: Task | None = None)
    Task(msg: str, /, *, comment: str | None = None, parent: Task | None = None)

    A class for indicating progress of some task.

    :param msg:
        task heading.
    :param args:
        arguments for ``%``\\ -formatting the task heading.
    :param comment:
        comment for the task. Can be specified after creation
        via the :meth:`~Task.comment` method.
    :param persistent:
        whether to keep showing this task after it finishes.
        Default is :data:`False`.

        To manually hide the task, call :meth:`~TaskBase.detach`.
    :param initial_status:
        initial status of the task.
    :param parent:
        parent task.

    You can have multiple tasks at the same time,
    create subtasks, set task's progress or add a comment about
    what's currently being done within a task.

    .. vhs:: /_tapes/tasks_multithreaded.tape
       :alt: Demonstration of the `Task` class.
       :scale: 40%

    This class can be used as a context manager:

    .. code-block:: python

        with yuio.io.Task("Processing input") as t:
            ...
            t.progress(0.3)
            ...

    .. dropdown:: Protected members

        .. autoattribute:: _widget_class

    """

    Status = yuio.widget.Task.Status

    _widget_class: _ClassVar[type[yuio.widget.Task]] = yuio.widget.Task
    """
    Class of the widget that will be used to draw this task, can be overridden
    in subclasses.

    """

    @_t.overload
    def __init__(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        comment: str | None = None,
        persistent: bool = False,
        initial_status: Task.Status = yuio.widget.Task.Status.RUNNING,
        parent: TaskBase | None = None,
    ): ...
    @_t.overload
    def __init__(
        self,
        msg: str,
        /,
        *,
        comment: str | None = None,
        persistent: bool = False,
        initial_status: Task.Status = yuio.widget.Task.Status.RUNNING,
        parent: TaskBase | None = None,
    ): ...
    def __init__(
        self,
        msg: str,
        /,
        *args,
        comment: str | None = None,
        persistent: bool = False,
        initial_status: Task.Status = yuio.widget.Task.Status.RUNNING,
        parent: TaskBase | None = None,
    ):
        super().__init__()

        self._widget = self._widget_class(msg, *args, comment=comment)
        self._persistent = persistent
        with self._lock:
            self.set_status(initial_status)
            self.attach(parent)

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
        and a total amount of work. In this case, optional argument `unit`
        can be used to indicate units for the progress.

        If given a single :data:`None`, reset task progress.

        .. note::

            Tasks are updated asynchronously once every ~100ms, so calling this method
            is relatively cheap. It still requires acquiring a global lock, though:
            contention could be an issue in multi-threaded applications.

        :param progress:
            a percentage between ``0`` and ``1``, or :data:`None`
            to reset task progress.
        :param done:
            amount of finished work, should be less than or equal to `total`.
        :param total:
            total amount of work.
        :param unit:
            unit for measuring progress. Only displayed when progress is given
            as `done` and `total`.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. code-block:: python

                with yuio.io.Task("Loading cargo") as task:
                    task.progress(110, 150, unit="Kg")

            This will print the following:

            .. code-block:: text

                ■■■■■■■■■■■□□□□ Loading cargo - 110/150Kg

        """

        with self._lock:
            self._widget.progress(*args, unit=unit, ndigits=ndigits)  # type: ignore
            self._request_update()

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

                with yuio.io.Task("Downloading a file") as task:
                    task.progress_size(31.05 * 2**20, 150 * 2**20)

            This will print:

            .. code-block:: text

                ■■■□□□□□□□□□□□□ Downloading a file - 31.05/150.00M

        """

        with self._lock:
            self._widget.progress_size(done, total, ndigits=ndigits)
            self._request_update()

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
            amount of finished work, should be less than or equal to `total`.
        :param total:
            total amount of work.
        :param unit:
            unit for measuring progress.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. code-block:: python

                with yuio.io.Task("Charging a capacitor") as task:
                    task.progress_scale(889.25e-3, 1, unit="V")

            This will print:

            .. code-block:: text

                ■■■■■■■■■■■■■□□ Charging a capacitor - 889.25mV/1.00V

        """

        with self._lock:
            self._widget.progress_scale(done, total, unit=unit, ndigits=ndigits)
            self._request_update()

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
        :param unit:
            unit for measuring progress.
        :param ndigits:
            number of digits to display after a decimal point.
        :example:
            .. invisible-code-block: python

                urls = []

            .. code-block:: python

                with yuio.io.Task("Fetching data") as t:
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

                with yuio.io.Task("Fetching data") as t:
                    for url in urls:
                        t.comment("%s", url)
                        ...

            This will output the following:

            .. code-block:: text

                ⣿ Fetching data - https://google.com

        """

        with self._lock:
            self._widget.comment(comment, *args)
            self._request_update()

    def set_status(self, status: Task.Status):
        """
        Set task status.

        :param status:
            New status.

        """

        with self._lock:
            if self._widget.status == status:
                return

            self._widget.status = status
            if status in [Task.Status.DONE, Task.Status.ERROR] and not self._persistent:
                self.detach()
            if self._widgets_are_displayed():
                self._request_update()
            else:
                raw(self._widget, add_newline=True)

    def running(self):
        """
        Indicate that this task is running.

        """

        self.set_status(Task.Status.RUNNING)

    def pending(self):
        """
        Indicate that this task is pending.

        """

        self.set_status(Task.Status.PENDING)

    def done(self):
        """
        Indicate that this task has finished successfully.

        """

        self.set_status(Task.Status.DONE)

    def error(self):
        """
        Indicate that this task has finished with an error.

        """

        self.set_status(Task.Status.ERROR)

    @_t.overload
    def subtask(
        self,
        msg: _t.LiteralString,
        /,
        *args,
        comment: str | None = None,
        persistent: bool = True,
        initial_status: Task.Status = yuio.widget.Task.Status.RUNNING,
    ) -> Task: ...
    @_t.overload
    def subtask(
        self,
        msg: str,
        /,
        *,
        comment: str | None = None,
        persistent: bool = True,
        initial_status: Task.Status = yuio.widget.Task.Status.RUNNING,
    ) -> Task: ...
    def subtask(
        self,
        msg: str,
        /,
        *args,
        comment: str | None = None,
        persistent: bool = True,
        initial_status: Task.Status = yuio.widget.Task.Status.RUNNING,
    ) -> Task:
        """
        Create a subtask within this task.

        :param msg:
            subtask heading.
        :param args:
            arguments for ``%``\\ -formatting the subtask heading.
        :param comment:
            comment for the task. Can be specified after creation
            via the :meth:`~Task.comment` method.
        :param persistent:
            whether to keep showing this subtask after it finishes. Default
            is :data:`True`.
        :param initial_status:
            initial status of the task.
        :returns:
            a new :class:`Task` that will be displayed as a sub-task of this task.

        """

        return Task(
            msg,
            *args,
            comment=comment,
            persistent=persistent,
            initial_status=initial_status,
            parent=self,
        )

    def __enter__(self):
        self.running()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.done()
        else:
            self.error()

    def _get_widget(self) -> yuio.widget.Widget[_t.Never]:
        return self._widget

    def _get_priority(self) -> int:
        return 1 if self._widget.status is yuio.widget.Task.Status.RUNNING else 0


class _TaskTree(yuio.widget.Widget[_t.Never]):
    def __init__(self, root: TaskBase):
        super().__init__()

        self._root = root

    def layout(self, rc: yuio.widget.RenderContext) -> tuple[int, int]:
        widgets: list[yuio.widget.Widget[_t.Never]] = []  # widget
        tree: dict[
            int, tuple[int | None, int, int]
        ] = {}  # index -> parent, level, priority

        # Build widgets tree.
        to_visit: list[tuple[TaskBase, int, int | None]] = [(self._root, 0, None)]
        while to_visit:
            node, level, parent = to_visit.pop()
            widget = node._get_widget()
            tree[len(widgets)] = parent, level, node._get_priority()
            to_visit.extend(
                (child, level + 1, len(widgets))
                for child in reversed(node._get_children())
            )
            widgets.append(widget)

        # Prepare layouts.
        layouts: dict[yuio.widget.Widget[_t.Never], tuple[int, int, int]] = {}
        self.__layouts = layouts
        total_min_h = 0
        total_max_h = 0
        for index, widget in enumerate(widgets):
            min_h, max_h = widget.layout(rc)
            assert min_h <= max_h, "incorrect layout"
            _, level, _ = tree[index]
            layouts[widget] = min_h, max_h, level
            total_min_h += min_h
            total_max_h += max_h

        if total_min_h <= rc.height:
            # All widgets fit.
            self.__min_h = total_min_h
            self.__max_h = total_max_h
            self.__widgets = widgets
            return total_min_h, total_max_h

        # Propagate priority upwards, ensure that parents are at least as important
        # as children.
        for index, widget in enumerate(widgets):
            parent, _, priority = tree[index]
            while parent is not None:
                grandparent, parent_level, parent_priority = tree[parent]
                if parent_priority >= priority:
                    break
                tree[parent] = grandparent, parent_level, priority
                widget = parent
                parent = grandparent

        # Sort by (-priority, level, -index). Since we've propagated priorities, we can
        # be sure that parents are always included first. Hence in the loop below,
        # we will visit children before parents.
        widgets_sorted = list(enumerate(widgets))
        widgets_sorted.sort(key=lambda w: (-tree[w[0]][2], tree[w[0]][1], -w[0]))

        # Decide which widgets to hide by introducing "holes" to widgets sequence.
        total_h = total_min_h
        holes = _DisjointSet[int]()
        for index, widget in reversed(widgets_sorted):
            if total_h <= rc.height:
                break

            min_h, max_h = widget.layout(rc)

            # We need to hide this widget.
            _, level, _ = tree[index]
            holes.add(index)
            total_h -= min_h
            total_h += 1  # Size of a message.

            # Join this hole with the next one.
            if index + 1 < len(widgets) and index + 1 in holes:
                _, next_level, _ = tree[index + 1]
                if next_level >= level:
                    holes.union(index, index + 1)
                    total_h -= 1
            # Join this hole with the previous one.
            if index - 1 >= 0 and index - 1 in holes:
                _, prev_level, _ = tree[index - 1]
                if prev_level <= level:
                    holes.union(index, index - 1)
                    total_h -= 1

        # Assemble the final sequence of widgets.
        hole_color = rc.theme.get_color("task/hole")
        hole_num_color = rc.theme.get_color("task/hole/num")
        prev_hole_id: int | None = None
        prev_hole_size = 0
        prev_hole_level: int | None = None
        displayed_widgets: list[yuio.widget.Widget[_t.Never]] = []
        for index, widget in enumerate(widgets):
            if index in holes:
                hole_id = holes.find(index)
                if hole_id == prev_hole_id:
                    prev_hole_size += 1
                    if prev_hole_level is None:
                        prev_hole_level = tree[index][1]
                    else:
                        prev_hole_level = min(prev_hole_level, tree[index][1])
                else:
                    if prev_hole_id is not None:
                        hole_widget = yuio.widget.Line(
                            yuio.string.ColorizedString(
                                hole_num_color,
                                "+",
                                str(prev_hole_size),
                                hole_color,
                                " more",
                            )
                        )
                        displayed_widgets.append(hole_widget)
                        layouts[hole_widget] = 1, 1, prev_hole_level or 1
                    prev_hole_id = hole_id
                    prev_hole_size = 1
                    prev_hole_level = tree[index][1]
            else:
                if prev_hole_id is not None:
                    hole_widget = yuio.widget.Line(
                        yuio.string.ColorizedString(
                            hole_num_color,
                            "+",
                            str(prev_hole_size),
                            hole_color,
                            " more",
                        )
                    )
                    displayed_widgets.append(hole_widget)
                    layouts[hole_widget] = 1, 1, prev_hole_level or 1
                prev_hole_id = None
                prev_hole_size = 0
                prev_hole_level = None
                displayed_widgets.append(widget)

        if prev_hole_id is not None:
            hole_widget = yuio.widget.Line(
                yuio.string.ColorizedString(
                    hole_num_color,
                    "+",
                    str(prev_hole_size),
                    hole_color,
                    " more",
                )
            )
            displayed_widgets.append(hole_widget)
            layouts[hole_widget] = 1, 1, prev_hole_level or 1

        total_min_h = 0
        total_max_h = 0
        for widget in displayed_widgets:
            min_h, max_h, _ = layouts[widget]
            total_min_h += min_h
            total_max_h += max_h

        self.__min_h = total_min_h
        self.__max_h = total_max_h
        self.__widgets = displayed_widgets
        return total_min_h, total_max_h

    def draw(self, rc: yuio.widget.RenderContext):
        if rc.height <= self.__min_h:
            scale = 0.0
        elif rc.height >= self.__max_h:
            scale = 1.0
        else:
            scale = (rc.height - self.__min_h) / (self.__max_h - self.__min_h)

        y1 = 0.0
        for widget in self.__widgets:
            min_h, max_h, level = self.__layouts[widget]
            y2 = y1 + min_h + scale * (max_h - min_h)

            iy1 = round(y1)
            iy2 = round(y2)

            with rc.frame(max((level - 1) * 2, 0), iy1, height=iy2 - iy1):
                widget.draw(rc)

            y1 = y2

        rc.set_final_pos(0, round(y1))


class Formatter(logging.Formatter):
    """
    Log formatter that uses ``%`` style with colorized string formatting
    and returns a string with ANSI escape characters generated for current
    output terminal.

    Every part of log message is colored with path :samp:`log/{name}:{level}`.
    For example, `asctime` in info log line is colored
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
            .as_code(ctx.term.color_support)
        )

    def formatException(self, ei):
        tb = "".join(traceback.format_exception(*ei)).rstrip()
        return self.formatStack(tb)

    def formatStack(self, stack_info):
        manager = _manager()
        theme = manager.theme
        term = manager.term
        highlighter, syntax_name = yuio.hl.get_highlighter("python-traceback")
        return "".join(
            highlighter.highlight(stack_info, theme=theme, syntax=syntax_name)
            .indent()
            .as_code(term.color_support)
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
    # If we see that it took more than this time to render progress bars,
    # we assume that the process was suspended, meaning that we might've been moved
    # from foreground to background or back. In either way, we should assume that the
    # screen was changed, and re-render all tasks accordingly. We have to track time
    # because Python might take significant time to call `SIGCONT` handler, so we can't
    # rely on it.
    TASK_RENDER_TIMEOUT_NS = 250_000_000

    def __init__(
        self,
        term: yuio.term.Term | None = None,
        theme: (
            yuio.theme.Theme | _t.Callable[[yuio.term.Term], yuio.theme.Theme] | None
        ) = None,
        enable_bg_updates: bool = True,
    ):
        self._out_term = yuio.term.get_term_from_stream(
            orig_stdout(), sys.stdin, allow_env_overrides=True
        )
        self._err_term = yuio.term.get_term_from_stream(
            orig_stderr(), sys.stdin, allow_env_overrides=True
        )

        self._term = term or self._err_term

        self._theme_ctor = theme
        if isinstance(theme, yuio.theme.Theme):
            self._theme = theme
        else:
            self._theme = yuio.theme.load(self._term, theme)
        self._rc = yuio.widget.RenderContext(self._term, self._theme)
        self._rc.prepare()

        self._suspended: int = 0
        self._suspended_lines: list[tuple[list[str], _t.TextIO]] = []

        self._tasks_root = _TasksRoot()
        self._tasks_widet = _TaskTree(self._tasks_root)
        self._printed_tasks: bool = False
        self._needs_update = False
        self._last_update_time_us = 0
        self._printed_some_lines = False

        self._stop = False
        self._stop_condition = threading.Condition(_IO_LOCK)
        self._thread: threading.Thread | None = None

        self._enable_bg_updates = enable_bg_updates
        self._prev_sigcont_handler: (
            None | yuio.Missing | int | _t.Callable[[int, types.FrameType | None], None]
        ) = yuio.MISSING
        self._seen_sigcont: bool = False
        if enable_bg_updates:
            self._setup_sigcont()
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

    @property
    def tasks_root(self):
        return self._tasks_root

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
            self.__dict__.pop("_update_rate_us", None)  # type: ignore
            self._update_tasks()

    def _setup_sigcont(self):
        import signal

        if not hasattr(signal, "SIGCONT"):
            return

        self._prev_sigcont_handler = signal.getsignal(signal.SIGCONT)
        signal.signal(signal.SIGCONT, self._on_sigcont)

    def _reset_sigcont(self):
        import signal

        if not hasattr(signal, "SIGCONT"):
            return

        if self._prev_sigcont_handler is not yuio.MISSING:
            signal.signal(signal.SIGCONT, self._prev_sigcont_handler)

    def _on_sigcont(self, sig: int, frame: types.FrameType | None):
        self._seen_sigcont = True
        if self._prev_sigcont_handler and not isinstance(
            self._prev_sigcont_handler, int
        ):
            self._prev_sigcont_handler(sig, frame)

    def _bg_update(self):
        while True:
            try:
                with _IO_LOCK:
                    while True:
                        update_rate_us = self._update_rate_us
                        start_ns = time.monotonic_ns()
                        now_us = start_ns // 1_000
                        sleep_us = update_rate_us - now_us % update_rate_us
                        deadline_ns = (
                            start_ns + 2 * sleep_us * 1000 + self.TASK_RENDER_TIMEOUT_NS
                        )

                        if self._stop_condition.wait_for(
                            lambda: self._stop, timeout=sleep_us / 1_000_000
                        ):
                            return

                        self._show_tasks(deadline_ns=deadline_ns)
            except Exception:
                yuio._logger.critical("exception in bg updater", exc_info=True)

    def stop(self):
        if self._stop:
            return

        with _IO_LOCK:
            atexit.unregister(self.stop)

            self._stop = True
            self._stop_condition.notify()
            self._show_tasks(immediate_render=True)

        if self._thread:
            self._thread.join()

        if self._prev_sigcont_handler is not yuio.MISSING:
            self._reset_sigcont()

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
            update_rate_ms //= 2
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

    def _should_draw_interactive_tasks(self):
        should_draw_interactive_tasks = (
            self._term.color_support >= yuio.term.ColorSupport.ANSI
            and self._term.ostream_is_tty
            and yuio.term._is_foreground(self._term.ostream)
        )

        if (
            not should_draw_interactive_tasks and self._printed_tasks
        ) or self._seen_sigcont:
            # We were moved from foreground to background. There's no point in hiding
            # tasks now (shell printed something when user sent C-z), but we need
            # to make sure that we'll start rendering tasks from scratch whenever
            # user brings us to foreground again.
            self.rc.prepare(reset_term_pos=True)
            self._printed_tasks = False
            self._seen_sigcont = False

        return should_draw_interactive_tasks

    def _clear_tasks(self):
        if self._should_draw_interactive_tasks() and self._printed_tasks:
            self._rc.finalize()
            self._printed_tasks = False

    def _update_tasks(self, immediate_render: bool = False):
        self._needs_update = True
        if immediate_render or not self._enable_bg_updates:
            self._show_tasks(immediate_render)

    def _show_tasks(
        self, immediate_render: bool = False, deadline_ns: int | None = None
    ):
        if (
            self._should_draw_interactive_tasks()
            and not self._suspended
            and (self._tasks_root._get_children() or self._printed_tasks)
        ):
            start_ns = time.monotonic_ns()
            if deadline_ns is None:
                deadline_ns = start_ns + self.TASK_RENDER_TIMEOUT_NS
            now_us = start_ns // 1000
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
            self._printed_tasks = bool(self._tasks_root._get_children())
            self._needs_update = False

            self._rc.prepare()
            self._tasks_widet.layout(self._rc)
            self._tasks_widet.draw(self._rc)

            now_ns = time.monotonic_ns()
            if not self._seen_sigcont and now_ns < deadline_ns:
                self._rc.render()
            else:
                # We have to skip this render: the process was suspended while we were
                # formatting tasks. Because of this, te position of the cursor
                # could've changed, so we need to reset rendering context and re-render.
                self._seen_sigcont = True


class _YuioOutputWrapper(_t.TextIO):  # pragma: no cover
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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__wrapped!r})"
