import pytest

import yuio
import yuio.cli
import yuio.config
import yuio.parse
import yuio.rst

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


def make_command(
    name: str = "test",
    options: _t.Collection[yuio.cli.Option[_t.Any]] | None = None,
    subcommands: dict[str, yuio.cli.Command[_t.Any]] | None = None,
    subcommand_required: bool = False,
    dest: str = "",
    ns_dest: str = "",
) -> yuio.cli.Command[dict[str, _t.Any]]:
    return yuio.cli.Command(
        name=name,
        desc="",
        help="",
        usage=None,
        epilog="",
        options=list(options or []),
        subcommands=subcommands or {},
        subcommand_required=subcommand_required,
        ns_ctor=dict,
        dest=dest,
        ns_dest=ns_dest,
    )


def str_option(
    flags: list[str] | yuio.Positional = ["--name"],
    dest: str = "name",
    required: bool = False,
    **kwargs,
) -> yuio.cli.ParseOneOption[str]:
    return yuio.cli.ParseOneOption(
        flags=flags,
        parser=yuio.parse.Str(),
        required=required,
        dest=dest,
        **kwargs,
    )


def int_option(
    flags: list[str] | yuio.Positional = ["--count"],
    dest: str = "count",
    metavar: str = "<n>",
    required: bool = False,
    **kwargs,
) -> yuio.cli.ParseOneOption[int]:
    return yuio.cli.ParseOneOption(
        flags=flags,
        parser=yuio.parse.Int(),
        required=required,
        dest=dest,
        **kwargs,
    )


def float_option(
    flags: list[str] | yuio.Positional = ["--value"],
    dest: str = "value",
    required: bool = False,
    **kwargs,
) -> yuio.cli.ParseOneOption[float]:
    return yuio.cli.ParseOneOption(
        flags=flags,
        parser=yuio.parse.Float(),
        required=required,
        dest=dest,
        **kwargs,
    )


def bool_option(
    pos_flags: list[str] = ["--verbose", "-v"],
    neg_flags: list[str] = ["--no-verbose"],
    dest: str = "verbose",
    required: bool = False,
    **kwargs,
) -> yuio.cli.BoolOption:
    return yuio.cli.BoolOption(
        pos_flags=pos_flags,
        neg_flags=neg_flags,
        required=required,
        dest=dest,
        **kwargs,
    )


def store_true_option(
    flags: list[str] = ["--flag"],
    dest: str = "flag",
    required: bool = False,
    **kwargs,
) -> yuio.cli.StoreTrueOption:
    return yuio.cli.StoreTrueOption(
        flags=flags,
        required=required,
        dest=dest,
        **kwargs,
    )


def store_false_option(
    flags: list[str] = ["--no-flag"],
    dest: str = "flag",
    required: bool = False,
    **kwargs,
) -> yuio.cli.StoreFalseOption:
    return yuio.cli.StoreFalseOption(
        flags=flags,
        required=required,
        dest=dest,
        **kwargs,
    )


def count_option(
    flags: list[str] = ["-v", "--verbose"],
    dest: str = "verbosity",
    required: bool = False,
    **kwargs,
) -> yuio.cli.CountOption:
    return yuio.cli.CountOption(
        flags=flags,
        required=required,
        dest=dest,
        **kwargs,
    )


def list_option(
    flags: list[str] | yuio.Positional = ["--files"],
    dest: str = "files",
    nargs: yuio.cli.NArgs = "+",
    allow_no_args: bool = True,
    required: bool = False,
    **kwargs,
) -> yuio.cli.ParseManyOption[list[str]]:
    opt = yuio.cli.ParseManyOption(
        flags=flags,
        parser=yuio.parse.List(yuio.parse.Str()),
        required=required,
        dest=dest,
        **kwargs,
    )
    opt.nargs = nargs  # Override parser's nargs for tests.
    opt.allow_no_args = allow_no_args
    return opt


def tuple_option(
    *parsers: yuio.parse.Parser[_t.Any],
    flags: list[str] | yuio.Positional = ["--coords"],
    dest: str = "coords",
    required: bool = False,
    **kwargs,
) -> yuio.cli.ParseManyOption[_t.Any]:
    if not parsers:
        parsers = (yuio.parse.Int(), yuio.parse.Int())
    return yuio.cli.ParseManyOption(
        flags=flags,
        parser=yuio.parse.Tuple(*parsers),
        required=required,
        dest=dest,
        **kwargs,
    )


def const_option(
    const: _t.Any,
    flags: list[str] = ["--const"],
    dest: str = "const",
    required: bool = False,
    **kwargs,
) -> yuio.cli.StoreConstOption[_t.Any]:
    return yuio.cli.StoreConstOption(
        flags=flags,
        const=const,
        required=required,
        dest=dest,
        **kwargs,
    )


def parse_args(
    options: _t.Collection[yuio.cli.Option[_t.Any]] | None = None,
    args: list[str] | None = None,
    subcommands: dict[str, yuio.cli.Command[_t.Any]] | None = None,
    subcommand_required: bool = False,
    dest: str = "",
    ns_dest: str = "",
    allow_abbrev: bool = False,
) -> dict[str, _t.Any]:
    command = make_command(
        options=options,
        subcommands=subcommands,
        subcommand_required=subcommand_required,
        dest=dest,
        ns_dest=ns_dest,
    )
    parser = yuio.cli.CliParser(
        command, allow_abbrev=allow_abbrev, help_parser=yuio.rst.RstParser()
    )
    return parser.parse(args or [])


