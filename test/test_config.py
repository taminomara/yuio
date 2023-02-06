import enum
import typing

import pytest

from yuio.config import *
import yuio.parse


class TestBasics:
    def test_default(self):
        class MyConfig(Config):
            f1: str = '1'
            f2: str = '2'

        c = MyConfig()
        assert c.f1 == '1'
        assert c.f2 == '2'

        c = MyConfig(f2='b')
        assert c.f1 == '1'
        assert c.f2 == 'b'

        c = MyConfig(f1='a', f2='b')
        assert c.f1 == 'a'
        assert c.f2 == 'b'

    def test_default_field(self):
        class MyConfig(Config):
            f1: str = field('1')
            f2: str = field('2')

        c = MyConfig()
        assert c.f1 == '1'
        assert c.f2 == '2'

        c = MyConfig(f2='b')
        assert c.f1 == '1'
        assert c.f2 == 'b'

        c = MyConfig(f1='a', f2='b')
        assert c.f1 == 'a'
        assert c.f2 == 'b'

    def test_missing(self):
        class MyConfig(Config):
            f1: str
            f2: str

        c = MyConfig()
        with pytest.raises(AttributeError, match='f1 is not configured'):
            _ = c.f1
        with pytest.raises(AttributeError, match='f2 is not configured'):
            _ = c.f2

        c = MyConfig(f1='a')
        assert c.f1 == 'a'
        with pytest.raises(AttributeError, match='f2 is not configured'):
            _ = c.f2

        c = MyConfig(f1='a', f2='b')
        assert c.f1 == 'a'
        assert c.f2 == 'b'

    def test_missing_field(self):
        class MyConfig(Config):
            f1: str = field()
            f2: str = field()

        c = MyConfig()
        with pytest.raises(AttributeError, match='f1 is not configured'):
            _ = c.f1
        with pytest.raises(AttributeError, match='f2 is not configured'):
            _ = c.f2

        c = MyConfig(f1='a')
        assert c.f1 == 'a'
        with pytest.raises(AttributeError, match='f2 is not configured'):
            _ = c.f2

        c = MyConfig(f1='a', f2='b')
        assert c.f1 == 'a'
        assert c.f2 == 'b'

    def test_init(self):
        class MyConfig(Config):
            f1: str
            f2: str

        with pytest.raises(TypeError, match=r'unknown field: x'):
            MyConfig(x=1)

    def test_repr(self):
        class MyConfig(Config):
            f1: str = '1'
            f2: str

        assert repr(MyConfig()) == "MyConfig(\n  f1='1',\n  f2=<missing>\n)"
        assert repr(MyConfig(f1='x')) == "MyConfig(\n  f1='x',\n  f2=<missing>\n)"
        assert repr(MyConfig(f2='y')) == "MyConfig(\n  f1='1',\n  f2='y'\n)"

    def test_inheritance(self):
        class Parent(Config):
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

            new_field: str = 'x'

        with pytest.raises(TypeError, match=r'unknown field: new_field'):
            Parent(new_field='-_-')

        c = Child(
            field_without_default=1,
            field_with_default=2,
            field_without_default_that_gets_overridden_with_default=3,
            field_without_default_that_gets_overridden_without_default=4,
            field_with_default_that_gets_overridden_with_default=5,
            field_with_default_that_gets_overridden_without_default=6,
            new_field='7',
        )

        assert c.field_without_default == 1
        assert c.field_with_default == 2
        assert c.field_without_default_that_gets_overridden_with_default == 3
        assert c.field_without_default_that_gets_overridden_without_default == 4
        assert c.field_with_default_that_gets_overridden_with_default == 5
        assert c.field_with_default_that_gets_overridden_without_default == 6
        assert c.new_field == '7'

        c = Child()

        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.field_without_default
        assert c.field_with_default == 0
        assert c.field_without_default_that_gets_overridden_with_default == 0
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.field_without_default_that_gets_overridden_without_default
        assert c.field_with_default_that_gets_overridden_with_default == 0
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.field_with_default_that_gets_overridden_without_default
        assert c.new_field == 'x'

    def test_subconfig(self):
        class SubConfig(Config):
            a: str = 'a'
            b: str

        class MyConfig(Config):
            sub: SubConfig
            x: int

        assert repr(MyConfig()) == \
               "MyConfig(\n" \
               "  sub=SubConfig(\n" \
               "    a='a',\n" \
               "    b=<missing>\n" \
               "  ),\n" \
               "  x=<missing>\n" \
               ")"
        assert repr(MyConfig(sub=SubConfig(b='2'))) == \
               "MyConfig(\n" \
               "  sub=SubConfig(\n" \
               "    a='a',\n" \
               "    b='2'\n" \
               "  ),\n" \
               "  x=<missing>\n" \
               ")"

    def test_update(self):
        class MyConfig(Config):
            f1: str = 'f1'
            f2: str

        c = MyConfig(f1='f1.2')
        c.update(MyConfig(f1='f1.3'))
        assert c.f1 == 'f1.3'

        c = MyConfig(f1='f1.2')
        c.update(MyConfig())
        assert c.f1 == 'f1.2'

        c = MyConfig(f1='f1.2')
        c.update(MyConfig(f2='f2'))
        assert c.f1 == 'f1.2'
        assert c.f2 == 'f2'

        c = MyConfig(f1='f1.2', f2='f2')
        c.update(MyConfig(f2='f2.2'))
        assert c.f1 == 'f1.2'
        assert c.f2 == 'f2.2'

    def test_update_recursive(self):
        class SubConfig(Config):
            a: str = 'a'
            b: str

        class MyConfig(Config):
            sub: SubConfig
            x: int

        c = MyConfig(sub=dict(b='2'))
        c.update(dict(x=2, sub=dict(a='a.2')))

        assert c.x == 2
        assert c.sub.a == 'a.2'
        assert c.sub.b == '2'

    class SubConfig(Config):
        y: int

    class ResolveConfig(Config):
        x: 'TestBasics.SubConfig'

    def test_resolve(self):
        c = TestBasics.ResolveConfig(x=dict(y=10))
        assert c.x.y == 10

    def test_resolve_locals(self):
        Ty = int

        class ResolveConfig(Config):
            f: 'Ty'

        with pytest.raises(NameError, match='forward references do not work inside functions'):
            ResolveConfig(f=10)

    def test_optional_lift(self):
        class MyConfig1(Config):
            x: int

        with pytest.raises(yuio.parse.ParsingError, match='expected an int'):
            assert MyConfig1.load_from_parsed_file(dict(x=None))

        class MyConfig2(Config):
            x: int = None  # type: ignore

        assert MyConfig2.load_from_parsed_file(dict(x=None)).x is None

        class MyConfig3(Config):
            x: int = field(
                parser=yuio.parse.Int(),
                default=None,
            )  # type: ignore

        assert MyConfig3.load_from_parsed_file(dict(x=None)).x is None

        class MyConfig4(Config):
            x: typing.Optional[int] = field(
                parser=yuio.parse.Int(),
            )

        assert MyConfig4.load_from_parsed_file(dict(x=None)).x is None


