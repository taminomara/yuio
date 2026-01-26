import os.path
import pathlib

import pytest

import yuio.complete


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("", "", 0),
        ("foo", "FOO", 0),
        ("qux", "qax", 1),
        ("bacon", "beacon", 1),
        ("raeson", "reason", 1),
        ("ass", "add", 2),
        ("r/traaaaannnnnnns", "r/traaaaaaannnnnnnnnns", 5),
    ],
)
def test_corrections(a, b, expected):
    assert yuio.complete._corrections(a, b) == expected


class TestCollector:
    @pytest.mark.parametrize(
        ("text", "pos", "expected_prefix", "expected_suffix"),
        [
            ("foobar", 0, "", "foobar"),
            ("foobar", 3, "foo", "bar"),
            ("foobar", 6, "foobar", ""),
        ],
    )
    def test_init(self, text, pos, expected_prefix, expected_suffix):
        collector = yuio.complete.CompletionCollector(text, pos)
        assert collector.iprefix == ""
        assert collector.prefix == expected_prefix
        assert collector.suffix == expected_suffix
        assert collector.rsuffix == ""
        assert collector.isuffix == ""

    @pytest.mark.parametrize(
        ("iprefix", "prefix", "suffix", "isuffix", "completions"),
        [
            (
                "",
                "",
                "",
                "",
                {
                    "foo": ("", "foo", ""),
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                },
            ),
            (
                "",
                "ba",
                "",
                "",
                {
                    "foo": None,
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                },
            ),
            (
                "",
                "ba",
                "r",
                "",
                {
                    "foo": None,
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                },
            ),
            (
                "",
                "",
                "foo",
                "",
                {
                    "foo": ("", "foo", ""),
                    "bar": ("", "bar", ""),
                    "baz": ("", "baz", ""),
                },
            ),
            (
                "",
                "meh",
                "",
                "",
                {
                    "foo": None,
                    "bar": None,
                    "baz": None,
                },
            ),
            (
                "mew-",
                "",
                "",
                "-quack",
                {
                    "foo": ("mew-", "foo", "-quack"),
                    "bar": ("mew-", "bar", "-quack"),
                    "baz": ("mew-", "baz", "-quack"),
                },
            ),
            (
                "mew-",
                "ba",
                "r",
                "-quack",
                {
                    "foo": None,
                    "bar": ("mew-", "bar", "-quack"),
                    "baz": ("mew-", "baz", "-quack"),
                },
            ),
        ],
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
        expected = list(
            sorted([c for c in completions.values() if c], key=lambda x: x[1])
        )
        assert result == expected

    @pytest.mark.parametrize(
        ("iprefix", "prefix", "suffix", "isuffix", "completions", "expected"),
        [
            ("", "", "", "", ["bar", "baz"], ("", "ba", "")),
            ("", "b", "", "", ["foo", "bar", "baz"], ("", "ba", "")),
            ("", "b", "ar", "", ["foo", "bar", "baz"], ("", "ba", "")),
            (
                "meow-",
                "b",
                "",
                "-quack",
                ["foo", "bar", "baz"],
                ("meow-", "ba", "-quack"),
            ),
        ],
    )
    def test_common_prefix(
        self, iprefix, prefix, suffix, isuffix, completions, expected
    ):
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


class TestCorrectingCollector:
    @pytest.mark.parametrize(
        ("text", "pos", "expected_prefix", "expected_suffix"),
        [
            ("foobar", 0, "", "foobar"),
            ("foobar", 3, "foo", "bar"),
            ("foobar", 6, "foobar", ""),
        ],
    )
    def test_init(self, text, pos, expected_prefix, expected_suffix):
        collector = yuio.complete._CorrectingCollector(text, pos)
        assert collector.iprefix == ""
        assert collector.prefix == expected_prefix
        assert collector.suffix == expected_suffix
        assert collector.rsuffix == ""
        assert collector.isuffix == ""

    @pytest.mark.parametrize(
        ("iprefix", "prefix", "suffix", "isuffix", "completions"),
        [
            (
                "",
                "abc",
                "",
                "",
                {
                    "abx": ("", "abx", "", None),
                    "foobar": None,
                },
            ),
            (
                "",
                "abc",
                "",
                "",
                {
                    "abx": ("", "abx", "", None),
                    "abxy": ("", "abxy", "", "corrected"),
                    "foobar": None,
                    None: ("", "abc", "", "original"),
                },
            ),
        ],
    )
    def test_add(self, iprefix, prefix, suffix, isuffix, completions):
        collector = yuio.complete._CorrectingCollector("", 0)
        collector.iprefix = iprefix
        collector.prefix = prefix
        collector.suffix = suffix
        collector.isuffix = isuffix

        for c in completions.keys():
            if c:
                collector.add(c)

        result = [
            (c.iprefix, c.completion, c.isuffix, c.comment)
            for c in collector.finalize()
        ]
        expected = [c for c in completions.values() if c]
        assert result == expected


def _get_completions(l: list[yuio.complete.Completion]):
    return [
        (
            c.iprefix,
            c.completion,
            c.isuffix,
            c.rsuffix,
            c.rsymbols,
            c.dprefix,
            c.dsuffix,
            c.comment,
        )
        for c in l
    ]


def test_empty():
    completer = yuio.complete.Empty()

    assert completer.complete("", 0) == []
    assert completer.complete("foo", 1) == []


def test_choice():
    completer = yuio.complete.Choice(
        [
            yuio.complete.Option("foo"),
            yuio.complete.Option("bar"),
            yuio.complete.Option("baz", comment="comment"),
        ]
    )

    assert _get_completions(completer.complete("", 0)) == [
        ("", "bar", "", "", "", "", "", None),
        ("", "baz", "", "", "", "", "", "comment"),
        ("", "foo", "", "", "", "", "", None),
    ]

    assert _get_completions(completer.complete("ba", 2)) == [
        ("", "bar", "", "", "", "", "", None),
        ("", "baz", "", "", "", "", "", "comment"),
    ]


def test_list():
    completer = yuio.complete.List(
        yuio.complete.Choice(
            [
                yuio.complete.Option("foo"),
                yuio.complete.Option("bar"),
                yuio.complete.Option("baz", comment="comment"),
            ]
        )
    )

    assert _get_completions(completer.complete("", 0)) == [
        ("", "bar", "", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("", "baz", "", " ", " \t\n\r\x0b\x0c", "", "", "comment"),
        ("", "foo", "", " ", " \t\n\r\x0b\x0c", "", "", None),
    ]

    assert _get_completions(completer.complete("ba", 2)) == [
        ("", "bar", "", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("", "baz", "", " ", " \t\n\r\x0b\x0c", "", "", "comment"),
    ]

    assert _get_completions(completer.complete("bat", 3)) == [
        ("", "bar", "", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("", "baz", "", " ", " \t\n\r\x0b\x0c", "", "", "comment"),
    ]

    assert _get_completions(completer.complete("qux ba duo", 6)) == [
        ("qux ", "bar", " duo", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("qux ", "baz", " duo", " ", " \t\n\r\x0b\x0c", "", "", "comment"),
    ]

    assert _get_completions(completer.complete("foo  bar", 4)) == [
        ("foo ", "baz", " bar", " ", " \t\n\r\x0b\x0c", "", "", "comment"),
    ]

    completer = yuio.complete.List(
        yuio.complete.Choice(
            [
                yuio.complete.Option("foo"),
                yuio.complete.Option("bar"),
                yuio.complete.Option("baz", comment="comment"),
            ]
        ),
        allow_duplicates=True,
    )

    assert _get_completions(completer.complete("foo  bar", 4)) == [
        ("foo ", "bar", " bar", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("foo ", "baz", " bar", " ", " \t\n\r\x0b\x0c", "", "", "comment"),
        ("foo ", "foo", " bar", " ", " \t\n\r\x0b\x0c", "", "", None),
    ]

    completer = yuio.complete.List(
        yuio.complete.Choice(
            [
                yuio.complete.Option("foo"),
                yuio.complete.Option("bar"),
                yuio.complete.Option("baz", comment="comment"),
            ]
        ),
        delimiter=",",
    )

    assert _get_completions(completer.complete("", 0)) == [
        ("", "bar", "", ",", ",", "", "", None),
        ("", "baz", "", ",", ",", "", "", "comment"),
        ("", "foo", "", ",", ",", "", "", None),
    ]

    assert _get_completions(completer.complete("qux,ba,duo", 6)) == [
        ("qux,", "bar", ",duo", "", "", "", "", None),
        ("qux,", "baz", ",duo", "", "", "", "", "comment"),
    ]

    assert _get_completions(completer.complete("qux,ba", 6)) == [
        ("qux,", "bar", "", ",", ",", "", "", None),
        ("qux,", "baz", "", ",", ",", "", "", "comment"),
    ]


def test_tuple():
    completer = yuio.complete.Tuple(
        yuio.complete.Choice(
            [
                yuio.complete.Option("foo"),
                yuio.complete.Option("bar"),
            ]
        ),
        yuio.complete.Choice(
            [
                yuio.complete.Option("qux"),
                yuio.complete.Option("duo"),
            ]
        ),
    )

    assert _get_completions(completer.complete("", 0)) == [
        ("", "bar", "", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("", "foo", "", " ", " \t\n\r\x0b\x0c", "", "", None),
    ]

    assert _get_completions(completer.complete("  ", 2)) == [
        ("  ", "bar", "", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("  ", "foo", "", " ", " \t\n\r\x0b\x0c", "", "", None),
    ]

    assert _get_completions(completer.complete("x ", 2)) == [
        ("x ", "duo", "", " ", " \t\n\r\x0b\x0c", "", "", None),
        ("x ", "qux", "", " ", " \t\n\r\x0b\x0c", "", "", None),
    ]

    assert _get_completions(completer.complete("x y ", 4)) == []


def _get_file_completions(base: str, l: list[yuio.complete.Completion]):
    return list(
        sorted(
            [
                (
                    c.iprefix.replace(base, "__base__"),
                    c.completion.replace(base, "__base__"),
                    c.isuffix.replace(base, "__base__"),
                    c.rsuffix,
                    c.rsymbols,
                    c.dprefix,
                    c.dsuffix,
                    c.comment,
                )
                for c in l
            ]
        )
    )


def test_file(tmpdir):
    root = pathlib.Path(tmpdir)
    root.joinpath("foo.toml").touch()
    root.joinpath("bar.cfg").touch()
    root.joinpath("dir1").mkdir()
    root.joinpath("dir2").mkdir()

    if os.name == "nt":
        root.joinpath("baz.cfg").touch()
        symlink_suffix = ""
    else:
        root.joinpath("baz.cfg").symlink_to(root / "bar.cfg")
        symlink_suffix = "@"

    completer = yuio.complete.File()

    base = str(root) + os.path.sep

    assert _get_file_completions(base, completer.complete(base, len(base))) == [
        ("__base__", "bar.cfg", "", "", "", "", "", None),
        ("__base__", "baz.cfg", "", "", "", "", symlink_suffix, None),
        ("__base__", "dir1" + os.path.sep, "", "", "", "", "", None),
        ("__base__", "dir2" + os.path.sep, "", "", "", "", "", None),
        ("__base__", "foo.toml", "", "", "", "", "", None),
    ]

    assert _get_file_completions(
        base, completer.complete(base + "ba", len(base) + 2)
    ) == [
        ("__base__", "bar.cfg", "", "", "", "", "", None),
        ("__base__", "baz.cfg", "", "", "", "", symlink_suffix, None),
    ]

    completer = yuio.complete.File(extensions=[".toml"])
    assert _get_file_completions(base, completer.complete(base, len(base))) == [
        ("__base__", "dir1" + os.path.sep, "", "", "", "", "", None),
        ("__base__", "dir2" + os.path.sep, "", "", "", "", "", None),
        ("__base__", "foo.toml", "", "", "", "", "", None),
    ]

    completer = yuio.complete.List(yuio.complete.File(), delimiter=";")
    assert _get_file_completions(base, completer.complete(base, len(base))) == [
        ("__base__", "bar.cfg", "", ";", ";", "", "", None),
        ("__base__", "baz.cfg", "", ";", ";", "", symlink_suffix, None),
        ("__base__", "dir1" + os.path.sep, "", "", ";", "", "", None),
        ("__base__", "dir2" + os.path.sep, "", "", ";", "", "", None),
        ("__base__", "foo.toml", "", ";", ";", "", "", None),
    ]

    assert _get_file_completions(
        base, completer.complete(base + ";xyz", len(base))
    ) == [
        ("__base__", "bar.cfg", ";xyz", "", "", "", "", None),
        ("__base__", "baz.cfg", ";xyz", "", "", "", symlink_suffix, None),
        ("__base__", "dir1" + os.path.sep, ";xyz", "", "", "", "", None),
        ("__base__", "dir2" + os.path.sep, ";xyz", "", "", "", "", None),
        ("__base__", "foo.toml", ";xyz", "", "", "", "", None),
    ]

    completer = yuio.complete.Dir()
    assert _get_file_completions(
        base, completer.complete(base + "dir", len(base) + 3)
    ) == [
        ("__base__", "dir1" + os.path.sep, "", "", "", "", "", None),
        ("__base__", "dir2" + os.path.sep, "", "", "", "", "", None),
    ]

    assert _get_file_completions(
        base, completer.complete(base + ".", len(base) + 1)
    ) == [
        ("__base__", ".." + os.path.sep, "", "", "", "", "", None),
        ("__base__", "." + os.path.sep, "", "", "", "", "", None),
    ]

    assert ("", "~" + os.path.sep, "", "", "", "", "", None) in _get_file_completions(
        base, completer.complete("~", 1)
    )