class TestBoolOption:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--verbose"], True),
            (["--no-verbose"], False),
            (["--verbose=true"], True),
            (["--verbose=false"], False),
            (["-v=true"], True),
            (["-v=false"], False),
        ],
    )
    def test_bool_variants(self, args, expected):
        ns = parse_args([bool_option()], args)
        assert ns["verbose"] is expected

    def test_explicit_value_with_negative_flag_raises(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([bool_option()], ["--no-verbose=false"])

    def test_implicit_value_with_short_flag_raises(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([bool_option()], ["-vfalse"])


class TestStoreConstOption:
    def test_const_value(self):
        ns = parse_args([const_option("json", ["--json"], "format")], ["--json"])
        assert ns["format"] == "json"

    def test_merge_const(self):
        option = yuio.cli.StoreConstOption(
            flags=["--add"],
            const=["item"],
            merge=lambda old, new: old + new,
            required=False,
            dest="items",
        )
        ns = parse_args([option], ["--add", "--add"])
        assert ns["items"] == ["item", "item"]


class TestStoreTrueAndFalse:
    def test_store_true(self):
        ns = parse_args([store_true_option(["--debug"], "debug")], ["--debug"])
        assert ns["debug"] is True

    def test_store_false(self):
        ns = parse_args([store_false_option(["--no-cache"], "cache")], ["--no-cache"])
        assert ns["cache"] is False


class TestCountOption:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["-v"], 1),
            (["-v", "-v", "-v"], 3),
            (["-vvv"], 3),
        ],
    )
    def test_count_variants(self, args, expected):
        ns = parse_args([count_option(["-v"])], args)
        assert ns["verbosity"] == expected


class TestParseOneOption:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--name", "Alice"], "Alice"),
            (["--name=Bob"], "Bob"),
        ],
    )
    def test_basic(self, args, expected):
        ns = parse_args([str_option()], args)
        assert ns["name"] == expected

    def test_int_parsing(self):
        ns = parse_args([int_option(["--count", "-c"])], ["--count", "42"])
        assert ns["count"] == 42

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["-n", "Charlie"], "Charlie"),
            (["-nDavid"], "David"),
            (["-n=David"], "David"),
        ],
    )
    def test_short_flag_variants(self, args, expected):
        ns = parse_args([str_option(["-n"])], args)
        assert ns["name"] == expected

    def test_merge_function(self):
        option = int_option(merge=lambda old, new: old + new)
        ns = parse_args([option], ["--count", "10", "--count", "5"])
        assert ns["count"] == 15

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["10"], 10),
            ([], None),
        ],
    )
    def test_optional_positional(self, args, expected):
        ns = parse_args([int_option(yuio.POSITIONAL, default=None)], args)
        assert ns.get("count") == expected


class TestParseManyOption:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--files", "a.txt", "b.txt", "c.txt"], ["a.txt", "b.txt", "c.txt"]),
            (["--files=a.txt b.txt c.txt"], ["a.txt", "b.txt", "c.txt"]),
        ],
    )
    def test_basic(self, args, expected):
        ns = parse_args([list_option(nargs="+", allow_no_args=True)], args)
        assert ns["files"] == expected

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["-f", "a.txt", "b.txt", "c.txt"], ["a.txt", "b.txt", "c.txt"]),
            (["-f=a.txt b.txt c.txt"], ["a.txt", "b.txt", "c.txt"]),
            (["-fa.txt b.txt c.txt"], ["a.txt", "b.txt", "c.txt"]),
        ],
    )
    def test_short_flag_variants(self, args, expected):
        ns = parse_args([list_option(["-f"], nargs="+", allow_no_args=True)], args)
        assert ns["files"] == expected

    def test_merge_function(self):
        option = list_option(merge=lambda old, new: old + new)
        ns = parse_args([option], ["--files", "a.txt", "--files", "b.txt", "c.txt"])
        assert ns["files"] == ["a.txt", "b.txt", "c.txt"]

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ([], None),
            (["10", "20"], (10, 20)),
        ],
    )
    def test_optional_positional(self, args, expected):
        ns = parse_args([tuple_option(flags=yuio.POSITIONAL, default=None)], args)
        assert ns.get("coords") == expected


class TestMutuallyExclusiveGroups:
    @pytest.fixture
    def mutex_options(self):
        group = yuio.config.MutuallyExclusiveGroup()
        return [
            store_true_option(["--json"], "json", mutex_group=group),
            store_true_option(["--xml"], "xml", mutex_group=group),
        ]

    @pytest.fixture
    def mutex_options_required_group(self):
        group = yuio.config.MutuallyExclusiveGroup(required=True)
        return [
            store_true_option(["--json"], "json", mutex_group=group),
            store_true_option(["--xml"], "xml", mutex_group=group),
        ]

    def test_mutually_exclusive_raises(self, mutex_options):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args(mutex_options, ["--json", "--xml"])

    def test_single_from_group_allowed(self, mutex_options):
        ns = parse_args(mutex_options, ["--json"])
        assert ns["json"] is True
        assert "xml" not in ns

    def test_none_from_group_allowed(self, mutex_options):
        ns = parse_args(mutex_options, [])
        assert "json" not in ns
        assert "xml" not in ns

    def test_single_from_required_mutex_group_allowed(
        self, mutex_options_required_group
    ):
        ns = parse_args(mutex_options_required_group, ["--json"])
        assert ns["json"] is True
        assert "xml" not in ns

    def test_required_mutex_group_raises(self, mutex_options_required_group):
        with pytest.raises(
            yuio.cli.ArgumentError,
            match=r"Either --json or --xml must be provided",
        ):
            parse_args(mutex_options_required_group, [])

    def test_positionals_cant_have_mutex_groups(self):
        group = yuio.config.MutuallyExclusiveGroup()
        options = [
            str_option(yuio.POSITIONAL, mutex_group=group),
        ]
        with pytest.raises(
            TypeError,
            match=r"positional arguments can't appear in mutually exclusive groups",
        ):
            parse_args(options, [])


