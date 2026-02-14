import textwrap
import types

import pytest

import yuio
import yuio.app
import yuio.config
from yuio.app import App, CommandInfo, app, field, inline, positional


@pytest.fixture
def width():
    return 120


@pytest.fixture(autouse=True)
def setup_argv(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "sys.argv", ["prog", "app should not use sys.argv if explicit args are given!"]
    )


@pytest.fixture
def results():
    return {}


class TestBasicArgumentParsing:
    def test_empty_args(self, results):
        @app
        def main(name: str = "", quiet: bool = False, count: int = 0):
            results["name"] = name
            results["quiet"] = quiet
            results["count"] = count

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 0
        assert results["name"] == ""
        assert results["quiet"] is False
        assert results["count"] == 0

    @pytest.mark.parametrize(
        ("args", "expected_name"),
        [
            (["--name", "Alice"], "Alice"),
            (["--name=Bob"], "Bob"),
        ],
    )
    def test_string_flag(self, results, args, expected_name):
        @app
        def main(name: str = ""):
            results["name"] = name

        with pytest.raises(SystemExit) as exc_info:
            main.run(args)
        assert exc_info.value.code == 0
        assert results["name"] == expected_name

    @pytest.mark.parametrize(
        ("args", "expected"),
        [
            (["--quiet"], True),
            (["--no-quiet"], False),
            (["--quiet=true"], True),
            (["--quiet=false"], False),
        ],
    )
    def test_bool_flag(self, results, args, expected):
        @app
        def main(quiet: bool = False):
            results["quiet"] = quiet

        with pytest.raises(SystemExit) as exc_info:
            main.run(args)
        assert exc_info.value.code == 0
        assert results["quiet"] is expected

    def test_int_flag(self, results):
        @app
        def main(count: int = 0):
            results["count"] = count

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--count", "42"])
        assert exc_info.value.code == 0
        assert results["count"] == 42

    def test_multiple_flags(self, results):
        @app
        def main(name: str = "", count: int = 0, quiet: bool = False):
            results["name"] = name
            results["count"] = count
            results["quiet"] = quiet

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--name", "Eve", "--count", "10", "--quiet"])
        assert exc_info.value.code == 0
        assert results["name"] == "Eve"
        assert results["count"] == 10
        assert results["quiet"] is True

    def test_keyword_only(self, results):
        @app
        def main(*, count: int = 0):
            results["count"] = count

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--count", "42"])
        assert exc_info.value.code == 0
        assert results["count"] == 42


class TestPositionalArguments:
    def test_positional_argument(self, results):
        with pytest.warns(
            yuio.YuioPendingDeprecationWarning,
            match="prefer using positional-only function arguments instead",
        ):

            @app
            def main(input_file: str = positional()):
                results["input_file"] = input_file

        with pytest.raises(SystemExit) as exc_info:
            main.run(["input.txt"])
        assert exc_info.value.code == 0
        assert results["input_file"] == "input.txt"

    def test_implicit_positional_argument(self, results):
        @app
        def main(input_file: str, /):
            results["input_file"] = input_file

        with pytest.raises(SystemExit) as exc_info:
            main.run(["input.txt"])
        assert exc_info.value.code == 0
        assert results["input_file"] == "input.txt"

    def test_positional_with_flag(self, results):
        with pytest.warns(
            yuio.YuioPendingDeprecationWarning,
            match="prefer using positional-only function arguments instead",
        ):

            @app
            def main(input_file: str = positional(), output: str = "out.txt"):
                results["input_file"] = input_file
                results["output"] = output

        with pytest.raises(SystemExit) as exc_info:
            main.run(["input.txt", "--output", "result.txt"])
        assert exc_info.value.code == 0
        assert results["input_file"] == "input.txt"
        assert results["output"] == "result.txt"

    def test_flag_before_positional(self, results):
        with pytest.warns(
            yuio.YuioPendingDeprecationWarning,
            match="prefer using positional-only function arguments instead",
        ):

            @app
            def main(input_file: str = positional(), output: str = "out.txt"):
                results["input_file"] = input_file
                results["output"] = output

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--output", "result.txt", "input.txt"])
        assert exc_info.value.code == 0
        assert results["input_file"] == "input.txt"
        assert results["output"] == "result.txt"

    def test_missing_required_positional(self):
        with pytest.warns(
            yuio.YuioPendingDeprecationWarning,
            match="prefer using positional-only function arguments instead",
        ):

            @app
            def main(input_file: str = positional()):
                pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1

    def test_positional_variadic(self, results):
        @app
        def main(*input_files: str):
            results["input_files"] = input_files

        with pytest.raises(SystemExit) as exc_info:
            main.run(["input.txt", "input-2.txt"])
        assert exc_info.value.code == 0
        assert results["input_files"] == ("input.txt", "input-2.txt")


