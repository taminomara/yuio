import datetime
import pathlib
import subprocess
import tempfile

import pytest

import yuio.complete
import yuio.git
import yuio.json_schema


class EqualsToAnything:
    def __eq__(self, value: object) -> bool:
        return True

    def __ne__(self, value: object) -> bool:
        return False

    def __lt__(self, rhs: object):
        return False


@pytest.fixture(autouse=True)
def git_env(monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "author")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "author@example.com")
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2020-01-01T00:00:00Z")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "committer")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "committer@example.com")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2020-01-02T00:00:00Z")
    pass


@pytest.fixture
def repo_base():
    with tempfile.TemporaryDirectory() as base_s:
        base = pathlib.Path(base_s).resolve()

        template = base / "template"
        template.mkdir()

        yield base


@pytest.fixture
def repo_path(repo_base):
    repo = repo_base / "repo"
    repo.mkdir()

    subprocess.check_call(
        ["git", "init", ".", "-b", "main", "--template", str(repo_base / "template")],
        cwd=repo,
    )

    return repo


@pytest.fixture
def remote_repo_path(repo_base):
    repo = repo_base / "repo_remote"
    repo.mkdir()

    subprocess.check_call(
        ["git", "init", ".", "-b", "main", "--template", str(repo_base / "template")],
        cwd=repo,
    )
    subprocess.check_call(
        ["git", "commit", "--allow-empty", "--message", "initial commit"],
        cwd=repo,
    )

    return repo


@pytest.fixture
def repo(repo_path):
    return yuio.git.Repo(repo_path)


def test_not_a_repo():
    with (
        tempfile.TemporaryDirectory() as base,
        pytest.raises(yuio.git.NotARepositoryError, match=r"not a git repository"),
    ):
        yuio.git.Repo(base)


@pytest.mark.linux
@pytest.mark.darwin
def test_git_unavailable(repo_path):
    with pytest.raises(yuio.git.GitUnavailableError, match=r"git executable not found"):
        yuio.git.Repo(repo_path, env={"PATH": ""})


def test_simple(repo_path):
    repo = yuio.git.Repo(repo_path)
    assert repo.path == repo_path
    assert repo.root == repo_path
    assert repo.git_dir == repo_path / ".git"


def test_status(repo):
    status = repo.status()

    assert status.commit is None
    assert status.branch == "main"
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert not status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == []

    repo.root.joinpath("foo").write_text("a")
    repo.root.joinpath("bar").write_text("b")

    status = repo.status()
    assert not status.has_staged_changes()
    assert status.has_unstaged_changes()
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path("bar"),
            path_from=None,
            staged=yuio.git.Modification.UNTRACKED,
            tree=yuio.git.Modification.UNTRACKED,
        ),
        yuio.git.FileStatus(
            path=pathlib.Path("foo"),
            path_from=None,
            staged=yuio.git.Modification.UNTRACKED,
            tree=yuio.git.Modification.UNTRACKED,
        ),
    ]

    repo.git("add", repo.root / "bar")

    status = repo.status()
    assert status.has_staged_changes()
    assert status.has_unstaged_changes()
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path("bar"),
            path_from=None,
            staged=yuio.git.Modification.ADDED,
            tree=yuio.git.Modification.UNMODIFIED,
        ),
        yuio.git.FileStatus(
            path=pathlib.Path("foo"),
            path_from=None,
            staged=yuio.git.Modification.UNTRACKED,
            tree=yuio.git.Modification.UNTRACKED,
        ),
    ]

    repo.git("add", repo.root / "foo")

    status = repo.status()
    assert status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path("bar"),
            path_from=None,
            staged=yuio.git.Modification.ADDED,
            tree=yuio.git.Modification.UNMODIFIED,
        ),
        yuio.git.FileStatus(
            path=pathlib.Path("foo"),
            path_from=None,
            staged=yuio.git.Modification.ADDED,
            tree=yuio.git.Modification.UNMODIFIED,
        ),
    ]

    repo.git("commit", "-m", "message")

    status = repo.status()
    assert status.commit is not None
    assert not status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.changes == []


