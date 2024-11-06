import datetime
import enum
import os.path
import pathlib
import sys

import pytest
import typing_extensions

import yuio.parse
from yuio import _typing as _t


class TestSimple:
    def test_str(self):
        parser = yuio.parse.Str()
        assert parser.parse("Test") == "Test"
        assert parser.parse("Test") == "Test"
        assert parser.parse_config("Test") == "Test"
        with pytest.raises(ValueError, match="expected a string"):
            parser.parse_config(10)
        assert isinstance(yuio.parse.from_type_hint(str), yuio.parse.Str)

    def test_str_lower(self):
        parser = yuio.parse.Str().lower()
        assert parser.parse("Test") == "test"
        assert parser.parse("Test") == "test"
        assert parser.parse_config("Test") == "test"
        with pytest.raises(ValueError, match="expected a string"):
            parser.parse_config(10)

    def test_str_upper(self):
        parser = yuio.parse.Str().upper()
        assert parser.parse("Test") == "TEST"
        assert parser.parse("Test") == "TEST"
        assert parser.parse_config("Test") == "TEST"
        with pytest.raises(ValueError, match="expected a string"):
            parser.parse_config(10)

    def test_regex(self):
        parser = yuio.parse.Str().regex(r"^a|b$")
        assert parser.parse("a") == "a"
        assert parser.parse("b") == "b"
        with pytest.raises(ValueError, match=r"should match regex '\^a\|b\$'"):
            parser.parse("foo")

    def test_int(self):
        parser = yuio.parse.Int()
        assert parser.parse("1") == 1
        assert parser.parse("1") == 1
        assert parser.parse_config(1) == 1
        assert parser.parse_config(1.0) == 1
        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("x")
        with pytest.raises(ValueError, match="expected an int"):
            parser.parse_config(1.5)
        with pytest.raises(ValueError, match="expected an int"):
            parser.parse_config("x")
        assert isinstance(yuio.parse.from_type_hint(int), yuio.parse.Int)

    def test_float(self):
        parser = yuio.parse.Float()
        assert parser.parse("1.5") == 1.5
        assert parser.parse("-10") == -10.0
        assert parser.parse("2e9") == 2e9
        assert parser.parse_config(1.0) == 1.0
        assert parser.parse_config(1.5) == 1.5
        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("x")
        with pytest.raises(ValueError, match="expected a float"):
            parser.parse_config("x")
        assert isinstance(yuio.parse.from_type_hint(float), yuio.parse.Float)


class TestBool:
    def test_basics(self):
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
        with pytest.raises(ValueError, match="expected a bool"):
            parser.parse_config("x")

        assert parser.describe() == "yes|no"
        assert parser.describe_value(True) == "yes"
        assert parser.describe_value(False) == "no"
        assert isinstance(yuio.parse.from_type_hint(bool), yuio.parse.Bool)


