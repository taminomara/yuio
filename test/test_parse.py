import datetime
import enum
import os.path
import pathlib
import re
import sys
from decimal import Decimal
from fractions import Fraction

import pytest

import yuio.parse
from yuio import _typing as _t


class TestStr:
    def test_basics(self):
        parser = yuio.parse.Str()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<str>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<str>"
        assert parser.describe_value("foo") == None
        assert parser.describe_value_or_def("foo") == "foo"

    def test_parse(self):
        parser = yuio.parse.Str()
        assert parser.parse("Test") == "Test"
        assert parser.parse("Test") == "Test"
        assert parser.parse_config("Test") == "Test"
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(str), yuio.parse.Str)

    def test_lower(self):
        parser = yuio.parse.Lower(yuio.parse.Str())
        assert parser.parse("Test") == "test"
        assert parser.parse("Test") == "test"
        assert parser.parse("ῼ") == "ῳ"
        assert parser.parse_config("Test") == "test"
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

    def test_casefold(self):
        parser = yuio.parse.CaseFold(yuio.parse.Str())
        assert parser.parse("Test") == "test"
        assert parser.parse("Test") == "test"
        assert parser.parse("ῼ") == "ωι"
        assert parser.parse_config("Test") == "test"
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

    def test_upper(self):
        parser = yuio.parse.Upper(yuio.parse.Str())
        assert parser.parse("Test") == "TEST"
        assert parser.parse("Test") == "TEST"
        assert parser.parse_config("Test") == "TEST"
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

    def test_strip(self):
        parser = yuio.parse.Strip(yuio.parse.Str())
        assert parser.parse("Test  ") == "Test"
        assert parser.parse("  Test") == "Test"
        assert parser.parse_config("  Test  ") == "Test"
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

    def test_regex(self):
        parser = yuio.parse.Regex(yuio.parse.Str(), r"^a|b$")
        assert parser.parse("a") == "a"
        assert parser.parse("b") == "b"
        with pytest.raises(ValueError, match=r"should match regex '\^a\|b\$'"):
            parser.parse("foo")

    def test_regex_compiled(self):
        parser = yuio.parse.Regex(yuio.parse.Str(), re.compile(r"^a|b$"))
        assert parser.parse("a") == "a"
        assert parser.parse("b") == "b"
        with pytest.raises(ValueError, match=r"should match regex '\^a\|b\$'"):
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
            match="annotating a type with Str will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[str, yuio.parse.Str(), yuio.parse.Str()]
            )


class TestInt:
    def test_basics(self):
        parser = yuio.parse.Int()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value(10) == None
        assert parser.describe_value_or_def(10) == "10"

    def test_parse(self):
        parser = yuio.parse.Int()
        assert parser.parse("1") == 1
        assert parser.parse("1") == 1
        assert parser.parse_config(1) == 1
        assert parser.parse_config(1.0) == 1
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("x")
        with pytest.raises(ValueError, match="expected int"):
            parser.parse_config(1.5)
        with pytest.raises(ValueError, match="expected int"):
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
            match="annotating a type with Int will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Int(), yuio.parse.Int()]
            )


class TestFloat:
    def test_basics(self):
        parser = yuio.parse.Float()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<float>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<float>"
        assert parser.describe_value(10.5) == None
        assert parser.describe_value_or_def(10.5) == "10.5"

    def test_parse(self):
        parser = yuio.parse.Float()
        assert parser.parse("1.5") == 1.5
        assert parser.parse("-10") == -10.0
        assert parser.parse("2e9") == 2e9
        assert parser.parse_config(1.0) == 1.0
        assert parser.parse_config(1.5) == 1.5
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("x")
        with pytest.raises(ValueError, match="expected float"):
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
            match="annotating a type with Float will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[float, yuio.parse.Float(), yuio.parse.Float()]
            )


