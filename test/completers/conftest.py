import pathlib
import shutil
import subprocess

import pytest


@pytest.fixture(autouse=True)
def setup_completions_home(tmp_path: pathlib.Path, monkeypatch):
    test_home = pathlib.Path(__file__).parent / "home"

    home = tmp_path / "home"
    shutil.copytree(test_home, home)

    data_home = home / "data"
    data_home.mkdir()

    cache_home = home / "cache"
    cache_home.mkdir()

    config_home = home / "config"
    config_home.mkdir()

    git_template_dir = home / "git_template_dir"
    git_template_dir.mkdir()

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("LOCALAPPDATA", str(home))
    monkeypatch.setenv("PATH", str(home), prepend=":")
    monkeypatch.chdir(home)

    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "")
    monkeypatch.setenv("GIT_AUTHOR_NAME", "author")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "author@example.com")
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2020-01-01T00:00:00Z")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "committer")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "committer@example.com")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2020-01-02T00:00:00Z")

    subprocess.check_call(
        ["git", "init", ".", "-b", "main", "--template", str(git_template_dir)]
    )


@pytest.fixture
def test_cases():
    cases = [
        "|",
        "-|",
        "--|",
        "a|",
        "args |",
        "args -|",
        "args --bool|",
        "args --bool |",
        "args --no-b|",
        "args --int |",
        "args --str |",
        "args --enum |",
        "args --enum op|",
        "args --override |",
        "args --override op|",
        "args --custom |",
        "args --custom c|",
        "args --custom comp_|",
        "args --one-of |",
        # git
        "args --tuple |",
        "args --tuple x |",
        "args --tuple x y |",
        "args --tuple |x y",
        "args --list |",
        "args --list x |",
        "args --list x | y",
        "args --list x --|",
        "args --list x --one-of |",
        "args --list=|",
        "args --list=op|",
        "args --l|ist=op",
        "args --list=x |",
        "args --set |",
        "args --set option_1 |",
        "args --set option_1 o| option_2",
        "args --dict |",
        "args --dict opt|",
        "args --dict oth|",
        "args --dict x:|",
        "args --dict opt|:xxx",
        "args --dict oth|:xxx",
    ]

    return list(map(_prepare_test_case, cases))


def _prepare_test_case(args_s: str):
    args = args_s.split()
    cword = 0
    prefix_len = 0
    for i, arg in enumerate(args):
        if i > 0:
            prefix_len += 1
        if "|" in arg:
            cword = i
            l, r = arg.split("|", maxsplit=1)
            prefix_len += len(l)
            args[i] = l + r
            break
        else:
            prefix_len += len(arg)
    else:
        assert False, "can't find cursor"
    return cword, prefix_len, args, args_s


def extract_results(output: str):
    lines = output.splitlines()
    i = lines.index("--BEGIN RESULTS--")
    j = lines.index("--END RESULTS--")
    return lines[i + 1 : j]
