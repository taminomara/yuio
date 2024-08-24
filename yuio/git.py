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

.. autoclass:: Status
   :members:

.. autoclass:: FileStatus
   :members:

.. autoclass:: Modification
   :members:


Parsing git refs
----------------

When you need to query a git ref from a user, :class:`RefParser` will ensure
that the ref points to a valid git object. Use :class:`Ref` in your type hints
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

"""

import dataclasses
import enum
import functools
import pathlib
import re
import subprocess
from yuio import _t
from dataclasses import dataclass
from datetime import datetime

import yuio.parse
import yuio.complete


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


_LOG_FMT = "%H%n%aN%n%aE%n%aI%n%cN%n%cE%n%cI%n%w(0,0,1)%B%w(0,0)%n-"


class Repo:
    """A class that allows interactions with a git repository.

    :param path:
        path to the repo root dir.
    :param skip_checks:
        don't check if we're inside a repo.

    """

    def __init__(self, path: _t.Union[pathlib.Path, str], /, skip_checks: bool = False):
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
        """Path to the repo, as was passed to the constructor."""

        return self.__path

    def git(self, *args: str) -> bytes:
        """Call git and return its stdout."""

        res = subprocess.run(
            ["git"] + list(args),
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=self.__path,
        )

        if res.returncode != 0:
            raise GitException(
                f"git exited with status code {res.returncode}:\n"
                f"{res.stderr.decode()}"
            )

        return res.stdout

    def root(self) -> pathlib.Path:
        """Get the root directory of the repo."""

        return pathlib.Path(self.git("rev-parse", "--show-toplevel").decode())

    def git_dir(self) -> pathlib.Path:
        """Get path to the ``.git`` directory of the repo."""

        return pathlib.Path(self.git("rev-parse", "--git-dir").decode())

    def status(self) -> "Status":
        """Query the current repository status."""

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

    def log(self, *refs: str, max_entries: _t.Optional[int] = 10) -> _t.List["Commit"]:
        """Query the log for given git objects.

        Note that by default log output is limited by ten entries.

        """

        args = [f"--pretty=format:{_LOG_FMT}"]

        if max_entries is not None:
            args += ["-n", str(max_entries)]

        args += list(refs)

        text = self.git("log", *args)
        lines = iter(text.decode().split("\n"))

        commits = []

        while commit := self.__parse_single_log_entry(lines):
            commits.append(commit)

        return commits

    def show(self, ref: str, /) -> "_t.Optional[Commit]":
        """Query information for the given git object.

        Return `None` if object is not found.

        """

        try:
            self.git("rev-parse", "--verify", ref)
        except GitException:
            return None

        text = self.git(
            "show",
            f"--pretty=format:{_LOG_FMT}",
            "-s",
            ref,
        )

        lines = iter(text.decode().split("\n"))

        commit = self.__parse_single_log_entry(lines)

        if commit is None:
            return None

        commit.orig_ref = ref

        return commit

    @staticmethod
    def __parse_single_log_entry(lines) -> "_t.Optional[Commit]":
        try:
            commit = next(lines)
            author = next(lines)
            author_email = next(lines)
            author_date = datetime.fromisoformat(next(lines))
            committer = next(lines)
            committer_email = next(lines)
            committer_date = datetime.fromisoformat(next(lines))
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
                author,
                author_email,
                author_date,
                committer,
                committer_email,
                committer_date,
                title,
                body,
            )
        except StopIteration:
            return None

    def tags(self) -> _t.List[str]:
        """
        List all tags in this repository.

        """

        return (
            self.git("for-each-ref", "--format='%(refname:short)'", "refs/tags")
            .decode()
            .splitlines()
        )

    def branches(self) -> _t.List[str]:
        """
        List all branches in this repository.

        """

        return (
            self.git("for-each-ref", "--format='%(refname:short)'", "refs/heads")
            .decode()
            .splitlines()
        )

    def remotes(self) -> _t.List[str]:
        """
        List all remote branches in this repository.

        """

        return (
            self.git("for-each-ref", "--format='%(refname:short)'", "refs/remotes")
            .decode()
            .splitlines()
        )


@dataclass
class Commit:
    """Commit description."""

    #: Commit hash.
    hash: str

    #: Author name.
    author: str

    #: Author email.
    author_email: str

    #: Author time.
    author_date: datetime

    #: Committer name.
    committer: str

    #: Committer email.
    committer_email: str

    #: Committer time.
    committer_date: datetime

    #: Commit title, i.e. first line of the message.
    title: str

    #: Commit body, i.e. the rest of the message.
    body: str

    #: If commit was parsed from a user input, this field will contain
    #: original input. I.e. if a user enters ``HEAD`` and it gets resolved
    #: into a commit, `orig_ref` will contain string ``'HEAD'``.
    #:
    #: See also :class:`CommitParser`.
    orig_ref: _t.Optional[str] = None

    @property
    def short_hash(self):
        return self.hash[:7]

    def __str__(self):
        if self.orig_ref:
            return self.orig_ref
        else:
            return self.short_hash


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
    UPDATED = "U"

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
    path_from: _t.Optional[pathlib.Path] = None

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
    branch: _t.Optional[str] = None

    #: Name of the upstream branch.
    upstream: _t.Optional[str] = None

    #: Number of commits the branch is ahead of upstream.
    ahead: _t.Optional[int] = None

    #: Number of commits the branch is behind of upstream.
    behind: _t.Optional[int] = None

    #: True if any tracked file was changed.
    has_tracked_changes: bool = False

    #: True if any file was added but not tracked.
    has_untracked_changes: bool = False

    #: List of changed files, both tracked and untracked.
    changes: _t.List[FileStatus] = dataclasses.field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        """True if there are any changes in the repository."""

        return self.has_tracked_changes or self.has_untracked_changes


class RefCompleter(yuio.complete.Completer):
    class Mode(enum.Enum):
        Branch = "b"
        Remote = "r"
        Tag = "t"
        Head = "h"

    def __init__(
        self, repo: Repo, modes: _t.Optional[_t.Set["RefCompleter.Mode"]] = None
    ):
        super().__init__()

        self._repo = repo
        self._modes = modes or {
            self.Mode.Branch,
            self.Mode.Tag,
            self.Mode.Head,
        }

    def process(self, collector: yuio.complete.CompletionCollector, /):
        try:
            if self.Mode.Head in self._modes:
                collector.add_group()
                git_dir = self._repo.git_dir()
                for head in ["HEAD", "ORIG_HEAD"]:
                    if (git_dir / head).exists():
                        collector.add(head)
            if self.Mode.Branch in self._modes:
                collector.add_group()
                for branch in self._repo.branches():
                    collector.add(branch)
            if self.Mode.Remote in self._modes:
                collector.add_group()
                for remote in self._repo.remotes():
                    collector.add(remote)
            if self.Mode.Tag in self._modes:
                collector.add_group()
                for tag in self._repo.tags():
                    collector.add(tag)
        except GitException:
            pass

    def _get_completion_model(
        self, *, is_many: bool = False
    ) -> "yuio.complete._CompleterSerializer.Model":
        return yuio.complete._CompleterSerializer.Git(
            set(
                yuio.complete._CompleterSerializer.Git.Mode(mode.value)
                for mode in self._modes
            )
        )


class CommitParser(yuio.parse.ValueParser[Commit]):
    """
    A parser for git refs (commits, tags, branches, and so on).

    This parser validates that the given ref exists in the given repository,
    parses it and returns a commit data associated with this ref.

    If you need a simple string without additional validation,
    use :class:`RefParser`.

    """

    def __init__(self, repo: Repo):
        super().__init__()

        self._repo = repo

    def parse(self, value: str, /) -> Commit:
        commit = self._repo.show(value)
        if commit is None:
            raise yuio.parse.ParsingError("invalid git ref")
        return commit

    def parse_config(self, value: _t.Any, /) -> Commit:
        if not isinstance(value, str):
            raise yuio.parse.ParsingError("expected a string")
        return self.parse(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo)


_Str = _t.TypeVar("_Str", bound=str)


class _RefParserImpl(yuio.parse.ValidatingParser[_Str], _t.Generic[_Str]):
    def __init__(
        self,
        repo_path: _t.Union[Repo, str, pathlib.Path, None] = None,
        /,
        *,
        should_exist: bool = False,
    ):
        super().__init__(_t.cast(yuio.parse.Parser[_Str], yuio.parse.Str()))

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

    def _validate(self, value: str, /):
        if self._should_exist and self._repo.show(value) is None:
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

    def _validate(self, value: str, /):
        try:
            self._repo.git("check-ref-format", f"refs/tags/{value}")
        except GitException:
            raise yuio.parse.ParsingError(f"{value} is not a valid tag name") from None

        super()._validate(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo, {RefCompleter.Mode.Tag})


class BranchParser(_RefParserImpl[Branch]):
    """
    A parser that checks if the given string is a valid tag name.

    """

    def _validate(self, value: str, /):
        try:
            self._repo.git("check-ref-format", f"refs/heads/{value}")
        except GitException:
            raise yuio.parse.ParsingError(
                f"{value} is not a valid branch name"
            ) from None

        super()._validate(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo, {RefCompleter.Mode.Branch})


class RemoteParser(_RefParserImpl[Remote]):
    """
    A parser that checks if the given string is a valid tag remote branch.

    """

    def _validate(self, value: str, /):
        try:
            self._repo.git("check-ref-format", f"refs/remotes/{value}")
        except GitException:
            raise yuio.parse.ParsingError(
                f"{value} is not a valid branch name"
            ) from None

        super()._validate(value)

    def completer(self) -> yuio.complete.Completer:
        return RefCompleter(self._repo, {RefCompleter.Mode.Branch})


yuio.parse.register_type_hint_conversion(
    lambda ty, origin, args: RefParser() if ty is Ref else None
)
