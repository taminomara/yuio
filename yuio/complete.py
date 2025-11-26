# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides autocompletion functionality for widgets and CLI.


Completer basics
----------------

All completers are derived from the :class:`Completer` base class
with a simple interface:

.. autoclass:: Completer
   :members:

.. autoclass:: Completion
   :members:


Completers
----------

Yuio provides basic completers that cover most of the cases:

.. autoclass:: Empty

.. autoclass:: Alternative

.. autoclass:: Choice

.. autoclass:: Option
   :members:

.. autoclass:: List

.. autoclass:: Tuple

.. autoclass:: File

.. autoclass:: Dir


Implementing your own completer
-------------------------------

To implement a custom completer, subclass :class:`Completer` and implement
its :meth:`~Completer._process` method.

.. note::

   When using a custom completer for CLI flags in :mod:`yuio.app`,
   completion script will invoke your program with special arguments
   to run the completer and get its result.

.. class:: Completer
   :noindex:

   .. automethod:: _process

.. autoclass:: CompletionCollector

"""

from __future__ import annotations

import abc
import argparse
import contextlib
import dataclasses
import enum
import functools
import json
import math
import os
import pathlib
import re
import shutil
import string
import subprocess
import sys
import typing
from dataclasses import dataclass

import yuio
import yuio.string
from yuio import _typing as _t

__all__ = [
    "Alternative",
    "Choice",
    "Completer",
    "Completion",
    "CompletionCollector",
    "Dir",
    "Empty",
    "File",
    "List",
    "Option",
    "Tuple",
]


@dataclass(frozen=True, **yuio._with_slots())
@functools.total_ordering
class Completion:
    """
    A single completion.

    """

    iprefix: str
    """
    See :class:`CompletionCollector.iprefix` for details.

    """

    completion: str
    """
    Text of the completion.

    """

    rsuffix: str
    """
    See :class:`CompletionCollector.rsuffix` for details.

    """

    rsymbols: str
    """
    See :class:`CompletionCollector.rsymbols` for details.

    """

    isuffix: str
    """
    See :class:`CompletionCollector.isuffix` for details.

    """

    comment: str | None
    """
    Short comment displayed alongside the completion.

    """

    dprefix: str
    """
    Prefix that will be displayed before :attr:`~Completion.completion`
    when listing completions, but will not be inserted once completion
    is applied.

    """

    dsuffix: str
    """
    Like :attr:`~Completion.dprefix`, but it's a suffix.

    """

    group_id: yuio.SupportsLt[_t.Any] = dataclasses.field(repr=False)
    """
    Group id, used to sort completions.

    Actual content of this property is an implementation detail.

    """

    group_color_tag: str | None
    """
    Color tag that's used when displaying this completion.

    See :meth:`CompletionCollector.add_group` for details.

    """

    def __lt__(self, other: Completion) -> bool:
        """
        Completions are ordered by their groups and then alphabetically.

        """

        return self.group_id < other.group_id or (
            self.group_id == other.group_id and self.completion < other.completion
        )


@dataclass(
    init=False,
    eq=False,
    repr=False,
    **({} if sys.version_info < (3, 10, 0) else {"match_args": False}),
)
class CompletionCollector:
    """
    A class that collects completions as completers are running.

    The text that is being completed is split into four parts, similar
    to what you might see in ZSH completion widgets. The main two are:

    .. autoattribute:: prefix

    .. autoattribute:: suffix

    When completions are added to the collector, they are checked against
    the current prefix to determine if they match the entered text. If they
    do, the completion system will replace text from ``prefix`` and ``suffix``
    with the new completion string.

    The two additional parts are:

    .. autoattribute:: iprefix

    .. autoattribute:: isuffix

    For example, suppose you're completing a second element
    of a colon-separated list. The list completer will set up
    the collector so that ``prefix`` and ``suffix`` contain parts of the
    current list element, while ``iprefix`` and ``isuffix`` contain
    the rest of the elements:

    .. code-block:: text

       list_element_1:list_el|ement_2:list_element_3
       └┬────────────┘└┬────┘│└┬────┘└┬────────────┘
        iprefix       prefix │ suffix isuffix
                             └ cursor

    Now, if the completer adds a completion ``"list_elements"``,
    this text will replace the ``prefix`` and ``suffix``, but not ``iprefix``
    and ``isuffix``. So, after the completion is applied, the string will
    look like so:

    .. code-block:: text

       list_element_1:list_elements:list_element_3
                      └┬──────────┘
                       this got replaced

    Finally, there is ``rsuffix``:

    .. autoattribute:: rsuffix

    .. autoattribute:: rsymbols

    So, when completing a colon-separated list, colons will be added and removed
    automatically, similar to how ZSH does it.

    .. autoattribute:: dedup_words

    .. autoattribute:: full_prefix

    .. autoattribute:: full_suffix

    .. autoattribute:: text

    .. autoattribute:: num_completions

    .. automethod:: add

    .. automethod:: add_group

    .. automethod:: save_state

    .. automethod:: split_off_prefix

    .. automethod:: split_off_suffix

    .. automethod:: finalize

    """

    iprefix: str
    """
    Contains text that goes before the :attr:`~CompletionCollector.prefix`.

    This prefix is not considered when checking whether a completion
    matches a text, and it is not replaced by the completion. It will also
    not be shown in the table of completions.

    This prefix starts empty, and then parts of :attr:`~CompletionCollector.prefix`
    are moved to :attr:`~CompletionCollector.iprefix` as completers split it into
    list elements.

    """

    prefix: str
    """
    Portion of the completed text before the cursor.

    """

    suffix: str
    """
    Portion of the completed text after the cursor.

    """

    rsuffix: str
    """
    Starts empty, and may be set to hold a list separator.

    This suffix will be added after the completion. However, it will be automatically
    removed if the user types one of :attr:`CompletionCollector.rsymbols`,
    or moves cursor, or alters input in some other way.

    This property is mutable and can be changed by completers.

    """

    rsymbols: str
    """
    If user types one of the symbols from this string,
    :attr:`~.CompletionCollector.rsuffix` will be removed.

    This property is mutable and can be changed by completers.

    """

    isuffix: str
    """
    Similar to :attr:`CompletionCollector.iprefix`, but for suffixes.

    """

    dedup_words: frozenset[str]
    """
    Completions from this set will not be added. This is useful
    when completing lists of unique values.

    This property is mutable and can be changed by completers.

    """

    # Internal fields.
    _group_id: int
    _group_sorted: bool
    _group_color_tag: str | None

    def __init__(self, text: str, pos: int, /):
        self.iprefix = ""
        self.prefix = text[:pos]
        self.suffix = text[pos:]
        self.rsuffix = ""
        self.rsymbols = ""
        self.isuffix = ""
        self.dedup_words = frozenset()

        self._group_id = 0
        self._group_sorted = True
        self._group_color_tag = None

        self._completions: list[Completion] = []

    @property
    def full_prefix(self) -> str:
        """
        Portion of the final completed text that goes before the cursor.

        """

        return self.iprefix + self.prefix

    @property
    def full_suffix(self) -> str:
        """
        Portion of the final completed text that goes after the cursor.

        """

        return self.suffix + self.isuffix

    @property
    def text(self) -> str:
        """
        Portion of the text that is being autocompleted.

        """

        return self.prefix + self.suffix

    @contextlib.contextmanager
    def save_state(self):
        """
        Save current state of the collector, i.e. prefixes,
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
        comment: str | None = None,
        dprefix: str = "",
        dsuffix: str = "",
        color_tag: str | None = None,
    ):
        """
        Add a new completion.

        :param completion:
            completed text without :attr:`~CompletionCollector.iprefix`
            and :attr:`~CompletionCollector.isuffix`. This text will replace
            :attr:`~CompletionCollector.prefix` and :attr:`~CompletionCollector.suffix`.
        :param comment:
            additional comment that will be displayed near the completion.
        :param color_tag:
            allows overriding color tag from the group.

        """

        if (
            completion
            and completion not in self.dedup_words
            and completion.startswith(self.prefix)
        ):
            self._add(
                completion,
                comment=comment,
                dprefix=dprefix,
                dsuffix=dsuffix,
                color_tag=color_tag,
            )

    def _add(
        self,
        completion: str,
        /,
        *,
        comment: str | None = None,
        dprefix: str = "",
        dsuffix: str = "",
        color_tag: str | None = None,
    ):
        if not self.isuffix or self.isuffix[0] in string.whitespace:
            # Only add `rsuffix` if we're at the end of an array element.
            # Don't add `rsuffix` if we're in the middle of an array, unless the array
            # is separated by spaces.
            rsuffix = self.rsuffix
            rsymbols = self.rsymbols
        else:
            rsuffix = ""
            rsymbols = ""

        if self._group_sorted:
            group_id = (self._group_id, 0)
        else:
            group_id = (self._group_id, len(self._completions))

        if color_tag is None:
            color_tag = self._group_color_tag

        self._completions.append(
            Completion(
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
            )
        )

    def add_group(self, /, *, sorted: bool = True, color_tag: str | None = None):
        """
        Add a new completions group.

        All completions added after call to this method will be placed to the new group.
        They will be grouped together, and colored according to the group's color tag.

        :param sorted:
            controls whether completions in the new group
            should be sorted lexicographically.
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
        """
        Number of completions added so far.

        """

        return len(self._completions)

    def split_off_prefix(self, delim: str | None = None, /):
        """
        Move everything up to the last occurrence of ``delim``
        from :attr:`~CompletionCollector.prefix`
        to :attr:`~CompletionCollector.iprefix`.

        :param delim:
            delimiter to split off; :data:`None` value splits off on any whitespace
            character, similar to :meth:`str.rsplit`.

        """

        delim = delim or " "
        parts = self.prefix.rsplit(delim, maxsplit=1)
        if len(parts) > 1:
            self.iprefix += parts[0] + delim
            self.prefix = parts[1]

    def split_off_suffix(self, delim: str | None = None, /):
        """
        Move everything past the first occurrence of ``delim``
        from :attr:`~CompletionCollector.suffix`
        to :attr:`~CompletionCollector.isuffix`.

        :param delim:
            delimiter to split off; :data:`None` value splits off on any whitespace
            character, similar to :meth:`str.split`.

        """

        delim = delim or " "
        parts = self.suffix.split(delim, maxsplit=1)
        if len(parts) > 1:
            self.suffix = parts[0]
            self.isuffix = delim + parts[1] + self.isuffix

    def finalize(self) -> list[Completion]:
        """
        Finish collecting completions and return everything that was collected.

        Do not reuse a collector after it was finalized.

        :returns:
            list of completions, sorted by their groups and preferred ordering
            within each group.

            If all completions start with a common prefix, a single completion
            is returned containing this prefix.

        """

        if len(self._completions) > 1:
            c0 = self._completions[0]

            iprefix = c0.iprefix
            isuffix = c0.isuffix

            if (
                self.full_prefix.startswith(iprefix)
                and self.full_suffix.endswith(isuffix)
                and all(
                    c.iprefix == iprefix and c.isuffix == isuffix
                    for c in self._completions
                )
            ):
                # If all completions have the same `iprefix` and `isuffix`...
                common_prefix = _commonprefix(
                    list(c.completion for c in self._completions)
                )
                if common_prefix and len(iprefix) + len(common_prefix) > len(
                    self.iprefix
                ) + len(self.prefix):
                    # ...and they have a common prefix that is longer than what's entered so far,
                    # then complete this common prefix.
                    rsuffix = ""
                    rsymbols = ""
                    if all(
                        common_prefix == c.completion and rsuffix == c.rsuffix
                        for c in self._completions
                    ):
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
                            dprefix="",
                            dsuffix="",
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
        comment: str | None = None,
        dprefix: str = "",
        dsuffix: str = "",
        color_tag: str | None = None,
    ):
        if not completion or completion in self.dedup_words:
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
            self._add(
                completion,
                comment=comment,
                dprefix=dprefix,
                dsuffix=dsuffix,
                color_tag=color_tag,
            )
        elif corrections <= threshold:
            # this is a correction, add it into corrections group
            if comment:
                comment = "corrected: " + comment
            else:
                comment = "corrected"
            with self.save_state():
                self._group_id = 0xFFFFFFFE  # (big enough) - 1
                self._group_color_tag = "corrected"
                self._add(
                    completion,
                    comment=comment,
                    dprefix=dprefix,
                    dsuffix=dsuffix,
                    color_tag=color_tag,
                )
                self._has_corrections = True

    def finalize(self) -> list[Completion]:
        if self._has_corrections:
            c0 = self._completions[0]

            iprefix = ""
            prefix = self.full_prefix
            suffix = self.full_suffix
            isuffix = ""

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
                self._group_id = 0xFFFFFFFF  # (big enough)
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
                (
                    d[i - 2][j - 2] + (a[i - 1] != b[j - 1])
                    if i > 2 and j > 2 and a[i - 2 : i] == b[j - 1 : j - 3 : -1]
                    else math.inf
                ),
            )

    return d[-1][-1]


def _commonprefix(m: list[str]) -> str:
    if not m:
        return ""
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


class Completer(abc.ABC):
    """
    An interface for text completion providers.

    """

    def complete(
        self, text: str, pos: int, /, *, do_corrections: bool = True
    ) -> list[Completion]:
        """
        Complete the given text at the given cursor position.

        :param text:
            text that is being completed.
        :param pos:
            position of the cursor in the text. ``0`` means the cursor
            is before the first character, ``len(text)`` means the cursor
            is after the last character.
        :param do_corrections:
            if :data:`True` (default), completion system will try to guess
            if there are any misspells in the ``text``, and offer to correct them.
        :returns:
            a sorted list of completions.

            If all completions start with a common prefix, a single completion
            is returned containing this prefix.

        """

        collector = CompletionCollector(text, pos)
        with collector.save_state():
            self._process(collector)
        completions = collector.finalize()
        if completions or not do_corrections:
            return completions

        collector = _CorrectingCollector(text, pos)
        with collector.save_state():
            self._process(collector)
        return collector.finalize()

    @abc.abstractmethod
    def _process(self, collector: CompletionCollector, /):
        """
        Generate completions and add them to the given collector.

        Implementing this class is straight forward, just feed all possible
        completions to the collector. For example, let's implement a completer
        for environment variables:

        .. code-block:: python

            class EnvVarCompleter(Completer):
                def _process(self, collector: CompletionCollector):
                    for var in os.environ.keys():
                        collector.add(var)

        """

        raise NotImplementedError()

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        """
        Internal, do not use.

        """

        return _CompleterSerializer.CustomCompleter(self)


class Empty(Completer):
    """
    An empty completer that returns no values.

    """

    def _process(self, collector: CompletionCollector):
        pass  # nothing to do

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        return _CompleterSerializer.Model()


@dataclass(frozen=True, **yuio._with_slots())
class Option:
    """
    A single completion option for the :class:`Choice` completer.

    """

    completion: str
    """
    This string will replace an element that is being completed.

    """

    comment: str | None = None
    """
    Short comment displayed alongside the completion.

    """


class Choice(Completer):
    """
    Completes input from a predefined list of completions.

    :param choices:
        options to choose completion from.

    """

    def __init__(self, choices: _t.Collection[Option], /):
        self._choices: _t.Collection[Option] = choices

    def _process(self, collector: CompletionCollector, /):
        for choice in self._choices:
            collector.add(choice.completion, comment=choice.comment)

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        if any(option.comment for option in self._choices):
            return _CompleterSerializer.ChoiceWithDesc(
                [(option.completion, option.comment or "") for option in self._choices]
            )
        else:
            return _CompleterSerializer.Choice(
                [option.completion for option in self._choices]
            )


class Alternative(Completer):
    """
    Joins outputs from multiple completers.

    :param completers:
        list of inner completers.

        This is a list of tuples. First tuple element is a description of a completion
        group. It will be displayed when this completer is used in shells
        that support it (namely, ZSH). Second tuple element is the inner completer
        itself.

    """

    def __init__(self, completers: list[tuple[str, Completer]], /):
        self._completers = completers

    def _process(self, collector: CompletionCollector, /):
        for _, completer in self._completers:
            with collector.save_state():
                collector.add_group()
                completer._process(collector)

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        return _CompleterSerializer.Alternative(
            [
                (name, completer._get_completion_model(is_many=is_many))
                for name, completer in self._completers
            ]
        )


class List(Completer):
    """
    Completes a value-separated list of elements.

    :param inner:
        completer for list items.
    :param delimiter:
        a character that separates list items. :data:`None` separates by any whitespace
        character, similar to :meth:`str.split`.
    :param allow_duplicates:
        whether to show completions that already appear in the list.

    """

    def __init__(
        self,
        inner: Completer,
        /,
        *,
        delimiter: str | None = None,
        allow_duplicates: bool = False,
    ):
        self._inner = inner
        if delimiter == "":
            raise ValueError("empty delimiter")
        self._delimiter = delimiter
        self._allow_duplicates = allow_duplicates

    def _process(self, collector: CompletionCollector, /):
        collector.split_off_prefix(self._delimiter)
        collector.split_off_suffix(self._delimiter)
        collector.rsuffix = self._delimiter or " "
        collector.rsymbols += self._delimiter or string.whitespace

        if not self._allow_duplicates:
            dedup_words = set(
                collector.iprefix.split(self._delimiter)
                + collector.isuffix.split(self._delimiter)
            )
            if collector.text in dedup_words:
                dedup_words.remove(collector.text)
            collector.dedup_words = frozenset(dedup_words)
        else:
            collector.dedup_words = frozenset()

        self._inner._process(collector)

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        if is_many:
            return _CompleterSerializer.ListMany(
                self._delimiter or " ", self._inner._get_completion_model()
            )
        else:
            return _CompleterSerializer.List(
                self._delimiter or " ", self._inner._get_completion_model()
            )


class Tuple(Completer):
    """
    Completes a value-separated tuple of elements.

    :param inner:
        completers for each tuple element.
    :param delimiter:
        a character that separates list items. :data:`None` separates by any whitespace
        character, similar to :meth:`str.split`.

    """

    def __init__(self, *inner: Completer, delimiter: str | None = None):
        self._inner = inner
        if delimiter == "":
            raise ValueError("empty delimiter")
        self._delimiter = delimiter

    def _process(self, collector: CompletionCollector, /):
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
        if pos > len(self._inner):
            return
        if pos > 0:
            pos -= 1

        collector.split_off_prefix(self._delimiter)
        collector.split_off_suffix(self._delimiter)
        collector.rsuffix = self._delimiter or " "
        collector.rsymbols += self._delimiter or string.whitespace

        self._inner[pos]._process(collector)

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        if is_many:
            return _CompleterSerializer.TupleMany(
                self._delimiter or " ",
                [inner._get_completion_model() for inner in self._inner],
            )
        else:
            return _CompleterSerializer.Tuple(
                self._delimiter or " ",
                [inner._get_completion_model() for inner in self._inner],
            )


class File(Completer):
    """
    Completes file paths.

    :param extensions:
        allowed file extensions, should include the leading dot.

    """

    def __init__(self, extensions: str | _t.Collection[str] | None = None):
        if isinstance(extensions, str):
            self._extensions = [extensions]
        elif extensions is not None:
            self._extensions = list(extensions)
        else:
            self._extensions = None

    def _process(self, collector: CompletionCollector, /):
        base, name = os.path.split(collector.prefix)
        if base and not base.endswith(os.path.sep):
            base += os.path.sep
        collector.iprefix += base
        collector.prefix = name
        collector.suffix = collector.suffix.split(os.sep, maxsplit=1)[0]
        resolved = pathlib.Path(base).expanduser().resolve()
        rsuffix = collector.rsuffix
        if resolved.is_dir():
            if name.startswith("."):
                collector.rsuffix = ""
                collector.add(os.path.curdir + os.path.sep, color_tag="dir")
                collector.add(os.path.pardir + os.path.sep, color_tag="dir")
            if name.startswith("~"):
                collector.rsuffix = ""
                collector.add("~" + os.path.sep, color_tag="dir")
            try:
                for path in resolved.iterdir():
                    if path.is_dir():
                        if path.is_symlink():
                            color_tag = "symlink"
                            dsuffix = "@"
                        else:
                            color_tag = "dir"
                            dsuffix = ""
                        collector.rsuffix = ""
                        collector.add(
                            path.name + os.sep, color_tag=color_tag, dsuffix=dsuffix
                        )
                    elif self._extensions is None or any(
                        path.name.endswith(ext) for ext in self._extensions
                    ):
                        collector.rsuffix = rsuffix
                        color_tag = None
                        dsuffix = ""
                        if path.is_symlink():
                            color_tag = "symlink"
                            dsuffix = "@"
                        elif path.is_file():
                            if (os.name != "nt" and os.access(path, os.X_OK)) or (
                                os.name == "nt" and path.suffix == ".exe"
                            ):
                                color_tag = "exec"
                                dsuffix = "*"
                            else:
                                color_tag = "file"
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
            except PermissionError:
                return

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        return _CompleterSerializer.File(
            "|".join(extension.lstrip(".") for extension in self._extensions or [])
        )


class Dir(File):
    """
    Completes directories.

    """

    def __init__(self):
        super().__init__([])

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> _CompleterSerializer.Model:
        return _CompleterSerializer.Dir()


class _CompleterSerializer:
    def __init__(
        self,
        add_help: bool,
        add_version: bool,
        add_bug_report: bool,
        path: str = "",
        custom_completers: dict[tuple[str, str], list[Completer]] = {},
    ):
        self._path = path
        self._custom_completers = custom_completers
        self._subcommands: dict[str, tuple[_CompleterSerializer, bool, str]] = {}
        self._positional = 0
        self._flags: list[
            tuple[
                list[str],
                str | None,
                str | tuple[str, ...] | None,
                int | _t.Literal["-", "+", "*", "?"],
                _CompleterSerializer.Model,
            ]
        ] = []
        self._add_help = add_help
        if add_help:
            self._flags.append(
                (
                    ["-h", "--help"],
                    "show help message and exit",
                    None,
                    "-",
                    _CompleterSerializer.Model(),
                )
            )
        self._add_version = add_version
        if add_version:
            self._flags.append(
                (
                    ["-V", "--version"],
                    "show program version and exit",
                    None,
                    "-",
                    _CompleterSerializer.Model(),
                )
            )
        self._add_bug_report = add_bug_report
        if add_bug_report:
            self._flags.append(
                (
                    ["--bug-report"],
                    "show environment data for bug report and exit",
                    None,
                    "-",
                    _CompleterSerializer.Model(),
                )
            )

    def add_argument(self, *args: str, **kwargs):
        if self._add_help and "--help" in args:
            return
        if self._add_version and "--version" in args:
            return
        if self._add_bug_report and "--bug-report" in args:
            return

        help = kwargs.get("help") or ""

        if help == argparse.SUPPRESS:
            return

        help = yuio.string.strip_color_tags(help)

        if all(not arg.startswith("-") for arg in args):
            args = (str(self._positional),)
            self._positional += 1

        action = kwargs.get("action")
        metavar = kwargs.get("metavar") or ""
        nargs = kwargs.get(
            "nargs",
            (
                0
                if action
                in [
                    "store_const",
                    "store_true",
                    "store_false",
                    "append_const",
                    "count",
                    "help",
                    "version",
                ]
                else 1
            ),
        )
        if get_parser := getattr(action, "get_parser", None):
            parser = get_parser()
            completer = parser.completer()
            if completer is None:
                completer = Empty()
            completion_model = completer._get_completion_model(
                is_many=parser.supports_parse_many()
            )
        else:
            completion_model = self.Model()

        self._args = ";".join(args)
        completion_model.collect(self)

        self._flags.append((list(args), help, metavar, nargs, completion_model))

    def add_mutually_exclusive_group(self, *args, **kwargs):
        return self

    def add_argument_group(self, *args, **kwargs):
        return self

    def add_subparsers(self, *args, **kwargs):
        return self

    def add_parser(
        self,
        name: str,
        *,
        aliases: _t.Sequence[str] = (),
        help: str,
        **kwargs,
    ):
        if help != argparse.SUPPRESS:
            help = yuio.string.strip_color_tags(str(help or ""))
        serializer = _CompleterSerializer(
            self._add_help,
            self._add_version,
            self._add_bug_report,
            f"{self._path}/{name}",
            self._custom_completers,
        )
        self._subcommands[name] = (serializer, False, help)
        for alias in aliases:
            self._subcommands[alias] = (serializer, True, help)
        return serializer

    def register_custom_completer(self, completer: Completer) -> str:
        completers = self._custom_completers.setdefault((self._path, self._args), [])
        data = json.dumps([self._path, self._args, len(completers)])
        completers.append(completer)
        return data

    def get_custom_completer(self, data: str) -> Completer | None:
        try:
            path, args, index = json.loads(data)
            return self._custom_completers[(path, args)][index]
        except (json.JSONDecodeError, IndexError, TypeError, ValueError):
            pass
        return None

    def as_parser(self) -> argparse.ArgumentParser:
        # We've implemented all methods that `Config._setup_arg_parser` could call.
        return _t.cast(argparse.ArgumentParser, self)

    _SPECIAL_SYMBOLS = str.maketrans("\r\n\a\b\t", "     ")

    def _dump(self, path: str, result: list[str]):
        if self._subcommands:
            self._flags.append(
                (
                    ["c"],
                    "subcommand",
                    "<cmd>",
                    1,
                    _CompleterSerializer.ChoiceWithDesc(
                        [
                            (name, help)
                            for name, (_, is_alias, help) in self._subcommands.items()
                            if not is_alias and help != argparse.SUPPRESS
                        ]
                    ),
                )
            )

        for opts, desc, meta, nargs, completer in self._flags:
            if not isinstance(meta, tuple):
                meta = (meta,)
            compspec: list[str] = [
                path,
                " ".join(opts),
                desc or "",
                " ".join(
                    re.sub(
                        r"[\\ ]",
                        lambda s: "\\S" if s.group() == " " else "\\L",
                        str(m),
                    )
                    or ""
                    for m in meta
                ),
                str(nargs),
                *completer.dump(),
            ]

            result.append(
                "\t".join(item.translate(self._SPECIAL_SYMBOLS) for item in compspec)
            )

        for subcommand, (serializer, *_) in self._subcommands.items():
            serializer._dump(f"{path}/{subcommand}", result)

    def _collect_nested(self, compspec: list[object]):
        for item in compspec:
            self._collect_nested_item(item)

    def _collect_nested_item(self, item: object):
        if isinstance(item, _CompleterSerializer.Model):
            item.collect(self)
        elif isinstance(item, (list, tuple)):
            for sub_item in item:
                self._collect_nested_item(sub_item)

    @staticmethod
    def _dump_nested(compspec: list[object]) -> list[str]:
        contents = []

        for item in compspec:
            contents.extend(_CompleterSerializer._dump_nested_item(item))

        return contents

    @staticmethod
    def _dump_nested_item(item: object) -> list[str]:
        contents = []

        if isinstance(item, _CompleterSerializer.Model):
            contents.extend(item.dump())
        elif isinstance(item, list):
            contents.append(str(len(item)))
            for sub_item in item:
                contents.extend(_CompleterSerializer._dump_nested_item(sub_item))
        elif isinstance(item, tuple):
            for sub_item in item:
                contents.extend(_CompleterSerializer._dump_nested_item(sub_item))
        else:
            contents.append(str(item))

        return contents

    class ModelBase:
        tag: typing.ClassVar[str] = "-"

        def __init_subclass__(cls, tag: str = "-", **kwargs):
            super().__init_subclass__(**kwargs)
            cls.tag = tag

    @dataclass()
    class Model(ModelBase):
        def collect(self, s: _CompleterSerializer):
            compspec = [getattr(self, field.name) for field in dataclasses.fields(self)]
            s._collect_nested(compspec)

        def dump(self) -> list[str]:
            compspec = [getattr(self, field.name) for field in dataclasses.fields(self)]
            contents = _CompleterSerializer._dump_nested(compspec)
            return [self.tag, str(len(contents)), *contents]

    @dataclass()
    class File(Model, tag="f"):
        ext: str

    @dataclass()
    class Dir(Model, tag="d"):
        pass

    @dataclass()
    class Choice(Model, tag="c"):
        choices: list[str]

        def dump(self) -> list[str]:
            return [self.tag, str(len(self.choices)), *self.choices]

    @dataclass()
    class ChoiceWithDesc(Model, tag="cd"):
        choices: list[tuple[str, str]]

        def dump(self) -> list[str]:
            return [
                self.tag,
                str(len(self.choices) * 2),
                *[c[0] for c in self.choices],
                *[yuio.string.strip_color_tags(c[1]) for c in self.choices],
            ]

    @dataclass()
    class Git(Model, tag="g"):
        class Mode(enum.Enum):
            Branch = "b"
            Remote = "r"
            Tag = "t"
            Head = "h"

        modes: set[Mode] = dataclasses.field(
            default_factory=lambda: {
                _CompleterSerializer.Git.Mode.Branch,
                _CompleterSerializer.Git.Mode.Tag,
                _CompleterSerializer.Git.Mode.Head,
            }
        )

        def dump(self) -> list[str]:
            return [self.tag, "1", "".join(mode.value for mode in self.modes)]

    @dataclass()
    class List(Model, tag="l"):
        delim: str
        inner: _CompleterSerializer.Model

    @dataclass()
    class ListMany(List, tag="lm"):
        pass

    @dataclass()
    class Tuple(Model, tag="t"):
        delim: str
        inner: list[_CompleterSerializer.Model]

    @dataclass()
    class TupleMany(Tuple, tag="tm"):
        pass

    @dataclass()
    class Alternative(Model, tag="a"):
        alternatives: list[tuple[str, _CompleterSerializer.Model]]

    @dataclass()
    class CustomCompleter(Model, tag="cc"):
        completer: Completer

        def collect(self, s: _CompleterSerializer):
            self._data = s.register_custom_completer(self.completer)

        def dump(self) -> list[str]:
            return [
                self.tag,
                "1",
                self._data,
            ]


def _run_custom_completer(s: _CompleterSerializer, data: str, word: str):
    completer = s.get_custom_completer(data)
    if completer is None:
        return
    completions = completer.complete(word, len(word), do_corrections=False)
    for completion in completions:
        print(
            f"{completion.iprefix}{completion.completion}{completion.isuffix}\t{completion.comment or ''}",
            file=sys.__stdout__,
        )


_PROG_ESCAPE = str.maketrans(
    string.punctuation + string.whitespace,
    "_" * (len(string.punctuation) + len(string.whitespace)),
)


def _write_completions(
    s: _CompleterSerializer, prog: str | None = None, shell: str = "all"
):
    import yuio.io

    true_prog = prog or pathlib.Path(sys.argv[0]).stem
    prog = (prog or pathlib.Path(sys.argv[0]).stem).translate(_PROG_ESCAPE)

    if pathlib.Path(sys.argv[0]).stem == "__main__":
        yuio.io.failure(
            "You've invoked this program as a python module, most likely with "
            "`python -m <module>`. For completions to work, the program "
            "must be invoked as a command in your `$PATH`"
        )
        sys.exit(1)
    if not prog:
        yuio.io.failure("Failed to generate completion because program name is empty")
        sys.exit(1)
    if not re.match(r"^[a-zA-Z0-9_-]+$", prog):
        yuio.io.failure(
            "Failed to generate completion due to "
            "forbidden characters in program name: `%r`",
            prog,
        )
        sys.exit(1)

    if shell == "uninstall":
        shell = "all"
        yuio.io.heading("Uninstalling completions for `%s`", true_prog)
        install = False
    else:
        yuio.io.heading("Generating completions for `%s`", true_prog)
        install = True

        if not shutil.which(true_prog):
            yuio.io.warning(
                "Program `%s` is not in your `$PATH`. Completions might not be able "
                "to initialize",
                true_prog,
            )

    if os.name == "nt":
        data_home = cache_home = config_home = pathlib.Path(
            os.environ.get("LOCALAPPDATA") or (pathlib.Path.home() / "AppData/Local")
        )
    else:
        data_home = pathlib.Path(
            os.environ.get("XDG_DATA_HOME") or (pathlib.Path.home() / ".local/share")
        )
        cache_home = pathlib.Path(
            os.environ.get("XDG_CACHE_HOME") or (pathlib.Path.home() / ".cache")
        )
        config_home = pathlib.Path(
            os.environ.get("XDG_CONFIG_HOME") or (pathlib.Path.home() / ".config")
        )

    compdata_path = data_home / f"yuio/{prog}.compdata.tsv"

    if install:
        task_heading = "Installing completions"
    else:
        task_heading = "Uninstalling completions"

    with yuio.io.Task(task_heading) as t:
        if install:
            result = []
            s._dump("", result)
            compdata = "\n".join(result)

            os.makedirs(data_home / "yuio", exist_ok=True)
            compdata_path.write_text(compdata)
            yuio.io.info(
                "Wrote <c note>completion data</c> to <c path>%s</c>", compdata_path
            )
        elif compdata_path.exists():
            os.remove(compdata_path)
            yuio.io.info("Removed <c path>%s</c>", compdata_path)

        if shell in ["all", "bash"]:
            t.comment("Bash")
            _write_bash_script(
                prog,
                true_prog,
                install,
                compdata_path,
                data_home,
                cache_home,
                config_home,
            )
        if shell in ["all", "zsh"]:
            t.comment("Zsh")
            _write_zsh_script(
                prog,
                true_prog,
                install,
                compdata_path,
                data_home,
                cache_home,
                config_home,
            )
        if shell in ["all", "fish"]:
            t.comment("Fish")
            _write_fish_script(
                prog,
                true_prog,
                install,
                compdata_path,
                data_home,
                cache_home,
                config_home,
            )
        if shell in ["all", "pwsh"]:
            t.comment("PowerShell")
            _write_pwsh_script(
                prog,
                true_prog,
                install,
                compdata_path,
                data_home,
                cache_home,
                config_home,
            )

    yuio.io.success("All done! Please restart your shell for changes to take effect.")
    if install:
        yuio.io.info("Run `%s --completions uninstall` to undo all changes.", prog)


def _write_bash_script(
    prog: str,
    true_prog: str,
    install: bool,
    compdata_path: pathlib.Path,
    data_home: pathlib.Path,
    cache_home: pathlib.Path,
    config_home: pathlib.Path,
):
    import yuio.exec
    import yuio.io

    if os.name == "nt":
        yuio.io.warning(
            "Skipped <c note>Bash</c>: completion script doesn't support windows"
        )
        return

    try:
        bash_completions_home = yuio.exec.exec(
            "bash",
            "-lc",
            'echo -n "${BASH_COMPLETION_USER_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion}/completions/"',
        ).splitlines()[-1]
    except (subprocess.CalledProcessError, IndexError):
        bash_completions_home = data_home / "bash-completion/completions/"
    bash_completions_home = pathlib.Path(bash_completions_home)
    script_dest = bash_completions_home / true_prog

    if install:
        _write_script(script_dest, "complete.bash", prog, true_prog, compdata_path)
        yuio.io.info("Wrote <c note>Bash</c> script to <c path>%s</c>", script_dest)
    elif script_dest.exists():
        os.remove(script_dest)
        yuio.io.info("Removed <c path>%s</c>", script_dest)


def _write_zsh_script(
    prog: str,
    true_prog: str,
    install: bool,
    compdata_path: pathlib.Path,
    data_home: pathlib.Path,
    cache_home: pathlib.Path,
    config_home: pathlib.Path,
):
    import yuio.exec
    import yuio.io

    if os.name == "nt":
        yuio.io.warning(
            "Skipped <c note>Zsh</c>: completion script doesn't support windows"
        )
        return

    needs_cache_cleanup = False

    zsh_completions_home = data_home / "zsh/completions"
    script_dest = zsh_completions_home / ("_" + true_prog)

    if install:
        needs_cache_cleanup = True
        _write_script(script_dest, "complete.zsh", prog, true_prog, compdata_path)
        yuio.io.info("Wrote <c note>Zsh</c> script to <c path>%s</c>", script_dest)
    elif script_dest.exists():
        needs_cache_cleanup = True

        os.remove(script_dest)
        yuio.io.info("Removed <c path>%s</c>", script_dest)

    try:
        fpath = (
            yuio.exec.exec(
                "zsh",
                "-lc",
                "echo -n $FPATH",
            )
            .splitlines()[-1]
            .split(":")
        )
    except (subprocess.CalledProcessError, IndexError):
        fpath = []

    try:
        zhome = yuio.exec.exec(
            "zsh",
            "-lc",
            "echo -n ${ZDOTDIR:-$HOME}",
        ).splitlines()[-1]
    except (subprocess.CalledProcessError, IndexError):
        zhome = pathlib.Path.home()

    zhome = pathlib.Path(zhome)
    zprofile_path = zhome / ".zprofile"
    zprofile_append_text = f"\nfpath=({zsh_completions_home} $fpath)\n"

    if install:
        if str(zsh_completions_home) not in fpath:
            with open(zprofile_path, "a") as f:
                f.write(zprofile_append_text)
            yuio.io.info(
                "<c note>Note:</c> modified <c path>%s</c> to add <c path>%s</c> to `fpath`",
                zprofile_path,
                zsh_completions_home,
            )
    elif zprofile_path.exists():
        zprofile_text = zprofile_path.read_text()
        if zprofile_append_text in zprofile_text:
            yuio.io.info(
                "<c note>Note:</c> modifications to <c path>%s</c> are not removed"
                " because other completions might rely on them",
                zprofile_path,
            )

    if not needs_cache_cleanup:
        return

    # Try to remove completions cache from the most common places.
    for zcomp_basedir in [zhome, cache_home / "prezto"]:
        if not zcomp_basedir.exists() or not zcomp_basedir.is_dir():
            continue
        for file in zcomp_basedir.iterdir():
            if file.is_file() and re.match(r"^\.?zcompdump", file.name):
                os.remove(file)
                yuio.io.info(
                    "<c note>Note:</c> deleted Zsh completions cache at <c path>%s</c>",
                    file,
                )

    try:
        # Run zsh with the right flags in case zshrc runs compinit.
        # If after generating completions user runs `zsh` without the `-l` flag,
        # our changes to fpath will not be visible, and compinit will dump
        # an invalid version of cache. To avoid this, we call zsh ourselves
        # before the user has a chance to do it. Notice, though, that we don't
        # run `compdump`. This is because we can't be sure that the user uses
        # the default cache path (~/.zcompdump).
        yuio.exec.exec("zsh", "-lc", "true")
    except subprocess.CalledProcessError:
        pass


def _write_fish_script(
    prog: str,
    true_prog: str,
    install: bool,
    compdata_path: pathlib.Path,
    data_home: pathlib.Path,
    cache_home: pathlib.Path,
    config_home: pathlib.Path,
):
    import yuio.io

    if os.name == "nt":
        yuio.io.warning(
            "Skipped <c note>Fish</c>: completion script doesn't support windows"
        )
        return

    fish_completions_home = data_home / "fish/vendor_completions.d"
    script_dest = fish_completions_home / (true_prog + ".fish")

    if install:
        _write_script(script_dest, "complete.fish", prog, true_prog, compdata_path)
        yuio.io.info("Wrote <c note>Fish</c> script to <c path>%s</c>", script_dest)
    elif script_dest.exists():
        os.remove(script_dest)
        yuio.io.info("Removed <c path>%s</c>", script_dest)


def _write_pwsh_script(
    prog: str,
    true_prog: str,
    install: bool,
    compdata_path: pathlib.Path,
    data_home: pathlib.Path,
    cache_home: pathlib.Path,
    config_home: pathlib.Path,
):
    import yuio.exec
    import yuio.io

    if shutil.which("pwsh"):
        command = "pwsh"
    elif shutil.which("powershell"):
        command = "powershell"
    else:
        yuio.io.warning(
            "Skipped <c note>PowerShell</c>: `pwsh` command is not available"
        )
        return

    try:
        pwsh_data = (
            yuio.exec.exec(
                command,
                "-Command",
                'Write-Host "$($PSVersionTable.PSVersion);$PROFILE"',
            )
            .splitlines()[-1]
            .strip()
        )
    except (subprocess.CalledProcessError, IndexError) as e:
        yuio.io.warning(
            "Skipped <c note>PowerShell</c>: failed to get powershell `$PROFILE` path: %s",
            e,
        )
        return
    except FileNotFoundError:
        yuio.io.warning("Skipped <c note>PowerShell</c>: `pwsh` command not found")
        return
    if match := re.match(r"^(\d+(?:\.\d+)*);(.*)$", pwsh_data):
        version = match.group(1)
        profile_s = match.group(2)
    else:
        yuio.io.warning(
            "Skipped <c note>PowerShell</c>: can't determine powershell version"
        )
        return
    if not profile_s:
        yuio.io.warning(
            "Skipped <c note>PowerShell</c>: powershell `$PROFILE` path is empty"
        )
        return
    if tuple(int(v) for v in version.split(".")) < (5, 0, 0):
        yuio.io.warning(
            "Skipped <c note>PowerShell</c>: completions script requires "
            "PowerShell 5 or newer, you have %s",
            version,
        )
        return

    profile_path = pathlib.Path(profile_s).expanduser().resolve()
    profile_path.parent.mkdir(exist_ok=True, parents=True)

    data_dir = data_home / "yuio/pwsh"
    loader_path = data_dir / "LoadCompletions.ps1"
    script_dest = data_dir / f"_{true_prog}.ps1"
    if install:
        _write_script(script_dest, "complete.ps1", prog, true_prog, compdata_path)
        yuio.io.info(
            "Wrote <c note>PowerShell</c> script to <c path>%s</c>", script_dest
        )
        _write_pwsh_loader(loader_path, data_dir)
    elif script_dest.exists():
        os.remove(script_dest)
        yuio.io.info("Removed <c path>%s</c>", script_dest)

    try:
        data_dirs = [
            pathlib.Path(f).expanduser().resolve()
            for f in yuio.exec.exec(
                command,
                "-Command",
                'Write-Host ($_YUIO_COMPL_V1_INIT_PATHS -join "`n")',
            )
            .strip()
            .splitlines()
        ]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return

    pwsh_profile_append_text = f"\n. {loader_path}\n"

    if install:
        if data_dir not in data_dirs:
            with open(profile_path, "a") as f:
                f.write(pwsh_profile_append_text)
            yuio.io.info(
                "<c note>Note:</c> modified <c path>%s</c> to call <c path>%s</c> on startup",
                profile_path,
                loader_path,
            )
    elif profile_path.exists():
        pwsh_profile_text = profile_path.read_text()
        if pwsh_profile_append_text in pwsh_profile_text:
            yuio.io.info(
                "<c note>Note:</c> modifications to <c path>%s</c> are not removed"
                " because other completions might rely on them",
                profile_path,
            )


def _write_script(
    path: pathlib.Path,
    script_name: str,
    prog: str,
    true_prog: str,
    compdata_path: pathlib.Path,
):
    script_template = _read_script(script_name)
    script = (
        (script_template)
        .replace("@prog@", prog)
        .replace("@true_prog@", true_prog)
        .replace("@data@", str(compdata_path))
        .replace("@version@", yuio.__version__)
    )

    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_text(script)


def _read_script(script_name: str):
    import zipfile
    import zipimport

    if isinstance(__loader__, zipimport.zipimporter):
        # Yuio is imported directly from a wheel.
        with zipfile.ZipFile(__loader__.archive) as archive:
            script_template = archive.read("yuio/_complete/" + script_name)
            return script_template.decode()
    else:
        script_template_path = pathlib.Path(__file__).parent / "_complete" / script_name
        return script_template_path.read_text()


def _write_pwsh_loader(loader_path: pathlib.Path, data_dir: pathlib.Path):
    import yuio.io

    loader_template_path = pathlib.Path(__file__).parent / "_complete/complete_init.ps1"
    loader_template = loader_template_path.read_text()

    loader_version = re.search(
        r"^\s*#\s*LOADER_VERSION:\s*(\d+)\s*$", loader_template, re.MULTILINE
    )
    assert loader_version

    if loader_path.exists() and loader_path.is_file():
        current_loader = loader_path.read_text()
        current_version_s = re.search(
            r"^\s*#\s*LOADER_VERSION:\s*(\d+)\s*$", current_loader, re.MULTILINE
        )

        if current_version_s is None:
            yuio.io.warning(
                "<c note>Note:</c> can't determine version of <c path>%s</c>, "
                "file will be overridden",
                loader_path,
            )
        elif int(loader_version.group(1)) <= int(current_version_s.group(1)):
            return

    loader_template = loader_template.replace("@data@", str(data_dir))
    loader_path.write_text(loader_template)
    yuio.io.info("Wrote <c note>PowerShell</c> script to <c path>%s</c>", loader_path)