def test_status_ignored_files(repo):
    repo.root.joinpath(".gitignore").write_text("ignored.txt\n")
    repo.git("add", ".gitignore")
    repo.git("commit", "-m", "message")

    status = repo.status()

    assert status.branch == "main"
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert not status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == []

    repo.root.joinpath("ignored.txt").write_text("...")

    status = repo.status()
    assert not status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.changes == []

    status = repo.status(include_ignored=True)
    assert not status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path("ignored.txt"),
            path_from=None,
            staged=yuio.git.Modification.IGNORED,
            tree=yuio.git.Modification.IGNORED,
        ),
    ]


def test_status_remote(repo, remote_repo_path):
    repo.git("remote", "add", "origin", str(remote_repo_path))
    repo.git("fetch", "origin")
    repo.git("checkout", "main")

    status = repo.status()
    assert status.branch == "main"
    assert status.upstream == "origin/main"
    assert status.ahead == 0
    assert status.behind == 0

    repo.git("commit", "-m", "message", "--allow-empty")

    status = repo.status()
    assert status.branch == "main"
    assert status.upstream == "origin/main"
    assert status.ahead == 1
    assert status.behind == 0


def test_status_conflicts(repo):
    repo.git("commit", "-m", "message", "--allow-empty")
    repo.root.joinpath("file.txt").write_text("1")
    repo.git("add", "file.txt")
    repo.git("commit", "-m", "message")
    repo.git("checkout", "HEAD~1")
    repo.root.joinpath("file.txt").write_text("2")
    repo.git("add", "file.txt")
    repo.git("commit", "-m", "message")
    try:
        repo.git("merge", "main")
    except yuio.git.GitError:
        pass
    status = repo.status()
    assert status.commit is not None
    assert status.branch is None
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert not status.has_staged_changes()
    assert status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is not None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == [
        yuio.git.UnmergedFileStatus(
            path=pathlib.Path("file.txt"),
            us=yuio.git.Modification.ADDED,
            them=yuio.git.Modification.ADDED,
        )
    ]


def test_status_move(repo):
    repo.root.joinpath("file.txt").write_text("foo bar baz" * 10)
    repo.git("add", "file.txt")
    repo.git("commit", "-m", "message", "--allow-empty")
    repo.git("mv", "file.txt", "file2.txt")
    status = repo.status()
    assert status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path("file2.txt"),
            path_from=pathlib.Path("file.txt"),
            staged=yuio.git.Modification.RENAMED,
            tree=yuio.git.Modification.UNMODIFIED,
        )
    ]


def test_status_submodule(repo, remote_repo_path):
    repo.git(
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        remote_repo_path,
        "submodule",
    )
    status = repo.status()
    assert status.commit is None
    assert status.branch == "main"
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path(".gitmodules"),
            path_from=None,
            staged=yuio.git.Modification.ADDED,
            tree=yuio.git.Modification.UNMODIFIED,
        ),
        yuio.git.SubmoduleStatus(
            path=pathlib.Path("submodule"),
            path_from=None,
            staged=yuio.git.Modification.ADDED,
            tree=yuio.git.Modification.UNMODIFIED,
            commit_changed=False,
            has_tracked_changes=False,
            has_untracked_changes=False,
        ),
    ]


def test_status_submodule_changed(repo, remote_repo_path):
    repo.git(
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        remote_repo_path,
        "submodule",
    )
    repo.git("commit", "--message", "message")
    repo.root.joinpath("submodule/file.txt").write_text("foo")

    status = repo.status()
    assert status.commit is not None
    assert status.branch == "main"
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert not status.has_staged_changes()
    assert status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == [
        yuio.git.SubmoduleStatus(
            path=pathlib.Path("submodule"),
            path_from=None,
            staged=yuio.git.Modification.UNMODIFIED,
            tree=yuio.git.Modification.MODIFIED,
            commit_changed=False,
            has_tracked_changes=False,
            has_untracked_changes=True,
        )
    ]