class TestBool:
    def test_basics(self):
        parser = yuio.parse.Bool()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "yes|no"
        assert parser.describe_or_def() == "yes|no"
        assert parser.describe_many() == "yes|no"
        assert parser.describe_many_or_def() == "yes|no"
        assert parser.describe_value(True) == "yes"
        assert parser.describe_value(False) == "no"
        assert parser.describe_value_or_def(True) == "yes"
        assert parser.describe_value_or_def(False) == "no"

    def test_parse(self):
        parser = yuio.parse.Bool()
        assert parser.parse("y") is True
        assert parser.parse("yes") is True
        assert parser.parse("yEs") is True
        assert parser.parse("n") is False
        assert parser.parse("no") is False
        assert parser.parse("nO") is False
        with pytest.raises(ValueError):
            parser.parse("Meh")
        assert parser.parse_config(True) is True
        assert parser.parse_config(False) is False
        with pytest.raises(ValueError, match="expected bool"):
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
            match="annotating a type with Bool will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[bool, yuio.parse.Bool(), yuio.parse.Bool()]
            )


class TestEnum:
    class Cuteness(enum.Enum):
        CATS = "Cats"
        DOGS = "Dogs"
        BLAHAJ = ":3"

    class Colors(enum.IntEnum):
        RED = 31
        GREEN = 32
        BLUE = 34

    def test_basics_by_value(self):
        parser = yuio.parse.Enum(self.Cuteness)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "Cats|Dogs|:3"
        assert parser.describe_or_def() == "Cats|Dogs|:3"
        assert parser.describe_many() == "Cats|Dogs|:3"
        assert parser.describe_many_or_def() == "Cats|Dogs|:3"
        assert parser.describe_value(self.Cuteness.BLAHAJ) == ":3"
        assert parser.describe_value_or_def(self.Cuteness.BLAHAJ) == ":3"

    def test_basics_by_name(self):
        parser = yuio.parse.Enum(self.Cuteness, by_name=True)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "CATS|DOGS|BLAHAJ"
        assert parser.describe_or_def() == "CATS|DOGS|BLAHAJ"
        assert parser.describe_many() == "CATS|DOGS|BLAHAJ"
        assert parser.describe_many_or_def() == "CATS|DOGS|BLAHAJ"
        assert parser.describe_value(self.Cuteness.BLAHAJ) == "BLAHAJ"
        assert parser.describe_value_or_def(self.Cuteness.BLAHAJ) == "BLAHAJ"

    def test_by_value(self):
        parser = yuio.parse.Enum(self.Cuteness)
        assert parser.parse("CATS") is self.Cuteness.CATS
        assert parser.parse("CATS") is self.Cuteness.CATS
        assert parser.parse_config("CATS") is self.Cuteness.CATS
        assert parser.parse("dogs") is self.Cuteness.DOGS
        assert parser.parse(":3") is self.Cuteness.BLAHAJ
        with pytest.raises(ValueError):
            parser.parse("Unchi")
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

    def test_by_name(self):
        parser = yuio.parse.Enum(self.Colors, by_name=True)
        assert parser.parse("RED") is self.Colors.RED
        assert parser.parse("RED") is self.Colors.RED
        assert parser.parse_config("RED") is self.Colors.RED
        assert parser.parse("green") is self.Colors.GREEN
        assert parser.parse("Blue") is self.Colors.BLUE
        with pytest.raises(ValueError):
            parser.parse("Color of a beautiful sunset")
        with pytest.raises(ValueError, match="expected string"):
            parser.parse_config(10)

        assert parser.describe() == "RED|GREEN|BLUE"
        assert parser.describe_value(self.Colors.RED) == "RED"

    def test_short(self):
        class Colors(enum.Enum):
            RED = "RED"
            GREEN_FORE = "GREEN_FORE"
            GREEN_BACK = "GREEN_BACK"

        parser = yuio.parse.Enum(Colors)
        assert parser.parse("R") is Colors.RED
        assert parser.parse("r") is Colors.RED
        with pytest.raises(
            ValueError, match="possible candidates are 'GREEN_FORE', 'GREEN_BACK'"
        ):
            parser.parse("G")
        assert parser.parse("GREEN_F") is Colors.GREEN_FORE
        assert parser.parse_config("red") is Colors.RED
        with pytest.raises(ValueError, match="did you mean RED?"):
            parser.parse_config("r")

    def test_from_type_hint(self):
        parser = yuio.parse.from_type_hint(self.Cuteness)
        assert isinstance(parser, yuio.parse.Enum)
        assert parser.parse(":3") is self.Cuteness.BLAHAJ

    def test_partial(self):
        parser = yuio.parse.Enum()
        with pytest.raises(TypeError, match="Enum requires an inner parser"):
            parser.parse("asd")  # type: ignore

        parser = yuio.parse.Enum(by_name=True)
        with pytest.raises(TypeError, match="Enum requires an inner parser"):
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
            match="annotating a type with Enum will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[self.Cuteness, yuio.parse.Enum(), yuio.parse.Enum()]
            )

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using Enum with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[self.Colors, yuio.parse.Enum(self.Colors)]
            )


