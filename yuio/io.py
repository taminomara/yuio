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
- ``FORCE_NO_COLORS``: disable colored output,
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

import dataclasses
import enum
import functools
import getpass
import itertools
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
from dataclasses import dataclass
from logging import LogRecord

import yuio.parse
from yuio.config import DISABLED, Disabled


T = _t.TypeVar('T')
Cb = _t.TypeVar('Cb', bound=_t.Callable[..., None])

_Progress = _t.Union[None, int, float, _t.Tuple[int, int], _t.Tuple[int, int, int]]
_ExcInfo = _t.Tuple[_t.Optional[_t.Type[BaseException]], _t.Optional[BaseException], _t.Optional[types.TracebackType]]


_STDIN: _t.TextIO = sys.__stdin__
_STDERR: _t.TextIO = sys.__stderr__


class UserIoError(IOError):
    """Raised when interaction with user fails.

    """





ColorMap = _t.Dict[str, _t.Union[str, Color]]


class Theme:
    decoration_symbol = '⣿'

    progress_bar_width = 15
    progress_bar_start_symbol = ''
    progress_bar_end_symbol = ''
    progress_bar_done_symbol = '■'
    progress_bar_inflight_symbol = '■'
    progress_bar_pending_symbol = '□'

    spinner_pattern = '⣤⠶⠛⠛⠛⠶⣤⣤'
    spinner_static_symbol = '⣿'
    spinner_simple_symbol = '>'
    spinner_update_rate_ms = 200

    #: Message colors::
    #:
    #:     > ⣿ Heading
    #:       │ ╰┬────╯
    #:       │  └ msg/heading/text
    #:       └ msg/heading/decoration
    #:
    #:     > Info message
    #:       ╰┬─────────╯
    #:        └ msg/info/text
    #:
    #:
    #: Log line colors::
    #:
    #:     > 2023-04-01 00:00:00 my_app.main CRIT FBI open up!
    #:       ╰┬────────────────╯ ╰┬────────╯ ╰┬─╯ ╰┬─────────╯
    #:        │                   │           │    └ log/message/critical
    #:        └ log/asctime       │           └ log/level/critical
    #:                            └ log/logger
    #:
    #:
    #: Colors for traceback lines::
    #:
    #:     > Traceback (most recent call last):         ⎬ tb/heading
    #:     >   File "<stdin>", line 1, in <module>      ⎬ tb/frame/usr/file
    #:     >     import x                               ⎬ tb/frame/usr/code
    #:     >     ^^^^^^^^                               ⎬ tb/frame/usr/highlight
    #:     >   File "site-packages/x.py", line 1, in x  ⎬ tb/frame/lib/file
    #:     >     1 / 0                                  ⎬ tb/frame/lib/code
    #:     >     ^^^^^                                  ⎬ tb/frame/lib/highlight
    #:     > ZeroDivisionError: division by zero        ⎬ tb/message
    #:
    #:
    #: Colors within traceback's 'file' line::
    #:
    #:     > File "<stdin>", line 1, in <module>
    #:            ╰┬──────╯       │     ╰┬─────╯
    #:             │              │      └ log/frame/usr/file/module
    #:             │              └ log/frame/usr/file/line
    #:             └ log/frame/usr/file/path
    #:
    #: Colors for task without progress::
    #:
    #:      > ⣿ Downloading the internet - initializing
    #:        │ ╰┬─────────────────────╯   ╰┬─────────╯
    #:        │  └ task/heading             └ task/comment
    #:        └ task/spinner/running (or .../done or .../error)
    #:
    #:
    #: Colors for task with progress::
    #:
    #: █████▒▒▒░░░░ Downloading the internet - 69% - www.reddit.com
    #: ╰┬──╯╰┬╯╰┬─╯ ╰┬─────────────────────╯   ╰┬╯   ╰┬───────────╯
    #:  │    │  │    └ task/heading             │     └ task/comment
    #:  │    │  └ task/progressbar/pending      └ task/progress (or .../done or .../error)
    #:  │    └ task/progressbar/inflight
    #:  └ task/progressbar/done
    colors: ColorMap = {
        'code': Color.FORE_MAGENTA,
        'note': Color.FORE_GREEN,

        'bold': Color.STYLE_BOLD,
        'b': 'bold',
        'dim': Color.STYLE_DIM,
        'd': 'dim',

        'black': Color.FORE_BLACK,
        'red': Color.FORE_RED,
        'green': Color.FORE_GREEN,
        'yellow': Color.FORE_YELLOW,
        'blue': Color.FORE_BLUE,
        'magenta': Color.FORE_MAGENTA,
        'cyan': Color.FORE_CYAN,
        'white': Color.FORE_WHITE,
    }

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        colors = {}
        for base in reversed(cls.__mro__):
            colors.update(getattr(base, 'colors', {}))
        cls.colors = colors

    def get_progressbar_gradient(self) -> _t.Callable[[float], Color]:
        color = self.get_color('task/progressbar/done')
        return lambda f, /: color

    @functools.cache
    def get_color(self, path: str, /) -> Color:
        color = Color.NONE

        for prefix in self._prefixes(path.split('/')):
            if (res := self.colors.get('/'.join(prefix))) is not None:
                color |= (self.get_color(res) if isinstance(res, str) else res)

        return color

    @staticmethod
    def _prefixes(it: _t.List[T]) -> _t.Iterable[_t.List[T]]:
        for i in range(1, len(it) + 1):
            yield it[:i]