def test_status_submodule_moved(repo, remote_repo_path):
    repo.git(
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        remote_repo_path,
        "submodule",
    )
    repo.git("commit", "--message", "message")
    repo.git("mv", "submodule", "submodule_moved")

    status = repo.status()
    assert status.commit is not None
    assert status.branch == "main"
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert status.has_staged_changes()
    assert not status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == [
        yuio.git.FileStatus(
            path=pathlib.Path(".gitmodules"),
            path_from=None,
            staged=yuio.git.Modification.MODIFIED,
            tree=yuio.git.Modification.UNMODIFIED,
        ),
        yuio.git.SubmoduleStatus(
            path=pathlib.Path("submodule_moved"),
            path_from=pathlib.Path("submodule"),
            staged=yuio.git.Modification.RENAMED,
            tree=yuio.git.Modification.UNMODIFIED,
            commit_changed=False,
            has_tracked_changes=False,
            has_untracked_changes=False,
        ),
    ]


def test_status_submodule_conflicts(repo, remote_repo_path):
    repo.git(
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        remote_repo_path,
        "submodule",
    )
    repo.git("commit", "--message", "message")

    submodule_repo = yuio.git.Repo(repo.root / "submodule")

    submodule_repo.root.joinpath("foo.txt").write_text("foo")
    submodule_repo.git("add", "foo.txt")
    submodule_repo.git("commit", "--message", "message")
    repo.git("add", "submodule")
    repo.git("commit", "--message", "message")

    repo.git("checkout", "HEAD~1")
    submodule_repo.git("checkout", "HEAD~1")

    submodule_repo.root.joinpath("foo.txt").write_text("bar")
    submodule_repo.git("add", "foo.txt")
    submodule_repo.git("commit", "--message", "message")
    repo.git("add", "submodule")
    repo.git("commit", "--message", "message")

    try:
        repo.git("merge", "main")
    except yuio.git.GitError:
        pass

    status = repo.status()
    assert status.commit is not None
    assert status.branch is None
    assert status.upstream is None
    assert status.ahead is None
    assert status.behind is None
    assert not status.has_staged_changes()
    assert status.has_unstaged_changes()
    assert status.cherry_pick_head is None
    assert status.merge_head is not None
    assert status.rebase_head is None
    assert status.revert_head is None
    assert status.changes == [
        yuio.git.UnmergedSubmoduleStatus(
            path=pathlib.Path("submodule"),
            us=yuio.git.Modification.UPDATED,
            them=yuio.git.Modification.UPDATED,
            commit_changed=False,
            has_tracked_changes=False,
            has_untracked_changes=False,
        )
    ]


