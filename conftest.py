from sybil import Sybil
from sybil.parsers.codeblock import PythonCodeBlockParser
from sybil.parsers.doctest import DocTestParser
from sybil.parsers.rest import SkipParser

# Examples use the new typing syntax.


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
    teardown=_teardown,
).pytest()
