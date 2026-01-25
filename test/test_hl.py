import pytest

import yuio.hl
import yuio.string
from yuio.color import Color


def serialize_colorized_string(code: str, s: yuio.string.ColorizedString):
    result = "".join(map(str, s))
    return f"{code}\n\n----------\n\n{result}\n"


@pytest.fixture(autouse=True)
def setup_hl_colors(theme):
    """Setup theme colors for syntax highlighting tests."""
    # Python highlighter colors
    theme.set_color("hl/kwd:py", Color.FORE_RED)
    theme.set_color("hl/str:py", Color.FORE_GREEN)
    theme.set_color("hl/str/prefix:py", Color.FORE_GREEN)
    theme.set_color("hl/str/esc:py", Color.FORE_BLUE)
    theme.set_color("hl/lit/num/dec:py", Color.FORE_YELLOW)
    theme.set_color("hl/lit/num/hex:py", Color.FORE_YELLOW)
    theme.set_color("hl/lit/num/oct:py", Color.FORE_YELLOW)
    theme.set_color("hl/lit/num/bin:py", Color.FORE_YELLOW)
    theme.set_color("hl/lit/builtin:py", Color.FORE_CYAN)
    theme.set_color("hl/type/builtin:py", Color.FORE_MAGENTA)
    theme.set_color("hl/type/user:py", Color.FORE_MAGENTA)
    theme.set_color("hl/punct:py", Color.FORE_WHITE)
    theme.set_color("hl/comment:py", Color.FORE_BLACK)
    theme.set_color("hl/error:py", Color.FORE_RED | Color.STYLE_BOLD)

    # Bash highlighter colors
    theme.set_color("hl/kwd:sh", Color.FORE_RED)
    theme.set_color("hl/prog:sh", Color.FORE_CYAN)
    theme.set_color("hl/str:sh", Color.FORE_GREEN)
    theme.set_color("hl/flag:sh", Color.FORE_YELLOW)
    theme.set_color("hl/punct:sh", Color.FORE_WHITE)
    theme.set_color("hl/comment:sh", Color.FORE_BLACK)

    # JSON highlighter colors
    theme.set_color("hl/lit/builtin:json", Color.FORE_CYAN)
    theme.set_color("hl/lit/num/dec:json", Color.FORE_YELLOW)
    theme.set_color("hl/str:json", Color.FORE_GREEN)
    theme.set_color("hl/str/esc:json", Color.FORE_BLUE)
    theme.set_color("hl/punct:json", Color.FORE_WHITE)

    # Diff highlighter colors
    theme.set_color("hl/meta:diff", Color.FORE_CYAN)
    theme.set_color("hl/added:diff", Color.FORE_GREEN)
    theme.set_color("hl/removed:diff", Color.FORE_RED)

    # Traceback highlighter colors
    theme.set_color("tb/heading", Color.FORE_RED)
    theme.set_color("tb/message", Color.FORE_RED)
    theme.set_color("tb/frame/usr/file", Color.FORE_WHITE)
    theme.set_color("tb/frame/usr/file/path", Color.FORE_CYAN)
    theme.set_color("tb/frame/usr/file/line", Color.FORE_YELLOW)
    theme.set_color("tb/frame/usr/file/module", Color.FORE_MAGENTA)
    theme.set_color("tb/frame/usr/code", Color.FORE_WHITE)
    theme.set_color("tb/frame/usr/highlight", Color.FORE_RED)
    theme.set_color("tb/frame/lib/file", Color.FORE_BLACK)
    theme.set_color("tb/frame/lib/file/path", Color.FORE_BLACK)
    theme.set_color("tb/frame/lib/file/line", Color.FORE_BLACK)
    theme.set_color("tb/frame/lib/file/module", Color.FORE_BLACK)
    theme.set_color("tb/frame/lib/code", Color.FORE_BLACK)
    theme.set_color("tb/frame/lib/highlight", Color.FORE_BLACK)


