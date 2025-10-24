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
and its methods. If an interaction fails, a :class:`GitError` is raised.

.. autoclass:: Repo
    :members:

.. autoclass:: GitError


Status objects
--------------

:meth:`Repo.status` returns repository status parsed from ``git status`` command.
It can show changed and unmerged files and submodules. See details about change
representation in `git status`__ manual.

__ https://git-scm.com/docs/git-status#_output

Yuio represents ``git status`` output as close to the original as possible,
but makes some convenience renames. This results in somewhat unexpected
class structure:

.. raw:: html

    <p>
    <pre class="mermaid">
    ---
    config:
        class:
            hideEmptyMembersBox: true
    ---
    classDiagram

    class PathStatus
    click PathStatus href "#yuio.git.PathStatus" "yuio.git.PathStatus"

    class FileStatus
    click FileStatus href "#yuio.git.FileStatus" "yuio.git.FileStatus"
    PathStatus <|-- FileStatus

    class SubmoduleStatus
    click SubmoduleStatus href "#yuio.git.SubmoduleStatus" "yuio.git.SubmoduleStatus"
    FileStatus <|-- SubmoduleStatus

    class UnmergedFileStatus
    click UnmergedFileStatus href "#yuio.git.UnmergedFileStatus" "yuio.git.UnmergedFileStatus"
    PathStatus <|-- UnmergedFileStatus

    class UnmergedSubmoduleStatus
    click UnmergedSubmoduleStatus href "#yuio.git.UnmergedSubmoduleStatus" "yuio.git.UnmergedSubmoduleStatus"
    UnmergedFileStatus <|-- UnmergedSubmoduleStatus
    </pre>
    </p>

.. autoclass:: Status
    :members:

.. autoclass:: PathStatus
    :members:

.. autoclass:: FileStatus
    :members:

.. autoclass:: SubmoduleStatus
    :members:

.. autoclass:: UnmergedFileStatus
    :members:

.. autoclass:: UnmergedSubmoduleStatus
    :members:

.. autoclass:: Modification
    :members:


Commit objects
--------------

.. autoclass:: Commit
    :members:

.. autoclass:: CommitTrailers
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

import contextlib
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

__all__ = [
    "GitError",
    "Ref",
    "Tag",
    "Branch",
    "Remote",
    "Repo",
    "Commit",
    "CommitTrailers",
    "Modification",
    "PathStatus",
    "FileStatus",
    "SubmoduleStatus",
    "UnmergedFileStatus",
    "UnmergedSubmoduleStatus",
    "Status",
    "RefCompleterMode",
    "RefCompleter",
    "RefParser",
    "TagParser",
    "BranchParser",
    "RemoteParser",
    "CommitParser",
]

_logger = logging.getLogger(__name__)


class GitError(subprocess.SubprocessError):
    """
    Raised when git returns a non-zero exit code.

    """


Ref = _t.NewType("Ref", str)
"""
A special kind of string that contains a git object reference.

Ref is not guaranteed to be valid; this type is used in type hints
to make use of the :class:`RefParser`.

"""

Tag = _t.NewType("Tag", str)
"""
A special kind of string that contains a tag name.

Ref is not guaranteed to be valid; this type is used in type hints
to make use of the :class:`TagParser`.

"""

Branch = _t.NewType("Branch", str)
"""
A special kind of string that contains a branch name.

Ref is not guaranteed to be valid; this type is used in type hints
to make use of the :class:`BranchParser`.

"""

