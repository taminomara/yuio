import enum
import typing

import pytest

from yuio.config import *
import yuio.parse


def test_default():
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


def test_default_field():
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


def test_missing():
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


def test_missing_field():
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


def test_init():
    class MyConfig(Config):
        f1: str
        f2: str

    with pytest.raises(TypeError, match=r'unknown field\(s\): x'):
        MyConfig(x=1)

    with pytest.raises(TypeError, match=r'unknown field\(s\): x, y'):
        MyConfig(f1='a', x=1, y=2)


def test_repr():
    class MyConfig(Config):
        f1: str = '1'
        f2: str

    assert repr(MyConfig()) == "MyConfig(\n  f1='1',\n  f2=<missing>\n)"
    assert repr(MyConfig(f1='x')) == "MyConfig(\n  f1='x',\n  f2=<missing>\n)"
    assert repr(MyConfig(f2='y')) == "MyConfig(\n  f1='1',\n  f2='y'\n)"


def test_inheritance():
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

    with pytest.raises(TypeError, match=r'unknown field\(s\): new_field'):
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


def test_subconfig():
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


def test_update():
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


def test_update_recursive():
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


def test_load_from_env():
    os.environ.clear()

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


def test_load_from_env_prefix():
    os.environ.clear()

    class MyConfig(Config):
        s: str

    os.environ['S'] = 's.1'
    os.environ['P_S'] = 's.2'

    c = MyConfig.load_from_env(prefix='')
    assert c.s == 's.1'

    c = MyConfig.load_from_env(prefix='P')
    assert c.s == 's.2'


def test_load_from_env_disabled():
    os.environ.clear()

    class MyConfig(Config):
        f_disabled: str = field(
            'f_disabled', env=disabled())
        f_enabled: str = 'f_enabled'

    os.environ['F_DISABLED'] = 'f_disabled.2'
    os.environ['F_ENABLED'] = 'f_enabled.2'
    c = MyConfig.load_from_env()
    assert c.f_disabled == 'f_disabled'
    assert c.f_enabled == 'f_enabled.2'


def test_load_from_env_configured_name():
    os.environ.clear()

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


def test_load_from_env_simple_parsers():
    os.environ.clear()

    class MyConfig(Config):
        b: bool
        s: str = field(
            parser=yuio.parse.OneOf(yuio.parse.Str(), ['x', 'y'])
        )

    os.environ['B'] = 'y'
    os.environ['S'] = 'x'
    c = MyConfig.load_from_env()
    assert c.b is True
    assert c.s is 'x'

    os.environ['S'] = 'z'
    with pytest.raises(ValueError, match='one of x, y'):
        _ = MyConfig.load_from_env()

    os.environ.clear()

    class E(enum.Enum):
        A = enum.auto()
        B = enum.auto()

    class MyConfig(Config):
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

    c = MyConfig.load_from_env()
    assert c.b is False
    assert c.s == 'str'
    assert c.f == 1.5
    assert c.i == -10
    assert c.e is E.B

    os.environ.clear()

    class MyConfig(Config):
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

    c = MyConfig.load_from_env()
    assert c.b is False
    assert c.s == 'str'
    assert c.f == 1.5
    assert c.i == -10
    assert c.e is E.B


def test_load_from_env_collection_parsers():
    os.environ.clear()

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


def test_load_from_env_subconfig():
    os.environ.clear()

    class SubConfig(Config):
        a: str

    class MyConfig(Config):
        sub: SubConfig

    os.environ['SUB_A'] = 'xxx1'
    c = MyConfig.load_from_env()
    assert c.sub.a == 'xxx1'


def test_load_from_env_subconfig_no_prefix():
    os.environ.clear()

    class SubConfig(Config):
        a: str

    class MyConfig(Config):
        sub: SubConfig = field(env='')

    os.environ['SUB_A'] = 'xxx1'
    os.environ['A'] = 'xxx2'
    c = MyConfig.load_from_env()
    assert c.sub.a == 'xxx2'


def test_load_from_args():
    class MyConfig(Config):
        a: str
        b: int
        c: int = 5

    c = MyConfig.load_from_args('--a abc --b 10 --c 11'.split())
    assert c.a == 'abc'
    assert c.b == 10
    assert c.c == 11

    c = MyConfig.load_from_args('--a abc'.split())
    assert c.a == 'abc'
    with pytest.raises(AttributeError, match='is not configured'):
        _ = c.b
    assert c.c == 5