class TestEnum:
    def test_by_value(self):
        class Cuteness(enum.Enum):
            CATS = "Cats"
            DOGS = "Dogs"
            BLAHAJ = ":3"

        parser = yuio.parse.Enum(Cuteness)
        assert parser.parse("CATS") is Cuteness.CATS
        assert parser.parse("CATS") is Cuteness.CATS
        assert parser.parse_config("CATS") is Cuteness.CATS
        assert parser.parse("dogs") is Cuteness.DOGS
        assert parser.parse(":3") is Cuteness.BLAHAJ
        with pytest.raises(ValueError):
            parser.parse("Unchi")
        with pytest.raises(ValueError, match="expected a string"):
            parser.parse_config(10)

        assert parser.describe() == "Cats|Dogs|:3"
        assert parser.describe_value(Cuteness.BLAHAJ) == ":3"

    def test_by_name(self):
        class Colors(enum.IntEnum):
            RED = 31
            GREEN = 32
            BLUE = 34

        parser = yuio.parse.Enum(Colors, by_name=True)
        assert parser.parse("RED") is Colors.RED
        assert parser.parse("RED") is Colors.RED
        assert parser.parse_config("RED") is Colors.RED
        assert parser.parse("green") is Colors.GREEN
        assert parser.parse("Blue") is Colors.BLUE
        with pytest.raises(ValueError):
            parser.parse("Color of a beautiful sunset")
        with pytest.raises(ValueError, match="expected a string"):
            parser.parse_config(10)

        assert parser.describe() == "RED|GREEN|BLUE"
        assert parser.describe_value(Colors.RED) == "RED"

    def test_short(self):
        class Colors(enum.Enum):
            RED = "RED"
            GREEN_FORE = "GREEN_FORE"
            GREEN_BACK = "GREEN_BACK"

        parser = yuio.parse.Enum(Colors)
        assert parser.parse("R") is Colors.RED
        assert parser.parse("r") is Colors.RED
        with pytest.raises(
            ValueError, match="possible candidates are GREEN_FORE, GREEN_BACK"
        ):
            parser.parse("G")
        assert parser.parse("GREEN_F") is Colors.GREEN_FORE
        assert parser.parse_config("red") is Colors.RED
        with pytest.raises(ValueError, match="did you mean RED?"):
            parser.parse_config("r")

    def test_from_type_hint(self):
        class Cuteness(enum.Enum):
            CATS = "Cats"
            DOGS = "Dogs"
            BLAHAJ = ":3"

        parser = yuio.parse.from_type_hint(Cuteness)
        assert isinstance(parser, yuio.parse.Enum)
        assert parser.parse(":3") is Cuteness.BLAHAJ


