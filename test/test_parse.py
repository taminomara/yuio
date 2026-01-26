import datetime
import enum
import math
import os.path
import pathlib
import re
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

import jsonschema
import pytest

import yuio.json_schema
import yuio.parse
import yuio.secret
import yuio.widget

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


class TestStrParsingContext:
    @pytest.mark.parametrize(
        ("s", "delim", "expected", "maxsplit"),
        [
            ("", None, [], -1),
            ("", ",", [("", 0, 0)], -1),
            ("asd", None, [("asd", 0, 3)], -1),
            ("asd dsa", None, [("asd", 0, 3), ("dsa", 4, 7)], -1),
            ("  asd  dsa  ", None, [("asd", 2, 5), ("dsa", 7, 10)], -1),
            ("asd  dsa  ", None, [("asd", 0, 3), ("dsa", 5, 8)], -1),
            ("  asd  dsa", None, [("asd", 2, 5), ("dsa", 7, 10)], -1),
            ("asd", None, [("asd", 0, 3)], 0),
            ("asd  ", None, [("asd  ", 0, 5)], 0),
            ("  asd", None, [("asd", 2, 5)], 0),
            ("  asd  ", None, [("asd  ", 2, 7)], 0),
            ("  asd", None, [("asd", 2, 5)], 1),
            ("asd  ", None, [("asd", 0, 3)], 1),
            ("  asd  ", None, [("asd", 2, 5)], 1),
            ("  asd  dsa   ", None, [("asd", 2, 5), ("dsa   ", 7, 13)], 1),
            ("  asd  dsa", None, [("asd", 2, 5), ("dsa", 7, 10)], 2),
            ("a,b,c", ",", [("a,b,c", 0, 5)], 0),
            ("a,b,c", ",", [("a", 0, 1), ("b,c", 2, 5)], 1),
            ("a,b,c", ",", [("a", 0, 1), ("b", 2, 3), ("c", 4, 5)], -1),
            (
                ",a,,b,",
                ",",
                [("", 0, 0), ("a", 1, 2), ("", 3, 3), ("b", 4, 5), ("", 6, 6)],
                -1,
            ),
        ],
    )
    def test_split(self, s, delim, expected, maxsplit):
        ctx = yuio.parse.StrParsingContext(s)

        results = [
            (ctx.value, ctx.start, ctx.end)
            for ctx in ctx.split(delim, maxsplit=maxsplit)
        ]
        assert results == expected

        raw_results = [res[0] for res in results]
        assert raw_results == s.split(delim, maxsplit=maxsplit), (
            "should match built-in str.split"
        )

    @pytest.mark.parametrize(
        ("s", "chars", "expected"),
        [
            ("", None, ("", 0, 0)),
            ("asd", None, ("asd", 0, 3)),
            (" asd ", None, ("asd", 1, 4)),
            ("\n\tasd  ", None, ("asd", 2, 5)),
            ("   ", None, ("", 3, 3)),
            ("", ".,", ("", 0, 0)),
            ("asd", ".,", ("asd", 0, 3)),
            (".,.asd.,.", ".,", ("asd", 3, 6)),
            (".,.", ".,", ("", 3, 3)),
        ],
    )
    def test_strip(self, s, chars, expected):
        ctx = yuio.parse.StrParsingContext(s)
        strip = ctx.strip(chars)
        result = (strip.value, strip.start, strip.end)
        assert result == expected
        assert strip.value == ctx.value.strip(chars)

    @pytest.mark.parametrize(
        ("s", "expected"),
        [
            ("", ("", 0, 0)),
            ("asd", ("asd", 0, 3)),
            (" asd ", ("asd", 1, 4)),
            ("\n\tasd  ", ("asd", 2, 5)),
            ("   ", ("   ", 0, 3)),
        ],
    )
    def test_strip_if_not_spaces(self, s, expected):
        ctx = yuio.parse.StrParsingContext(s)
        strip = ctx.strip_if_non_space()
        result = (strip.value, strip.start, strip.end)
        assert result == expected


class TestConfigParsingContext:
    def test_descend(self):
        ctx = yuio.parse.ConfigParsingContext(1)

        assert ctx.value == 1
        assert ctx.key is None
        assert ctx.desc is None
        assert ctx.parent is None

        ctx2 = ctx.descend(2, "k2", "d2")

        assert ctx2.value == 2
        assert ctx2.key == "k2"
        assert ctx2.desc == "d2"
        assert ctx2.parent is ctx

    def test_make_path(self):
        ctx = yuio.parse.ConfigParsingContext(1)

        assert ctx.make_path() == []
        ctx2 = ctx.descend(2, "k2", "d2")
        assert ctx2.make_path() == [("k2", "d2")]
        ctx3 = ctx2.descend(3, "k3")
        assert ctx3.make_path() == [("k2", "d2"), ("k3", None)]
        ctx4 = ctx3.descend(3, "k4")
        assert ctx4.make_path() == [("k2", "d2"), ("k3", None), ("k4", None)]


@pytest.mark.parametrize(
    ("s", "pos", "expected_s", "expected_pos"),
    [
        ("", (0, 0), '""', (1, 1)),
        ("asd", (0, 0), '"asd"', (1, 1)),
        ("asd", (0, 3), '"asd"', (1, 4)),
        ("asd", (3, 3), '"asd"', (4, 4)),
        ("asd\ndsa", (0, 3), '"asd\\ndsa"', (1, 4)),
        ("asd\ndsa", (0, 4), '"asd\\ndsa"', (1, 6)),
        ("asd\ndsa", (4, 6), '"asd\\ndsa"', (6, 8)),
    ],
)
def test_repr_and_adjust_pos(s, pos, expected_s, expected_pos):
    s2, pos2 = yuio.parse._repr_and_adjust_pos(s, pos)
    assert s2 == expected_s
    assert pos2 == expected_pos


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ([], ""),
        ([("foo", None)], "$.foo"),
        ([("_foo", None)], "$._foo"),
        ([("-foo", None)], "$['-foo']"),
        ([("foo", None), ("bar", None)], "$.foo.bar"),
        ([("foo", None), (10, None)], "$.foo[10]"),
        ([("f\no", None), (10, None)], "$['f\\no'][10]"),
        ([("foo", "desc")], "desc"),
        ([("foo", "desc %(key)s")], "desc foo"),
        ([("foo", "desc %(key)r")], "desc 'foo'"),
        ([("x", None), ("foo", "desc %(key)r")], "$.x, desc 'foo'"),
        ([(10, None), ("foo", "desc %(key)r")], "$[10], desc 'foo'"),
        ([("foo", "desc %(key)r"), ("x", None)], "$.<desc 'foo'>.x"),
    ],
)
def test_path_renderer(path, expected, ctx):
    assert str(ctx.str(yuio.parse._PathRenderer(path))) == expected


@pytest.mark.parametrize(("as_cli"), [True, False])
@pytest.mark.parametrize(
    ("code", "pos", "a", "b"),
    [
        (
            "code",
            (0, 4),
            "> code",
            "  ~~~~",
        ),
        (
            "code",
            (2, 3),
            "> code",
            "    ~",
        ),
        (
            "some very long code very long indeed",
            (0, 36),
            "> some very long ...",
            "  ~~~~~~~~~~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (15, 36),
            "> ...code very lo...",
            "     ~~~~~~~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (3, 36),
            "> some very long ...",
            "     ~~~~~~~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (0, 9),
            "> some very long ...",
            "  ~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (3, 12),
            "> some very long ...",
            "     ~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (5, 17),
            "> ...very long co...",
            "     ~~~~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (25, 36),
            "> ...ery long indeed",
            "         ~~~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (5, 14),
            "> some very long ...",
            "       ~~~~~~~~~",
        ),
        (
            "some very long code very long indeed",
            (25, 33),
            "> ...ery long indeed",
            "         ~~~~~~~~",
        ),
        (
            "some very long code",
            (5, 9),
            "> some very long ...",
            "       ~~~~",
        ),
    ],
)
def test_code_renderer(code, pos, a, b, as_cli, ctx):
    if as_cli:
        a = "$ " + a[2:]
    col = ctx.str(yuio.parse._CodeRenderer(code, pos, as_cli=as_cli))
    assert str(col) == a + "\n" + b


class TestErrorMessages:
    def test_code(self):
        parser = yuio.parse.List(yuio.parse.Int())
        with pytest.raises(
            yuio.parse.ParsingError,
            match=re.escape("> \"10 xx 30\"\n      ~~\nCan't parse 'xx' as int"),
        ):
            parser.parse("10 xx 30")

    def test_path(self):
        parser = yuio.parse.List(yuio.parse.Int())
        with pytest.raises(
            yuio.parse.ParsingError,
            match=re.escape("In $[1]:\n  Expected int, got str: '20'"),
        ):
            parser.parse_config([10, "20", 30])


