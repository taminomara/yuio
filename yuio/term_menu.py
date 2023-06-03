import dataclasses
from dataclasses import dataclass
import select
import sys
import termios
import tty
import contextlib
import re
import enum
import string
import typing as _t

import yuio.io
import yuio.term


_STDIN = open(sys.__stdin__.fileno(), 'rb', 0)


_WORD_SEPARATORS = '/:@ \t'
_N_CHOICES = 5


def choice(choices: _t.List[str]):
    filtered_choices = choices

    cur_choice = 0

    buffer = ''
    orig_buffer = ''

    _render_choices(filtered_choices, cur_choice, buffer)

    for event in _event_stream():
        if isinstance(event.key, str) and not event.ctrl and not event.alt:
            buffer += event.key
            orig_buffer = buffer
            filtered_choices = None
        elif event.key == _Key.BACKSPACE:
            buffer = buffer[:-1]
            orig_buffer = buffer
            filtered_choices = None
        elif event.ctrl and event.key == 'w':
            if match := re.match(r'^(.*[' + _WORD_SEPARATORS + r'])', buffer.rstrip(_WORD_SEPARATORS)):
                buffer = match.group(0)
            else:
                buffer = ''
            orig_buffer = buffer
            filtered_choices = None
        elif event.key == _Key.ENTER:
            if filtered_choices:
                sys.stdout.write('\n\x1b[J')
                sys.stdout.flush()
                return filtered_choices[cur_choice]
            else:
                sys.stdout.write('\a')
                sys.stdout.flush()
        elif filtered_choices:
            if event.key == _Key.ARROW_DOWN:
                cur_choice = (cur_choice + 1) % len(filtered_choices)
            elif event.key == _Key.ARROW_UP:
                cur_choice = (cur_choice - 1) % len(filtered_choices)
            elif event.key == _Key.TAB:
                cur_choice -= cur_choice % _N_CHOICES
                cur_choice += _N_CHOICES
                if cur_choice > len(filtered_choices):
                    cur_choice = 0
            elif event.key == _Key.SHIFT_TAB:
                cur_choice -= cur_choice % _N_CHOICES
                cur_choice -= _N_CHOICES
                if cur_choice < 0:
                    cur_choice = max(len(filtered_choices) - 1 - _N_CHOICES, 0)

        if filtered_choices is None:
            if buffer:
                filtered_choices = [choice for choice in choices if choice.startswith(buffer)]
            else:
                filtered_choices = choices
            cur_choice = 0

        if cur_choice > 0:
            buffer = filtered_choices[cur_choice]
        else:
            buffer = orig_buffer

        _render_choices(filtered_choices, cur_choice, buffer)


def _render_choices(choices:  _t.List[str], choice_index: int, query: str):
    search_color = '\x1b[0;2m'
    highlight_color = '\x1b[0;35m'
    reset_color = '\x1b[0m'

    choice_index_in_page = choice_index % _N_CHOICES
    page_begin = choice_index - choice_index_in_page

    out = []

    out.extend(
        (highlight_color + '> ' if i == choice_index_in_page else '  ') + choice + reset_color + '\n'
        for i, choice in enumerate(choices[page_begin:page_begin + _N_CHOICES])
    )

    line = f'\x1b[J\n{"".join(out)}\x1b[{len(out) + 1}F\x1b[G\x1b[K{search_color}/ '
    if query:
        line += query + reset_color
    else:
        line += '  (type to filter, up/down to navigate)\x1b[3G' + reset_color

    sys.stdout.write(line)
    sys.stdout.flush()


class _Key(enum.Enum):
    ESCAPE = enum.auto()
    BACKSPACE = enum.auto()
    TAB = enum.auto()
    ENTER = enum.auto()
    SHIFT_TAB = enum.auto()
    DELETE = enum.auto()
    HOME = enum.auto()
    END = enum.auto()
    PAGE_UP = enum.auto()
    PAGE_DOWN = enum.auto()

    ARROW_UP = enum.auto()
    ARROW_DOWN = enum.auto()
    ARROW_LEFT = enum.auto()
    ARROW_RIGHT = enum.auto()


@dataclass(frozen=True, slots=True)
class _Event:
    key: str | _Key = ''
    ctrl: bool = False
    alt: bool = False