class TestEnv:
    @pytest.fixture(autouse=True)
    def auto_fixtures(self, save_env):
        pass

    def test_load(self):
        class MyConfig(Config):
            f1: str
            f2: str = 'f2'

        c = MyConfig.load_from_env()
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.f1
        assert c.f2 == 'f2'

        os.environ['F1'] = 'f1.2'
        c = MyConfig.load_from_env()
        assert c.f1 == 'f1.2'
        assert c.f2 == 'f2'

        os.environ['F2'] = 'f2.2'
        c = MyConfig.load_from_env()
        assert c.f1 == 'f1.2'
        assert c.f2 == 'f2.2'

    def test_prefix(self):
        class MyConfig(Config):
            s: str

        os.environ['S'] = 's.1'
        os.environ['P_S'] = 's.2'

        c = MyConfig.load_from_env(prefix='')
        assert c.s == 's.1'

        c = MyConfig.load_from_env(prefix='P')
        assert c.s == 's.2'

    def test_disabled(self):
        class MyConfig(Config):
            f_disabled: str = field(
                'f_disabled', env=DISABLED)
            f_enabled: str = 'f_enabled'

        os.environ['F_DISABLED'] = 'f_disabled.2'
        os.environ['F_ENABLED'] = 'f_enabled.2'
        c = MyConfig.load_from_env()
        assert c.f_disabled == 'f_disabled'
        assert c.f_enabled == 'f_enabled.2'

    def test_configured_name(self):
        class MyConfig(Config):
            f1: str = field('f1', env='FX')

        os.environ['F1'] = 'f1.2'
        c = MyConfig.load_from_env()
        assert c.f1 == 'f1'

        os.environ['FX'] = 'f1.3'
        c = MyConfig.load_from_env()
        assert c.f1 == 'f1.3'

        with pytest.raises(TypeError, match='empty env variable name'):
            class ErrConfig(Config):
                a: str = field(env='')

            ErrConfig.load_from_env()

    def test_simple_parsers(self):
        class MyConfig1(Config):
            b: bool
            s: str = field(
                parser=yuio.parse.OneOf(yuio.parse.Str(), ['x', 'y'])
            )

        os.environ['B'] = 'y'
        os.environ['S'] = 'x'
        c = MyConfig1.load_from_env()
        assert c.b is True
        assert c.s == 'x'

        os.environ['S'] = 'z'
        with pytest.raises(ValueError, match='one of x, y'):
            _ = MyConfig1.load_from_env()

        class E(enum.Enum):
            A = enum.auto()
            B = enum.auto()

        class MyConfig2(Config):
            b: bool
            s: str
            f: float
            i: int
            e: E

        os.environ['B'] = 'no'
        os.environ['S'] = 'str'
        os.environ['F'] = '1.5'
        os.environ['I'] = '-10'
        os.environ['E'] = 'B'

        c = MyConfig2.load_from_env()
        assert c.b is False
        assert c.s == 'str'
        assert c.f == 1.5
        assert c.i == -10
        assert c.e is E.B

        class MyConfig3(Config):
            b: typing.Optional[bool]
            s: typing.Optional[str]
            f: typing.Optional[float]
            i: typing.Optional[int]
            e: typing.Optional[E]

        os.environ['B'] = 'no'
        os.environ['S'] = 'str'
        os.environ['F'] = '1.5'
        os.environ['I'] = '-10'
        os.environ['E'] = 'B'

        c = MyConfig3.load_from_env()
        assert c.b is False
        assert c.s == 'str'
        assert c.f == 1.5
        assert c.i == -10
        assert c.e is E.B

    def test_collection_parsers(self):
        class MyConfig(Config):
            b: list = field(
                parser=yuio.parse.List(
                    yuio.parse.Pair(
                        yuio.parse.Str(), yuio.parse.Int())))
            s: typing.Set[int]
            x: typing.Tuple[int, float]
            d: typing.Dict[str, int]

        os.environ['B'] = 'a:1 b:2'
        os.environ['S'] = '1 2 3 5 3'
        os.environ['X'] = '1 2'
        os.environ['D'] = 'a:10 b:20'
        c = MyConfig.load_from_env()
        assert c.b == [('a', 1), ('b', 2)]
        assert c.s == {1, 2, 3, 5}
        assert c.x == (1, 2.0)
        assert c.d == {'a': 10, 'b': 20}

    def test_subconfig(self):
        class SubConfig(Config):
            a: str

        class MyConfig(Config):
            sub: SubConfig

        os.environ['SUB_A'] = 'xxx1'
        c = MyConfig.load_from_env()
        assert c.sub.a == 'xxx1'

    def test_subconfig_no_prefix(self):
        class SubSubConfig(Config):
            b: str

        class SubConfig(Config):
            a: str
            sub: SubSubConfig = field(env='')

        class MyConfig(Config):
            sub: SubConfig = field(env='')

        os.environ['SUB_A'] = 'xxx1'
        os.environ['A'] = 'xxx-a'
        os.environ['B'] = 'xxx-b'

        c = MyConfig.load_from_env()
        assert c.sub.a == 'xxx-a'
        assert c.sub.sub.b == 'xxx-b'

        os.environ['P_SUB_A'] = 'xxx2'
        os.environ['P_A'] = 'xxx-a2'
        os.environ['P_B'] = 'xxx-b2'

        c = MyConfig.load_from_env(prefix='P')
        assert c.sub.a == 'xxx-a2'
        assert c.sub.sub.b == 'xxx-b2'


