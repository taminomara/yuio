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

    .. autoattribute:: separate_headings

    .. autoattribute:: fallback_width

    .. autoattribute:: msg_decorations_unicode

    .. automethod:: set_msg_decoration_unicode

    .. automethod:: _set_msg_decoration_unicode_if_not_overridden

    .. autoattribute:: msg_decorations_ascii

    .. automethod:: set_msg_decoration_ascii

    .. automethod:: _set_msg_decoration_ascii_if_not_overridden

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

.. autoclass:: BaseTheme

.. autoclass:: DefaultTheme


.. _all-color-paths:

Color paths
-----------

.. _common-tags:

.. color-path:: common tags

    :class:`BaseTheme` sets up commonly used colors that you can use
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
    -   ``muted``: muted foreground (see :attr:`~yuio.color.Color.FORE_NORMAL_DIM`),
    -   ``red``: foreground,
    -   ``green``: foreground,
    -   ``yellow``: foreground,
    -   ``blue``: foreground,
    -   ``magenta``: foreground,
    -   ``cyan``: foreground,

    .. note::

        We don't define ``black`` and ``white`` because they can be invisible
        with some terminal themes. Prefer ``muted`` when you need a muted color.

        We also don't define tags for backgrounds because there's no way to tell
        which foreground/background combination will be readable and which will not.
        Prefer ``inverse`` when you need to add a background.

.. _main-colors:

.. color-path:: main colors

    :class:`DefaultTheme` defines *main colors*, which you can override by subclassing.

    -   ``heading_color``: for headings,
    -   ``primary_color``: for main text,
    -   ``accent_color``, ``accent_color_2``: for visually highlighted elements,
    -   ``secondary_color``: for visually dimmed elements,
    -   ``error_color``: for everything that indicates an error,
    -   ``warning_color``: for everything that indicates a warning,
    -   ``success_color``: for everything that indicates a success,
    -   ``critical_color``: for critical or internal errors,
    -   ``low_priority_color_a``: for auxiliary elements such as help widget,
    -   ``low_priority_color_b``: for auxiliary elements such as help widget,
        even lower priority.

.. _term-colors:

.. color-path:: `term/{color}`

    :class:`DefaultTheme` will export default colors for the attached terminal
    as :samp:`term/{color}`. This is useful when defining gradients for progress bars,
    as they require exact color values for interpolation.

    ``color`` can be one ``background``, ``foreground``, ``black``, ``bright_black``,
    ``red``, ``bright_red``, ``green``, ``bright_green``, ``yellow``, ``bright_yellow``,
    ``blue``, ``bright_blue``, ``magenta``, ``bright_magenta``,
    ``cyan``, ``bright_cyan``, ``white``, or ``bright_white``.

.. color-path:: `msg/decoration:{tag}`

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

.. color-path:: `msg/text:{tag}`

    Color for the text part of messages:

    -   ``msg/text:info`` and all other tags from ``msg/decoration``,
    -   ``msg/text:paragraph``: plain text in markdown,
    -   :samp:`msg/text:code/{syntax}`: plain text in highlighted code blocks.

.. color-path:: `task/...:{status}`

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

.. color-path:: `hl/{token}:{syntax}`

    Color for highlighted part of code:

    -   ``hl/comment``: code comments,
    -   ``hl/kwd``: keyword,
    -   ``hl/lit``: non-string literals,
    -   ``hl/lit/builtin``: built-in literals, i.e. ``None``, ``True``, ``False``,
    -   ``hl/lit/num``: numeric literals,
    -   ``hl/lit/num/bin``: binary numeric literals,
    -   ``hl/lit/num/oct``: octal numeric literals,
    -   ``hl/lit/num/dec``: decimal numeric literals,
    -   ``hl/lit/num/hex``: hexadecimal numeric literals,
    -   ``hl/punct``: punctuation,
    -   ``hl/str``: string literals,
    -   ``hl/str/esc``: escape sequences in strings,
    -   ``hl/str/prefix``: string prefix, i.e. ``f`` in ``f"str"``,
    -   ``hl/type``: type names,
    -   ``hl/type/builtin``: type names for builtin types,
    -   ``hl/type/user``: type names for user-defined types,
    -   ``hl/meta``: diff meta info for diff highlighting,
    -   ``hl/added``: added lines in diff highlighting,
    -   ``hl/removed``: removed lines in diff highlighting,
    -   ``hl/prog``: program name in CLI usage and shell highlighting,
    -   ``hl/flag``: CLI flags,
    -   ``hl/metavar``: meta variables in CLI usage.

