# import typing as _t

# from yuio.app import *
# from yuio.config import *
# import yuio.parse

# import pytest


# class TestArgs:
#     def test_no_args(self):
#         pass


# class TestPositionals:
#     def test_single_positional(self, capsys):
#         run_result = {}

#         @app
#         def cmd(p: int = positional()):
#             run_result.update(locals())

#         try:
#             cmd.run('10'.split())
#         except SystemExit as e:
#             assert e.code == 0
#         assert run_result['p'] == 10

#         with pytest.raises(SystemExit):
#             cmd.run(''.split())
#         assert 'the following arguments are required: <p>' in capsys.readouterr().err

#         with pytest.raises(SystemExit):
#             cmd.run('1 2'.split())
#         assert 'unrecognized arguments: 2' in capsys.readouterr().err

#         with pytest.raises(SystemExit):
#             cmd.run('abc'.split())
#         assert 'could not parse value \'abc\' as an int' in capsys.readouterr().err

#         assert '[-h] [-v] <p>' in cmd._setup_arg_parser().format_usage()

#     def test_single_positional_with_default(self, capsys):
#         run_result = {}

#         @app
#         def cmd(p: int = positional(15)):
#             run_result.update(locals())

#         cmd.run('10'.split())
#         assert run_result['p'] == 10

#         cmd.run(''.split())
#         assert run_result['p'] == 15

#         with pytest.raises(SystemExit):
#             cmd.run('abc'.split())
#         assert 'could not parse value \'abc\' as an int' in capsys.readouterr().err

#         assert '[-h] [-v] [<p>]' in cmd._setup_arg_parser().format_usage()

#     def test_optional_positional(self, capsys):
#         run_result = {}

#         @app
#         def cmd(p: _t.Optional[int] = positional()):
#             run_result.update(locals())

#         cmd.run('10'.split())
#         assert run_result['p'] == 10

#         with pytest.raises(SystemExit):
#             cmd.run(''.split())
#         assert 'the following arguments are required: <p>' in capsys.readouterr().err

#         with pytest.raises(SystemExit):
#             cmd.run('abc'.split())
#         assert 'could not parse value \'abc\' as an int' in capsys.readouterr().err

#         assert '[-h] [-v] <p>' in cmd._setup_arg_parser().format_usage()

#     def test_optional_positional_with_default(self, capsys):
#         run_result = {}

#         @app
#         def cmd(p: _t.Optional[int] = positional(15)):
#             run_result.update(locals())

#         cmd.run('10'.split())
#         assert run_result['p'] == 10

#         cmd.run(''.split())
#         assert run_result['p'] == 15

#         with pytest.raises(SystemExit):
#             cmd.run('abc'.split())
#         assert 'could not parse value \'abc\' as an int' in capsys.readouterr().err

#         assert '[-h] [-v] [<p>]' in cmd._setup_arg_parser().format_usage()

#     def test_list_positional(self, capsys):
#         run_result = {}

#         @app
#         def cmd(p: _t.List[int] = positional()):
#             run_result.update(locals())

#         cmd.run(''.split())
#         assert run_result['p'] == []

#         cmd.run('10'.split())
#         assert run_result['p'] == [10]

#         cmd.run('10 11 12'.split())
#         assert run_result['p'] == [10, 11, 12]

#         with pytest.raises(SystemExit):
#             cmd.run('10 abc 12'.split())
#         assert 'could not parse value \'abc\' as an int' in capsys.readouterr().err

#         assert '[-h] [-v] [<p> ...]' in cmd._setup_arg_parser().format_usage()

#     def test_list_positional_len_bounds_ge(self, capsys):
#         run_result = {}

#         @app
#         def cmd(
#             p: _t.List[int] = positional(
#                 parser=yuio.parse.List(yuio.parse.Int()).len_ge(2))
#         ):
#             run_result.update(locals())

#         cmd.run('1 2'.split())
#         assert run_result['p'] == [1, 2]

#         cmd.run('1 2 3'.split())
#         assert run_result['p'] == [1, 2, 3]

#         with pytest.raises(SystemExit):
#             cmd.run(''.split())
#         assert 'the following arguments are required: <p>' in capsys.readouterr().err

#         with pytest.raises(SystemExit):
#             cmd.run('1'.split())
#         assert (
#             'argument <p>: length of a value should be greater or equal to 2, '
#             'got [1] instead' in capsys.readouterr().err
#         )

#         assert '[-h] [-v] <p> [<p> ...]' in cmd._setup_arg_parser().format_usage()

#     def test_list_positional_len_bounds_eq(self, capsys):
#         run_result = {}

#         @app
#         def cmd(
#             p: _t.List[int] = positional(
#                 parser=yuio.parse.List(yuio.parse.Int()).len_eq(2))
#         ):
#             run_result.update(locals())

#         cmd.run('1 2'.split())
#         assert run_result['p'] == [1, 2]

#         with pytest.raises(SystemExit):
#             cmd.run(''.split())
#         assert 'the following arguments are required: <p>' in capsys.readouterr().err

#         with pytest.raises(SystemExit):
#             cmd.run('1'.split())
#         assert 'the following arguments are required: <p>' in capsys.readouterr().err

#         with pytest.raises(SystemExit):
#             cmd.run('1 2 3'.split())
#         assert 'unrecognized arguments: 3' in capsys.readouterr().err

#         assert '[-h] [-v] <p> <p>' in cmd._setup_arg_parser().format_usage()

#     def test_list_positional_with_default(self):
#         @app
#         def cmd(p: _t.List[int] = positional([])):
#             assert False, 'should never launch'

#         with pytest.raises(TypeError, match='positional multi-value arguments can\'t have defaults'):
#             cmd.run(''.split())

#     def test_tuple_positional(self):
#         pass

#     def test_tuple_positional_with_default(self):
#         pass


# class TestSubCommands:
#     # test subcommands with positionals
#     # test context
#     pass


# class TestSubConfigs:
#     pass


# class TestHelp:
#     pass


# # int                               - R (-)
# # int = 5                           - O (?)

# # optional[int]                     - R (-)
# # optional[int] = 5                 - O (?)

# # list[int]                         - R (*)
# # list[int] = []                    - O (*)

# # optional[list[int]]               - R (*)
# # optional[list[int]] = None        - O (*)

# # optional[tuple[int, int]]         - R (2)
# # optional[tuple[int, int]] = None  - O (0|2)

# # simple:
# #  - -> ?
# #  ? -> ?

# # positional:
# #  - -> ?
# #  ? -> ?

# #  * -> *
# #  + -> *
# #  n -> 0|n