class TestDecimal:
    def test_basics(self):
        parser = yuio.parse.Decimal()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<decimal>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<decimal>"
        assert parser.describe_value(Decimal(10)) == None
        assert parser.describe_value_or_def(Decimal(10)) == "10"

    def test_parse(self):
        parser = yuio.parse.Decimal()
        assert parser.parse("1.5") == Decimal("1.5")
        assert parser.parse("-10") == Decimal("-10")
        assert parser.parse_config(1.0) == Decimal("1.0")
        assert parser.parse_config("1.5") == Decimal("1.5")
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("x")
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse_config("x")
        with pytest.raises(ValueError, match="expected int or float or string"):
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
            match="annotating a type with Decimal will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[Decimal, yuio.parse.Decimal(), yuio.parse.Decimal()]
            )


class TestFraction:
    def test_basics(self):
        parser = yuio.parse.Fraction()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<fraction>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<fraction>"
        assert parser.describe_value(Fraction(10)) == None
        assert parser.describe_value_or_def(Fraction(10)) == "10"

    def test_parse(self):
        parser = yuio.parse.Fraction()
        assert parser.parse("1/3") == Fraction("1/3")
        assert parser.parse("-10") == Fraction("-10")
        assert parser.parse_config(1.0) == Fraction("1.0")
        assert parser.parse_config("1/3") == Fraction("1/3")
        assert parser.parse_config([2, 5]) == Fraction("2/5")
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("x")
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse_config("x")
        with pytest.raises(
            ValueError,
            match="expected int or float or fraction string or a tuple of two ints",
        ):
            parser.parse_config([])
        with pytest.raises(ValueError, match="can't parse value 1/0 as a fraction"):
            parser.parse_config([1, 0])

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
            match="annotating a type with Fraction will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[Fraction, yuio.parse.Fraction(), yuio.parse.Fraction()]
            )


class TestJson:
    def test_basics(self):
        parser = yuio.parse.Json()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<json>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<json>"
        assert parser.describe_value(dict(a=0)) == None
        assert parser.describe_value_or_def(dict(a=0)) == "{'a': 0}"

    def test_unstructured(self):
        parser = yuio.parse.Json()
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        assert parser.parse_config("[1, 2, 3]") == "[1, 2, 3]"
        with pytest.raises(ValueError, match="unable to decode JSON"):
            parser.parse("x")
        assert isinstance(
            yuio.parse.from_type_hint(yuio.parse.JsonValue), yuio.parse.Json
        )

    def test_structured(self):
        parser = yuio.parse.Json(yuio.parse.List(yuio.parse.Int()))
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        with pytest.raises(ValueError, match="unable to decode JSON"):
            parser.parse("x")
        with pytest.raises(ValueError, match="expected list, got str"):
            parser.parse_config("[1, 2, 3]")

    def test_from_type_hint_annotated_unstructured(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[yuio.parse.JsonValue, yuio.parse.Json()]
        )
        assert parser.parse("1.5") == 1.5

    def test_from_type_hint_annotated_structured(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[list[int], yuio.parse.Json()])
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        with pytest.raises(ValueError, match="unable to decode JSON"):
            parser.parse("x")
        with pytest.raises(ValueError, match="expected list, got str"):
            parser.parse_config("[1, 2, 3]")

    def test_from_type_hint_annotated_shadowing(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[yuio.parse.JsonValue, yuio.parse.Json(), yuio.parse.Json()]
        )
        assert parser.parse("[1, 2, 3]") == [1, 2, 3]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]

    def test_from_type_hint_annotated_unstructured(self):
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using Json with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[yuio.parse.JsonValue, yuio.parse.Json(yuio.parse.Int())]
            )

    def test_from_type_hint_annotated_structured(self):
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using Json with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Json(yuio.parse.Int())]
            )