.. color-path:: `tb/heading`
                `tb/message`
                `tb/frame/{location}/...`

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

.. color-path:: `log/{part}:{level}`

    Colors for log records. ``part`` is name of a `log record attribute`__,
    level is lowercase name of logging level.

    __ https://docs.python.org/3/library/logging.html#logrecord-attributes

    .. seealso::

        :class:`yuio.io.Formatter`.

.. color-path:: input widget

    Colors for :class:`yuio.widget.Input`:

    -   ``menu/decoration:input``: decoration before an input box,
    -   ``menu/text:input``: entered text in an input box,
    -   ``menu/text/esc:input``: highlights for invisible characters in an input box,
    -   ``menu/text/error:input``: highlights for error region reported by a parser,
    -   ``menu/text/placeholder:input``: placeholder text in an input box,

.. color-path:: grid widgets

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

.. color-path:: full screen help menu

    Colors for help menu that appears when pressing :kbd:`F1`:

    -   ``menu/text/heading:help_menu``: section heading,
    -   ``menu/text/help_key:help_menu``: key names,
    -   ``menu/text/help_sep:help_menu``: separators between key names,
    -   ``menu/decoration:help_menu``: decorations.

.. color-path:: inline help menu

    Colors for help items rendered under a widget:

    -   ``menu/text/help_info:help``: help items that aren't associated with any key,
    -   ``menu/text/help_msg:help``: regular help items,
    -   ``menu/text/help_key:help``: keybinding names,
    -   ``menu/text/help_sep:help``: separator between items.


.. _all-decorations:

Decorations
-----------

.. decoration-path:: `info`

    Messages from :mod:`yuio.io.info`.

.. decoration-path:: `warning`

    Messages from :mod:`yuio.io.warning`.

.. decoration-path:: `error`

    Messages from :mod:`yuio.io.error`.

.. decoration-path:: `success`

    Messages from :mod:`yuio.io.success`.

.. decoration-path:: `failure`

    Messages from :mod:`yuio.io.failure`.

.. decoration-path:: `heading/{level}`

    Messages from :mod:`yuio.io.heading` and headings in markdown.

.. decoration-path:: `heading/section`

    First-level headings in CLI help.

.. decoration-path:: `question`

    Messages from :func:`yuio.io.ask`.

.. decoration-path:: `list`

    Bullets in markdown.

.. decoration-path:: `quote`

    Quote decorations in markdown.

.. decoration-path:: `code`

    Code decorations in markdown.

.. decoration-path:: `thematic_break`

    Thematic breaks (i.e. horizontal rulers) in markdown.

.. decoration-path:: `overflow`

    Ellipsis symbol for lines that don't fit terminal width. Must be one character wide.

.. decoration-path:: `progress_bar/{position}`

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

.. decoration-path:: `spinner/pattern`

    Defines a sequence of symbols that will be used to show spinners for tasks
    without known progress. Next element of the sequence will be shown
    every :attr:`~Theme.spinner_update_rate_ms`.

    You can find some pre-made patterns in py-spinners__ package.

    __ https://github.com/ManrajGrover/py-spinners?tab=readme-ov-file

.. decoration-path:: `spinner/static_symbol`

    Static spinner symbol, for sub-tasks that've finished running but'.

.. decoration-path:: `hr/{weight}/{position}`

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
        Filler of the ruler that's used if `msg` is empty.
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

.. decoration-path:: input widget

    Decorations for :class:`yuio.widget.Input`:

    -   ``menu/input/decoration``: decoration before an input box,
    -   ``menu/input/decoration_search``: decoration before a search input box.

