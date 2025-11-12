# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

__all__ = []

# from __future__ import annotations

# import abc
# import re
# import sys
# from dataclasses import dataclass

# import yuio
# import yuio.complete
# import yuio.parse
# import yuio.term
# from yuio import _typing as _t

# __all__ = []

# T = _t.TypeVar("T")

# _PREFIX_CHARS = tuple("-+")

# _SHORT_FLAG_RE = r"^[-+][a-zA-Z0-9]$"
# _LONG_FLAG_RE = r"^[-+][a-zA-Z0-9_+/-]+$"

# _NUM_RE = r"""(?x)
#     ^
#     [+-]?
#     (?:
#       (?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?
#       |0[bB][01]+
#       |0[oO][0-7]+
#       |0[xX][0-9a-fA-F]+
#     )
#     $
# """

# NArgs: _t.TypeAlias = int | _t.Literal["?", "*", "+"]
# """
# Type alias for nargs.

# """


# class ArgumentError(yuio.parse.ParsingError):
#     pass


# @dataclass(kw_only=True)
# class Option(abc.ABC):
#     """
#     Base class for a CLI option.

#     """

#     metavar: str = "<value>"
#     """
#     Option's meta variable, used for displaying help messages.

#     """

#     completer: yuio.complete.Completer | None = None
#     """
#     Option's completer, used for generating completion scripts.

#     """

#     usage: yuio.Group | bool = True
#     """
#     Specifies whether this option should be displayed in CLI usage.

#     """

#     help: str = ""
#     """
#     Help message for an option.

#     """

#     flags: list[str] | yuio.Positional
#     """
#     Flags corresponding to this option.

#     """

#     nargs: NArgs
#     """
#     How many arguments this option takes.

#     """

#     mutually_exclusive_group: None | _t.Any = None
#     """
#     Index of a mutually exclusive group.

#     """

#     dest: str
#     """
#     Key where to store parsed argument.

#     """

#     @abc.abstractmethod
#     def process(
#         self,
#         cli_parser: CliParser,
#         name: str,
#         args: str | list[str],
#         ns: _t.MutableMapping[str, _t.Any],
#     ):
#         """
#         Process this argument.

#         This method is called every time an option is encountered
#         on the command line. It should parse option's args and merge them
#         with previous values, if there are any.

#         When option's arguments are passed separately (i.e. ``--opt arg1 arg2 ...``),
#         ``args`` is given as a list. List's length is checked against ``nargs``
#         before this method is called.

#         When option's arguments are passed as an inline value (i.e. ``--long=arg``
#         or ``-Sarg``), the ``args`` is given as a string. ``nargs`` are not checked
#         in this case, giving you an opportunity to handle inline option
#         however you like.

#         :param cli_parser:
#             CLI parser instance that's doing the parsing. Not to be confused with
#             :class:`yuio.parse.Parser`.
#         :param name:
#             name of the flag that set this option. For positional options, an empty
#             string is passed.
#         :param args:
#             option arguments, see above.
#         :param ns:
#             namespace where parsed arguments should be stored.
#         :raises:
#             :class:`ArgumentError`, :class:`~yuio.parse.ParsingError`.

#         """

#     def format_usage(self) -> yuio.term.ColorizedString:
#         """
#         Allows customizing how this option looks in CLI usage.

#         """

#         return yuio.term.ColorizedString()

#     def format_toc_usage(self) -> yuio.term.ColorizedString:
#         """
#         Allows customizing how this option looks in CLI help.

#         """

#         return yuio.term.ColorizedString()


# @dataclass(kw_only=True)
# class SubCommandOption(Option):
#     """
#     A positional option for subcommands.

#     """

#     subcommands: dict[str, Command]
#     """
#     All subcommands.

#     """

#     ns_dest: str
#     """
#     Where to save subcommand's namespace.

#     """

#     ns_ctor: _t.Callable[[], _t.MutableMapping[str, _t.Any]]
#     """
#     A constructor that will be called to create namespace for subcommand's arguments.

#     """

#     def __init__(
#         self,
#         *,
#         subcommands: dict[str, Command],
#         subcommand_required: bool,
#         ns_dest: str,
#         ns_ctor: _t.Callable[[], _t.MutableMapping[str, _t.Any]],
#         **kwargs,
#     ):
#         super().__init__(
#             metavar="<subcommand>",
#             completer=None,
#             usage=True,
#             flags=[],
#             nargs=1 if subcommand_required else "?",
#             mutually_exclusive_group=None,
#             **kwargs,
#         )

