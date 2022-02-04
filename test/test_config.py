import enum
import os
import typing

import pytest

import yuio.config


def test_default():
    class Config(yuio.config.Config):
        f1: str = '1'
        f2: str = '2'

    c = Config()
    assert c.f1 == '1'
    assert c.f2 == '2'

    c = Config(f2='b')
    assert c.f1 == '1'
    assert c.f2 == 'b'

    c = Config(f1='a', f2='b')
    assert c.f1 == 'a'
    assert c.f2 == 'b'


def test_default_field():
    class Config(yuio.config.Config):
        f1: str = yuio.config.field('1')
        f2: str = yuio.config.field('2')

    c = Config()
    assert c.f1 == '1'
    assert c.f2 == '2'

    c = Config(f2='b')
    assert c.f1 == '1'
    assert c.f2 == 'b'

    c = Config(f1='a', f2='b')
    assert c.f1 == 'a'
    assert c.f2 == 'b'


def test_missing():
    class Config(yuio.config.Config):
        f1: str
        f2: str

    c = Config()
    with pytest.raises(AttributeError, match='f1 is not configured'):
        _ = c.f1
    with pytest.raises(AttributeError, match='f2 is not configured'):
        _ = c.f2

    c = Config(f1='a')
    assert c.f1 == 'a'
    with pytest.raises(AttributeError, match='f2 is not configured'):
        _ = c.f2

    c = Config(f1='a', f2='b')
    assert c.f1 == 'a'
    assert c.f2 == 'b'


def test_missing_field():
    class Config(yuio.config.Config):
        f1: str = yuio.config.field()
        f2: str = yuio.config.field()

    c = Config()
    with pytest.raises(AttributeError, match='f1 is not configured'):
        _ = c.f1
    with pytest.raises(AttributeError, match='f2 is not configured'):
        _ = c.f2

    c = Config(f1='a')
    assert c.f1 == 'a'
    with pytest.raises(AttributeError, match='f2 is not configured'):
        _ = c.f2

    c = Config(f1='a', f2='b')
    assert c.f1 == 'a'
    assert c.f2 == 'b'


def test_init():
    class Config(yuio.config.Config):
        f1: str
        f2: str

    with pytest.raises(TypeError, match=r'unknown field\(s\): x'):
        Config(x=1)

    with pytest.raises(TypeError, match=r'unknown field\(s\): x, y'):
        Config(f1='a', x=1, y=2)


def test_repr():
    class Config(yuio.config.Config):
        f1: str = '1'
        f2: str

    assert repr(Config()) == 'Config()'
    assert repr(Config(f1='x')) == "Config(f1='x')"
    assert repr(Config(f2='y')) == "Config(f2='y')"


def test_inheritance():
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


def test_update():
    class Config(yuio.config.Config):
        f1: str = 'f1'
        f2: str

    c = Config(f1='f1.2')
    c.update(Config(f1='f1.3'))
    assert c.f1 == 'f1.3'

    c = Config(f1='f1.2')
    c.update(Config())
    assert c.f1 == 'f1.2'

    c = Config(f1='f1.2')
    c.update(Config(f2='f2'))
    assert c.f1 == 'f1.2'
    assert c.f2 == 'f2'

    c = Config(f1='f1.2', f2='f2')
    c.update(Config(f2='f2.2'))
    assert c.f1 == 'f1.2'
    assert c.f2 == 'f2.2'


def test_load_from_env():
    os.environ.clear()

    class Config(yuio.config.Config):
        f1: str
        f2: str = 'f2'

    c = Config.load_from_env()
    with pytest.raises(AttributeError, match='is not configured'):
        _ = c.f1
    assert c.f2 == 'f2'

    os.environ['F1'] = 'f1.2'
    c = Config.load_from_env()
    assert c.f1 == 'f1.2'
    assert c.f2 == 'f2'

    os.environ['F2'] = 'f2.2'
    c = Config.load_from_env()
    assert c.f1 == 'f1.2'
    assert c.f2 == 'f2.2'


def test_load_from_env_disabled():
    os.environ.clear()

    class Config(yuio.config.Config):
        f_disabled: str = yuio.config.field(
            'f_disabled', env=yuio.config.disabled())
        f_enabled: str = 'f_enabled'

    os.environ['F_DISABLED'] = 'f_disabled.2'
    os.environ['F_ENABLED'] = 'f_enabled.2'
    c = Config.load_from_env()
    assert c.f_disabled == 'f_disabled'
    assert c.f_enabled == 'f_enabled.2'


def test_load_from_env_configured():
    os.environ.clear()

    class Config(yuio.config.Config):
        f1: str = yuio.config.field('f1', env='FX')

    os.environ['F1'] = 'f1.2'
    c = Config.load_from_env()
    assert c.f1 == 'f1'

    os.environ['FX'] = 'f1.3'
    c = Config.load_from_env()
    assert c.f1 == 'f1.3'


def test_load_from_env_parsers():
    os.environ.clear()

    class Config(yuio.config.Config):
        b: bool
        s: str = yuio.config.field(
            parser=yuio.parse.OneOf(yuio.parse.Str(), ['x', 'y'])
        )

    os.environ['B'] = 'y'
    os.environ['S'] = 'x'
    c = Config.load_from_env()
    assert c.b is True
    assert c.s is 'x'

    os.environ['S'] = 'z'
    with pytest.raises(ValueError, match='one of x, y'):
        _ = Config.load_from_env()

    os.environ.clear()

    class E(enum.Enum):
        A = enum.auto()
        B = enum.auto()

    class Config(yuio.config.Config):
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

    c = Config.load_from_env()
    assert c.b is False
    assert c.s == 'str'
    assert c.f == 1.5
    assert c.i == -10
    assert c.e is E.B

    os.environ.clear()

    class Config(yuio.config.Config):
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

    c = Config.load_from_env()
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