.. decoration-path:: choice and multiselect widget

    Decorations for :class:`yuio.widget.Choice` and :class:`yuio.widget.Multiselect`:

    -   ``menu/choice/decoration/active_item``: current item,
    -   ``menu/choice/decoration/selected_item``: selected item in multiselect widget,
    -   ``menu/choice/decoration/deselected_item``: deselected item in multiselect widget.

.. decoration-path:: inline help and help menu

    Decorations for widget help:

    -   ``menu/help/decoration``: decoration at the bottom of the help menu,
    -   :samp:`menu/help/key/{key}`: text for functional keys.

        ``key`` can be one of ``ctrl``, ``shift``, ``enter``, ``escape``, ``insert``,
        ``delete``, ``backspace``, ``tab``, ``home``, ``end``, ``page_up``,
        ``page_down``, ``arrow_up``, ``arrow_down``, ``arrow_left``, ``arrow_right``,
        ``space``, ``f1``...\\ ``f12``.

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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "BaseTheme",
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


_COLOR_NAMES = [
    "background",
    "foreground",
    "black",
    "bright_black",
    "red",
    "bright_red",
    "green",
    "bright_green",
    "yellow",
    "bright_yellow",
    "blue",
    "bright_blue",
    "magenta",
    "bright_magenta",
    "cyan",
    "bright_cyan",
    "white",
    "bright_white",
]


@_t.final
class _ImmutableDict(_t.Mapping[K, V], _t.Generic[K, V]):
    def __init__(
        self, data: dict[K, V], sources: dict[K, type[Theme] | None], attr: str
    ):
        self.__data = data
        self.__sources = sources
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
        raise TypeError(f"Theme.{self.__attr} is immutable")

    def __delitem__(self, key):
        raise TypeError(f"Theme.{self.__attr} is immutable")

    def copy(self) -> _t.Self:
        return self.__class__(
            self.__data.copy(),
            self.__sources.copy(),
            self.__attr,
        )

    def _set(self, key: K, value: V, source: type[Theme]):
        self.__data[key] = value
        self.__sources[key] = source

    def _set_if_not_overridden(self, key: K, value: V, source: type[Theme] | None):
        if source is None:
            raise TypeError(
                f"Theme._set_{self.__attr}_if_not_overridden can't be called "
                "outside of __init__"
            )
        prev_source = self.__sources.get(key)
        if prev_source is None or issubclass(source, prev_source):
            self._set(key, value, source)


@_t.final
class _ReadOnlyDescriptor:
    def __set_name__(self, owner: object, attr: str):
        self.__attr = attr
        self.__private_name = f"_Theme__{attr}"

    def __get__(self, instance: object | None, owner: type[object] | None = None):
        if instance is None:  # pragma: no cover
            return self
        elif (data := instance.__dict__.get(self.__private_name)) is not None:
            return data
        else:
            data = owner.__dict__[self.__private_name].copy()
            instance.__dict__[self.__private_name] = data
            return data

    def __set__(self, instance: object, value: _t.Any):
        raise TypeError(f"Theme.{self.__attr} is immutable")

    def __delete__(self, instance: object):
        raise TypeError(f"Theme.{self.__attr} is immutable")