#         self.subcommands = subcommands
#         self.ns_dest = ns_dest
#         self.ns_ctor = ns_ctor

#     def process(
#         self,
#         cli_parser: CliParser,
#         name: str,
#         args: str | list[str],
#         ns: _t.MutableMapping[str, _t.Any],
#     ):
#         assert isinstance(args, list) and len(args) == 1
#         subcommand = self.subcommands.get(args[0])
#         if subcommand is None:
#             allowed_subcommands = ", ".join(sorted(self.subcommands))
#             raise ArgumentError(
#                 f"unknown subcommand {args[0]}, can be one of {allowed_subcommands}"
#             )
#         ns[self.dest] = subcommand.name
#         ns[self.ns_dest] = new_ns = self.ns_ctor()
#         cli_parser._load_command(subcommand, new_ns)


# @dataclass
# class BoolOption(Option):
#     """
#     An option with flags to set :data:`True` and :data:`False` values.

#     """

#     parser: yuio.parse.Parser[bool]
#     """
#     A parser used to parse bools when an explicit value is provided.

#     """

#     neg_flags: list[str]
#     """
#     List of flag names that negate this boolean option.

#     """

#     def __init__(
#         self,
#         *,
#         flags: list[str],
#         neg_flags: list[str],
#         parser: yuio.parse.Parser[bool] | None = None,
#         **kwargs,
#     ):
#         self.parser = parser or yuio.parse.Bool()
#         self.neg_flags = neg_flags

#         super().__init__(
#             completer=None,
#             flags=flags + neg_flags,
#             nargs=0,
#             **kwargs,
#         )

#     def process(
#         self,
#         cli_parser: CliParser,
#         name: str,
#         args: str | list[str],
#         ns: _t.MutableMapping[str, _t.Any],
#     ):
#         if name in self.neg_flags:
#             if isinstance(args, str):
#                 raise ArgumentError(f"{name} expected 0 arguments, got 1")
#             ns[self.dest] = False
#         elif isinstance(args, str):
#             ns[self.dest] = self.parser.parse(args)
#         else:
#             ns[self.dest] = True


# @dataclass
# class ParseOneOption(Option, _t.Generic[T]):
#     """
#     An option with a single argument that uses Yuio parser.

#     """

#     parser: yuio.parse.Parser[T]
#     """
#     A parser used to parse bools when an explicit value is provided.

#     """

#     merge: _t.Callable[[T, T], T] | None
#     """
#     Function to merge previous and new value.

#     """

#     def __init__(
#         self,
#         *,
#         parser: yuio.parse.Parser[T],
#         merge: _t.Callable[[T, T], T] | None = None,
#         **kwargs,
#     ):
#         self.parser = parser
#         self.merge = merge

#         super().__init__(
#             nargs=1,
#             **kwargs,
#         )

#         if self.completer is None:
#             self.completer = self.parser.completer()

#     def process(
#         self,
#         cli_parser: CliParser,
#         name: str,
#         args: str | list[str],
#         ns: _t.MutableMapping[str, _t.Any],
#     ):
#         if not isinstance(args, str):
#             args = args[0]
#         try:
#             value = self.parser.parse(args)
#         except yuio.parse.ParsingError as e:
#             raise e.with_prefix("Error in <c flag>%s</c>:", name) from None
#         if self.merge and self.dest in ns:
#             ns[self.dest] = self.merge(ns[self.dest], value)
#         else:
#             ns[self.dest] = value


# @dataclass
# class ParseManyOption(Option, _t.Generic[T]):
#     """
#     An option with a multiple arguments that uses Yuio parser.

#     """

#     parser: yuio.parse.Parser[T]
#     """
#     A parser used to parse bools when an explicit value is provided.

#     """

#     merge: _t.Callable[[T, T], T] | None
#     """
#     Function to merge previous and new value.

#     """

#     def __init__(
#         self,
#         *,
#         parser: yuio.parse.Parser[T],
#         merge: _t.Callable[[T, T], T] | None = None,
#         **kwargs,
#     ):
#         self.parser = parser
#         self.merge = merge

#         super().__init__(
#             nargs=self.parser.get_nargs(),
#             **kwargs,
#         )

#         if self.completer is None:
#             self.completer = self.parser.completer()

#     def process(
#         self,
#         cli_parser: CliParser,
#         name: str,
#         args: str | list[str],
#         ns: _t.MutableMapping[str, _t.Any],
#     ):
#         try:
#             if isinstance(args, str):
#                 value = self.parser.parse(args)
#             else:
#                 value = self.parser.parse_many(args)
#         except yuio.parse.ParsingError as e:
#             raise e.with_prefix("Error in <c flag>%s</c>:", name) from None
#         if self.merge and self.dest in ns:
#             ns[self.dest] = self.merge(ns[self.dest], value)
#         else:
#             ns[self.dest] = value