class TestSubcommands:
    def test_subcommand_basic(self, results):
        @app
        def main():
            results["main_called"] = True

        @main.subcommand
        def build():
            results["build_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["build"])
        assert exc_info.value.code == 0
        assert results["main_called"] is True
        assert results["build_called"] is True

    def test_subcommand_with_args(self, results):
        @app
        def main():
            results["main_called"] = True

        @main.subcommand
        def build(target: str = "default"):
            results["target"] = target

        with pytest.raises(SystemExit) as exc_info:
            main.run(["build", "--target", "release"])
        assert exc_info.value.code == 0
        assert results["target"] == "release"

    def test_parent_flag_before_subcommand(self, results):
        @app
        def main(quiet: bool = False):
            results["quiet"] = quiet

        @main.subcommand
        def test_cmd():
            results["test_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--quiet", "test-cmd"])
        assert exc_info.value.code == 0
        assert results["quiet"] is True
        assert results["test_called"] is True

    def test_parent_flag_after_subcommand(self, results):
        @app
        def main(quiet: bool = False):
            results["quiet"] = quiet

        @main.subcommand
        def test_cmd():
            results["test_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["test-cmd", "--quiet"])
        assert exc_info.value.code == 0
        assert results["quiet"] is True
        assert results["test_called"] is True

    def test_unknown_subcommand_error(self):
        @app
        def main():
            pass

        @main.subcommand
        def sub():
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["unknown"])
        assert exc_info.value.code == 1

    def test_subcommand_required_by_default(self):
        @app
        def main():
            pass

        @main.subcommand
        def sub():
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1

    def test_optional_subcommand(self, results):
        @app
        def main(quiet: bool = False):
            results["quiet"] = quiet
            results["main_called"] = True

        main.subcommand_required = False

        @main.subcommand
        def sub():
            results["sub_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--quiet"])
        assert exc_info.value.code == 0
        assert results["quiet"] is True
        assert results["main_called"] is True
        assert "sub_called" not in results