class _ThemeMeta(type):
    # BEWARE OF MAGIC!
    #
    #
    # Descriptors
    # -----------
    #
    # _ThemeMeta.__dict__["colors"]
    #     this is a `_ReadOnlyDescriptor` that handles access to `Theme.colors`,
    #     proxying it to `Theme.__dict__["_Theme__colors"]`.
    #
    #     Accessing `Theme.colors` is equivalent to calling
    #     `_ThemeMeta.__dict__["colors"].__get__(Theme)`,
    #     which in turn will return `Theme.__dict__["_Theme__colors"]`.
    #
    #     Value for `Theme.__dict__["_Theme__colors"]` is assigned by this metaclass.
    #
    # Theme.__dict__["colors"]
    #     this is a `_ReadOnlyDescriptor` that handles access to `theme.colors`,
    #     proxying it to `theme.__dict__["_Theme__colors"]`.
    #
    #     Accessing `theme.colors` is equivalent to calling
    #     `Theme.__dict__["colors"].__get__(theme)`,
    #     which in turn will return `theme.__dict__["_Theme__colors"]`.
    #
    #     If `theme.__dict__` does not contain `"_Theme__colors"`, then it  will assign
    #     `theme.__dict__["_Theme__colors"] = Theme.__dict__["_Theme__colors"].copy()`.
    #
    # theme.__dict__["colors"]
    #     this attribute does not exist. Accessing `theme.colors` is handled
    #     by its descriptor.
    #
    #
    # Data
    # ----
    #
    # Theme.__dict__["_Theme__colors"]
    #     this is the data returned when accessing `Theme.colors`. It contains
    #     an `_ImmutableDict` with combination of all colors from all bases.
    #
    # Theme.__dict__["_Theme__colors__orig"]
    #     this is original data assigned to `colors` variable in `Theme`'s namespace.
    #
    #     For example:
    #
    #         class MyTheme(Theme):
    #             colors = {"foo": "#000000"}
    #
    #     In this class:
    #
    #     - `MyTheme.__dict__["_Theme__colors"]` will contain combination of
    #       colors defined in `Theme` and in `MyTheme`.
    #     - `MyTheme.__dict__["_Theme__colors__orig"]` will contain initial dict
    #       `{"foo": "#000000"}`.
    #
    # theme.__dict__["_Theme__colors"]
    #     this is lazily initialized copy of `Theme.__dict__["_Theme__colors"]`;
    #     `Theme.set_color` will mutate this value.

    _managed_attrs = ["msg_decorations_ascii", "msg_decorations_unicode", "colors"]
    for _attr in _managed_attrs:
        locals()[_attr] = _ReadOnlyDescriptor()
    del _attr  # type: ignore

    def __new__(mcs, name, bases, ns, **kwargs):
        # Pop any overrides from class' namespace and save them in `_Theme__attr__orig`.
        # Set up read-only descriptors for managed attributes.
        for attr in mcs._managed_attrs:
            ns[f"_Theme__{attr}__orig"] = ns.pop(attr, {})
            ns[attr] = _ReadOnlyDescriptor()

        # Create metaclass instance.
        cls = super().__new__(mcs, name, bases, ns, **kwargs)

        # Set up class-level data for managed attributes.
        for attr in mcs._managed_attrs:
            setattr(cls, f"_Theme__{attr}", mcs._collect_data(cls, attr))

        # Patch `__init__` so that it handles `__expected_source`.
        if init := cls.__dict__.get("__init__", None):

            @functools.wraps(init)
            def _wrapped_init(self, *args, **kwargs):
                prev_expected_source = self._Theme__expected_source
                self._Theme__expected_source = cls
                try:
                    return init(self, *args, **kwargs)
                finally:
                    self._Theme__expected_source = prev_expected_source

            setattr(cls, "__init__", _wrapped_init)

        return cls

    def _collect_data(cls, attr):
        attr_orig = f"_Theme__{attr}__orig"
        data = {}
        sources = {}
        for base in reversed(cls.__mro__):
            if base_data := base.__dict__.get(attr_orig):
                data.update(base_data)
                sources.update(dict.fromkeys(base_data, base))
        return _ImmutableDict(data, sources, attr)


