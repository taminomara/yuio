import importlib.util
import io

import pytest

import yuio.dbg

__version__ = "1.1.2.2"


def test_report():
    sio = io.StringIO()
    yuio.dbg.print_report(dest=sio)
    res = sio.getvalue()
    print(res)

    assert "System" in res
    assert "Versions" in res
    assert "Terminal and CLI" in res


def test_custom_collector():
    sio = io.StringIO()
    yuio.dbg.print_report(
        dest=sio,
        settings=yuio.dbg.ReportSettings(
            collectors=[
                yuio.dbg.Report("x Custom Report x", ["x Custom Report Content x"]),
                lambda: yuio.dbg.Report(
                    "x Custom Report 2 x", ["x Custom Report Content 2 x"]
                ),
                lambda: 1 // 0,  # type: ignore
            ]
        ),
    )
    res = sio.getvalue()
    print(res)

    assert "x Custom Report x" in res
    assert "x Custom Report Content x" in res
    assert "x Custom Report 2 x" in res
    assert "x Custom Report Content 2 x" in res
    assert "test.test_dbg.test_custom_collector.<locals>.<lambda>" in res
    assert "ZeroDivisionError:" in res


def test_app_version():
    try:
        from dbg_hooks import main  # type: ignore
    except ImportError:
        pytest.skip("test/test_deps/dbg_hooks is not installed")

    sio = io.StringIO()
    yuio.dbg.print_report(dest=sio, app=main)
    res = sio.getvalue()
    print(res)

    assert "__app__: 1.0.0.1" in res
    assert "dbg_hooks: 1.2.3" in res


def test_packages():
    try:
        import dbg_hooks  # type: ignore
    except ImportError:
        pytest.skip("test/test_deps/dbg_hooks is not installed")

    sio = io.StringIO()
    yuio.dbg.print_report(
        dest=sio,
        settings=yuio.dbg.ReportSettings(
            package=dbg_hooks,
            dependencies=[
                __name__,
                "__main__",
                "foo.bar",
                dbg_hooks,
                "dbg_dep.mod",
                None,  # type: ignore
            ],
        ),
    )
    res = sio.getvalue()
    print(res)

    assert "__main__: unknown" in res
    assert "dbg-dep[opt]: 3.2.1" in res
    assert "dbg_dep.mod: 100.0.0" in res
    assert "dbg_hooks: 1.2.3" in res
    assert "foo.bar: can't collect this item: No module named 'foo'" in res
    assert "test.test_dbg: 1.1.2.2" in res
    assert "yuio: " + yuio.__version__ in res
    assert "TypeError: expected str or ModuleType, got NoneType: None" in res


def test_hooks():
    if not importlib.util.find_spec("dbg_hooks"):
        pytest.skip("test/test_deps/dbg_hooks is not installed")

    sio = io.StringIO()
    yuio.dbg.print_report(dest=sio)
    res = sio.getvalue()
    print(res)

    assert "Collect Env Ok" in res
    assert "Something something" in res
    assert "foo: bar" in res
    assert "collect_env_err" in res
    assert "RuntimeError: something went wrong" in res
    assert "collect_env_missing" in res
    assert "module 'dbg_hooks' has no attribute 'collect_env_missing'" in res
