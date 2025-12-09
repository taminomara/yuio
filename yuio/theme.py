# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
Controlling visual aspects of Yuio with themes.

Theme base class
----------------

The overall look and feel of a Yuio application is declared
in a :class:`Theme` object:

.. autoclass:: Theme

    .. autoattribute:: progress_bar_width

    .. autoattribute:: spinner_update_rate_ms

    .. autoattribute:: msg_decorations

    .. automethod:: set_msg_decoration

    .. automethod:: _set_msg_decoration_if_not_overridden

    .. autoattribute:: colors

    .. automethod:: set_color

    .. automethod:: _set_color_if_not_overridden

    .. automethod:: get_color

    .. automethod:: to_color

    .. automethod:: check


Default theme
-------------

Use the following loader to create an instance of the default theme:

.. autofunction:: load

.. autoclass:: DefaultTheme


.. _all-color-paths:

Color paths
-----------

common tags
    :class:`DefaultTheme` sets up commonly used colors that you can use
    in formatted messages:

    -   ``code``: inline code,
    -   ``note``: inline highlighting,
    -   ``path``: file paths,
    -   ``flag``: CLI flags,
    -   ``bold``, ``b``: font style,
    -   ``dim``, ``d``: font style,
    -   ``italic``, ``i``: font style,
    -   ``underline``, ``u``: font style,
    -   ``inverse``: swap foreground and background colors,
    -   ``normal``: normal foreground,
    -   ``normal_dim``: muted foreground (see :attr:`~yuio.color.Color.FORE_NORMAL_DIM`),
    -   ``red``: foreground,
    -   ``green``: foreground,
    -   ``yellow``: foreground,
    -   ``blue``: foreground,
    -   ``magenta``: foreground,
    -   ``cyan``: foreground,

    .. note::

        We don't define ``black`` and ``white`` because they can be invisible
        with some terminal themes. Prefer ``normal_dim`` when you need a muted color.

        We also don't define tags for backgrounds because there's no way to tell
        which foreground/background combination will be readable and which will not.
        Prefer ``inverse`` when you need to add a background.

:samp:`msg/decoration:{tag}`
    Color for decorations in front of messages:

    -   ``msg/decoration:info``: messages from :mod:`yuio.io.info`,
    -   ``msg/decoration:warning``: messages from :mod:`yuio.io.warning`,
    -   ``msg/decoration:error``: messages from :mod:`yuio.io.error`,
    -   ``msg/decoration:success``: messages from :mod:`yuio.io.success`,
    -   ``msg/decoration:failure``: messages from :mod:`yuio.io.failure`,
    -   :samp:`msg/decoration:heading/{level}`: messages from :mod:`yuio.io.heading`
        and headings in markdown,
    -   ``msg/decoration:heading/section``: first-level headings in CLI help,
    -   ``msg/decoration:question``: messages from :func:`yuio.io.ask`,
    -   ``msg/decoration:list``: bullets in markdown,
    -   ``msg/decoration:quote``: quote decorations in markdown,
    -   ``msg/decoration:code``: code decorations in markdown,
    -   ``msg/decoration:thematic_break``: thematic breaks
        (i.e. horizontal rulers) in markdown,
    -   :samp:`msg/decoration:hr/{weight}`: horizontal rulers (see :func:`yuio.io.hr`
        and :func:`yuio.string.Hr`).

:samp:`msg/text:{tag}`
    Color for the text part of messages:

    -   ``msg/text:info`` and all other tags from ``msg/decoration``,
    -   ``msg/text:paragraph``: plain text in markdown,
    -   :samp:`msg/text:code/{syntax}`: plain text in highlighted code blocks.

:samp:`task/...:{status}`
    Running and finished tasks:

    -   :samp:`task/decoration`: decoration before the task,
    -   ``task/progressbar/done``: filled portion of the progress bar,
    -   ``task/progressbar/done/start``: gradient start for the filled
        portion of the progress bar,
    -   ``task/progressbar/done/end``: gradient end for the filled
        portion of the progress bar,
    -   ``task/progressbar/pending``: unfilled portion of the progress bar,
    -   ``task/progressbar/pending/start``: gradient start for the unfilled
        portion of the progress bar,
    -   ``task/progressbar/pending/end``: gradient end for the unfilled
        portion of the progress bar,
    -   ``task/heading``: task title,
    -   ``task/progress``: number that indicates task progress,
    -   ``task/comment``: task comment.

    ``status`` can be ``running``, ``done``, or ``error``.

:samp:`hl/{part}:{syntax}`
    Color for highlighted part of code:

    -   ``hl/comment``: code comments,
    -   ``hl/kwd``: keyword,
    -   ``hl/lit``: non-string literals,
    -   ``hl/punct``: punctuation,
    -   ``hl/str``: string literals,
    -   ``hl/str/esc``: escape sequences in strings,
    -   ``hl/type``: type names,
    -   ``hl/meta``: diff meta info for diff highlighting,
    -   ``hl/added``: added lines in diff highlighting,
    -   ``hl/removed``: removed lines in diff highlighting,
    -   ``hl/prog``: program name in CLI usage and shell highlighting,
    -   ``hl/flag``: CLI flags,
    -   ``hl/metavar``: meta variables in CLI usage.

``tb/heading``, ``tb/message``, :samp:`tb/frame/{location}/...`
    For highlighted tracebacks:

    -   ``tb/heading``: traceback heading,
    -   ``tb/message``: error message,
    -   :samp:`tb/frame/{location}/file/module`: module name,
    -   :samp:`tb/frame/{location}/file/line`: line number,
    -   :samp:`tb/frame/{location}/file/path`: file path,
    -   :samp:`tb/frame/{location}/code`: code sample at the error line,
    -   :samp:`tb/frame/{location}/highlight`: highlighting under the code sample.

    ``location`` is either ``lib`` or ``usr`` depending on whether the code
    is located in site-packages or in user code.

:samp:`log/{part}:{level}`
    Colors for log records. ``part`` is name of a `log record attribute`__,
    level is lowercase name of logging level.

    __ https://docs.python.org/3/library/logging.html#logrecord-attributes

    .. seealso::

        :class:`yuio.io.Formatter`.

input widget
    Colors for :class:`yuio.widget.Input`:

    -   ``menu/decoration:input``: decoration before an input box,
    -   ``menu/text:input``: entered text in an input box,
    -   ``menu/text/esc:input``: highlights for invisible characters in an input box,
    -   ``menu/text/error:input``: highlights for error region reported by a parser,
    -   ``menu/text/placeholder:input``: placeholder text in an input box,

