import pytest

import yuio
import yuio.color
import yuio.util


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("", ""),
        ("foo", "foo"),
        ("Foo", "foo"),
        ("FOO", "foo"),
        ("FooBar", "foo-bar"),
        ("FooBAR", "foo-bar"),
        ("Foo10", "foo-10"),
        ("Foo#$", "foo-#$"),
        ("FOOBar", "foo-bar"),
        ("FOO10", "foo-10"),
        ("FOO#$", "foo-#$"),
        ("10Foo", "10-foo"),
        ("10FOO", "10-foo"),
        ("#$Foo", "#$-foo"),
        ("#$FOO", "#$-foo"),
        ("HTMLToXML", "html-to-xml"),
        ("html_to_xml", "html-to-xml"),
        ("HTML_To_XML", "html-to-xml"),
        ("HTTP2.0Processor", "http-2.0-processor"),
        ("HTTP2.0PROCESSOR", "http-2.0-processor"),
    ],
)
def test_to_dash_case(given, expected):
    assert yuio.util.to_dash_case(given) == expected


class EmptyCls:
    pass


class DocsCls:
    no_docs = None

    no_docs_2: int

    #: Doc for foo.
    foo = None

    #: Doc
    #: for
    #: bar.
    BAR = None

    #: Doc for baz.
    baz: int

    docstring = None
    """
    Doc for docstring.

    """

    docstring_separate = None
    # Some comment.
    """
    Doc for docstring_separate.

    """

    docstring_separate_2 = None
    #: Ignored (XXX: should we not ignore this?)
    """
    Doc for docstring_separate_2.

    """

    #: Ignored.
    merged = None
    """Merged 1."""

    #: Split 1 ignored.

    #: Split 2.
    split = None

    consecutive_docstrings = None
    """Docs for consecutive_docstrings."""
    """Ignored."""


def docs_fn_empty(): ...


def docs_fn(
    #: Doc foo.
    foo,
    # Not a doc.
    bar,
    baz,  #: Also not a doc.
    qux,
    #: Doc
    #: for
    #: duo
    duo,
): ...


def local_cls():
    class Foo:
        field = None
        """Docs for field."""

    return Foo


@pytest.mark.parametrize(
    ("obj", "expected"),
    [
        (EmptyCls, {}),
        (
            DocsCls,
            {
                "BAR": "Doc\nfor\nbar.",
                "baz": "Doc for baz.",
                "consecutive_docstrings": "Docs for consecutive_docstrings.",
                "docstring": "Doc for docstring.",
                "docstring_separate": "Doc for docstring_separate.",
                "docstring_separate_2": "Doc for docstring_separate_2.",
                "foo": "Doc for foo.",
                "merged": "Merged 1.",
                "split": "Split 2.",
            },
        ),
        (docs_fn_empty, {}),
        (docs_fn, {"duo": "Doc\nfor\nduo", "foo": "Doc foo."}),
        ([], {}),
        (local_cls(), {}),
        (object, {}),
    ],
)
def test_find_docs(obj, expected):
    assert yuio.util.find_docs(obj) == expected


@pytest.mark.parametrize(
    ("doc", "expected"),
    [
        ("", ""),
        ("foo", "foo\n"),
        ("foo\n\n", "foo\n"),
        ("  foo", "foo\n"),
        ("foo\n  bar\n   baz", "foo\nbar\n baz\n"),
    ],
)
def test_dedent(doc, expected):
    assert yuio.util.dedent(doc) == expected


def test_pretty_exception(ctx):
    a = yuio.PrettyException("foo %r bar", "xyz")
    assert ctx.str(a)._parts == [
        yuio.color.Color.NONE,
        "foo ",
        "'xyz'",
        " bar",
    ]
    assert str(a) == "foo 'xyz' bar"
    assert repr(a) == "PrettyException('foo %r bar', 'xyz')"


class TrackedUserString(yuio.util.UserString):
    """A UserString subclass that tracks _wrap calls."""

    __slots__ = ()
    wrap_calls: list[str] = []

    def _wrap(self, data: str):
        TrackedUserString.wrap_calls.append(data)
        return TrackedUserString(data)


@pytest.fixture
def tracked_string():
    """Create a tracked string and clear call history."""
    TrackedUserString.wrap_calls = []
    return TrackedUserString("hello world")