class TestStr:
    def test_basics(self):
        parser = yuio.parse.Str()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<str>"
        assert parser.describe_many() == "<str>"
        assert parser.describe_value("foo") == "foo"

    def test_json_schema(self):
        parser = yuio.parse.Str()
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.String()
        )
        assert parser.to_json_value("asd") == "asd"

    def test_parse(self):
        parser = yuio.parse.Str()
        assert parser.parse("Test") == "Test"
        assert parser.parse(" Test ") == " Test "
        assert parser.parse_config("Test") == "Test"
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_lower(self):
        parser = yuio.parse.Lower(yuio.parse.Str())
        assert parser.parse("Test") == "test"
        assert parser.parse("Test") == "test"
        assert parser.parse("ῼ") == "ῳ"
        assert parser.parse_config("Test") == "test"
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_casefold(self):
        parser = yuio.parse.CaseFold(yuio.parse.Str())
        assert parser.parse("Test") == "test"
        assert parser.parse("Test") == "test"
        assert parser.parse("ῼ") == "ωι"
        assert parser.parse_config("Test") == "test"
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_upper(self):
        parser = yuio.parse.Upper(yuio.parse.Str())
        assert parser.parse("Test") == "TEST"
        assert parser.parse("Test") == "TEST"
        assert parser.parse_config("Test") == "TEST"
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_strip(self):
        parser = yuio.parse.Strip(yuio.parse.Str())
        assert parser.parse("Test  ") == "Test"
        assert parser.parse("  Test") == "Test"
        assert parser.parse_config("  Test  ") == "Test"
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_regex(self):
        parser = yuio.parse.Regex(yuio.parse.Str(), r"^a|b$")
        assert parser.parse("a") == "a"
        assert parser.parse("b") == "b"
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Value doesn't match regex \^a\|b\$"
        ):
            parser.parse("foo")

    def test_regex_compiled(self):
        parser = yuio.parse.Regex(yuio.parse.Str(), re.compile(r"^a|b$"))
        assert parser.parse("a") == "a"
        assert parser.parse("b") == "b"
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Value doesn't match regex \^a\|b\$"
        ):
            parser.parse("foo")

    def test_many(self):
        parser = yuio.parse.Str()
        with pytest.raises(RuntimeError, match=r"unable to parse multiple values"):
            parser.parse_many([])

    def test_from_type_hint(self):
        parser = yuio.parse.from_type_hint(str)
        assert parser.parse("Test") == "Test"

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[str, yuio.parse.Str()])
        assert parser.parse("  Test  ") == "  Test  "

    def test_from_type_hint_annotated_strip(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[str, yuio.parse.Str(), yuio.parse.Strip()]
        )
        assert parser.parse("  Test  ") == "Test"

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Str conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Str()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Str will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[str, yuio.parse.Str(), yuio.parse.Str()]
            )


class TestInt:
    def test_basics(self):
        parser = yuio.parse.Int()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(10) == "10"

    def test_json_schema(self):
        parser = yuio.parse.Int()
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Integer()
        )
        assert parser.to_json_value(10) == 10

    def test_parse(self):
        parser = yuio.parse.Int()
        assert parser.parse("1") == 1
        assert parser.parse("0x10") == 16
        assert parser.parse("0o10") == 8
        assert parser.parse("0b10") == 2
        assert parser.parse("-1") == -1
        assert parser.parse("-0x10") == -16
        assert parser.parse("-0o10") == -8
        assert parser.parse("-0b10") == -2
        assert parser.parse("  -  1  ") == -1
        assert parser.parse("  -  0x10  ") == -16
        assert parser.parse("  -  0o10  ") == -8
        assert parser.parse("  -  0b10  ") == -2
        assert parser.parse_config(1) == 1
        assert parser.parse_config(1.0) == 1
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("x")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("0x-10")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("0x 10")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("--10")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected int"):
            parser.parse_config(1.5)
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected int"):
            parser.parse_config("x")

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(int), yuio.parse.Int)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Int()])
        assert parser.parse("1") == 1

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating str with Int conflicts with default "
                "parser for this type, which is Str."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[str, yuio.parse.Int()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Int will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Int(), yuio.parse.Int()]
            )


class TestFloat:
    def test_basics(self):
        parser = yuio.parse.Float()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<float>"
        assert parser.describe_many() == "<float>"
        assert parser.describe_value(10.5) == "10.5"

    def test_json_schema(self):
        parser = yuio.parse.Float()
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Number()
        )
        assert parser.to_json_value(10.5) == 10.5

    def test_parse(self):
        parser = yuio.parse.Float()
        assert parser.parse("1.5") == 1.5
        assert parser.parse("-10") == -10.0
        assert parser.parse("2e9") == 2e9
        assert parser.parse_config(1.0) == 1.0
        assert parser.parse_config(1.5) == 1.5
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("x")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected float"):
            parser.parse_config("x")

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(float), yuio.parse.Float)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[float, yuio.parse.Float()])
        assert parser.parse("1.5") == 1.5

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Float conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Float()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Float will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[float, yuio.parse.Float(), yuio.parse.Float()]
            )


class TestBool:
    def test_basics(self):
        parser = yuio.parse.Bool()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "{yes|no}"
        assert parser.describe_or_def() == "{yes|no}"
        assert parser.describe_many() == "{yes|no}"
        assert parser.describe_value(True) == "yes"
        assert parser.describe_value(False) == "no"

    def test_json_schema(self):
        parser = yuio.parse.Bool()
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Boolean()
        )
        assert parser.to_json_value(True)

    def test_parse(self):
        parser = yuio.parse.Bool()
        assert parser.parse("y") is True
        assert parser.parse("yes") is True
        assert parser.parse("yEs") is True
        assert parser.parse("n") is False
        assert parser.parse("no") is False
        assert parser.parse("nO") is False
        with pytest.raises(yuio.parse.ParsingError, match=r"yes, no, true, or false"):
            parser.parse("Meh")
        assert parser.parse_config(True) is True
        assert parser.parse_config(False) is False
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected bool"):
            parser.parse_config("x")

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(bool), yuio.parse.Bool)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[bool, yuio.parse.Bool()])
        assert parser.parse("yes") is True

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Bool conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Bool()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Bool will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[bool, yuio.parse.Bool(), yuio.parse.Bool()]
            )


