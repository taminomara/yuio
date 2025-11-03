import io
import platform

import pytest
from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser
from sybil.parsers.rest import SkipParser

# Examples use the new typing syntax.


def _setup(*_args, **_kwargs):
    import yuio.io
    import yuio.term

    yuio.io.setup(term=yuio.term.Term(io.StringIO(), io.StringIO()))


def _teardown(*_args, **_kwargs):
    import yuio.io

    yuio.io.restore_streams()


pytest_collect_file = Sybil(
    parsers=[
        DocTestParser(),
        PythonCodeBlockParser(),
        SkipParser(),
    ],
    patterns=["*.rst", "*.py"],
    excludes=["yuio/_vendor/*", "yuio/ext/sphinx.py"],
    setup=_setup,
    teardown=_teardown,
).pytest()

_PLATFORMS = {"windows", "linux", "darwin"}


def pytest_runtest_setup(item):
    supported_platforms = _PLATFORMS.intersection(
        mark.name for mark in item.iter_markers()
    )
    plat = platform.system().lower()
    if supported_platforms and plat not in supported_platforms:
        pytest.skip(f"cannot run on platform {plat}")
