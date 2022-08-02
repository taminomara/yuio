import os.path
import py.path
import pytest

from yuio.parse import *


def test_str():
    parser = Str()
    assert parser('Test') == 'Test'
    assert parser.parse('Test') == 'Test'
    assert parser.parse_config('Test') == 'Test'
    with pytest.raises(ValueError, match='expected a string'):
        parser.parse_config(10)


def test_str_lower():
    parser = Str().lower()
    assert parser('Test') == 'test'
    assert parser.parse('Test') == 'test'
    assert parser.parse_config('Test') == 'test'
    with pytest.raises(ValueError, match='expected a string'):
        parser.parse_config(10)


def test_str_upper():
    parser = Str().upper()
    assert parser('Test') == 'TEST'
    assert parser.parse('Test') == 'TEST'
    assert parser.parse_config('Test') == 'TEST'
    with pytest.raises(ValueError, match='expected a string'):
        parser.parse_config(10)


def test_int():
    parser = Int()
    assert parser('1') == 1
    assert parser.parse('1') == 1
    assert parser.parse_config(1) == 1
    assert parser.parse_config(1.0) == 1
    with pytest.raises(ValueError, match='could not parse'):
        parser.parse('x')
    with pytest.raises(ValueError, match='expected an int'):
        parser.parse_config(1.5)
    with pytest.raises(ValueError, match='expected an int'):
        parser.parse_config('x')


def test_float():
    parser = Float()
    assert parser('1.5') == 1.5
    assert parser('-10') == -10.0
    assert parser('2e9') == 2e9
    assert parser.parse_config(1.0) == 1.0
    assert parser.parse_config(1.5) == 1.5
    with pytest.raises(ValueError, match='could not parse'):
        parser.parse('x')
    with pytest.raises(ValueError, match='expected a float'):
        parser.parse_config('x')


def test_bool():
    parser = Bool()
    assert parser('y') is True
    assert parser('yes') is True
    assert parser('yEs') is True
    assert parser('n') is False
    assert parser('no') is False
    assert parser('nO') is False
    with pytest.raises(ValueError):
        parser.parse('Meh')
    assert parser.parse_config(True) is True
    assert parser.parse_config(False) is False
    with pytest.raises(ValueError, match='expected a bool'):
        parser.parse_config('x')

    assert parser.describe() == 'yes|no'
    assert parser.describe_value(True) == 'yes'
    assert parser.describe_value(False) == 'no'


def test_enum():
    class Cuteness(enum.Enum):
        CATS = enum.auto()
        DOGS = enum.auto()
        BLAHAJ = ':3'

    parser = Enum(Cuteness)
    assert parser('CATS') is Cuteness.CATS
    assert parser.parse('CATS') is Cuteness.CATS
    assert parser.parse_config('CATS') is Cuteness.CATS
    assert parser('dogs') is Cuteness.DOGS
    assert parser('Blahaj') is Cuteness.BLAHAJ
    with pytest.raises(ValueError):
        parser('Unchi')
    with pytest.raises(ValueError, match='expected a string'):
        parser.parse_config(10)

    assert parser.describe() == 'CATS|DOGS|BLAHAJ'
    assert parser.describe_value(Cuteness.BLAHAJ) == 'BLAHAJ'


def test_int_enum():
    class Colors(enum.IntEnum):
        RED = 31
        GREEN = 32
        BLUE = 34

    parser = Enum(Colors)
    assert parser('RED') is Colors.RED
    assert parser.parse('RED') is Colors.RED
    assert parser.parse_config('RED') is Colors.RED
    assert parser('green') is Colors.GREEN
    assert parser('Blue') is Colors.BLUE
    with pytest.raises(ValueError):
        parser('Color of a beautiful sunset')
    with pytest.raises(ValueError, match='expected a string'):
        parser.parse_config(10)

    assert parser.describe() == 'RED|GREEN|BLUE'
    assert parser.describe_value(Colors.RED) == 'RED'


def test_optional():
    parser = Optional(Int())
    assert parser('') is None
    assert parser('1') == 1
    with pytest.raises(ValueError):
        parser.parse('asd')
    assert parser.parse_config(None) is None
    assert parser.parse_config(1) == 1
    with pytest.raises(ValueError, match='expected an int'):
        parser.parse_config('3')


def test_list():
    parser = List(Int())
    assert parser('') == []
    assert parser('1 2 3') == [1, 2, 3]
    assert parser('1\n2') == [1, 2]
    with pytest.raises(ValueError):
        parser.parse('1:2')
    assert parser.parse_many(['1', '2']) == [1, 2]
    assert parser.parse_config([1, 2, 3]) == [1, 2, 3]
    with pytest.raises(ValueError, match='expected an int'):
        parser.parse_config([2, '3'])
    with pytest.raises(ValueError, match='expected a list'):
        parser.parse_config(10)

    assert parser.describe() == 'int[ int[ ...]]'

    with pytest.raises(ValueError, match='empty delimiter'):
        List(Int(), delimiter='')