class TestSubcommandAliases:
    def test_alias_resolves_to_canonical_name(self, results):
        @app
        def main():
            pass

        @main.subcommand(name="build", aliases=["b"])
        def build_cmd():
            results["build_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["b"])
        assert exc_info.value.code == 0
        assert results["build_called"] is True

        results.clear()
        with pytest.raises(SystemExit) as exc_info:
            main.run(["build"])
        assert exc_info.value.code == 0
        assert results["build_called"] is True


class TestNestedSubcommands:
    def test_two_level_subcommands(self, results):
        @app
        def main(root_flag: bool = False):
            results["root_flag"] = root_flag

        @main.subcommand
        def outer(outer_flag: str = ""):
            results["outer_flag"] = outer_flag

        @outer.subcommand
        def inner(inner_flag: int = 0):
            results["inner_flag"] = inner_flag

        with pytest.raises(SystemExit) as exc_info:
            main.run(
                [
                    "--root-flag",
                    "outer",
                    "--outer-flag",
                    "val",
                    "inner",
                    "--inner-flag",
                    "42",
                ]
            )
        assert exc_info.value.code == 0
        assert results["root_flag"] is True
        assert results["outer_flag"] == "val"
        assert results["inner_flag"] == 42


class TestCommandInfo:
    def test_command_info_name(self, results):
        @app
        def main(_command_info: CommandInfo):
            results["name"] = _command_info.name

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 0
        assert results["name"] == "__main__"

    def test_command_info_subcommand_none_when_no_subcommand(self, results):
        @app
        def main(_command_info: CommandInfo):
            results["subcommand"] = _command_info.subcommand

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 0
        assert results["subcommand"] is None

    def test_command_info_subcommand_present(self, results):
        @app
        def main(_command_info: CommandInfo):
            results["has_subcommand"] = _command_info.subcommand is not None
            if _command_info.subcommand:
                results["subcommand_name"] = _command_info.subcommand.name

        main.subcommand_required = False

        @main.subcommand
        def sub():
            results["sub_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["sub"])
        assert exc_info.value.code == 0
        assert results["has_subcommand"] is True
        assert results["subcommand_name"] == "sub"
        assert results["sub_called"] is True

    def test_command_info_manual_subcommand_invocation(self, results):
        @app
        def main(_command_info: CommandInfo):
            results["main_called"] = True
            if _command_info.subcommand:
                _command_info.subcommand()
            return False  # Prevent automatic subcommand invocation

        main.subcommand_required = False

        @main.subcommand
        def sub():
            results["sub_called"] = True
            results["sub_called_n"] = results.setdefault("sub_called_n", 0) + 1

        with pytest.raises(SystemExit) as exc_info:
            main.run(["sub"])
        assert exc_info.value.code == 0
        assert results["main_called"] is True
        assert results["sub_called"] is True
        assert results["sub_called_n"] == 1

    def test_command_info_manual_subcommand_invocation_without_explicit_prevention(
        self, results
    ):
        @app
        def main(_command_info: CommandInfo):
            results["main_called"] = True
            if _command_info.subcommand:
                _command_info.subcommand()
            # Don't prevent automatic subcommand invocation

        main.subcommand_required = False

        @main.subcommand
        def sub():
            results["sub_called"] = True
            results["sub_called_n"] = results.setdefault("sub_called_n", 0) + 1

        with pytest.raises(SystemExit) as exc_info:
            main.run(["sub"])
        assert exc_info.value.code == 0
        assert results["main_called"] is True
        assert results["sub_called"] is True
        assert results["sub_called_n"] == 1

    def test_command_info_prevent_subcommand_invocation(self, results):
        @app
        def main(_command_info: CommandInfo):
            results["main_called"] = True
            return False  # Prevent automatic subcommand invocation

        main.subcommand_required = False

        @main.subcommand
        def sub():
            results["sub_called"] = True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["sub"])
        assert exc_info.value.code == 0
        assert results["main_called"] is True
        assert "sub_called" not in results


class TestFieldFunction:
    def test_field_with_custom_flags(self, results):
        @app
        def main(output: str = field(default="", flags=["-o", "--output"])):
            results["output"] = output

        with pytest.raises(SystemExit) as exc_info:
            main.run(["-o", "test.txt"])
        assert exc_info.value.code == 0
        assert results["output"] == "test.txt"

    def test_field_required(self):
        @app
        def main(name: str = field(required=True)):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1


class TestInlineFunction:
    def test_inline_config(self, results):
        class DbConfig(yuio.config.Config):
            host: str = "localhost"
            port: int = 5432

        @app
        def main(db: DbConfig = inline()):
            results["host"] = db.host
            results["port"] = db.port

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--host", "example.com", "--port", "3306"])
        assert exc_info.value.code == 0
        assert results["host"] == "example.com"
        assert results["port"] == 3306


class TestConfigIntegration:
    def test_nested_config_with_prefix(self, results):
        class AuthConfig(yuio.config.Config):
            token: str = ""
            timeout: int = 30

        @app
        def main(auth: AuthConfig = field(flags="--auth")):
            results["token"] = auth.token
            results["timeout"] = auth.timeout

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--auth-token", "secret", "--auth-timeout", "60"])
        assert exc_info.value.code == 0
        assert results["token"] == "secret"
        assert results["timeout"] == 60


class TestEdgeCases:
    def test_empty_string_value(self, results):
        @app
        def main(name: str = "default"):
            results["name"] = name

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--name="])
        assert exc_info.value.code == 0
        assert results["name"] == ""

    def test_value_with_equals_sign(self, results):
        @app
        def main(config: str = ""):
            results["config"] = config

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--config=key=value"])
        assert exc_info.value.code == 0
        assert results["config"] == "key=value"

    def test_negative_numbers(self, results):
        @app
        def main(count: int = 0):
            results["count"] = count

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--count", "-5"])
        assert exc_info.value.code == 0
        assert results["count"] == -5

    def test_double_dash_separator(self, results):
        with pytest.warns(
            yuio.YuioPendingDeprecationWarning,
            match="prefer using positional-only function arguments instead",
        ):

            @app
            def main(flag: bool = False, files: list[str] = positional(default=[])):
                results["flag"] = flag
                results["files"] = files

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--", "--flag", "-x"])
        assert exc_info.value.code == 0
        assert results["flag"] is False
        assert results["files"] == ["--flag", "-x"]

    def test_unknown_flag_error(self):
        @app
        def main(name: str = ""):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--unknown"])
        assert exc_info.value.code == 1


class TestListArguments:
    def test_list_multiple_values(self, results):
        @app
        def main(files: list[str] = []):
            results["files"] = files

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--files", "a.txt", "b.txt", "c.txt"])
        assert exc_info.value.code == 0
        assert results["files"] == ["a.txt", "b.txt", "c.txt"]

    def test_list_inline_value(self, results):
        @app
        def main(files: list[str] = []):
            results["files"] = files

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--files=a.txt b.txt c.txt"])
        assert exc_info.value.code == 0
        assert results["files"] == ["a.txt", "b.txt", "c.txt"]

    def test_list_empty(self, results):
        @app
        def main(files: list[str] = []):
            results["files"] = files

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--files"])
        assert exc_info.value.code == 0
        assert results["files"] == []

    def test_list_specified_two_times(self, results):
        @app
        def main(files: list[str] = []):
            results["files"] = files

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--files", "a.txt", "b.txt", "--files", "x.txt", "y.txt"])
        assert exc_info.value.code == 0
        assert results["files"] == ["x.txt", "y.txt"]


class TestExitCodes:
    def test_unknown_flag_exits_with_1(self):
        @app
        def main(name: str = ""):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--unknown"])
        assert exc_info.value.code == 1

    def test_missing_required_exits_with_1(self):
        @app
        def main(name: str = field(required=True)):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1

    def test_invalid_value_exits_with_1(self):
        @app
        def main(count: int = 0):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--count", "not_a_number"])
        assert exc_info.value.code == 1

    def test_unknown_subcommand_exits_with_1(self):
        @app
        def main():
            pass

        @main.subcommand
        def sub():
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["unknown_sub"])
        assert exc_info.value.code == 1

    def test_app_error_exits_with_1(self):
        @app
        def main():
            raise yuio.app.AppError("Something went wrong")

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1

    def test_keyboard_interrupt_exits_with_130(self):
        @app
        def main():
            raise KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 130

    def test_error_exits_with_3(self):
        @app
        def main():
            raise RuntimeError()

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 3


