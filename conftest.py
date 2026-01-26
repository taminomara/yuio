from __future__ import annotations

import io
import platform
import sys

import pytest
from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser
from sybil.parsers.rest import SkipParser

import yuio.io
import yuio.term

if sys.version_info >= (3, 14):

    def _setup(*_args, **_kwargs):
        yuio.term._TTY_SETUP_PERFORMED = True
        yuio.term._TTY_OUTPUT = None
        yuio.term._TTY_INPUT = None
        yuio.term._TERMINAL_THEME = None
        yuio.term._EXPLICIT_COLOR_SUPPORT = yuio.term.ColorSupport.NONE
        yuio.term._COLOR_SUPPORT = yuio.term.ColorSupport.NONE

        yuio.io.setup(term=yuio.term.Term(io.StringIO(), io.StringIO()))

    def _teardown(*_args, **_kwargs):
        yuio.io.restore_streams()
        yuio.io._manager().stop()
        yuio.io._IO_MANAGER = None
        yuio.term._TTY_SETUP_PERFORMED = False
        del yuio.term._TTY_OUTPUT
        del yuio.term._TTY_INPUT
        del yuio.term._TERMINAL_THEME
        del yuio.term._EXPLICIT_COLOR_SUPPORT
        del yuio.term._COLOR_SUPPORT

    pytest_collect_file = Sybil(
        parsers=[
            DocTestParser(),
            PythonCodeBlockParser(),
            SkipParser(),
        ],
        patterns=["*.rst", "*.py"],
        excludes=["yuio/_dist/*", "yuio/ext/sphinx/*"],
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


def pytest_ignore_collect(collection_path, config):
    if collection_path.name.endswith("_314.py"):
        return sys.version_info < (3, 14)

    return False