class TestEnum:
    class Cuteness(enum.Enum):
        #: Cats!
        CATS = "Cats"
        #: Dogs!
        DOGS = "Dogs"
        #: Sharkie!
        BLAHAJ = ":3"

    class CutenessInline(enum.Enum):
        __yuio_doc_inline__ = True

        #: Cats!
        CATS = "Cats"
        #: Dogs!
        DOGS = "Dogs"
        #: Sharkie!
        BLAHAJ = ":3"

    class Colors(enum.IntEnum):
        RED = 31
        GREEN = 32
        BLUE = 34

    class ColorsByName(enum.IntEnum):
        __yuio_by_name__ = True

        RED = 31
        GREEN = 32
        BLUE = 34

    class LongComments(enum.IntEnum):
        #: Long comment
        #: that spans multiple lines.
        LONG = 1
        #: Longer comment
        #: that spans multiple lines...
        #:
        #: And has a second paragraph.
        LONGER = 2

    def test_basics_by_value(self):
        parser = yuio.parse.Enum(self.Cuteness)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() == [
            yuio.widget.Option(
                value=self.Cuteness.CATS,
                display_text="Cats",
                display_text_prefix="",
                display_text_suffix="",
                comment="Cats!",
                color_tag="none",
            ),
            yuio.widget.Option(
                value=self.Cuteness.DOGS,
                display_text="Dogs",
                display_text_prefix="",
                display_text_suffix="",
                comment="Dogs!",
                color_tag="none",
            ),
            yuio.widget.Option(
                value=self.Cuteness.BLAHAJ,
                display_text=":3",
                display_text_prefix="",
                display_text_suffix="",
                comment="Sharkie!",
                color_tag="none",
            ),
        ]
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "{Cats|Dogs|:3}"
        assert parser.describe_or_def() == "{Cats|Dogs|:3}"
        assert parser.describe_many() == "{Cats|Dogs|:3}"
        assert parser.describe_value(self.Cuteness.BLAHAJ) == ":3"

    def test_basics_by_name(self):
        parser = yuio.parse.Enum(self.Cuteness, by_name=True)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "{CATS|DOGS|BLAHAJ}"
        assert parser.describe_or_def() == "{CATS|DOGS|BLAHAJ}"
        assert parser.describe_many() == "{CATS|DOGS|BLAHAJ}"
        assert parser.describe_value(self.Cuteness.BLAHAJ) == "BLAHAJ"

    def test_json_schema_by_value(self):
        parser = yuio.parse.Enum(self.Cuteness)
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref(
            "#/$defs/test.test_parse.TestEnum.Cuteness",
            "test.test_parse.TestEnum.Cuteness",
        )
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate("Cats")
        validator.validate("Dogs")
        validator.validate(":3")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("DOGS")
        assert parser.to_json_value(self.Cuteness.BLAHAJ) == ":3"

    def test_json_schema_by_name(self):
        parser = yuio.parse.Enum(self.Cuteness, by_name=True)
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref(
            "#/$defs/test.test_parse.TestEnum.Cuteness",
            "test.test_parse.TestEnum.Cuteness",
        )
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate("CATS")
        validator.validate("DOGS")
        validator.validate("BLAHAJ")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("Dogs")
        assert parser.to_json_value(self.Cuteness.BLAHAJ) == "BLAHAJ"

    def test_json_schema_name_clash(self):
        ctx = yuio.json_schema.JsonSchemaContext()
        parser = yuio.parse.Enum(self.Cuteness)
        assert parser.to_json_schema(ctx) == yuio.json_schema.Ref(
            "#/$defs/test.test_parse.TestEnum.Cuteness",
            "test.test_parse.TestEnum.Cuteness",
        )

        parser = yuio.parse.Enum(self.Cuteness, by_name=True)
        assert parser.to_json_schema(ctx) == yuio.json_schema.Ref(
            "#/$defs/test.test_parse.TestEnum.Cuteness2",
            "test.test_parse.TestEnum.Cuteness2",
        )

        parser = yuio.parse.Enum(self.Cuteness, to_dash_case=True)
        assert parser.to_json_schema(ctx) == yuio.json_schema.Ref(
            "#/$defs/test.test_parse.TestEnum.Cuteness3",
            "test.test_parse.TestEnum.Cuteness3",
        )

        parser = yuio.parse.Enum(self.Cuteness)
        assert parser.to_json_schema(ctx) == yuio.json_schema.Ref(
            "#/$defs/test.test_parse.TestEnum.Cuteness",
            "test.test_parse.TestEnum.Cuteness",
        )

    def test_json_schema_inline(self):
        parser = yuio.parse.Enum(self.Cuteness, doc_inline=True)
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Enum(
            ["Cats", "Dogs", ":3"], ["Cats!", "Dogs!", "Sharkie!"]
        )

    def test_json_schema_inline_magic(self):
        parser = yuio.parse.Enum(self.CutenessInline)
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Enum(
            ["Cats", "Dogs", ":3"], ["Cats!", "Dogs!", "Sharkie!"]
        )

    def test_json_schema_trim_comments(self):
        parser = yuio.parse.Enum(self.LongComments, by_name=True, doc_inline=True)
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Enum(
            ["LONG", "LONGER"],
            [
                "Long comment\nthat spans multiple lines.",
                "Longer comment\nthat spans multiple lines...",
            ],
        )

    def test_by_value(self):
        parser = yuio.parse.Enum(self.Cuteness)
        assert parser.parse("CATS") is self.Cuteness.CATS
        assert parser.parse("CATS") is self.Cuteness.CATS
        assert parser.parse_config("Cats") is self.Cuteness.CATS
        assert parser.parse_config(self.Cuteness.CATS) is self.Cuteness.CATS
        with pytest.raises(yuio.parse.ParsingError):
            parser.parse_config("CATS")
        assert parser.parse("dogs") is self.Cuteness.DOGS
        assert parser.parse(":3") is self.Cuteness.BLAHAJ
        with pytest.raises(yuio.parse.ParsingError):
            parser.parse("Unchi")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_by_name(self):
        parser = yuio.parse.Enum(self.Colors, by_name=True)
        assert parser.parse("RED") is self.Colors.RED
        assert parser.parse("RED") is self.Colors.RED
        assert parser.parse_config("RED") is self.Colors.RED
        assert parser.parse_config(self.Colors.RED) is self.Colors.RED
        assert parser.parse("green") is self.Colors.GREEN
        assert parser.parse("Blue") is self.Colors.BLUE
        with pytest.raises(yuio.parse.ParsingError):
            parser.parse("Color of a beautiful sunset")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

        assert parser.describe() == "{RED|GREEN|BLUE}"
        assert parser.describe_or_def() == "{RED|GREEN|BLUE}"
        assert parser.describe_value(self.Colors.RED) == "RED"

    def test_by_name_magic(self):
        parser = yuio.parse.Enum(self.ColorsByName)
        assert parser.parse("RED") is self.ColorsByName.RED
        assert parser.parse("RED") is self.ColorsByName.RED
        assert parser.parse_config("RED") is self.ColorsByName.RED
        assert parser.parse_config(self.ColorsByName.RED) is self.ColorsByName.RED
        assert parser.parse("green") is self.ColorsByName.GREEN
        assert parser.parse("Blue") is self.ColorsByName.BLUE
        with pytest.raises(yuio.parse.ParsingError):
            parser.parse("Color of a beautiful sunset")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

        assert parser.describe() == "{RED|GREEN|BLUE}"
        assert parser.describe_or_def() == "{RED|GREEN|BLUE}"
        assert parser.describe_value(self.ColorsByName.RED) == "RED"

    def test_to_dash_case(self):
        class Colors(enum.Enum):
            RED = "RED"
            GREEN_FORE = "GREEN_FORE"
            GREEN_BACK = "GREEN_BACK"

        parser = yuio.parse.Enum(Colors, to_dash_case=True)
        assert parser.parse("green-fore") is Colors.GREEN_FORE

    def test_to_dash_case_magic(self):
        class Colors(enum.Enum):
            __yuio_to_dash_case__ = True

            RED = "RED"
            GREEN_FORE = "GREEN_FORE"
            GREEN_BACK = "GREEN_BACK"

        parser = yuio.parse.Enum(Colors)
        assert parser.parse("green-fore") is Colors.GREEN_FORE

    def test_short(self):
        class Colors(enum.Enum):
            RED = "RED"
            GREEN_FORE = "GREEN_FORE"
            GREEN_BACK = "GREEN_BACK"

        parser = yuio.parse.Enum(Colors)
        assert parser.parse("R") is Colors.RED
        assert parser.parse("r") is Colors.RED
        with pytest.raises(
            yuio.parse.ParsingError,
            match=r"possible candidates are GREEN_FORE or GREEN_BACK",
        ):
            parser.parse("G")
        assert parser.parse("GREEN_F") is Colors.GREEN_FORE
        with pytest.raises(yuio.parse.ParsingError, match=r"did you mean RED?"):
            parser.parse_config("r")

    def test_from_type_hint(self):
        parser = yuio.parse.from_type_hint(self.Cuteness)
        assert isinstance(parser, yuio.parse.Enum)
        assert parser.parse(":3") is self.Cuteness.BLAHAJ

    def test_partial(self):
        parser = yuio.parse.Enum()
        with pytest.raises(TypeError, match=r"Enum requires an inner parser"):
            parser.parse("asd")  # type: ignore

        parser = yuio.parse.Enum(by_name=True)
        with pytest.raises(TypeError, match=r"Enum requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[self.Cuteness, yuio.parse.Enum()]
        )
        assert parser.parse(":3") is self.Cuteness.BLAHAJ

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Enum conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Enum()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Enum will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[self.Cuteness, yuio.parse.Enum(), yuio.parse.Enum()]
            )

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Enum with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[self.Colors, yuio.parse.Enum(self.Colors)]
            )

    def test_options(self):
        parser = yuio.parse.Enum(self.LongComments, by_name=True)
        options = list(parser.options())
        assert options == [
            yuio.widget.Option(
                value=self.LongComments.LONG,
                display_text="LONG",
                comment="Long comment...",
            ),
            yuio.widget.Option(
                value=self.LongComments.LONGER,
                display_text="LONGER",
                comment="Longer comment...",
            ),
        ]


class TestDecimal:
    def test_basics(self):
        parser = yuio.parse.Decimal()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<decimal>"
        assert parser.describe_many() == "<decimal>"
        assert parser.describe_value(Decimal(10)) == "10"

    def test_json_schema(self):
        parser = yuio.parse.Decimal()
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref("#/$defs/Decimal", "Decimal")
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate(10)
        validator.validate(10.5)
        validator.validate("NaN")
        validator.validate("sNaN")
        validator.validate("-10e2")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        assert parser.to_json_value(Decimal(10)) == "10"

    def test_parse(self):
        parser = yuio.parse.Decimal()
        assert parser.parse("1.5") == Decimal("1.5")
        assert parser.parse("-10") == Decimal("-10")
        assert parser.parse_config(1.0) == Decimal("1.0")
        assert parser.parse_config("1.5") == Decimal("1.5")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("x")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse_config("x")
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Expected int, float, or str, got list"
        ):
            parser.parse_config([])

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(Decimal), yuio.parse.Decimal)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[Decimal, yuio.parse.Decimal()])
        assert parser.parse("1.5") == 1.5

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Decimal conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Decimal()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Decimal will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[Decimal, yuio.parse.Decimal(), yuio.parse.Decimal()]
            )


class TestFraction:
    def test_basics(self):
        parser = yuio.parse.Fraction()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<fraction>"
        assert parser.describe_many() == "<fraction>"
        assert parser.describe_value(Fraction(10)) == "10"

    def test_json_schema(self):
        parser = yuio.parse.Fraction()
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref("#/$defs/Fraction", "Fraction")
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate(10)
        validator.validate(10.5)
        validator.validate("NaN")
        validator.validate("1/2")
        validator.validate("-1/2")
        validator.validate("-10e2")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        assert parser.to_json_value(Fraction("2/3")) == "2/3"

    def test_parse(self):
        parser = yuio.parse.Fraction()
        assert parser.parse("1/3") == Fraction("1/3")
        assert parser.parse("-10") == Fraction("-10")
        assert parser.parse_config(1.0) == Fraction("1.0")
        assert parser.parse_config("1/3") == Fraction("1/3")
        assert parser.parse_config([2, 5]) == Fraction("2/5")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("x")
        with pytest.raises(yuio.parse.ParsingError, match=r"division by zero"):
            parser.parse("1/0")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse_config("x")
        with pytest.raises(
            yuio.parse.ParsingError,
            match=r"Expected int, float, str, or a tuple of two ints, got list",
        ):
            parser.parse_config([])
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse 1/0 as fraction"
        ):
            parser.parse_config([1, 0])
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse 1/nan as fraction"
        ):
            parser.parse_config([1, math.nan])
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse nan as fraction"
        ):
            parser.parse_config(math.nan)

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(Fraction), yuio.parse.Fraction)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[Fraction, yuio.parse.Fraction()]
        )
        assert parser.parse("1.5") == 1.5

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Fraction conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Fraction()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Fraction will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[Fraction, yuio.parse.Fraction(), yuio.parse.Fraction()]
            )


class TestJson:
    def test_basics(self):
        parser = yuio.parse.Json()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<json>"
        assert parser.describe_many() == "<json>"
        assert parser.describe_value(dict(a=0)) == "{'a': 0}"

    def test_unstructured(self):
        parser = yuio.parse.Json()
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        assert parser.parse_config("[1, 2, 3]") == "[1, 2, 3]"
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse 'x' as JsonValue"
        ):
            parser.parse("x")
        assert isinstance(
            yuio.parse.from_type_hint(yuio.json_schema.JsonValue), yuio.parse.Json
        )
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Any()
        )
        assert parser.to_json_value([1, dict(a=0)]) == [1, dict(a=0)]

    def test_structured(self):
        parser = yuio.parse.Json(yuio.parse.List(yuio.parse.Int()))
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse 'x' as JsonValue"
        ):
            parser.parse("x")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected int, got float"):
            parser.parse("[1.5]")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected list, got str"):
            parser.parse_config("[1, 2, 3]")
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Array(yuio.json_schema.Integer())
        assert parser.to_json_value([1, 2, 3]) == [1, 2, 3]
        with pytest.raises(TypeError):
            parser.to_json_value([1, dict(a=10)])

    def test_from_type_hint_annotated_unstructured(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[yuio.json_schema.JsonValue, yuio.parse.Json()]
        )
        assert parser.parse("1.5") == 1.5

    def test_from_type_hint_annotated_structured(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[list[int], yuio.parse.Json()])
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse 'x' as JsonValue"
        ):
            parser.parse("x")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected list, got str"):
            parser.parse_config("[1, 2, 3]")

    def test_from_type_hint_annotated_shadowing(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[
                yuio.json_schema.JsonValue, yuio.parse.Json(), yuio.parse.Json()
            ]
        )
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]

    def test_from_type_hint_annotated_unstructured_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Json with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    yuio.json_schema.JsonValue, yuio.parse.Json(yuio.parse.Int())
                ]
            )

    def test_from_type_hint_annotated_structured_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Json with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Json(yuio.parse.Int())]
            )