class TestMutuallyExclusiveGroups:
    def test_mutex_group_error(self):
        group = yuio.config.MutuallyExclusiveGroup()

        @app
        def main(
            json_output: bool = field(default=False, mutex_group=group),
            xml_output: bool = field(default=False, mutex_group=group),
        ):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--json-output", "--xml-output"])
        assert exc_info.value.code == 1

    def test_mutex_group_single_allowed(self, results):
        group = yuio.config.MutuallyExclusiveGroup()

        @app
        def main(
            json_output: bool = field(default=False, mutex_group=group),
            xml_output: bool = field(default=False, mutex_group=group),
        ):
            results["json_output"] = json_output
            results["xml_output"] = xml_output

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--json-output"])
        assert exc_info.value.code == 0
        assert results["json_output"] is True
        assert results["xml_output"] is False

    def test_mutex_group_required(self):
        group = yuio.config.MutuallyExclusiveGroup(required=True)

        @app
        def main(
            json_output: bool = field(default=False, mutex_group=group),
            xml_output: bool = field(default=False, mutex_group=group),
        ):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1


class TestAppSettings:
    def test_app_prog_name(self):
        @app(prog="myapp")
        def main():
            pass

        assert main.prog == "myapp"

    def test_app_description_from_docstring(self):
        @app
        def main():
            """This is the app description."""
            pass

        assert main.description is not None
        assert "app description" in main.description

    def test_app_version(self):
        @app(version="1.0.0")
        def main():
            pass

        assert main.version == "1.0.0"

    def test_app_epilog(self):
        @app(epilog="More info at example.com")
        def main():
            pass

        assert main.epilog == "More info at example.com"


