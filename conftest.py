import io

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