class TestDateTime:
    def test_basics(self):
        parser = yuio.parse.DateTime()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "YYYY-MM-DD[ HH:MM:SS]"
        assert parser.describe_or_def() == "YYYY-MM-DD[ HH:MM:SS]"
        assert parser.describe_many() == "YYYY-MM-DD[ HH:MM:SS]"
        assert (
            parser.describe_value(datetime.datetime(2025, 1, 1))
            == "2025-01-01 00:00:00"
        )

    def test_json_schema(self):
        parser = yuio.parse.DateTime()
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref("#/$defs/DateTime", "DateTime")
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate("2025-01-01 15:00")
        validator.validate("20250101T15:00")
        validator.validate("2025-W10-2")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("2025W10-2")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(10)
        assert (
            parser.to_json_value(datetime.datetime(2025, 1, 1, 15))
            == "2025-01-01 15:00:00"
        )

    def test_parse(self):
        parser = yuio.parse.DateTime()

        assert parser.parse("2007-01-02T10:00:05.001") == datetime.datetime(
            2007, 1, 2, 10, 0, 5, 1000
        )
        assert parser.parse("2007-01-02 10:00:05.001") == datetime.datetime(
            2007, 1, 2, 10, 0, 5, 1000
        )
        assert parser.parse_config("2007-01-02T10:00:05.001") == datetime.datetime(
            2007, 1, 2, 10, 0, 5, 1000
        )
        assert parser.parse_config(
            datetime.datetime(2007, 1, 2, 10, 0, 5, 1000)
        ) == datetime.datetime(2007, 1, 2, 10, 0, 5, 1000)
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("2007 01 02")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_from_type_hint(self):
        assert isinstance(
            yuio.parse.from_type_hint(datetime.datetime), yuio.parse.DateTime
        )

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[datetime.datetime, yuio.parse.DateTime()]
        )
        assert parser.parse("2007-01-02 10:00:05.001") == datetime.datetime(
            2007, 1, 2, 10, 0, 5, 1000
        )

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with DateTime conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.DateTime()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with DateTime will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    datetime.datetime, yuio.parse.DateTime(), yuio.parse.DateTime()
                ]
            )


class TestDate:
    def test_basics(self):
        parser = yuio.parse.Date()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "YYYY-MM-DD"
        assert parser.describe_or_def() == "YYYY-MM-DD"
        assert parser.describe_many() == "YYYY-MM-DD"
        assert parser.describe_value(datetime.date(2025, 1, 1)) == "2025-01-01"

    def test_json_schema(self):
        parser = yuio.parse.Date()
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref("#/$defs/Date", "Date")
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate("2025-01-01")
        validator.validate("20250101")
        validator.validate("2025-W10-2")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("2025W10-2")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(10)
        assert parser.to_json_value(datetime.date(2025, 1, 1)) == "2025-01-01"

    def test_parse(self):
        parser = yuio.parse.Date()

        assert parser.parse("2007-01-02") == datetime.date(2007, 1, 2)
        assert parser.parse_config("2007-01-02") == datetime.date(2007, 1, 2)
        assert parser.parse_config(datetime.date(2007, 1, 2)) == datetime.date(
            2007, 1, 2
        )
        assert parser.parse_config(datetime.datetime(2007, 1, 2)) == datetime.date(
            2007, 1, 2
        )
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("2007 01 02")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(datetime.time(10, 1))

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(datetime.date), yuio.parse.Date)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[datetime.date, yuio.parse.Date()]
        )
        assert parser.parse("2007-01-02") == datetime.date(2007, 1, 2)

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Date conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Date()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Date will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[datetime.date, yuio.parse.Date(), yuio.parse.Date()]
            )


class TestTime:
    def test_basics(self):
        parser = yuio.parse.Time()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "HH:MM:SS"
        assert parser.describe_or_def() == "HH:MM:SS"
        assert parser.describe_many() == "HH:MM:SS"
        assert parser.describe_value(datetime.time()) == "00:00:00"

    def test_json_schema(self):
        parser = yuio.parse.Time()
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref("#/$defs/Time", "Time")
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate("15:00")
        validator.validate("15:00:00.123432Z")
        validator.validate("15:00:00-02")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("15:00:00-02Z")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(10)
        assert parser.to_json_value(datetime.time(15, 00)) == "15:00:00"

    def test_parse(self):
        parser = yuio.parse.Time()

        assert parser.parse("10:05") == datetime.time(10, 5)
        assert parser.parse_config("10:05") == datetime.time(10, 5)
        assert parser.parse_config(datetime.time(10, 5)) == datetime.time(10, 5)
        assert parser.parse_config(
            datetime.datetime(2007, 1, 2, 12, 30, 5)
        ) == datetime.time(12, 30, 5)
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("10?05")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(datetime.date(1996, 1, 1))

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(datetime.time), yuio.parse.Time)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[datetime.time, yuio.parse.Time()]
        )
        assert parser.parse("10:00:05.001") == datetime.time(10, 0, 5, 1000)

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Time conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Time()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Time will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[datetime.time, yuio.parse.Time(), yuio.parse.Time()]
            )


class TestTimeDelta:
    def test_basics(self):
        parser = yuio.parse.TimeDelta()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "[+|-]HH:MM:SS"
        assert parser.describe_or_def() == "[+|-]HH:MM:SS"
        assert parser.describe_many() == "[+|-]HH:MM:SS"
        assert parser.describe_value(datetime.timedelta(hours=10)) == "10:00:00"

    def test_json_schema(self):
        parser = yuio.parse.TimeDelta()
        ctx = yuio.json_schema.JsonSchemaContext()
        res = parser.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref("#/$defs/TimeDelta", "TimeDelta")
        schema: _t.Any = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate("1day")
        validator.validate("-1 day")
        validator.validate("2 weeks 1 day 15:00:00")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("2 weeks 1 day,")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(", 15:00:00")
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(10)
        assert parser.to_json_value(datetime.timedelta(1, 25)) == "1 day, 0:00:25"

    def test_parse(self):
        parser = yuio.parse.TimeDelta()

        assert parser.parse("1w") == datetime.timedelta(weeks=1)
        assert parser.parse("1week") == datetime.timedelta(weeks=1)
        assert parser.parse("5weeks") == datetime.timedelta(weeks=5)
        assert parser.parse("2d") == datetime.timedelta(days=2)
        assert parser.parse("1day") == datetime.timedelta(days=1)
        assert parser.parse("3days") == datetime.timedelta(days=3)
        assert parser.parse("5s") == datetime.timedelta(seconds=5)
        assert parser.parse("1sec") == datetime.timedelta(seconds=1)
        assert parser.parse("2second") == datetime.timedelta(seconds=2)
        assert parser.parse("3secs") == datetime.timedelta(seconds=3)
        assert parser.parse("4seconds") == datetime.timedelta(seconds=4)
        assert parser.parse("5m") == datetime.timedelta(minutes=5)
        assert parser.parse("1min") == datetime.timedelta(minutes=1)
        assert parser.parse("2minute") == datetime.timedelta(minutes=2)
        assert parser.parse("3mins") == datetime.timedelta(minutes=3)
        assert parser.parse("4minutes") == datetime.timedelta(minutes=4)
        assert parser.parse("5h") == datetime.timedelta(hours=5)
        assert parser.parse("1h") == datetime.timedelta(hours=1)
        assert parser.parse("1hr") == datetime.timedelta(hours=1)
        assert parser.parse("2hour") == datetime.timedelta(hours=2)
        assert parser.parse("3hrs") == datetime.timedelta(hours=3)
        assert parser.parse("4hours") == datetime.timedelta(hours=4)
        assert parser.parse("5ms") == datetime.timedelta(milliseconds=5)
        assert parser.parse("5l") == datetime.timedelta(milliseconds=5)
        assert parser.parse("1milli") == datetime.timedelta(milliseconds=1)
        assert parser.parse("2millis") == datetime.timedelta(milliseconds=2)
        assert parser.parse("3millisecond") == datetime.timedelta(milliseconds=3)
        assert parser.parse("4milliseconds") == datetime.timedelta(milliseconds=4)
        assert parser.parse("5us") == datetime.timedelta(microseconds=5)
        assert parser.parse("5u") == datetime.timedelta(microseconds=5)
        assert parser.parse("1micro") == datetime.timedelta(microseconds=1)
        assert parser.parse("2micros") == datetime.timedelta(microseconds=2)
        assert parser.parse("3microsecond") == datetime.timedelta(microseconds=3)
        assert parser.parse("4microseconds") == datetime.timedelta(microseconds=4)

        assert parser.parse("1d5secs") == datetime.timedelta(1, 5)
        assert parser.parse("1d 5secs") == datetime.timedelta(1, 5)
        assert parser.parse("-1d5secs") == -datetime.timedelta(1, 5)
        assert parser.parse("- 1d 5secs") == -datetime.timedelta(1, 5)

        assert parser.parse("10:00:01") == datetime.timedelta(hours=10, seconds=1)
        assert parser.parse("-10:00:01") == datetime.timedelta(hours=-10, seconds=-1)

        assert parser.parse("1d 05:00") == datetime.timedelta(days=1, hours=5)
        assert parser.parse("+1d +05:00") == datetime.timedelta(days=1, hours=5)
        assert parser.parse("-1d 05:00") == datetime.timedelta(days=-1, hours=5)
        assert parser.parse("-1d +05:00") == datetime.timedelta(days=-1, hours=5)
        assert parser.parse("-1d -05:00") == datetime.timedelta(days=-1, hours=-5)
        assert parser.parse("-1d2h +05:00") == datetime.timedelta(days=-1, hours=-2 + 5)

        assert parser.parse("1d, +5:00") == datetime.timedelta(days=1, hours=5)

        with pytest.raises(yuio.parse.ParsingError, match=r"empty timedelta"):
            parser.parse("")

        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("-")

        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("00:00,")

        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse(",00:00")

        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("00")

        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("1 megasecond")

        assert parser.parse_config("10:00:01") == datetime.timedelta(
            hours=10, seconds=1
        )
        assert parser.parse_config(
            datetime.timedelta(hours=10, seconds=1)
        ) == datetime.timedelta(hours=10, seconds=1)
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str, got int: 10"):
            parser.parse_config(10)

    def test_from_type_hint(self):
        assert isinstance(
            yuio.parse.from_type_hint(datetime.timedelta), yuio.parse.TimeDelta
        )

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[datetime.timedelta, yuio.parse.TimeDelta()]
        )
        assert parser.parse("01:00") == datetime.timedelta(hours=1)

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with TimeDelta conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.TimeDelta()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with TimeDelta will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    datetime.timedelta, yuio.parse.TimeDelta(), yuio.parse.TimeDelta()
                ]
            )