class TestUserStringWrap:
    def test_add(self, tracked_string):
        result = tracked_string + " test"
        assert result == "hello world test"
        assert isinstance(result, TrackedUserString)
        assert "hello world test" in TrackedUserString.wrap_calls

    def test_format(self, tracked_string):
        result = format(tracked_string, ">20")
        assert result == "         hello world"
        assert isinstance(result, TrackedUserString)
        assert "         hello world" in TrackedUserString.wrap_calls

    def test_getitem_index(self, tracked_string):
        result = tracked_string[0]
        assert result == "h"
        assert isinstance(result, TrackedUserString)
        assert "h" in TrackedUserString.wrap_calls

    def test_getitem_slice(self, tracked_string):
        result = tracked_string[0:5]
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_mod(self, tracked_string):
        s = TrackedUserString("hello %s")
        TrackedUserString.wrap_calls = []
        result = s % "world"
        assert result == "hello world"
        assert isinstance(result, TrackedUserString)
        assert "hello world" in TrackedUserString.wrap_calls

    def test_mul(self, tracked_string):
        s = TrackedUserString("ab")
        TrackedUserString.wrap_calls = []
        result = s * 3
        assert result == "ababab"
        assert isinstance(result, TrackedUserString)
        assert "ababab" in TrackedUserString.wrap_calls

    def test_rmul(self, tracked_string):
        s = TrackedUserString("ab")
        TrackedUserString.wrap_calls = []
        result = 3 * s
        assert result == "ababab"
        assert isinstance(result, TrackedUserString)
        assert "ababab" in TrackedUserString.wrap_calls

    def test_capitalize(self, tracked_string):
        result = tracked_string.capitalize()
        assert result == "Hello world"
        assert isinstance(result, TrackedUserString)
        assert "Hello world" in TrackedUserString.wrap_calls

    def test_casefold(self, tracked_string):
        s = TrackedUserString("HELLO")
        TrackedUserString.wrap_calls = []
        result = s.casefold()
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_center(self, tracked_string):
        s = TrackedUserString("hi")
        TrackedUserString.wrap_calls = []
        result = s.center(6)
        assert result == "  hi  "
        assert isinstance(result, TrackedUserString)
        assert "  hi  " in TrackedUserString.wrap_calls

    def test_expandtabs(self, tracked_string):
        s = TrackedUserString("a\tb")
        TrackedUserString.wrap_calls = []
        result = s.expandtabs(4)
        assert result == "a   b"
        assert isinstance(result, TrackedUserString)
        assert "a   b" in TrackedUserString.wrap_calls

    def test_format_map(self, tracked_string):
        s = TrackedUserString("{name}")
        TrackedUserString.wrap_calls = []
        result = s.format_map({"name": "test"})
        assert result == "test"
        assert isinstance(result, TrackedUserString)
        assert "test" in TrackedUserString.wrap_calls

    def test_format_method(self, tracked_string):
        s = TrackedUserString("{} {}")
        TrackedUserString.wrap_calls = []
        result = s.format("hello", "world")
        assert result == "hello world"
        assert isinstance(result, TrackedUserString)
        assert "hello world" in TrackedUserString.wrap_calls

    def test_join(self, tracked_string):
        s = TrackedUserString("-")
        TrackedUserString.wrap_calls = []
        result = s.join(["a", "b", "c"])
        assert result == "a-b-c"
        assert isinstance(result, TrackedUserString)
        assert "a-b-c" in TrackedUserString.wrap_calls

    def test_ljust(self, tracked_string):
        s = TrackedUserString("hi")
        TrackedUserString.wrap_calls = []
        result = s.ljust(5)
        assert result == "hi   "
        assert isinstance(result, TrackedUserString)
        assert "hi   " in TrackedUserString.wrap_calls

    def test_lower(self, tracked_string):
        s = TrackedUserString("HELLO")
        TrackedUserString.wrap_calls = []
        result = s.lower()
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_lstrip(self, tracked_string):
        s = TrackedUserString("  hello")
        TrackedUserString.wrap_calls = []
        result = s.lstrip()
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_partition(self, tracked_string):
        result = tracked_string.partition(" ")
        assert result == ("hello", " ", "world")
        assert all(isinstance(part, TrackedUserString) for part in result)
        assert "hello" in TrackedUserString.wrap_calls
        assert " " in TrackedUserString.wrap_calls
        assert "world" in TrackedUserString.wrap_calls

    def test_removeprefix(self, tracked_string):
        result = tracked_string.removeprefix("hello ")
        assert result == "world"
        assert isinstance(result, TrackedUserString)
        assert "world" in TrackedUserString.wrap_calls

    def test_removesuffix(self, tracked_string):
        result = tracked_string.removesuffix(" world")
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_replace(self, tracked_string):
        result = tracked_string.replace("world", "there")
        assert result == "hello there"
        assert isinstance(result, TrackedUserString)
        assert "hello there" in TrackedUserString.wrap_calls

    def test_rjust(self, tracked_string):
        s = TrackedUserString("hi")
        TrackedUserString.wrap_calls = []
        result = s.rjust(5)
        assert result == "   hi"
        assert isinstance(result, TrackedUserString)
        assert "   hi" in TrackedUserString.wrap_calls

    def test_rpartition(self, tracked_string):
        s = TrackedUserString("a-b-c")
        TrackedUserString.wrap_calls = []
        result = s.rpartition("-")
        assert result == ("a-b", "-", "c")
        assert all(isinstance(part, TrackedUserString) for part in result)
        assert "a-b" in TrackedUserString.wrap_calls
        assert "-" in TrackedUserString.wrap_calls
        assert "c" in TrackedUserString.wrap_calls

    def test_rsplit(self, tracked_string):
        result = tracked_string.rsplit(" ")
        assert result == ["hello", "world"]
        assert all(isinstance(part, TrackedUserString) for part in result)
        assert "hello" in TrackedUserString.wrap_calls
        assert "world" in TrackedUserString.wrap_calls

    def test_rstrip(self, tracked_string):
        s = TrackedUserString("hello  ")
        TrackedUserString.wrap_calls = []
        result = s.rstrip()
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_split(self, tracked_string):
        result = tracked_string.split(" ")
        assert result == ["hello", "world"]
        assert all(isinstance(part, TrackedUserString) for part in result)
        assert "hello" in TrackedUserString.wrap_calls
        assert "world" in TrackedUserString.wrap_calls

    def test_splitlines(self, tracked_string):
        s = TrackedUserString("line1\nline2\nline3")
        TrackedUserString.wrap_calls = []
        result = s.splitlines()
        assert result == ["line1", "line2", "line3"]
        assert all(isinstance(part, TrackedUserString) for part in result)
        assert "line1" in TrackedUserString.wrap_calls
        assert "line2" in TrackedUserString.wrap_calls
        assert "line3" in TrackedUserString.wrap_calls

    def test_strip(self, tracked_string):
        s = TrackedUserString("  hello  ")
        TrackedUserString.wrap_calls = []
        result = s.strip()
        assert result == "hello"
        assert isinstance(result, TrackedUserString)
        assert "hello" in TrackedUserString.wrap_calls

    def test_swapcase(self, tracked_string):
        s = TrackedUserString("HeLLo")
        TrackedUserString.wrap_calls = []
        result = s.swapcase()
        assert result == "hEllO"
        assert isinstance(result, TrackedUserString)
        assert "hEllO" in TrackedUserString.wrap_calls

    def test_title(self, tracked_string):
        result = tracked_string.title()
        assert result == "Hello World"
        assert isinstance(result, TrackedUserString)
        assert "Hello World" in TrackedUserString.wrap_calls

    def test_translate(self, tracked_string):
        s = TrackedUserString("abc")
        TrackedUserString.wrap_calls = []
        table = str.maketrans("abc", "xyz")
        result = s.translate(table)
        assert result == "xyz"
        assert isinstance(result, TrackedUserString)
        assert "xyz" in TrackedUserString.wrap_calls

    def test_upper(self, tracked_string):
        result = tracked_string.upper()
        assert result == "HELLO WORLD"
        assert isinstance(result, TrackedUserString)
        assert "HELLO WORLD" in TrackedUserString.wrap_calls

    def test_zfill(self, tracked_string):
        s = TrackedUserString("42")
        TrackedUserString.wrap_calls = []
        result = s.zfill(5)
        assert result == "00042"
        assert isinstance(result, TrackedUserString)
        assert "00042" in TrackedUserString.wrap_calls

    def test_string_methods_still_work(self):
        s = yuio.util.UserString("hello world")
        assert s.startswith("hello")
        assert s.endswith("world")
        assert s.find("world") == 6
        assert len(s) == 11

    def test_equality_with_str(self):
        s = yuio.util.UserString("hello")
        assert s == "hello"

    def test_hash_matches_str(self):
        s = yuio.util.UserString("hello")
        assert hash(s) == hash("hello")


