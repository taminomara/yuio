# pyright: reportCallIssue=false, reportGeneralTypeIssues=false, reportArgumentType=false

import copy
import enum

import jsonschema
import pytest

import yuio.config
import yuio.json_schema
import yuio.parse

import typing


class TestBasics:
    def test_default(self):
        class MyConfig(yuio.config.Config):
            f1: str = "1"
            f2: str = "2"

        c = MyConfig()
        assert c.f1 == "1"
        assert c.f2 == "2"

        c = MyConfig(f2="b")
        assert c.f1 == "1"
        assert c.f2 == "b"

        c = MyConfig(f1="a", f2="b")
        assert c.f1 == "a"
        assert c.f2 == "b"

    def test_default_field(self):
        class MyConfig(yuio.config.Config):
            f1: str = yuio.config.field(default="1")
            f2: str = yuio.config.field(default="2")

        c = MyConfig()
        assert c.f1 == "1"
        assert c.f2 == "2"

        c = MyConfig(f2="b")
        assert c.f1 == "1"
        assert c.f2 == "b"

        c = MyConfig(f1="a", f2="b")
        assert c.f1 == "a"
        assert c.f2 == "b"

    def test_missing(self):
        class MyConfig(yuio.config.Config):
            f1: str
            f2: str

        c = MyConfig()
        with pytest.raises(AttributeError, match=r"f1 is not configured"):
            _ = c.f1
        with pytest.raises(AttributeError, match=r"f2 is not configured"):
            _ = c.f2

        c = MyConfig(f1="a")
        assert c.f1 == "a"
        with pytest.raises(AttributeError, match=r"f2 is not configured"):
            _ = c.f2

        c = MyConfig(f1="a", f2="b")
        assert c.f1 == "a"
        assert c.f2 == "b"

    def test_missing_field(self):
        class MyConfig(yuio.config.Config):
            f1: str = yuio.config.field()
            f2: str = yuio.config.field()

        c = MyConfig()
        with pytest.raises(AttributeError, match=r"f1 is not configured"):
            _ = c.f1
        with pytest.raises(AttributeError, match=r"f2 is not configured"):
            _ = c.f2

        c = MyConfig(f1="a")
        assert c.f1 == "a"
        with pytest.raises(AttributeError, match=r"f2 is not configured"):
            _ = c.f2

        c = MyConfig(f1="a", f2="b")
        assert c.f1 == "a"
        assert c.f2 == "b"

    def test_init(self):
        class MyConfig(yuio.config.Config):
            f1: str
            f2: str

        with pytest.raises(TypeError, match=r"unknown field: x"):
            MyConfig(x=1)

    def test_repr(self):
        class MyConfig(yuio.config.Config):
            f1: str = "1"
            f2: str

        assert repr(MyConfig()) == "MyConfig(f1='1', f2=yuio.MISSING)"
        assert repr(MyConfig(f1="x")) == "MyConfig(f1='x', f2=yuio.MISSING)"
        assert repr(MyConfig(f2="y")) == "MyConfig(f1='1', f2='y')"

    def test_inheritance(self):
        class Parent(yuio.config.Config):
            field_without_default: int
            field_with_default: int = 0
            field_without_default_that_gets_overridden_with_default: int
            field_without_default_that_gets_overridden_without_default: int
            field_with_default_that_gets_overridden_with_default: int = 0
            field_with_default_that_gets_overridden_without_default: int = 0

        class Child(Parent):
            field_without_default_that_gets_overridden_with_default: int = 0
            field_without_default_that_gets_overridden_without_default: int
            field_with_default_that_gets_overridden_with_default: int = 0
            field_with_default_that_gets_overridden_without_default: int

            new_field: str = "x"

        with pytest.raises(TypeError, match=r"unknown field: new_field"):
            Parent(new_field="-_-")

        c = Child(
            field_without_default=1,
            field_with_default=2,
            field_without_default_that_gets_overridden_with_default=3,
            field_without_default_that_gets_overridden_without_default=4,
            field_with_default_that_gets_overridden_with_default=5,
            field_with_default_that_gets_overridden_without_default=6,
            new_field="7",
        )

        assert c.field_without_default == 1
        assert c.field_with_default == 2
        assert c.field_without_default_that_gets_overridden_with_default == 3
        assert c.field_without_default_that_gets_overridden_without_default == 4
        assert c.field_with_default_that_gets_overridden_with_default == 5
        assert c.field_with_default_that_gets_overridden_without_default == 6
        assert c.new_field == "7"

        c = Child()

        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.field_without_default
        assert c.field_with_default == 0
        assert c.field_without_default_that_gets_overridden_with_default == 0
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.field_without_default_that_gets_overridden_without_default
        assert c.field_with_default_that_gets_overridden_with_default == 0
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.field_with_default_that_gets_overridden_without_default
        assert c.new_field == "x"

    def test_subconfig(self):
        class SubConfig(yuio.config.Config):
            a: str = "a"
            b: str

        class MyConfig(yuio.config.Config):
            sub: SubConfig
            x: int

        assert (
            repr(MyConfig())
            == "MyConfig(sub=SubConfig(a='a', b=yuio.MISSING), x=yuio.MISSING)"
        )
        assert (
            repr(MyConfig(sub=SubConfig(b="2")))
            == "MyConfig(sub=SubConfig(a='a', b='2'), x=yuio.MISSING)"
        )

    def test_update(self):
        class MyConfig(yuio.config.Config):
            f1: str = "f1"
            f2: str

        c = MyConfig(f1="f1.2")
        c.update(MyConfig(f1="f1.3"))
        assert c.f1 == "f1.3"

        c = MyConfig(f1="f1.2")
        c.update(MyConfig())
        assert c.f1 == "f1.2"

        c = MyConfig(f1="f1.2")
        c.update(MyConfig(f2="f2"))
        assert c.f1 == "f1.2"
        assert c.f2 == "f2"

        c = MyConfig(f1="f1.2", f2="f2")
        c.update(MyConfig(f2="f2.2"))
        assert c.f1 == "f1.2"
        assert c.f2 == "f2.2"

    def test_update_recursive(self):
        class SubConfig(yuio.config.Config):
            a: str = "a"
            b: str

        class MyConfig(yuio.config.Config):
            sub: SubConfig
            x: int

        c = MyConfig(sub=dict(b="2"))
        c.update(dict(x=2, sub=dict(a="a.2")))

        assert c.x == 2
        assert c.sub.a == "a.2"
        assert c.sub.b == "2"

    def test_update_incompatible(self):
        class MyConfig1(yuio.config.Config):
            pass

        class MyConfig2(yuio.config.Config):
            pass

        c1 = MyConfig1()
        with pytest.raises(TypeError, match=r"updating from an incompatible config"):
            c1.update(MyConfig2())

        with pytest.raises(TypeError, match=r"expected a dict or a config class"):
            c1.update(123)

    class SubConfig(yuio.config.Config):
        y: int

    class ResolveConfig(yuio.config.Config):
        x: "TestBasics.SubConfig"

    def test_resolve(self):
        c = TestBasics.ResolveConfig(x=dict(y=10))
        assert c.x.y == 10

    def test_resolve_locals(self):
        Ty = int

        class ResolveConfig(yuio.config.Config):
            f: "Ty"  # type: ignore

        with pytest.raises(
            NameError, match=r"forward references do not work inside functions"
        ):
            ResolveConfig(f=10)

    def test_unannotated_field_error(self):
        with pytest.raises(
            TypeError, match=r"field without annotations is not allowed"
        ):

            class MyConfig(yuio.config.Config):  # pyright: ignore[reportUnusedClass]
                f1 = yuio.config.field(default="1")

    def test_field_edge_cases(self):
        with pytest.raises(
            TypeError, match=r"positional arguments are not allowed in configs"
        ):

            class PosConfig(yuio.config.Config):
                f1: int = yuio.config.positional()

            PosConfig()

        with pytest.raises(TypeError, match=r"got an empty env variable name"):

            class EnvConfig(yuio.config.Config):
                f1: int = yuio.config.field(env="")

            EnvConfig()

        with pytest.raises(TypeError, match=r"should have at least one flag"):

            class FlagConfig(yuio.config.Config):
                f1: int = yuio.config.field(flags=[])

            FlagConfig()

    def test_nested_config_edge_cases(self):
        class Sub(yuio.config.Config):
            x: int = 0

        with pytest.raises(TypeError, match=r"nested configs can't be positional"):

            class PosNested(yuio.config.Config, _allow_positionals=True):
                sub: Sub = yuio.config.positional()

            PosNested()

        with pytest.raises(
            TypeError, match=r"nested configs should have exactly one flag"
        ):

            class MultiFlagNested(yuio.config.Config):
                sub: Sub = yuio.config.field(flags=[])

            MultiFlagNested()

        with pytest.raises(
            TypeError, match=r"nested configs can't have multiple flags"
        ):

            class MultiFlagNested2(yuio.config.Config):
                sub: Sub = yuio.config.field(flags=["--a", "--b"])

            MultiFlagNested2()

        with pytest.raises(TypeError, match=r"nested configs can't have a short flag"):

            class ShortFlagNested(yuio.config.Config):
                sub: Sub = yuio.config.field(flags="-s")

            ShortFlagNested()

        with pytest.raises(TypeError, match=r"nested configs can't have defaults"):

            class DefaultNested(yuio.config.Config):
                sub: Sub = yuio.config.field(default=Sub())

            DefaultNested()

        with pytest.raises(TypeError, match=r"nested configs can't have parsers"):

            class ParserNested(yuio.config.Config):
                sub: Sub = yuio.config.field(parser=yuio.parse.Int())  # type: ignore

            ParserNested()

        with pytest.raises(
            TypeError, match=r"nested configs can't have merge function"
        ):

            class MergeNested(yuio.config.Config):
                sub: Sub = yuio.config.field(merge=lambda l, r: r)

            MergeNested()

        mutex = yuio.config.MutuallyExclusiveGroup()
        with pytest.raises(
            TypeError,
            match=r"nested configs can't be a part of a mutually exclusive group",
        ):

            class MutexNested(yuio.config.Config):
                sub: Sub = yuio.config.field(mutex_group=mutex)

            MutexNested()

        with pytest.raises(TypeError, match=r"nested configs can't be required"):

            class RequiredNested(yuio.config.Config):
                sub: Sub = yuio.config.field(required=True)

            RequiredNested()

        with pytest.raises(
            TypeError,
            match=r"positional arguments can't appear in mutually exclusive groups",
        ):

            class MutexPos(yuio.config.Config, _allow_positionals=True):
                f1: int = yuio.config.field(flags=yuio.POSITIONAL, mutex_group=mutex)

            MutexPos()

    def test_optional_lift(self):
        class MyConfig1(yuio.config.Config):
            x: int

        with pytest.raises(yuio.parse.ParsingError, match=r"Expected int"):
            assert MyConfig1.load_from_parsed_file(dict(x=None))

        class MyConfig2(yuio.config.Config):
            x: int = None  # type: ignore

        assert MyConfig2.load_from_parsed_file(dict(x=None)).x is None

        class MyConfig3(yuio.config.Config):
            x: int = yuio.config.field(
                parser=yuio.parse.Int(),
                default=None,
            )  # type: ignore

        assert MyConfig3.load_from_parsed_file(dict(x=None)).x is None

        class MyConfig4(yuio.config.Config):
            x: int | None = yuio.config.field(
                parser=yuio.parse.Int(),
            )

        assert MyConfig4.load_from_parsed_file(dict(x=None)).x is None

        class MyConfig5(yuio.config.Config):
            x: typing.Annotated[int, "some annotation"] = None  # type: ignore

        assert MyConfig5.load_from_parsed_file(dict(x=None)).x is None

    def test_inline(self, monkeypatch: pytest.MonkeyPatch):
        class SubConfig(yuio.config.Config):
            a: str
            b: int = 1

        class MyConfig(yuio.config.Config):
            sub: SubConfig = yuio.config.inline()
            x: str = "x"

        monkeypatch.setenv("A", "aaa")
        monkeypatch.setenv("B", "2")
        monkeypatch.setenv("X", "xxx")

        c = MyConfig.load_from_env()
        assert c.sub.a == "aaa"
        assert c.sub.b == 2
        assert c.x == "xxx"

        options = MyConfig._build_options()
        flags = {opt.flags[0] for opt in options if opt.flags is not yuio.POSITIONAL}
        assert "--a" in flags
        assert "--b" in flags
        assert "--x" in flags
        assert "--sub-a" not in flags