class TestPath:
    def test_basics(self):
        parser = yuio.parse.Path()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<path>"
        assert parser.describe_many() == "<path>"
        assert parser.describe_value(pathlib.Path("/")) == os.path.sep

        parser = yuio.parse.Path(extensions=[".toml"])
        assert parser.describe_or_def() == "<*.toml>"
        assert parser.describe_or_def() == "<*.toml>"
        parser = yuio.parse.Path(extensions=[".toml", ".yaml"])
        assert parser.describe_or_def() == "{<*.toml>|<*.yaml>}"
        assert parser.describe_or_def() == "{<*.toml>|<*.yaml>}"

    def test_json_schema(self):
        parser = yuio.parse.Path()
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.String()
        )
        assert parser.to_json_value(pathlib.Path("path")) == "path"

    def test_parse(self):
        parser = yuio.parse.Path()
        assert parser.parse("/a/s/d") == pathlib.Path("/a/s/d").resolve().absolute()
        assert parser.parse("/a/s/d/..") == pathlib.Path("/a/s").resolve().absolute()
        assert parser.parse("a/s/d") == pathlib.Path("a/s/d").resolve().absolute()
        assert parser.parse("./a/s/./d") == pathlib.Path("a/s/d").resolve().absolute()
        assert (
            parser.parse("~/a")
            == pathlib.Path(os.path.expanduser("~/a")).resolve().absolute()
        )
        assert (
            parser.parse_config("/a/s/d") == pathlib.Path("/a/s/d").resolve().absolute()
        )
        assert (
            parser.parse_config("/a/s/d/..")
            == pathlib.Path("/a/s").resolve().absolute()
        )
        assert (
            parser.parse_config("a/s/d") == pathlib.Path("a/s/d").resolve().absolute()
        )
        assert (
            parser.parse_config("./a/s/./d")
            == pathlib.Path("a/s/d").resolve().absolute()
        )
        assert (
            parser.parse_config("~/a")
            == pathlib.Path(os.path.expanduser("~/a")).resolve().absolute()
        )
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            parser.parse_config(10)

    def test_extensions(self):
        parser = yuio.parse.Path(extensions=[".cfg", ".txt"])
        assert (
            parser.parse("/a/s/d.cfg")
            == pathlib.Path("/a/s/d.cfg").resolve().absolute()
        )
        assert (
            parser.parse("/a/s/d.txt")
            == pathlib.Path("/a/s/d.txt").resolve().absolute()
        )
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should have extension \.cfg or \.txt"
        ):
            parser.parse("file.sql")

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(pathlib.Path), yuio.parse.Path)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[pathlib.Path, yuio.parse.Path()]
        )
        assert parser.parse("/a/s/d") == pathlib.Path("/a/s/d").resolve().absolute()

    def test_from_type_hint_annotated_extensions(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[pathlib.Path, yuio.parse.Path(extensions=[".x"])]
        )
        assert parser.parse("/a/s/d.x") == pathlib.Path("/a/s/d.x").resolve().absolute()
        with pytest.raises(yuio.parse.ParsingError, match=r"should have extension \.x"):
            parser.parse("file.y")

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Path conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Path()])

    def test_from_type_hint_annotated_shadowing(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Path will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[pathlib.Path, yuio.parse.Path(), yuio.parse.Path()]
            )


class TestExistingPath:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.ExistingPath()
        with pytest.raises(yuio.parse.ParsingError, match=r"doesn't exist"):
            parser.parse(tmpdir.join("file2.cfg").strpath)
        assert (
            str(parser.parse(tmpdir.join("file.cfg").strpath))
            == tmpdir.join("file.cfg").strpath
        )

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[pathlib.Path, yuio.parse.ExistingPath()]
        )
        assert isinstance(parser, yuio.parse.ExistingPath)


class TestNonExistentPath:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.NonExistentPath()
        with pytest.raises(yuio.parse.ParsingError, match=r"already exists"):
            parser.parse(tmpdir.join("file.cfg").strpath)
        assert (
            str(parser.parse(tmpdir.join("file2.cfg").strpath))
            == tmpdir.join("file2.cfg").strpath
        )

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[pathlib.Path, yuio.parse.NonExistentPath()]
        )
        assert isinstance(parser, yuio.parse.NonExistentPath)


class TestFile:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.File()
        assert (
            str(parser.parse(tmpdir.join("file.cfg").strpath))
            == tmpdir.join("file.cfg").strpath
        )
        with pytest.raises(yuio.parse.ParsingError, match=r"doesn't exist"):
            parser.parse(tmpdir.join("file.txt").strpath)
        with pytest.raises(yuio.parse.ParsingError, match=r"is not a file"):
            parser.parse(tmpdir.strpath)

        parser = yuio.parse.File(extensions=[".cfg", ".txt"])
        assert (
            str(parser.parse(tmpdir.join("file.cfg").strpath))
            == tmpdir.join("file.cfg").strpath
        )
        with pytest.raises(yuio.parse.ParsingError, match=r"doesn't exist"):
            parser.parse(tmpdir.join("file.txt").strpath)
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should have extension \.cfg or \.txt"
        ):
            parser.parse(tmpdir.join("file.sql").strpath)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[pathlib.Path, yuio.parse.File()]
        )
        assert isinstance(parser, yuio.parse.File)


class TestDir:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.Dir()
        assert str(parser.parse("~")) == os.path.expanduser("~")
        assert str(parser.parse(tmpdir.strpath)) == tmpdir.strpath
        with pytest.raises(yuio.parse.ParsingError, match=r"doesn't exist"):
            parser.parse(tmpdir.join("subdir").strpath)
        with pytest.raises(yuio.parse.ParsingError, match=r"is not a directory"):
            parser.parse(tmpdir.join("file.cfg").strpath)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[pathlib.Path, yuio.parse.Dir()])
        assert isinstance(parser, yuio.parse.Dir)


class TestGitRepo:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.GitRepo()
        with pytest.raises(yuio.parse.ParsingError, match=r"is not a git repository"):
            parser.parse(tmpdir.strpath)
        with pytest.raises(yuio.parse.ParsingError, match=r"doesn't exist"):
            parser.parse(tmpdir.join("subdir").strpath)
        with pytest.raises(yuio.parse.ParsingError, match=r"is not a directory"):
            parser.parse(tmpdir.join("file.cfg").strpath)

        tmpdir.join(".git").mkdir()

        assert str(parser.parse(tmpdir.strpath)) == tmpdir.strpath

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[pathlib.Path, yuio.parse.GitRepo()]
        )
        assert isinstance(parser, yuio.parse.GitRepo)