class TestSpecialParameters:
    def test_unknown_special_param_error(self):
        with pytest.raises(TypeError, match="unknown special param"):

            @app
            def main(_unknown_param: str = ""):
                pass

    def test_command_info_param_accepted(self, results):
        @app
        def main(_command_info: CommandInfo | None):
            results["info_received"] = _command_info is not None

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 0
        assert results["info_received"] is True


class TestOptionCtors:
    def test_count_option(self, results):
        @app
        def main(
            quiet: int = field(
                default=0,
                flags=["-q", "--quiet"],
                option_ctor=yuio.app.count_option(),
            ),
        ):
            results["quiet"] = quiet

        with pytest.raises(SystemExit) as exc_info:
            main.run(["-q", "-q", "-q"])
        assert exc_info.value.code == 0
        assert results["quiet"] == 3

    def test_store_true_option(self, results):
        @app
        def main(
            debug: bool = field(
                default=False,
                option_ctor=yuio.app.store_true_option(),
            ),
        ):
            results["debug"] = debug

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--debug"])
        assert exc_info.value.code == 0
        assert results["debug"] is True

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--debug=true"])
        assert exc_info.value.code == 1

    def test_store_false_option(self, results):
        @app
        def main(
            cache: bool = field(
                default=True,
                flags=["--no-cache"],
                option_ctor=yuio.app.store_false_option(),
            ),
        ):
            results["cache"] = cache

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--no-cache"])
        assert exc_info.value.code == 0
        assert results["cache"] is False

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--no-cache=true"])
        assert exc_info.value.code == 1

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--no-no-cache"])
        assert exc_info.value.code == 1

    def test_store_const_option(self, results):
        @app
        def main(
            format: str = field(
                default="text",
                flags=["--json"],
                option_ctor=yuio.app.store_const_option("json"),
            ),
        ):
            results["format"] = format

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--json"])
        assert exc_info.value.code == 0
        assert results["format"] == "json"

    def test_bool_option(self, results):
        @app
        def main(
            json_output: bool = field(
                default=False,
                option_ctor=yuio.app.bool_option(),
            ),
        ):
            results["json_output"] = json_output

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--json-output"])
        assert exc_info.value.code == 0
        assert results["json_output"] is True

    def test_bool_option_custom_neg_flags(self, results):
        @app
        def main(
            json_output: bool = field(
                default=False,
                flags=["--json"],
                option_ctor=yuio.app.bool_option(neg_flags=["--disable-json"]),
            ),
        ):
            results["json_output"] = json_output

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--disable-json"])
        assert exc_info.value.code == 0
        assert results["json_output"] is False

    def test_bool_option_auto_generated_neg_flag(self, results):
        @app
        def main(
            feature: bool | None = field(
                default=None,
                flags=["--enable-feature"],
                option_ctor=yuio.app.bool_option(),
            ),
        ):
            results["feature"] = feature

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--no-enable-feature"])
        assert exc_info.value.code == 0
        assert results["feature"] is False

    def test_bool_option_auto_generated_neg_flag_with_prefix(self, results):
        class ConnectionConfig(yuio.config.Config):
            keep_alive: bool | None = field(
                default=None,
                option_ctor=yuio.app.bool_option(),
            )

        @app
        def main(
            connection: ConnectionConfig,
        ):
            results["keep_alive"] = connection.keep_alive

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--connection-no-keep-alive"])
        assert exc_info.value.code == 0
        assert results["keep_alive"] is False

    def test_bool_option_positional_raises(self):
        with pytest.warns(
            yuio.YuioPendingDeprecationWarning,
            match="prefer using positional-only function arguments instead",
        ):

            @app
            def main(
                flag: bool = field(
                    default=False,
                    flags=yuio.POSITIONAL,
                    option_ctor=yuio.app.bool_option(),
                ),
            ):
                pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 3