class TestContainers:
    @pytest.mark.parametrize(
        "ctor",
        [
            lambda: yuio.parse.Optional(yuio.parse.Int()),
            lambda: yuio.parse.from_type_hint(_t.Optional[int]),
        ],
    )
    def test_optional(self, ctor):
        parser = ctor()
        assert parser.parse("1") == 1
        with pytest.raises(ValueError):
            parser.parse("")
        with pytest.raises(ValueError):
            parser.parse("asd")
        assert parser.parse_config(None) is None
        assert parser.parse_config(1) == 1
        with pytest.raises(ValueError, match="expected an int"):
            parser.parse_config("3")

        assert parser.describe() is None
        assert parser.describe_or_def() == "int"
        assert parser.describe_value(None) == "<none>"
        assert parser.describe_value_or_def(10) == "10"

    @pytest.mark.parametrize(
        "ctor",
        [
            lambda: yuio.parse.List(yuio.parse.Int()),
            lambda: yuio.parse.from_type_hint(_t.List[int]),
        ],
    )
    def test_list(self, ctor):
        parser = ctor()
        assert parser.parse("") == []
        assert parser.parse("1 2 3") == [1, 2, 3]
        assert parser.parse("1\n2") == [1, 2]
        with pytest.raises(ValueError):
            parser.parse("1:2")
        assert parser.parse_many(["1", "2"]) == [1, 2]
        assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
        with pytest.raises(ValueError, match="expected an int"):
            parser.parse_config([2, "3"])
        with pytest.raises(ValueError, match="expected a list"):
            parser.parse_config(10)

        assert parser.describe() == "int[ int[ ...]]"
        assert parser.describe_many() is None
        assert parser.describe_many_or_def() == "int"
        assert parser.describe_value([1, 2, 3]) == "1 2 3"

        with pytest.raises(ValueError, match="empty delimiter"):
            yuio.parse.List(yuio.parse.Int(), delimiter="")

    @pytest.mark.parametrize(
        "ctor",
        [
            lambda: yuio.parse.Set(yuio.parse.Int()),
            lambda: yuio.parse.from_type_hint(_t.Set[int]),
        ],
    )
    def test_set(self, ctor):
        parser = ctor()
        assert parser.parse("") == set()
        assert parser.parse("1 2 3") == {1, 2, 3}
        assert parser.parse("1 2 1") == {1, 2}
        with pytest.raises(ValueError):
            parser.parse("1:2")
        assert parser.parse_many(["1", "2"]) == {1, 2}
        assert parser.parse_config([1, 2, 1]) == {1, 2}
        with pytest.raises(ValueError, match="expected an int"):
            parser.parse_config([2, "3"])
        with pytest.raises(ValueError, match="expected a list"):
            parser.parse_config(10)

        assert parser.describe() == "int[ int[ ...]]"
        assert parser.describe_many() is None
        assert parser.describe_many_or_def() == "int"

        with pytest.raises(ValueError, match="empty delimiter"):
            yuio.parse.Set(yuio.parse.Int(), delimiter="")

    @pytest.mark.parametrize(
        "ctor",
        [
            lambda: yuio.parse.FrozenSet(yuio.parse.Int()),
            lambda: yuio.parse.from_type_hint(_t.FrozenSet[int]),
        ],
    )
    def test_frozenset(self, ctor):
        parser = ctor()
        assert parser.parse("") == frozenset()
        assert parser.parse("1 2 3") == frozenset({1, 2, 3})
        assert parser.parse("1 2 1") == frozenset({1, 2})
        with pytest.raises(ValueError):
            parser.parse("1:2")
        assert parser.parse_many(["1", "2"]) == frozenset({1, 2})
        assert parser.parse_config([1, 2, 1]) == frozenset({1, 2})
        with pytest.raises(ValueError, match="expected an int"):
            parser.parse_config([2, "3"])
        with pytest.raises(ValueError, match="expected a list"):
            parser.parse_config(10)

        assert parser.describe() == "int[ int[ ...]]"
        assert parser.describe_many() is None
        assert parser.describe_many_or_def() == "int"

        with pytest.raises(ValueError, match="empty delimiter"):
            yuio.parse.FrozenSet(yuio.parse.Int(), delimiter="")

    @pytest.mark.parametrize(
        "ctor",
        [
            lambda: yuio.parse.Dict(yuio.parse.Int(), yuio.parse.Str()),
            lambda: yuio.parse.from_type_hint(_t.Dict[int, str]),
        ],
    )
    def test_frozenset(self, ctor):
        parser = ctor()
        assert parser.parse("10:abc") == {10: "abc"}
        assert parser.parse("10:abc 11:xyz") == {10: "abc", 11: "xyz"}
        with pytest.raises(ValueError, match="expected 2 element"):
            parser.parse("10")
        assert parser.describe() == "int:str[ int:str[ ...]]"
        assert parser.describe_many() == "int:str"
        assert parser.describe_value({1: "z", 2: "y"}) == "1:z 2:y"

    def test_dict_with_pair_value(self):
        parser = yuio.parse.Dict(
            yuio.parse.Int(),
            yuio.parse.Tuple(yuio.parse.Str(), yuio.parse.Str(), delimiter=":"),
        )
        assert parser.parse("10:abc:xyz 11:abc::") == {
            10: ("abc", "xyz"),
            11: ("abc", ":"),
        }
        assert parser.describe() == "int:str:str[ int:str:str[ ...]]"
        assert (
            parser.describe_value({-5: ("xyz", "abc"), 10: ("a", "b")})
            == "-5:xyz:abc 10:a:b"
        )
        with pytest.raises(ValueError, match="empty delimiter"):
            yuio.parse.Dict(yuio.parse.Int(), yuio.parse.Int(), delimiter="")

    @pytest.mark.parametrize(
        "ctor",
        [
            lambda: yuio.parse.Tuple(
                yuio.parse.Int(), yuio.parse.Int(), yuio.parse.Str()
            ),
            lambda: yuio.parse.from_type_hint(_t.Tuple[int, int, str]),
        ],
    )
    def test_tuple(self, ctor):
        parser = ctor()
        assert parser.parse("1 2 asd") == (1, 2, "asd")
        assert parser.parse("1 2 asd dsa") == (1, 2, "asd dsa")
        with pytest.raises(ValueError, match="expected 3 element"):
            parser.parse("1 2")
        with pytest.raises(ValueError, match="as an int"):
            parser.parse("1 dsa asd")
        with pytest.raises(ValueError, match="empty tuple"):
            yuio.parse.Tuple()
        with pytest.raises(ValueError, match="empty delimiter"):
            yuio.parse.Tuple(yuio.parse.Int(), delimiter="")

        assert parser.describe() == "int int str"
        assert parser.describe_many() == ("value", "value", "value")