# @dataclass
# class ConstOption(Option, _t.Generic[T]):
#     """
#     An option with no arguments that stores a constant to namespace.

#     """

#     const: T
#     """
#     Constant that will be stored.

#     """

#     merge: _t.Callable[[T, T], T] | None
#     """
#     Function to merge previous and new value.

#     """

#     def __init__(
#         self,
#         *,
#         const: T,
#         merge: _t.Callable[[T, T], T] | None = None,
#         **kwargs,
#     ):
#         self.const = const
#         self.merge = merge

#         super().__init__(
#             nargs=0,
#             **kwargs,
#         )

#     def process(
#         self,
#         cli_parser: CliParser,
#         name: str,
#         args: str | list[str],
#         ns: _t.MutableMapping[str, _t.Any],
#     ):
#         if isinstance(args, str):
#             raise ArgumentError(f"{name} expected 0 arguments, got 1")

#         if self.merge and self.dest in ns:
#             ns[self.dest] = self.merge(ns[self.dest], self.const)
#         else:
#             ns[self.dest] = self.const


# @dataclass
# class CountOption(ConstOption[int]):
#     """
#     An option that counts number of its appearances on the command line.

#     """

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs, const=1, merge=lambda l, r: l + r)


# @dataclass
# class StoreTrueOption(ConstOption[bool]):
#     """
#     An option that stores :data:`True` to namespace.

#     """

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs, const=True)


# @dataclass
# class StoreFalseOption(ConstOption[bool]):
#     """
#     An option that stores :data:`False` to namespace.

#     """

#     def __init__(self, **kwargs):
#         super().__init__(**kwargs, const=False)


# @dataclass
# class Command:
#     """
#     Data about CLI interface of a single command or subcommand.

#     """

#     name: str
#     """
#     Name of this command.

#     """

#     desc: str
#     """
#     Long description for a command.

#     """

#     help: str
#     """
#     Help message displayed when listing subcommands.

#     """

#     options: list[Option]
#     """
#     Options for this command.

#     """

#     subcommands: dict[str, Command]
#     """
#     Last positional option can be a sub-command.

#     This is a map from subcommand's name or alias to subcommand's implementation.

#     Subcommand's implementation is either a :class:`Command` or a callable that takes
#     name/alias which invoked a subcommand, and returns a :class:`Command` instance.

#     The latter is especially useful to set up command's options and bind them
#     to a namespace.

#     """

#     subcommand_required: bool
#     """
#     Whether subcommand is required or optional.

#     """

#     def make_subcommand_option(self) -> SubCommandOption | None:
#         """
#         Turn :attr:`~Command.subcommands` and :attr:`~Command.subcommand_required`
#         into a :class:`SubCommandOption`.

#         Return :data:`None` if this command doesn't have any subcommands.

#         """

#         if not self.subcommands:
#             return None
#         else:
#             return SubCommandOption(
#                 subcommands=self.subcommands,
#                 subcommand_required=self.subcommand_required,
#                 help=self.help,
#                 dest="subcommand",
#                 ns_dest="subcommand_data",
#                 ns_ctor=dict,
#             )


# @dataclass
# class _BoundOption:
#     wrapped: Option
#     ns: _t.MutableMapping[str, _t.Any]

#     @property
#     def metavar(self):
#         return self.wrapped.metavar

#     @property
#     def completer(self):
#         return self.wrapped.completer

#     @property
#     def usage(self):
#         return self.wrapped.usage

#     @property
#     def flags(self):
#         return self.wrapped.flags

#     @property
#     def nargs(self):
#         return self.wrapped.nargs

#     @property
#     def mutually_exclusive_group(self):
#         return self.wrapped.mutually_exclusive_group

#     @property
#     def dest(self):
#         return self.wrapped.dest


# class CliParser:
#     """
#     CLI arguments parser.

#     :param command:
#         root command.

#     """

#     def __init__(self, command: Command, ns: _t.MutableMapping[str, _t.Any]) -> None:
#         self._root_command = command
#         self._allow_abbrev = True

#         self._seen_mutex_groups: dict[_t.Any, tuple[_BoundOption, str]] = {}

#         self._known_long_args: dict[str, _BoundOption] = {}
#         self._known_short_args: dict[str, _BoundOption] = {}

#         self._current_positional: int = 0
#         self._current_positional_args: list[str] = []

