import pytest

import yuio.doc
import yuio.string
import yuio.term


def serialize_formatter_output(
    ast: yuio.doc.AstBase, lines: list[yuio.string.ColorizedString]
):
    result = "\n".join(map(str, lines))
    return f"{ast.dump()}\n\n----------\n\n{result}\n"


@pytest.fixture
def formatter(ctx):
    return yuio.doc.Formatter(ctx)


@pytest.fixture
def formatter_no_headings(ctx):
    return yuio.doc.Formatter(ctx, allow_headings=False)


class TestFormatterBasicText:
    def test_empty_document(self, formatter, file_regression):
        node = yuio.doc.Document(items=[])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_single_paragraph(self, formatter, file_regression):
        node = yuio.doc.Paragraph(items=["Simple text"])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_multiple_paragraphs(self, formatter, file_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Paragraph(items=["First paragraph"]),
                yuio.doc.Paragraph(items=["Second paragraph"]),
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "text_length",
        [50, 100, 200],
        ids=["short_wrap", "medium_wrap", "long_wrap"],
    )
    def test_paragraph_wrapping(self, formatter, text_length, file_regression):
        text = "A" * text_length
        node = yuio.doc.Paragraph(items=[text])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_paragraph(self, formatter, file_regression):
        node = yuio.doc.Paragraph(items=[])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterTextRegions:
    def test_text_with_emphasis(self, formatter, file_regression):
        node = yuio.doc.Paragraph(
            items=[yuio.doc.HighlightedRegion("emphasized", color="em")]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_text_with_multiple_regions(self, formatter, file_regression):
        node = yuio.doc.Paragraph(
            items=[
                "normal ",
                yuio.doc.NoWrapRegion(yuio.doc.HighlightedRegion("code", color="code")),
                " text",
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_text_with_url_colors_supported(self, ctx, file_regression):
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(
            items=[yuio.doc.LinkRegion("link", url="https://example.com")]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_text_with_url_no_colors(self, term, theme, file_regression):
        term_no_colors = yuio.term.Term(
            term.ostream,
            term.istream,
            color_support=yuio.term.ColorSupport.NONE,
            ostream_is_tty=False,
            istream_is_tty=False,
        )
        ctx = yuio.string.ReprContext(term=term_no_colors, theme=theme, width=20)
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(
            items=[yuio.doc.LinkRegion("link", url="https://example.com")]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_text_region(self, formatter, file_regression):
        node = yuio.doc.Paragraph(items=[yuio.doc.HighlightedRegion("", color="em")])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterHeadings:
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6], ids=lambda x: f"level_{x}")
    def test_heading_levels(self, formatter, level, file_regression):
        node = yuio.doc.Heading(items=["Heading"], level=level)
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_heading_with_allow_headings_false(
        self, formatter_no_headings, file_regression
    ):
        node = yuio.doc.Heading(items=["Title"], level=1)
        result = formatter_no_headings.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_heading(self, formatter, file_regression):
        node = yuio.doc.Heading(items=[], level=1)
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_heading_with_inline_formatting(self, formatter, file_regression):
        node = yuio.doc.Heading(
            items=[yuio.doc.HighlightedRegion("Bold Title", color="strong")],
            level=1,
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterLists:
    def test_simple_bullet_list(self, formatter, file_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(
                    items=[yuio.doc.Paragraph(items=["Item 1"])], number=None
                )
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_simple_numbered_list(self, formatter, file_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["Item"])], number=1)
            ],
            enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER,
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_list(self, formatter, file_regression):
        node = yuio.doc.List(items=[])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_list_with_empty_items(self, formatter, file_regression):
        node = yuio.doc.List(items=[yuio.doc.ListItem(items=[], number=None)])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_nested_lists(self, formatter, file_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(
                    items=[
                        yuio.doc.Paragraph(items=["Outer"]),
                        yuio.doc.List(
                            items=[
                                yuio.doc.ListItem(
                                    items=[yuio.doc.Paragraph(items=["Inner"])],
                                    number=None,
                                )
                            ]
                        ),
                    ],
                    number=None,
                )
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_nested_lists_indent(self, formatter, file_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(
                    items=[
                        yuio.doc.List(
                            items=[
                                yuio.doc.ListItem(
                                    items=[yuio.doc.Paragraph(items=["First"])],
                                    number=1,
                                ),
                                yuio.doc.ListItem(
                                    items=[yuio.doc.Paragraph(items=["Second"])],
                                    number=2,
                                ),
                            ],
                            enumerator_kind=yuio.doc.ListEnumeratorKind.SMALL_LETTER,
                        ),
                    ],
                    number=1,
                )
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    @pytest.mark.parametrize(
        "enumerator_kind",
        [
            yuio.doc.ListEnumeratorKind.NUMBER,
            yuio.doc.ListEnumeratorKind.SMALL_LETTER,
            yuio.doc.ListEnumeratorKind.CAPITAL_LETTER,
            yuio.doc.ListEnumeratorKind.SMALL_ROMAN,
            yuio.doc.ListEnumeratorKind.CAPITAL_ROMAN,
        ],
        ids=[
            "number",
            "small_letter",
            "capital_letter",
            "small_roman",
            "capital_roman",
        ],
    )
    def test_different_enumerator_kinds(
        self, formatter, enumerator_kind, file_regression
    ):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["A"])], number=1),
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["B"])], number=2),
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["C"])], number=3),
            ],
            enumerator_kind=enumerator_kind,
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_list_starting_non_one(self, formatter, file_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["A"])], number=5),
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["B"])], number=6),
            ],
            enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER,
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_multi_paragraph_list_items(self, formatter, file_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(
                    items=[
                        yuio.doc.Paragraph(items=["First"]),
                        yuio.doc.Paragraph(items=["Second"]),
                    ],
                    number=1,
                ),
                yuio.doc.ListItem(
                    items=[
                        yuio.doc.Paragraph(items=["Third"]),
                    ],
                    number=2,
                ),
            ],
            enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER,
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_list_with_wide_markers(self, formatter, file_regression):
        items = [
            yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=[f"Item {i}"])], number=i)
            for i in range(98, 102)
        ]
        node = yuio.doc.List(
            items=items, enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterQuotes:
    def test_simple_quote(self, formatter, file_regression):
        node = yuio.doc.Quote(items=[yuio.doc.Paragraph(items=["Quoted text"])])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_quote(self, formatter, file_regression):
        node = yuio.doc.Quote(items=[])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_nested_quotes(self, formatter, file_regression):
        node = yuio.doc.Quote(
            items=[yuio.doc.Quote(items=[yuio.doc.Paragraph(items=["Inner quote"])])]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_quote_with_multiple_paragraphs(self, formatter, file_regression):
        node = yuio.doc.Quote(
            items=[
                yuio.doc.Paragraph(items=["P1"]),
                yuio.doc.Paragraph(items=["P2"]),
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterAdmonitions:
    @pytest.mark.parametrize(
        "admonition_type",
        ["note", "warning", "error", "tip", "caution"],
        ids=lambda x: f"type_{x}",
    )
    def test_standard_admonition_types(
        self, formatter, admonition_type, file_regression
    ):
        node = yuio.doc.Admonition(
            title=["Title"],
            items=[yuio.doc.Paragraph(items=["Content"])],
            type=admonition_type,
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_admonition_with_custom_title(self, formatter, file_regression):
        node = yuio.doc.Admonition(
            title=["Custom Title"],
            items=[yuio.doc.Paragraph(items=["Content"])],
            type="note",
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_admonition(self, formatter, file_regression):
        node = yuio.doc.Admonition(title=["Title"], items=[], type="note")
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_admonition_empty_title(self, formatter, file_regression):
        node = yuio.doc.Admonition(
            title=[], items=[yuio.doc.Paragraph(items=["Content"])], type="note"
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_admonition_multiple_paragraphs(self, formatter, file_regression):
        node = yuio.doc.Admonition(
            title=["Note"],
            items=[
                yuio.doc.Paragraph(items=["P1"]),
                yuio.doc.Paragraph(items=["P2"]),
            ],
            type="note",
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterCodeBlocks:
    def test_simple_code_block(self, formatter, file_regression):
        node = yuio.doc.Code(lines=["def foo():", "    pass"], syntax="python")
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_code_block_unknown_syntax(self, formatter, file_regression):
        node = yuio.doc.Code(lines=["code"], syntax="unknown-lang")
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_code_block(self, formatter, file_regression):
        node = yuio.doc.Code(lines=[], syntax="python")
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_code_block_with_blank_lines(self, formatter, file_regression):
        node = yuio.doc.Code(lines=["line1", "", "", "line2"], syntax="")
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_very_long_code_line(self, formatter, file_regression):
        node = yuio.doc.Code(lines=["x" * 200], syntax="")
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterFootnotes:
    def test_simple_footnote(self, formatter, file_regression):
        node = yuio.doc.Footnote(
            marker="1", items=[yuio.doc.Paragraph(items=["Note text"])]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_footnote_long_marker(self, formatter, file_regression):
        node = yuio.doc.Footnote(
            marker="[note-123]", items=[yuio.doc.Paragraph(items=["Text"])]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_footnote_container(self, formatter, file_regression):
        node = yuio.doc.FootnoteContainer(
            items=[
                yuio.doc.Footnote(marker="1", items=[yuio.doc.Paragraph(items=["A"])]),
                yuio.doc.Footnote(marker="2", items=[yuio.doc.Paragraph(items=["B"])]),
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_empty_footnote(self, formatter, file_regression):
        node = yuio.doc.Footnote(marker="1", items=[])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterOtherElements:
    def test_thematic_break(self, formatter, file_regression):
        node = yuio.doc.ThematicBreak()
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_raw_colorized_string(self, formatter, file_regression):
        node = yuio.doc.Raw(raw=yuio.string.ColorizedString("pre-formatted text"))
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_no_headings_wrapper(self, formatter, file_regression):
        node = yuio.doc.NoHeadings(items=[yuio.doc.Heading(items=["Title"], level=1)])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterIndentationAndWidth:
    def test_very_narrow_width(self, term, theme, file_regression):
        ctx = yuio.string.ReprContext(term=term, theme=theme, width=10)
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(items=["This is a long paragraph that will wrap"])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_very_wide_width(self, term, theme, file_regression):
        ctx = yuio.string.ReprContext(term=term, theme=theme, width=1000)
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(items=["This is a normal paragraph"])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_complex_nested_indentation(self, formatter, file_regression):
        node = yuio.doc.Quote(
            items=[
                yuio.doc.List(
                    items=[
                        yuio.doc.ListItem(
                            items=[
                                yuio.doc.Quote(
                                    items=[yuio.doc.Paragraph(items=["Text"])]
                                )
                            ],
                            number=None,
                        )
                    ]
                )
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_long_nowrap_text(self, formatter, file_regression):
        node = yuio.doc.Paragraph(items=[yuio.doc.NoWrapRegion("x" * 200)])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterSeparatorLogic:
    def test_first_element_in_document(self, formatter, file_regression):
        node = yuio.doc.Document(items=[yuio.doc.Heading(items=["Title"], level=1)])
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_multiple_headings_succession(self, formatter, file_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Heading(items=["First"], level=1),
                yuio.doc.Heading(items=["Second"], level=2),
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )

    def test_mixed_empty_non_empty_items(self, formatter, file_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Paragraph(items=[]),
                yuio.doc.Paragraph(items=["Text"]),
                yuio.doc.Paragraph(items=[]),
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestFormatterIntegration:
    def test_complete_document_structure(self, formatter, file_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Heading(items=["Document Title"], level=1),
                yuio.doc.Paragraph(items=["Introduction paragraph."]),
                yuio.doc.Heading(items=["Section 1"], level=2),
                yuio.doc.Paragraph(items=["Section content."]),
                yuio.doc.List(
                    items=[
                        yuio.doc.ListItem(
                            items=[yuio.doc.Paragraph(items=["Item 1"])], number=1
                        ),
                        yuio.doc.ListItem(
                            items=[yuio.doc.Paragraph(items=["Item 2"])], number=2
                        ),
                    ],
                    enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER,
                ),
                yuio.doc.Quote(items=[yuio.doc.Paragraph(items=["A quote."])]),
                yuio.doc.Admonition(
                    title=["Note"],
                    items=[yuio.doc.Paragraph(items=["Important!"])],
                    type="note",
                ),
                yuio.doc.Code(
                    lines=["def example():", "    return True"], syntax="python"
                ),
                yuio.doc.ThematicBreak(),
                yuio.doc.FootnoteContainer(
                    items=[
                        yuio.doc.Footnote(
                            marker="1", items=[yuio.doc.Paragraph(items=["Footnote 1"])]
                        )
                    ]
                ),
            ]
        )
        result = formatter.format(node)
        file_regression.check(
            serialize_formatter_output(node, result), encoding="utf-8"
        )


class TestRoles:
    """Tests for @_role decorated functions and role processing."""

    @pytest.mark.parametrize(
        ("role_name", "text"),
        [
            ("flag", "value"),
            ("code", "snippet"),
            ("literal", "text"),
            ("math", "x^2"),
            ("abbr", "ABBR (Description)"),
            ("command", "ls -la"),
            ("dfn", "term"),
            ("mailheader", "Content-Type"),
            ("makevar", "CFLAGS"),
            ("mimetype", "text/plain"),
            ("newsgroup", "comp.lang.python"),
            ("program", "python"),
            ("regexp", "[a-z]+"),
            ("cve", "CVE-2021-1234"),
            ("cwe", "CWE-89"),
            ("pep", "PEP-8"),
            ("rfc", "RFC-2616"),
            ("manpage", "ls(1)"),
            ("kbd", "Ctrl+C"),
            ("any", "module.Class"),
            ("any", "~module.Class"),
            ("any", ".Class"),
            ("any", "~.Class"),
            ("any", "custom title <module.Class>"),
            ("doc", "getting_started"),
            ("download", "file.zip"),
            ("envvar", "PATH"),
            ("keyword", "async"),
            ("numref", "fig:example"),
            ("option", "--verbose"),
            ("cmdoption", "--help"),
            ("ref", "section_name"),
            ("term", "glossary_term"),
            ("token", "if"),
            ("eq", "ref"),
            ("cli:cfg", "server.host"),
            ("cli:field", "user.name"),
            ("cli:field", "~user.name"),
            ("cli:field", ".name"),
            ("cli:field", "~.name"),
            ("cli:obj", "obj.attr"),
            ("cli:env", "HOME.path"),
            ("cli:any", "any.thing"),
            ("cli:cmd", "command subcommand"),
            ("cli:cmd", "~command sub subcommand"),
            ("cli:cmd", "~command sub\\\\ subcommand"),
            ("cli:cmd", "~command \\<sub subcommand>"),
            ("cli:cmd", "~command 1 (sub subcommand)"),
            ("cli:cmd", "~command 2 [sub subcommand]"),
            ("cli:cmd", "~command 3 {sub subcommand}"),
            ("cli:cmd", "~command 4 'sub subcommand'"),
            ("cli:cmd", "~command 5 'sub \\\\' subcommand'"),
            ("cli:cmd", ". subcommand"),
            ("cli:cmd", ".subcommand"),
            ("cli:flag", "--verbose"),
            ("cli:arg", "<filename>"),
            ("cli:arg", "cmd \\<filename>"),
            ("cli:arg", "cmd <filename>"),
            ("cli:opt", "--option=value"),
            ("cli:cli", "tool command"),
            ("guilabel", "File"),
            ("guilabel", "&File"),
            ("guilabel", "&File && More"),
            ("guilabel", "A&B&C"),
            ("menuselection", "File"),
            ("menuselection", "File --> Edit"),
            ("menuselection", "File --> Edit --> Copy"),
            ("menuselection", "&File --> &Edit"),
            ("file", "/path/to/file"),
            ("file", "/path/{variable}"),
            ("file", "/path/{var1}/mid/{var2}"),
            ("file", "/path/\\{escaped\\}"),
            ("file", "/path/{var{brace}inside}"),
            ("file", "/path/{}"),
            ("file", "{"),
            ("samp", "text"),
            ("samp", "text{var}"),
            ("samp", "{var1}{var2}"),
            ("samp", "text\\{escaped\\}"),
            ("unknown_role", "text"),
            ("my:custom:role", "text <target>"),
        ],
    )
    def test_roles(self, role_name, text, file_regression):
        result = yuio.doc._process_role(text, role_name)
        file_regression.check(
            f"Role: {role_name}\nText: {text}\nResult: {result}\n",
            encoding="utf-8",
        )