class TestShortFlagCombinations:
    def test_combined_short_flags(self):
        options = [
            store_true_option(["-l"], "long"),
            store_true_option(["-a"], "all"),
            store_true_option(["-h"], "human"),
        ]
        ns = parse_args(options, ["-lah"])
        assert ns["long"] is True
        assert ns["all"] is True
        assert ns["human"] is True

    def test_combined_bool_flags(self):
        options = [
            bool_option(["-l"], [], "long"),
            bool_option(["-a"], [], "all"),
            bool_option(["-h"], [], "human"),
        ]
        ns = parse_args(options, ["-lah"])
        assert ns["long"] is True
        assert ns["all"] is True
        assert ns["human"] is True

    @pytest.mark.parametrize(
        ("args", "expected_output", "expected_verbose"),
        [
            (["-vo", "out.txt"], "out.txt", True),
            (["-voout.txt"], "out.txt", True),
            (["-vo=out.txt"], "out.txt", True),
            (["-ov"], "v", None),
        ],
    )
    def test_combined_with_argument_variants(
        self, args, expected_verbose, expected_output
    ):
        options = [
            store_true_option(["-v"], "verbose"),
            str_option(["-o"], "output"),
        ]
        ns = parse_args(options, args)
        assert ns.get("verbose") is expected_verbose
        assert ns["output"] == expected_output


class TestNumericArguments:
    def test_negative_number_as_positional(self):
        opt = yuio.cli.ParseManyOption(
            flags=yuio.POSITIONAL,
            parser=yuio.parse.List(yuio.parse.Int()),
            required=False,
            dest="numbers",
        )
        ns = parse_args([opt], ["-42", "-0x42", "-0o42", "-0b11"])
        assert ns["numbers"] == [-42, -0x42, -0o42, -0b11]

    def test_float_as_positional(self):
        ns = parse_args([float_option(yuio.POSITIONAL, "number")], ["-3.14"])
        assert ns["number"] == -3.14

    def test_negative_number_as_flag(self):
        opt = yuio.cli.ParseManyOption(
            flags=["--numbers"],
            parser=yuio.parse.List(yuio.parse.Int()),
            required=False,
            dest="numbers",
        )
        ns = parse_args([opt], ["--numbers", "-42", "-0x42", "-0o42", "-0b11"])
        assert ns["numbers"] == [-42, -0x42, -0o42, -0b11]

    def test_float_as_flag(self):
        ns = parse_args([float_option(["--number"], "number")], ["--number", "-3.14"])
        assert ns["number"] == -3.14

    def test_flag_takes_precedence_over_negative_numbers(self):
        options = [
            list_option(yuio.POSITIONAL, "numbers", nargs="+", allow_no_args=True),
            const_option(2, ["-4"], "meaning"),
        ]
        ns = parse_args(options, ["-4"])
        assert ns["meaning"] == 2
        assert ns["numbers"] == []


class TestCliParserBasic:
    def test_empty_args(self):
        ns = parse_args()
        assert ns == {}

    def test_unknown_flag_error(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([], ["--unknown"])

    def test_required_flag_missing(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([str_option(required=True)], [])

    def test_multiple_options(self):
        options = [
            str_option(["--name"], "name"),
            int_option(["--age"], "age"),
        ]
        ns = parse_args(options, ["--name", "Eve", "--age", "30"])
        assert ns["name"] == "Eve"
        assert ns["age"] == 30


class TestFlagAbbreviation:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--verb", "yes"], "yes"),
            (["--verb=yes"], "yes"),
        ],
    )
    def test_abbreviation_works(self, args, expected):
        ns = parse_args([str_option(["--verbose"], "verbose")], args, allow_abbrev=True)
        assert ns["verbose"] == expected

    def test_ambiguous_abbreviation_error(self):
        options = [
            store_true_option(["--verbose"], "verbose"),
            store_true_option(["--version"], "version"),
        ]
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args(options, ["--ver"], allow_abbrev=True)

    def test_abbreviation_raises_if_disabled(self):
        options = [str_option(["--verbose"], "verbose")]
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args(options, ["--verb"], allow_abbrev=False)