class TestBound:
    def test_api(self):
        with pytest.raises(TypeError, match=r"lower and lower_inclusive"):
            yuio.parse.Bound(yuio.parse.Int(), lower=0, lower_inclusive=1)
        with pytest.raises(TypeError, match=r"upper and upper_inclusive"):
            yuio.parse.Bound(yuio.parse.Int(), upper=0, upper_inclusive=1)

    def test_empty_bounds(self):
        parser = yuio.parse.Bound(yuio.parse.Int())
        assert parser.parse("0") == 0
        assert parser.parse("-10") == -10
        assert parser.parse("10") == 10

    def test_gt(self):
        parser = yuio.parse.Gt(yuio.parse.Int(), 0)
        assert parser.parse("10") == 10
        with pytest.raises(yuio.parse.ParsingError, match=r"should be greater than 0"):
            parser.parse("-1")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be greater than 0"):
            parser.parse("0")

    def test_ge(self):
        parser = yuio.parse.Ge(yuio.parse.Int(), 0)
        assert parser.parse("10") == 10
        assert parser.parse("0") == 0
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should be greater than or equal to 0"
        ):
            parser.parse("-1")

    def test_lt(self):
        parser = yuio.parse.Lt(yuio.parse.Int(), 10)
        assert parser.parse("5") == 5
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 10"):
            parser.parse("10")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 10"):
            parser.parse("11")

    def test_le(self):
        parser = yuio.parse.Le(yuio.parse.Int(), 10)
        assert parser.parse("5") == 5
        assert parser.parse("10") == 10
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should be lesser than or equal to 10"
        ):
            parser.parse("11")

    def test_range_inclusive(self):
        parser = yuio.parse.Bound(
            yuio.parse.Int(), lower_inclusive=0, upper_inclusive=5
        )
        assert parser.parse("0") == 0
        assert parser.parse("2") == 2
        assert parser.parse("5") == 5
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should be greater than or equal to 0"
        ):
            parser.parse("-1")
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should be lesser than or equal to 5"
        ):
            parser.parse("6")

    def test_range_non_inclusive(self):
        parser = yuio.parse.Bound(yuio.parse.Int(), lower=0, upper=5)
        assert parser.parse("2") == 2
        with pytest.raises(yuio.parse.ParsingError, match=r"should be greater than 0"):
            parser.parse("0")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 5"):
            parser.parse("5")

    def test_partial(self):
        parser = yuio.parse.Bound()
        with pytest.raises(TypeError, match=r"Bound requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[int, yuio.parse.Bound(lower_inclusive=0, upper=10)]
        )
        assert parser.parse("0") == 0
        assert parser.parse("9") == 9
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 10"):
            parser.parse("10")

    def test_from_type_hint_annotated_combine(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[
                int, yuio.parse.Bound(lower_inclusive=0), yuio.parse.Bound(upper=10)
            ]
        )
        assert parser.parse("0") == 0
        assert parser.parse("9") == 9
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 10"):
            parser.parse("10")

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Bound with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Bound(yuio.parse.Int())]
            )

    def test_gt_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Gt(0)])
        assert parser.parse("10") == 10
        with pytest.raises(yuio.parse.ParsingError, match=r"should be greater than 0"):
            parser.parse("-1")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be greater than 0"):
            parser.parse("0")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Gt(yuio.parse.Int(), 0, 0)]  # type: ignore
            )

    def test_ge_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Ge(0)])
        assert parser.parse("10") == 10
        assert parser.parse("0") == 0
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should be greater than or equal to 0"
        ):
            parser.parse("-1")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Ge(yuio.parse.Int(), 0, 0)]  # type: ignore
            )

    def test_lt_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Lt(10)])
        assert parser.parse("5") == 5
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 10"):
            parser.parse("10")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be lesser than 10"):
            parser.parse("11")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Lt(yuio.parse.Int(), 10, 0)]  # type: ignore
            )

    def test_le_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Le(10)])
        assert parser.parse("5") == 5
        assert parser.parse("10") == 10
        with pytest.raises(
            yuio.parse.ParsingError, match=r"should be lesser than or equal to 10"
        ):
            parser.parse("11")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Le(yuio.parse.Int(), 10, 0)]  # type: ignore
            )


class TestOneOf:
    def test_parse(self):
        parser = yuio.parse.OneOf(yuio.parse.Str(), ["qux", "duo"])
        assert parser.parse("qux") == "qux"
        assert parser.parse("duo") == "duo"
        with pytest.raises(yuio.parse.ParsingError, match=r"should be 'qux' or 'duo'"):
            parser.parse("foo")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be 'qux' or 'duo'"):
            parser.parse("Qux")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be 'qux' or 'duo'"):
            parser.parse("Duo")

    def test_partial(self):
        parser = yuio.parse.OneOf([])
        with pytest.raises(TypeError, match=r"OneOf requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_one_of_combined_with_lower(self):
        parser = yuio.parse.OneOf(yuio.parse.Lower(yuio.parse.Str()), ["qux", "duo"])
        assert parser.parse("Qux") == "qux"
        assert parser.parse("Duo") == "duo"

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[str, yuio.parse.OneOf(["qux", "duo"])]
        )
        assert parser.parse("qux") == "qux"
        assert parser.parse("duo") == "duo"
        with pytest.raises(yuio.parse.ParsingError, match=r"should be 'qux' or 'duo'"):
            parser.parse("foo")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be 'qux' or 'duo'"):
            parser.parse("Qux")
        with pytest.raises(yuio.parse.ParsingError, match=r"should be 'qux' or 'duo'"):
            parser.parse("Duo")

    def test_from_type_hint_annotated_combined_with_lower(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[
                str,
                yuio.parse.Str(),
                yuio.parse.Lower(),
                yuio.parse.OneOf(["qux", "duo"]),
            ]
        )
        assert parser.parse("Qux") == "qux"
        assert parser.parse("Duo") == "duo"

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using OneOf with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.OneOf(yuio.parse.Int(), [1, 2, 3])]
            )


class TestMap:
    @dataclass
    class Wrapper:
        value: _t.Any

    def test_basics(self):
        parser = yuio.parse.Map(
            yuio.parse.Int(), TestMap.Wrapper, lambda wrapped: wrapped.value
        )
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(TestMap.Wrapper(10)) == "10"

    def test_secret(self):
        parser = yuio.parse.Map(yuio.parse.Secret(yuio.parse.Str()), lambda x: x)
        assert parser.is_secret()

    def test_basics_collection(self):
        parser = yuio.parse.Map(
            yuio.parse.List(yuio.parse.Int()),
            TestMap.Wrapper,
            lambda wrapped: wrapped.value,
        )
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.options() is None
        assert parser.parse_many(["1", "2", "3"]) == TestMap.Wrapper([1, 2, 3])
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(TestMap.Wrapper([])) == ""

    def test_same_type(self):
        parser = yuio.parse.Map(yuio.parse.Int(), lambda x: x * 2)
        assert parser.describe_value(20) == "20"

        parser = yuio.parse.Map(yuio.parse.Int(), lambda x: x * 2, lambda x: x // 2)
        assert parser.describe_value(20) == "10"

    def test_json_schema(self):
        parser = yuio.parse.Map(yuio.parse.Bool(), lambda x: not x, lambda x: not x)
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Boolean()
        )
        assert not parser.to_json_value(True)

    def test_options(self):
        class E(enum.Enum):
            pass

        parser = yuio.parse.Map(yuio.parse.Enum(E), lambda x: x)
        assert parser.options() == []

        class E(enum.Enum):
            FOO = "foo"

        parser = yuio.parse.Map(yuio.parse.Enum(E), lambda x: x)
        assert parser.options() == [
            yuio.widget.Option(
                value=E.FOO,
                display_text="foo",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
        ]

    def test_parse(self):
        parser = yuio.parse.Map(yuio.parse.Int(), lambda x: x * 2)
        assert parser.parse("2") == 4
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("foo")

    def test_partial(self):
        parser = yuio.parse.Map(lambda x: x)
        with pytest.raises(TypeError, match=r"Map requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[int, yuio.parse.Map[int, int](lambda x: x * 2)]
        )
        assert parser.parse("2") == 4
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("foo")

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Map with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Map(yuio.parse.Int(), lambda x: x)]
            )


class TestApply:
    def test_basics(self):
        parser = yuio.parse.Apply(yuio.parse.Int(), lambda x: None)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(10) == "10"

    def test_secret(self):
        parser = yuio.parse.Apply(yuio.parse.Secret(yuio.parse.Str()), lambda x: None)
        assert parser.is_secret()

    def test_basics_collection(self):
        parser = yuio.parse.Apply(yuio.parse.List(yuio.parse.Int()), lambda x: None)
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse_many(["1", "2", "3"]) == [1, 2, 3]
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value([]) == ""

    def test_json_schema(self):
        parser = yuio.parse.Apply(yuio.parse.Int(), lambda x: None)
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Integer()
        )
        assert parser.to_json_value(10) == 10

    def test_options(self):
        class E(enum.Enum):
            pass

        parser = yuio.parse.Apply(yuio.parse.Enum(E), lambda x: None)
        assert parser.options() == []

        class E(enum.Enum):
            FOO = "foo"

        parser = yuio.parse.Apply(yuio.parse.Enum(E), lambda x: None)
        assert parser.options() == [
            yuio.widget.Option(
                value=E.FOO,
                display_text="foo",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
        ]

    def test_parse(self):
        value = None

        def fn(x):
            nonlocal value
            value = x
            return x * 2

        parser = yuio.parse.Apply(yuio.parse.Int(), fn)
        assert parser.parse("2") == 2
        assert value == 2

        value = None

        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("foo")
        assert value is None

    def test_partial(self):
        parser = yuio.parse.Apply(print)
        with pytest.raises(TypeError, match=r"Apply requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        value = None

        def fn(x):
            nonlocal value
            value = x
            return x * 2

        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Apply(fn)])
        assert parser.parse("2") == 2
        assert value == 2

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Apply with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Apply(yuio.parse.Int(), lambda x: None)]
            )


class TestSimpleCollections:
    @pytest.fixture(
        params=[
            (yuio.parse.List, list),
            (yuio.parse.Set, set),
            (yuio.parse.FrozenSet, frozenset),
        ]
    )
    def test_params(self, request):
        return request.param

    def test_parse(self, test_params):
        parser_cls, ctor = test_params

        parser = parser_cls(yuio.parse.Int())
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.options() is None
        assert not parser.is_secret()
        assert parser.parse("1 2 3") == ctor([1, 2, 3])
        assert parser.parse_config([1, 2, 3]) == ctor([1, 2, 3])
        assert parser.parse_many(["1", "2", "3"]) == ctor([1, 2, 3])
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(ctor([1, 2, 3])) == "1 2 3"

        with pytest.raises(yuio.parse.ParsingError, match=r"Expected .*?, got int"):
            parser.parse_config(123)

    def test_secret(self, test_params):
        parser_cls, _ = test_params

        parser = parser_cls(yuio.parse.Secret(yuio.parse.Int()))
        assert parser.is_secret()

    def test_json_schema(self, test_params):
        parser_cls, ctor = test_params
        parser = parser_cls(yuio.parse.Int())
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Array(
            yuio.json_schema.Integer(), unique_items=issubclass(ctor, (set, frozenset))
        )
        assert parser.to_json_value(ctor([1, 2, 3])) == [1, 2, 3]

    def test_delim(self, test_params):
        parser_cls, ctor = test_params

        parser = parser_cls(yuio.parse.Int(), delimiter=",")
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse("1, 2, 3") == ctor([1, 2, 3])
        assert parser.parse_config([1, 2, 3]) == ctor([1, 2, 3])
        assert parser.parse_many(["1", "2", "3"]) == ctor([1, 2, 3])
        assert parser.describe() == "<int>[,<int>[,...]]"
        assert parser.describe_or_def() == "<int>[,<int>[,...]]"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(ctor([1, 2, 3])) == "1,2,3"

    def test_partial(self, test_params):
        parser_cls, _ = test_params

        parser = parser_cls()
        with pytest.raises(TypeError, match=r"requires an inner parser"):
            parser.parse("asd")

    def test_from_type_hint_annotated(self, test_params):
        parser_cls, ctor = test_params
        parser = yuio.parse.from_type_hint(_t.Annotated[ctor[int], parser_cls()])
        assert parser.parse("1 2 3") == ctor([1, 2, 3])
        parser = yuio.parse.from_type_hint(
            _t.Annotated[ctor[int], parser_cls(delimiter=",")]
        )
        assert parser.parse("1, 2, 3") == ctor([1, 2, 3])

    def test_from_type_hint_annotated_shadows(self, test_params):
        parser_cls, ctor = test_params
        with pytest.raises(
            TypeError,
            match=r"annotating a type with .*? will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[ctor[int], parser_cls(), parser_cls()]
            )

    def test_from_type_hint_annotated_wrong_type(self, test_params):
        parser_cls, _ = test_params
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with .*? conflicts with "
                "default parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, parser_cls()])

    def test_from_type_hint_annotated_non_partial(self, test_params):
        parser_cls, ctor = test_params
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using .*? with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[ctor[int], parser_cls(yuio.parse.Int())]
            )


