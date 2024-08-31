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

    .. autoattribute:: progress_bar_start_symbol

    .. autoattribute:: progress_bar_end_symbol

    .. autoattribute:: progress_bar_done_symbol

    .. autoattribute:: progress_bar_pending_symbol

    .. autoattribute:: spinner_pattern

    .. autoattribute:: spinner_update_rate_ms

    .. autoattribute:: spinner_static_symbol

    .. autoattribute:: msg_decorations

    .. automethod:: set_msg_decoration

    .. automethod:: _set_msg_decoration_if_not_overridden

    .. autoattribute:: colors

    .. automethod:: set_color

    .. automethod:: _set_color_if_not_overridden

    .. automethod:: get_color

    .. automethod:: to_color


Default theme
-------------

Use the following loader to create an instance of the default theme:

.. autofunction:: load

.. autoclass:: DefaultTheme

"""

import dataclasses
import functools
import os
from dataclasses import dataclass

import yuio.term
from yuio import _t
from yuio.term import Color, Term

T = _t.TypeVar("T")


class _ImmutableDictProxy(_t.Mapping[str, T], _t.Generic[T]):
    def __init__(self, data: _t.Dict[str, T], /, *, attr: str):
        self.__data = data
        self.__attr = attr

    def items(self) -> _t.ItemsView[str, T]:
        return self.__data.items()

    def keys(self) -> _t.KeysView[str]:
        return self.__data.keys()

    def values(self) -> _t.ValuesView[T]:
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
    """Base class for Yuio themes."""

    _Self = _t.TypeVar("_Self", bound="Theme")

    #: Decorative symbols for certain text elements, such as headings,
    #: list items, etc.
    #:
    #: This mapping becomes immutable once a theme class is created. The only possible
    #: way to modify it is by using :meth:`~Theme.set_msg_decoration`
    #: or :meth:`~Theme._set_msg_decoration_if_not_overridden`.
    msg_decorations: _t.Mapping[str, str] = {
        "heading/section": "",
        "heading/1": "⣿ ",
        "heading/2": "",
        "heading/3": "",
        "heading/4": "",
        "heading/5": "",
        "heading/6": "",
        "question": "> ",
        "task": "> ",
        "thematic_break": "╌╌╌╌╌",
        "list": "•   ",
        "quote": ">   ",
        "code": " " * 8,
        # TODO: support these in widgets
        # 'menu_selected_item': '▶︎',
        # 'menu_default_item': '★',
        # 'menu_select': '#',
        # 'menu_search': '/',
    }

    #: An actual mutable version of :attr:`~Theme.msg_decorations`
    #: is kept here, because `__init_subclass__` will replace
    #: :attr:`~Theme.msg_decorations` with an immutable proxy.
    __msg_decorations: _t.Dict[str, str]
    #: Keeps track of where a message decoration was inherited from. This var is used
    #: to avoid `__init__`-ing message decorations that were overridden in a subclass.
    __msg_decoration_sources: _t.Dict[str, _t.Optional[type]] = {}

    #: Width of a progress bar for :class:`yuio.io.Task`.
    progress_bar_width: int = 15
    #: A symbol rendered on a left side of a progressbar.
    #:
    #: Set to ``'['`` to enclose progressbar in square brackets, for example.
    progress_bar_start_symbol: str = ""
    #: A symbol rendered on a right side of a progressbar.
    #:
    #: Set to ``']'`` to enclose progressbar in square brackets, for example.
    progress_bar_end_symbol: str = ""
    #: Symbol rendered in the filled portion of a progressbar.
    progress_bar_done_symbol: str = "■"
    #: Symbol rendered in the unfilled portion of a progressbar.
    progress_bar_pending_symbol: str = "□"
    #: Spinner pattern for running tasks that don't have a progressbar.
    #:
    #: Every tick, a symbol in front of a task's heading updates, showing elements
    #: of this sequence.
    spinner_pattern: _t.Sequence[str] = "⣤⣤⣤⠶⠛⠛⠛⠶"
    #: How often the :attr:`~Theme.spinner_pattern` changes.
    spinner_update_rate_ms: int = 200
    #: Symbol for finished and failed tasks.
    #:
    #: It meant to resemble a static spinner.
    spinner_static_symbol = "⣿"

    #: Mapping of color paths to actual colors.
    #:
    #: Themes use color paths to describe styles and colors for different
    #: parts of an application. Color paths are similar to file paths,
    #: they use snake case identifiers separated by slashes, and consist of
    #: two parts separated by a colon.
    #:
    #: The first part represents an object, i.e. what are we coloring.
    #:
    #: The second part represents a context, i.e. what is the state or location
    #: of an object that we're coloring.
    #:
    #: For example, a color for the filled part of the task's progress bar
    #: has path ``'task/progressbar/done'``, a color for a text of an error
    #: log record has path ``'log/message:error'``, and a color for a string escape
    #: sequence in a highlighted python code has path ``'hl/str/esc:python'``.
    #:
    #: A color at a certain path is propagated to all sub-paths. For example,
    #: if ``'task/progressbar'`` is bold, and ``'task/progressbar/done'`` is green,
    #: the final color will be bold green.
    #:
    #: Each color path can be associated with either an instance of :class:`Color`,
    #: another path, or a list of colors and paths.
    #:
    #: If path is mapped to a :class:`Color`, then the path is associated
    #: with that particular color.
    #:
    #: If path is mapped to another path, then the path is associated with
    #: the color value for that other path (please don't create recursions here).
    #:
    #: If path is mapped to a list of colors and paths, then those colors and paths
    #: are combined.
    #:
    #: For example::
    #:
    #:     colors = {
    #:         'heading_color': Color.BOLD,
    #:         'error_color': Color.RED,
    #:         'tb/heading': ['heading_color', 'error_color'],
    #:     }
    #:
    #: Here, color of traceback's heading ``'tb/heading'`` will be bold and red.
    #:
    #: The base theme class provides colors for basic tags, such as `bold`, `red`,
    #: `code`, `note`, etc. :class:`DefaultTheme` expands on it, providing main
    #: colors that control the overall look of the theme, and then colors for all
    #: interface elements.
    #:
    #: When deriving from a theme, you can override this mapping. When looking up
    #: colors via :meth:`~Theme.get_color`, base classes will be tried for color,
    #: in order of method resolution.
    #:
    #: This mapping becomes immutable once a theme class is created. The only possible
    #: way to modify it is by using :meth:`~Theme.set_color`
    #: or :meth:`~Theme._set_color_if_not_overridden`.
    colors: _t.Mapping[str, _t.Union[str, Color, _t.List[_t.Union[str, Color]]]] = {
        "code": "magenta",
        "note": "green",
        "bold": Color.STYLE_BOLD,
        "b": "bold",
        "dim": Color.STYLE_DIM,
        "d": "dim",
        "normal": Color.FORE_NORMAL,
        "normal_dim": Color.FORE_NORMAL_DIM,
        "red": Color.FORE_RED,
        "green": Color.FORE_GREEN,
        "yellow": Color.FORE_YELLOW,
        "blue": Color.FORE_BLUE,
        "magenta": Color.FORE_MAGENTA,
        "cyan": Color.FORE_CYAN,
    }

    #: An actual mutable version of :attr:`~Theme.colors`
    #: is kept here, because `__init_subclass__` will replace
    #: :attr:`~Theme.colors` with an immutable proxy.
    __colors: _t.Dict[str, _t.Union[str, Color, _t.List[_t.Union[str, Color]]]]
    #: Keeps track of where a color was inherited from. This var is used
    #: to avoid `__init__`-ing colors that were overridden in a subclass.
    __color_sources: _t.Dict[str, _t.Optional[type]] = {}

    #: When running an `__init__` function, this variable will be set to the class
    #: that implemented it, regardless of type of `self`.
    #:
    #: That is, inside `DefaultTheme.__init__`, `__expected_source` is set
    #: to `DefaultTheme`, in `MyTheme.__init__` it is `MyTheme`, etc.
    #:
    #: This is possible because `__init_subclass__` wraps any implementation
    #: of `__init__` into a wrapper that sets this variable.
    __expected_source: _t.Optional[type] = None

    def __init__(self):
        pass

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
        """Set message decoration by name, but only if it wasn't overridden
        in a subclass.

        This method should be called from `__init__` implementations
        to dynamically set message decorations. It will only set the decoration
        if it was not overridden by any child class.

        """

        if self.__expected_source is None:
            raise RuntimeError(
                f"_set_msg_decoration_if_not_overridden should only be called from __init__"
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
        """Set message decoration by name."""

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

    def _set_color_if_not_overridden(
        self,
        path: str,
        color: _t.Union[str, Color, _t.List[_t.Union[str, Color]]],
        /,
    ):
        """Set color by path, but only if the color was not overridden in a subclass.

        This method should be called from `__init__` implementations
        to dynamically set colors. It will only set the color if it was not overridden
        by any child class.

        """

        if self.__expected_source is None:
            raise RuntimeError(
                f"_set_color_if_not_overridden should only be called from __init__"
            )
        source = self.__color_sources.get(path, Theme)
        # The class who's `__init__` is currently running should be a parent
        # of the color's source. This means that the color was assigned by a parent.
        if source is not None and issubclass(self.__expected_source, source):
            self.set_color(path, color)

    def set_color(
        self,
        path: str,
        color: _t.Union[str, Color, _t.List[_t.Union[str, Color]]],
        /,
    ):
        """Set color by path."""

        if "_Theme__colors" not in self.__dict__:
            self.__colors = self.__class__.__colors.copy()
            self.__color_sources = self.__class__.__color_sources.copy()
            self.colors = _ImmutableDictProxy(self.__colors, attr="colors")
        self.__colors[path] = color
        self.__color_sources[path] = self.__expected_source
        self.get_color.cache_clear()
        self.__dict__.pop("_Theme__color_tree", None)

    @dataclass(**yuio._with_slots())
    class __ColorTree:
        """
        Prefix-like tree that contains all of the theme's colors.

        """

        #: Colors in this node.
        colors: _t.Union[str, Color, _t.List[_t.Union[str, Color]]] = Color.NONE

        #: Location part of the tree.
        loc: _t.Dict[str, "Theme.__ColorTree"] = dataclasses.field(default_factory=dict)

        #: Context part of the tree.
        ctx: _t.Dict[str, "Theme.__ColorTree"] = dataclasses.field(default_factory=dict)

    @functools.cached_property
    def __color_tree(self) -> "Theme.__ColorTree":
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
    def __parse_path(path: str, /) -> _t.Tuple[_t.List[str], _t.List[str]]:
        path_parts = path.split(":", maxsplit=1)
        if len(path_parts) == 1:
            loc, ctx = path_parts[0], ""
        else:
            loc, ctx = path_parts
        return loc.split("/") if loc else [], ctx.split("/") if ctx else []

    @_t.final
    @functools.lru_cache(maxsize=None)
    def get_color(self, path: str, /) -> Color:
        """Lookup a color by path."""

        loc, ctx = self.__parse_path(path)
        return self.__get_color_in_loc(self.__color_tree, loc, ctx)

    def __get_color_in_loc(
        self, node: "Theme.__ColorTree", loc: _t.List[str], ctx: _t.List[str]
    ):
        color = Color.NONE

        for part in loc:
            if part not in node.loc:
                break
            color |= self.__get_color_in_ctx(node, ctx)
            node = node.loc[part]

        return color | self.__get_color_in_ctx(node, ctx)

    def __get_color_in_ctx(self, node: "Theme.__ColorTree", ctx: _t.List[str]):
        color = Color.NONE

        for part in ctx:
            if part not in node.ctx:
                break
            color |= self.__get_color_in_node(node)
            node = node.ctx[part]

        return color | self.__get_color_in_node(node)

    def __get_color_in_node(self, node: "Theme.__ColorTree") -> Color:
        color = Color.NONE

        if isinstance(node.colors, str):
            color |= self.get_color(node.colors)
        elif isinstance(node.colors, list):
            for c in node.colors:
                color |= self.get_color(c) if isinstance(c, str) else c
        else:
            color |= node.colors

        return color

    def to_color(self, color_or_path: _t.Union[Color, str, None]) -> Color:
        """
        Convert color or color path to color.

        """

        if color_or_path is None:
            return Color.NONE
        elif isinstance(color_or_path, Color):
            return color_or_path
        else:
            return self.get_color(color_or_path)


Theme.__init_subclass__()


class DefaultTheme(Theme):
    """Default Yuio theme. Adapts for terminal background color,
    if one can be detected.

    This theme defines *main colors*, which you can override by subclassing.

    - ``'heading_color'``: for headings,
    - ``'primary_color'``: for main text,
    - ``'accent_color'``: for visually highlighted elements,
    - ``'secondary_color'``: for visually dimmed elements,
    - ``'error_color'``: for everything that indicates an error,
    - ``'warning_color'``: for everything that indicates a warning,
    - ``'success_color'``: for everything that indicates a success,
    - ``'low_priority_color_a'``: for auxiliary elements such as help widget,
    - ``'low_priority_color_b'``: for auxiliary elements such as help widget,
      even lower priority.

    """

    #: Colors for default theme are separated into several sections.
    #:
    #: The main section (the first one) has common settings which are referenced
    #: from all other sections. You'll probably want to override
    colors = {
        #
        # Main settings
        # -------------
        # This section controls the overall theme look.
        # Most likely you'll want to change accent colors from here.
        "heading_color": ["bold", "primary_color"],
        "primary_color": "normal",
        "accent_color": "magenta",
        "accent_color_2": "cyan",
        "secondary_color": "normal_dim",
        "error_color": "red",
        "warning_color": "yellow",
        "success_color": "green",
        "low_priority_color_a": "normal_dim",
        "low_priority_color_b": "normal_dim",
        #
        # Common tags
        # -----------
        "code": "accent_color",
        "note": "accent_color_2",
        #
        # IO messages and text
        # --------------------
        "msg/decoration": "secondary_color",
        "msg/decoration:heading": "accent_color",
        "msg/decoration:thematic_break": "secondary_color",
        "msg/text": "primary_color",
        "msg/text:heading": "heading_color",
        "msg/text:heading/section": "accent_color",
        "msg/text:question": "heading_color",
        "msg/text:error": "error_color",
        "msg/text:warning": "warning_color",
        "msg/text:success": "success_color",
        "msg/text:info": "primary_color",
        "msg/text:thematic_break": "secondary_color",
        #
        # Log messages
        # ------------
        "log/asctime": "secondary_color",
        "log/logger": "secondary_color",
        "log/level": "heading_color",
        "log/level:critical": "error_color",
        "log/level:error": "error_color",
        "log/level:warning": "warning_color",
        "log/level:info": "success_color",
        "log/level:debug": "secondary_color",
        "log/message": "primary_color",
        #
        # Tasks and progress bars
        # -----------------------
        "task": "secondary_color",
        "task/decoration:running": "accent_color",
        "task/decoration:done": "success_color",
        "task/decoration:error": "error_color",
        "task/progressbar/done": "accent_color",
        "task/progressbar/pending": "secondary_color",
        "task/heading": "heading_color",
        "task/progress": "secondary_color",
        "task/comment": "primary_color",
        #
        # Syntax highlighting
        # -------------------
        "hl/kwd": "bold",
        "hl/str": Color.NONE,
        "hl/str/esc": "bold",
        "hl/lit": Color.NONE,
        "hl/punct": "blue",
        "hl/comment": "secondary_color",
        "hl/prog": "bold",
        "hl/flag": "accent_color_2",
        "hl/metavar": "bold",
        "tb/heading": ["bold", "red"],
        "tb/message": "tb/heading",
        "tb/frame/usr/file/module": "code",
        "tb/frame/usr/file/line": "code",
        "tb/frame/usr/file/path": "code",
        "tb/frame/usr/code": Color.NONE,
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
        "menu/text/heading": ["menu/text", "heading_color"],
        "menu/text/help_info:help": "low_priority_color_a",
        "menu/text/help_msg:help": "low_priority_color_b",
        "menu/text/help_key:help": "low_priority_color_a",
        "menu/text/help_sep:help": "low_priority_color_b",
        "menu/text/help_key:help_menu": "accent_color_2",
        "menu/text/help_sep:help_menu": "secondary_color",
        "menu/text/comment": "note",
        "menu/text/comment/decoration": "secondary_color",
        "menu/text:choice/active": "accent_color",
        "menu/text:choice/active/selected": ["bold"],
        "menu/text:choice/normal/selected": ["accent_color_2", "bold"],
        "menu/text:choice/normal/dir": "blue",
        "menu/text:choice/normal/exec": "red",
        "menu/text:choice/normal/symlink": "magenta",
        "menu/text:choice/normal/socket": "green",
        "menu/text:choice/normal/pipe": "yellow",
        "menu/text:choice/normal/block_device": ["cyan", "bold"],
        "menu/text:choice/normal/char_device": ["yellow", "bold"],
        "menu/text/comment:choice/normal/original": "success_color",
        "menu/text/comment:choice/normal/corrected": "error_color",
        "menu/text/prefix:choice/normal": "primary_color",
        "menu/text/prefix:choice/normal/selected": ["accent_color_2", "bold"],
        "menu/text/prefix:choice/active": "accent_color",
        "menu/text/prefix:choice/active/selected": ["bold"],
        "menu/text/suffix:choice/normal": "primary_color",
        "menu/text/suffix:choice/normal/selected": ["accent_color_2", "bold"],
        "menu/text/suffix:choice/active": "accent_color",
        "menu/text/suffix:choice/active/selected": ["bold"],
        "menu/text:choice/status_line": "low_priority_color_b",
        "menu/text:choice/status_line/number": "low_priority_color_a",
        "menu/placeholder": "secondary_color",
        "menu/decoration": "accent_color",
        "menu/decoration:choice/normal": "menu/text",
    }

    def __init__(self, term: Term):
        super().__init__()

        if term.terminal_colors is None:
            return

        # Gradients look bad in other modes.
        if term.has_colors_true:
            self._set_color_if_not_overridden(
                "task/progressbar/done/start", Color(fore=term.terminal_colors.blue)
            )
            self._set_color_if_not_overridden(
                "task/progressbar/done/end", Color(fore=term.terminal_colors.magenta)
            )

        if term.terminal_colors.lightness == yuio.term.Lightness.UNKNOWN:
            return

        background = term.terminal_colors.background
        foreground = term.terminal_colors.foreground

        if term.terminal_colors.lightness is term.terminal_colors.lightness.DARK:
            self._set_color_if_not_overridden(
                "low_priority_color_a",
                Color(fore=foreground.match_luminosity(background.lighten(0.30))),
            )
            self._set_color_if_not_overridden(
                "low_priority_color_b",
                Color(fore=foreground.match_luminosity(background.lighten(0.25))),
            )
        else:
            self._set_color_if_not_overridden(
                "low_priority_color_a",
                Color(fore=foreground.match_luminosity(background.darken(0.30))),
            )
            self._set_color_if_not_overridden(
                "low_priority_color_b",
                Color(fore=foreground.match_luminosity(background.darken(0.25))),
            )


def load(term: Term, /) -> Theme:
    """Loads a default theme."""

    # NOTE: loading themes from json is beta, don't use it yet.

    theme = DefaultTheme(term)

    if not (path := os.environ.get("YUIO_THEME_PATH")):
        return theme

    import yuio.config

    class ThemeData(yuio.config.Config):
        progress_bar_width: _t.Optional[int] = None
        progress_bar_start_symbol: _t.Optional[str] = None
        progress_bar_end_symbol: _t.Optional[str] = None
        progress_bar_done_symbol: _t.Optional[str] = None
        progress_bar_pending_symbol: _t.Optional[str] = None
        spinner_pattern: _t.Optional[str] = None
        spinner_update_rate_ms: _t.Optional[int] = None
        spinner_static_symbol: _t.Optional[str] = None
        msg_decorations: _t.Optional[_t.Dict[str, str]] = None
        colors: _t.Optional[_t.Dict[str, str]] = None

    theme_data = ThemeData.load_from_json_file(path)

    if theme_data.progress_bar_width is not None:
        theme.progress_bar_width = theme_data.progress_bar_width
    if theme_data.progress_bar_start_symbol is not None:
        theme.progress_bar_start_symbol = theme_data.progress_bar_start_symbol
    if theme_data.progress_bar_end_symbol is not None:
        theme.progress_bar_end_symbol = theme_data.progress_bar_end_symbol
    if theme_data.progress_bar_done_symbol is not None:
        theme.progress_bar_done_symbol = theme_data.progress_bar_done_symbol
    if theme_data.progress_bar_pending_symbol is not None:
        theme.progress_bar_pending_symbol = theme_data.progress_bar_pending_symbol
    if theme_data.spinner_pattern is not None:
        theme.spinner_pattern = theme_data.spinner_pattern
    if theme_data.spinner_update_rate_ms is not None:
        theme.spinner_update_rate_ms = theme_data.spinner_update_rate_ms
    if theme_data.spinner_static_symbol is not None:
        theme.spinner_static_symbol = theme_data.spinner_static_symbol

    if theme_data.msg_decorations is not None:
        for k, v in theme_data.msg_decorations.items():
            theme.set_msg_decoration(k, v)

    if theme_data.colors is not None:
        theme.colors = theme_data.colors

        for k, v in theme_data.colors.items():
            v = [Color.fore_from_hex(c) if c.startswith("#") else c for c in v.split()]
            theme.set_color(k, v[0] if len(v) == 1 else v)

    return theme
