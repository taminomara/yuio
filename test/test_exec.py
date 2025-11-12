import logging
import os
import pathlib

import pytest

import yuio.exec


def make_script(exitcode=0, as_shell=False):
    if os.name == "nt":
        command = f"echo out_message & echo err_message 1>&2 & exit {exitcode}"
        if as_shell:
            return [command]
        else:
            return ["cmd", "/k", command]
    else:
        command = f"echo out_message && echo err_message 1>&2 && exit {exitcode}"
        if as_shell:
            return [command]
        else:
            return ["sh", "-c", command]


@pytest.mark.parametrize(
    ("logger", "logger_name"),
    [
        (None, "yuio.exec"),
        ("custom.logger", "custom.logger"),
        (logging.getLogger("custom.logger"), "custom.logger"),
    ],
)
def test_exec(capsys, caplog, logger, logger_name):
    caplog.set_level(logging.DEBUG)

    result = yuio.exec.exec(*make_script(), logger=logger)
    assert result.strip() == "out_message"

    result = yuio.exec.exec(*make_script(), logger=logger, level=logging.INFO)
    assert result.strip() == "out_message"

    res = capsys.readouterr()
    assert res.out == ""
    assert res.err == ""

    records = [(n, l, m.strip()) for n, l, m in caplog.record_tuples]
    assert (logger_name, logging.DEBUG, "-> err_message") in records
    assert (logger_name, logging.INFO, "-> err_message") in records


def test_input():
    if os.name == "nt":
        args = [
            "powershell",
            "-noprofile",
            "-command",
            "[Console]::In.ReadToEnd() | Write-Host -NoNewline",
        ]
    else:
        args = ["cat"]
    result = yuio.exec.exec(*args, input="hello\n")
    assert result.strip() == "hello"


def test_large_input():
    if os.name == "nt":
        args = [
            "powershell",
            "-noprofile",
            "-command",
            "[Console]::In.ReadToEnd() | Write-Host -NoNewline",
        ]
    else:
        args = ["cat"]
    data = "x" * 1024 * 1024
    result = yuio.exec.exec(*args, input=data + "\n")
    assert result.strip() == data


def test_env():
    if os.name == "nt":
        args = ["cmd", "/k", "echo %FOO% & exit 0"]
    else:
        args = ["printenv", "FOO"]

    result = yuio.exec.exec(*args, env={"FOO": "BAR"})
    assert result.strip() == "BAR"


def test_cwd(tmp_path):
    if os.name == "nt":
        args = ["cmd", "/k", "cd & exit 0"]
    else:
        args = ["pwd"]
    result = yuio.exec.exec(*args, cwd=tmp_path)
    assert result.strip() == str(tmp_path)


@pytest.mark.linux
@pytest.mark.darwin
def test_path(tmp_path):
    yuio.exec.exec("ls", pathlib.Path(tmp_path))


def test_fail():
    try:
        yuio.exec.exec(*make_script(2))
    except yuio.exec.ExecError as e:
        assert "err_message" in e.stderr
        assert e.stdout.strip() == "out_message"
        assert e.returncode == 2
    else:
        assert False, "didn't fail"


def test_dont_capture_io(capsys, caplog):
    caplog.set_level(logging.DEBUG, "yuio.exec")

    result = yuio.exec.exec(*make_script(), capture_io=False)
    assert result is None

    # We check that our loggers didn't print anything.
    res = capsys.readouterr()
    assert res.out == ""
    assert res.err == ""
    assert " ".join(make_script()) in caplog.messages