grid widgets
    Colors for :class:`yuio.widget.Grid`, :class:`yuio.widget.Choice`, and other
    similar widgets:

    -   :samp:`menu/decoration:choice/{status}/{color_tag}`:
        decoration before a grid item,
    -   :samp:`menu/decoration/comment:choice/{status}/{color_tag}`:
        decoration around comments for a grid item,
    -   :samp:`menu/text:choice/{status}/{color_tag}`:
        text of a grid item,
    -   :samp:`menu/text/comment:choice/{status}/{color_tag}`:
        comment for a grid item,
    -   :samp:`menu/text/prefix:choice/{status}/{color_tag}`:
        prefix before the main text of a grid item
        (see :attr:`yuio.widget.Option.display_text_prefix` and
        :attr:`yuio.complete.Completion.dprefix`),
    -   :samp:`menu/text/suffix:choice/{status}/{color_tag}`:
        suffix after the main text of a grid item
        (see :attr:`yuio.widget.Option.display_text_suffix` and
        :attr:`yuio.complete.Completion.dsuffix`),
    -   ``menu/text:choice/status_line``: status line (i.e. "Page x of y").
    -   ``menu/text:choice/status_line/number``: page numbers in a status line.

    ``status`` is either ``normal`` or ``active``:

    -   ``normal`` for regular grid items,
    -   ``active`` for the currently selected item.

    ``color_tag`` is whatever tag specified by :attr:`yuio.widget.Option.color_tag`
    and :attr:`yuio.complete.Completion.group_color_tag`. Currently supported tags:

    -   ``none``: color tag is not given,
    -   ``selected``: items selected in :class:`yuio.widget.Multiselect`,
    -   ``dir``: directory (in file completion),
    -   ``exec``: executable file (in file completion),
    -   ``symlink``: symbolic link (in file completion),
    -   ``socket``: socket (in file completion),
    -   ``pipe``: FIFO pipe (in file completion),
    -   ``block_device``: block device (in file completion),
    -   ``char_device``: character device (in file completion),
    -   ``original``: original completion item before spelling correction,
    -   ``corrected``: completion item that was found after spelling correction.

full screen help menu
    Colors for help menu that appears when pressing :kbd:`F1`:

    -   ``menu/text/heading:help_menu``: section heading,
    -   ``menu/text/help_key:help_menu``: key names,
    -   ``menu/text/help_sep:help_menu``: separators between key names,
    -   ``menu/decoration:help_menu``: decorations.

inline help menu
    Colors for help items rendered under a widget:

    -   ``menu/text/help_info:help``: help items that aren't associated with any key,
    -   ``menu/text/help_msg:help``: regular help items,
    -   ``menu/text/help_key:help``: keybinding names,
    -   ``menu/text/help_sep:help``: separator between items.


.. _all-decorations:

Decorations
-----------

``info``
    Messages from :mod:`yuio.io.info`.

``warning``
    Messages from :mod:`yuio.io.warning`.

``error``
    Messages from :mod:`yuio.io.error`.

``success``
    Messages from :mod:`yuio.io.success`.

``failure``
    Messages from :mod:`yuio.io.failure`.

:samp:`heading/{level}`
    Messages from :mod:`yuio.io.heading` and headings in markdown.

``heading/section``
    First-level headings in CLI help.

``question``
    Messages from :func:`yuio.io.ask`.

``list``
    Bullets in markdown.

``quote``
    Quote decorations in markdown.

``code``
    Code decorations in markdown.

``thematic_break``
    Thematic breaks (i.e. horizontal rulers) in markdown.

``overflow``
    Ellipsis symbol for lines that don't fit terminal width. Must be one character wide.

:samp:`progress_bar/{position}`
    Decorations for progress bars.

    Available positions are:

    :``start_symbol``:
        Start of the progress bar.
    :``done_symbol``:
        Tiles finished portion of the progress bar, must be one character wide.
    :``pending_symbol``:
        Tiles unfinished portion of the progress bar, must be one character wide.
    :``end_symbol``:
        End of the progress bar.
    :``transition_pattern``:
        If this decoration is empty, there's no symbol between finished and unfinished
        parts of the progress bar.

        Otherwise, this decoration defines a left-to-right gradient of transition
        characters, ordered from most filled to least filled. Each character
        must be one character wide.

    .. raw:: html

        <div class="highlight-text notranslate">
        <div class="highlight">
        <pre class="ascii-graphics">
            <span class="k">[------>          ]</span>
            │└┬───┘│└┬───────┘│
            │ │    │ │       end_symbol
            │ │    │ └ pending_symbol
            │ │    └ transition_pattern
            │ └ done_symbol
            └ start_symbol
        </pre>
        </div>
        </div>

    **Example:**

    To get the classic blocky look, you can do the following:

    .. code-block:: python

        class BlockProgressTheme(yuio.theme.DefaultTheme):
            msg_decorations = {
                "progress_bar/start_symbol": "|",
                "progress_bar/end_symbol": "|",
                "progress_bar/done_symbol": "█",
                "progress_bar/pending_symbol": " ",
                "progress_bar/transition_pattern": "█▉▊▋▌▍▎▏ ",
            }

``spinner/pattern``
    Defines a sequence of symbols that will be used to show spinners for tasks
    without known progress. Next element of the sequence will be shown
    every :attr:`~Theme.spinner_update_rate_ms`.

    You can find some pre-made patterns in py-spinners__ package.

    __ https://github.com/ManrajGrover/py-spinners?tab=readme-ov-file

``spinner/static_symbol``
    Static spinner symbol, for sub-tasks that've finished running but'.

:samp:`hr/{weight}/{position}`
    Decorations for horizontal rulers (see :func:`yuio.io.hr`
    and :func:`yuio.string.Hr`).

    Default theme defines three weights:

    -   ``0`` prints no ruler (but still prints centered text),
    -   ``1`` prints normal ruler,
    -   ``2`` prints bold ruler.

    Available positions are:

    :``left_start``:
        Start of the ruler to the left of the message.
    :``left_middle``:
        Filler of the ruler to the left of the message.
    :``left_end``:
        End of the ruler to the left of the message.
    :``middle``:
        Filler of the ruler that's used if ``msg`` is empty.
    :``right_start``:
        Start of the ruler to the right of the message.
    :``right_middle``:
        Filler of the ruler to the right of the message.
    :``right_end``:
        End of the ruler to the right of the message.

    .. raw:: html

        <div class="highlight-text notranslate">
        <div class="highlight">
        <pre class="ascii-graphics">
            <span class="k"><------>message<------></span>
            │└┬───┘│       │└┬───┘│
            │ │    │       │ │   right_end
            │ │    │       │ └ right_middle
            │ │    │       └ right_start
            │ │    └ left_end
            │ └ left_middle
            └ left_start

            <span class="k"><---------------------></span>
            │└┬──────────────────┘│
            │ middle             right_end
            └ left_start
        </pre>
        </div>
        </div>