class DefaultTheme(Theme):
    colors: ColorMap = {
        'msg/heading/decoration': Color.FORE_MAGENTA,
        'msg/heading/text': Color.STYLE_BOLD,
        'msg/question': Color.STYLE_BOLD,
        'msg/error': Color.FORE_RED,
        'msg/warning': Color.FORE_YELLOW,
        'msg/success': Color.FORE_GREEN,
        'msg/info': Color.NONE,
        'msg/debug': Color.STYLE_DIM,
        'msg/hr': Color.STYLE_DIM,
        'msg/group': Color.FORE_BLUE,

        'log/plain_text': Color.STYLE_DIM,
        'log/asctime': Color.STYLE_DIM,
        'log/logger': Color.STYLE_DIM,
        'log/level': Color.STYLE_BOLD,
        'log/level/critical': Color.FORE_WHITE | Color.BACK_RED,
        'log/level/error': Color.FORE_RED,
        'log/level/warning': Color.FORE_YELLOW,
        'log/level/info': Color.FORE_CYAN,
        'log/level/debug': Color.STYLE_DIM,
        'log/message': Color.NONE,

        'tb/plain_text': Color.STYLE_DIM,
        'tb/heading': Color.FORE_RED | Color.STYLE_BOLD,
        'tb/frame/usr': Color.NONE,
        'tb/frame/usr/file': Color.NONE,
        'tb/frame/usr/file/module': 'code',
        'tb/frame/usr/file/line': 'code',
        'tb/frame/usr/file/path': 'code',
        'tb/frame/usr/code': Color.NONE,
        'tb/frame/usr/highlight': Color.NONE,
        'tb/frame/lib': Color.STYLE_DIM,
        'tb/frame/lib/file': 'tb/frame/usr/file',
        'tb/frame/lib/file/module': 'tb/frame/usr/file/module',
        'tb/frame/lib/file/line': 'tb/frame/usr/file/line',
        'tb/frame/lib/file/path': 'tb/frame/usr/file/path',
        'tb/frame/lib/code': 'tb/frame/usr/code',
        'tb/frame/lib/highlight': 'tb/frame/usr/highlight',
        'tb/message': Color.FORE_RED | Color.STYLE_BOLD,

        'task/plain_text': Color.STYLE_DIM,
        'task/heading': Color.STYLE_BOLD,
        'task/comment': Color.NONE,
        'task/spinner/running': Color.FORE_MAGENTA,
        'task/spinner/done': Color.FORE_GREEN,
        'task/spinner/error': Color.FORE_RED,
        'task/progressbar': Color.NONE,
        'task/progressbar/done': Color.FORE_MAGENTA,
        'task/progressbar/inflight': Color.STYLE_DIM,
        'task/progressbar/pending': Color.STYLE_DIM,
        'task/progress/running': Color.FORE_MAGENTA,
        'task/progress/done': Color.FORE_GREEN,
        'task/progress/error': Color.FORE_RED,

        'cli/flag': 'note',
        'cli/default/code': 'code',
        'cli/section': 'msg/group',
    }

    def __init__(self, term_info: yuio.term.TermInfo):
        if term_info.has_ansi_256_colors:
            self.get_progressbar_gradient = lambda: Color.lerp(Color.fore_from_hex('#6719D5'), Color.fore_from_hex('#C00FBA'))

            if term_info.theme == yuio.term.TermTheme.DARK and term_info.background_color:
                self.colors['msg/hr'] = Color(fore=term_info.background_color.lighten(0.2))
            elif term_info.theme == yuio.term.TermTheme.DARK:
                self.colors['msg/hr'] = Color.fore_from_hex('#323232')
            elif term_info.theme == yuio.term.TermTheme.LIGHT and term_info.background_color:
                self.colors['msg/hr'] = Color(fore=term_info.background_color.darken(0.2))
            elif term_info.theme == yuio.term.TermTheme.LIGHT:
                self.colors['msg/hr'] = Color.fore_from_hex('#CCCCCC')

    def get_progressbar_gradient(self) -> _t.Callable[[float], Color]:
        return Color.lerp(Color.fore_from_hex('#6719D5'), Color.fore_from_hex('#C00FBA'))