class TestPositionalArguments:
    def test_positional_argument(self):
        ns = parse_args([str_option(yuio.POSITIONAL, "file")], ["input.txt"])
        assert ns["file"] == "input.txt"

    def test_unexpected_positional_error(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([], ["unexpected"])


class TestNargs:
    @pytest.mark.parametrize(
        ("nargs", "allow_no_args", "args", "expected"),
        [
            ("+", True, [], []),
            ("+", True, ["a.txt"], ["a.txt"]),
            ("+", True, ["a.txt", "b.txt", "c.txt"], ["a.txt", "b.txt", "c.txt"]),
            ("+", False, ["a.txt"], ["a.txt"]),
            ("+", False, ["a.txt", "b.txt", "c.txt"], ["a.txt", "b.txt", "c.txt"]),
        ],
    )
    def test_nargs_and_allow_no_args(self, nargs, allow_no_args, args, expected):
        ns = parse_args(
            [
                list_option(
                    yuio.POSITIONAL, "files", nargs=nargs, allow_no_args=allow_no_args
                )
            ],
            args,
        )
        assert ns["files"] == expected

    def test_nargs_plus_requires_one(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args(
                [list_option(yuio.POSITIONAL, "files", nargs="+", allow_no_args=False)],
                [],
            )

    def test_nargs_integer_exact_count(self):
        ns = parse_args([tuple_option(flags=yuio.POSITIONAL)], ["10", "20"])
        assert ns["coords"] == (10, 20)

    def test_nargs_integer_too_few_arguments(self):
        option = list_option(
            yuio.POSITIONAL,
            "files",
            nargs=3,
            allow_no_args=False,
        )
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([option], ["10", "20"])

    def test_nargs_integer_too_few_arguments_allow_no_arguments(self):
        option = list_option(
            yuio.POSITIONAL,
            "files",
            nargs=3,
            allow_no_args=True,
        )
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([option], ["10", "20"])

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ([], []),
            (["myconfig.yaml"], ["myconfig.yaml"]),
        ],
    )
    def test_nargs_allow_no_args_1(self, args, expected):
        ns = parse_args(
            [
                list_option(
                    nargs=1, allow_no_args=True, dest="config", flags=yuio.POSITIONAL
                )
            ],
            args,
        )
        assert ns["config"] == expected

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            ([], []),
            (["a.yaml", "b.yaml", "c.yaml"], ["a.yaml", "b.yaml", "c.yaml"]),
        ],
    )
    def test_nargs_allow_no_args_n(self, args, expected):
        ns = parse_args(
            [
                list_option(
                    nargs=3, allow_no_args=True, dest="config", flags=yuio.POSITIONAL
                )
            ],
            args,
        )
        assert ns["config"] == expected


class TestNargsFlag:
    @pytest.mark.parametrize(
        ("nargs", "allow_no_args", "args", "expected"),
        [
            ("+", True, ["--files"], []),
            ("+", True, ["--files", "a.txt"], ["a.txt"]),
            (
                "+",
                True,
                ["--files", "a.txt", "b.txt", "c.txt"],
                ["a.txt", "b.txt", "c.txt"],
            ),
            ("+", False, ["--files", "a.txt"], ["a.txt"]),
            (
                "+",
                False,
                ["--files", "a.txt", "b.txt", "c.txt"],
                ["a.txt", "b.txt", "c.txt"],
            ),
        ],
    )
    def test_nargs_and_allow_no_args(self, nargs, allow_no_args, args, expected):
        ns = parse_args([list_option(nargs=nargs, allow_no_args=allow_no_args)], args)
        assert ns["files"] == expected

    def test_nargs_plus_requires_one(self):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([list_option(nargs="+", allow_no_args=False)], ["--files"])

    def test_nargs_integer_exact_count(self):
        ns = parse_args([tuple_option()], ["--coords", "10", "20"])
        assert ns["coords"] == (10, 20)

    def test_nargs_integer_too_few_arguments(self):
        option = tuple_option(
            yuio.parse.Int(),
            yuio.parse.Int(),
            yuio.parse.Int(),
        )
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args([option], ["--files", "10", "20"])

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--files"], []),
            (["--files", "myconfig.yaml"], ["myconfig.yaml"]),
        ],
    )
    def test_nargs_allow_no_args(self, args, expected):
        ns = parse_args([list_option(nargs=1, allow_no_args=True)], args)
        assert ns["files"] == expected