class TestDict:
    def test_json_schema(self):
        parser = yuio.parse.Dict(yuio.parse.Str(), yuio.parse.Int())
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Dict(
            yuio.json_schema.String(), yuio.json_schema.Integer()
        )
        assert parser.to_json_value({"x": 1}) == {"x": 1}

        parser = yuio.parse.Dict(yuio.parse.Int(), yuio.parse.Str())
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Dict(
            yuio.json_schema.Integer(), yuio.json_schema.String()
        )
        assert parser.to_json_value({1: "x"}) == [[1, "x"]]

    def test_secret(self):
        parser = yuio.parse.Dict(
            yuio.parse.Secret(yuio.parse.Str()),
            yuio.parse.Str(),
        )
        assert parser.is_secret()

        parser = yuio.parse.Dict(
            yuio.parse.Str(),
            yuio.parse.Secret(yuio.parse.Str()),
        )
        assert parser.is_secret()

    def test_parse(self):
        parser = yuio.parse.Dict(yuio.parse.Int(), yuio.parse.Str())
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.options() is None
        assert not parser.is_secret()
        assert parser.parse("1:a 2:b") == {1: "a", 2: "b"}
        assert parser.parse_config({1: "a", 2: "b"}) == {1: "a", 2: "b"}
        assert parser.parse_config([(1, "a"), (2, "b")]) == {1: "a", 2: "b"}
        assert parser.parse_many(["1:a", "2:b"]) == {1: "a", 2: "b"}
        assert parser.describe() == "<int>:<str>[ <int>:<str>[ ...]]"
        assert parser.describe_or_def() == "<int>:<str>[ <int>:<str>[ ...]]"
        assert parser.describe_many() == "<int>:<str>"
        assert parser.describe_value({1: "a", 2: "b"}) == "1:a 2:b"

        with pytest.raises(
            yuio.parse.ParsingError, match=r"Expected dict or list, got int"
        ):
            parser.parse_config(123)
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected int, got str"):
            parser.parse_config({"x": "y"})

    def test_delim(self):
        parser = yuio.parse.Dict(
            yuio.parse.Int(), yuio.parse.Str(), delimiter=",", pair_delimiter="-"
        )
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse("1-a, 2-b") == {1: "a", 2: "b"}
        assert parser.parse_many(["1-a", "2-b"]) == {1: "a", 2: "b"}
        assert parser.describe() == "<int>-<str>[,<int>-<str>[,...]]"
        assert parser.describe_or_def() == "<int>-<str>[,<int>-<str>[,...]]"
        assert parser.describe_many() == "<int>-<str>"
        assert parser.describe_value({1: "a", 2: "b"}) == "1-a,2-b"

    def test_partial(self):
        parser = yuio.parse.Dict()
        with pytest.raises(TypeError, match=r"requires an inner parser"):
            parser.parse("asd")  # type: ignore
        parser = yuio.parse.Dict(yuio.parse.Int())  # type: ignore
        with pytest.raises(TypeError, match=r"requires an inner parser"):
            parser.parse("asd")

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[dict[int, str], yuio.parse.Dict()]
        )
        assert parser.parse("1:a 2:b") == {1: "a", 2: "b"}
        parser = yuio.parse.from_type_hint(
            _t.Annotated[
                dict[int, str], yuio.parse.Dict(delimiter=",", pair_delimiter="-")
            ]
        )
        assert parser.parse("1-a,2-b") == {1: "a", 2: "b"}

    def test_from_type_hint_annotated_shadows(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Dict will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[dict[int, str], yuio.parse.Dict(), yuio.parse.Dict()]
            )

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Dict conflicts with "
                "default parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Dict()])

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Dict with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    dict[str, int],
                    yuio.parse.Dict(yuio.parse.Str(), yuio.parse.Int()),
                ]
            )


class TestTuple:
    def test_json_schema(self):
        parser = yuio.parse.Tuple(yuio.parse.Str(), yuio.parse.Int(), yuio.parse.Bool())
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.Tuple(
            [
                yuio.json_schema.String(),
                yuio.json_schema.Integer(),
                yuio.json_schema.Boolean(),
            ]
        )
        assert parser.to_json_value(("x", -5, True)) == ["x", -5, True]

    def test_basics(self):
        parser = yuio.parse.Tuple(yuio.parse.Int())
        assert parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        assert parser.parse_many(["1"]) == (1,)
        assert parser.describe() == "<int>"
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == ("<int>",)
        assert parser.describe_value((10,)) == "10"

        parser = yuio.parse.Tuple(yuio.parse.Int(), yuio.parse.Str())
        assert parser.supports_parse_many()
        assert parser.get_nargs() == 2
        assert parser.options() is None
        assert parser.parse_many(["1", "x"]) == (1, "x")
        assert parser.describe() == "<int> <str>"
        assert parser.describe_or_def() == "<int> <str>"
        assert parser.describe_many() == ("<int>", "<str>")
        assert parser.describe_value((10, "x")) == "10 x"

        parser = yuio.parse.Tuple(yuio.parse.Int(), yuio.parse.Str(), yuio.parse.Bool())
        assert parser.supports_parse_many()
        assert parser.get_nargs() == 3
        assert parser.options() is None
        assert parser.parse_many(["1", "x", "no"]) == (1, "x", False)
        assert parser.describe() == "<int> <str> {yes|no}"
        assert parser.describe_or_def() == "<int> <str> {yes|no}"
        assert parser.describe_many() == ("<int>", "<str>", "{yes|no}")
        assert parser.describe_value((10, "x", False)) == "10 x no"

    def test_secret(self):
        parser = yuio.parse.Tuple(yuio.parse.Secret(yuio.parse.Str()))
        assert parser.is_secret()
        parser = yuio.parse.Tuple(
            yuio.parse.Int(), yuio.parse.Str(), yuio.parse.Secret(yuio.parse.Str())
        )
        assert parser.is_secret()

    def test_parse(self):
        parser = yuio.parse.Tuple(yuio.parse.Int())
        assert parser.parse("1") == (1,)
        assert parser.parse_config([1]) == (1,)
        assert parser.parse_config([1.0]) == (1,)
        assert parser.parse_many(["1"]) == (1,)
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("1 2 3")
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse"):
            parser.parse("foo")
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Expected list or tuple, got int"
        ):
            parser.parse_config(5)
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected int, got str"):
            parser.parse_config(["5"])
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected 1 element, got 0"):
            parser.parse("")
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected 1 element, got 2"):
            parser.parse_config([1, 2])
        with pytest.raises(yuio.parse.ParsingError, match=r"Expected 1 element, got 2"):
            parser.parse_many(["1", "2"])

        parser = yuio.parse.Tuple(yuio.parse.Str(), yuio.parse.Str())
        assert parser.parse("1 2") == ("1", "2")
        assert parser.parse("x y z") == ("x", "y z")
        assert parser.parse_config(["x", "y"]) == ("x", "y")
        assert parser.parse_many(["x", "y"]) == ("x", "y")
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Expected 2 elements, got 1"
        ):
            parser.parse("x")

    def test_delim(self):
        parser = yuio.parse.Tuple(yuio.parse.Str(), yuio.parse.Str(), delimiter=",")
        assert parser.parse("1, 2") == ("1", " 2")
        assert parser.parse("x, y, z") == ("x", " y, z")
        assert parser.parse_config(["x", "y"]) == ("x", "y")
        assert parser.parse_many(["x", "y"]) == ("x", "y")

    def test_partial(self):
        parser = yuio.parse.Tuple()
        with pytest.raises(TypeError, match=r"requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[tuple[int, str], yuio.parse.Tuple()]
        )
        assert parser.parse("1 a") == (1, "a")
        parser = yuio.parse.from_type_hint(
            _t.Annotated[tuple[int, str], yuio.parse.Tuple(delimiter=",")]
        )
        assert parser.parse("1,a") == (1, "a")

    def test_from_type_hint_annotated_shadows(self):
        with pytest.raises(
            TypeError,
            match=r"annotating a type with Tuple will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[tuple[int, str], yuio.parse.Tuple(), yuio.parse.Tuple()]
            )

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                r"annotating list(\[int\])? with Tuple conflicts with "
                r"default parser for this type, which is List\."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[list[int], yuio.parse.Tuple()])

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using Tuple with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    tuple[str, int],
                    yuio.parse.Tuple(yuio.parse.Str(), yuio.parse.Int()),
                ]
            )