def setup(
    *,
    use_colors: _t.Optional[bool] = None,
    theme: _t.Optional[Theme] = None,
    debug_output: _t.Optional[bool] = None,
):
    """Initial setup of the logging facilities.

    :param use_colors:
        use ANSI escape sequences to color the output.
    :param theme:
        override for the default theme.

    """

    global _DEBUG_OUTPUT

    if debug_output is not None:
        _DEBUG_OUTPUT = debug_output

    _handler().setup(use_colors, theme)


def _print(
    msg: str,
    args: _t.Optional[tuple],
    m_tag: str,
    add_newline: bool = True,
    ignore_suspended: bool = False,
    exc_info: _t.Union[None, bool, BaseException, _ExcInfo] = None,
    decorate: bool = False,
):
    if exc_info is True:
        exc_info = sys.exc_info()
    elif exc_info is False:
        exc_info = None
    elif isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)

    _handler().print(
        msg, args, m_tag,
        add_newline=add_newline,
        ignore_suspended=ignore_suspended,
        exc_info=exc_info,
        decorate=decorate,
    )


_DEBUG_OUTPUT: bool = False


def debug(msg: str, /, *args, **kwargs):
    """Log a debug message.

    """

    if _DEBUG_OUTPUT:
        _print(msg, args, 'debug', **kwargs)


def info(msg: str, /, *args, **kwargs):
    """Log an info message.

    """

    _print(msg, args, 'info', **kwargs)


def warning(msg: str, /, *args, **kwargs):
    """Log a warning message.

    """

    _print(msg, args, 'warning', **kwargs)


def success(msg: str, /, *args, **kwargs):
    """Log a success message.

    """

    _print(msg, args, 'success', **kwargs)


def error(msg: str, /, *args, **kwargs):
    """Log an error message.

    """

    _print(msg, args, 'error', **kwargs)


def error_with_tb(msg: str, /, *args, **kwargs):
    """Log an error message and capture the current exception.

    Call this function in the `except` clause of a `try` block
    or in an `__exit__` function of a context manager to attach
    current exception details to the log message.

    """

    kwargs.setdefault('exc_info', True)
    _print(msg, args, 'error', **kwargs)


def question(msg: str, /, *args, **kwargs):
    """Log a message with input prompts and other user communications.

    These messages don't end with newline.

    """

    kwargs.setdefault('add_newline', False)
    _print(msg, args, 'question', **kwargs)


def heading(msg: str, /, *args, **kwargs):
    """Log a heading message.

    """

    kwargs.setdefault('decorate', True)
    _print(msg, args, 'heading', **kwargs)


def hr():
    """Print a horizontal ruler.

    """

    _handler().hr()