class TestTime:
    def test_datetime(self):
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
        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("2007 01 02")
        with pytest.raises(ValueError, match="expected a datetime"):
            parser.parse_config(10)
        assert isinstance(
            yuio.parse.from_type_hint(datetime.datetime), yuio.parse.DateTime
        )

    def test_date(self):
        parser = yuio.parse.Date()

        assert parser.parse("2007-01-02") == datetime.date(2007, 1, 2)
        assert parser.parse_config("2007-01-02") == datetime.date(2007, 1, 2)
        assert parser.parse_config(datetime.date(2007, 1, 2)) == datetime.date(
            2007, 1, 2
        )
        assert parser.parse_config(datetime.datetime(2007, 1, 2)) == datetime.date(
            2007, 1, 2
        )
        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("2007 01 02")
        with pytest.raises(ValueError, match="expected a date"):
            parser.parse_config(10)
        with pytest.raises(ValueError, match="expected a date"):
            parser.parse_config(datetime.time(10, 1))
        assert isinstance(yuio.parse.from_type_hint(datetime.date), yuio.parse.Date)

    def test_time(self):
        parser = yuio.parse.Time()

        assert parser.parse("10:05") == datetime.time(10, 5)
        assert parser.parse_config("10:05") == datetime.time(10, 5)
        assert parser.parse_config(datetime.time(10, 5)) == datetime.time(10, 5)
        assert parser.parse_config(
            datetime.datetime(2007, 1, 2, 12, 30, 5)
        ) == datetime.time(12, 30, 5)
        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("10?05")
        with pytest.raises(ValueError, match="expected a time"):
            parser.parse_config(10)
        with pytest.raises(ValueError, match="expected a time"):
            parser.parse_config(datetime.date(1996, 1, 1))
        assert isinstance(yuio.parse.from_type_hint(datetime.time), yuio.parse.Time)

    def test_timedelta(self):
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

        with pytest.raises(ValueError, match="empty timedelta"):
            parser.parse("")

        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("-")

        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("00")

        assert isinstance(
            yuio.parse.from_type_hint(datetime.timedelta), yuio.parse.TimeDelta
        )