def _event_stream() -> _t.Iterable[_Event]:
    term_info = yuio.io.get_term_info()
    if not term_info.is_interactive and term_info.can_move_cursor:
        return

    with _set_cbreak():
        while True:
            key = _getch()
            while _kbhit():
                key += _getch()
            key = key.decode(sys.__stdin__.encoding, 'replace')

            # Esc key
            if key == '\x1b':
                yield _Event(_Key.ESCAPE)
            elif key == '\x1b\x1b':
                yield _Event(_Key.ESCAPE, alt=True)

            elif key == '\t':
                yield _Event(_Key.TAB)
            elif key == '\n':
                yield _Event(_Key.ENTER)
            elif key == '\x7f':
                yield _Event(_Key.BACKSPACE)

            # CSI
            elif key == '\x1b[':
                yield _Event('[', alt=True)
            elif key.startswith('\x1b['):
                yield from _parse_csi(key[2:])
            elif key.startswith('\x1b\x1b['):
                yield from _parse_csi(key[3:], alt=True)

            # SS2
            elif key == '\x1bN':
                yield _Event('N', alt=True)
            elif key.startswith('\x1bN'):
                pass
            elif key.startswith('\x1b\x1bN'):
                pass

            # SS3
            elif key == '\x1bO':
                yield _Event('O', alt=True)
            elif key.startswith('\x1bO'):
                pass
            elif key.startswith('\x1b\x1bO'):
                pass

            # DSC
            elif key == '\x1bP':
                yield _Event('P', alt=True)
            elif key.startswith('\x1bP'):
                pass
            elif key.startswith('\x1b\x1bP'):
                pass

            # Alt + Key
            elif key.startswith('\x1b'):
                yield from _parse_char(key[1:], alt=True)

            # Just normal Keypress
            else:
                yield from _parse_char(key)



@contextlib.contextmanager
def _set_cbreak():
    prev_mode = termios.tcgetattr(_STDIN)
    tty.setcbreak(sys.__stdin__, termios.TCSANOW)

    try:
        yield
    finally:
        termios.tcsetattr(_STDIN, termios.TCSAFLUSH, prev_mode)

def _getch() -> bytes:
    return _STDIN.read(1)

def _kbhit() -> bool:
    return bool(select.select([_STDIN], [], [], 0)[0])

_CSI_CODES = {
    '1': _Key.HOME,
    '3': _Key.DELETE,
    '4': _Key.END,
    '5': _Key.PAGE_UP,
    '6': _Key.PAGE_DOWN,
    '7': _Key.HOME,
    '8': _Key.END,
    'A': _Key.ARROW_UP,
    'B': _Key.ARROW_DOWN,
    'C': _Key.ARROW_RIGHT,
    'D': _Key.ARROW_LEFT,
    'F': _Key.END,
    'H': _Key.HOME,
    'Z': _Key.SHIFT_TAB,
}

def _parse_csi(csi: str, ctrl: bool = False, alt: bool = False) -> _t.Iterable[_Event]:
    if match := re.match(r'^(?P<code>\d+)?(?:;(?P<modifier>\d+))?~$', csi):
        code = match.group('code') or '1'
        modifier = int(match.group('modifier') or '1') - 1
    elif match := re.match(r'^(?:\d+;)?(?P<modifier>\d+)?(?P<code>[A-Z])$', csi):
        code = match.group('code') or '1'
        modifier = int(match.group('modifier') or '1') - 1
    else:
        return

    alt |= bool(modifier & 2)
    ctrl |= bool(modifier & 4)

    if (key := _CSI_CODES.get(code)) is not None:
        yield _Event(key, ctrl, alt)

def _parse_char(char: str, ctrl: bool = False, alt: bool = False) -> _t.Iterable[_Event]:
    if len(char) == 1 and '\x01' <= char <= '\x1A':
        yield _Event(chr(ord(char) - 0x1 + ord('a')), True, alt)
    elif len(char) == 1 and '\x0C' <= char <= '\x1F':
        yield _Event(chr(ord(char) - 0x1C + ord('4')), True, alt)
    elif (len(char) == 1 and (char in string.printable or ord(char) >= 160)) or len(char) > 1:
        yield _Event(char, ctrl, alt)

print(choice(['A', 'B', 'CDS', 'qux', 'duo', 'phaaa', 'quick', 'brown', 'fox']))
