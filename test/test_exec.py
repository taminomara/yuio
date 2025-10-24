import logging
import pathlib

import pytest

import yuio.exec


def test_exec():
    result = yuio.exec.exec("echo", "hello")
    assert result == "hello\n"


def test_input():
    result = yuio.exec.exec("cat", input="hello\n")
    assert result == "hello\n"


def test_logging(capsys):
    logging.basicConfig(level=logging.DEBUG, force=True)
    logging.root.manager._clear_cache()  # type: ignore

    result = yuio.exec.exec("bash", "-c", "echo 'message' 1>&2; echo 'result'")
    assert result == "result\n"

    result = yuio.exec.exec(
        "bash", "-c", "echo 'message2' 1>&2; echo 'result2'", level=logging.INFO
    )
    assert result == "result2\n"

    res = capsys.readouterr()
    assert res.out == ""
    assert "DEBUG:yuio.exec:bash -c echo 'message' 1>&2; echo 'result'" in res.err
    assert "DEBUG:yuio.exec:message" in res.err
    assert "INFO:yuio.exec:bash -c echo 'message2' 1>&2; echo 'result2'" in res.err
    assert "INFO:yuio.exec:message2" in res.err


def test_env():
    result = yuio.exec.exec("env", env={"FOO": "BAR"})
    assert "FOO=BAR" in result


def test_cwd(tmp_path):
    result = yuio.exec.exec("pwd", cwd=tmp_path)
    assert pathlib.Path(result.strip()).resolve() == tmp_path.resolve()


def test_path(tmp_path):
    yuio.exec.exec("ls", pathlib.Path(tmp_path))


def test_fail():
    with pytest.raises(yuio.exec.ExecError, match="message"):
        yuio.exec.exec("bash", "-c", "echo 'message' 1>&2; echo 'result'; exit 1")


def test_sh():
    result = yuio.exec.sh("echo hello")
    assert result == "hello\n"