class TestDateTime:
    def test_basics(self):
        parser = yuio.parse.DateTime()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<date-time>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<date-time>"
        assert parser.describe_value(datetime.datetime(2025, 1, 1)) == None
        assert (
            parser.describe_value_or_def(datetime.datetime(2025, 1, 1))
            == "2025-01-01 00:00:00"
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
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("2007 01 02")
        with pytest.raises(ValueError, match="expected str"):
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
            match="annotating a type with DateTime will override all previous annotations",
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
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<date>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<date>"
        assert parser.describe_value(datetime.date(2025, 1, 1)) == None
        assert parser.describe_value_or_def(datetime.date(2025, 1, 1)) == "2025-01-01"

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
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("2007 01 02")
        with pytest.raises(ValueError, match="expected str"):
            parser.parse_config(10)
        with pytest.raises(ValueError, match="expected str"):
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
            match="annotating a type with Date will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[datetime.date, yuio.parse.Date(), yuio.parse.Date()]
            )


class TestTime:
    def test_basics(self):
        parser = yuio.parse.Time()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<time>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<time>"
        assert parser.describe_value(datetime.time()) == None
        assert parser.describe_value_or_def(datetime.time()) == "00:00:00"

    def test_parse(self):
        parser = yuio.parse.Time()

        assert parser.parse("10:05") == datetime.time(10, 5)
        assert parser.parse_config("10:05") == datetime.time(10, 5)
        assert parser.parse_config(datetime.time(10, 5)) == datetime.time(10, 5)
        assert parser.parse_config(
            datetime.datetime(2007, 1, 2, 12, 30, 5)
        ) == datetime.time(12, 30, 5)
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("10?05")
        with pytest.raises(ValueError, match="expected str"):
            parser.parse_config(10)
        with pytest.raises(ValueError, match="expected str"):
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
            match="annotating a type with Time will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[datetime.time, yuio.parse.Time(), yuio.parse.Time()]
            )


class TestTimeDelta:
    def test_basics(self):
        parser = yuio.parse.TimeDelta()
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<time-delta>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<time-delta>"
        assert parser.describe_value(datetime.timedelta(hours=10)) == None
        assert parser.describe_value_or_def(datetime.timedelta(hours=10)) == "10:00:00"

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

        with pytest.raises(ValueError, match="empty timedelta"):
            parser.parse("")

        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("-")

        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("00:00,")

        with pytest.raises(ValueError, match="can't parse"):
            parser.parse(",00:00")

        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("00")

        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("1 megasecond")

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
            match="annotating a type with TimeDelta will override all previous annotations",
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
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<path>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<path>"
        assert parser.describe_value(pathlib.Path("/")) == None
        assert parser.describe_value_or_def(pathlib.Path("/")) == os.path.sep

    def test_parse(
        self,
    ):
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
        with pytest.raises(ValueError, match="expected string"):
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
        with pytest.raises(ValueError, match="should have extension .cfg, .txt"):
            parser.parse("file.sql")

    def test_from_type_hint(self):
        assert isinstance(yuio.parse.from_type_hint(pathlib.Path), yuio.parse.Path)
        assert isinstance(
            yuio.parse.from_type_hint(_t.Union[pathlib.Path, str]), yuio.parse.Path
        )
        assert isinstance(
            yuio.parse.from_type_hint(_t.Union[str, pathlib.Path]), yuio.parse.Path
        )

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
        with pytest.raises(ValueError, match="should have extension .x"):
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
            match="annotating a type with Path will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[pathlib.Path, yuio.parse.Path(), yuio.parse.Path()]
            )