def test_log(repo):
    repo.git(
        "commit",
        "--allow-empty",
        "--message",
        "Title 1\n\nBody 1",
    )
    repo.git(
        "commit",
        "--allow-empty",
        "--message",
        "Title 2\n\nBody 2",
    )
    repo.git("tag", "tag1")
    repo.git("tag", "tag2")
    repo.git(
        "commit",
        "--allow-empty",
        "--message",
        "Title 3\n\nBody 3",
        "--trailer",
        "Trailer1:Value1",
        "--trailer",
        "Trailer2:Value2",
    )

    log = repo.log()
    assert log == [
        yuio.git.Commit(
            hash=EqualsToAnything(),  # type: ignore
            tags=[],
            author="author",
            author_email="author@example.com",
            author_datetime=datetime.datetime(
                2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            ),
            committer="committer",
            committer_email="committer@example.com",
            committer_datetime=datetime.datetime(
                2020, 1, 2, 0, 0, tzinfo=datetime.timezone.utc
            ),
            title="Title 3",
            body="Body 3\n\nTrailer1: Value1\nTrailer2: Value2\n",
            orig_ref=None,
        ),
        yuio.git.Commit(
            hash=EqualsToAnything(),  # type: ignore
            tags=["tag2", "tag1"],
            author="author",
            author_email="author@example.com",
            author_datetime=datetime.datetime(
                2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            ),
            committer="committer",
            committer_email="committer@example.com",
            committer_datetime=datetime.datetime(
                2020, 1, 2, 0, 0, tzinfo=datetime.timezone.utc
            ),
            title="Title 2",
            body="Body 2\n",
            orig_ref=None,
        ),
        yuio.git.Commit(
            hash=EqualsToAnything(),  # type: ignore
            tags=[],
            author="author",
            author_email="author@example.com",
            author_datetime=datetime.datetime(
                2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            ),
            committer="committer",
            committer_email="committer@example.com",
            committer_datetime=datetime.datetime(
                2020, 1, 2, 0, 0, tzinfo=datetime.timezone.utc
            ),
            title="Title 1",
            body="Body 1\n",
            orig_ref=None,
        ),
    ]

    trailers = repo.trailers()
    assert trailers == [
        yuio.git.CommitTrailers(
            hash=log[0].hash,
            trailers=[("Trailer1", "Value1\n"), ("Trailer2", "Value2\n")],
        ),
        yuio.git.CommitTrailers(hash=log[1].hash, trailers=[]),
        yuio.git.CommitTrailers(hash=log[2].hash, trailers=[]),
    ]


def test_show(repo):
    repo.git("commit", "--allow-empty", "--message", "message")
    commit = repo.show("HEAD")
    assert commit == yuio.git.Commit(
        hash=EqualsToAnything(),  # type: ignore
        tags=[],
        author="author",
        author_email="author@example.com",
        author_datetime=datetime.datetime(
            2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
        ),
        committer="committer",
        committer_email="committer@example.com",
        committer_datetime=datetime.datetime(
            2020, 1, 2, 0, 0, tzinfo=datetime.timezone.utc
        ),
        title="message",
        body="",
        orig_ref="HEAD",
    )

    assert repo.show("WAT") is None


def test_tags(repo):
    repo.git("commit", "--allow-empty", "--message", "message")
    repo.git("tag", "tag1")
    repo.git("tag", "tag2")
    assert set(repo.tags()) == {"tag1", "tag2"}


def test_branches(repo):
    repo.git("commit", "--allow-empty", "--message", "message")
    assert repo.branches() == ["main"]
    repo.git("checkout", "-B", "branch")
    assert set(repo.branches()) == {"branch", "main"}


def test_remotes(repo, remote_repo_path):
    repo.git("commit", "--allow-empty", "--message", "message")
    assert repo.remotes() == []
    repo.git("remote", "add", "origin", str(remote_repo_path))
    repo.git("fetch", "origin")
    assert repo.remotes() == ["origin/main"]