class TestFlagsAndPositionalsInteraction:
    @pytest.mark.parametrize(
        "args",
        [
            ["myfile.txt", "--verbose"],
            ["--verbose", "myfile.txt"],
        ],
    )
    def test_positional_and_flag_order(self, args):
        options = [
            str_option(yuio.POSITIONAL, "input"),
            store_true_option(["--verbose"], "verbose"),
        ]
        ns = parse_args(options, args)
        assert ns["input"] == "myfile.txt"
        assert ns["verbose"] is True

    def test_flag_with_value_between_positionals(self):
        options = [
            str_option(yuio.POSITIONAL, "source"),
            str_option(yuio.POSITIONAL, "dest"),
            str_option(["--format"], "format"),
        ]
        ns = parse_args(options, ["input.txt", "--format", "json", "output.txt"])
        assert ns["source"] == "input.txt"
        assert ns["dest"] == "output.txt"
        assert ns["format"] == "json"

    def test_multiple_positionals_different_nargs(self):
        options = [
            str_option(yuio.POSITIONAL, "cmd"),
            list_option(yuio.POSITIONAL, "args", nargs="+", allow_no_args=True),
        ]
        ns = parse_args(options, ["run", "arg1", "arg2"])
        assert ns["cmd"] == "run"
        assert ns["args"] == ["arg1", "arg2"]

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (
                ["output.txt", "input1.txt", "input2.txt"],
                {"dest": "output.txt", "files": ["input1.txt", "input2.txt"]},
            ),
            (
                ["--format", "json", "output.txt", "input1.txt", "input2.txt"],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "format": "json",
                },
            ),
            (
                ["--protocol", "smtp", "output.txt", "input1.txt", "input2.txt"],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "protocol": ["smtp"],
                },
            ),
            (
                ["--protocol", "--", "output.txt", "input1.txt", "input2.txt"],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "protocol": [],
                },
            ),
            (
                ["--protocol=smtp", "output.txt", "input1.txt", "input2.txt"],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "protocol": ["smtp"],
                },
            ),
            (
                [
                    "--protocol",
                    "--coords",
                    "10",
                    "20",
                    "output.txt",
                    "input1.txt",
                    "input2.txt",
                ],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "protocol": [],
                    "coords": (10, 20),
                },
            ),
            (
                [
                    "--configs",
                    "--patches",
                    "a.patch",
                    "b.patch",
                    "--",
                    "output.txt",
                    "input1.txt",
                    "input2.txt",
                ],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "patches": ["a.patch", "b.patch"],
                    "configs": [],
                },
            ),
            (
                [
                    "--configs",
                    "main.cfg",
                    "--patches",
                    "a.patch",
                    "b.patch",
                    "--",
                    "output.txt",
                    "input1.txt",
                    "input2.txt",
                ],
                {
                    "dest": "output.txt",
                    "files": ["input1.txt", "input2.txt"],
                    "patches": ["a.patch", "b.patch"],
                    "configs": ["main.cfg"],
                },
            ),
        ],
    )
    def test_positionals_and_flags_interactions(self, args, expected):
        options = [
            str_option(yuio.POSITIONAL, "dest"),
            list_option(yuio.POSITIONAL),
            str_option(["--format"], "format"),  # Nargs 1
            tuple_option(),  # Nargs 2
            list_option(["--configs"], "configs"),  # Nargs *
            list_option(["--patches"], "patches", nargs="+"),  # Nargs +
            list_option(
                ["--protocol"], "protocol", nargs=1, allow_no_args=True
            ),  # Nargs ?
        ]
        ns = parse_args(options, args)
        assert ns == expected


class TestDoubleDash:
    def test_double_dash_separates_flags_from_positionals(self):
        options = [
            store_true_option(["--verbose"], "verbose"),
            list_option(yuio.POSITIONAL, "files", nargs="+", allow_no_args=True),
        ]
        ns = parse_args(options, ["--", "--verbose", "-x", "file.txt"])
        assert "verbose" not in ns
        assert ns["files"] == ["--verbose", "-x", "file.txt"]


class TestUnknownFlags:
    @pytest.mark.parametrize(
        ("flags", "args", "match"),
        [
            (["-l", "-a", "-h"], ["-laUh"], r"Unknown flag.*-U"),
            (["-a"], ["-xa"], r"Unknown flag.*-x"),
            (["-a", "-b"], ["-abz"], r"Unknown flag.*-z"),
        ],
    )
    def test_unknown_flag_in_group(self, flags, args, match):
        options = [store_true_option([f], f"opt_{f[-1]}") for f in flags]
        with pytest.raises(yuio.cli.ArgumentError, match=match):
            parse_args(options, args)


class TestEdgeCases:
    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--config=key=value"], "key=value"),
            (["-c=key=value"], "key=value"),
            (["--name="], ""),
            (["--value=-5"], "-5"),
        ],
    )
    def test_special_values(self, args, expected):
        flag = args[0].split("=")[0]
        ns = parse_args([str_option([flag], "dest")], args)
        assert ns["dest"] == expected


class TestSubcommands:
    @pytest.fixture
    def sub_with_flag(self):
        sub_opt = str_option(["--sub-flag"], "sub_flag")
        return make_command(name="sub", options=[sub_opt])

    def test_subcommand_parsing(self, sub_with_flag):
        ns = parse_args(
            subcommands={"sub": sub_with_flag},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
            args=["sub", "--sub-flag", "value"],
        )
        assert ns["subcommand"] == "sub"
        assert ns["sub_ns"]["sub_flag"] == "value"

    def test_unknown_subcommand_error(self, sub_with_flag):
        with pytest.raises(yuio.cli.ArgumentError):
            parse_args(
                subcommands={"sub": sub_with_flag},
                subcommand_required=True,
                dest="subcommand",
                ns_dest="sub_ns",
                args=["unknown"],
            )

    def test_parent_flags_after_subcommand(self):
        parent_opt = store_true_option(["--parent-flag"], "parent_flag")
        subcommand = make_command(name="sub")
        ns = parse_args(
            options=[parent_opt],
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
            args=["sub", "--parent-flag"],
        )
        assert ns["subcommand"] == "sub"
        assert ns["parent_flag"] is True

    def test_two_level_subcommands(self):
        inner_sub = make_command(
            name="inner", options=[str_option(["--inner"], "inner")]
        )
        outer_sub = make_command(
            name="outer",
            options=[str_option(["--outer"], "outer")],
            subcommands={"inner": inner_sub},
            subcommand_required=True,
            dest="inner_cmd",
            ns_dest="inner_ns",
        )
        ns = parse_args(
            options=[store_true_option(["--root"], "root")],
            subcommands={"outer": outer_sub},
            subcommand_required=True,
            dest="outer_cmd",
            ns_dest="outer_ns",
            args=["--root", "outer", "--outer", "oval", "inner", "--inner", "ival"],
        )
        assert ns["root"] is True
        assert ns["outer_cmd"] == "outer"
        assert ns["outer_ns"]["outer"] == "oval"
        assert ns["outer_ns"]["inner_cmd"] == "inner"
        assert ns["outer_ns"]["inner_ns"]["inner"] == "ival"