class TestExistingPath:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.ExistingPath()
        with pytest.raises(ValueError, match="doesn't exist"):
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
        with pytest.raises(ValueError, match="already exists"):
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
        with pytest.raises(ValueError, match="doesn't exist"):
            parser.parse(tmpdir.join("file.txt").strpath)
        with pytest.raises(ValueError, match="is not a file"):
            parser.parse(tmpdir.strpath)

        parser = yuio.parse.File(extensions=[".cfg", ".txt"])
        assert (
            str(parser.parse(tmpdir.join("file.cfg").strpath))
            == tmpdir.join("file.cfg").strpath
        )
        with pytest.raises(ValueError, match="doesn't exist"):
            parser.parse(tmpdir.join("file.txt").strpath)
        with pytest.raises(ValueError, match="should have extension .cfg, .txt"):
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
        with pytest.raises(ValueError, match="doesn't exist"):
            parser.parse(tmpdir.join("subdir").strpath)
        with pytest.raises(ValueError, match="is not a directory"):
            parser.parse(tmpdir.join("file.cfg").strpath)

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[pathlib.Path, yuio.parse.Dir()])
        assert isinstance(parser, yuio.parse.Dir)


class TestGitRepo:
    def test_parse(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.GitRepo()
        with pytest.raises(ValueError, match="is not a git repository"):
            parser.parse(tmpdir.strpath)
        with pytest.raises(ValueError, match="doesn't exist"):
            parser.parse(tmpdir.join("subdir").strpath)
        with pytest.raises(ValueError, match="is not a directory"):
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
        with pytest.raises(TypeError, match="lower and lower_inclusive"):
            yuio.parse.Bound(yuio.parse.Int(), lower=0, lower_inclusive=1)
        with pytest.raises(TypeError, match="upper and upper_inclusive"):
            yuio.parse.Bound(yuio.parse.Int(), upper=0, upper_inclusive=1)

    def test_empty_bounds(self):
        parser = yuio.parse.Bound(yuio.parse.Int())
        assert parser.parse("0") == 0
        assert parser.parse("-10") == -10
        assert parser.parse("10") == 10

    def test_gt(self):
        parser = yuio.parse.Gt(yuio.parse.Int(), 0)
        assert parser.parse("10") == 10
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("-1")
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("0")

    def test_ge(self):
        parser = yuio.parse.Ge(yuio.parse.Int(), 0)
        assert parser.parse("10") == 10
        assert parser.parse("0") == 0
        with pytest.raises(ValueError, match="should be greater or equal to 0"):
            parser.parse("-1")

    def test_lt(self):
        parser = yuio.parse.Lt(yuio.parse.Int(), 10)
        assert parser.parse("5") == 5
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("10")
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("11")

    def test_le(self):
        parser = yuio.parse.Le(yuio.parse.Int(), 10)
        assert parser.parse("5") == 5
        assert parser.parse("10") == 10
        with pytest.raises(ValueError, match="should be lesser or equal to 10"):
            parser.parse("11")

    def test_range_inclusive(self):
        parser = yuio.parse.Bound(
            yuio.parse.Int(), lower_inclusive=0, upper_inclusive=5
        )
        assert parser.parse("0") == 0
        assert parser.parse("2") == 2
        assert parser.parse("5") == 5
        with pytest.raises(ValueError, match="should be greater or equal to 0"):
            parser.parse("-1")
        with pytest.raises(ValueError, match="should be lesser or equal to 5"):
            parser.parse("6")

    def test_range_non_inclusive(self):
        parser = yuio.parse.Bound(yuio.parse.Int(), lower=0, upper=5)
        assert parser.parse("2") == 2
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("0")
        with pytest.raises(ValueError, match="should be lesser than 5"):
            parser.parse("5")

    def test_partial(self):
        parser = yuio.parse.Bound()
        with pytest.raises(TypeError, match="Bound requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[int, yuio.parse.Bound(lower_inclusive=0, upper=10)]
        )
        assert parser.parse("0") == 0
        assert parser.parse("9") == 9
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("10")

    def test_from_type_hint_annotated_combine(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[
                int, yuio.parse.Bound(lower_inclusive=0), yuio.parse.Bound(upper=10)
            ]
        )
        assert parser.parse("0") == 0
        assert parser.parse("9") == 9
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("10")

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using Bound with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Bound(yuio.parse.Int())]
            )

    def test_gt_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Gt(0)])
        assert parser.parse("10") == 10
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("-1")
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("0")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Gt(yuio.parse.Int(), 0, 0)])  # type: ignore

    def test_ge_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Ge(0)])
        assert parser.parse("10") == 10
        assert parser.parse("0") == 0
        with pytest.raises(ValueError, match="should be greater or equal to 0"):
            parser.parse("-1")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Ge(yuio.parse.Int(), 0, 0)])  # type: ignore

    def test_lt_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Lt(10)])
        assert parser.parse("5") == 5
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("10")
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("11")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Lt(yuio.parse.Int(), 10, 0)])  # type: ignore

    def test_le_annotated(self):
        parser = yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Le(10)])
        assert parser.parse("5") == 5
        assert parser.parse("10") == 10
        with pytest.raises(ValueError, match="should be lesser or equal to 10"):
            parser.parse("11")
        with pytest.raises(TypeError):
            yuio.parse.from_type_hint(_t.Annotated[int, yuio.parse.Le(yuio.parse.Int(), 10, 0)])  # type: ignore


