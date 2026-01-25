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


class TestPositionalArguments:
    def test_positional_argument(self, results):
        @app
        def main(input_file: str = positional()):
            results["input_file"] = input_file

        with pytest.raises(SystemExit) as exc_info:
            main.run(["input.txt"])
        assert exc_info.value.code == 0
        assert results["input_file"] == "input.txt"

    def test_positional_with_flag(self, results):
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
        @app
        def main(input_file: str = positional()):
            pass

        with pytest.raises(SystemExit) as exc_info:
            main.run([])
        assert exc_info.value.code == 1


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
    def test_wrapped_callable(self, results):
        @app
        def main(name: str = "default"):
            results["name"] = name

        result = main.wrapped(name="test")
        assert result is False  # Returns False from CommandInfo()
        assert results["name"] == "test"

    def test_wrapped_with_positional_args(self, results):
        @app
        def main(a: str = "", b: int = 0):
            results["a"] = a
            results["b"] = b

        result = main.wrapped("hello", 42)
        assert result is False
        assert results["a"] == "hello"
        assert results["b"] == 42

    def test_wrapped_with_fields(self, results):
        @app
        def main(name: str = field(default="default")):
            results["name"] = name

        result = main.wrapped(name="test")
        assert result is False  # Returns False from CommandInfo()
        assert results["name"] == "test"

    def test_wrapped_with_command_info(self, results):
        @app
        def main(_command_info, name: str = field(default="default")):
            results["name"] = name

        result = main.wrapped(name="test")  # type: ignore
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