class TestRequiredAndShadowedFlags:
    def test_shadowed_flag_generates_warning(self):
        parent_opt = str_option(["--name"], "parent_name")
        sub_opt = str_option(["--name"], "sub_name")
        subcommand = make_command(name="sub", options=[sub_opt])
        command = make_command(
            options=[parent_opt],
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )
        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.warns(yuio.cli.CliWarning, match="shadows"):
            ns = parser.parse(["sub", "--name", "value"])
        assert ns["sub_ns"]["sub_name"] == "value"

    def test_required_flag_missing(self):
        required_opt = yuio.cli.ParseOneOption(
            flags=["--required"],
            parser=yuio.parse.Str(),
            required=True,
            dest="required",
        )
        command = make_command(
            options=[required_opt],
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.raises(yuio.cli.ArgumentError, match="required"):
            parser.parse([])

    @pytest.mark.parametrize(
        "args",
        [
            ["--required", "value", "sub"],
            ["sub", "--required", "value"],
        ],
        ids=["before_subcommand", "after_subcommand"],
    )
    def test_required_flag_provided_at_various_positions(self, args):
        required_opt = yuio.cli.ParseOneOption(
            flags=["--required"],
            parser=yuio.parse.Str(),
            required=True,
            dest="required",
        )
        subcommand = make_command(name="sub")
        command = make_command(
            options=[required_opt],
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(args)
        assert ns["required"] == "value"
        assert ns["subcommand"] == "sub"

    def test_required_flag_shadowed_still_requires_parent(self):
        parent_opt = yuio.cli.ParseOneOption(
            flags=["--name"],
            parser=yuio.parse.Str(),
            required=True,
            dest="parent_name",
        )
        sub_opt = yuio.cli.ParseOneOption(
            flags=["--name"],
            parser=yuio.parse.Str(),
            required=False,
            dest="sub_name",
        )
        subcommand = make_command(name="sub", options=[sub_opt])
        command = make_command(
            options=[parent_opt],
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with (
            pytest.warns(yuio.cli.CliWarning, match="shadows"),
            pytest.raises(yuio.cli.ArgumentError, match="required"),
        ):
            parser.parse(["sub", "--name", "value"])

        with (
            pytest.warns(yuio.cli.CliWarning, match="shadows"),
            pytest.raises(yuio.cli.ArgumentError, match="required"),
        ):
            parser.parse(["sub"])

    def test_required_parent_flag_satisfied_before_shadow(self):
        parent_opt = yuio.cli.ParseOneOption(
            flags=["--name"],
            parser=yuio.parse.Str(),
            required=True,
            dest="parent_name",
        )
        sub_opt = yuio.cli.ParseOneOption(
            flags=["--name"],
            parser=yuio.parse.Str(),
            required=False,
            dest="sub_name",
        )
        subcommand = make_command(name="sub", options=[sub_opt])
        command = make_command(
            options=[parent_opt],
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.warns(yuio.cli.CliWarning, match="shadows"):
            ns = parser.parse(["--name", "parent_value", "sub", "--name", "sub_value"])
        assert ns["parent_name"] == "parent_value"
        assert ns["sub_ns"]["sub_name"] == "sub_value"

    def test_required_subcommand_flag_missing(self):
        sub_opt = yuio.cli.ParseOneOption(
            flags=["--required-sub"],
            parser=yuio.parse.Str(),
            required=True,
            dest="required_sub",
        )
        subcommand = make_command(name="sub", options=[sub_opt])
        command = make_command(
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.raises(yuio.cli.ArgumentError, match="required"):
            parser.parse(["sub"])

    def test_required_subcommand_flag_provided(self):
        sub_opt = yuio.cli.ParseOneOption(
            flags=["--required-sub"],
            parser=yuio.parse.Str(),
            required=True,
            dest="required_sub",
        )
        subcommand = make_command(name="sub", options=[sub_opt])
        command = make_command(
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["sub", "--required-sub", "value"])
        assert ns["sub_ns"]["required_sub"] == "value"

    def test_multiple_required_flags_all_missing(self):
        opt1 = yuio.cli.ParseOneOption(
            flags=["--req1"],
            parser=yuio.parse.Str(),
            required=True,
            dest="req1",
        )
        opt2 = yuio.cli.ParseOneOption(
            flags=["--req2"],
            parser=yuio.parse.Str(),
            required=True,
            dest="req2",
        )
        command = make_command(options=[opt1, opt2])

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.raises(yuio.cli.ArgumentError, match="required"):
            parser.parse([])

    def test_multiple_required_flags_one_missing(self):
        opt1 = yuio.cli.ParseOneOption(
            flags=["--req1"],
            parser=yuio.parse.Str(),
            required=True,
            dest="req1",
        )
        opt2 = yuio.cli.ParseOneOption(
            flags=["--req2"],
            parser=yuio.parse.Str(),
            required=True,
            dest="req2",
        )
        command = make_command(
            options=[opt1, opt2],
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.raises(yuio.cli.ArgumentError, match="required"):
            parser.parse(["--req1", "val1"])

    def test_multiple_required_flags_all_provided(self):
        opt1 = yuio.cli.ParseOneOption(
            flags=["--req1"],
            parser=yuio.parse.Str(),
            required=True,
            dest="req1",
        )
        opt2 = yuio.cli.ParseOneOption(
            flags=["--req2"],
            parser=yuio.parse.Str(),
            required=True,
            dest="req2",
        )
        command = make_command(
            options=[opt1, opt2],
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["--req1", "val1", "--req2", "val2"])
        assert ns["req1"] == "val1"
        assert ns["req2"] == "val2"

    def test_required_subcommand_flag_not_checked_when_subcommand_not_used(self):
        sub_opt = yuio.cli.ParseOneOption(
            flags=["--required-sub"],
            parser=yuio.parse.Str(),
            required=True,
            dest="required_sub",
        )
        subcommand = make_command(name="sub", options=[sub_opt])
        command = make_command(
            subcommands={"sub": subcommand},
            subcommand_required=False,  # Subcommand is optional
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        # No subcommand given - should succeed even though sub has required flag
        ns = parser.parse([])
        assert "subcommand" not in ns

    def test_required_subcommand_flag_not_checked_when_different_subcommand_used(self):
        sub1_opt = yuio.cli.ParseOneOption(
            flags=["--required-in-sub1"],
            parser=yuio.parse.Str(),
            required=True,
            dest="required_in_sub1",
        )
        sub1 = make_command(name="sub1", options=[sub1_opt])
        sub2 = make_command(name="sub2")  # No required flags

        command = make_command(
            subcommands={"sub1": sub1, "sub2": sub2},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        # Using sub2 - should succeed even though sub1 has required flag
        ns = parser.parse(["sub2"])
        assert ns["subcommand"] == "sub2"


class TestOptionalVsRequiredSubcommands:
    def test_required_subcommand_missing_error(self):
        subcommand = make_command(name="sub")
        command = make_command(
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.raises(yuio.cli.ArgumentError):
            parser.parse([])

    def test_required_subcommand_provided(self):
        subcommand = make_command(name="sub")
        command = make_command(
            subcommands={"sub": subcommand},
            subcommand_required=True,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["sub"])
        assert ns["subcommand"] == "sub"

    def test_optional_subcommand_not_provided(self):
        root_opt = yuio.cli.StoreTrueOption(
            flags=["--flag"],
            required=False,
            dest="flag",
        )
        subcommand = make_command(name="sub")
        command = make_command(
            options=[root_opt],
            subcommands={"sub": subcommand},
            subcommand_required=False,  # Optional
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["--flag"])
        assert ns["flag"] is True
        assert "subcommand" not in ns

    def test_optional_subcommand_provided(self):
        root_opt = yuio.cli.StoreTrueOption(
            flags=["--flag"],
            required=False,
            dest="flag",
        )
        subcommand = make_command(name="sub")
        command = make_command(
            options=[root_opt],
            subcommands={"sub": subcommand},
            subcommand_required=False,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["--flag", "sub"])
        assert ns["flag"] is True
        assert ns["subcommand"] == "sub"

    def test_optional_subcommand_with_flags_after(self):
        root_opt = yuio.cli.StoreTrueOption(
            flags=["--root"],
            required=False,
            dest="root",
        )
        sub_opt = yuio.cli.StoreTrueOption(
            flags=["--sub"],
            required=False,
            dest="sub",
        )
        subcommand = make_command(name="cmd", options=[sub_opt])
        command = make_command(
            options=[root_opt],
            subcommands={"cmd": subcommand},
            subcommand_required=False,
            dest="subcommand",
            ns_dest="sub_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["cmd", "--sub", "--root"])
        assert ns["root"] is True
        assert ns["subcommand"] == "cmd"
        assert ns["sub_ns"]["sub"] is True

    def test_multiple_subcommands_one_required(self):
        sub1 = make_command(name="build")
        sub2 = make_command(name="test")
        sub3 = make_command(name="deploy")
        command = make_command(
            subcommands={"build": sub1, "test": sub2, "deploy": sub3},
            subcommand_required=True,
            dest="action",
            ns_dest="action_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )

        ns = parser.parse(["build"])
        assert ns["action"] == "build"

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["test"])
        assert ns["action"] == "test"

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["deploy"])
        assert ns["action"] == "deploy"

    def test_subcommand_aliases(self):
        sub = make_command(name="build")
        # Same command under multiple names
        command = make_command(
            subcommands={"build": sub, "b": sub},
            subcommand_required=True,
            dest="action",
            ns_dest="action_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["build"])
        assert ns["action"] == "build"

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["b"])
        assert ns["action"] == "build"  # Should resolve to canonical name

    def test_nested_optional_subcommands(self):
        inner = make_command(name="inner")
        outer = make_command(
            name="outer",
            subcommands={"inner": inner},
            subcommand_required=False,  # Inner is optional
            dest="inner_cmd",
            ns_dest="inner_ns",
        )
        command = make_command(
            subcommands={"outer": outer},
            subcommand_required=False,  # Outer is also optional
            dest="outer_cmd",
            ns_dest="outer_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        # No subcommand
        ns = parser.parse([])
        assert "outer_cmd" not in ns

        # Just outer
        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["outer"])
        assert ns["outer_cmd"] == "outer"
        assert "inner_cmd" not in ns["outer_ns"]

        # Both outer and inner
        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["outer", "inner"])
        assert ns["outer_cmd"] == "outer"
        assert ns["outer_ns"]["inner_cmd"] == "inner"

    def test_required_inner_optional_outer_subcommand(self):
        inner = make_command(name="inner")
        outer = make_command(
            name="outer",
            subcommands={"inner": inner},
            subcommand_required=True,  # Inner is required when outer is used
            dest="inner_cmd",
            ns_dest="inner_ns",
        )
        command = make_command(
            subcommands={"outer": outer},
            subcommand_required=False,  # Outer is optional
            dest="outer_cmd",
            ns_dest="outer_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        # No subcommand - OK since outer is optional
        ns = parser.parse([])
        assert "outer_cmd" not in ns

        # Just outer without inner - should fail
        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        with pytest.raises(yuio.cli.ArgumentError):
            parser.parse(["outer"])

        # Both outer and inner - OK
        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["outer", "inner"])
        assert ns["outer_cmd"] == "outer"
        assert ns["outer_ns"]["inner_cmd"] == "inner"


class TestSubcommandEdgeCases:
    def test_subcommand_with_same_name_as_flag_value(self):
        flag_opt = yuio.cli.ParseOneOption(
            flags=["--mode"],
            parser=yuio.parse.Str(),
            required=False,
            dest="mode",
        )
        subcommand = make_command(name="run")
        command = make_command(
            options=[flag_opt],
            subcommands={"run": subcommand},
            subcommand_required=True,
            dest="cmd",
            ns_dest="cmd_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        # --mode takes "fast" as argument, "run" is subcommand
        ns = parser.parse(["--mode", "fast", "run"])
        assert ns["mode"] == "fast"
        assert ns["cmd"] == "run"

    def test_subcommand_with_positional_before_it(self):
        pos_opt = yuio.cli.ParseOneOption(
            flags=yuio.POSITIONAL,
            parser=yuio.parse.Str(),
            required=False,
            dest="config",
        )
        subcommand = make_command(name="run")
        command = make_command(
            options=[pos_opt],
            subcommands={"run": subcommand},
            subcommand_required=True,
            dest="cmd",
            ns_dest="cmd_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        ns = parser.parse(["config.yaml", "run"])
        assert ns["config"] == "config.yaml"
        assert ns["cmd"] == "run"

    def test_double_dash_before_subcommand(self):
        flag_opt = yuio.cli.StoreTrueOption(
            flags=["--flag"],
            required=False,
            dest="flag",
        )
        subcommand = make_command(name="--weird-name")
        # This is a weird edge case - subcommand name starts with --
        command = make_command(
            options=[flag_opt],
            subcommands={"--weird-name": subcommand},
            subcommand_required=True,
            dest="cmd",
            ns_dest="cmd_ns",
        )

        parser = yuio.cli.CliParser(
            command, allow_abbrev=False, help_parser=yuio.rst.RstParser()
        )
        # Using -- to force "--weird-name" to be treated as positional/subcommand
        ns = parser.parse(["--", "--weird-name"])
        assert ns["cmd"] == "--weird-name"


class TestMalformedFlags:
    @pytest.mark.parametrize(
        ("flag", "expected"),
        [
            ("-a", True),
            ("-Z", True),
            ("-0", True),
            ("--verbose", False),
            ("--my-flag", False),
        ],
    )
    def test_is_short_valid_flags(self, flag, expected):
        yuio.cli._check_flag(flag)
        assert yuio.cli._is_short(flag) is expected

    @pytest.mark.parametrize(
        ("flag", "match"),
        [
            ("noflag", "should start with"),
            ("-", "too short"),
            ("-!", "invalid short flag"),
            ("--", "invalid short flag"),
            ("--flag!", "invalid long flag"),
        ],
    )
    def test_is_short_invalid_flags(self, flag, match):
        with pytest.raises(TypeError, match=match):
            yuio.cli._check_flag(flag)


class TestConfigNamespace:
    def test_config_namespace_basic(self):
        class TestConfig(yuio.config.Config):
            name: str = ""
            count: int = 0
            knonw: int

        config = TestConfig()  # type: ignore
        ns = yuio.cli.ConfigNamespace(config)
        assert ns.config is config
        assert "name" not in ns
        assert "count" not in ns
        ns["name"] = "test"
        ns["count"] = 42
        assert config.name == "test"
        assert config.count == 42
        assert ns["name"] == "test"
        assert "name" in ns
        assert "known" not in ns
        assert "unknown" not in ns

    def test_config_namespace_nested(self):
        class InnerConfig(yuio.config.Config):
            count: int = 0

        class TestConfig(yuio.config.Config):
            name: str = ""
            inner: InnerConfig

        config = TestConfig()  # type: ignore
        ns = yuio.cli.ConfigNamespace(config)
        assert ns.config is config
        assert "inner.count" not in ns
        assert "inner.unknown" not in ns
        ns["inner.count"] = 42
        assert config.inner.count == 42
        assert ns["inner.count"] == 42
        assert "inner.count" in ns
        assert "inner.unknown" not in ns


class TestHelperFunctions:
    @pytest.mark.parametrize(
        ("input", "expected"),
        [
            ("simple", "simple"),
            ("with spaces", "'with spaces'"),
            ("with\0spaces", "'with spaces'"),
            ("", "''"),
            ("it's", "'it'\"'\"'s'"),
        ],
    )
    def test_quote(self, input, expected):
        assert yuio.cli._quote(input) == expected