class TestRefCompleter:
    @pytest.fixture(autouse=True)
    def setup(self, repo, remote_repo_path):
        repo.git("commit", "--allow-empty", "--message", "message")
        repo.git("tag", "tag1")
        repo.git("tag", "tag2")
        repo.git("remote", "add", "origin", str(remote_repo_path))
        repo.git("fetch", "origin")

    def test_default_mode(self, repo):
        completer = yuio.git.RefCompleter(repo)
        result = completer.complete("", 0)
        assert result == [
            yuio.complete.Completion(
                iprefix="",
                completion="HEAD",
                rsuffix="",
                rsymbols="",
                isuffix="",
                comment=None,
                dprefix="",
                dsuffix="",
                group_color_tag=None,
                group_id=EqualsToAnything(),
            ),
            yuio.complete.Completion(
                iprefix="",
                completion="main",
                rsuffix="",
                rsymbols="",
                isuffix="",
                comment="branch",
                dprefix="",
                dsuffix="",
                group_color_tag=None,
                group_id=EqualsToAnything(),
            ),
            yuio.complete.Completion(
                iprefix="",
                completion="tag1",
                rsuffix="",
                rsymbols="",
                isuffix="",
                comment="tag",
                dprefix="",
                dsuffix="",
                group_color_tag=None,
                group_id=EqualsToAnything(),
            ),
            yuio.complete.Completion(
                iprefix="",
                completion="tag2",
                rsuffix="",
                rsymbols="",
                isuffix="",
                comment="tag",
                dprefix="",
                dsuffix="",
                group_color_tag=None,
                group_id=EqualsToAnything(),
            ),
        ]

    def test_mode(self, repo):
        completer = yuio.git.RefCompleter(
            repo,
            modes={yuio.git.RefCompleterMode.HEAD, yuio.git.RefCompleterMode.REMOTE},
        )
        result = completer.complete("", 0)
        assert result == [
            yuio.complete.Completion(
                iprefix="",
                completion="HEAD",
                rsuffix="",
                rsymbols="",
                isuffix="",
                comment=None,
                dprefix="",
                dsuffix="",
                group_color_tag=None,
                group_id=EqualsToAnything(),
            ),
            yuio.complete.Completion(
                iprefix="",
                completion="origin/main",
                rsuffix="",
                rsymbols="",
                isuffix="",
                comment="remote",
                dprefix="",
                dsuffix="",
                group_color_tag=None,
                group_id=EqualsToAnything(),
            ),
        ]


class TestCommitParser:
    @pytest.fixture(autouse=True)
    def setup(self, repo):
        repo.git("commit", "--allow-empty", "--message", "message")

    def test_basics(self, repo):
        parser = yuio.git.CommitParser(repo=repo)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["HEAD"])
        assert parser.describe() == "<commit>"
        assert parser.describe_or_def() == "<commit>"
        assert parser.describe_many() == "<commit>"
        assert parser.describe_value(repo.show("HEAD")) == "HEAD"

    def test_json_schema(self, repo):
        parser = yuio.git.CommitParser(repo=repo)
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.String()
        )
        assert parser.to_json_value(repo.show("HEAD")) == "HEAD"

    def test_parse(self, repo):
        parser = yuio.git.CommitParser(repo=repo)
        assert parser.parse("HEAD") == repo.show("HEAD")
        assert parser.parse_config("HEAD") == repo.show("HEAD")
        with pytest.raises(ValueError, match=r"invalid git ref"):
            parser.parse("WAT")

    def test_completer(self, repo):
        parser = yuio.git.CommitParser(repo=repo)
        assert isinstance(parser.completer(), yuio.git.RefCompleter)


class TestRefParser:
    @pytest.mark.parametrize(
        ("parser", "name", "modes"),
        [
            (
                yuio.git.RefParser(),
                "<ref>",
                {
                    yuio.git.RefCompleterMode.BRANCH,
                    yuio.git.RefCompleterMode.TAG,
                    yuio.git.RefCompleterMode.HEAD,
                },
            ),
            (
                yuio.git.TagParser(),
                "<tag>",
                {
                    yuio.git.RefCompleterMode.TAG,
                },
            ),
            (
                yuio.git.BranchParser(),
                "<branch>",
                {
                    yuio.git.RefCompleterMode.BRANCH,
                },
            ),
            (
                yuio.git.RemoteParser(),
                "<remote>",
                {
                    yuio.git.RefCompleterMode.REMOTE,
                },
            ),
        ],
    )
    def test_basics(self, parser, name, modes):
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["HEAD"])
        assert parser.describe() == name
        assert parser.describe_or_def() == name
        assert parser.describe_many() == name
        assert parser.describe_value("HEAD") == "HEAD"

        completer = parser.completer()
        assert isinstance(completer, yuio.git.RefCompleter)
        assert completer._modes == modes