def test_set():
    parser = Set(Int())
    assert parser('') == set()
    assert parser('1 2 3') == {1, 2, 3}
    assert parser('1 2 1') == {1, 2}
    with pytest.raises(ValueError):
        parser.parse('1:2')
    assert parser.parse_many(['1', '2']) == {1, 2}
    assert parser.parse_config([1, 2, 1]) == {1, 2}
    with pytest.raises(ValueError, match='expected an int'):
        parser.parse_config([2, '3'])
    with pytest.raises(ValueError, match='expected a list'):
        parser.parse_config(10)

    assert parser.describe() == 'int[ int[ ...]]'

    with pytest.raises(ValueError, match='empty delimiter'):
        Set(Int(), delimiter='')


def test_frozenset():
    parser = FrozenSet(Int())
    assert parser('') == frozenset()
    assert parser('1 2 3') == frozenset({1, 2, 3})
    assert parser('1 2 1') == frozenset({1, 2})
    with pytest.raises(ValueError):
        parser.parse('1:2')
    assert parser.parse_many(['1', '2']) == frozenset({1, 2})
    assert parser.parse_config([1, 2, 1]) == frozenset({1, 2})
    with pytest.raises(ValueError, match='expected an int'):
        parser.parse_config([2, '3'])
    with pytest.raises(ValueError, match='expected a list'):
        parser.parse_config(10)

    assert parser.describe() == 'int[ int[ ...]]'

    with pytest.raises(ValueError, match='empty delimiter'):
        FrozenSet(Int(), delimiter='')


def test_dict():
    parser = Dict(Int(), Str(), '-')
    assert parser('10:abc') == {10: 'abc'}
    assert parser('10:abc-11:xyz') == {10: 'abc', 11: 'xyz'}
    with pytest.raises(ValueError, match='could not parse'):
        parser('10')
    assert parser.describe() == 'int:str[-int:str[-...]]'
    assert parser.describe_value({1: 'z', 2: 'y'}) == '1:z-2:y'

    parser = Dict(Int(), Pair(Str(), Str()))
    assert parser('10:abc:xyz 11:abc::') \
           == {10: ('abc', 'xyz'), 11: ('abc', ':')}
    assert parser.describe() == 'int:str:str[ int:str:str[ ...]]'
    assert parser.describe_value({-5: ('xyz', 'abc'), 10: ('a', 'b')}) \
           == '-5:xyz:abc 10:a:b'
    with pytest.raises(ValueError, match='empty delimiter'):
        Dict(Int(), Int(), delimiter='')


def test_pair():
    parser = Pair(Int(), Str(), '-')
    assert parser('10-abc') == (10, 'abc')
    assert parser('10-abc-xyz') == (10, 'abc-xyz')
    with pytest.raises(ValueError, match='could not parse'):
        parser('10')
    assert parser.describe() == 'int-str'
    assert parser.describe_value((-5, 'xyz')) == '-5-xyz'

    parser = Pair(Int(), Pair(Str(), Str()))
    assert parser('10:abc:xyz') == (10, ('abc', 'xyz'))
    assert parser('10:abc::') == (10, ('abc', ':'))
    assert parser('10::xyz') == (10, ('', 'xyz'))
    with pytest.raises(ValueError, match='could not parse'):
        parser('10:abc')
    assert parser.describe() == 'int:str:str'
    assert parser.describe_value((-5, ('xyz', 'abc'))) == '-5:xyz:abc'
    with pytest.raises(ValueError, match='empty delimiter'):
        Pair(Int(), Int(), delimiter='')


def test_tuple():
    parser = Tuple(Int(), Int(), Str())
    assert parser('1 2 asd') == (1, 2, 'asd')
    assert parser('1 2 asd dsa') == (1, 2, 'asd dsa')
    with pytest.raises(ValueError, match='could not parse'):
        parser('1 2')
    with pytest.raises(ValueError, match='as an int'):
        parser('1 dsa asd')
    with pytest.raises(ValueError, match='empty tuple'):
        Tuple()
    with pytest.raises(ValueError, match='empty delimiter'):
        Tuple(Int(), delimiter='')


def test_path():
    parser = Path()
    assert str(parser('/a/s/d')) == '/a/s/d'
    assert str(parser('/a/s/d/..')) == '/a/s'
    assert str(parser('a/s/d')) == os.path.abspath('a/s/d')
    assert str(parser('./a/s/./d')) == os.path.abspath('a/s/d')
    assert str(parser('~/a')) == os.path.expanduser('~/a')

    parser = Path(extensions=['.cfg', '.txt'])
    assert str(parser('/a/s/d.cfg')) == '/a/s/d.cfg'
    assert str(parser('/a/s/d.txt')) == '/a/s/d.txt'
    with pytest.raises(ValueError, match='should have extension .cfg, .txt'):
        parser('file.sql')