#         self._current_flag: _BoundOption | None = None
#         self._current_flag_name: str = ""
#         self._current_flag_args: list[str] = []

#         self._positionals = []
#         self._current_positional = 0

#         self._load_command(command, ns)

#     def _load_command(self, command: Command, ns: _t.MutableMapping[str, _t.Any]):
#         # All pending flags and positionals should'be been flushed by now.
#         assert self._current_flag is None
#         assert self._current_positional == len(self._positionals)

#         # Update known flags and positionals.
#         self._positionals = []
#         for option in command.options:
#             if option.flags is yuio.POSITIONAL:
#                 self._positionals.append(option)
#             else:
#                 for flag in option.flags:
#                     if _is_short(flag):
#                         dest = self._known_short_args
#                     else:
#                         dest = self._known_short_args
#                     dest[flag] = _BoundOption(option, ns)
#         if subcommand := command.make_subcommand_option():
#             self._positionals.append(subcommand)
#         self._current_positional = 0

#     def parse(self, args: list[str] | None):
#         """
#         Parse arguments and invoke their actions.

#         :param args:
#             CLI arguments, not including the program name (i.e. the first argument).
#             If :data:`None`, use :data:`sys.argv` instead.
#         :returns:
#             subcommand path, starting with the name of the root command,
#             and namespace filled with parsing results.
#         :raises:
#             :class:`ArgumentError`, :class:`~yuio.parse.ParsingError`.

#         """

#         if args is None:
#             args = sys.argv[1:]

#         allow_flags = True

#         for arg in args:
#             # Handle `--`.
#             if arg == "--" and allow_flags:
#                 self._flush_flag()
#                 allow_flags = False
#                 continue

#             # Check what we have here.
#             if allow_flags:
#                 result = self._detect_flag(arg, accept_negative_numbers=False)
#             else:
#                 result = None

#             if result is None:
#                 # This not a flag. Can be an argument to a positional/flag option.
#                 self._handle_positional(arg)
#             else:
#                 # This is a flag.
#                 options, inline_arg = result
#                 self._handle_flags(options, inline_arg)

#         self._flush_flag()
#         self._flush_positional()

#     def _detect_flag(
#         self, arg: str, accept_negative_numbers: bool
#     ) -> tuple[list[tuple[_BoundOption, str]], str | None] | None:
#         if not arg.startswith(_PREFIX_CHARS):
#             # This is a positional.
#             return None

#         # Detect long flag.
#         if "=" in arg:
#             long_arg, long_inline_arg = arg.split("=", maxsplit=1)
#         else:
#             long_arg, long_inline_arg = arg, None
#         if long_opt := self._known_long_args.get(long_arg):
#             return [(long_opt, long_arg)], long_inline_arg

#         # This can be an abbreviated long flag or a short flag.

#         # Try detecting short flags first.
#         prefix_char = arg[0]
#         short_opts: list[tuple[_BoundOption, str]] = []
#         short_inline_arg = None
#         unknown_ch = None
#         for i, ch in enumerate(arg[1:]):
#             if ch == "=":
#                 # Short flag with explicit argument.
#                 short_inline_arg = arg[i + 2 :]
#                 break
#             elif short_opts and short_opts[-1][0].nargs != 0:
#                 # Short flag with implicit argument.
#                 short_inline_arg = arg[i + 1 :]
#                 break
#             elif short_opt := self._known_short_args.get(prefix_char + ch):
#                 # Short flag, arguments may follow.
#                 short_opts.append((short_opt, prefix_char + ch))
#             else:
#                 # Unknown short flag. Will try parsing as abbreviated long flag next.
#                 unknown_ch = ch
#                 break

#         # Try as abbreviated long flags.
#         candidates = []
#         if self._allow_abbrev:
#             for candidate in self._known_long_args:
#                 if candidate.startswith(long_arg):
#                     candidates.append(candidate)
#             if len(candidates) == 1:
#                 candidate = candidates[0]
#                 return [(self._known_long_args[candidate], candidate)], long_inline_arg

#         # Try as signed int.
#         if re.match(_NUM_RE, arg):
#             # This is a positional.
#             return None

#         # Exhausted all options, raise an error.
#         if candidates:
#             raise ArgumentError(
#                 "Unknown flag <c flag>%s</c>, can be "
#                 + "".join([""] * len(candidates)),
#                 long_arg,
#                 *candidates,
#             )
#         elif unknown_ch:
#             raise ArgumentError(
#                 "Unknown short option {prefix_char}{short_inline_arg} in argument {arg}"
#             )
#         else:
#             raise ArgumentError("Unknown flag {arg}")