class TestOneOf:
    def test_parse(self):
        parser = yuio.parse.OneOf(yuio.parse.Str(), ["qux", "duo"])
        assert parser.parse("qux") == "qux"
        assert parser.parse("duo") == "duo"
        with pytest.raises(ValueError, match="'qux', 'duo'"):
            parser.parse("foo")
        with pytest.raises(ValueError, match="'qux', 'duo'"):
            parser.parse("Qux")
        with pytest.raises(ValueError, match="'qux', 'duo'"):
            parser.parse("Duo")

    def test_partial(self):
        parser = yuio.parse.OneOf([])
        with pytest.raises(TypeError, match="OneOf requires an inner parser"):
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
        with pytest.raises(ValueError, match="'qux', 'duo'"):
            parser.parse("foo")
        with pytest.raises(ValueError, match="'qux', 'duo'"):
            parser.parse("Qux")
        with pytest.raises(ValueError, match="'qux', 'duo'"):
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
            match="don't provide inner parser when using OneOf with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.OneOf(yuio.parse.Int(), [1, 2, 3])]
            )


class TestMap:
    def test_basics(self):
        parser = yuio.parse.Map(yuio.parse.Int(), lambda x: x)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value(10) == None
        assert parser.describe_value_or_def(10) == "10"

    def test_basics_collection(self):
        parser = yuio.parse.Map(yuio.parse.List(yuio.parse.Int()), lambda x: x)
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse_many(["1", "2", "3"]) == [1, 2, 3]
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value([]) == ""
        assert parser.describe_value_or_def([]) == ""

    def test_parse(self):
        parser = yuio.parse.Map(yuio.parse.Int(), lambda x: x * 2)
        assert parser.parse("2") == 4
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("foo")

    def test_partial(self):
        parser = yuio.parse.Map(lambda x: x)
        with pytest.raises(TypeError, match="Map requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[int, yuio.parse.Map[int, int](lambda x: x * 2)]
        )
        assert parser.parse("2") == 4
        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("foo")

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using Map with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Map(yuio.parse.Int(), lambda x: x)]
            )


