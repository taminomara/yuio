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
    subprocess.check_call(["git", "commit", "--allow-empty", "-m", "initial commit"])
    subprocess.check_call(["git", "tag", "v1.0.0"])
    subprocess.check_call(["git", "tag", "v1.1.0"])


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
        "args --bool=|",
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
        "args --git-ref |",
        "args --git-tag |",
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
        "args --nested-tuple |",
        "args --nested-tuple opt|",
        "args --nested-tuple oth|",
        "args --nested-tuple x,|",
        "args --nested-tuple x,opt|",
        "args --nested-tuple opt|,x",
        "args --nested-tuple oth|,x",
        "args --nested-list |",
        "args --nested-list opt|",
        "args --nested-list oth|",
        "args --nested-list x,|",
        "args --nested-list x,|,y",
        "args --nested-list x,oth|,y",
        "args --nested-set |",
        "args --nested-set opt|",
        "args --nested-set oth|",
        "args --nested-set x,|",
        "args --nested-set x,|,y",
        "args --nested-set option_1,|,y",
        "args --nested-set x,oth|,y",
        "args --nested-set option_1,y opt|",
        "args --nested-set option_1,y option_1,opt|",
        "args --nested-dict |",
        "args --nested-dict oth|",
        "args --nested-dict x:|",
        "args --nested-dict x:o|",
        "args --nested-dict x:y,|",
        "args --nested-dict x:y,o|ther:zzz",
        "args --union |",
        "args --union oth|",
        "args --enum-by-name |",
        "args --special-chars |",
        "hidden |",
        "hidden --|",
        "hidden --secret |",
        "hidden --secret x |",
    ]

    return list(map(_prepare_test_case, cases))


def _prepare_test_case(args_s: str):
    args = args_s.split()
    cword = 0
    prefix_len = 0
    token_prefix_len = 0
    for i, arg in enumerate(args):
        if i > 0:
            prefix_len += 1
        if "|" in arg:
            cword = i
            l, r = arg.split("|", maxsplit=1)
            prefix_len += len(l)
            token_prefix_len = len(l)
            args[i] = l + r
            break
        else:
            prefix_len += len(arg)
    else:
        assert False, "can't find cursor"
    return cword, prefix_len, token_prefix_len, args, args_s


def extract_results(output: str):
    lines = output.splitlines()
    i = lines.index("--BEGIN RESULTS--")
    j = lines.index("--END RESULTS--")
    res = list(set(filter(lambda x: x, (line.rstrip() for line in lines[i + 1 : j]))))
    res.sort()
    return res