class Theme(metaclass=_ThemeMeta):
    """
    Base class for Yuio themes.

    .. warning::

        Do not change theme contents after it was passed to :func:`yuio.io.setup`.
        Otherwise there's a risc of race conditions.

    """

    msg_decorations_unicode: _t.Mapping[str, str] = {}
    """
    Decorative symbols for certain text elements, such as headings,
    list items, etc.

    This mapping becomes immutable once a theme class is created. The only possible
    way to modify it is by using :meth:`~Theme.set_msg_decoration_ascii`
    or :meth:`~Theme._set_msg_decoration_ascii_if_not_overridden`.

    """

    msg_decorations_ascii: _t.Mapping[str, str] = {}
    """
    Like :attr:`~Theme.msg_decorations_unicode`, but suitable for non-unicode terminals.

    """

    progress_bar_width: int = 15
    """
    Width of a progress bar for :class:`yuio.io.Task`.

    """

    spinner_update_rate_ms: int = 200
    """
    How often the spinner pattern changes.

    """

    separate_headings: bool = True
    """
    Whether to print newlines before and after :func:`yuio.io.heading`.

    """

    fallback_width: int = 80
    """
    Preferred width that will be used if printing to a stream that's redirected
    to a file.

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

    __expected_source: type[Theme] | None = None
    """
    When running an ``__init__`` function, this variable will be set to the class
    that implemented it, regardless of type of `self`.

    That is, inside ``DefaultTheme.__init__``, ``__expected_source`` is set
    to ``DefaultTheme``, in ``MyTheme.__init__`` it is ``MyTheme``, etc.

    This is possible because ``_ThemeMeta`` wraps any implementation
    of ``__init__`` into a wrapper that sets this variable.

    """

    def __init__(self):
        self.__color_cache: dict[str, yuio.color.Color | None] = {}

    def _set_msg_decoration_unicode_if_not_overridden(
        self,
        name: str,
        msg_decoration: str,
        /,
    ):
        """
        Set Unicode message decoration by name, but only if it wasn't overridden
        in a subclass.

        This method should be called from ``__init__`` implementations
        to dynamically set message decorations. It will only set the decoration
        if it was not overridden by any child class.

        """

        proxy = _t.cast(_ImmutableDict[str, str], self.msg_decorations_unicode)
        proxy._set_if_not_overridden(
            name,
            msg_decoration,
            self.__expected_source,
        )

    def set_msg_decoration_unicode(
        self,
        name: str,
        msg_decoration: str,
        /,
    ):
        """
        Set Unicode message decoration by name.

        """

        proxy = _t.cast(_ImmutableDict[str, str], self.msg_decorations_unicode)
        proxy._set(
            name,
            msg_decoration,
            self.__expected_source or type(self),
        )

    def _set_msg_decoration_ascii_if_not_overridden(
        self,
        name: str,
        msg_decoration: str,
        /,
    ):
        """
        Set ASCII message decoration by name, but only if it wasn't overridden
        in a subclass.

        This method should be called from ``__init__`` implementations
        to dynamically set message decorations. It will only set the decoration
        if it was not overridden by any child class.

        """

        proxy = _t.cast(_ImmutableDict[str, str], self.msg_decorations_ascii)
        proxy._set_if_not_overridden(
            name,
            msg_decoration,
            self.__expected_source,
        )

    def set_msg_decoration_ascii(
        self,
        name: str,
        msg_decoration: str,
        /,
    ):
        """
        Set ASCII message decoration by name.

        """

        proxy = _t.cast(_ImmutableDict[str, str], self.msg_decorations_ascii)
        proxy._set(
            name,
            msg_decoration,
            self.__expected_source or type(self),
        )

    def get_msg_decoration(self, key: str, /, *, is_unicode: bool) -> str:
        """
        Get message decoration by name.

        """

        msg_decorations = (
            self.msg_decorations_unicode if is_unicode else self.msg_decorations_ascii
        )
        return msg_decorations.get(key, "")

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

        proxy = _t.cast(_ImmutableDict[str, str | yuio.color.Color], self.colors)
        proxy._set_if_not_overridden(
            path,
            color,
            self.__expected_source,
        )
        self.__color_cache.clear()
        self.__dict__.pop("_Theme__color_tree", None)  # type: ignore

    def set_color(
        self,
        path: str,
        color: str | yuio.color.Color,
        /,
    ):
        """
        Set color by path.

        """

        proxy = _t.cast(_ImmutableDict[str, str | yuio.color.Color], self.colors)
        proxy._set(
            path,
            color,
            self.__expected_source or type(self),
        )
        self.__color_cache.clear()
        self.__dict__.pop("_Theme__color_tree", None)  # type: ignore

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

        for path, colors in self.colors.items():
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


class BaseTheme(Theme):
    """
    This theme defines :ref:`common colors <common-tags>` that are commonly used
    in :ref:`inline color tags <color-tags>`.

    """

    colors = {
        #
        # Common tags
        # -----------
        "code": "bold",
        "note": "cyan",
        "strong": "note",
        "em": "italic",
        "path": "underline",
        "flag": "note",
        "kbd": "note",
        "gui": "kbd",
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
        "muted": yuio.color.Color.FORE_NORMAL_DIM,
        "black": yuio.color.Color.FORE_BLACK,
        "red": yuio.color.Color.FORE_RED,
        "green": yuio.color.Color.FORE_GREEN,
        "yellow": yuio.color.Color.FORE_YELLOW,
        "blue": yuio.color.Color.FORE_BLUE,
        "magenta": yuio.color.Color.FORE_MAGENTA,
        "cyan": yuio.color.Color.FORE_CYAN,
        "white": yuio.color.Color.FORE_WHITE,
    }


class DefaultTheme(BaseTheme):
    """
    Default Yuio theme. Adapts for terminal background color,
    if one can be detected.

    This theme defines :ref:`main colors <main-colors>`, which you can override
    by subclassing. All other colors are expressed in terms of main colors,
    so changing a main color will have an effect on the entire theme.

    """

    msg_decorations_ascii = {
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
        "code": "    ",
        "admonition/title": "",
        "admonition/body": "    ",
        "overflow": "~",
        "progress_bar/start_symbol": "[",
        "progress_bar/end_symbol": "]",
        "progress_bar/done_symbol": "-",
        "progress_bar/pending_symbol": " ",
        "progress_bar/transition_pattern": ">",
        "spinner/pattern": "|||/-\\",
        "spinner/static_symbol": ">",
        "menuselection_separator": "->",
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
        "menu/choice/decoration/active_item": "> ",
        "menu/choice/decoration/deselected_item": "- ",
        "menu/choice/decoration/selected_item": "* ",
        "menu/input/decoration_search": "/ ",
        "menu/input/decoration": "> ",
        "menu/help/key/alt": "M-",
        "menu/help/key/ctrl": "C-",
        "menu/help/key/shift": "S-",
        "menu/help/key/enter": "ret",
        "menu/help/key/escape": "esc",
        "menu/help/key/insert": "ins",
        "menu/help/key/delete": "del",
        "menu/help/key/backspace": "bsp",
        "menu/help/key/tab": "tab",
        "menu/help/key/home": "home",
        "menu/help/key/end": "end",
        "menu/help/key/page_up": "pgup",
        "menu/help/key/page_down": "pgdn",
        "menu/help/key/arrow_up": "up",
        "menu/help/key/arrow_down": "down",
        "menu/help/key/arrow_left": "left",
        "menu/help/key/arrow_right": "right",
        "menu/help/key/space": "space",
        "menu/help/key/f1": "f1",
        "menu/help/key/f2": "f2",
        "menu/help/key/f3": "f3",
        "menu/help/key/f4": "f4",
        "menu/help/key/f5": "f5",
        "menu/help/key/f6": "f6",
        "menu/help/key/f7": "f7",
        "menu/help/key/f8": "f8",
        "menu/help/key/f9": "f9",
        "menu/help/key/f10": "f10",
        "menu/help/key/f11": "f11",
        "menu/help/key/f12": "f12",
    }

    msg_decorations_unicode = {
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
        "code": "    ",
        "admonition/title": "",
        "admonition/body": "    ",
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
        "menuselection_separator": " → ",
        "menu/input/decoration": "> ",
        "menu/input/decoration_search": "/ ",
        "menu/choice/decoration/active_item": "> ",
        "menu/choice/decoration/selected_item": "◉ ",
        "menu/choice/decoration/deselected_item": "○ ",
        "menu/help/decoration": ":",
        "menu/help/key/alt": "M-",
        "menu/help/key/ctrl": "C-",
        "menu/help/key/shift": "S-",
        "menu/help/key/enter": "ret",
        "menu/help/key/escape": "esc",
        "menu/help/key/insert": "ins",
        "menu/help/key/delete": "del",
        "menu/help/key/backspace": "bsp",
        "menu/help/key/tab": "tab",
        "menu/help/key/home": "home",
        "menu/help/key/end": "end",
        "menu/help/key/page_up": "pgup",
        "menu/help/key/page_down": "pgdn",
        "menu/help/key/arrow_up": "↑",
        "menu/help/key/arrow_down": "↓",
        "menu/help/key/arrow_left": "←",
        "menu/help/key/arrow_right": "→",
        "menu/help/key/space": "␣",
        "menu/help/key/f1": "f1",
        "menu/help/key/f2": "f2",
        "menu/help/key/f3": "f3",
        "menu/help/key/f4": "f4",
        "menu/help/key/f5": "f5",
        "menu/help/key/f6": "f6",
        "menu/help/key/f7": "f7",
        "menu/help/key/f8": "f8",
        "menu/help/key/f9": "f9",
        "menu/help/key/f10": "f10",
        "menu/help/key/f11": "f11",
        "menu/help/key/f12": "f12",
    }

    colors = {
        "note": "accent_color_2",
        #
        # Main settings
        # -------------
        # This section controls the overall theme look.
        # Most likely you'll want to change accent colors from here.
        "heading_color": "bold primary_color",
        "primary_color": "normal",
        "accent_color": "magenta",
        "accent_color_2": "cyan",
        "secondary_color": "muted",
        "error_color": "red",
        "warning_color": "yellow",
        "success_color": "green",
        "critical_color": "inverse error_color",
        "low_priority_color_a": "muted",
        "low_priority_color_b": "muted",
        #
        # IO messages and text
        # --------------------
        "msg/decoration": "secondary_color",
        "msg/decoration:heading": "heading_color accent_color",
        "msg/decoration:thematic_break": "secondary_color",
        "msg/text:code": "primary_color",
        "msg/text:heading": "heading_color",
        "msg/text:heading/1": "accent_color",
        "msg/text:heading/section": "green",
        "msg/text:heading/note": "green",
        "msg/text:question": "heading_color",
        "msg/text:error": "error_color",
        "msg/text:error/note": "green",
        "msg/text:warning": "warning_color",
        "msg/text:success": "heading_color success_color",
        "msg/text:failure": "heading_color error_color",
        "msg/text:info": "primary_color",
        "msg/text:thematic_break": "secondary_color",
        "msg/text:help/tail": "dim",
        "msg/text:admonition/title": "heading_color blue",
        "msg/text:admonition/body": "blue",
        "msg/text:admonition/title/attention": "warning_color",
        "msg/text:admonition/body/attention": "warning_color",
        "msg/text:admonition/title/caution": "warning_color",
        "msg/text:admonition/body/caution": "warning_color",
        "msg/text:admonition/title/danger": "error_color",
        "msg/text:admonition/body/danger": "error_color",
        "msg/text:admonition/title/error": "error_color",
        "msg/text:admonition/body/error": "error_color",
        "msg/text:admonition/title/hint": "success_color",
        "msg/text:admonition/body/hint": "success_color",
        "msg/text:admonition/title/important": "warning_color",
        "msg/text:admonition/body/important": "warning_color",
        "msg/text:admonition/title/seealso": "success_color",
        "msg/text:admonition/body/seealso": "success_color",
        "msg/text:admonition/title/tip": "success_color",
        "msg/text:admonition/body/tip": "success_color",
        "msg/text:admonition/title/warning": "warning_color",
        "msg/text:admonition/body/warning": "warning_color",
        "msg/text:admonition/title/versionadded": "success_color",
        "msg/text:admonition/body/versionadded": "success_color",
        "msg/text:admonition/title/versionchanged": "warning_color",
        "msg/text:admonition/body/versionchanged": "warning_color",
        "msg/text:admonition/title/deprecated": "error_color",
        "msg/text:admonition/body/deprecated": "error_color",
        "msg/text:admonition/title/definition": "primary_color",
        "msg/text:admonition/body/definition": "primary_color",
        "msg/text:admonition/title/field": "primary_color",
        "msg/text:admonition/body/field": "primary_color",
        "msg/text:admonition/title/unknown-dir": "primary_color",
        "msg/text:admonition/body/unknown-dir": "primary_color",
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
        "task/progressbar/done/start": "term/bright_blue",
        "task/progressbar/done/end": "term/bright_magenta",
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
        "hl/doctest_marker": "accent_color",
        "hl/doctest_marker/continue": "secondary_color",
        "hl/metavar:sh-usage": "bold",
        "tb/heading": "bold error_color",
        "tb/message": "tb/heading",
        "tb/frame/usr/file/module": "accent_color",
        "tb/frame/usr/file/line": "accent_color",
        "tb/frame/usr/file/path": "accent_color",
        "tb/frame/usr/code": "primary_color",
        "tb/frame/usr/highlight": "error_color",
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
        "menu/text/help_key:help_menu": "kbd",
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
        "menu/decoration/comment": "secondary_color",
        "menu/decoration:choice/normal": "menu/text",
        "menu/decoration:choice/normal/selected": "accent_color_2 bold",
        "menu/decoration:choice/active/selected": "bold",
        **{f"term/{name}": yuio.color.Color.NONE for name in _COLOR_NAMES},
        #
        # Documentation roles
        # -------------------
        "role/footnote": "secondary_color",
        "role/flag": "flag",
        "role/code": "code",
        "role/literal": "em",
        "role/math": "em",
        "role/abbr": "em",
        "role/command": "em",
        "role/dfn": "em",
        "role/mailheader": "em",
        "role/makevar": "em",
        "role/mimetype": "em",
        "role/newsgroup": "em",
        "role/program": "flag",
        "role/regexp": "code",
        "role/cve": "em",
        "role/cwe": "em",
        "role/pep": "em",
        "role/rfc": "em",
        "role/manpage": "em",
        "role/any": "em",
        "role/doc": "em",
        "role/download": "em",
        "role/envvar": "code",
        "role/keyword": "em",
        "role/numref": "em",
        "role/option": "flag",
        "role/cmdoption": "flag",
        "role/ref": "em",
        "role/term": "em",
        "role/token": "em",
        "role/eq": "em",
        "role/kbd": "kbd",
        "role/guilabel": "note",
        "role/guilabel/accelerator": "underline",
        "role/menuselection": "note",
        # "role/menuselection/separator": "secondary_color",
        "role/menuselection/accelerator": "underline",
        "role/file": "path",
        "role/file/variable": "italic",
        "role/samp": "code",
        "role/samp/variable": "italic",
        "role/cli/cfg": "code",
        "role/cli/field": "code",
        "role/cli/obj": "code",
        "role/cli/env": "code",
        "role/cli/any": "code",
        "role/cli/cmd": "flag",
        "role/cli/flag": "flag",
        "role/cli/arg": "flag",
        "role/cli/opt": "flag",
        "role/cli/cli": "flag",
        "role/unknown": "code",
    }
    """
    Colors for default theme are separated into several sections.

    The main section (the first one) has common settings which are referenced
    from all other sections. You'll probably want to override

    """

    def __init__(self, term: yuio.term.Term):
        super().__init__()

        if (colors := term.terminal_theme) is None:
            return

        # Gradients look bad in other modes.
        if term.supports_colors_true:
            for name in _COLOR_NAMES:
                self._set_color_if_not_overridden(
                    f"term/{name}", yuio.color.Color(fore=getattr(colors, name))
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
        separate_headings: bool | None = None
        fallback_width: _t.Annotated[int, yuio.parse.Gt(0)] | None = None
        msg_decorations_unicode: dict[str, str] = yuio.config.field(
            default={},
            merge=lambda l, r: {**l, **r},
        )
        msg_decorations_ascii: dict[str, str] = yuio.config.field(
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
    if theme_data.separate_headings is not None:
        theme.separate_headings = theme_data.separate_headings
    if theme_data.fallback_width is not None:
        theme.fallback_width = theme_data.fallback_width

    for k, v in theme_data.msg_decorations_ascii.items():
        theme.set_msg_decoration_ascii(k, v)
    for k, v in theme_data.msg_decorations_unicode.items():
        theme.set_msg_decoration_unicode(k, v)
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