class TestShortFlagCombinations:
    def test_combined_short_flags(self, results):
        @app
        def main(
            all_files: bool = field(default=False, flags=["-a"]),
            long_format: bool = field(default=False, flags=["-l"]),
            human_readable: bool = field(default=False, flags=["-H"]),
        ):
            results["all_files"] = all_files
            results["long_format"] = long_format
            results["human_readable"] = human_readable

        with pytest.raises(SystemExit) as exc_info:
            main.run(["-alH"])
        assert exc_info.value.code == 0
        assert results["all_files"] is True
        assert results["long_format"] is True
        assert results["human_readable"] is True


class TestAppDecorator:
    def test_app_decorator_no_parens(self):
        @app
        def main():
            pass

        assert isinstance(main, App)

    def test_app_decorator_with_parens(self):
        @app()
        def main():
            pass

        assert isinstance(main, App)

    def test_app_decorator_with_args(self):
        @app(prog="test", version="1.0")
        def main():
            pass

        assert isinstance(main, App)
        assert main.prog == "test"
        assert main.version == "1.0"


class TestAppWrapped:
    @pytest.mark.parametrize(
        ("sig", "args", "kwargs", "expected"),
        [
            (
                "a: int, b: int",
                (),
                {},
                pytest.raises(TypeError, match=r"missing required argument a"),
            ),
            (
                "a: int, b: int",
                (1,),
                {"a": 2, "b": 3},
                pytest.raises(TypeError, match=r"argument a was given twice"),
            ),
            ("a: int, b: int", (1, 2), {}, {"a": 1, "b": 2}),
            ("a: int, b: int", (1,), {"b": 2}, {"a": 1, "b": 2}),
            ("a: int, b: int", (), {"a": 1, "b": 2}, {"a": 1, "b": 2}),
            ("a: int = 0", (), {}, {"a": 0}),
            ("a: int = 0, /", (), {}, {"a": 0}),
            ("a: int = field(default=0)", (), {}, {"a": 0}),
            ("a: int = field(default=0), /", (), {}, {"a": 0}),
            (
                "a: int, /, b: int, *, c: int",
                (1, 2, 3),
                {},
                pytest.raises(
                    TypeError, match=r"expected at most 2 positional arguments, got 3"
                ),
            ),
            (
                "a: int, /, b: int, *, c: int",
                (1, 2),
                {"c": 3},
                {"a": 1, "b": 2, "c": 3},
            ),
            (
                "a: int, /, b: int, *, c: int",
                (1,),
                {"b": 2, "c": 3},
                {"a": 1, "b": 2, "c": 3},
            ),
            (
                "a: int, /, b: int, *, c: int",
                (),
                {"a": 1, "b": 2, "c": 3},
                pytest.raises(
                    TypeError,
                    match=r"positional-only argument a was given as keyword argument",
                ),
            ),
            ("a: int, *b: int", (1, 2, 3), {}, {"a": 1, "b": (2, 3)}),
            ("*a: int", (1, 2, 3), {}, {"a": (1, 2, 3)}),
            (
                "*a: int",
                (1, 2, 3),
                {"a": (1, 2, 3)},
                pytest.raises(
                    TypeError,
                    match=r"unexpected argument a",
                ),
            ),
        ],
    )
    def test_wrapped_callable(self, sig, args, kwargs, expected):
        ns = {}

        exec(
            textwrap.dedent(
                f"""
                ns = locals()["ns"]

                @app
                def main({sig}):
                    global ns
                    ns["results"] = locals().copy()

                ns["main"] = main
                """
            )
        )

        if isinstance(expected, pytest.RaisesExc):
            with expected:
                ns["main"].wrapped(*args, **kwargs)
        else:
            result = ns["main"].wrapped(*args, **kwargs)
            assert result is False
            assert ns["results"] == expected

    def test_wrapped_with_command_info(self, results):
        @app
        def main(_command_info: CommandInfo, name: str = field(default="default")):
            results["name"] = name
            assert _command_info.name == "__main__"
            assert _command_info.subcommand is None

        result = main.wrapped(name="test")  # type: ignore
        assert result is False  # Returns False from CommandInfo()
        assert results["name"] == "test"

    def test_wrapped_with_command_info_no_annotation(self, results):
        @app
        def main(_command_info, name: str = field(default="default")):
            results["name"] = name
            assert _command_info.name == "__main__"
            assert _command_info.subcommand is None

        result = main.wrapped(name="test")  # type: ignore
        assert result is False  # Returns False from CommandInfo()
        assert results["name"] == "test"

    def test_wrapped_with_command_info_no_override(self, results):
        @app
        def main(_command_info, name: str = field(default="default")):
            results["name"] = name
            assert _command_info.name == "__main__"
            assert _command_info.subcommand is None

        result = main.wrapped(name="test", _command_info=None)
        assert result is False  # Returns False from CommandInfo()
        assert results["name"] == "test"