class TestEnv:
    def test_load(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig(yuio.config.Config):
            f1: str
            f2: str = "f2"

        c = MyConfig.load_from_env()
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.f1
        assert c.f2 == "f2"

        monkeypatch.setenv("F1", "f1.2")
        c = MyConfig.load_from_env()
        assert c.f1 == "f1.2"
        assert c.f2 == "f2"

        monkeypatch.setenv("F2", "f2.2")
        c = MyConfig.load_from_env()
        assert c.f1 == "f1.2"
        assert c.f2 == "f2.2"

    def test_load_error(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig(yuio.config.Config):
            i: int

        monkeypatch.setenv("I", "not-an-int")
        with pytest.raises(
            yuio.parse.ParsingError, match=r"Can't parse environment variable I"
        ):
            MyConfig.load_from_env()

    def test_prefix(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig(yuio.config.Config):
            s: str

        monkeypatch.setenv("S", "s.1")
        monkeypatch.setenv("P_S", "s.2")

        c = MyConfig.load_from_env(prefix="")
        assert c.s == "s.1"

        c = MyConfig.load_from_env(prefix="P")
        assert c.s == "s.2"

    def test_disabled(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig(yuio.config.Config):
            f_disabled: str = yuio.config.field(default="f_disabled", env=yuio.DISABLED)
            f_enabled: str = "f_enabled"

        monkeypatch.setenv("F_DISABLED", "f_disabled.2")
        monkeypatch.setenv("F_ENABLED", "f_enabled.2")
        c = MyConfig.load_from_env()
        assert c.f_disabled == "f_disabled"
        assert c.f_enabled == "f_enabled.2"

    def test_configured_name(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig(yuio.config.Config):
            f1: str = yuio.config.field(default="f1", env="FX")

        monkeypatch.setenv("F1", "f1.2")
        c = MyConfig.load_from_env()
        assert c.f1 == "f1"

        monkeypatch.setenv("FX", "f1.3")
        c = MyConfig.load_from_env()
        assert c.f1 == "f1.3"

        with pytest.raises(TypeError, match=r"empty env variable name"):

            class ErrConfig(yuio.config.Config):
                a: str = yuio.config.field(env="")

            ErrConfig.load_from_env()

    def test_simple_parsers(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig1(yuio.config.Config):
            b: bool
            s: str = yuio.config.field(
                parser=yuio.parse.OneOf(yuio.parse.Str(), ["x", "y"])
            )

        monkeypatch.setenv("B", "y")
        monkeypatch.setenv("S", "x")
        c = MyConfig1.load_from_env()
        assert c.b is True
        assert c.s == "x"

        monkeypatch.setenv("S", "z")
        with pytest.raises(ValueError, match=r"should be 'x' or 'y'"):
            _ = MyConfig1.load_from_env()

        class E(enum.Enum):
            A = "A"
            B = "B"

        class MyConfig2(yuio.config.Config):
            b: bool
            s: str
            f: float
            i: int
            e: E

        monkeypatch.setenv("B", "no")
        monkeypatch.setenv("S", "str")
        monkeypatch.setenv("F", "1.5")
        monkeypatch.setenv("I", "-10")
        monkeypatch.setenv("E", "B")

        c = MyConfig2.load_from_env()
        assert c.b is False
        assert c.s == "str"
        assert c.f == 1.5
        assert c.i == -10
        assert c.e is E.B

        class MyConfig3(yuio.config.Config):
            b: bool | None
            s: str | None
            f: float | None
            i: int | None
            e: E | None

        monkeypatch.setenv("B", "no")
        monkeypatch.setenv("S", "str")
        monkeypatch.setenv("F", "1.5")
        monkeypatch.setenv("I", "-10")
        monkeypatch.setenv("E", "B")

        c = MyConfig3.load_from_env()
        assert c.b is False
        assert c.s == "str"
        assert c.f == 1.5
        assert c.i == -10
        assert c.e is E.B

    def test_collection_parsers(self, monkeypatch: pytest.MonkeyPatch):
        class MyConfig(yuio.config.Config):
            b: list = yuio.config.field(  # type: ignore
                parser=yuio.parse.List(
                    yuio.parse.Tuple(yuio.parse.Str(), yuio.parse.Int(), delimiter=":")
                )
            )
            s: set[int]
            x: tuple[int, float]
            d: dict[str, int]

        monkeypatch.setenv("B", "a:1 b:2")
        monkeypatch.setenv("S", "1 2 3 5 3")
        monkeypatch.setenv("X", "1 2")
        monkeypatch.setenv("D", "a:10 b:20")
        c = MyConfig.load_from_env()
        assert c.b == [("a", 1), ("b", 2)]
        assert c.s == {1, 2, 3, 5}
        assert c.x == (1, 2.0)
        assert c.d == {"a": 10, "b": 20}

    def test_subconfig(self, monkeypatch: pytest.MonkeyPatch):
        class SubConfig(yuio.config.Config):
            a: str

        class MyConfig(yuio.config.Config):
            sub: SubConfig

        monkeypatch.setenv("SUB_A", "xxx1")
        c = MyConfig.load_from_env()
        assert c.sub.a == "xxx1"

    def test_subconfig_no_prefix(self, monkeypatch: pytest.MonkeyPatch):
        class SubSubConfig(yuio.config.Config):
            b: str

        class SubConfig(yuio.config.Config):
            a: str
            sub: SubSubConfig = yuio.config.field(env="")

        class MyConfig(yuio.config.Config):
            sub: SubConfig = yuio.config.field(env="")

        monkeypatch.setenv("SUB_A", "xxx1")
        monkeypatch.setenv("A", "xxx-a")
        monkeypatch.setenv("B", "xxx-b")

        c = MyConfig.load_from_env()
        assert c.sub.a == "xxx-a"
        assert c.sub.sub.b == "xxx-b"

        monkeypatch.setenv("P_SUB_A", "xxx2")
        monkeypatch.setenv("P_A", "xxx-a2")
        monkeypatch.setenv("P_B", "xxx-b2")

        c = MyConfig.load_from_env(prefix="P")
        assert c.sub.a == "xxx-a2"
        assert c.sub.sub.b == "xxx-b2"


class TestLoadFromFile:
    def test_load_from_parsed_file(self):
        class MyConfig(yuio.config.Config):
            a: str
            b: int
            c: int = 5

        c = MyConfig.load_from_parsed_file(dict(a="abc", b=10, c=11))
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 11

        c = MyConfig.load_from_parsed_file(dict(a="abc"))
        assert c.a == "abc"
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.b
        assert c.c == 5

    def test_load_from_parsed_file_root_type_mismatch(self):
        class MyConfig(yuio.config.Config):
            a: int

        with pytest.raises(yuio.parse.ParsingError, match=r"Expected dict"):
            MyConfig.load_from_parsed_file(123)

    def test_load_from_parsed_file_unknown_fields(self):
        class MyConfig(yuio.config.Config):
            a: str
            b: int
            c: int = 5

        with pytest.raises(ValueError, match=r"Unknown field x"):
            MyConfig.load_from_parsed_file(dict(a="abc", b=10, x=11))

    def test_load_from_parsed_file_unknown_fields_ignored(self):
        class MyConfig(yuio.config.Config):
            a: str
            b: int

        c = MyConfig.load_from_parsed_file(
            dict(a="abc", x=10), ignore_unknown_fields=True
        )
        assert c.a == "abc"
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.b

    def test_load_from_parsed_file_type_mismatch(self):
        class MyConfig(yuio.config.Config):
            a: str

        with pytest.raises(yuio.parse.ParsingError, match=r"Expected str"):
            MyConfig.load_from_parsed_file(dict(a=10))

    def test_load_from_parsed_file_subconfig(self):
        class SubConfig(yuio.config.Config):
            a: str

        class MyConfig(yuio.config.Config):
            b: str
            c: SubConfig

        c = MyConfig.load_from_parsed_file(dict(b="abc", c=dict(a="cde")))
        assert c.b == "abc"
        assert c.c.a == "cde"

        with pytest.raises(ValueError, match=r"Unknown field c\.x"):
            MyConfig.load_from_parsed_file(dict(b="abc", c=dict(x="cde")))

    def test_load_from_json_file(self, tmp_path):
        class MyConfig(yuio.config.Config):
            a: str
            b: int
            c: int = 5

        data_path = tmp_path / "data.json"

        with open(data_path, "w") as f:
            f.write('{"a": "abc", "b": 10}')

        c = MyConfig.load_from_json_file(data_path)
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 5

        data_path_2 = tmp_path / "data_2.json"

        with open(data_path_2, "w") as f:
            f.write('{"a": "abc", "b": 10, "x": 0}')

        c = MyConfig.load_from_json_file(data_path_2, ignore_unknown_fields=True)
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 5

        with pytest.raises(ValueError, match=r"Unknown field x"):
            MyConfig.load_from_json_file(data_path_2)

        c = MyConfig.load_from_json_file(
            tmp_path / "foo.json", ignore_missing_file=True
        )
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.a
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.b
        assert c.c == 5

    def test_load_from_json_file_invalid(self, tmp_path):
        class MyConfig(yuio.config.Config):
            a: int

        data_path = tmp_path / "invalid.json"
        data_path.write_text("{")

        with pytest.raises(yuio.parse.ParsingError, match=r"Invalid config"):
            MyConfig.load_from_json_file(data_path)

    def test_load_from_yaml_file(self, tmp_path):
        class MyConfig(yuio.config.Config):
            a: str
            b: int
            c: int = 5

        data_path = tmp_path / "data.yaml"

        with open(data_path, "w") as f:
            f.write("a: abc\nb: 10")

        c = MyConfig.load_from_yaml_file(data_path)
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 5

        data_path_2 = tmp_path / "data_2.yaml"

        with open(data_path_2, "w") as f:
            f.write("a: abc\nb: 10\nx: 0")

        c = MyConfig.load_from_yaml_file(data_path_2, ignore_unknown_fields=True)
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 5

        with pytest.raises(ValueError, match=r"Unknown field x"):
            MyConfig.load_from_yaml_file(data_path_2)

        c = MyConfig.load_from_yaml_file(
            tmp_path / "foo.yaml", ignore_missing_file=True
        )
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.a
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.b
        assert c.c == 5

    def test_load_from_yaml_file_invalid(self, tmp_path):
        class MyConfig(yuio.config.Config):
            a: int

        data_path = tmp_path / "invalid.yaml"
        data_path.write_text(":")

        with pytest.raises(yuio.parse.ParsingError, match=r"Invalid config"):
            MyConfig.load_from_yaml_file(data_path)

    def test_load_from_toml_file(self, tmp_path):
        class MyConfig(yuio.config.Config):
            a: str
            b: int
            c: int = 5

        data_path = tmp_path / "data.toml"

        with open(data_path, "w") as f:
            f.write('a="abc"\nb=10')

        c = MyConfig.load_from_toml_file(data_path)
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 5

        data_path_2 = tmp_path / "data_2.toml"

        with open(data_path_2, "w") as f:
            f.write('a="abc"\nb=10\nx=0')

        c = MyConfig.load_from_toml_file(data_path_2, ignore_unknown_fields=True)
        assert c.a == "abc"
        assert c.b == 10
        assert c.c == 5

        with pytest.raises(ValueError, match=r"Unknown field x"):
            MyConfig.load_from_toml_file(data_path_2)

        c = MyConfig.load_from_toml_file(
            tmp_path / "foo.toml", ignore_missing_file=True
        )
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.a
        with pytest.raises(AttributeError, match=r"is not configured"):
            _ = c.b
        assert c.c == 5

    def test_load_from_toml_file_invalid(self, tmp_path):
        class MyConfig(yuio.config.Config):
            a: int

        data_path = tmp_path / "invalid.toml"
        data_path.write_text("=")

        with pytest.raises(yuio.parse.ParsingError, match=r"Invalid config"):
            MyConfig.load_from_toml_file(data_path)


class TestMerge:
    class MyConfig(yuio.config.Config):
        x: int = yuio.config.field(default=1, merge=lambda l, r: l + r)

    def test_merge_ctor(self):
        c = self.MyConfig()
        assert c.x == 1

        c = self.MyConfig(x=2)
        assert c.x == 2

        c = self.MyConfig(self.MyConfig(), self.MyConfig(x=2))
        assert c.x == 2

        c = self.MyConfig(self.MyConfig(x=1), self.MyConfig(x=2))
        assert c.x == 3

    def test_merge_update(self):
        c = self.MyConfig()
        assert c.x == 1

        c.update(dict(x=2))
        assert c.x == 2

        c.update(dict(x=1))
        assert c.x == 3


class TestJsonSchema:
    class MyConfig(yuio.config.Config):
        """Help for MyConfig."""

        x: int = 5
        #: Help for y.
        y: list[int]

    class MyConfig2(yuio.config.Config):
        x: "TestJsonSchema.MyConfig"
        y: int = 5

    def test_to_json_schema(self):
        ctx = yuio.json_schema.JsonSchemaContext()
        res = TestJsonSchema.MyConfig.to_json_schema(ctx)
        assert res == yuio.json_schema.Ref(
            "#/$defs/test.test_config.TestJsonSchema.MyConfig",
            "test.test_config.TestJsonSchema.MyConfig",
        )
        schema = ctx.render(res)
        validator = jsonschema.Draft7Validator(schema)
        validator.validate({"x": 5, "y": [1, 2, 3]}, schema)
        validator.validate({"x": 5}, schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate("what?", schema)
        with pytest.raises(jsonschema.ValidationError):
            validator.validate({"x": "y"}, schema)

        # fmt: off
        assert schema["$defs"]["test.test_config.TestJsonSchema.MyConfig"]["description"] == "Help for MyConfig.\n"  # type: ignore
        assert schema["$defs"]["test.test_config.TestJsonSchema.MyConfig"]["properties"]["y"]["description"] == "Help for y.\n"  # type: ignore
        # fmt: on

    def test_to_json_schema_nested(self):
        ctx = yuio.json_schema.JsonSchemaContext()
        res = TestJsonSchema.MyConfig2.to_json_schema(ctx)
        schema = ctx.render(res)

        # fmt: off
        assert "test.test_config.TestJsonSchema.MyConfig" in schema["$defs"]  # type: ignore
        assert "test.test_config.TestJsonSchema.MyConfig2" in schema["$defs"]  # type: ignore
        nested_ref = schema["$defs"]["test.test_config.TestJsonSchema.MyConfig2"]["properties"]["x"]["$ref"]  # type: ignore
        assert nested_ref == "#/$defs/test.test_config.TestJsonSchema.MyConfig"
        # fmt: on

    def test_to_json_schema_default_fail(self):
        class Unserializable:
            pass

        class MyConfig(yuio.config.Config):
            x: Unserializable = yuio.config.field(
                default=Unserializable(),
                parser=yuio.parse.Map(
                    yuio.parse.Str(),
                    lambda s: Unserializable(),
                    # Not specifying reverse mapping (Unserializable -> str) so that
                    # JSON serialization fails.
                ),
            )

        ctx = yuio.json_schema.JsonSchemaContext()
        res = MyConfig.to_json_schema(ctx)
        schema = ctx.render(res)

        assert "default" not in schema["$defs"][res.name]["default"]  # type: ignore

    def test_to_json_value(self):
        config = TestJsonSchema.MyConfig(x=10, y=[3, 2, 1])
        assert config.to_json_value() == {"x": 10, "y": [3, 2, 1]}

        config = TestJsonSchema.MyConfig()
        assert config.to_json_value() == {"x": 5}
        assert config.to_json_value(include_defaults=False) == {}

        config = TestJsonSchema.MyConfig(y=[1])
        assert config.to_json_value() == {"x": 5, "y": [1]}
        assert config.to_json_value(include_defaults=False) == {"y": [1]}

        config = TestJsonSchema.MyConfig2()
        assert config.to_json_value() == {"x": {"x": 5}, "y": 5}
        assert config.to_json_value(include_defaults=False) == {}

        config = TestJsonSchema.MyConfig2(x=TestJsonSchema.MyConfig(x=5))
        assert config.to_json_value() == {"x": {"x": 5}, "y": 5}
        assert config.to_json_value(include_defaults=False) == {"x": {"x": 5}}


class TestCopy:
    def test_shallow_copy_basic(self):
        class MyConfig(yuio.config.Config):
            x: int = 1
            y: str = "test"

        original = MyConfig(x=10, y="hello")
        copied = copy.copy(original)

        assert copied is not original
        assert copied.x == 10
        assert copied.y == "hello"

        copied.x = 15
        assert original.x == 10
        assert copied.x == 15

    def test_shallow_copy_with_mutable_values(self):
        class MyConfig(yuio.config.Config):
            items: list[int] = []

        original = MyConfig(items=[1, 2, 3])
        copied = copy.copy(original)

        assert copied is not original
        assert copied.items is original.items
        original.items.append(4)
        assert copied.items == [1, 2, 3, 4]

    def test_shallow_copy_nested_configs(self):
        class SubConfig(yuio.config.Config):
            value: int = 0

        class MyConfig(yuio.config.Config):
            sub: SubConfig

        original = MyConfig(sub=SubConfig(value=42))
        copied = copy.copy(original)

        assert copied is not original
        assert copied.sub is not original.sub
        assert copied.sub.value == 42

        copied.sub.value = 24
        assert original.sub.value == 42
        assert copied.sub.value == 24

    def test_shallow_copy_with_missing_fields(self):
        class MyConfig(yuio.config.Config):
            x: int
            y: str = "default"

        original = MyConfig(y="custom")
        copied = copy.copy(original)

        with pytest.raises(AttributeError, match=r"x is not configured"):
            _ = copied.x
        assert copied.y == "custom"

    def test_deepcopy_basic(self):
        class MyConfig(yuio.config.Config):
            x: int = 1
            y: str = "test"

        original = MyConfig(x=10, y="hello")
        copied = copy.deepcopy(original)

        assert copied is not original
        assert copied.x == 10
        assert copied.y == "hello"

        copied.x = 15
        assert original.x == 10
        assert copied.x == 15

    def test_deepcopy_with_mutable_values(self):
        class MyConfig(yuio.config.Config):
            items: list[int] = []

        original = MyConfig(items=[1, 2, 3])
        copied = copy.deepcopy(original)

        assert copied is not original
        assert copied.items is not original.items
        assert copied.items == [1, 2, 3]
        original.items.append(4)
        assert copied.items == [1, 2, 3]

    def test_deepcopy_nested_configs(self):
        class SubConfig(yuio.config.Config):
            items: list[int] = []
            value: int = 0

        class MyConfig(yuio.config.Config):
            sub: SubConfig

        original = MyConfig(sub=SubConfig(value=42, items=[1, 2, 3]))
        copied = copy.deepcopy(original)

        assert copied is not original
        assert copied.sub is not original.sub
        assert copied.sub.value == 42
        assert copied.sub.items == [1, 2, 3]
        assert copied.sub.items is not original.sub.items
        original.sub.items.append(4)
        assert copied.sub.items == [1, 2, 3]

    def test_deepcopy_deeply_nested_configs(self):
        class Level3(yuio.config.Config):
            data: dict[str, int] = {}

        class Level2(yuio.config.Config):
            level3: Level3

        class Level1(yuio.config.Config):
            level2: Level2

        original = Level1(level2=Level2(level3=Level3(data={"a": 1, "b": 2})))
        copied = copy.deepcopy(original)

        assert copied is not original
        assert copied.level2 is not original.level2
        assert copied.level2.level3 is not original.level2.level3
        assert copied.level2.level3.data is not original.level2.level3.data
        assert copied.level2.level3.data == {"a": 1, "b": 2}
        original.level2.level3.data["c"] = 3
        assert copied.level2.level3.data == {"a": 1, "b": 2}

    def test_deepcopy_with_missing_fields(self):
        class MyConfig(yuio.config.Config):
            x: int
            y: str = "default"

        original = MyConfig(y="custom")
        copied = copy.deepcopy(original)

        with pytest.raises(AttributeError, match=r"x is not configured"):
            _ = copied.x
        assert copied.y == "custom"