def test_file(tmpdir: py.path.local):
    tmpdir.join('file.cfg').write('hi!')

    parser = File()
    assert str(parser(tmpdir.join('file.cfg').strpath)) \
           == tmpdir.join('file.cfg').strpath
    with pytest.raises(ValueError, match='doesn\'t exist'):
        parser(tmpdir.join('file.txt').strpath)
    with pytest.raises(ValueError, match='is not a file'):
        parser(tmpdir.strpath)

    parser = File(extensions=['.cfg', '.txt'])
    assert str(parser(tmpdir.join('file.cfg').strpath)) \
           == tmpdir.join('file.cfg').strpath
    with pytest.raises(ValueError, match='doesn\'t exist'):
        parser(tmpdir.join('file.txt').strpath)
    with pytest.raises(ValueError, match='should have extension .cfg, .txt'):
        parser(tmpdir.join('file.sql').strpath)


def test_dir(tmpdir: py.path.local):
    tmpdir.join('file.cfg').write('hi!')

    parser = Dir()
    assert str(parser('~')) == os.path.expanduser('~')
    assert str(parser(tmpdir.strpath)) == tmpdir.strpath
    with pytest.raises(ValueError, match='doesn\'t exist'):
        parser(tmpdir.join('subdir').strpath)
    with pytest.raises(ValueError, match='is not a directory'):
        parser(tmpdir.join('file.cfg').strpath)


def test_git_repo(tmpdir: py.path.local):
    tmpdir.join('file.cfg').write('hi!')

    parser = GitRepo()
    with pytest.raises(ValueError, match='is not a git repository'):
        parser(tmpdir.strpath)
    with pytest.raises(ValueError, match='doesn\'t exist'):
        parser(tmpdir.join('subdir').strpath)
    with pytest.raises(ValueError, match='is not a directory'):
        parser(tmpdir.join('file.cfg').strpath)

    tmpdir.join('.git').mkdir()

    assert str(parser(tmpdir.strpath)) == tmpdir.strpath


def test_bound():
    with pytest.raises(TypeError, match='lower and lower_inclusive'):
        Bound(Int(), lower=0, lower_inclusive=1)
    with pytest.raises(TypeError, match='upper and upper_inclusive'):
        Bound(Int(), upper=0, upper_inclusive=1)

    parser = Bound(Int())

    assert parser('0') == 0
    assert parser('-10') == -10
    assert parser('10') == 10

    parser.lower_bound(0)
    assert parser('10') == 10
    with pytest.raises(ValueError, match='should be greater than 0'):
        parser('-1')
    with pytest.raises(ValueError, match='should be greater than 0'):
        parser('0')

    parser.lower_bound_inclusive(0)
    assert parser('10') == 10
    assert parser('0') == 0
    with pytest.raises(ValueError, match='should be greater or equal to 0'):
        parser('-1')

    parser.upper_bound(10)
    assert parser('5') == 5
    with pytest.raises(ValueError, match='should be lesser than 10'):
        parser('10')
    with pytest.raises(ValueError, match='should be lesser than 10'):
        parser('11')

    parser.upper_bound_inclusive(10)
    assert parser('5') == 5
    assert parser('10') == 10
    with pytest.raises(ValueError, match='should be lesser or equal to 10'):
        parser('11')

    parser = Bound(Int(), lower_inclusive=0, upper_inclusive=5)
    assert parser('0') == 0
    assert parser('2') == 2
    assert parser('5') == 5
    with pytest.raises(ValueError, match='should be greater or equal to 0'):
        parser('-1')
    with pytest.raises(ValueError, match='should be lesser or equal to 5'):
        parser('6')

    parser = Bound(Int(), lower=0, upper=5)
    assert parser('2') == 2
    with pytest.raises(ValueError, match='should be greater than 0'):
        parser('0')
    with pytest.raises(ValueError, match='should be lesser than 5'):
        parser('5')


def test_one_of():
    parser = OneOf(Str(), ['qux', 'duo'])
    assert parser('qux') == 'qux'
    assert parser('duo') == 'duo'
    with pytest.raises(ValueError, match="qux, duo"):
        parser('foo')
    with pytest.raises(ValueError, match="qux, duo"):
        parser('Qux')
    with pytest.raises(ValueError, match="qux, duo"):
        parser('Duo')

    assert parser.describe() == 'qux|duo'

    parser = OneOf(Str().lower(), ['qux', 'duo'])
    assert parser('Qux') == 'qux'
    assert parser('Duo') == 'duo'


def test_regex():
    parser = Regex(Str(), r'^a|b$')
    assert parser('a') == 'a'
    assert parser('b') == 'b'
    with pytest.raises(ValueError, match=r"should match regex '\^a\|b\$'"):
        parser('foo')
