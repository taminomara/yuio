# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides autocompletion functionality for widgets and CLI.

"""

import abc
import contextlib
import dataclasses
import functools
import math
import os
import pathlib
import string
import sys
import typing as _t
from dataclasses import dataclass

import yuio


@dataclass(frozen=True, slots=True)
@functools.total_ordering
class Completion:
    """A single completion.

    """

    #: See :class:`CompletionCollector.iprefix` for details.
    iprefix: str

    #: Text of the completion.
    completion: str

    #: See :class:`CompletionCollector.rsuffix` for details.
    rsuffix: str

    #: See :class:`CompletionCollector.rsymbols` for details.
    rsymbols: str

    #: See :class:`CompletionCollector.isuffix` for details.
    isuffix: str

    #: Short comment displayed alongside the completion.
    comment: _t.Optional[str]

    #: Prefix that will be displayed before :attr:`~Completion.completion`
    #: when listing completions, but will not be inserted once completion
    #: is applied.
    dprefix: str

    #: Like :attr:`~Completion.dprefix`, but it's a suffix.
    dsuffix: str

    #: Group id, used to sort completions.
    #:
    #: Group IDs are tuples of ints, but this is an implementation detail,
    #: and you shouldn't rely on it.
    group_id: _t.Tuple[int, int]

    #: Color tag that's used when displaying this completion.
    #:
    #: See :meth:`CompletionCollector.add_group` for details.
    group_color_tag: _t.Optional[str]

    def __lt__(self, other: 'Completion') -> bool:
        """Completions are ordered by their groups and then alphabetically.

        """

        return (
            self.group_id < other.group_id
            or (self.group_id == other.group_id and self.completion < other.completion)
        )


@dataclass(init=False, eq=False, repr=False,
           **({} if sys.version_info < (3, 10, 0) else {"match_args": False}))
class CompletionCollector:
    """A class that collects completions as completers are running.

    The text that is being completed is split into four parts, similar
    to what you might see in ZSH completion widgets. The main two are:

    .. autoattribute:: prefix

    .. autoattribute:: suffix

    When completions are added to the collector, they are checked against
    the current prefix to determine if the match the entered text. If they
    match, the completion system will replace text from `prefix` and `suffix`
    with the new completion string.

    The two additional parts are:

    .. autoattribute:: iprefix

    .. autoattribute:: isuffix

    For example, suppose you're completing a second element
    of a colon-separated list. The list completer will set up
    the collector so that `prefix` and `suffix` contain parts of the
    current list element, while `iprefix` and `isuffix` contain
    the rest of the elements:

    .. code-block:: text

       list_element_1:list_el|ement_2:list_element_3
       └┬────────────┘└┬────┘│└┬────┘└┬────────────┘
        iprefix       prefix │ suffix isuffix
                             └ cursor

    Now, if the completer adds a completion ``'list_elements'``,
    this text will replace the `prefix` and `suffix`, but not `iprefix`
    and `isuffix`. So, after the completion is applied, the string will
    look like so:

    .. code-block:: text

       list_element_1:completed_part:list_element_3
                      └┬───────────┘
                       this got replaced

    .. autoattribute:: rsuffix

    .. autoattribute:: rsymbols

    """

    #: Contains text that goes before the :attr:`~CompletionCollector.prefix`.
    #:
    #: This prefix is not considered when checking whether a completion
    #: matches a text, and it is not replaced by the completion. It will also
    #: not be shown in the table of completions.
    #:
    #: This prefix starts empty, and then parts of :attr:`~CompletionCollector.prefix`
    #: are moved to :attr:`~CompletionCollector.iprefix` as completers split it into
    #: list elements.
    iprefix: str

    #: Portion of the completed text before cursor.
    prefix: str

    #: Portion of the completed text after the cursor.
    suffix: str

    #: Starts empty, and may be set to hold a list separator.
    #:
    #: This suffix will be added after the completion. However, it will be automatically
    #: removed if the user types one of :attr:`CompletionCollector.rsymbols`,
    #: or moves cursor, or alters input in some other way.
    rsuffix: str

    #: If user types one of
    rsymbols: str

    #: Similar to :attr:`CompletionCollector.iprefix`, but for suffixes.
    isuffix: str

    # Internal fields.
    _group_id: int
    _group_sorted: bool
    _group_color_tag: _t.Optional[str]

    def __init__(self, text: str, pos: int, /):
        self.iprefix = ''
        self.prefix = text[:pos]
        self.suffix = text[pos:]
        self.rsuffix = ''
        self.rsymbols = ''
        self.isuffix = ''

        self._group_id = 0
        self._group_sorted = True
        self._group_color_tag = None

        self._completions: _t.List[Completion] = []

    @property
    def full_prefix(self) -> str:
        """Portion of the final completed text that goes before the cursor.

        """

        return self.iprefix + self.prefix

    @property
    def full_suffix(self) -> str:
        """Portion of the final completed text that goes after the cursor.

        """

        return self.suffix + self.isuffix

    @contextlib.contextmanager
    def save_state(self):
        """Save current state of the collector, i.e. prefixes,
        suffixes, etc., upon entering this context manager,
        then restore state upon exiting.

        Use this context manager when you need to call nested
        completers more than once to prevent changes made in
        one nested completer bleeding out into another
        nested completer.

        """

        state = {f.name: getattr(self, f.name) for f in dataclasses.fields(self)}

        try:
            yield
        finally:
            for name, value in state.items():
                setattr(self, name, value)

    def add(
        self,
        completion: str,
        /,
        *,
        comment: _t.Optional[str] = None,
        dprefix: str = '',
        dsuffix: str = '',
        color_tag: _t.Optional[str] = None,
    ):
        """Add a new completion.

        :param completion:
            completed text without :attr:`~CompletionCollector.iprefix`
            and :attr:`~CompletionCollector.isuffix`. This text will replace
            :attr:`~CompletionCollector.prefix` and :attr:`~CompletionCollector.suffix`.
        :param comment:
            additional comment that will be displayed near the completion.
        :param color_tag:
            allows overriding color tag from the group.

        """

        if completion and completion.startswith(self.prefix):
            self._add(completion, comment=comment, dprefix=dprefix, dsuffix=dsuffix, color_tag=color_tag)

    def _add(
        self,
        completion: str,
        /,
        *,
        comment: _t.Optional[str] = None,
        dprefix: str = '',
        dsuffix: str = '',
        color_tag: _t.Optional[str] = None,
    ):
        if not self.isuffix or self.isuffix[0] in string.whitespace:
            # Only add `rsuffix` if we're at the end of an array element.
            # Don't add `rsuffix` if we're in the middle of an array, unless the array
            # is separated by spaces.
            rsuffix = self.rsuffix
            rsymbols = self.rsymbols
        else:
            rsuffix = ''
            rsymbols = ''

        if self._group_sorted:
            group_id = (self._group_id, 0)
        else:
            group_id = (self._group_id, len(self._completions))

        if color_tag is None:
            color_tag = self._group_color_tag

        self._completions.append(Completion(
            iprefix=self.iprefix,
            completion=completion,
            rsuffix=rsuffix,
            rsymbols=rsymbols,
            isuffix=self.isuffix,
            comment=comment,
            dprefix=dprefix,
            dsuffix=dsuffix,
            group_id=group_id,
            group_color_tag=color_tag,
        ))

    def add_group(self, /, *, sorted: bool = True, color_tag: _t.Optional[str] = None):
        """Add a new completions group.

        All completions added after call to this method will be placed to the new group.
        The will be grouped together, and colored according to the group's color tag.

        :param sorted:
            controls whether completions in the new group should be sorted.
        :param color_tag:
            which color tag should be used to display completions
            and their help messages for this group.

            See :attr:`yuio.widget.Option.color_tag` for details.

        """

        self._group_id += 1
        self._group_sorted = sorted
        self._group_color_tag = color_tag

    @property
    def num_completions(self) -> int:
        """Return number of completions that were added so far.

        """

        return len(self._completions)

    def split_off_prefix(self, delim: _t.Optional[str] = None, /):
        """Move everything up to the last occurrence of `delim`
        from :attr:`~CompletionCollector.prefix`
        to :attr:`~CompletionCollector.iprefix`.

        """

        delim = delim or ' '
        parts = self.prefix.rsplit(delim, maxsplit=1)
        if len(parts) > 1:
            self.iprefix += parts[0] + delim
            self.prefix = parts[1]

    def split_off_suffix(self, delim: _t.Optional[str] = None, /):
        """Move everything past the first occurrence of `delim`
        from :attr:`~CompletionCollector.suffix`
        to :attr:`~CompletionCollector.isuffix`.

        """

        delim = delim or ' '
        parts = self.suffix.split(delim, maxsplit=1)
        if len(parts) > 1:
            self.suffix = parts[0]
            self.isuffix = delim + parts[1] + self.isuffix

    def finalize(self) -> _t.List[Completion]:
        """Finish collecting completions and return everything that was collected.

        Do not reuse a collector after it was finalized.

        """

        if len(self._completions) > 1:
            c0 = self._completions[0]

            iprefix = c0.iprefix
            isuffix = c0.isuffix

            if (
                self.full_prefix.startswith(iprefix)
                and self.full_suffix.endswith(isuffix)
                and all(c.iprefix == iprefix and c.isuffix == isuffix for c in self._completions)
            ):
                # If all completions have the same `iprefix` and `isuffix`...
                common_prefix = _commonprefix(list(c.completion for c in self._completions))
                if common_prefix and len(iprefix) + len(common_prefix) > len(self.iprefix) + len(self.prefix):
                    # ...and they have a common prefix that is longer than what's entered so far,
                    # then complete this common prefix.
                    rsuffix = ''
                    rsymbols = ''
                    if all(common_prefix == c.completion and rsuffix == c.rsuffix for c in self._completions):
                        # If completing common prefix actually fulfills a completion, add `rsuffix` as well.
                        rsuffix = c0.rsuffix
                        rsymbols = c0.rsymbols
                    return [
                        Completion(
                            iprefix=iprefix,
                            completion=common_prefix,
                            rsuffix=rsuffix,
                            rsymbols=rsymbols,
                            isuffix=isuffix,
                            comment=None,
                            dprefix='',
                            dsuffix='',
                            group_id=(0, 0),
                            group_color_tag=None,
                        )
                    ]

        self._completions.sort()
        return self._completions


_MAX_COMPLETION_CORRECTIONS: int = 1
_MAX_COMPLETION_CORRECTIONS_RATE: float = 1 / 3


@_t.final
class _CorrectingCollector(CompletionCollector):
    def __init__(self, text: str, pos: int):
        super().__init__(text, pos)

        self._has_corrections = False

    def add(
        self,
        completion: str,
        /,
        *,
        comment: _t.Optional[str] = None,
        dprefix: str = '',
        dsuffix: str = '',
        color_tag: _t.Optional[str] = None,
    ):
        if not completion:
            return

        a = self.prefix + self.suffix
        b = completion
        corrections = _corrections(a, b)
        threshold = (
            _MAX_COMPLETION_CORRECTIONS
            + _MAX_COMPLETION_CORRECTIONS_RATE * (len(a) + len(b)) / 2
        )

        if corrections <= 1:
            # this is a simple mistype, add it as usual
            self._add(completion, comment=comment)
        elif corrections <= threshold:
            # this is a correction, add it into corrections group
            if comment:
                comment = "corrected: " + comment
            else:
                comment = "corrected"
            with self.save_state():
                self._group_id = 0xfffffffe  # (big enough) - 1
                self._group_color_tag = "corrected"
                self._add(completion, comment=comment, dprefix=dprefix, dsuffix=dsuffix, color_tag=color_tag)
                self._has_corrections = True

    def finalize(self) -> _t.List[Completion]:
        if self._has_corrections:
            c0 = self._completions[0]

            iprefix = ''
            prefix = self.full_prefix
            suffix = self.full_suffix
            isuffix = ''

            if prefix.startswith(c0.iprefix):
                l = len(c0.iprefix)
                iprefix = prefix[:l]
                prefix = prefix[l:]

            if suffix.endswith(c0.isuffix):
                l = len(c0.isuffix)
                isuffix = suffix[-l:]
                suffix = suffix[:-l]

            # If we have corrections, add original value to the end.
            with self.save_state():
                self._group_id = 0xffffffff  # (big enough)
                self._group_color_tag = "original"
                self.iprefix = iprefix
                self.isuffix = isuffix
                self._add(prefix + suffix, comment="original")

        self._completions.sort()
        return self._completions


def _corrections(a: str, b: str) -> float:
    # Damerau–Levenshtein distance (Optimal String Alignment distance)

    a = a.casefold()
    b = b.casefold()
    d = [x[:] for x in [[0.0] * (len(b) + 1)] * (len(a) + 1)]
    for i in range(len(a) + 1):
        d[i][0] = i
    for j in range(len(b) + 1):
        d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            d[i][j] = min(
                # Add to `a`:
                d[i - 1][j] + 1,
                # Add to `b`:
                d[i][j - 1] + 1,
                # Replace:
                d[i - 1][j - 1] + (a[i - 1] != b[j - 1]),
                # Transpose:
                d[i - 2][j - 2] + (a[i - 1] != b[j - 1])
                if i > 2 and j > 2 and a[i - 2:i] == b[j - 1:j - 3:-1]
                else math.inf,
            )

    return d[-1][-1]


def _commonprefix(m: _t.List[str]) -> str:
    if not m:
        return ''
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


class Completer(abc.ABC):
    """An interface for text completion providers.

    """

    def complete(self, text: str, pos: int, /) -> _t.List[Completion]:
        """Complete the given text at the given cursor position.

        """

        collector = CompletionCollector(text, pos)
        with collector.save_state():
            self.process(collector)
        completions = collector.finalize()
        if completions:
            return completions

        collector = _CorrectingCollector(text, pos)
        with collector.save_state():
            self.process(collector)
        return collector.finalize()

    @abc.abstractmethod
    def process(self, collector: CompletionCollector, /):
        """Add completions to the given collector.

        """


@dataclass(frozen=True, slots=True)
class CompletionChoice:
    """A single completion option for the :chass:`Choice` completer.

    """

    #: This string will replace an element that is being completed.
    completion: str

    #: Short comment displayed alongside the completion.
    comment: _t.Optional[str] = None


class Choice(Completer):
    """Completes input from a predefined list of completions.

    """

    def __init__(self, choices: _t.List[CompletionChoice], /):
        self._choices = choices

    def process(self, collector: CompletionCollector, /):
        for choice in self._choices:
            collector.add(choice.completion, comment=choice.comment)


class List(Completer):
    """Completes a value-separated list of elements.

    """

    def __init__(self, inner: Completer, /, *, delimiter: _t.Optional[str] = None):
        self._inner = inner
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def process(self, collector: CompletionCollector, /):
        collector.split_off_prefix(self._delimiter)
        collector.split_off_suffix(self._delimiter)
        collector.rsuffix = self._delimiter or ' '
        collector.rsymbols += self._delimiter or string.whitespace
        self._inner.process(collector)


class Tuple(Completer):
    """Completes a value-separated tuple of elements.

    """

    def __init__(self, *inners: Completer, delimiter: _t.Optional[str] = None):
        self._inners = inners
        if delimiter == '':
            raise ValueError('empty delimiter')
        self._delimiter = delimiter

    def process(self, collector: CompletionCollector, /):
        pos = len(collector.prefix.split(self._delimiter))
        if (
            pos
            and self._delimiter is None
            and collector.prefix
            and collector.prefix[-1] in string.whitespace
        ):
            # `.split(None)` will trim whitespaces at the end.
            # Make sure we count those towards the current position in the tuple.
            pos += 1
        if pos > len(self._inners):
            pos = len(self._inners)
        if pos > 0:
            pos -= 1

        collector.split_off_prefix(self._delimiter)
        collector.split_off_suffix(self._delimiter)
        collector.rsuffix = self._delimiter or ' '
        collector.rsymbols += self._delimiter or string.whitespace

        self._inners[pos].process(collector)


class File(Completer):
    def __init__(self, extensions: _t.Optional[_t.Collection[str]] = None):
        self._extensions = extensions

    def process(self, collector: CompletionCollector, /):
        base, name = os.path.split(collector.prefix)
        collector.iprefix += os.path.join(base, '')
        collector.prefix = name
        collector.suffix = collector.suffix.split(os.sep, 2)[0]
        resolved = pathlib.Path(base).resolve()
        rsuffix = collector.rsuffix
        if resolved.is_dir():
            if name.startswith('.'):
                collector.rsuffix = ''
                collector.add('./', color_tag="dir")
                collector.add('../', color_tag="dir")
            for path in resolved.iterdir():
                if path.is_dir():
                    if path.is_symlink():
                        color_tag = "symlink"
                        dsuffix = "@"
                    else:
                        color_tag = "dir"
                        dsuffix = ""
                    collector.rsuffix = ''
                    collector.add(path.name + os.sep, color_tag=color_tag, dsuffix=dsuffix)
                elif (
                    self._extensions is None
                    or any(path.name.endswith(ext) for ext in self._extensions)
                ):
                    collector.rsuffix = rsuffix
                    color_tag = None
                    dsuffix = ''
                    if path.is_file():
                        if os.access(path, os.X_OK):
                            color_tag = "exec"
                            dsuffix = "*"
                        else:
                            color_tag = "file"
                    elif path.is_symlink():
                        color_tag = "symlink"
                        dsuffix = "@"
                    elif path.is_socket():
                        color_tag = "socket"
                        dsuffix = "="
                    elif path.is_fifo():
                        color_tag = "pipe"
                        dsuffix = "|"
                    elif path.is_block_device():
                        color_tag = "block_device"
                        dsuffix = "#"
                    elif path.is_char_device():
                        color_tag = "char_device"
                        dsuffix = "%"
                    collector.add(path.name, color_tag=color_tag, dsuffix=dsuffix)


class Dir(File):
    def __init__(self):
        super().__init__([])
