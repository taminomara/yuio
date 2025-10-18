# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides basic functionality to interact with git.
It comes in handy when writing deployment scripts.


Interacting with a repository
-----------------------------

All repository interactions are done through the :class:`Repo` class
and its methods. If an interaction fails, a :class:`GitException` is raised.

.. autoclass:: Repo
   :members:

.. autoclass:: GitException


Commit and status objects
-------------------------

Some of :class:`Repo` commands return parsed descriptions of git objects:

.. autoclass:: Commit
   :members:

.. autoclass:: CommitTrailers
   :members:

.. autoclass:: Status
   :members:

.. autoclass:: FileStatus
   :members:

.. autoclass:: Modification
   :members:


Parsing git refs
----------------

When you need to query a git ref from a user, :class:`RefParser` will check
that the given ref is formatted correctly. Use :class:`Ref` in your type hints
to help Yuio detect that you want to parse it as a git reference:

.. autoclass:: Ref

.. autoclass:: Tag

.. autoclass:: Branch

.. autoclass:: Remote

.. autoclass:: RefParser

.. autoclass:: TagParser

.. autoclass:: BranchParser

.. autoclass:: RemoteParser

If you know path to your repository before hand, and want to make sure that the user
supplies a valid ref that points to an existing git object, use :class:`CommitParser`:

.. autoclass:: CommitParser


Autocompleting git refs
-----------------------

.. autoclass:: RefCompleter

.. autoclass:: RefCompleterMode
    :members:

"""

from __future__ import annotations

import dataclasses
import enum
import functools
import logging
import pathlib
import re
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import datetime

import yuio.complete
import yuio.parse
from yuio import _typing as _t

_logger = logging.getLogger(__name__)


class GitException(subprocess.SubprocessError):
    """Raised when git returns a non-zero exit code."""


#: A special kind of string that contains a git object reference.
#:
#: Ref is not guaranteed to be valid; this type is used in type hints
#: to make use of the :class:`RefParser`.
Ref = _t.NewType("Ref", str)

#: A special kind of string that contains a tag name.
#:
#: Ref is not guaranteed to be valid; this type is used in type hints
#: to make use of the :class:`TagParser`.
Tag = _t.NewType("Tag", str)

#: A special kind of string that contains a branch name.
#:
#: Ref is not guaranteed to be valid; this type is used in type hints
#: to make use of the :class:`BranchParser`.
Branch = _t.NewType("Branch", str)

#: A special kind of string that contains a remote branch name.
#:
#: Ref is not guaranteed to be valid; this type is used in type hints
#: to make use of the :class:`RemoteParser`.
Remote = _t.NewType("Remote", str)


_LOG_FMT = "%H%n%aN%n%aE%n%aI%n%cN%n%cE%n%cI%n%(decorate:prefix=,suffix=,tag=,separator= )%n%w(0,0,1)%B%w(0,0)%n-"
_LOG_TRAILERS_FMT = "%H%n%w(0,1,1)%(trailers:only=true)%w(0,0)%n-"
_LOG_TRAILER_KEY_RE = re.compile(r"^(?P<key>\S+):\s")


class Repo:
    """
    A class that allows interactions with a git repository.

    :param path:
        path to the repo root dir.
    :param skip_checks:
        don't check if we're inside a repo.

    """

    def __init__(self, path: pathlib.Path | str, /, skip_checks: bool = False):
        self.__path = pathlib.Path(path)

        try:
            self.git("--version")
        except FileNotFoundError:
            raise GitException(f"git executable was not found")

        if skip_checks:
            return

        try:
            self.git("rev-parse", "--is-inside-work-tree")
        except GitException:
            raise GitException(f"{path} is not a git repository")

    @property
    def path(self) -> pathlib.Path:
        """
        Path to the repo, as was passed to the constructor.

        """

        return self.__path

    def git(self, *args: str) -> bytes:
        """
        Call git and return its stdout.

        """

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("git %s", " ".join(args))

        res = subprocess.run(
            ["git"] + list(args),
            capture_output=True,
            cwd=self.__path,
        )

        if res.stderr:
            _logger.debug("%s", res.stderr.decode())

        if res.returncode != 0:
            raise GitException(
                f"git exited with status code {res.returncode}:\n"
                f"{res.stderr.decode()}"
            )

        return res.stdout

    def root(self) -> pathlib.Path:
        """
        Get the root directory of the repo.

        """

        return pathlib.Path(self.git("rev-parse", "--show-toplevel").decode())

    def git_dir(self) -> pathlib.Path:
        """
        Get path to the ``.git`` directory of the repo.

        """

        return pathlib.Path(self.git("rev-parse", "--git-dir").decode())

    def status(self) -> Status:
        """
        Query the current repository status.

        """

        text = self.git("status", "--porcelain=v2", "--branch", "-z")
        lines = iter(text.split(b"\0"))

        status = Status(commit="")

        for line_b in lines:
            line = line_b.decode()
            if line.startswith("# branch.oid"):
                status.commit = line[13:]
            elif line.startswith("# branch.head"):
                if line[14:] != "(detached)":
                    status.branch = line[14:]
            elif line.startswith("# branch.upstream"):
                status.upstream = line[18:]
            elif line.startswith("# branch.ab"):
                match = re.match(r"^\+(\d+) -(\d+)$", line[12:])
                assert match is not None
                status.ahead = int(match.group(1))
                status.behind = int(match.group(2))
            elif line.startswith("1"):
                match = re.match(r"^(.)(.) .{4} (?:[^ ]+ ){5}(.*)$", line[2:])
                assert match is not None
                file_status = FileStatus(
                    path=pathlib.Path(match.group(3)),
                    staged=Modification(match.group(1)),
                    tree=Modification(match.group(2)),
                )
                status.changes.append(file_status)
                status.has_tracked_changes |= (
                    file_status.staged is not Modification.UNTRACKED
                )
                status.has_untracked_changes |= (
                    file_status.staged is Modification.UNTRACKED
                )
            elif line.startswith("2"):
                match = re.match(r"^(.)(.) .{4} (?:[^ ]+ ){6}(.*)$", line[2:])
                assert match is not None
                file_status = FileStatus(
                    path=pathlib.Path(match.group(3)),
                    path_from=pathlib.Path(next(lines).decode()),
                    staged=Modification(match.group(1)),
                    tree=Modification(match.group(2)),
                )
                status.changes.append(file_status)
                status.has_tracked_changes |= (
                    file_status.staged is not Modification.UNTRACKED
                )
                status.has_untracked_changes |= (
                    file_status.staged is Modification.UNTRACKED
                )

        return status

    def log(self, *refs: str, max_entries: int | None = None) -> list[Commit]:
        """
        Query the log for given git objects.

        """

        args = [
            f"--pretty=format:{_LOG_FMT}",
            "--decorate-refs=refs/tags",
            "--decorate=short",
        ]

        if max_entries is not None:
            args += ["-n", str(max_entries)]

        args += list(refs)

        text = self.git("log", *args)
        lines = iter(text.decode().split("\n"))

        commits = []

        while commit := self.__parse_single_log_entry(lines):
            commits.append(commit)

        return commits

    def trailers(
        self, *refs: str, max_entries: int | None = None
    ) -> list[CommitTrailers]:
        """
        Query trailer lines for given git objects.

        Trailers are lines at the end of a commit message formatted as ``key: value``
        pairs. See `git-interpret-trailers`__ for further description.

        __ https://git-scm.com/docs/git-interpret-trailers

        """

        args = [f"--pretty=format:{_LOG_TRAILERS_FMT}"]

        if max_entries is not None:
            args += ["-n", str(max_entries)]

        args += list(refs)

        text = self.git("log", *args)
        lines = iter(text.decode().split("\n"))

        trailers = []

        while commit := self.__parse_single_trailer_entry(lines):
            trailers.append(commit)

        return trailers

    def show(self, ref: str, /) -> Commit | None:
        """
        Query information for the given git object.

        Return `None` if object is not found.

        """

        try:
            self.git("rev-parse", "--verify", ref)
        except GitException:
            return None

        text = self.git(
            "log",
            f"--pretty=format:{_LOG_FMT}",
            "-n1",
            ref,
        )

        lines = iter(text.decode().split("\n"))

        commit = self.__parse_single_log_entry(lines)

        if commit is None:
            return None

        commit.orig_ref = ref

        return commit

    @staticmethod
    def __parse_single_log_entry(lines) -> Commit | None:
        try:
            commit = next(lines)
            author = next(lines)
            author_email = next(lines)
            author_datetime = datetime.fromisoformat(next(lines))
            committer = next(lines)
            committer_email = next(lines)
            committer_datetime = datetime.fromisoformat(next(lines))
            tags = next(lines).split()
            title = next(lines)
            body = ""

            while True:
                line = next(lines)
                if not line or line.startswith(" "):
                    body += line[1:] + "\n"
                else:
                    break

            body = body.strip("\n")
            if body:
                body += "\n"

            return Commit(
                commit,
                tags,
                author,
                author_email,
                author_datetime,
                committer,
                committer_email,
                committer_datetime,
                title,
                body,
            )
        except StopIteration:
            return None

    @staticmethod
    def __parse_single_trailer_entry(
        lines,
    ) -> CommitTrailers | None:
        try:
            commit = next(lines)
            trailers = []
            current_key = None
            current_value = ""

            while True:
                line = next(lines)
                if not line or line.startswith(" "):
                    line = line[1:] + "\n"
                    if match := _LOG_TRAILER_KEY_RE.match(line):
                        if current_key:
                            first, *rest = current_value.splitlines(keepends=True)
                            current_value = (
                                first.strip() + "\n" + textwrap.dedent("".join(rest))
                            ).rstrip() + "\n"
                            trailers.append((current_key, current_value))
                        current_key = match.group("key")
                        current_value = line[match.end() :]
                    else:
                        current_value += line
                else:
                    break
            if current_key:
                first, *rest = current_value.splitlines(keepends=True)
                current_value = (
                    first.strip() + "\n" + textwrap.dedent("".join(rest))
                ).rstrip() + "\n"
                trailers.append((current_key, current_value))

            return CommitTrailers(commit, trailers)
        except StopIteration:
            return None

    def tags(self) -> list[str]:
        """
        List all tags in this repository.

        """

        return (
            self.git("for-each-ref", "--format=%(refname:short)", "refs/tags")
            .decode()
            .splitlines()
        )

    def branches(self) -> list[str]:
        """
        List all branches in this repository.

        """

        return (
            self.git("for-each-ref", "--format=%(refname:short)", "refs/heads")
            .decode()
            .splitlines()
        )

    def remotes(self) -> list[str]:
        """
        List all remote branches in this repository.

        """

        return (
            self.git("for-each-ref", "--format=%(refname:short)", "refs/remotes")
            .decode()
            .splitlines()
        )


@dataclass
class Commit:
    """
    Commit description.

    """

    #: Commit hash.
    hash: str

    #: Tags attached to this commit.
    tags: list[str]

    #: Author name.
    author: str

    #: Author email.
    author_email: str

    #: Author time.
    author_datetime: datetime

    #: Committer name.
    committer: str

    #: Committer email.
    committer_email: str

    #: Committer time.
    committer_datetime: datetime

    #: Commit title, i.e. first line of the message.
    title: str

    #: Commit body, i.e. the rest of the message.
    body: str

    #: If commit was parsed from a user input, this field will contain
    #: original input. I.e. if a user enters ``HEAD`` and it gets resolved
    #: into a commit, `orig_ref` will contain string ``"HEAD"``.
    #:
    #: See also :class:`CommitParser`.
    orig_ref: str | None = None

    @property
    def short_hash(self):
        """
        First seven characters of the commit hash.

        """

        return self.hash[:7]

    def __str__(self):
        if self.orig_ref:
            return self.orig_ref
        else:
            return self.short_hash


@dataclass
class CommitTrailers:
    """
    Commit trailers.

    """

    #: Commit hash.
    hash: str

    #: Key-value pairs for commit trailers.
    trailers: list[tuple[str, str]]


class Modification(enum.Enum):
    """For changed file, what modification was applied to it."""

    #: File wasn't changed.
    UNMODIFIED = "."

    #: File was changed.
    MODIFIED = "M"

    #: File was created.
    ADDED = "A"

    #: File was deleted.
    DELETED = "D"

    #: File was renamed (and possibly changed).
    RENAMED = "R"

    #: File was copied (and possibly changed).
    COPIED = "C"

    #: File with conflicts is unmerged.
    UNMERGED = "U"

    #: File is in ``.gitignore``.
    IGNORED = "?"

    #: File was created but not yet added to git, i.e. not staged.
    UNTRACKED = "!"


@dataclass
class FileStatus:
    """Status of a changed file."""

    #: Path of the file.
    path: pathlib.Path

    #: If file was moved, contains path where it was moved from.
    path_from: pathlib.Path | None = None

    #: File modification in the index (staged).
    staged: Modification = Modification.UNMODIFIED

    #: File modification in the tree (unstaged).
    tree: Modification = Modification.UNMODIFIED


@dataclass
class Status:
    """Status of a working copy."""

    #: Current commit hash.
    commit: str

    #: Name of the current branch.
    branch: str | None = None

    #: Name of the upstream branch.
    upstream: str | None = None

    #: Number of commits the branch is ahead of upstream.
    ahead: int | None = None

    #: Number of commits the branch is behind of upstream.
    behind: int | None = None

    #: True if any tracked file was changed.
    has_tracked_changes: bool = False

    #: True if any file was added but not tracked.
    has_untracked_changes: bool = False

    #: List of changed files, both tracked and untracked.
    changes: list[FileStatus] = dataclasses.field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """True if there are any changes in the repository."""

        return self.has_tracked_changes or self.has_untracked_changes


class RefCompleterMode(enum.Enum):
    """
    Specifies operation modes for :class:`RefCompleter`.

    """

    #: Completes branches.
    Branch = "b"

    #: Completes remote branches.
    Remote = "r"

    #: Completes tags.
    Tag = "t"

    #: Completes ``HEAD`` and ``ORIG_HEAD``.
    Head = "h"


class RefCompleter(yuio.complete.Completer):
    """
    Completes git refs.

    :param repo:
        source of completions.
    :param modes:
        which objects to complete.

    """

    def __init__(self, repo: Repo, modes: set[RefCompleterMode] | None = None):
        super().__init__()

        self._repo = repo
        self._modes = modes or {
            RefCompleterMode.Branch,
            RefCompleterMode.Tag,
            RefCompleterMode.Head,
        }

    def _process(self, collector: yuio.complete.CompletionCollector, /):
        try:
            if RefCompleterMode.Head in self._modes:
                collector.add_group()
                git_dir = self._repo.git_dir()
                for head in ["HEAD", "ORIG_HEAD"]:
                    if (git_dir / head).exists():
                        collector.add(head)
            if RefCompleterMode.Branch in self._modes:
                collector.add_group()
                for branch in self._repo.branches():
                    collector.add(branch, comment="branch")
            if RefCompleterMode.Remote in self._modes:
                collector.add_group()
                for remote in self._repo.remotes():
                    collector.add(remote, comment="remote")
            if RefCompleterMode.Tag in self._modes:
                collector.add_group()
                for tag in self._repo.tags():
                    collector.add(tag, comment="tag")
        except GitException:
            pass

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> yuio.complete._CompleterSerializer.Model:
        return yuio.complete._CompleterSerializer.Git(
            {
                yuio.complete._CompleterSerializer.Git.Mode(mode.value)
                for mode in self._modes
            }
        )


def CommitParser(*, repo: Repo) -> yuio.parse.Parser[Commit]:
    """
    A parser for git refs (commits, tags, branches, and so on).

    This parser validates that the given ref exists in the given repository,
    parses it and returns a commit data associated with this ref.

    If you need a simple string without additional validation,
    use :class:`RefParser`.

    """

    def map(value: str, /) -> Commit:
        commit = repo.show(value)
        if commit is None:
            raise yuio.parse.ParsingError("invalid git ref")
        return commit

    def rev(value: Commit | object) -> str:
        if isinstance(value, Commit):
            return str(value)
        elif isinstance(value, str):
            return value
        else:
            raise TypeError(
                f"parser Commit can't handle value "
                f"of type {_t.type_repr(type(value))}"
            )

    return yuio.parse.Map(yuio.parse.Str(), map, rev)


T = _t.TypeVar("T")


class _RefParserImpl(yuio.parse.ValidatingParser[T], _t.Generic[T]):
    if _t.TYPE_CHECKING:

        def __new__(
            cls,
            /,
            *,
            repo_path: Repo | str | pathlib.Path | None = None,
            should_exist: bool = False,
        ) -> _RefParserImpl[T]: ...

    def __init__(
        self,
        /,
        *,
        repo_path: Repo | str | pathlib.Path | None = None,
        should_exist: bool = False,
    ):
        super().__init__(_t.cast(yuio.parse.Parser[T], yuio.parse.Str()))

        if repo_path is None:
            repo_path = pathlib.Path.cwd()
        elif isinstance(repo_path, Repo):
            repo_path = repo_path.path
        else:
            repo_path = pathlib.Path(repo_path)

        self._repo_path = repo_path
        self._should_exist = should_exist

    @functools.cached_property
    def _repo(self) -> Repo:
        try:
            return Repo(self._repo_path, skip_checks=not self._should_exist)
        except GitException as e:
            raise yuio.parse.ParsingError(str(e)) from None

    def _validate(self, value: T, /):
        if self._should_exist and self._repo.show(str(value)) is None:
            raise yuio.parse.ParsingError(
                f"{value} does not exist in {self._repo_path}"
            )

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo)


class RefParser(_RefParserImpl[Ref]):
    """
    A parser that provides autocompletion for git refs, but doesn't verify
    anything else.

    """


class TagParser(_RefParserImpl[Tag]):
    """
    A parser that checks if the given string is a valid tag name.

    """

    def _validate(self, value: Tag, /):
        try:
            self._repo.git("check-ref-format", f"refs/tags/{value}")
        except GitException:
            raise yuio.parse.ParsingError(f"{value} is not a valid tag name") from None

        super()._validate(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo, {RefCompleterMode.Tag})


class BranchParser(_RefParserImpl[Branch]):
    """
    A parser that checks if the given string is a valid tag name.

    """

    def _validate(self, value: Branch, /):
        try:
            self._repo.git("check-ref-format", f"refs/heads/{value}")
        except GitException:
            raise yuio.parse.ParsingError(
                f"{value} is not a valid branch name"
            ) from None

        super()._validate(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo, {RefCompleterMode.Branch})


class RemoteParser(_RefParserImpl[Remote]):
    """
    A parser that checks if the given string is a valid tag remote branch.

    """

    def _validate(self, value: Remote, /):
        try:
            self._repo.git("check-ref-format", f"refs/remotes/{value}")
        except GitException:
            raise yuio.parse.ParsingError(
                f"{value} is not a valid branch name"
            ) from None

        super()._validate(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo, {RefCompleterMode.Branch})


yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: yuio.parse._str_ty_union_parser(
        ty, origin, args, Ref, RefParser
    )
)

yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: yuio.parse._str_ty_union_parser(
        ty, origin, args, Tag, TagParser
    )
)

yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: yuio.parse._str_ty_union_parser(
        ty, origin, args, Branch, BranchParser
    )
)

yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: yuio.parse._str_ty_union_parser(
        ty, origin, args, Remote, RemoteParser
    )
)
