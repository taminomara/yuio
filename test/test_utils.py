import pytest

import yuio


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
    assert yuio.to_dash_case(given) == expected


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

    #: Merged 1.
    merged = None
    """Ignored."""

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
                "BAR": "doc\nfor\nbar",
                "baz": "doc for baz",
                "consecutive_docstrings": "docs for consecutive_docstrings",
                "docstring": "doc for docstring",
                "docstring_separate": "doc for docstring_separate",
                "docstring_separate_2": "doc for docstring_separate_2",
                "foo": "doc for foo",
                "merged": "merged 1",
                "split": "split 2",
            },
        ),
        (docs_fn_empty, {}),
        (docs_fn, {"duo": "doc\nfor\nduo", "foo": "doc foo"}),
        ([], {}),
        (local_cls(), {}),
        (object, {}),
    ],
)
def test_find_docs(obj, expected):
    assert yuio._find_docs(obj) == expected


@pytest.mark.parametrize(
    ("doc", "expected"),
    [
        ("Simple doc.", "simple doc"),
        ("HTTP header.", "HTTP header"),
        ("something...", "something..."),
        ("A beautiful string", "a beautiful string"),
        ("A.2", "A.2"),
        ("Paragraph 1\nline 2\n\nparagraph 2", "paragraph 1\nline 2"),
        ("some :class:`Foo.bar` method", "some `Foo.bar` method"),
        ("some `Foo.bar`:class: method", "some `Foo.bar` method"),
        ("some :py:some-role:`title <Foo.bar>` method", "some `title` method"),
        ("`rst link`_", "`rst link`"),
        ("`rst link`__", "`rst link`"),
        ("`~Foo.bar.baz`", "`~Foo.bar.baz`"),
        ("``~Foo.bar.baz``", "``~Foo.bar.baz``"),
        (":class:`~Foo.bar.baz`", "`baz`"),
        ("`~Foo.bar.baz`:class:", "`baz`"),
        ("`literal \\` with \\` backticks`", "`` literal ` with ` backticks ``"),
        ("`literal \\`\\`with\\`\\` backticks`", "``` literal ``with`` backticks ```"),
        ("`literal\\\nwith\\\nnewline`", "`literal with newline`"),
    ],
)
def test_process_docstring(doc, expected):
    assert yuio._process_docstring(doc) == expected


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
    assert yuio.dedent(doc) == expected
