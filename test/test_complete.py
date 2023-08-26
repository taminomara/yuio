import os.path
import pytest

import yuio.complete


@pytest.mark.parametrize(
    'strings,expected',
    [
        (['ax', 'bx'], ''),
        (['abc', 'aby'], 'ab'),
        (['foobar', 'foobity', 'foobaz'], 'foob'),
    ]
)
def test_commonprefix(strings, expected):
    assert yuio._commonprefix(strings) == expected


@pytest.mark.parametrize(
    'a,b,expected',
    [
        ('', '', 0),
        ('foo', 'FOO', 0),
        ('qux', 'qax', 1),
        ('bacon', 'beacon', 1),
        ('raeson', 'reason', 1),
        ('ass', 'add', 2),
        ('r/traaaaannnnnnns', 'r/traaaaaaannnnnnnnnns', 5),
    ]
)
def test_corrections(a, b, expected):
    assert yuio.complete._corrections(a, b) == expected


class TestCollector:
    @pytest.mark.parametrize(
        'text,pos,expected_prefix,expected_suffix',
        [
            ("foobar", 0, "", "foobar"),
            ("foobar", 3, "foo", "bar"),
            ("foobar", 6, "foobar", ""),
        ]
    )
    def test_init(self, text, pos, expected_prefix, expected_suffix):
        collector = yuio.complete.CompletionCollector(text, pos)
        assert collector.iprefix == ''
        assert collector.prefix == expected_prefix
        assert collector.suffix == expected_suffix
        assert collector.rsuffix == ''
        assert collector.isuffix == ''

    @pytest.mark.parametrize(
        'iprefix,prefix,suffix,isuffix,completions',
        [
            (
                "", "", "", "",
                {
                    "foo": ("", "foo", ""),
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                }
            ),
            (
                "", "ba", "", "",
                {
                    "foo": None,
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                }
            ),
            (
                "", "ba", "r", "",
                {
                    "foo": None,
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                }
            ),
            (
                "", "", "foo", "",
                {
                    "foo": ("", "foo", ""),
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                }
            ),
            (
                "", "meh", "", "",
                {
                    "foo": None,
                    "bar": None,
                    "baz": None,
                }
            ),
            (
                "mew-", "", "", "-quack",
                {
                    "foo": ("mew-", "foo", "-quack"),
                    "bar": ("mew-", "bar", "-quack"),
                    "baz": ("mew-", "baz", "-quack"),
                }
            ),
            (
                "mew-", "ba", "r", "-quack",
                {
                    "foo": None,
                    "bar": ("mew-", "bar", "-quack"),
                    "baz": ("mew-", "baz", "-quack"),
                }
            ),
        ]
    )
    def test_add(self, iprefix, prefix, suffix, isuffix, completions):
        collector = yuio.complete.CompletionCollector("", 0)
        collector.iprefix = iprefix
        collector.prefix = prefix
        collector.suffix = suffix
        collector.isuffix = isuffix

        for c in completions.keys():
            collector.add(c)

        result = [(c.iprefix, c.completion, c.isuffix) for c in collector.finalize()]
        expected = list(sorted([c for c in completions.values() if c], key=lambda x: x[1]))
        assert result == expected

    @pytest.mark.parametrize(
        'iprefix,prefix,suffix,isuffix,completions,expected',
        [
            ("", "", "", "", ["bar", "baz"], ("", "ba", "")),
            ("", "b", "", "", ["foo", "bar", "baz"], ("", "ba", "")),
            ("", "b", "ar", "", ["foo", "bar", "baz"], ("", "ba", "")),
            ("meow-", "b", "", "-quack", ["foo", "bar", "baz"], ("meow-", "ba", "-quack")),
        ]
    )
    def test_common_prefix(self, iprefix, prefix, suffix, isuffix, completions, expected):
        collector = yuio.complete.CompletionCollector("", 0)
        collector.iprefix = iprefix
        collector.prefix = prefix
        collector.suffix = suffix
        collector.isuffix = isuffix

        for c in completions:
            collector.add(c)

        result = [(c.iprefix, c.completion, c.isuffix) for c in collector.finalize()]
        assert result == [expected]

    def test_common_prefix_different_isuffix_iprefix(self):
        collector = yuio.complete.CompletionCollector("", 0)

        collector.add("foo")

        with collector.save_state():
            collector.iprefix = "a"
            collector.add("foo")

        with collector.save_state():
            collector.isuffix = "a"
            collector.add("foo")

        with collector.save_state():
            collector.iprefix = "a"
            collector.isuffix = "a"
            collector.add("foo")

        result = [(c.iprefix, c.completion, c.isuffix) for c in collector.finalize()]
        assert result == [
            ("", "foo", ""),
            ("a", "foo", ""),
            ("", "foo", "a"),
            ("a", "foo", "a"),
        ]

    def test_groups(self):
        collector = yuio.complete.CompletionCollector("", 0)

        collector.add("b1")
        collector.add("c1")
        collector.add("a1")

        collector.add_group()

        collector.add("c2")
        collector.add("a2")

        collector.add_group(color_tag="yellow")

        collector.add("b3")
        collector.add("x3")
        collector.add("a3")

        collector.add_group(sorted=False)

        collector.add("b4")
        collector.add("c4")
        collector.add("a4")

        result = [(c.completion, c.group_color_tag) for c in collector.finalize()]
        assert result == [
            ("a1", None),
            ("b1", None),
            ("c1", None),

            ("a2", None),
            ("c2", None),

            ("a3", "yellow"),
            ("b3", "yellow"),
            ("x3", "yellow"),

            ("b4", None),
            ("c4", None),
            ("a4", None),
        ]