class TestGetHighlighter:
    def test_get_python_highlighter(self):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        assert isinstance(highlighter, yuio.hl._PyHighlighter)
        assert syntax == "py"

    def test_get_unknown_highlighter_returns_dummy(self):
        highlighter, syntax = yuio.hl.get_highlighter("unknown-language")
        assert isinstance(highlighter, yuio.hl._DummySyntaxHighlighter)
        assert syntax == "unknown-language"

    @pytest.mark.parametrize(
        ("name", "expected_syntax"),
        [
            ("py", "py"),
            ("py3", "py"),
            ("python", "py"),
            ("python3", "py"),
            ("python-3", "py"),
            ("repr", "py"),
        ],
    )
    def test_python_highlighter_variations(self, name, expected_syntax):
        highlighter, syntax = yuio.hl.get_highlighter(name)
        assert isinstance(highlighter, yuio.hl._PyHighlighter)
        assert syntax == expected_syntax

    @pytest.mark.parametrize(
        ("name", "expected_syntax"),
        [
            ("bash", "sh"),
            ("sh", "sh"),
        ],
    )
    def test_bash_highlighter_variations(self, name, expected_syntax):
        highlighter, syntax = yuio.hl.get_highlighter(name)
        assert isinstance(highlighter, yuio.hl.ReSyntaxHighlighter)
        assert syntax == expected_syntax

    @pytest.mark.parametrize(
        ("name", "expected_syntax"),
        [
            ("tb", "tb"),
            ("traceback", "tb"),
            ("python-traceback", "tb"),
        ],
    )
    def test_traceback_highlighter_variations(self, name, expected_syntax):
        highlighter, syntax = yuio.hl.get_highlighter(name)
        assert isinstance(highlighter, yuio.hl._TbHighlighter)
        assert syntax == expected_syntax

    def test_syntax_name_case_insensitive(self):
        _, s1 = yuio.hl.get_highlighter("Python")
        _, s2 = yuio.hl.get_highlighter("PYTHON")
        _, s3 = yuio.hl.get_highlighter("python")
        assert s1 == s2 == s3 == "py"

    def test_syntax_name_underscore_to_dash(self):
        _, s1 = yuio.hl.get_highlighter("python_3")
        _, s2 = yuio.hl.get_highlighter("python-3")
        assert s1 == s2 == "py"


class TestRegisterHighlighter:
    def test_register_custom_highlighter(self):
        custom = yuio.hl.ReSyntaxHighlighter([])
        yuio.hl.register_highlighter(["custom-lang"], custom)

        highlighter, syntax = yuio.hl.get_highlighter("custom-lang")
        assert highlighter is custom
        assert syntax == "custom-lang"

    def test_register_multiple_syntax_names(self):
        custom = yuio.hl.ReSyntaxHighlighter([])
        yuio.hl.register_highlighter(["custom1", "custom2", "custom3"], custom)

        h1, s1 = yuio.hl.get_highlighter("custom1")
        h2, s2 = yuio.hl.get_highlighter("custom2")
        h3, s3 = yuio.hl.get_highlighter("custom3")

        assert h1 is h2 is h3 is custom
        assert s1 == s2 == s3 == "custom1"


class TestTextHighlighter:
    def test_simple(self, theme, file_regression):
        code = "Foo bar!\nBar baz!\n"
        highlighter, syntax = yuio.hl.get_highlighter("text")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )


class TestPythonHighlighter:
    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("if True:", id="keyword_if"),
            pytest.param("def foo():", id="keyword_def"),
            pytest.param("return None", id="keyword_return_and_builtin"),
            pytest.param("import os", id="keyword_import"),
            pytest.param("class MyClass:", id="keyword_class"),
            pytest.param("async def bar():", id="keyword_async"),
            pytest.param("await func()", id="keyword_await"),
            pytest.param("for x in range(10):", id="keyword_for_and_builtin_type"),
            pytest.param("lambda x: x + 1", id="keyword_lambda"),
            pytest.param("with open() as f:", id="keyword_with_as"),
        ],
    )
    def test_keywords(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param('"hello"', id="double_quote"),
            pytest.param("'world'", id="single_quote"),
            pytest.param('"""triple"""', id="triple_double_quote"),
            pytest.param("'''triple'''", id="triple_single_quote"),
            pytest.param('r"raw"', id="raw_string"),
            pytest.param('f"format"', id="f_string"),
            pytest.param('b"bytes"', id="bytes_string"),
            pytest.param('u"unicode"', id="unicode_string"),
        ],
    )
    def test_strings(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param(r'"hello\nworld"', id="newline"),
            pytest.param(r'"tab\there"', id="tab"),
            pytest.param(r'"\x41"', id="hex_escape"),
            pytest.param(r'"\101"', id="octal_escape"),
            pytest.param(r'"\u0041"', id="unicode_4"),
            pytest.param(r'"\U00000041"', id="unicode_8"),
            pytest.param(r'"\N{LATIN CAPITAL LETTER A}"', id="unicode_name"),
            pytest.param(r'"quote\"here"', id="escaped_quote"),
            pytest.param(r'"{}"', id="format_brackets"),
            pytest.param(r'"%s"', id="percent_format"),
        ],
    )
    def test_string_escapes(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("42", id="decimal"),
            pytest.param("3.14", id="float"),
            pytest.param("-10", id="negative"),
            pytest.param("1.5e10", id="scientific"),
            pytest.param("0xFF", id="hex"),
            pytest.param("0o77", id="octal"),
            pytest.param("0b101", id="binary"),
            pytest.param(".5", id="leading_dot"),
        ],
    )
    def test_numbers(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("None", id="none"),
            pytest.param("True", id="true"),
            pytest.param("False", id="false"),
        ],
    )
    def test_builtins(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("str", id="str"),
            pytest.param("int", id="int"),
            pytest.param("float", id="float"),
            pytest.param("list", id="list"),
            pytest.param("dict", id="dict"),
            pytest.param("bool", id="bool"),
        ],
    )
    def test_builtin_types(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("MyClass", id="simple"),
            pytest.param("HTTPServer", id="with_acronym"),
            pytest.param("URLParser", id="all_caps_start"),
        ],
    )
    def test_user_types(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("# comment", id="simple"),
            pytest.param("x = 1  # inline comment", id="inline"),
        ],
    )
    def test_comments(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_complex_code(self, theme, file_regression):
        code = (
            'def foo(x: int) -> str:\n    """Docstring."""\n    return f"result: {x}"'
        )
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_doctests(self, theme, file_regression):
        code = ">>> for i in x:\n...     print(i)\n1\n2\n3\nNone\n"
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_doctests_multiple_statements(self, theme, file_regression):
        code = ">>> for i in x:\n...     print(i)\n1\n2\n3\n>>> print('hello!')\n'hello!'\n"
        highlighter, syntax = yuio.hl.get_highlighter("python")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )


class TestBashHighlighter:
    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("if [ -f file ]; then echo ok; fi", id="if_statement"),
            pytest.param("for x in *; do echo $x; done", id="for_loop"),
            pytest.param("while true; do sleep 1; done", id="while_loop"),
            pytest.param("case $x in esac", id="case_statement"),
            pytest.param("[[ -f file ]]", id="double_brackets"),
        ],
    )
    def test_keywords(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("bash")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("ls -la", id="ls_with_flags"),
            pytest.param("cat file.txt", id="cat"),
            pytest.param("grep pattern", id="grep"),
            pytest.param("echo hello", id="echo"),
        ],
    )
    def test_programs(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("bash")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param('"hello world"', id="double_quotes"),
            pytest.param("'single quotes'", id="single_quotes"),
        ],
    )
    def test_strings(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("bash")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("cat file | grep pattern", id="pipe"),
            pytest.param("cmd1 && cmd2", id="and"),
            pytest.param("cmd1 || cmd2", id="or"),
        ],
    )
    def test_operators(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("bash")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_comment(self, theme, file_regression):
        code = "# This is a comment"
        highlighter, syntax = yuio.hl.get_highlighter("bash")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )


class TestJsonHighlighter:
    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("true", id="true"),
            pytest.param("false", id="false"),
            pytest.param("null", id="null"),
        ],
    )
    def test_keywords(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("json")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("42", id="integer"),
            pytest.param("3.14", id="float"),
            pytest.param("-10", id="negative"),
            pytest.param("1.5e10", id="scientific"),
            pytest.param("0", id="zero"),
        ],
    )
    def test_numbers(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("json")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param('"hello"', id="simple"),
            pytest.param(r'"with\nnewline"', id="escape_newline"),
            pytest.param(r'"with\ttab"', id="escape_tab"),
            pytest.param(r'"with\u0041unicode"', id="escape_unicode"),
            pytest.param(r'"quote\"here"', id="escape_quote"),
            pytest.param(r'"backslash\\"', id="escape_backslash"),
        ],
    )
    def test_strings_and_escapes(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("json")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_complex_json(self, theme, file_regression):
        code = '{"key": [1, 2, 3], "nested": {"value": true}}'
        highlighter, syntax = yuio.hl.get_highlighter("json")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )


class TestDiffHighlighter:
    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("--- a/file.py", id="old_file"),
            pytest.param("+++ b/file.py", id="new_file"),
            pytest.param("@@ -1,3 +1,3 @@", id="hunk_header"),
        ],
    )
    def test_metadata(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("diff")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "code",
        [
            pytest.param("+added line", id="added"),
            pytest.param("-removed line", id="removed"),
            pytest.param(" context line", id="context"),
        ],
    )
    def test_lines(self, theme, code, file_regression):
        highlighter, syntax = yuio.hl.get_highlighter("diff")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )


class TestTracebackHighlighter:
    def test_heading(self, theme, file_regression):
        code = "Traceback (most recent call last):"
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_exception_group_heading(self, theme, file_regression):
        code = "Exception Group Traceback (most recent call last):"
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_file_line(self, theme, file_regression):
        code = 'Traceback (most recent call last):\n  File "test.py", line 10, in foo'
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_error_message(self, theme, file_regression):
        code = "ValueError: invalid value"
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(code, theme=theme, syntax=syntax)
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_full_traceback(self, theme, file_regression):
        tb = """Traceback (most recent call last):
  File "test.py", line 10, in foo
    x = 1 / 0
        ~~^~~
ZeroDivisionError: division by zero"""
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(tb, theme=theme, syntax=syntax)
        file_regression.check(serialize_colorized_string(tb, result), encoding="utf-8")

    def test_library_frames(self, theme, file_regression):
        tb = """Traceback (most recent call last):
  File "/lib/site-packages/module.py", line 10, in foo
    x = 1
ValueError: error"""
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(tb, theme=theme, syntax=syntax)
        file_regression.check(serialize_colorized_string(tb, result), encoding="utf-8")

    def test_traceback_stack(self, theme, file_regression):
        tb = """Traceback (most recent call last):
  File "test.py", line 10, in foo
    x = 1 / 0
        ~~^~~
ZeroDivisionError: division by zero

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "test2.py", line 4, in bar
    assert False
           ^^^^^
AssertionError"""
        highlighter, syntax = yuio.hl.get_highlighter("traceback")
        result = highlighter.highlight(tb, theme=theme, syntax=syntax)
        file_regression.check(serialize_colorized_string(tb, result), encoding="utf-8")


class TestReSyntaxHighlighter:
    def test_no_color(self, theme, file_regression):
        highlighter = yuio.hl.ReSyntaxHighlighter([(r"\d+", None)])
        theme.set_color("hl/number:test", Color.FORE_YELLOW)
        code = "The answer is 42"
        result = highlighter.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_basic_pattern(self, theme, file_regression):
        highlighter = yuio.hl.ReSyntaxHighlighter([(r"\d+", "number")])
        theme.set_color("hl/number:test", Color.FORE_YELLOW)
        code = "The answer is 42"
        result = highlighter.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_multiple_patterns(self, theme, file_regression):
        highlighter = yuio.hl.ReSyntaxHighlighter(
            [(r"\d+", "number"), (r"[a-z]+", "word")]
        )
        theme.set_color("hl/number:test", Color.FORE_YELLOW)
        theme.set_color("hl/word:test", Color.FORE_CYAN)
        code = "abc 123 def 456"
        result = highlighter.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_base_color(self, theme, file_regression):
        highlighter = yuio.hl.ReSyntaxHighlighter(
            [(r"\d+", "number")], base_color="base"
        )
        theme.set_color("hl/base:test", Color.FORE_RED)
        theme.set_color("hl/number:test", Color.FORE_YELLOW)
        code = "text 42 more"
        result = highlighter.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_capturing_groups(self, theme, file_regression):
        highlighter = yuio.hl.ReSyntaxHighlighter(
            [(r'(")(.*?)(")', ("quote", "content", "quote"))]
        )
        theme.set_color("hl/quote:test", Color.FORE_RED)
        theme.set_color("hl/content:test", Color.FORE_GREEN)
        code = '"hello world"'
        result = highlighter.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_overlapping_capturing_groups(self, theme, file_regression):
        highlighter = yuio.hl.ReSyntaxHighlighter(
            [(r'(")(hello (world))(")', ("quote", "content", "content2", "quote"))]
        )
        theme.set_color("hl/quote:test", Color.FORE_RED)
        theme.set_color("hl/content:test", Color.FORE_GREEN)
        theme.set_color("hl/content2:test", Color.FORE_RED)
        code = '"hello world"'
        result = highlighter.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_nested_highlighter(self, theme, file_regression):
        inner = yuio.hl.ReSyntaxHighlighter([(r"x", "x")], base_color="inner")
        outer = yuio.hl.ReSyntaxHighlighter([(r"(\[)(.*?)(\])", inner)])
        theme.set_color("hl/inner:test", Color.FORE_GREEN)
        theme.set_color("hl/x:test", Color.FORE_RED)
        code = "[x and x]"
        result = outer.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )

    def test_nested_highlighter_for_group(self, theme, file_regression):
        inner = yuio.hl.ReSyntaxHighlighter([(r"x", "x")], base_color="inner")
        outer = yuio.hl.ReSyntaxHighlighter([(r"(\[)(.*?)(\])", (None, inner, None))])
        theme.set_color("hl/inner:test", Color.FORE_GREEN)
        theme.set_color("hl/x:test", Color.FORE_RED)
        code = "[x and x]"
        result = outer.highlight(code, theme=theme, syntax="test")
        file_regression.check(
            serialize_colorized_string(code, result), encoding="utf-8"
        )