class TestPath:
    def test_path(
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

        assert isinstance(yuio.parse.from_type_hint(pathlib.Path), yuio.parse.Path)
        assert isinstance(
            yuio.parse.from_type_hint(_t.Union[pathlib.Path, str]), yuio.parse.Path
        )

    def test_file(self, tmpdir):
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

    def test_dir(self, tmpdir):
        tmpdir.join("file.cfg").write("hi!")

        parser = yuio.parse.Dir()
        assert str(parser.parse("~")) == os.path.expanduser("~")
        assert str(parser.parse(tmpdir.strpath)) == tmpdir.strpath
        with pytest.raises(ValueError, match="doesn't exist"):
            parser.parse(tmpdir.join("subdir").strpath)
        with pytest.raises(ValueError, match="is not a directory"):
            parser.parse(tmpdir.join("file.cfg").strpath)

    def test_git_repo(self, tmpdir):
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


class TestConstraints:
    def test_bound(self):
        with pytest.raises(TypeError, match="lower and lower_inclusive"):
            yuio.parse.Bound(yuio.parse.Int(), lower=0, lower_inclusive=1)
        with pytest.raises(TypeError, match="upper and upper_inclusive"):
            yuio.parse.Bound(yuio.parse.Int(), upper=0, upper_inclusive=1)

        parser = yuio.parse.Int().bound()
        assert parser.parse("0") == 0
        assert parser.parse("-10") == -10
        assert parser.parse("10") == 10

        parser = yuio.parse.Int().gt(0)
        assert parser.parse("10") == 10
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("-1")
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("0")

        parser = yuio.parse.Int().ge(0)
        assert parser.parse("10") == 10
        assert parser.parse("0") == 0
        with pytest.raises(ValueError, match="should be greater or equal to 0"):
            parser.parse("-1")

        parser = yuio.parse.Int().lt(10)
        assert parser.parse("5") == 5
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("10")
        with pytest.raises(ValueError, match="should be lesser than 10"):
            parser.parse("11")

        parser = yuio.parse.Int().le(10)
        assert parser.parse("5") == 5
        assert parser.parse("10") == 10
        with pytest.raises(ValueError, match="should be lesser or equal to 10"):
            parser.parse("11")

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

        parser = yuio.parse.Bound(yuio.parse.Int(), lower=0, upper=5)
        assert parser.parse("2") == 2
        with pytest.raises(ValueError, match="should be greater than 0"):
            parser.parse("0")
        with pytest.raises(ValueError, match="should be lesser than 5"):
            parser.parse("5")

    def test_one_of(self):
        parser = yuio.parse.OneOf(yuio.parse.Str(), ["qux", "duo"])
        assert parser.parse("qux") == "qux"
        assert parser.parse("duo") == "duo"
        with pytest.raises(ValueError, match="qux, duo"):
            parser.parse("foo")
        with pytest.raises(ValueError, match="qux, duo"):
            parser.parse("Qux")
        with pytest.raises(ValueError, match="qux, duo"):
            parser.parse("Duo")

        assert parser.describe() == "qux|duo"

        parser = yuio.parse.OneOf(yuio.parse.Str().lower(), ["qux", "duo"])
        assert parser.parse("Qux") == "qux"
        assert parser.parse("Duo") == "duo"


class TestFunctional:
    def test_map(self):
        parser = yuio.parse.Map(yuio.parse.Int(), lambda x: x * 2)
        assert parser.parse("2") == 4
        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("foo")

    def test_apply(self):
        value = None

        def fn(x):
            nonlocal value
            value = x
            return x * 2

        parser = yuio.parse.Apply(yuio.parse.Int(), fn)
        assert parser.parse("2") == 2
        assert value == 2

        value = None

        with pytest.raises(ValueError, match="could not parse"):
            parser.parse("foo")
        assert value is None


class TestFromTypeHint:
    @pytest.mark.parametrize(
        "typehint_ctor",
        [
            lambda: _t.Optional[int],
            lambda: _t.Union[int, None],
            lambda: typing_extensions.Optional[int],
            lambda: typing_extensions.Union[int, None],
            pytest.param(
                lambda: int | None,  # type: ignore
                marks=pytest.mark.skipif(
                    sys.version_info < (3, 10), reason="New union syntax"
                ),
            ),
        ],
    )
    def test_optionals(self, typehint_ctor):
        parser = yuio.parse.from_type_hint(typehint_ctor())
        assert isinstance(parser, yuio.parse.Optional)
        assert parser.parse("10") == 10

    @pytest.mark.parametrize(
        "typehint_ctor",
        [
            lambda: _t.Union[int, str],
            lambda: typing_extensions.Union[int, str],
            pytest.param(
                lambda: int | str,  # type: ignore
                marks=pytest.mark.skipif(
                    sys.version_info < (3, 10), reason="New union syntax"
                ),
            ),
        ],
    )
    def test_union(self, typehint_ctor):
        with pytest.raises(TypeError, match="unions are not supported"):
            yuio.parse.from_type_hint(typehint_ctor())