class TestHelpAndVersionFlags:
    def test_help_flag_exits_with_0(self, capsys):
        @app
        def main():
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--help"])
        assert exc_info.value.code == 0

    def test_version_flag_exits_with_0(self, capsys):
        @app(version="1.0.0")
        def main():
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run(["--version"])
        assert exc_info.value.code == 0


class TestLazySubcommand:
    @pytest.fixture
    def mock_importlib(self, monkeypatch):
        modules = {}
        import_calls = []

        def mock_import_module(name):
            import_calls.append(name)
            if name in modules:
                return modules[name]
            raise ImportError(f"no module named {name!r}")

        monkeypatch.setattr("importlib.import_module", mock_import_module)

        return types.SimpleNamespace(
            modules=modules,
            import_calls=import_calls,
        )

    class TestLazyCommandImport:
        def test_command_imported_on_invocation(self, mock_importlib, results):
            mock_module = types.ModuleType("fake_module")

            @app
            def lazy_cmd():
                results["lazy_called"] = True

            setattr(mock_module, "lazy_cmd", lazy_cmd)
            mock_importlib.modules["fake_module"] = mock_module

            @app
            def main():
                results["main_called"] = True

            main.lazy_subcommand("fake_module:lazy_cmd", "lazy")

            # Just registering should not import
            assert len(mock_importlib.import_calls) == 0

            with pytest.raises(SystemExit) as exc_info:
                main.run(["lazy"])

            assert exc_info.value.code == 0
            assert mock_importlib.import_calls == ["fake_module"]
            assert results.get("main_called") is True
            assert results.get("lazy_called") is True

        def test_command_not_imported_until_needed(self, mock_importlib):
            @app
            def main():
                pass

            main.subcommand_required = False
            main.lazy_subcommand("some.module:command", "lazy", help="Pre-defined help")

            # Just registering should not import
            assert len(mock_importlib.import_calls) == 0

            # Running without the lazy subcommand should not import it
            with pytest.raises(SystemExit) as exc_info:
                main.run([])

            assert exc_info.value.code == 0
            assert mock_importlib.import_calls == []

        def test_command_not_imported_until_needed_help_generation(
            self, mock_importlib, stdout
        ):
            @app
            def main():
                pass

            main.subcommand_required = False
            main.lazy_subcommand("some.module:command", "lazy", help="Pre-defined help")

            # Just registering should not import
            assert len(mock_importlib.import_calls) == 0

            # Running without the lazy subcommand should not import it
            with pytest.raises(SystemExit) as exc_info:
                main.run(["-h"])

            assert exc_info.value.code == 0
            assert mock_importlib.import_calls == []
            assert "Pre-defined help" in stdout.getvalue()

        def test_command_not_imported_until_needed_help_generation_import(
            self, mock_importlib, stdout
        ):
            mock_module = types.ModuleType("some.module")

            @app
            def lazy_cmd():
                """Help me!"""
                assert False

            setattr(mock_module, "lazy_cmd", lazy_cmd)
            mock_importlib.modules["some.module"] = mock_module

            @app
            def main():
                pass

            main.subcommand_required = False
            main.lazy_subcommand("some.module:lazy_cmd", "lazy")

            # Just registering should not import
            assert len(mock_importlib.import_calls) == 0

            # Running without the lazy subcommand should not import it
            with pytest.raises(SystemExit) as exc_info:
                main.run(["-h"])

            assert exc_info.value.code == 0
            assert mock_importlib.import_calls == ["some.module"]
            assert "Help me!" in stdout.getvalue()

    class TestMalformedPath:
        @pytest.mark.parametrize(
            ("path", "message", "import_calls"),
            [
                # Module doesn't exist (no colon separator)
                (
                    "nonexistent.module.command",
                    "failed to import lazy subcommand nonexistent.module.command",
                    ["nonexistent.module.command", "nonexistent.module", "nonexistent"],
                ),
                # Module doesn't exist (with colon separator)
                (
                    "nonexistent.module:command",
                    "failed to import lazy subcommand nonexistent.module:command",
                    ["nonexistent.module"],
                ),
            ],
        )
        def test_malformed_path_raises_import_error(
            self, mock_importlib, path, message, import_calls, ostream
        ):
            @app
            def main():
                pass

            main.lazy_subcommand(path, "broken")

            with pytest.raises(SystemExit) as exc_info:
                main.run(["broken"])

            assert exc_info.value.code == 3
            assert message in ostream.getvalue()
            assert mock_importlib.import_calls == import_calls

        def test_nonexistent_attribute_raises_error(self, mock_importlib, ostream):
            mock_module = types.ModuleType("existing_module")
            # Module exists but has no 'nonexistent' attribute
            mock_importlib.modules["existing_module"] = mock_module

            @app
            def main():
                pass

            main.lazy_subcommand("existing_module:nonexistent", "broken")

            with pytest.raises(SystemExit) as exc_info:
                main.run(["broken"])

            assert exc_info.value.code == 3
            assert (
                "failed to import lazy subcommand existing_module:nonexistent"
                in ostream.getvalue()
            )
            assert mock_importlib.import_calls == ["existing_module"]

        def test_nested_nonexistent_attribute_raises_error(
            self, mock_importlib, ostream
        ):
            mock_module = types.ModuleType("mymodule")
            mock_class = type("MyClass", (), {})()
            setattr(mock_module, "MyClass", mock_class)
            mock_importlib.modules["mymodule"] = mock_module

            @app
            def main():
                pass

            main.lazy_subcommand("mymodule:MyClass.missing_method", "broken")

            with pytest.raises(SystemExit) as exc_info:
                main.run(["broken"])

            assert exc_info.value.code == 3
            assert (
                "failed to import lazy subcommand mymodule:MyClass.missing_method"
                in ostream.getvalue()
            )
            assert mock_importlib.import_calls == ["mymodule"]

    class TestFunctionWrappedAsApp:
        def test_plain_function_becomes_app(self, mock_importlib, results):
            mock_module = types.ModuleType("func_module")

            def plain_function():
                results["plain_called"] = True

            setattr(mock_module, "plain_function", plain_function)
            mock_importlib.modules["func_module"] = mock_module

            @app
            def main():
                pass

            main.lazy_subcommand("func_module:plain_function", "plain")

            with pytest.raises(SystemExit) as exc_info:
                main.run(["plain"])

            assert exc_info.value.code == 0
            assert results.get("plain_called") is True

        def test_app_instance_used_directly(self, mock_importlib, results):
            mock_module = types.ModuleType("app_module")

            @app
            def existing_app():
                results["app_called"] = True

            setattr(mock_module, "existing_app", existing_app)
            mock_importlib.modules["app_module"] = mock_module

            @app
            def main():
                pass

            main.lazy_subcommand("app_module:existing_app", "existing")

            with pytest.raises(SystemExit) as exc_info:
                main.run(["existing"])

            assert exc_info.value.code == 0
            assert results.get("app_called") is True