Remote = _t.NewType("Remote", str)
"""
A special kind of string that contains a remote branch name.

Ref is not guaranteed to be valid; this type is used in type hints
to make use of the :class:`RemoteParser`.

"""


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
    :param env:
        environment variables for the git executable.

    """

    def __init__(
        self,
        path: pathlib.Path | str,
        /,
        skip_checks: bool = False,
        env: dict[str, str] | None = None,
    ):
        self.__path = pathlib.Path(path)
        self.__env = env

        if skip_checks:
            return

        try:
            self.git("--version")
        except FileNotFoundError:
            raise GitError(f"git executable not found")

        try:
            self.git("rev-parse", "--is-inside-work-tree")
        except GitError:
            raise GitError(f"{path} is not a git repository")

    @property
    def path(self) -> pathlib.Path:
        """
        Path to the repo, as was passed to the constructor.

        """

        return self.__path

    def git(self, *args: str | pathlib.Path, capture_output: bool = True) -> bytes:
        """
        Call git and return its stdout.

        """

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("git %s", " ".join(map(str, args)))

        with contextlib.ExitStack() as context:
            if not capture_output:
                import yuio.io

                context.enter_context(yuio.io.SuspendOutput())
            try:
                res = subprocess.run(
                    ["git"] + list(args),
                    capture_output=capture_output,
                    cwd=self.__path,
                    env=self.__env,
                )
            except FileNotFoundError:
                raise GitError(f"git executable not found")

        if res.stderr:
            _logger.debug("%s", res.stderr.decode())

        if res.returncode != 0:
            raise GitError(
                f"git exited with status code {res.returncode}:\n"
                f"{res.stderr.decode()}"
            )

        return res.stdout

    @functools.cached_property
    def root(self) -> pathlib.Path:
        """
        The root directory of the repo.

        """

        return pathlib.Path(
            self.git("rev-parse", "--path-format=absolute", "--show-toplevel")
            .decode()
            .strip()
        )

    @functools.cached_property
    def git_dir(self) -> pathlib.Path:
        """
        Get path to the ``.git`` directory of the repo.

        """

        return pathlib.Path(
            self.git("rev-parse", "--path-format=absolute", "--git-dir")
            .decode()
            .strip()
        )

    def status(
        self, /, include_ignored: bool = False, include_submodules: bool = True
    ) -> Status:
        """
        Query the current repository status.

        :param include_ignored:
            include ignored status in the list of changes. Disable by default.

        :param include_submodules:
            include status of submodules in the list of changes. Enabled by default.

        """

        text = self.git(
            "status",
            "--porcelain=v2",
            "-z",
            "--ahead-behind",
            "--branch",
            "--renames",
            "--untracked-files=normal",
            "--ignore-submodules=" + ("none" if include_submodules else "all"),
            "--ignored=" + ("matching" if include_ignored else "no"),
        )
        lines = iter(text.split(b"\0"))

        status = Status(commit=None)

        for line_b in lines:
            line = line_b.decode()
            if line.startswith("# branch.oid"):
                if line[13:] != "(initial)":
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
                match = re.match(
                    r"^(?P<X>.)(?P<Y>.) (?P<sub>.{4}) (?:[^ ]+ ){5}(?P<path>.*)$",
                    line[2:],
                )
                assert match is not None
                sub = match.group("sub")
                if sub[0] == "S":
                    path_status = SubmoduleStatus(
                        path=pathlib.Path(match.group("path")),
                        path_from=None,
                        staged=Modification(match.group("X")),
                        tree=Modification(match.group("Y")),
                        commit_changed=sub[1] != ".",
                        has_tracked_changes=sub[2] != ".",
                        has_untracked_changes=sub[3] != ".",
                    )
                else:
                    path_status = FileStatus(
                        path=pathlib.Path(match.group("path")),
                        path_from=None,
                        staged=Modification(match.group("X")),
                        tree=Modification(match.group("Y")),
                    )
                status.changes.append(path_status)
            elif line.startswith("2"):
                match = re.match(
                    r"^(?P<X>.)(?P<Y>.) (?P<sub>.{4}) (?:[^ ]+ ){6}(?P<path>.*)$",
                    line[2:],
                )
                assert match is not None
                path_from = pathlib.Path(next(lines).decode())
                sub = match.group("sub")
                if sub[0] == "S":
                    path_status = SubmoduleStatus(
                        path=pathlib.Path(match.group("path")),
                        path_from=path_from,
                        staged=Modification(match.group("X")),
                        tree=Modification(match.group("Y")),
                        commit_changed=sub[1] != ".",
                        has_tracked_changes=sub[2] != ".",
                        has_untracked_changes=sub[3] != ".",
                    )
                else:
                    path_status = FileStatus(
                        path=pathlib.Path(match.group("path")),
                        path_from=path_from,
                        staged=Modification(match.group("X")),
                        tree=Modification(match.group("Y")),
                    )
                status.changes.append(path_status)
            elif line.startswith("u"):
                match = re.match(
                    r"^(?P<X>.)(?P<Y>.) (?P<sub>.{4}) (?:[^ ]+ ){7}(?P<path>.*)$",
                    line[2:],
                )
                assert match is not None
                sub = match.group("sub")
                if sub[0] == "S":
                    path_status = UnmergedSubmoduleStatus(
                        path=pathlib.Path(match.group("path")),
                        us=Modification(match.group("X")),
                        them=Modification(match.group("Y")),
                        commit_changed=sub[1] != ".",
                        has_tracked_changes=sub[2] != ".",
                        has_untracked_changes=sub[3] != ".",
                    )
                else:
                    path_status = UnmergedFileStatus(
                        path=pathlib.Path(match.group("path")),
                        us=Modification(match.group("X")),
                        them=Modification(match.group("Y")),
                    )
                status.changes.append(path_status)
            elif line.startswith("?"):
                status.changes.append(
                    FileStatus(
                        path=pathlib.Path(line[2:]),
                        path_from=None,
                        staged=Modification.UNTRACKED,
                        tree=Modification.UNTRACKED,
                    )
                )
            elif line.startswith("!"):
                status.changes.append(
                    FileStatus(
                        path=pathlib.Path(line[2:]),
                        path_from=None,
                        staged=Modification.IGNORED,
                        tree=Modification.IGNORED,
                    )
                )

        try:
            status.cherry_pick_head = (
                self.git("rev-parse", "--verify", "CHERRY_PICK_HEAD").decode().strip()
            )
        except GitError:
            pass
        try:
            status.merge_head = (
                self.git("rev-parse", "--verify", "MERGE_HEAD").decode().strip()
            )
        except GitError:
            pass
        try:
            status.rebase_head = (
                self.git("rev-parse", "--verify", "REBASE_HEAD").decode().strip()
            )
        except GitError:
            pass
        try:
            status.revert_head = (
                self.git("rev-parse", "--verify", "REVERT_HEAD").decode().strip()
            )
        except GitError:
            pass

        return status

    def print_status(self):
        """
        Run ``git status`` and show its output to the user.

        """

        self.git("status", capture_output=False)

    def log(self, *refs: str, max_entries: int | None = None) -> list[Commit]:
        """
        Query the log for given git objects.

        :param refs:
            git references that will be passed to ``git log``.
        :param max_entries:
            maximum number of returned references.

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

        :param refs:
            git references that will be passed to ``git log``.
        :param max_entries:
            maximum number of checked commits.

            .. warning::

                This option limits number of checked commits, not the number
                of trailers.

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

        Return :data:`None` if object is not found.

        :param ref:
            git reference that will be passed to ``git log``.

        """

        try:
            self.git("rev-parse", "--verify", ref)
        except GitError:
            return None

        log = self.log(ref, max_entries=1)
        if not log:
            return None
        else:
            commit = log[0]
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

        return [
            remote
            for remote in self.git(
                "for-each-ref", "--format=%(refname:short)", "refs/remotes"
            )
            .decode()
            .splitlines()
            if "/" in remote
        ]


@dataclass
class Commit:
    """
    Commit description.

    """

    hash: str
    """
    Commit hash.

    """

    tags: list[str]
    """
    Tags attached to this commit.

    """

    author: str
    """
    Author name.

    """

    author_email: str
    """
    Author email.

    """

    author_datetime: datetime
    """
    Author time.

    """

    committer: str
    """
    Committer name.

    """

    committer_email: str
    """
    Committer email.

    """

    committer_datetime: datetime
    """
    Committer time.

    """

    title: str
    """
    Commit title, i.e. first line of the message.

    """

    body: str
    """
    Commit body, i.e. the rest of the message.

    """

    orig_ref: str | None = None
    """
    If commit was parsed from a user input, this field will contain
    original input. I.e. if a user enters ``HEAD`` and it gets resolved
    into a commit, `orig_ref` will contain string ``"HEAD"``.

    See also :class:`CommitParser`.

    """

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

    hash: str
    """
    Commit hash.

    """

    trailers: list[tuple[str, str]]
    """
    Key-value pairs for commit trailers.

    """


class Modification(enum.Enum):
    """
    For changed file or submodule, what modification was applied to it.

    """

    UNMODIFIED = "."
    """
    File wasn't changed.

    """

    MODIFIED = "M"
    """
    File was changed.

    """

    SUBMODULE_MODIFIED = "m"
    """
    Contents of submodule were modified.

    """

    TYPE_CHANGED = "T"
    """
    File type changed.

    """

    ADDED = "A"
    """
    File was created.

    """

    DELETED = "D"
    """
    File was deleted.

    """

    RENAMED = "R"
    """
    File was renamed (and possibly changed).

    """

    COPIED = "C"
    """
    File was copied (and possibly changed).

    """

    UPDATED = "U"
    """
    File was updated but unmerged.

    """

    UNTRACKED = "?"
    """
    File is untracked, i.e. not yet staged or committed.

    """

    IGNORED = "!"
    """
    File is in ``.gitignore``.

    """


@dataclass
class PathStatus:
    """
    Status of a changed path.

    """

    path: pathlib.Path
    """
    Path of the file.

    """


@dataclass
class FileStatus(PathStatus):
    """
    Status of a changed file.

    """

    path_from: pathlib.Path | None
    """
    If file was moved, contains path where it was moved from.

    """

    staged: Modification
    """
    File modification in the index (staged).

    """

    tree: Modification
    """
    File modification in the tree (unstaged).

    """


@dataclass
class SubmoduleStatus(FileStatus):
    """
    Status of a submodule.

    """

    commit_changed: bool
    """
    The submodule has a different HEAD than recorded in the index.

    """

    has_tracked_changes: bool
    """
    Tracked files were changed in the submodule.

    """

    has_untracked_changes: bool
    """
    Untracked files were changed in the submodule.

    """


@dataclass
class UnmergedFileStatus(PathStatus):
    """
    Status of an unmerged file.

    """

    us: Modification
    """
    File modification that has happened at the head.

    """

    them: Modification
    """
    File modification that has happened at the merge head.

    """


@dataclass
class UnmergedSubmoduleStatus(UnmergedFileStatus):
    """
    Status of an unmerged submodule.

    """

    commit_changed: bool
    """
    The submodule has a different HEAD than recorded in the index.

    """

    has_tracked_changes: bool
    """
    Tracked files were changed in the submodule.

    """

    has_untracked_changes: bool
    """
    Untracked files were changed in the submodule.

    """


@dataclass
class Status:
    """
    Status of a working copy.

    """

    commit: str | None
    """
    Current commit hash. Can be absent if current branch is orphaned and doesn't have
    any commits yet.

    """

    branch: str | None = None
    """
    Name of the current branch.

    """

    upstream: str | None = None
    """
    Name of the upstream branch.

    """

    ahead: int | None = None
    """
    Number of commits the branch is ahead of upstream.

    """

    behind: int | None = None
    """
    Number of commits the branch is behind of upstream.

    """

    changes: list[PathStatus] = dataclasses.field(default_factory=list)
    """
    List of changed files, both tracked and untracked.

    See details about change representation in `git status`__ manual.

    __ https://git-scm.com/docs/git-status#_output

    """

    cherry_pick_head: str | None = None
    """
    Position of the ``CHERRY_PICK_HEAD``.

    If this field is not :data:`None`, cherry pick is in progress.

    """

    merge_head: str | None = None
    """
    Position of the ``MERGE_HEAD``.

    If this field is not :data:`None`, merge is in progress.

    """

    rebase_head: str | None = None
    """
    Position of the ``REBASE_HEAD``.

    If this field is not :data:`None`, rebase is in progress.

    """

    revert_head: str | None = None
    """
    Position of the ``REVERT_HEAD``.

    If this field is not :data:`None`, revert is in progress.

    """

    def has_staged_changes(self) -> bool:
        """
        Return :data:`True` if there are unstaged changes in this repository.

        """

        return next(self.get_staged_changes(), None) is not None

    def get_staged_changes(self) -> _t.Iterator[PathStatus]:
        return (
            change
            for change in self.changes
            if isinstance(change, FileStatus)
            and change.staged
            not in [
                Modification.UNMODIFIED,
                Modification.IGNORED,
                Modification.UNTRACKED,
            ]
        )

    def has_unstaged_changes(self) -> bool:
        """
        Return :data:`True` if there are unstaged changes in this repository.

        """

        return next(self.get_unstaged_changes(), None) is not None

    def get_unstaged_changes(self) -> _t.Iterator[PathStatus]:
        return (
            change
            for change in self.changes
            if isinstance(change, UnmergedFileStatus)
            or (
                isinstance(change, FileStatus)
                and change.tree
                not in [
                    Modification.UNMODIFIED,
                    Modification.IGNORED,
                ]
            )
        )


class RefCompleterMode(enum.Enum):
    """
    Specifies operation modes for :class:`RefCompleter`.

    """

    BRANCH = "b"
    """
    Completes branches.

    """

    REMOTE = "r"
    """
    Completes remote branches.

    """

    TAG = "t"
    """
    Completes tags.

    """

    HEAD = "h"
    """
    Completes ``HEAD`` and ``ORIG_HEAD``.

    """


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
            RefCompleterMode.BRANCH,
            RefCompleterMode.TAG,
            RefCompleterMode.HEAD,
        }

    def _process(self, collector: yuio.complete.CompletionCollector, /):
        try:
            if RefCompleterMode.HEAD in self._modes:
                collector.add_group()
                git_dir = self._repo.git_dir
                for head in ["HEAD", "ORIG_HEAD"]:
                    if (git_dir / head).exists():
                        collector.add(head)
            if RefCompleterMode.BRANCH in self._modes:
                collector.add_group()
                for branch in self._repo.branches():
                    collector.add(branch, comment="branch")
            if RefCompleterMode.REMOTE in self._modes:
                collector.add_group()
                for remote in self._repo.remotes():
                    collector.add(remote, comment="remote")
            if RefCompleterMode.TAG in self._modes:
                collector.add_group()
                for tag in self._repo.tags():
                    collector.add(tag, comment="tag")
        except GitError:
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

    :param repo:
        initialized repository is required to ensure that commit is valid.

    """

    def map(value: str, /) -> Commit:
        commit = repo.show(value)
        if commit is None:
            raise yuio.parse.ParsingError("invalid git ref")
        return commit

    def rev(value: Commit | object) -> str:
        if isinstance(value, Commit):
            return str(value)
        else:
            raise TypeError(
                f"parser Commit can't handle value "
                f"of type {_t.type_repr(type(value))}"
            )

    return yuio.parse.WithMeta(
        yuio.parse.Map(yuio.parse.Str(), map, rev),
        desc="<commit>",
        completer=RefCompleter(repo),
    )