def br():
    """Print an empty line.

    """

    _print('', None, '')


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

    if not get_terminal_info().has_interactive_input:
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

    if not get_terminal_info().has_interactive_input:
        return

    with SuspendLogging() as s:
        s.question(msg, *args, add_newline=True)
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

    if get_terminal_info().has_interactive_input:
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
    def debug(msg: str, /, *args, **kwargs):
        """Log a :func:`debug` message, ignore suspended status.

        """

        kwargs.setdefault('ignore_suspended', True)
        debug(msg, *args, **kwargs)


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

    def __init__(self, msg: str, /, *args, _parent: _t.Optional['Task'] = None):
        # Task properties should not be written to directly.
        # Instead, task should be sent to a handler for modification.
        # This ensures thread safety, because handler has a lock.
        # See handler's implementation details.
        self._msg: str = msg
        self._args: tuple = args
        self._progress: _Progress = None
        self._comment: _t.Optional[str] = None
        self._comment_args: _t.Optional[tuple] = None
        self._status: Task._Status = Task._Status.RUNNING
        self._subtasks: _t.List[Task] = []

        self._cached_msg = None

        if _parent is None:
            _handler().start_task(self)
        else:
            _handler().start_subtask(_parent, self)

    def progress(self, progress: _Progress, /):
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

        _handler().set_progress(self, progress)

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
    """A worker that reads messages from a queue and prints them to a stream.

    This worker lives in a separate daemon thread, so keyboard interrupts
    do not affect it.

    """

    def __init__(self):
        self._term_info = yuio.term.get_stderr_info()

        self._theme: Theme = DefaultTheme(self._term_info)

        self._use_colors = self._term_info.has_ansi_8_colors
        if 'FORCE_NO_COLORS' in os.environ:
            self._use_colors = False
        elif 'FORCE_COLORS' in os.environ:
            self._use_colors = True

        self._print_sticky_tasks = self._term_info.can_move_cursor and self._use_colors

        self._indent = 0
        self._printed_some_lines = False

        self._tasks: _t.List[Task] = []

        self._tasks_shown: int = 0

        self._suspended: int = 0
        self._suspended_lines: _t.List[str] = []

        self._spinner_state = 0
        self._spinner_next_update_time_ms = 0
        self._lock = threading.Lock()

        threading.Thread(target=self._bg_update, name='yuio_io_thread', daemon=True).start()

    def _bg_update(self):
        update_period_ms = max(self._theme.spinner_update_rate_ms, 10)
        while update_period_ms < 100:
            update_period_ms *= 2
        while update_period_ms > 250:
            update_period_ms /= 2
        while True:
            time.sleep(update_period_ms / 1000)
            with self._lock:
                self._update_visible_tasks(can_update_later=True)

    def setup(self, use_colors: _t.Optional[bool], theme: _t.Optional[Theme]):
        with self._lock:
            if use_colors is not None:
                self._use_colors = use_colors
                self._print_sticky_tasks = self._term_info.can_move_cursor and self._use_colors
            if theme is not None:
                self._theme = theme

    def indent(self):
        with self._lock:
            self._indent += 1

    def dedent(self):
        with self._lock:
            self._indent -= 1

            if self._indent < 0:
                self._indent = 0
                yuio._logger.error('unequal number of indents and dedents')

    def hr(self):
        with self._lock:
            msg = '\n' + '┄' * shutil.get_terminal_size().columns + '\n'
            line = self._format_line(msg, None, 'hr', True, None, False)

            self._emit(line)

            self._printed_some_lines = False

    def print(
        self,
        msg: str,
        args: _t.Optional[tuple],
        m_tag: str,
        /,
        *,
        add_newline: bool = True,
        ignore_suspended: bool = False,
        exc_info: _t.Optional[_ExcInfo] = None,
        decorate: bool = False,
    ):
        with self._lock:
            line = self._format_line(msg, args, m_tag, add_newline, exc_info, decorate)

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

    def set_progress(self, task: Task, progress: _Progress):
        with self._lock:
            can_update_later = (task._progress is None) == (progress is None)

            task._progress = progress
            task._cached_msg = None

            self._update_visible_tasks(can_update_later)

    def set_comment(self, task: Task, comment: _t.Optional[str], args):
        with self._lock:
            task._comment = comment
            task._comment_args = args
            task._cached_msg = None

            self._update_visible_tasks()

    def suspend(self):
        with self._lock:
            self._suspend()

    def resume(self):
        with self._lock:
            self._resume()

    #
    # IMPLEMENTATION: TASKS AND LOGGING
    # =================================
    #
    # These functions dispatch drawing calls from API,
    # taking care of `use_colors` and `suspended` things.
    #
    # Basic logic:
    #
    # - if we're not using colors, then we can't print progress bars and such.
    #   Therefore, it is always safe to print new lines in this state;
    # - if we're using colors, some progress bars may be displayed at the moment,
    #   so we need to take care of them before printing anything;
    # - if we're suspended though, no progress bars are displayed because we've hidden them.
    #   In this case, we're fine to print new lines even if we use colors.

    def _emit(self, msg: str, ignore_suspended: bool = False):
        if self._suspended and not ignore_suspended:
            # We can't print messages right now.
            self._suspended_lines.append(msg)
        elif self._suspended or not self._print_sticky_tasks:
            # There are no tasks displayed at the screen right now.
            # Print directly to stream.
            _STDERR.write(msg)
        else:
            # Some tasks may be displayed at the screen right now.
            # Do the full undraw-print-draw routine.
            self._hide_tasks()
            _STDERR.write(msg)
            self._show_tasks()

        self._printed_some_lines = True

    def _suspend(self):
        self._suspended += 1

        if self._suspended == 1 and self._print_sticky_tasks:
            # We're entering the suspended state, and some tasks may be displayed.
            # We need to hide them then.
            self._hide_tasks()

    def _resume(self):
        self._suspended -= 1

        if self._suspended == 0:
            # We're exiting the suspended state, so dump all stashed lines...
            for line in self._suspended_lines:
                _STDERR.write(line)
            self._suspended_lines.clear()

            # And we need to print tasks that we've hidden in `_suspend`.
            if self._print_sticky_tasks:
                self._show_tasks()

        if self._suspended < 0:
            yuio._logger.debug('unequal number of suspends and resumes')
            self._suspended = 0

    def _start_task(self, task: Task):
        if self._print_sticky_tasks:
            self._tasks.append(task)
            self._update_visible_tasks()
        else:
            self._emit(self._format_task(task))

    def _start_subtask(self, parent: Task, task: Task):
        if self._print_sticky_tasks:
            parent._subtasks.append(task)
            self._update_visible_tasks()
        else:
            self._emit(self._format_task(task))

    def _finish_task(self, task: Task, status: Task._Status):
        if task._status != Task._Status.RUNNING:
            yuio._logger.debug('trying to change status of an already stopped task')
            return

        task._status = status
        task._cached_msg = None

        if self._print_sticky_tasks:
            if task in self._tasks:
                self._tasks.remove(task)
            self._update_visible_tasks()
        else:
            self._emit(self._format_task(task))

    def _update_visible_tasks(self, can_update_later: bool = False):
        if self._print_sticky_tasks and not self._suspended:
            now = time.monotonic_ns() // 1_000_000
            if not can_update_later or now >= self._spinner_next_update_time_ms:
                self._hide_tasks()
                self._show_tasks()

    #
    # IMPLEMENTATION: TASK RENDERING
    # ==============================
    #
    # These functions draw sticked tasks when `use_colors` is on.

    def _hide_tasks(self):
        # Clear drawn tasks from the screen.

        assert self._print_sticky_tasks

        if self._tasks_shown > 0:
            _STDERR.write(f'\033[{self._tasks_shown}F\033[J')
            self._tasks_shown = 0

    def _show_tasks(self):
        # Draw current tasks.

        assert self._print_sticky_tasks

        now = time.monotonic_ns() // 1_000_000
        now -= now % self._theme.spinner_update_rate_ms
        self._spinner_state = now // self._theme.spinner_update_rate_ms
        self._spinner_next_update_time_ms = now + self._theme.spinner_update_rate_ms

        tasks: _t.List[_t.Tuple[Task, int]] = [
            (task, 0) for task in reversed(self._tasks)
        ]

        while tasks:
            task, indent = tasks.pop()

            _STDERR.write(self._format_task(task, indent))
            self._tasks_shown += 1

            indent += 1
            tasks.extend(
                [(subtask, indent) for subtask in reversed(task._subtasks)]
            )

    #
    # IMPLEMENTATION: LOG LINE FORMATTING
    # ===================================

    def _format_task(self, task: Task, indent: int = 0) -> str:
        # Format a task with respect to `_use_colors`.

        out: _t.List[_t.Union[str, Color]] = []

        t_tag = task._status.name.lower()

        plain_text_color = self._theme.get_color('task/plain_text')
        heading_color = self._theme.get_color('task/heading')
        progress_color = self._theme.get_color(f'task/{t_tag}/progress')

        if not self._print_sticky_tasks:
            out.extend(self._make_spinner_simple(t_tag))
            out.append(plain_text_color)
            out.append(' ')
            out.append(heading_color)
            out.extend(self._colorize(task._msg, task._args))
            out.append(plain_text_color)
            if task._status == Task._Status.RUNNING:
                out.append('...')
            else:
                out.append(' - ')
                out.append(progress_color)
                out.append(task._status.name.lower())
            out.append(Color.NONE)
            out.append('\n')
            return self._merge_colored_out(out)

        out.append('  ' * indent)
        out.append(plain_text_color)

        if task._status == Task._Status.RUNNING:
            if task._progress is None:
                out.extend(self._make_spinner(t_tag))
            else:
                out.extend(self._make_progress_bar(task._progress))
        else:
            out.extend(self._make_spinner_static(t_tag))

        out.append(plain_text_color)
        out.append(' ')
        out.extend(self._colorize(task._msg, task._args, heading_color))
        out.append(plain_text_color)

        if task._status in (Task._Status.DONE, Task._Status.ERROR):
            out.append(' - ')
            out.append(progress_color)
            out.append(task._status.name.lower())
            out.append(plain_text_color)
        elif task._status == Task._Status.RUNNING and task._progress is not None:
            out.append(' - ')
            if isinstance(task._progress, (float, int)):
                out.append(progress_color)
                out.append(f'{task._progress:0.0%}')
                out.append(plain_text_color)
            elif isinstance(task._progress, tuple):
                inflight = None
                if len(task._progress) == 2:
                    done, total = task._progress
                elif len(task._progress) == 3:
                    done, inflight, total = task._progress
                else:
                    done, total = 0, 0

                out.append(self._theme.get_color(f'task/{t_tag}/progress/done'))
                out.append(str(done))
                out.append(plain_text_color)

                if inflight is not None:
                    out.append('+')
                    out.append(self._theme.get_color(f'task/{t_tag}/progress/inflight'))
                    out.append(str(inflight))
                    out.append(plain_text_color)

                out.append('/')
                out.append(self._theme.get_color(f'task/{t_tag}/progress/total'))
                out.append(str(total))
                out.append(plain_text_color)

        if task._status == Task._Status.RUNNING and task._comment is not None:
            out.append(' - ')
            comment_color = self._theme.get_color(f'task/{t_tag}/comment')
            out.extend(self._colorize(task._comment, task._comment_args, comment_color))
            out.append(plain_text_color)

        out.append(Color.NONE)
        out.append('\n')

        return self._merge_colored_out(out)

    def _format_line(self, msg: str, args: _t.Optional[tuple], m_tag: str, add_newline: bool, exc_info: _t.Optional[_ExcInfo], decorate: bool) -> str:
        out: _t.List[_t.Union[str, Color]] = []

        if decorate and self._printed_some_lines:
            out.append('\n\n')

        if self._indent:
            out.append('  ' * self._indent)

        if decorate:
            out.append(self._theme.get_color(f'msg/{m_tag}/decoration'))
            out.append(self._theme.decoration_symbol)
            out.append(self._theme.get_color(f'msg/{m_tag}'))
            out.append(' ')

        out.extend(self._colorize(msg, args, self._theme.get_color(f'msg/{m_tag}/text')))

        if add_newline:
            out.append('\n')
            if decorate:
                out.append('\n')

        if exc_info is not None:
            out.extend(self._colorize_tb(''.join(traceback.format_exception(*exc_info)), '  ' * (self._indent + 1)))

        return self._merge_colored_out(out)

    def _format_record(self, record: logging.LogRecord) -> str:
        # Format a record with respect to `_use_colors`.

        out: _t.List[_t.Union[str, Color]] = []

        plain_text_color = self._theme.get_color('log/plain_text')

        asctime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(record.created))
        logger = record.name
        level = record.levelname
        if level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            level = level[:4]
        message = record.getMessage()

        out.extend([
            self._theme.get_color('log/asctime'),
            asctime,
            plain_text_color,
            ' ',
            self._theme.get_color('log/logger'),
            logger,
            plain_text_color,
            ' ',
            self._theme.get_color(f'log/level/{record.levelname.lower()}'),
            level,
            plain_text_color,
            ' ',
            self._theme.get_color(f'log/message/{record.levelname.lower()}'),
            message,
            plain_text_color,
            '\n',
        ])

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = ''.join(traceback.format_exception(*record.exc_info))
            out.extend(self._colorize_tb(record.exc_text, '  '))
        if record.stack_info:
            out.extend(self._colorize_tb(record.stack_info, '  '))

        out.append(Color.NONE)

        return self._merge_colored_out(out)

    #
    # IMPLEMENTATION: COLORING
    # ========================

    _TAG_RE = re.compile(r'<c:(?P<name>[a-z0-9, _/@]+)>|</c>')

    def _colorize(self, msg: str, args: _t.Optional[tuple], default_color: Color = Color.NONE) -> _t.Iterable[_t.Union[str, Color]]:
        # Colorize a message, process color tags if necessary.
        # Respect `_use_colors`.

        out: _t.List[_t.Union[str, Color]] = []

        if not self._use_colors:
            out.append(self._TAG_RE.sub('', msg))
        else:
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
                        color = color | self._theme.get_color(sub_name)
                    out.append(color)
                    stack.append(color)
                elif len(stack) > 1:
                    stack.pop()
                    out.append(stack[-1])

            out.append(msg[last_pos:])

            out.append(Color.NONE)

        if args:
            return [self._merge_colored_out(out) % args]
        else:
            return out

    _TB_RE = re.compile(r'^(?P<indent>[ |+]*)(Stack|Traceback|Exception Group Traceback) \(most recent call last\):$')
    _TB_MSG_RE = re.compile(r'^(?P<indent>[ |+]*)[A-Za-z_][A-Za-z0-9_]*($|:.*$)')
    _TB_LINE_FILE = re.compile(r'^[ |+]*File (?P<file>"[^"]*"), line (?P<line>\d+)(?:, in (?P<loc>.*))?$')
    _TB_LINE_HIGHLIGHT = re.compile(r'^[ |+^~-]*$')
    _SITE_PACKAGES = os.sep + 'lib' + os.sep + 'site-packages' + os.sep
    _LIB_PYTHON = os.sep + 'lib' + os.sep + 'python'

    def _colorize_tb(self, tb: str, indent: str) -> _t.Iterable[_t.Union[str, Color]]:
        if not self._use_colors:
            if indent:
                tb = textwrap.indent(tb, indent)
            return [tb]

        plain_text_color = self._theme.get_color('tb/plain_text')
        heading_color = self._theme.get_color('tb/heading')
        message_color = self._theme.get_color('tb/message')

        stack_normal_colors = self._stack_colors('usr')
        stack_lib_colors = self._stack_colors('lib')
        stack_colors = stack_normal_colors

        out: _t.List[_t.Union[str, Color]] = []

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

                        out.append(plain_text_color)
                        out.append(indent)
                        out.append(stack_indent)

                        out.append(stack_colors.file_color)
                        out.append('File ')
                        out.append(stack_colors.file_path_color)
                        out.append(file)
                        out.append(stack_colors.file_color)
                        out.append(', line ')
                        out.append(stack_colors.file_line_color)
                        out.append(line)
                        out.append(stack_colors.file_color)

                        if loc:
                            out.append(', in ')
                            out.append(stack_colors.file_module_color)
                            out.append(loc)
                            out.append(stack_colors.file_color)

                        out.append('\n')
                    elif match := self._TB_LINE_HIGHLIGHT.match(line):
                        out.append(plain_text_color)
                        out.append(indent)
                        out.append(stack_indent)
                        out.append(stack_colors.highlight_color)
                        out.append(line[len(stack_indent):])
                    else:
                        out.append(plain_text_color)
                        out.append(indent)
                        out.append(stack_indent)
                        out.append(stack_colors.code_color)
                        out.append(line[len(stack_indent):])
                    continue
                else:
                    # Stack has ended, this line is actually a message.
                    state = _HandlerImpl._StackParsingState.MESSAGE

            if state is _HandlerImpl._StackParsingState.MESSAGE:
                if line and line != '\n' and line.startswith(message_indent):
                    # We're still in the message.
                    out.append(plain_text_color)
                    out.append(indent)
                    out.append(message_indent)
                    out.append(message_color)
                    out.append(line[len(message_indent):])
                    continue
                else:
                    # Message has ended, this line is actually a plain text.
                    state = _HandlerImpl._StackParsingState.PLAIN_TEXT

            if state is _HandlerImpl._StackParsingState.PLAIN_TEXT:
                if match := self._TB_RE.match(line):
                    # Plain text has ended, this is actually a heading.
                    message_indent = match.group('indent').replace('+', '|')
                    stack_indent = message_indent + '  '

                    out.append(plain_text_color)
                    out.append(indent)
                    out.append(message_indent)
                    out.append(heading_color)
                    out.append(line[len(message_indent):])

                    state = _HandlerImpl._StackParsingState.STACK
                    continue
                elif match := self._TB_MSG_RE.match(line):
                    # Plain text has ended, this is an error message (without a traceback).
                    message_indent = match.group('indent').replace('+', '|')
                    stack_indent = message_indent + '  '

                    out.append(plain_text_color)
                    out.append(indent)
                    out.append(message_indent)
                    out.append(message_color)
                    out.append(line[len(message_indent):])

                    state = _HandlerImpl._StackParsingState.MESSAGE
                    continue
                else:
                    # We're still in plain text.
                    out.append(plain_text_color)
                    out.append(indent)
                    out.append(line)
                    continue

        out.append(Color.NONE)

        return out

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

    def _stack_colors(self, s_tag: str):
        return self._StackColors(self._theme, s_tag)

    def _make_progress_bar(self, progress: _Progress) -> _t.Iterable[_t.Union[str, Color]]:
        done = 0.0
        inflight = 0.0
        if isinstance(progress, tuple):
            if len(progress) == 2:
                done = float(progress[0]) / float(progress[1])
            elif len(progress) == 3:
                done = float(progress[0]) / float(progress[2])
                inflight = float(progress[1]) / float(progress[2])
        elif isinstance(progress, (float, int)):
            done = float(progress)
        done = max(0.0, min(1.0, done))
        inflight = max(0.0, min(1.0 - done, inflight))

        done_len = int(self._theme.progress_bar_width * done)
        inflight_len = int(self._theme.progress_bar_width * inflight)
        pending_len = self._theme.progress_bar_width - done_len - inflight_len

        color = self._theme.get_color(f'task/progressbar')
        done_color = self._theme.get_progressbar_gradient()
        inflight_color = self._theme.get_color(f'task/progressbar/inflight')
        pending_color = self._theme.get_color(f'task/progressbar/pending')

        out = []

        out.append(color)
        out.append(self._theme.progress_bar_start_symbol)

        for i in range(done_len):
            out.append(done_color(i / self._theme.progress_bar_width))
            out.append(self._theme.progress_bar_done_symbol)

        out.append(inflight_color)
        out.append(self._theme.progress_bar_inflight_symbol * inflight_len)

        out.append(pending_color)
        out.append(self._theme.progress_bar_pending_symbol * pending_len)

        out.append(color)
        out.append(self._theme.progress_bar_end_symbol)

        return out

    def _make_spinner(self, t_tag: str) -> _t.Iterable[_t.Union[str, Color]]:
        spinner_color = self._theme.get_color(f'task/spinner/{t_tag}')
        return [spinner_color, self._theme.spinner_pattern[self._spinner_state % len(self._theme.spinner_pattern)]]

    def _make_spinner_static(self, t_tag: str) -> _t.Iterable[_t.Union[str, Color]]:
        spinner_color = self._theme.get_color(f'task/spinner/{t_tag}')
        return [spinner_color, self._theme.spinner_static_symbol]

    def _make_spinner_simple(self, t_tag: str) -> _t.Iterable[_t.Union[str, Color]]:
        spinner_color = self._theme.get_color(f'task/spinner/{t_tag}')
        return [spinner_color, self._theme.spinner_simple_symbol]

    def _merge_colored_out(self, out: _t.Iterable[_t.Union[str, Color]]) -> str:
        if self._use_colors:
            cap = max(self._term_info.color_capability, yuio.term.TermColorCapability.ANSI_8)
        else:
            cap = yuio.term.TermColorCapability.NONE
        return ''.join([s if isinstance(s, str) else s.as_code(cap) for s in out])


@functools.cache
def _handler() -> _HandlerImpl:
    return _HandlerImpl()
