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
   :members:


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
that the ref points to a valid git object:

.. autoclass:: RefParser

"""

import dataclasses
import enum
import pathlib
import re
import subprocess
import typing as _t
from dataclasses import dataclass
from datetime import datetime

import yuio.parse


class GitException(subprocess.SubprocessError):
    """Raised when git returns a non-zero exit code.

    """


class Repo:
    """A class that allows interactions with a git repository.

    """

    def __init__(self, path: _t.Union[pathlib.Path, str], /):
        self._path = pathlib.Path(path)

        if not self._path.joinpath('.git').is_dir():
            raise GitException(f'{path} is not a git repository')

        try:
            self.git('--version')
        except FileNotFoundError:
            raise GitException(f'git executable was not found')

        try:
            self.git('status')
        except GitException:
            raise GitException(f'{path} is not a git repository')

    def git(self, *args: str) -> bytes:
        """Call git and return its stdout.

        """

        res = subprocess.run(
            ['git'] + list(args),
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=self._path,
        )

        if res.returncode != 0:
            raise GitException(
                f'git exited with status code {res.returncode}:\n'
                f'{res.stderr.decode()}'
            )

        return res.stdout

    def status(self) -> 'Status':
        """Query the current repository status.

        """

        text = self.git('status', '--porcelain=v2', '--branch', '-z')
        lines = iter(text.split(b'\0'))

        status = Status(commit='')

        for line_b in lines:
            line = line_b.decode()
            if line.startswith('# branch.oid'):
                status.commit = line[13:]
            elif line.startswith('# branch.head'):
                if line[14:] != '(detached)':
                    status.branch = line[14:]
            elif line.startswith('# branch.upstream'):
                status.upstream = line[18:]
            elif line.startswith('# branch.ab'):
                match = re.match(
                    r'^\+(\d+) -(\d+)$', line[12:])
                assert match is not None
                status.ahead = int(match.group(1))
                status.behind = int(match.group(2))
            elif line.startswith('1'):
                match = re.match(
                    r'^(.)(.) .{4} (?:[^ ]+ ){5}(.*)$', line[2:])
                assert match is not None
                file_status = FileStatus(
                    path=pathlib.Path(match.group(3)),
                    staged=Modification(match.group(1)),
                    tree=Modification(match.group(2)),
                )
                status.changes.append(file_status)
                status.has_tracked_changes |= \
                    file_status.staged is not Modification.UNTRACKED
                status.has_untracked_changes |= \
                    file_status.staged is Modification.UNTRACKED
            elif line.startswith('2'):
                match = re.match(
                    r'^(.)(.) .{4} (?:[^ ]+ ){6}(.*)$', line[2:])
                assert match is not None
                file_status = FileStatus(
                    path=pathlib.Path(match.group(3)),
                    path_from=pathlib.Path(next(lines).decode()),
                    staged=Modification(match.group(1)),
                    tree=Modification(match.group(2)),
                )
                status.changes.append(file_status)
                status.has_tracked_changes |= \
                    file_status.staged is not Modification.UNTRACKED
                status.has_untracked_changes |= \
                    file_status.staged is Modification.UNTRACKED

        return status

    _LOG_FMT = '%H%n%aN%n%aE%n%aI%n%cN%n%cE%n%cI%n%w(0,0,1)%B%w(0,0)%n-'

    def log(
        self,
        *refs: str,
        max_entries: _t.Optional[int] = 10
    ) -> _t.List['Commit']:
        """Query the log for given git objects.

        Note that by default log output is limited by ten entries.

        """

        args = [f'--pretty=format:{self._LOG_FMT}']

        if max_entries is not None:
            args += ['-n', str(max_entries)]

        args += list(refs)

        text = self.git('log', *args)
        lines = iter(text.decode().split('\n'))

        commits = []

        while commit := self._parse_single_log_entry(lines):
            commits.append(commit)

        return commits

    def show(self, ref: str, /) -> _t.Optional['Commit']:
        """Query information for the given git object.

        Return `None` if object is not found.

        """

        try:
            text = self.git(
                'show',
                f'--pretty=format:{self._LOG_FMT}',
                '-s',
                ref,
            )
        except GitException:
            return None

        lines = iter(text.decode().split('\n'))

        commit = self._parse_single_log_entry(lines)

        if commit is None:
            return None

        commit.orig_ref = ref

        return commit

    @staticmethod
    def _parse_single_log_entry(lines) -> _t.Optional['Commit']:
        try:
            commit = next(lines)
            author = next(lines)
            author_email = next(lines)
            author_date = datetime.fromisoformat(next(lines))
            committer = next(lines)
            committer_email = next(lines)
            committer_date = datetime.fromisoformat(next(lines))
            title = next(lines)
            body = ''

            while True:
                line = next(lines)
                if not line or line.startswith(' '):
                    body += line[1:] + '\n'
                else:
                    break

            body = body.strip('\n')
            if body:
                body += '\n'

            return Commit(
                commit,
                author,
                author_email,
                author_date,
                committer,
                committer_email,
                committer_date,
                title,
                body
            )
        except StopIteration:
            return None


@dataclass
class Commit:
    """Commit description.

    """

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
    #: See also :class:`RefParser`.
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
    """For changed file, what modification was applied to it.

    """

    #: File wasn't changed.
    UNMODIFIED = '.'

    #: File was changed.
    MODIFIED = 'M'

    #: File was created.
    ADDED = 'A'

    #: File was deleted.
    DELETED = 'D'

    #: File was renamed (and possibly changed).
    RENAMED = 'R'

    #: File was copied (and possibly changed).
    COPIED = 'C'

    #: File with conflicts is unmerged.
    UPDATED = 'U'

    #: File is in ``.gitignore``.
    IGNORED = '?'

    #: File was created but not yet added to git, i.e. not staged.
    UNTRACKED = '!'


@dataclass
class FileStatus:
    """Status of a changed file.

    """

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
    """Status of a working copy.

    """

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
        """True if there are any changes in the repository.

        """

        return self.has_tracked_changes or self.has_untracked_changes


class RefParser(yuio.parse.Parser[Commit]):
    """A parser for git refs (commits, tags, branches, and so on).

    """

    def __init__(self, repo: Repo):
        super().__init__()

        self._repo = repo

    def _parse(self, value: str, /) -> Commit:
        commit = self._repo.show(value)
        if commit is None:
            raise yuio.parse.ParsingError('invalid git ref')
        return commit

    def _parse_config(self, value: _t.Any, /) -> Commit:
        if not isinstance(value, str):
            raise yuio.parse.ParsingError('expected a string')
        return self.parse(value)