class StatefulUserString(yuio.util.UserString):
    """A UserString with internal state to test _wrap preserves state."""

    __slots__ = ("_tag",)

    def __new__(cls, data: str, tag: str = "default"):
        instance = super().__new__(cls, data)
        instance._tag = tag
        return instance

    def _wrap(self, data: str):
        return StatefulUserString(data, self._tag)


class TestUserStringWithState:
    def test_state_preserved_through_operations(self):
        s = StatefulUserString("hello world", tag="custom")
        result = s.upper()
        assert result == "HELLO WORLD"
        assert isinstance(result, StatefulUserString)
        assert result._tag == "custom"

    def test_state_preserved_through_split(self):
        s = StatefulUserString("a-b-c", tag="mytag")
        parts = s.split("-")
        assert parts == ["a", "b", "c"]
        for part in parts:
            assert isinstance(part, StatefulUserString)
            assert part._tag == "mytag"

    def test_state_preserved_through_partition(self):
        s = StatefulUserString("hello world", tag="test")
        left, sep, right = s.partition(" ")
        assert left._tag == "test"
        assert sep._tag == "test"
        assert right._tag == "test"


@pytest.mark.parametrize(
    ("strings", "expected"),
    [
        (["ax", "bx"], ""),
        (["abc", "aby"], "ab"),
        (["foobar", "foobity", "foobaz"], "foob"),
    ],
)
def test_commonprefix(strings, expected):
    assert yuio.util.commonprefix(strings) == expected