class TestApply:
    def test_basics(self):
        parser = yuio.parse.Apply(yuio.parse.Int(), lambda x: None)
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value(10) == None
        assert parser.describe_value_or_def(10) == "10"

    def test_basics_collection(self):
        parser = yuio.parse.Apply(yuio.parse.List(yuio.parse.Int()), lambda x: None)
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse_many(["1", "2", "3"]) == [1, 2, 3]
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value([]) == ""
        assert parser.describe_value_or_def([]) == ""

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

        with pytest.raises(ValueError, match="can't parse"):
            parser.parse("foo")
        assert value is None

    def test_partial(self):
        parser = yuio.parse.Apply(print)
        with pytest.raises(TypeError, match="Apply requires an inner parser"):
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
            match="don't provide inner parser when using Apply with type annotations",
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
        assert parser.parse("1 2 3") == ctor([1, 2, 3])
        assert parser.parse_config([1, 2, 3]) == ctor([1, 2, 3])
        assert parser.parse_many(["1", "2", "3"]) == ctor([1, 2, 3])
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value(ctor([1, 2, 3])) == "1 2 3"
        assert parser.describe_value_or_def(ctor([1, 2, 3])) == "1 2 3"

        with pytest.raises(yuio.parse.ParsingError, match="expected .*?, got int"):
            parser.parse_config(123)

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
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value(ctor([1, 2, 3])) == "1,2,3"
        assert parser.describe_value_or_def(ctor([1, 2, 3])) == "1,2,3"

    def test_partial(self, test_params):
        parser_cls, _ = test_params

        parser = parser_cls()
        with pytest.raises(TypeError, match="requires an inner parser"):
            parser.parse("asd")

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="new typing syntax")
    def test_from_type_hint_annotated(self, test_params):
        parser_cls, ctor = test_params
        parser = yuio.parse.from_type_hint(_t.Annotated[ctor[int], parser_cls()])
        assert parser.parse("1 2 3") == ctor([1, 2, 3])
        parser = yuio.parse.from_type_hint(
            _t.Annotated[ctor[int], parser_cls(delimiter=",")]
        )
        assert parser.parse("1, 2, 3") == ctor([1, 2, 3])

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="new typing syntax")
    def test_from_type_hint_annotated_shadows(self, test_params):
        parser_cls, ctor = test_params
        with pytest.raises(
            TypeError,
            match="annotating a type with .*? will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[ctor[int], parser_cls(), parser_cls()]
            )

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="new typing syntax")
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

    @pytest.mark.skipif(sys.version_info < (3, 10), reason="new typing syntax")
    def test_from_type_hint_annotated_non_partial(self, test_params):
        parser_cls, ctor = test_params
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using .*? with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[ctor[int], parser_cls(yuio.parse.Int())]
            )


class TestDict:
    def test_parse(self):
        parser = yuio.parse.Dict(yuio.parse.Int(), yuio.parse.Str())
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse("1:a 2:b") == {1: "a", 2: "b"}
        assert parser.parse_config({1: "a", 2: "b"}) == {1: "a", 2: "b"}
        assert parser.parse_config([(1, "a"), (2, "b")]) == {1: "a", 2: "b"}
        assert parser.parse_many(["1:a", "2:b"]) == {1: "a", 2: "b"}
        assert parser.describe() == "<int>:<str>[ <int>:<str>[ ...]]"
        assert parser.describe_or_def() == "<int>:<str>[ <int>:<str>[ ...]]"
        assert parser.describe_many() == "<int>:<str>"
        assert parser.describe_many_or_def() == "<int>:<str>"
        assert parser.describe_value({1: "a", 2: "b"}) == "1:a 2:b"
        assert parser.describe_value_or_def({1: "a", 2: "b"}) == "1:a 2:b"

        with pytest.raises(
            yuio.parse.ParsingError, match="expected dict or list, got int"
        ):
            parser.parse_config(123)
        with pytest.raises(yuio.parse.ParsingError, match="expected int, got str"):
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
        assert parser.describe_many_or_def() == "<int>-<str>"
        assert parser.describe_value({1: "a", 2: "b"}) == "1-a,2-b"
        assert parser.describe_value_or_def({1: "a", 2: "b"}) == "1-a,2-b"

    def test_partial(self):
        parser = yuio.parse.Dict()
        with pytest.raises(TypeError, match="requires an inner parser"):
            parser.parse("asd")  # type: ignore
        parser = yuio.parse.Dict(yuio.parse.Int())  # type: ignore
        with pytest.raises(TypeError, match="requires an inner parser"):
            parser.parse("asd")

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[_t.Dict[int, str], yuio.parse.Dict()]
        )
        assert parser.parse("1:a 2:b") == {1: "a", 2: "b"}
        parser = yuio.parse.from_type_hint(
            _t.Annotated[
                _t.Dict[int, str], yuio.parse.Dict(delimiter=",", pair_delimiter="-")
            ]
        )
        assert parser.parse("1-a,2-b") == {1: "a", 2: "b"}

    def test_from_type_hint_annotated_shadows(self):
        with pytest.raises(
            TypeError,
            match="annotating a type with Dict will override all previous annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[_t.Dict[int, str], yuio.parse.Dict(), yuio.parse.Dict()]
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
            match="don't provide inner parser when using Dict with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    _t.Dict[str, int],
                    yuio.parse.Dict(yuio.parse.Str(), yuio.parse.Int()),
                ]
            )