class TestOptional:
    def test_basics(self):
        parser = yuio.parse.Optional(yuio.parse.Int())
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value(10) == "10"
        assert parser.describe_value(None) == "<none>"

    def test_secret(self):
        parser = yuio.parse.Optional(yuio.parse.Secret(yuio.parse.Str()))
        assert parser.is_secret()

    def test_json_schema(self):
        parser = yuio.parse.Optional(yuio.parse.Int())
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.OneOf(
            [yuio.json_schema.Integer(), yuio.json_schema.Null()]
        )
        assert parser.to_json_value(None) is None
        assert parser.to_json_value(10) == 10

    def test_basics_collection(self):
        parser = yuio.parse.Optional(yuio.parse.List(yuio.parse.Int()))
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse_many(["1", "2", "3"]) == [1, 2, 3]
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == "<int>"
        assert parser.describe_value([]) == ""
        assert parser.describe_value(None) == "<none>"

    def test_options(self):
        class E(enum.Enum):
            pass

        parser = yuio.parse.Optional(yuio.parse.Enum(E))
        assert parser.options() == []

        class E(enum.Enum):
            FOO = "foo"

        parser = yuio.parse.Optional(yuio.parse.Enum(E))
        assert parser.options() == [
            yuio.widget.Option(
                value=E.FOO,
                display_text="foo",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
        ]

    def test_parse(self):
        parser = yuio.parse.Optional(yuio.parse.Int())
        assert parser.parse("1") == 1
        assert parser.parse_config(1) == 1
        assert parser.parse_config(None) is None
        assert parser.supports_parse_many() is False

    def test_partial(self):
        parser = yuio.parse.Optional()
        with pytest.raises(TypeError, match=r"requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[list[int], yuio.parse.Optional()]
        )
        assert parser.parse_config(None) is None
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using .*? with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Optional(yuio.parse.Int())]
            )


class TestUnion:
    def test_basics(self):
        parser = yuio.parse.Union(yuio.parse.Int(), yuio.parse.Str())
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "{<int>|<str>}"
        assert parser.describe_or_def() == "{<int>|<str>}"
        assert parser.describe_many() == "{<int>|<str>}"
        assert parser.describe_value(10) == "10"

    def test_secret(self):
        parser = yuio.parse.Union(
            yuio.parse.Secret(yuio.parse.Str()),
        )
        assert parser.is_secret()
        parser = yuio.parse.Union(
            yuio.parse.Secret(yuio.parse.Str()),
            yuio.parse.Int(),
        )
        assert parser.is_secret()
        parser = yuio.parse.Union(
            yuio.parse.Int(),
            yuio.parse.Secret(yuio.parse.Str()),
        )
        assert parser.is_secret()

    def test_json_schema(self):
        parser = yuio.parse.Union(
            yuio.parse.Map(yuio.parse.Int(), lambda x: x * 2, lambda x: x // 2),
            yuio.parse.Date(),
            yuio.parse.Str(),
        )
        assert parser.to_json_schema(
            yuio.json_schema.JsonSchemaContext()
        ) == yuio.json_schema.OneOf(
            [
                yuio.json_schema.Integer(),
                yuio.json_schema.Ref("#/$defs/Date", "Date"),
                yuio.json_schema.String(),
            ]
        )
        assert parser.to_json_value("10") == "10"
        assert parser.to_json_value(datetime.date(2024, 1, 1)) == "2024-01-01"
        assert parser.to_json_value(10) == 5

    def test_options(self):
        class E(enum.Enum):
            pass

        parser = yuio.parse.Union(yuio.parse.Enum(E))
        assert parser.options() is None

        class E(enum.Enum):
            FOO = "foo"

        parser = yuio.parse.Union(yuio.parse.Enum(E))
        assert parser.options() == [
            yuio.widget.Option(
                value=E.FOO,
                display_text="foo",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
        ]

        class E2(enum.Enum):
            BAR = "bar"

        parser = yuio.parse.Union(yuio.parse.Enum(E), yuio.parse.Enum(E2))
        assert parser.options() == [
            yuio.widget.Option(
                value=E.FOO,
                display_text="foo",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
            yuio.widget.Option(
                value=E2.BAR,
                display_text="bar",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
        ]

    def test_parse(self):
        parser = yuio.parse.Union(
            yuio.parse.Int(), yuio.parse.OneOf(yuio.parse.Str(), ["foo", "bar"])
        )

        assert parser.parse("10") == 10
        assert parser.parse("foo") == "foo"
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse 'baz'"):
            parser.parse("baz")

        assert parser.parse_config(10) == 10
        assert parser.parse_config("foo") == "foo"
        with pytest.raises(yuio.parse.ParsingError, match=r"Can't parse 'baz'"):
            parser.parse_config("baz")

    def test_partial(self):
        parser = yuio.parse.Union()
        with pytest.raises(TypeError, match=r"requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int | str, yuio.parse.Union()])
        assert parser.parse("10") == 10
        assert parser.parse("foo") == "foo"

    def test_from_type_hint_annotated_wrong_type(self):
        with pytest.raises(
            TypeError,
            match=(
                "annotating int with Union conflicts with default "
                "parser for this type, which is Int."
            ),
        ):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Union()])

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match=r"don't provide inner parser when using .*? with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    int | str,
                    yuio.parse.Union(yuio.parse.Int(), yuio.parse.Str()),
                ]
            )


class TestWithMeta:
    def test_basics(self):
        parser = yuio.parse.WithMeta(yuio.parse.Int(), desc="desc")
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert not parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "desc"
        assert parser.describe_or_def() == "desc"
        assert parser.describe_many() == "desc"
        assert parser.describe_value(10) == "10"

    def test_secret(self):
        parser = yuio.parse.WithMeta(yuio.parse.Secret(yuio.parse.Str()), desc="...")
        assert parser.is_secret()

    def test_json_schema(self):
        parser = yuio.parse.WithMeta(yuio.parse.Int(), desc="desc")
        assert (
            parser.to_json_schema(yuio.json_schema.JsonSchemaContext())
            == yuio.json_schema.Integer()
        )
        assert parser.to_json_value(10) == 10

    def test_options(self):
        class E(enum.Enum):
            pass

        parser = yuio.parse.WithMeta(yuio.parse.Enum(E))
        assert parser.options() == []

        class E(enum.Enum):
            FOO = "foo"

        parser = yuio.parse.WithMeta(yuio.parse.Enum(E))
        assert parser.options() == [
            yuio.widget.Option(
                value=E.FOO,
                display_text="foo",
                display_text_prefix="",
                display_text_suffix="",
                comment=None,
                color_tag="none",
            ),
        ]

    def test_parse(self):
        parser = yuio.parse.WithMeta(yuio.parse.Int(), desc="desc")
        assert parser.parse("1") == 1
        assert parser.parse_config(1) == 1

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[int, yuio.parse.WithMeta(desc="desc")]
        )
        assert parser.describe() == "desc"

    def test_from_type_hint_annotated_not_partial(self):
        with pytest.raises(
            TypeError,
            match=(
                "don't provide inner parser when using WithMeta with type annotations"
            ),
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[str, yuio.parse.WithMeta(yuio.parse.Int(), desc="desc")]
            )


class TestSecret:
    def test_basics(self):
        parser = yuio.parse.Secret(yuio.parse.Str())
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == 1
        assert parser.options() is None
        assert parser.is_secret()
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() is None
        assert parser.describe_or_def() == "<str>"
        assert parser.describe_many() == "<str>"
        assert parser.describe_value(10) == "***"

    def test_from_type_hint(self):
        parser = yuio.parse.from_type_hint(yuio.parse.SecretString)
        assert isinstance(parser, yuio.parse.Secret)
        assert isinstance(parser._inner_raw, yuio.parse.Str)
        with pytest.raises(TypeError, match=r"SecretValue requires type arguments"):
            yuio.parse.from_type_hint(yuio.parse.SecretValue)

    def test_options(self):
        class E(enum.Enum):
            pass

        parser = yuio.parse.Secret(yuio.parse.Enum(E))
        assert parser.options() is None

        class E(enum.Enum):
            FOO = "foo"

        parser = yuio.parse.Secret(yuio.parse.Enum(E))
        assert parser.options() is None

    def test_parse(self):
        parser = yuio.parse.Secret(yuio.parse.Int())

        assert parser.parse("10") == yuio.secret.SecretValue(10)
        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
        ):
            parser.parse("xxx")

    def test_parse_config(self):
        parser = yuio.parse.Secret(yuio.parse.Int())

        assert parser.parse_config(10) == yuio.secret.SecretValue(10)
        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
            match=r"^Expected int, got str$",
        ):
            parser.parse_config("xxx")

    def test_parse_many(self):
        parser = yuio.parse.Secret(yuio.parse.List(yuio.parse.Int()))

        assert parser.parse("10 11 12") == yuio.secret.SecretValue([10, 11, 12])
        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
            match=r"^Can't parse value as int$",
        ):
            parser.parse("xxx")

        assert parser.parse_many(["10", "11", "12"]) == yuio.secret.SecretValue(
            [10, 11, 12]
        )
        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
            match=r"^Can't parse value as int$",
        ):
            parser.parse_many(["10", "xxx", "12"])

    def test_list_of_secrets(self):
        parser = yuio.parse.List(yuio.parse.Secret(yuio.parse.Int()))
        assert parser.is_secret()
        assert parser.parse("10 11 12") == [
            yuio.secret.SecretValue(10),
            yuio.secret.SecretValue(11),
            yuio.secret.SecretValue(12),
        ]

        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
            match=r"^Can't parse value as int$",
        ):
            parser.parse("xxx")

        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
            match=r"^Can't parse value as int$",
        ):
            parser.parse_many(["10", "xxx", "12"])

        with pytest.raises(
            yuio.parse.ParsingError,
            check=lambda e: "xxx" not in str(e) and e.raw is None,
            match=r"^In \$\[1\]:\n  Expected int, got str$",
        ):
            parser.parse_config([10, "xxx", 12])