class TestArgs:
    C = typing.TypeVar('C', bound=Config)

    @staticmethod
    def load_from_args(confg: typing.Type[C], args: str) -> C:
        parser = argparse.ArgumentParser()
        confg.setup_arg_parser(parser)
        return confg.load_from_namespace(parser.parse_args(args.split()))

    def test_load(self):
        class MyConfig(Config):
            a: str
            b: int
            c: int = 5

        c = self.load_from_args(MyConfig, '--a abc --b 10 --c 11')
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 11

        c = self.load_from_args(MyConfig, '--a abc')
        assert c.a == 'abc'
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.b
        assert c.c == 5

    def test_disabled(self, capsys):
        class MyConfig(Config):
            a: str = field(default='def', flags=DISABLED)

        c = self.load_from_args(MyConfig, '')
        assert c.a == 'def'

        with pytest.raises(SystemExit):
            self.load_from_args(MyConfig, '--a asd')
        assert 'unrecognized arguments: --a asd' in capsys.readouterr().err

    def test_configured_flags(self):
        class MyConfig(Config):
            a: str = field(flags=['-a', '--a-long'])

        c = self.load_from_args(MyConfig, '-a foo')
        assert c.a == 'foo'

        c = self.load_from_args(MyConfig, '--a-long bar')
        assert c.a == 'bar'

        with pytest.raises(TypeError, match='empty flag'):
            class _ErrConfig1(Config):
                a: str = field(flags='')

            self.load_from_args(_ErrConfig1, '')

        with pytest.raises(TypeError, match='empty flag'):
            class _ErrConfig2(Config):
                a: str = field(flags=[''])

            self.load_from_args(_ErrConfig2, '')

    def test_simple_parsers(self, capsys):
        class MyConfig(Config):
            b: bool
            s: str = field(
                parser=yuio.parse.OneOf(yuio.parse.Str(), ['x', 'y'])
            )

        c = self.load_from_args(MyConfig, '--b --s x')
        assert c.b is True
        assert c.s == 'x'

        with pytest.raises(SystemExit):
            self.load_from_args(MyConfig, '--s z')
        assert 'one of x, y' in capsys.readouterr().err

    def test_collection_parsers(self):
        class MyConfig(Config):
            b: list = field(
                parser=yuio.parse.List(
                    yuio.parse.Pair(
                        yuio.parse.Str(), yuio.parse.Int())))
            s: typing.Set[int]
            x: typing.Tuple[int, float]
            d: typing.Dict[str, int]

        c = self.load_from_args(MyConfig, '--b a:1 b:2 --s 1 2 3 5 3 --x 1 2 --d a:10 b:20')
        assert c.b == [('a', 1), ('b', 2)]
        assert c.s == {1, 2, 3, 5}
        assert c.x == (1, 2.0)
        assert c.d == {'a': 10, 'b': 20}

    def test_bool_flag(self):
        class MyConfig(Config):
            a: bool
            b: bool

        c = self.load_from_args(MyConfig, '--a --no-b')
        assert c.a is True
        assert c.b is False

    def test_subconfig(self):
        class SubConfig(Config):
            a: str

        class MyConfig(Config):
            b: str
            sub: SubConfig

        c = self.load_from_args(MyConfig, '--b foo --sub-a bar')
        assert c.b == 'foo'
        assert c.sub.a == 'bar'

    def test_subconfig_custom_prefix(self):
        class SubConfig(Config):
            a: str

        class MyConfig(Config):
            b: str
            sub: SubConfig = field(flags='--sub-sub')

        c = self.load_from_args(MyConfig, '--b foo --sub-sub-a bar')
        assert c.b == 'foo'
        assert c.sub.a == 'bar'

    def test_subconfig_no_prefix(self):
        class SubConfig(Config):
            a: str

        class MyConfig(Config):
            b: str
            sub: SubConfig = field(flags='')

        c = self.load_from_args(MyConfig, '--b foo --a bar')
        assert c.b == 'foo'
        assert c.sub.a == 'bar'

    class DocSubConfig(Config):
        #: help for `a`.
        a: str

    class DocConfig(Config):
        #: help for `sub`.
        sub: 'TestArgs.DocSubConfig'

    def test_help(self):
        parser = argparse.ArgumentParser()
        TestArgs.DocConfig.setup_arg_parser(parser)
        help = parser.format_help()
        assert 'help for `sub`:' in help
        assert 'help for `a`.' in help