def test_load_from_args_disabled(capsys):
    class MyConfig(Config):
        a: str = field(default='def', flags=disabled())

    c = MyConfig.load_from_args(''.split())
    assert c.a == 'def'

    with pytest.raises(SystemExit):
        MyConfig.load_from_args('--a asd'.split())
    assert 'unrecognized arguments: --a asd' in capsys.readouterr().err


def test_load_from_args_configured_flags():
    class MyConfig(Config):
        a: str = field(flags=['-a', '--a-long'])

    c = MyConfig.load_from_args('-a foo'.split())
    assert c.a == 'foo'

    c = MyConfig.load_from_args('--a-long bar'.split())
    assert c.a == 'bar'


def test_load_from_args_configured_required(capsys):
    class MyConfig(Config):
        a: str = field(default='def', required=True)

    c = MyConfig.load_from_args('--a foo'.split())
    assert c.a == 'foo'

    with pytest.raises(SystemExit):
        MyConfig.load_from_args(''.split())
    assert 'required: --a' in capsys.readouterr().err


def test_load_from_args_simple_parsers(capsys):
    class MyConfig(Config):
        b: bool
        s: str = field(
            parser=yuio.parse.OneOf(yuio.parse.Str(), ['x', 'y'])
        )

    c = MyConfig.load_from_args('--b --s x'.split())
    assert c.b is True
    assert c.s is 'x'

    with pytest.raises(SystemExit):
        MyConfig.load_from_args('--s z'.split())
    assert 'one of x, y' in capsys.readouterr().err


def test_load_from_args_collection_parsers():
    os.environ.clear()

    class MyConfig(Config):
        b: list = field(
            parser=yuio.parse.List(
                yuio.parse.Pair(
                    yuio.parse.Str(), yuio.parse.Int())))
        s: typing.Set[int]
        x: typing.Tuple[int, float]
        d: typing.Dict[str, int]

    c = MyConfig.load_from_args(
        '--b a:1 b:2 --s 1 2 3 5 3 --x 1 2 --d a:10 b:20'.split())
    assert c.b == [('a', 1), ('b', 2)]
    assert c.s == {1, 2, 3, 5}
    assert c.x == (1, 2.0)
    assert c.d == {'a': 10, 'b': 20}


def test_load_from_args_bool_flag():
    class MyConfig(Config):
        a: bool
        b: bool
        c: bool
        d: bool

    c = MyConfig.load_from_args('--a --no-b --c yes --d no'.split())
    assert c.a is True
    assert c.b is False
    assert c.c is True
    assert c.d is False


def test_load_from_args_subconfig():
    class SubConfig(Config):
        a: str

    class MyConfig(Config):
        b: str
        sub: SubConfig

    c = MyConfig.load_from_args('--b foo --sub-a bar'.split())
    assert c.b == 'foo'
    assert c.sub.a == 'bar'


def test_load_from_args_subconfig_custom_prefix():
    class SubConfig(Config):
        a: str

    class MyConfig(Config):
        b: str
        sub: SubConfig = field(flags='--sub-sub')

    c = MyConfig.load_from_args('--b foo --sub-sub-a bar'.split())
    assert c.b == 'foo'
    assert c.sub.a == 'bar'


def test_load_from_args_subconfig_no_prefix():
    class SubConfig(Config):
        a: str

    class MyConfig(Config):
        b: str
        sub: SubConfig = field(flags='')

    c = MyConfig.load_from_args('--b foo --a bar'.split())
    assert c.b == 'foo'
    assert c.sub.a == 'bar'


class DocSubConfig(Config):
    #: help for `a`
    a: str


class DocConfig(Config):
    #: help for `sub`
    sub: DocSubConfig


def test_load_from_args_help():
    help = DocConfig.setup_arg_parser().format_help()
    assert 'help for `sub`:' in help
    assert 'help for `a`' in help


def test_load_from_parsed_file():
    pass


def test_load_from_parsed_file_unknown_fields():
    pass


def test_load_from_parsed_file_unknown_fields_ignored():
    pass


def test_load_from_parsed_file_type_mismatch():
    pass


def test_load_from_parsed_file_subconfig():
    pass


def test_load_from_json_file():
    pass


def test_load_from_yaml_file():
    pass


def test_load_from_toml_file():
    pass
