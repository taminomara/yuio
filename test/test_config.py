import enum
import typing

import pytest

from yuio.config import *


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

    assert repr(MyConfig()) == "MyConfig(\n  f1='1'\n)"
    assert repr(MyConfig(f1='x')) == "MyConfig(\n  f1='x'\n)"
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

    assert repr(MyConfig()) == "MyConfig(\n  sub=SubConfig(\n    a='a'\n  )\n)"
    assert repr(MyConfig(sub=SubConfig(b='2'))) == \
           "MyConfig(\n  sub=SubConfig(\n    a='a',\n    b='2'\n  )\n)"


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


def test_load_from_env_configured():
    os.environ.clear()

    class MyConfig(Config):
        f1: str = field('f1', env='FX')

    os.environ['F1'] = 'f1.2'
    c = MyConfig.load_from_env()
    assert c.f1 == 'f1'

    os.environ['FX'] = 'f1.3'
    c = MyConfig.load_from_env()
    assert c.f1 == 'f1.3'


def test_load_from_env_parsers():
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


def test_load_from_config():
    pass


def test_load_from_config_unknown_options():
    pass


def test_load_from_config_unknown_options_ignored():
    pass


def test_load_from_config_parsers():
    pass


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


def test_load_from_args_configured():
    pass


def test_load_from_args_parsers():
    pass


def test_load_from_args_bool_flag():
    pass


def test_load_from_args_subconfig():
    pass