T = _t.TypeVar("T")


class _RefParserImpl(yuio.parse.Str, _t.Generic[T]):
    @functools.cached_property
    def _description(self):
        return "<" + self.__class__.__name__.removesuffix("Parser").lower() + ">"

    def describe(self) -> str | None:
        return self._description

    def describe_or_def(self) -> str:
        return self._description

    def describe_many(self) -> str | tuple[str, ...] | None:
        return self._description

    def describe_many_or_def(self) -> str | tuple[str, ...]:
        return self._description


class RefParser(_RefParserImpl[Ref]):
    """
    A parser that provides autocompletion for git refs, but doesn't verify
    anything else.

    """

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(
            Repo(pathlib.Path.cwd(), skip_checks=True),
        )


class TagParser(_RefParserImpl[Tag]):
    """
    A parser that provides autocompletion for git tag, but doesn't verify
    anything else.

    """

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(
            Repo(pathlib.Path.cwd(), skip_checks=True),
            {RefCompleterMode.TAG},
        )


class BranchParser(_RefParserImpl[Branch]):
    """
    A parser that provides autocompletion for git branches, but doesn't verify
    anything else.

    """

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(
            Repo(pathlib.Path.cwd(), skip_checks=True),
            {RefCompleterMode.BRANCH},
        )


class RemoteParser(_RefParserImpl[Remote]):
    """
    A parser that provides autocompletion for git remotes, but doesn't verify
    anything else.

    """

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(
            Repo(pathlib.Path.cwd(), skip_checks=True),
            {RefCompleterMode.REMOTE},
        )


yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: RefParser() if ty is Ref else None
)

yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: TagParser() if ty is Tag else None
)

yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: BranchParser() if ty is Branch else None
)

yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: RemoteParser() if ty is Remote else None
)