class TestOptional:
    def test_basics(self):
        parser = yuio.parse.Optional(yuio.parse.Int())
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == None
        assert parser.describe_or_def() == "<int>"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value(10) == None
        assert parser.describe_value_or_def(10) == "10"
        assert parser.describe_value(None) == "<none>"
        assert parser.describe_value_or_def(None) == "<none>"

    def test_basics_collection(self):
        parser = yuio.parse.Optional(yuio.parse.List(yuio.parse.Int()))
        assert parser.supports_parse_many()
        assert parser.get_nargs() == "*"
        assert parser.parse_many(["1", "2", "3"]) == [1, 2, 3]
        assert parser.describe() == "<int>[ <int>[ ...]]"
        assert parser.describe_or_def() == "<int>[ <int>[ ...]]"
        assert parser.describe_many() == None
        assert parser.describe_many_or_def() == "<int>"
        assert parser.describe_value([]) == ""
        assert parser.describe_value_or_def([]) == ""
        assert parser.describe_value(None) == "<none>"
        assert parser.describe_value_or_def(None) == "<none>"

    def test_parse(self):
        parser = yuio.parse.Optional(yuio.parse.Int())
        assert parser.parse("1") == 1
        assert parser.parse_config(1) == 1
        assert parser.parse_config(None) == None
        assert parser.supports_parse_many() is False

    def test_partial(self):
        parser = yuio.parse.Optional()
        with pytest.raises(TypeError, match="requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[_t.List[int], yuio.parse.Optional()]
        )
        assert parser.parse_config(None) == None
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]

    def test_from_type_hint_annotated_non_partial(self):
        with pytest.raises(
            TypeError,
            match="don't provide inner parser when using .*? with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[int, yuio.parse.Optional(yuio.parse.Int())]
            )


class TestUnion:
    def test_basics(self):
        parser = yuio.parse.Union(yuio.parse.Int(), yuio.parse.Str())
        assert not parser.supports_parse_many()
        assert parser.get_nargs() == None
        with pytest.raises(RuntimeError):
            assert parser.parse_many(["1", "2", "3"])
        assert parser.describe() == "<int>|<str>"
        assert parser.describe_or_def() == "<int>|<str>"
        assert parser.describe_many() == "<int>|<str>"
        assert parser.describe_many_or_def() == "<int>|<str>"
        assert parser.describe_value(10) == None
        assert parser.describe_value_or_def(10) == "10"

    def test_parse(self):
        parser = yuio.parse.Union(
            yuio.parse.Int(), yuio.parse.OneOf(yuio.parse.Str(), ["foo", "bar"])
        )

        assert parser.parse("10") == 10
        assert parser.parse("foo") == "foo"
        with pytest.raises(ValueError, match="can't parse 'baz'"):
            parser.parse("baz")

        assert parser.parse_config(10) == 10
        assert parser.parse_config("foo") == "foo"
        with pytest.raises(ValueError, match="can't parse 'baz'"):
            parser.parse_config("baz")

    def test_partial(self):
        parser = yuio.parse.Union()
        with pytest.raises(TypeError, match="requires an inner parser"):
            parser.parse("asd")  # type: ignore

    def test_from_type_hint_annotated(self):
        parser = yuio.parse.from_type_hint(
            _t.Annotated[_t.Union[int, str], yuio.parse.Union()]
        )
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
            match="don't provide inner parser when using .*? with type annotations",
        ):
            yuio.parse.from_type_hint(
                _t.Annotated[
                    _t.Union[int, str],
                    yuio.parse.Union(yuio.parse.Int(), yuio.parse.Str()),
                ]
            )