#     def _handle_positional(self, arg: str):
#         if self._current_flag is not None:
#             # This is an argument for a flag option.
#             self._current_flag_args.append(arg)
#             nargs = self._current_flag.nargs
#             if nargs == "?" or (
#                 isinstance(nargs, int) and len(self._current_flag_args) == nargs
#             ):
#                 self._flush_flag()  # This flag is full.
#         else:
#             # This is an argument for a positional option.
#             if self._current_positional >= len(self._positionals):
#                 raise ArgumentError(f"unexpected positional argument {arg}")
#             self._current_positional_args.append(arg)
#             nargs = self._positionals[self._current_positional].nargs
#             if nargs == "?" or (
#                 isinstance(nargs, int) and len(self._current_positional_args) == nargs
#             ):
#                 self._flush_positional()  # This positional is full.

#     def _handle_flags(
#         self, options: list[tuple[_BoundOption, str]], inline_arg: str | None
#     ):
#         # If we've seen another flag before this one, and we were waiting
#         # for that flag's arguments, flush them now.
#         self._flush_flag()

#         # Handle short flags in multi-arg sequence, i.e. `-li` -> `-l -c`
#         for opt, name in options[:-1]:
#             self._eval_option(opt, name, [])

#         # Handle the last short flag in multi-arg sequence.
#         opt, name = options[-1]
#         if inline_arg is not None:
#             # Flag with an inline argument, i.e. `-Xfoo`/`-X=foo` -> `-X foo`
#             self._eval_option(opt, name, inline_arg)
#         else:
#             self._push_flag(opt, name)

#     def _flush_positional(self):
#         if self._current_positional >= len(self._positionals):
#             return
#         opt, args = (
#             self._positionals[self._current_positional],
#             self._current_positional_args,
#         )

#         self._current_positional += 1
#         self._current_positional_args = []

#         self._eval_option(opt, "", args)

#     def _flush_flag(self):
#         if self._current_flag is None:
#             return

#         opt, name, args = (
#             self._current_flag,
#             self._current_flag_name,
#             self._current_flag_args,
#         )

#         self._current_flag = None
#         self._current_flag_name = ""
#         self._current_flag_args = []

#         self._eval_option(opt, name, args)

#     def _push_flag(self, opt: _BoundOption, name: str):
#         assert self._current_flag is None

#         if opt.nargs == 0:
#             # Flag without arguments, handle it right now.
#             self._eval_option(opt, name, [])
#         else:
#             # Flag with possible arguments, save it. If we see a non-flag later,
#             # it will be added to this flag's arguments.
#             self._current_flag = opt
#             self._current_flag_name = name
#             self._current_flag_args = []

#     def _eval_option(self, opt: _BoundOption, name: str, args: str | list[str]):
#         metavar = name or opt.metavar
#         if opt.mutually_exclusive_group is not None:
#             if seen := self._seen_mutex_groups.get(opt.mutually_exclusive_group):
#                 prev_opt, prev_name = seen
#                 prev_name = prev_name or prev_opt.metavar
#                 raise ArgumentError(f"{metavar} can't be given with option {prev_name}")
#             self._seen_mutex_groups[opt.mutually_exclusive_group] = opt, name

#         if isinstance(args, list):
#             if opt.nargs == "?":
#                 if len(args) > 1:
#                     raise ArgumentError(
#                         f"{metavar} expected at most 1 argument, got {len(args)}"
#                     )
#             elif opt.nargs == "+":
#                 if not args:
#                     raise ArgumentError(
#                         f"{metavar} requires at least one argument, got 0"
#                     )
#             elif opt.nargs != "*":
#                 if len(args) != opt.nargs:
#                     s = "" if opt.nargs == 1 else "s"
#                     raise ArgumentError(
#                         f"{metavar} expected {opt.nargs} argument{s}, got {len(args)}"
#                     )

#         opt.wrapped.process(self, name, args, opt.ns)


# def _is_short(flag: str):
#     if not flag.startswith(_PREFIX_CHARS):
#         pchars = " or ".join(map(repr, _PREFIX_CHARS))
#         raise TypeError(f"flag {flag!r} should start with {pchars}")
#     if len(flag) == 2:
#         if not re.match(_SHORT_FLAG_RE, flag):
#             raise TypeError(f"invalid short flag {flag!r}")
#         return True
#     elif len(flag) == 1:
#         raise TypeError(f"flag {flag!r} is too short")
#     else:
#         if not re.match(_LONG_FLAG_RE, flag):
#             raise TypeError(f"invalid long flag {flag!r}")
#         return False