class TestLoadFromFile:
    def test_load_from_parsed_file(self):
        class MyConfig(Config):
            a: str
            b: int
            c: int = 5

        c = MyConfig.load_from_parsed_file(dict(a='abc', b=10, c=11))
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 11

        c = MyConfig.load_from_parsed_file(dict(a='abc'))
        assert c.a == 'abc'
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.b
        assert c.c == 5

    def test_load_from_parsed_file_unknown_fields(self):
        class MyConfig(Config):
            a: str
            b: int
            c: int = 5

        with pytest.raises(ValueError, match='unknown field x'):
            MyConfig.load_from_parsed_file(dict(a='abc', b=10, x=11))

    def test_load_from_parsed_file_unknown_fields_ignored(self):
        class MyConfig(Config):
            a: str
            b: int

        c = MyConfig.load_from_parsed_file(
            dict(a='abc', x=10), ignore_unknown_fields=True)
        assert c.a == 'abc'
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.b

    def test_load_from_parsed_file_type_mismatch(self):
        class MyConfig(Config):
            a: str

        with pytest.raises(yuio.parse.ParsingError, match='expected a string'):
            MyConfig.load_from_parsed_file(dict(a=10))

    def test_load_from_parsed_file_subconfig(self):
        class SubConfig(Config):
            a: str

        class MyConfig(Config):
            b: str
            c: SubConfig

        c = MyConfig.load_from_parsed_file(dict(b='abc', c=dict(a='cde')))
        assert c.b == 'abc'
        assert c.c.a == 'cde'

        with pytest.raises(ValueError, match='unknown field c.x'):
            MyConfig.load_from_parsed_file(dict(b='abc', c=dict(x='cde')))

    def test_load_from_json_file(self, tmp_path):
        class MyConfig(Config):
            a: str
            b: int
            c: int = 5

        data_path = tmp_path / 'data.json'

        with open(data_path, 'w') as f:
            f.write('{"a": "abc", "b": 10}')

        c = MyConfig.load_from_json_file(data_path)
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 5

        data_path_2 = tmp_path / 'data_2.json'

        with open(data_path_2, 'w') as f:
            f.write('{"a": "abc", "b": 10, "x": 0}')

        c = MyConfig.load_from_json_file(data_path_2, ignore_unknown_fields=True)
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 5

        with pytest.raises(ValueError, match='unknown field x'):
            MyConfig.load_from_json_file(data_path_2)

        c = MyConfig.load_from_json_file(
            tmp_path / 'foo.json', ignore_missing_file=True)
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.a
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.b
        assert c.c == 5

    def test_load_from_yaml_file(self, tmp_path):
        class MyConfig(Config):
            a: str
            b: int
            c: int = 5

        data_path = tmp_path / 'data.yaml'

        with open(data_path, 'w') as f:
            f.write('a: abc\nb: 10')

        c = MyConfig.load_from_yaml_file(data_path)
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 5

        data_path_2 = tmp_path / 'data_2.yaml'

        with open(data_path_2, 'w') as f:
            f.write('a: abc\nb: 10\nx: 0')

        c = MyConfig.load_from_yaml_file(data_path_2, ignore_unknown_fields=True)
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 5

        with pytest.raises(ValueError, match='unknown field x'):
            MyConfig.load_from_yaml_file(data_path_2)

        c = MyConfig.load_from_yaml_file(
            tmp_path / 'foo.yaml', ignore_missing_file=True)
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.a
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.b
        assert c.c == 5

    def test_load_from_toml_file(self, tmp_path):
        class MyConfig(Config):
            a: str
            b: int
            c: int = 5

        data_path = tmp_path / 'data.toml'

        with open(data_path, 'w') as f:
            f.write('a="abc"\nb=10')

        c = MyConfig.load_from_toml_file(data_path)
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 5

        data_path_2 = tmp_path / 'data_2.toml'

        with open(data_path_2, 'w') as f:
            f.write('a="abc"\nb=10\nx=0')

        c = MyConfig.load_from_toml_file(data_path_2, ignore_unknown_fields=True)
        assert c.a == 'abc'
        assert c.b == 10
        assert c.c == 5

        with pytest.raises(ValueError, match='unknown field x'):
            MyConfig.load_from_toml_file(data_path_2)

        c = MyConfig.load_from_toml_file(
            tmp_path / 'foo.toml', ignore_missing_file=True)
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.a
        with pytest.raises(AttributeError, match='is not configured'):
            _ = c.b
        assert c.c == 5