"""

from __future__ import annotations

import dataclasses
import functools
import os
import pathlib
import warnings
from dataclasses import dataclass
from enum import IntFlag

import yuio.color
import yuio.term
from yuio import _typing as _t

__all__ = [
    "DefaultTheme",
    "RecursiveThemeWarning",
    "TableJunction",
    "Theme",
    "ThemeWarning",
    "load",
]

K = _t.TypeVar("K")
V = _t.TypeVar("V")


class ThemeWarning(yuio.YuioWarning):
    pass


class RecursiveThemeWarning(ThemeWarning):
    pass


class _ImmutableDictProxy(_t.Mapping[K, V], _t.Generic[K, V]):  # pragma: no cover
    def __init__(self, data: dict[K, V], /, *, attr: str):
        self.__data = data
        self.__attr = attr

    def items(self) -> _t.ItemsView[K, V]:
        return self.__data.items()

    def keys(self) -> _t.KeysView[K]:
        return self.__data.keys()

    def values(self) -> _t.ValuesView[V]:
        return self.__data.values()

    def __len__(self):
        return len(self.__data)

    def __getitem__(self, key):
        return self.__data[key]

    def __iter__(self):
        return iter(self.__data)

    def __contains__(self, key):
        return key in self.__data

    def __repr__(self):
        return repr(self.__data)

    def __setitem__(self, key, item):
        raise RuntimeError(f"Theme.{self.__attr} is immutable")

    def __delitem__(self, key):
        raise RuntimeError(f"Theme.{self.__attr} is immutable")


class Theme:
    """
    Base class for Yuio themes.

    .. warning::

        Do not change theme contents after it was passed to :func:`yuio.io.setup`.
        Otherwise there's a risc of race conditions.

    """

    msg_decorations: _t.Mapping[str, str] = {}
    """
    Decorative symbols for certain text elements, such as headings,
    list items, etc.

    This mapping becomes immutable once a theme class is created. The only possible
    way to modify it is by using :meth:`~Theme.set_msg_decoration`
    or :meth:`~Theme._set_msg_decoration_if_not_overridden`.

    """

    __msg_decorations: dict[str, str]
    """
    An actual mutable version of :attr:`~Theme.msg_decorations`
    is kept here, because ``__init_subclass__`` will replace
    :attr:`~Theme.msg_decorations` with an immutable proxy.

    """

    __msg_decoration_sources: dict[str, type | None] = {}
    """
    Keeps track of where a message decoration was inherited from. This var is used
    to avoid ``__init__``-ing message decorations that were overridden in a subclass.

    """

    table_drawing_symbols: _t.Mapping[int, str] = {}
    """
    TODO!
    """

    __table_drawing_symbols: dict[int, str] = {}
    """
    An actual mutable version of :attr:`~Theme.table_drawing_symbols`
    is kept here, because ``__init_subclass__`` will replace
    :attr:`~Theme.table_drawing_symbols` with an immutable proxy.

    """

    __table_drawing_symbol_sources: dict[int, type | None] = {}
    """
    Keeps track of where a table drawing symbol was inherited from. This var is used
    to avoid ``__init__``-ing table drawing symbols that were overridden in a subclass.

    """

    progress_bar_width: int = 15
    """
    Width of a progress bar for :class:`yuio.io.Task`.

    """

    spinner_update_rate_ms: int = 200
    """
    How often the spinner pattern changes.

    """

    colors: _t.Mapping[str, str | yuio.color.Color] = {}
    """
    Mapping of color paths to actual colors.

    Themes use color paths to describe styles and colors for different
    parts of an application. Color paths are similar to file paths,
    they use snake case identifiers separated by slashes, and consist of
    two parts separated by a colon.

    The first part represents an object, i.e. what we're coloring.

    The second part represents a context, i.e. what is the state or location
    of an object that we're coloring.

    For example, a color for the filled part of the task's progress bar
    has path ``"task/progressbar/done"``, a color for a text of an error
    log record has path ``"log/message:error"``, and a color for a string escape
    sequence in a highlighted python code has path ``"hl/str/esc:python"``.

    A color at a certain path is propagated to all sub-paths. For example,
    if ``"task/progressbar"`` is bold, and ``"task/progressbar/done"`` is green,
    the final color will be bold green.

    Each color path can be associated with an instance of :class:`~yuio.color.Color`
    or with another path.

    If path is mapped to a :class:`~yuio.color.Color`, then the path is associated
    with that particular color.

    If path is mapped to another path, then the path is associated with
    the color value for that other path (please don't create recursions here).

    You can combine multiple paths within the same mapping by separating them with
    whitespaces. In this case colors for those paths are combined.

    For example:

    .. code-block:: python

        colors = {
            "heading_color": "bold",
            "error_color": "red",
            "tb/heading": "heading_color error_color",
        }

    Here, color of traceback's heading ``"tb/heading"`` will be bold and red.

    When deriving from a theme, you can override this mapping. When looking up
    colors via :meth:`~Theme.get_color`, base classes will be tried for color,
    in order of method resolution.

    This mapping becomes immutable once a theme class is created. The only possible
    way to modify it is by using :meth:`~Theme.set_color`
    or :meth:`~Theme._set_color_if_not_overridden`.

    """

    __colors: dict[str, str | yuio.color.Color]
    """
    An actual mutable version of :attr:`~Theme.colors`
    is kept here, because ``__init_subclass__`` will replace
    :attr:`~Theme.colors` with an immutable proxy.

    """

    __color_sources: dict[str, type | None] = {}
    """
    Keeps track of where a color was inherited from. This var is used
    to avoid ``__init__``-ing colors that were overridden in a subclass.

    """

    __expected_source: type | None = None
    """
    When running an ``__init__`` function, this variable will be set to the class
    that implemented it, regardless of type of ``self``.

    That is, inside ``DefaultTheme.__init__``, ``__expected_source`` is set
    to ``DefaultTheme``, in ``MyTheme.__init__`` it is ``MyTheme``, etc.

    This is possible because ``__init_subclass__`` wraps any implementation
    of ``__init__`` into a wrapper that sets this variable.

    """

    def __init__(self):
        self.__color_cache: dict[str, yuio.color.Color | None] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        colors = {}
        color_sources = {}
        for base in reversed(cls.__mro__):
            base_colors = getattr(base, "_Theme__colors", {})
            colors.update(base_colors)
            base_color_sources = getattr(base, "_Theme__color_sources", {})
            color_sources.update(base_color_sources)

        colors.update(cls.colors)
        color_sources.update(dict.fromkeys(cls.colors.keys(), cls))

        cls.__colors = colors
        cls.__color_sources = color_sources
        cls.colors = _ImmutableDictProxy(cls.__colors, attr="colors")

        msg_decorations = {}
        msg_decoration_sources = {}
        for base in reversed(cls.__mro__):
            base_msg_decorations = getattr(base, "_Theme__msg_decorations", {})
            msg_decorations.update(base_msg_decorations)
            base_msg_decoration_sources = getattr(
                base, "_Theme__msg_decoration_sources", {}
            )
            msg_decoration_sources.update(base_msg_decoration_sources)

        msg_decorations.update(cls.msg_decorations)
        msg_decoration_sources.update(dict.fromkeys(cls.msg_decorations.keys(), cls))

        cls.__msg_decorations = msg_decorations
        cls.__msg_decoration_sources = msg_decoration_sources
        cls.msg_decorations = _ImmutableDictProxy(
            cls.__msg_decorations, attr="msg_decorations"
        )

        table_drawing_symbols = {}
        table_drawing_symbol_sources = {}
        for base in reversed(cls.__mro__):
            base_table_drawing_symbols = getattr(
                base, "_Theme__table_drawing_symbols", {}
            )
            table_drawing_symbols.update(base_table_drawing_symbols)
            base_table_drawing_symbol_sources = getattr(
                base, "_Theme__table_drawing_symbol_sources", {}
            )
            table_drawing_symbol_sources.update(base_table_drawing_symbol_sources)

        table_drawing_symbols.update(cls.table_drawing_symbols)
        table_drawing_symbol_sources.update(
            dict.fromkeys(cls.table_drawing_symbols.keys(), cls)
        )

        cls.__table_drawing_symbols = table_drawing_symbols
        cls.__table_drawing_symbol_sources = table_drawing_symbol_sources
        cls.table_drawing_symbols = _ImmutableDictProxy(
            cls.__table_drawing_symbols, attr="table_drawing_symbols"
        )

        if init := cls.__dict__.get("__init__", None):

            @functools.wraps(init)
            def _wrapped_init(_self, *args, **kwargs):
                prev_expected_source = _self._Theme__expected_source
                _self._Theme__expected_source = cls
                try:
                    return init(_self, *args, **kwargs)
                finally:
                    _self._Theme__expected_source = prev_expected_source

            cls.__init__ = _wrapped_init  # type: ignore

    def _set_msg_decoration_if_not_overridden(
        self,
        name: str,
        msg_decoration: str,
        /,
    ):
        """
        Set message decoration by name, but only if it wasn't overridden
        in a subclass.

        This method should be called from ``__init__`` implementations
        to dynamically set message decorations. It will only set the decoration
        if it was not overridden by any child class.

        """

        if self.__expected_source is None:
            raise RuntimeError(
                "_set_msg_decoration_if_not_overridden should only be called from __init__"
            )
        source = self.__msg_decoration_sources.get(name, Theme)
        # The class that's `__init__` is currently running should be a parent
        # of the msg_decoration's source. This means that the msg_decoration was assigned by a parent.
        if source is not None and issubclass(self.__expected_source, source):
            self.set_msg_decoration(name, msg_decoration)

    def set_msg_decoration(
        self,
        name: str,
        msg_decoration: str,
        /,
    ):
        """
        Set message decoration by name.

        """

        if "_Theme__msg_decorations" not in self.__dict__:
            self.__msg_decorations = self.__class__.__msg_decorations.copy()
            self.__msg_decoration_sources = (
                self.__class__.__msg_decoration_sources.copy()
            )
            self.msg_decorations = _ImmutableDictProxy(
                self.__msg_decorations, attr="msg_decorations"
            )
        self.__msg_decorations[name] = msg_decoration
        self.__msg_decoration_sources[name] = self.__expected_source

    def _set_table_drawing_symbol_if_not_overridden(
        self,
        code: int,
        table_drawing_symbol: str,
        /,
    ):
        """
        Set table drawing symbol by code, but only if it wasn't overridden
        in a subclass.

        This method should be called from ``__init__`` implementations
        to dynamically set table drawing symbols. It will only set the symbol
        if it was not overridden by any child class.

        """

        if self.__expected_source is None:
            raise RuntimeError(
                "_set_table_drawing_symbol_if_not_overridden should only be called from __init__"
            )
        source = self.__table_drawing_symbol_sources.get(code, Theme)
        # The class that's `__init__` is currently running should be a parent
        # of the table_drawing_symbol's source. This means that the table_drawing_symbol was assigned by a parent.
        if source is not None and issubclass(self.__expected_source, source):
            self.set_table_drawing_symbol(code, table_drawing_symbol)

    def set_table_drawing_symbol(
        self,
        code: int,
        table_drawing_symbol: str,
        /,
    ):
        """
        Set table drawing symbol by code.

        """

        if "_Theme__table_drawing_symbols" not in self.__dict__:
            self.__table_drawing_symbols = self.__class__.__table_drawing_symbols.copy()
            self.__table_drawing_symbol_sources = (
                self.__class__.__table_drawing_symbol_sources.copy()
            )
            self.table_drawing_symbols = _ImmutableDictProxy(
                self.__table_drawing_symbols, attr="table_drawing_symbols"
            )
        self.__table_drawing_symbols[code] = table_drawing_symbol
        self.__table_drawing_symbol_sources[code] = self.__expected_source

    def _set_color_if_not_overridden(
        self,
        path: str,
        color: str | yuio.color.Color,
        /,
    ):
        """
        Set color by path, but only if the color was not overridden in a subclass.

        This method should be called from ``__init__`` implementations
        to dynamically set colors. It will only set the color if it was not overridden
        by any child class.

        """

        if self.__expected_source is None:
            raise RuntimeError(
                "_set_color_if_not_overridden should only be called from __init__"
            )
        source = self.__color_sources.get(path, Theme)
        # The class who's `__init__` is currently running should be a parent
        # of the color's source. This means that the color was assigned by a parent.
        if source is not None and issubclass(self.__expected_source, source):
            self.set_color(path, color)

    def set_color(
        self,
        path: str,
        color: str | yuio.color.Color,
        /,
    ):
        """
        Set color by path.

        """

        if "_Theme__colors" not in self.__dict__:
            self.__colors = self.__class__.__colors.copy()
            self.__color_sources = self.__class__.__color_sources.copy()
            self.colors = _ImmutableDictProxy(self.__colors, attr="colors")
        self.__colors[path] = color
        self.__color_sources[path] = self.__expected_source
        self.__color_cache.clear()
        self.__dict__.pop("_Theme__color_tree", None)

    @dataclass(kw_only=True, slots=True)
    class __ColorTree:
        """
        Prefix-like tree that contains all of the theme's colors.

        """

        colors: str | yuio.color.Color = yuio.color.Color.NONE
        """
        Colors in this node.

        """

        loc: dict[str, Theme.__ColorTree] = dataclasses.field(default_factory=dict)
        """
        Location part of the tree.

        """

        ctx: dict[str, Theme.__ColorTree] = dataclasses.field(default_factory=dict)
        """
        Context part of the tree.

        """

    @functools.cached_property
    def __color_tree(self) -> Theme.__ColorTree:
        root = self.__ColorTree()

        for path, colors in self.__colors.items():
            loc, ctx = self.__parse_path(path)

            node = root

            for part in loc:
                if part not in node.loc:
                    node.loc[part] = self.__ColorTree()
                node = node.loc[part]

            for part in ctx:
                if part not in node.ctx:
                    node.ctx[part] = self.__ColorTree()
                node = node.ctx[part]

            node.colors = colors

        return root

    @staticmethod
    def __parse_path(path: str, /) -> tuple[list[str], list[str]]:
        path_parts = path.split(":", maxsplit=1)
        if len(path_parts) == 1:
            loc, ctx = path_parts[0], ""
        else:
            loc, ctx = path_parts
        return loc.split("/") if loc else [], ctx.split("/") if ctx else []

    @_t.final
    def get_color(self, paths: str, /) -> yuio.color.Color:
        """
        Lookup a color by path.

        """

        color = yuio.color.Color.NONE
        for path in paths.split():
            color |= self.__get_color(path)
        return color

    def __get_color(self, path: str, /) -> yuio.color.Color:
        res: yuio.color.Color | None | yuio.Missing = self.__color_cache.get(
            path, yuio.MISSING
        )
        if res is None:
            warnings.warn(f"recursive color path {path!r}", RecursiveThemeWarning)
            return yuio.color.Color.NONE
        elif res is not yuio.MISSING:
            return res

        self.__color_cache[path] = None
        if path.startswith("#") and len(path) == 7:
            try:
                res = yuio.color.Color.fore_from_hex(path)
            except ValueError as e:
                warnings.warn(f"invalid color code {path!r}: {e}", ThemeWarning)
                res = yuio.color.Color.NONE
        elif path[:3].lower() == "bg#" and len(path) == 9:
            try:
                res = yuio.color.Color.back_from_hex(path[2:])
            except ValueError as e:
                warnings.warn(f"invalid color code {path!r}: {e}", ThemeWarning)
                res = yuio.color.Color.NONE
        else:
            loc, ctx = self.__parse_path(path)
            res = self.__get_color_in_loc(self.__color_tree, loc, ctx)
        self.__color_cache[path] = res
        return res

    def __get_color_in_loc(
        self, node: Theme.__ColorTree, loc: list[str], ctx: list[str]
    ):
        color = yuio.color.Color.NONE

        for part in loc:
            if part not in node.loc:
                break
            color |= self.__get_color_in_ctx(node, ctx)
            node = node.loc[part]

        return color | self.__get_color_in_ctx(node, ctx)

    def __get_color_in_ctx(self, node: Theme.__ColorTree, ctx: list[str]):
        color = yuio.color.Color.NONE

        for part in ctx:
            if part not in node.ctx:
                break
            color |= self.__get_color_in_node(node)
            node = node.ctx[part]

        return color | self.__get_color_in_node(node)

    def __get_color_in_node(self, node: Theme.__ColorTree) -> yuio.color.Color:
        color = yuio.color.Color.NONE

        if isinstance(node.colors, str):
            color |= self.get_color(node.colors)
        else:
            color |= node.colors

        return color

    def to_color(
        self, color_or_path: yuio.color.Color | str | None, /
    ) -> yuio.color.Color:
        """
        Convert color or color path to color.

        """

        if color_or_path is None:
            return yuio.color.Color.NONE
        elif isinstance(color_or_path, yuio.color.Color):
            return color_or_path
        else:
            return self.get_color(color_or_path)

    def check(self):
        """
        Check theme for recursion.

        This method is slow, and should be called from unit tests of your application.

        """

        if "" in self.colors:
            warnings.warn("colors map contains an empty key", ThemeWarning)

        for k, v in self.colors.items():
            if not v:
                warnings.warn(f"color value for path {k!r} is empty", ThemeWarning)

        err_path = None
        with warnings.catch_warnings():
            warnings.simplefilter("error", category=RecursiveThemeWarning)
            for k in self.colors:
                try:
                    self.get_color(k)
                except RecursiveThemeWarning:
                    err_path = k
        if err_path is None:
            return

        self.__color_cache.clear()
        recursive_path = []
        get_color_inner = self.__get_color

        def get_color(path: str):
            recursive_path.append(path)
            return get_color_inner(path)

        self.__get_color = get_color

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", category=RecursiveThemeWarning)
                self.get_color(err_path)
        except RecursiveThemeWarning:
            self.__get_color = get_color_inner
        else:
            assert False, (
                "unreachable, please report hitting this assert "
                "to https://github.com/taminomara/yuio/issues"
            )

        raise RecursiveThemeWarning(
            f"infinite recursion in color path {err_path!r}:\n  "
            + "\n  ".join(
                f"{path!r} -> {self.colors.get(path)!r}" for path in recursive_path[:-1]
            )
        )


Theme.__init_subclass__()


class DefaultTheme(Theme):
    """
    Default Yuio theme. Adapts for terminal background color,
    if one can be detected.

    This theme defines *main colors*, which you can override by subclassing.

    - ``"heading_color"``: for headings,
    - ``"primary_color"``: for main text,
    - ``"accent_color"``, ``"accent_color_2"``: for visually highlighted elements,
    - ``"secondary_color"``: for visually dimmed elements,
    - ``"error_color"``: for everything that indicates an error,
    - ``"warning_color"``: for everything that indicates a warning,
    - ``"success_color"``: for everything that indicates a success,
    - ``"critical_color"``: for critical or internal errors,
    - ``"low_priority_color_a"``: for auxiliary elements such as help widget,
    - ``"low_priority_color_b"``: for auxiliary elements such as help widget,
      even lower priority.

    """

    colors = {
        #
        # Main settings
        # -------------
        # This section controls the overall theme look.
        # Most likely you'll want to change accent colors from here.
        "heading_color": "bold primary_color",
        "primary_color": "normal",
        "accent_color": "magenta",
        "accent_color_2": "cyan",
        "secondary_color": "normal_dim",
        "error_color": "red",
        "warning_color": "yellow",
        "success_color": "green",
        "critical_color": "inverse error_color",
        "low_priority_color_a": "normal_dim",
        "low_priority_color_b": "normal_dim",
        #
        # Common tags
        # -----------
        "code": "italic",
        "note": "accent_color_2",
        "path": "code",
        "flag": "note",
        #
        # Styles
        # ------
        "bold": yuio.color.Color.STYLE_BOLD,
        "b": "bold",
        "dim": yuio.color.Color.STYLE_DIM,
        "d": "dim",
        "italic": yuio.color.Color.STYLE_ITALIC,
        "i": "italic",
        "underline": yuio.color.Color.STYLE_UNDERLINE,
        "u": "underline",
        "inverse": yuio.color.Color.STYLE_INVERSE,
        #
        # Foreground
        # ----------
        # Note: we don't have tags for background because it's impossible to guarantee
        # that they'll work nicely with whatever foreground you choose. Prefer using
        # `inverse` instead.
        "normal": yuio.color.Color.FORE_NORMAL,
        "normal_dim": yuio.color.Color.FORE_NORMAL_DIM,
        "black": yuio.color.Color.FORE_BLACK,
        "red": yuio.color.Color.FORE_RED,
        "green": yuio.color.Color.FORE_GREEN,
        "yellow": yuio.color.Color.FORE_YELLOW,
        "blue": yuio.color.Color.FORE_BLUE,
        "magenta": yuio.color.Color.FORE_MAGENTA,
        "cyan": yuio.color.Color.FORE_CYAN,
        "white": yuio.color.Color.FORE_WHITE,
        #
        # IO messages and text
        # --------------------
        "msg/decoration": "secondary_color",
        "msg/decoration:heading": "heading_color accent_color",
        "msg/decoration:thematic_break": "secondary_color",
        "msg/text": "primary_color",
        "msg/text:heading": "heading_color",
        "msg/text:heading/1": "accent_color",
        "msg/text:heading/section": "green",
        "msg/text:question": "heading_color",
        "msg/text:error": "error_color",
        "msg/text:warning": "warning_color",
        "msg/text:success": "heading_color success_color",
        "msg/text:failure": "heading_color error_color",
        "msg/text:info": "primary_color",
        "msg/text:thematic_break": "secondary_color",
        #
        # Log messages
        # ------------
        "log/name": "dim accent_color_2",
        "log/pathname": "dim",
        "log/filename": "dim",
        "log/module": "dim",
        "log/lineno": "dim",
        "log/funcName": "dim",
        "log/created": "dim",
        "log/asctime": "dim",
        "log/msecs": "dim",
        "log/relativeCreated": "dim",
        "log/thread": "dim",
        "log/threadName": "dim",
        "log/taskName": "dim",
        "log/process": "dim",
        "log/processName": "dim",
        "log/levelno": "log/levelname",
        "log/levelno:critical": "log/levelname:critical",
        "log/levelno:error": "log/levelname:error",
        "log/levelno:warning": "log/levelname:warning",
        "log/levelno:info": "log/levelname:info",
        "log/levelno:debug": "log/levelname:debug",
        "log/levelname": "heading_color",
        "log/levelname:critical": "critical_color",
        "log/levelname:error": "error_color",
        "log/levelname:warning": "warning_color",
        "log/levelname:info": "success_color",
        "log/levelname:debug": "dim",
        "log/message": "primary_color",
        "log/message:critical": "bold error_color",
        "log/message:debug": "dim",
        "log/colMessage": "log/message",
        "log/colMessage:critical": "log/message:critical",
        "log/colMessage:error": "log/message:error",
        "log/colMessage:warning": "log/message:warning",
        "log/colMessage:info": "log/message:info",
        "log/colMessage:debug": "log/message:debug",
        #
        # Tasks and progress bars
        # -----------------------
        "task": "secondary_color",
        "task/decoration": "msg/decoration:heading",
        "task/decoration:running": "accent_color",
        "task/decoration:done": "success_color",
        "task/decoration:error": "error_color",
        "task/progressbar/done": "accent_color",
        "task/progressbar/done/start": "blue",
        "task/progressbar/done/end": "accent_color",
        "task/progressbar/pending": "secondary_color",
        "task/heading": "heading_color",
        "task/progress": "secondary_color",
        "task/comment": "primary_color",
        #
        # Syntax highlighting
        # -------------------
        "hl/kwd": "bold",
        "hl/str": "yellow",
        "hl/str/esc": "accent_color",
        "hl/punct": "secondary_color",
        "hl/comment": "green",
        "hl/lit": "blue",
        "hl/type": "cyan",
        "hl/prog": "bold underline",
        "hl/flag": "flag",
        "hl/meta": "accent_color",
        "hl/added": "green",
        "hl/removed": "red",
        "hl/error": "bold error_color",
        "tb/heading": "bold error_color",
        "tb/message": "tb/heading",
        "tb/frame/usr/file/module": "accent_color",
        "tb/frame/usr/file/line": "accent_color",
        "tb/frame/usr/file/path": "accent_color",
        "tb/frame/usr/code": "primary_color",
        "tb/frame/usr/highlight": "low_priority_color_a",
        "tb/frame/lib": "dim",
        "tb/frame/lib/file/module": "tb/frame/usr/file/module",
        "tb/frame/lib/file/line": "tb/frame/usr/file/line",
        "tb/frame/lib/file/path": "tb/frame/usr/file/path",
        "tb/frame/lib/code": "tb/frame/usr/code",
        "tb/frame/lib/highlight": "tb/frame/usr/highlight",
        #
        # Menu and widgets
        # ----------------
        "menu/text": "primary_color",
        "menu/text/heading": "menu/text heading_color",
        "menu/text/help_info:help": "low_priority_color_a",
        "menu/text/help_msg:help": "low_priority_color_b",
        "menu/text/help_key:help": "low_priority_color_a",
        "menu/text/help_sep:help": "low_priority_color_b",
        "menu/text/help_key:help_menu": "accent_color_2",
        "menu/text/help_sep:help_menu": "secondary_color",
        "menu/text/esc": "white on_magenta",
        "menu/text/error": "bold underline error_color",
        "menu/text/comment": "accent_color_2",
        "menu/text:choice/active": "accent_color",
        "menu/text:choice/active/selected": "bold",
        "menu/text:choice/normal/selected": "accent_color_2 bold",
        "menu/text:choice/normal/dir": "blue",
        "menu/text:choice/normal/exec": "red",
        "menu/text:choice/normal/symlink": "magenta",
        "menu/text:choice/normal/socket": "green",
        "menu/text:choice/normal/pipe": "yellow",
        "menu/text:choice/normal/block_device": "cyan bold",
        "menu/text:choice/normal/char_device": "yellow bold",
        "menu/text/comment:choice/normal/original": "success_color",
        "menu/text/comment:choice/active/original": "success_color",
        "menu/text/comment:choice/normal/corrected": "error_color",
        "menu/text/comment:choice/active/corrected": "error_color",
        "menu/text/prefix:choice/normal": "primary_color",
        "menu/text/prefix:choice/normal/selected": "accent_color_2 bold",
        "menu/text/prefix:choice/active": "accent_color",
        "menu/text/prefix:choice/active/selected": "bold",
        "menu/text/suffix:choice/normal": "primary_color",
        "menu/text/suffix:choice/normal/selected": "accent_color_2 bold",
        "menu/text/suffix:choice/active": "accent_color",
        "menu/text/suffix:choice/active/selected": "bold",
        "menu/text:choice/status_line": "low_priority_color_b",
        "menu/text:choice/status_line/number": "low_priority_color_a",
        "menu/text/placeholder": "secondary_color",
        "menu/decoration": "accent_color",
        "menu/decoration/quick-select": "secondary_color",
        "menu/decoration/comment": "secondary_color",
        "menu/decoration:choice/normal": "menu/text",
    }
    """
    Colors for default theme are separated into several sections.

    The main section (the first one) has common settings which are referenced
    from all other sections. You'll probably want to override

    """

    def __init__(self, term: yuio.term.Term):
        super().__init__()

        if term.is_unicode:
            decorations = _MSG_DECORATIONS_UNICODE
            table_symbols = _TABLE_SYMBOLS_UNICODE
        else:
            decorations = _MSG_DECORATIONS_ASCII
            table_symbols = _TABLE_SYMBOLS_ASCII
        for k, v in decorations.items():
            self._set_msg_decoration_if_not_overridden(k, v)
        for k, v in table_symbols.items():
            self._set_table_drawing_symbol_if_not_overridden(k, v)

        if (colors := term.terminal_theme) is None:
            return

        # Gradients look bad in other modes.
        if term.supports_colors_true:
            self._set_color_if_not_overridden(
                "normal", yuio.color.Color(fore=colors.foreground)
            )
            self._set_color_if_not_overridden(
                "black", yuio.color.Color(fore=colors.black)
            )
            self._set_color_if_not_overridden(
                "red",
                yuio.color.Color(fore=colors.red),
            )
            self._set_color_if_not_overridden(
                "green", yuio.color.Color(fore=colors.green)
            )
            self._set_color_if_not_overridden(
                "yellow", yuio.color.Color(fore=colors.yellow)
            )
            self._set_color_if_not_overridden(
                "blue", yuio.color.Color(fore=colors.blue)
            )
            self._set_color_if_not_overridden(
                "magenta", yuio.color.Color(fore=colors.magenta)
            )
            self._set_color_if_not_overridden(
                "cyan", yuio.color.Color(fore=colors.cyan)
            )
            self._set_color_if_not_overridden(
                "white", yuio.color.Color(fore=colors.white)
            )

        if colors.lightness == yuio.term.Lightness.UNKNOWN:
            return

        background = colors.background
        foreground = colors.foreground

        if colors.lightness is colors.lightness.DARK:
            self._set_color_if_not_overridden(
                "low_priority_color_a",
                yuio.color.Color(
                    fore=foreground.match_luminosity(background.lighten(0.30))
                ),
            )
            self._set_color_if_not_overridden(
                "low_priority_color_b",
                yuio.color.Color(
                    fore=foreground.match_luminosity(background.lighten(0.25))
                ),
            )
        else:
            self._set_color_if_not_overridden(
                "low_priority_color_a",
                yuio.color.Color(
                    fore=foreground.match_luminosity(background.darken(0.30))
                ),
            )
            self._set_color_if_not_overridden(
                "low_priority_color_b",
                yuio.color.Color(
                    fore=foreground.match_luminosity(background.darken(0.25))
                ),
            )


def load(
    term: yuio.term.Term,
    theme_ctor: _t.Callable[[yuio.term.Term], Theme] | None = None,
    /,
) -> Theme:
    """
    Loads a default theme.

    """

    # NOTE: loading themes from json is beta, don't use it yet.

    if theme_ctor is None:
        theme_ctor = DefaultTheme

    if not (path := os.environ.get("YUIO_THEME_PATH")):
        return theme_ctor(term)

    import yuio.config
    import yuio.parse

    class ThemeData(yuio.config.Config):
        include: list[str] | str | None = None
        progress_bar_width: _t.Annotated[int, yuio.parse.Ge(0)] | None = None
        spinner_update_rate_ms: _t.Annotated[int, yuio.parse.Ge(0)] | None = None
        msg_decorations: dict[str, str] = yuio.config.field(
            default={},
            merge=lambda l, r: {**l, **r},
        )
        colors: dict[str, str] = yuio.config.field(
            default={},
            merge=lambda l, r: {**l, **r},
        )

    seen = set()
    stack = [pathlib.Path(path)]
    loaded_partials = []
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        if not path.exists():
            warnings.warn(f"theme file {path} does not exist", ThemeWarning)
            continue
        if not path.is_file():
            warnings.warn(f"theme file {path} is not a file", ThemeWarning)
            continue
        try:
            loaded = ThemeData.load_from_json_file(path, ignore_unknown_fields=True)
        except yuio.parse.ParsingError as e:
            warnings.warn(str(e), ThemeWarning)
            continue
        loaded_partials.append(loaded)
        include = loaded.include
        if isinstance(include, str):
            include = [include]
        if include:
            stack.extend([path.parent / new_path for new_path in include])

    theme_data = ThemeData()
    for partial in reversed(loaded_partials):
        theme_data.update(partial)

    theme = theme_ctor(term)

    if theme_data.progress_bar_width is not None:
        theme.progress_bar_width = theme_data.progress_bar_width
    if theme_data.spinner_update_rate_ms is not None:
        theme.spinner_update_rate_ms = theme_data.spinner_update_rate_ms

    for k, v in theme_data.msg_decorations.items():
        theme.set_msg_decoration(k, v)

    for k, v in theme_data.colors.items():
        theme.set_color(k, v)

    return theme


class TableJunction(IntFlag):
    WEST = 1 << 0
    WEST_ALT = 1 << 1
    SOUTH = 1 << 2
    SOUTH_ALT = 1 << 3
    EAST = 1 << 4
    EAST_ALT = 1 << 5
    NORTH = 1 << 6
    NORTH_ALT = 1 << 7
    ALT_STYLE = 1 << 8

    def __repr__(self) -> str:
        res = "".join(
            [
                ["", "n", "", "N"][
                    bool(self & self.NORTH) + 2 * bool(self & self.NORTH_ALT)
                ],
                ["", "e", "", "E"][
                    bool(self & self.EAST) + 2 * bool(self & self.EAST_ALT)
                ],
                ["", "s", "", "S"][
                    bool(self & self.SOUTH) + 2 * bool(self & self.SOUTH_ALT)
                ],
                ["", "w", "", "W"][
                    bool(self & self.WEST) + 2 * bool(self & self.WEST_ALT)
                ],
                ["-", "="][bool(self & self.ALT_STYLE)],
            ]
        )
        return f"<{self.__class__.__name__} {res}>"


_MSG_DECORATIONS_UNICODE: dict[str, str] = {
    "heading/section": "",
    "heading/1": "⣿ ",
    "heading/2": "",
    "heading/3": "",
    "heading/4": "",
    "heading/5": "",
    "heading/6": "",
    "question": "> ",
    "task": "> ",
    "thematic_break": "╌╌╌╌╌╌╌╌",
    "list": "•   ",
    "quote": ">   ",
    "code": " " * 8,
    "overflow": "…",
    "hr/1/left_start": "─",
    "hr/1/left_middle": "─",
    "hr/1/left_end": "╴",
    "hr/1/middle": "─",
    "hr/1/right_start": "╶",
    "hr/1/right_middle": "─",
    "hr/1/right_end": "─",
    "hr/2/left_start": "━",
    "hr/2/left_middle": "━",
    "hr/2/left_end": "╸",
    "hr/2/middle": "━",
    "hr/2/right_start": "╺",
    "hr/2/right_middle": "━",
    "hr/2/right_end": "━",
    "progress_bar/start_symbol": "",
    "progress_bar/end_symbol": "",
    "progress_bar/done_symbol": "■",  # "█",
    "progress_bar/pending_symbol": "□",  # " ",
    "progress_bar/transition_pattern": "",  # "█▉▊▋▌▍▎▏ ",
    "spinner/pattern": "⣤⣤⣤⠶⠛⠛⠛⠶",
    "spinner/static_symbol": "⣿",
    # TODO: support these in widgets
    # 'menu/current_item': '▶︎',
    # 'menu/selected_item': '★',
    # 'menu/default_item': '★',
    # 'menu/select': '#',
    # 'menu/search': '/',
}

# fmt: off
_TABLE_SYMBOLS_UNICODE: dict[int, str] = {
    0x000: " ", 0x040: "╵", 0x0C0: "╹", 0x010: "╶", 0x050: "└", 0x0D0: "┖", 0x030: "╺",
    0x070: "┕", 0x0F0: "┗", 0x001: "╴", 0x041: "┘", 0x0C1: "┚", 0x011: "─", 0x051: "┴",
    0x0D1: "┸", 0x031: "╼", 0x071: "┶", 0x0F1: "┺", 0x003: "╸", 0x043: "┙", 0x0C3: "┛",
    0x013: "╾", 0x053: "┵", 0x0D3: "┹", 0x033: "━", 0x073: "┷", 0x0F3: "┻", 0x004: "╷",
    0x044: "│", 0x0C4: "╿", 0x014: "┌", 0x054: "├", 0x0D4: "┞", 0x034: "┍", 0x074: "┝",
    0x0F4: "┡", 0x005: "┐", 0x045: "┤", 0x0C5: "┦", 0x015: "┬", 0x055: "┼", 0x0D5: "╀",
    0x035: "┮", 0x075: "┾", 0x0F5: "╄", 0x007: "┑", 0x047: "┥", 0x0C7: "┩", 0x017: "┭",
    0x057: "┽", 0x0D7: "╃", 0x037: "┯", 0x077: "┿", 0x0F7: "╇", 0x00C: "╻", 0x04C: "╽",
    0x0CC: "┃", 0x01C: "┎", 0x05C: "┟", 0x0DC: "┠", 0x03C: "┎", 0x07C: "┢", 0x0FC: "┣",
    0x00D: "┒", 0x04D: "┧", 0x0CD: "┨", 0x01D: "┰", 0x05D: "╁", 0x0DD: "╂", 0x03D: "┲",
    0x07D: "╆", 0x0FD: "╊", 0x00F: "┓", 0x04F: "┪", 0x0CF: "┫", 0x01F: "┱", 0x05F: "╅",
    0x0DF: "╉", 0x03F: "┳", 0x07F: "╈", 0x0FF: "╋", 0x100: " ", 0x140: "╵", 0x1C0: "║",
    0x110: "╶", 0x150: "└", 0x1D0: "╙", 0x130: "═", 0x170: "╘", 0x1F0: "╚", 0x101: "╴",
    0x141: "┘", 0x1C1: "╜", 0x111: "─", 0x151: "┴", 0x1D1: "╨", 0x131: "═", 0x171: "╧",
    0x1F1: "╩", 0x103: "╸", 0x143: "╛", 0x1C3: "╝", 0x113: "═", 0x153: "╧", 0x1D3: "╩",
    0x133: "═", 0x173: "╧", 0x1F3: "╩", 0x104: "╷", 0x144: "│", 0x1C4: "║", 0x114: "┌",
    0x154: "├", 0x1D4: "╟", 0x134: "╒", 0x174: "╞", 0x1F4: "╠", 0x105: "┐", 0x145: "┤",
    0x1C5: "╢", 0x115: "┬", 0x155: "┼", 0x1D5: "╫", 0x135: "╤", 0x175: "╪", 0x1F5: "╬",
    0x107: "╕", 0x147: "╡", 0x1C7: "╣", 0x117: "╤", 0x157: "╪", 0x1D7: "╬", 0x137: "╤",
    0x177: "╪", 0x1F7: "╬", 0x10C: "║", 0x14C: "║", 0x1CC: "║", 0x11C: "╓", 0x15C: "╟",
    0x1DC: "╟", 0x13C: "╔", 0x17C: "╠", 0x1FC: "╠", 0x10D: "╖", 0x14D: "╢", 0x1CD: "╢",
    0x11D: "╥", 0x15D: "╫", 0x1DD: "╫", 0x13D: "╦", 0x17D: "╬", 0x1FD: "╬", 0x10F: "╗",
    0x14F: "╣", 0x1CF: "╣", 0x11F: "╦", 0x15F: "╬", 0x1DF: "╬", 0x13F: "╦", 0x17F: "╬",
    0x1FF: "╬",
}
# fmt: on

_MSG_DECORATIONS_ASCII: dict[str, str] = {
    "heading/section": "",
    "heading/1": "# ",
    "heading/2": "",
    "heading/3": "",
    "heading/4": "",
    "heading/5": "",
    "heading/6": "",
    "question": "> ",
    "task": "> ",
    "thematic_break": "-" * 8,
    "list": "*   ",
    "quote": ">   ",
    "code": " " * 8,
    "overflow": "~",
    "progress_bar/start_symbol": "[",
    "progress_bar/end_symbol": "]",
    "progress_bar/done_symbol": "-",
    "progress_bar/pending_symbol": " ",
    "progress_bar/transition_pattern": ">",
    "spinner/pattern": "|||/-\\",
    "spinner/static_symbol": ">",
    "hr/1/left_start": "-",
    "hr/1/left_middle": "-",
    "hr/1/left_end": " ",
    "hr/1/middle": "-",
    "hr/1/right_start": " ",
    "hr/1/right_middle": "-",
    "hr/1/right_end": "-",
    "hr/2/left_start": "=",
    "hr/2/left_middle": "=",
    "hr/2/left_end": " ",
    "hr/2/middle": "=",
    "hr/2/right_start": " ",
    "hr/2/right_middle": "=",
    "hr/2/right_end": "=",
    # TODO: support these in widgets
    # 'menu/current_item': '>',
    # 'menu/selected_item': '*',
    # 'menu/default_item': '*',
    # 'menu/select': '#',
    # 'menu/search': '/',
}

# fmt: off
_TABLE_SYMBOLS_ASCII: dict[int, str] = {
    0x000: " ", 0x040: "+", 0x0C0: "+", 0x010: "+", 0x050: "+", 0x0D0: "+", 0x030: "+",
    0x070: "+", 0x0F0: "+", 0x001: "+", 0x041: "+", 0x0C1: "+", 0x011: "-", 0x051: "+",
    0x0D1: "+", 0x031: "+", 0x071: "+", 0x0F1: "+", 0x003: "+", 0x043: "+", 0x0C3: "+",
    0x013: "+", 0x053: "+", 0x0D3: "+", 0x033: "=", 0x073: "+", 0x0F3: "+", 0x004: "+",
    0x044: "|", 0x0C4: "+", 0x014: "+", 0x054: "+", 0x0D4: "+", 0x034: "+", 0x074: "+",
    0x0F4: "+", 0x005: "+", 0x045: "+", 0x0C5: "+", 0x015: "+", 0x055: "+", 0x0D5: "+",
    0x035: "+", 0x075: "+", 0x0F5: "+", 0x007: "+", 0x047: "+", 0x0C7: "+", 0x017: "+",
    0x057: "+", 0x0D7: "+", 0x037: "+", 0x077: "+", 0x0F7: "+", 0x00C: "+", 0x04C: "+",
    0x0CC: "|", 0x01C: "+", 0x05C: "+", 0x0DC: "+", 0x03C: "+", 0x07C: "+", 0x0FC: "+",
    0x00D: "+", 0x04D: "+", 0x0CD: "+", 0x01D: "+", 0x05D: "+", 0x0DD: "+", 0x03D: "+",
    0x07D: "+", 0x0FD: "+", 0x00F: "+", 0x04F: "+", 0x0CF: "+", 0x01F: "+", 0x05F: "+",
    0x0DF: "+", 0x03F: "+", 0x07F: "+", 0x0FF: "+", 0x100: " ", 0x140: "+", 0x1C0: "#",
    0x110: "+", 0x150: "+", 0x1D0: "#", 0x130: "#", 0x170: "#", 0x1F0: "#", 0x101: "+",
    0x141: "+", 0x1C1: "#", 0x111: "-", 0x151: "+", 0x1D1: "#", 0x131: "#", 0x171: "#",
    0x1F1: "#", 0x103: "#", 0x143: "#", 0x1C3: "#", 0x113: "#", 0x153: "#", 0x1D3: "#",
    0x133: "*", 0x173: "#", 0x1F3: "#", 0x104: "+", 0x144: "|", 0x1C4: "#", 0x114: "+",
    0x154: "+", 0x1D4: "#", 0x134: "#", 0x174: "#", 0x1F4: "#", 0x105: "+", 0x145: "+",
    0x1C5: "#", 0x115: "+", 0x155: "+", 0x1D5: "#", 0x135: "#", 0x175: "#", 0x1F5: "#",
    0x107: "#", 0x147: "#", 0x1C7: "#", 0x117: "#", 0x157: "#", 0x1D7: "#", 0x137: "#",
    0x177: "#", 0x1F7: "#", 0x10C: "#", 0x14C: "#", 0x1CC: "*", 0x11C: "#", 0x15C: "#",
    0x1DC: "#", 0x13C: "#", 0x17C: "#", 0x1FC: "#", 0x10D: "#", 0x14D: "#", 0x1CD: "#",
    0x11D: "#", 0x15D: "#", 0x1DD: "#", 0x13D: "#", 0x17D: "#", 0x1FD: "#", 0x10F: "#",
    0x14F: "#", 0x1CF: "#", 0x11F: "#", 0x15F: "#", 0x1DF: "#", 0x13F: "#", 0x17F: "#",
    0x1FF: "#",
}
# fmt: on
