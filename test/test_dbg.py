import importlib.util
import io

import pytest

import yuio.dbg


def test_report():
    sio = io.StringIO()
    yuio.dbg.print_report(dest=sio)
    res = sio.getvalue()
    assert "System" in res
    assert "Versions" in res
    assert "Terminal and CLI" in res


def test_hooks():
    if not importlib.util.find_spec("yuio_test_hooks"):
        pytest.skip("test/dbg_hooks is not installed")

    sio = io.StringIO()
    yuio.dbg.print_report(dest=sio)
    res = sio.getvalue()

    assert "Collect Env Ok" in res
    assert "Something something" in res
    assert "foo: bar" in res
    assert "collect_env_err" in res
    assert "RuntimeError: something went wrong" in res
