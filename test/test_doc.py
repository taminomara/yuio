import yuio.doc
import yuio.string
import yuio.term

import pytest


def serialize_formatter_output(
    ast: yuio.doc.AstBase, lines: list[yuio.string.ColorizedString]
):
    return {
        "ast": ast.dump(),
        "lines": [str(line) for line in lines],
    }


@pytest.fixture
def formatter(ctx):
    return yuio.doc.Formatter(ctx)


@pytest.fixture
def formatter_no_headings(ctx):
    return yuio.doc.Formatter(ctx, allow_headings=False)


class TestFormatterBasicText:
    def test_empty_document(self, formatter, data_regression):
        node = yuio.doc.Document(items=[])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_single_paragraph(self, formatter, data_regression):
        node = yuio.doc.Paragraph(items=["Simple text"])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_multiple_paragraphs(self, formatter, data_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Paragraph(items=["First paragraph"]),
                yuio.doc.Paragraph(items=["Second paragraph"]),
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    @pytest.mark.parametrize(
        "text_length",
        [50, 100, 200],
        ids=["short_wrap", "medium_wrap", "long_wrap"],
    )
    def test_paragraph_wrapping(self, formatter, text_length, data_regression):
        text = "A" * text_length
        node = yuio.doc.Paragraph(items=[text])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_paragraph(self, formatter, data_regression):
        node = yuio.doc.Paragraph(items=[])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterTextRegions:
    def test_text_with_emphasis(self, formatter, data_regression):
        node = yuio.doc.Paragraph(
            items=[yuio.doc.TextRegion(content="emphasized", color="em")]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_text_with_multiple_regions(self, formatter, data_regression):
        node = yuio.doc.Paragraph(
            items=[
                "normal ",
                yuio.doc.TextRegion(content="code", color="code", no_wrap=True),
                " text",
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_text_with_url_colors_supported(self, ctx, data_regression):
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(
            items=[yuio.doc.TextRegion(content="link", url="https://example.com")]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_text_with_url_no_colors(self, term, theme, data_regression):
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
            items=[yuio.doc.TextRegion(content="link", url="https://example.com")]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_text_region(self, formatter, data_regression):
        node = yuio.doc.Paragraph(items=[yuio.doc.TextRegion(content="", color="em")])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterHeadings:
    @pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6], ids=lambda x: f"level_{x}")
    def test_heading_levels(self, formatter, level, data_regression):
        node = yuio.doc.Heading(items=["Heading"], level=level)
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_heading_with_allow_headings_false(
        self, formatter_no_headings, data_regression
    ):
        node = yuio.doc.Heading(items=["Title"], level=1)
        result = formatter_no_headings.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_heading(self, formatter, data_regression):
        node = yuio.doc.Heading(items=[], level=1)
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_heading_with_inline_formatting(self, formatter, data_regression):
        node = yuio.doc.Heading(
            items=[yuio.doc.TextRegion(content="Bold Title", color="strong")], level=1
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterLists:
    def test_simple_bullet_list(self, formatter, data_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(
                    items=[yuio.doc.Paragraph(items=["Item 1"])], number=None
                )
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_simple_numbered_list(self, formatter, data_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["Item"])], number=1)
            ],
            enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER,
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_list(self, formatter, data_regression):
        node = yuio.doc.List(items=[])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_list_with_empty_items(self, formatter, data_regression):
        node = yuio.doc.List(items=[yuio.doc.ListItem(items=[], number=None)])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_nested_lists(self, formatter, data_regression):
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
        data_regression.check(serialize_formatter_output(node, result))

    def test_nested_lists_indent(self, formatter, data_regression):
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
        data_regression.check(serialize_formatter_output(node, result))

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
        self, formatter, enumerator_kind, data_regression
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
        data_regression.check(serialize_formatter_output(node, result))

    def test_list_starting_non_one(self, formatter, data_regression):
        node = yuio.doc.List(
            items=[
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["A"])], number=5),
                yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=["B"])], number=6),
            ],
            enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER,
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_multi_paragraph_list_items(self, formatter, data_regression):
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
        data_regression.check(serialize_formatter_output(node, result))

    def test_list_with_wide_markers(self, formatter, data_regression):
        items = [
            yuio.doc.ListItem(items=[yuio.doc.Paragraph(items=[f"Item {i}"])], number=i)
            for i in range(98, 102)
        ]
        node = yuio.doc.List(
            items=items, enumerator_kind=yuio.doc.ListEnumeratorKind.NUMBER
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterQuotes:
    def test_simple_quote(self, formatter, data_regression):
        node = yuio.doc.Quote(items=[yuio.doc.Paragraph(items=["Quoted text"])])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_quote(self, formatter, data_regression):
        node = yuio.doc.Quote(items=[])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_nested_quotes(self, formatter, data_regression):
        node = yuio.doc.Quote(
            items=[yuio.doc.Quote(items=[yuio.doc.Paragraph(items=["Inner quote"])])]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_quote_with_multiple_paragraphs(self, formatter, data_regression):
        node = yuio.doc.Quote(
            items=[
                yuio.doc.Paragraph(items=["P1"]),
                yuio.doc.Paragraph(items=["P2"]),
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterAdmonitions:
    @pytest.mark.parametrize(
        "admonition_type",
        ["note", "warning", "error", "tip", "caution"],
        ids=lambda x: f"type_{x}",
    )
    def test_standard_admonition_types(
        self, formatter, admonition_type, data_regression
    ):
        node = yuio.doc.Admonition(
            title=["Title"],
            items=[yuio.doc.Paragraph(items=["Content"])],
            type=admonition_type,
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_admonition_with_custom_title(self, formatter, data_regression):
        node = yuio.doc.Admonition(
            title=["Custom Title"],
            items=[yuio.doc.Paragraph(items=["Content"])],
            type="note",
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_admonition(self, formatter, data_regression):
        node = yuio.doc.Admonition(title=["Title"], items=[], type="note")
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_admonition_empty_title(self, formatter, data_regression):
        node = yuio.doc.Admonition(
            title=[], items=[yuio.doc.Paragraph(items=["Content"])], type="note"
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_admonition_multiple_paragraphs(self, formatter, data_regression):
        node = yuio.doc.Admonition(
            title=["Note"],
            items=[
                yuio.doc.Paragraph(items=["P1"]),
                yuio.doc.Paragraph(items=["P2"]),
            ],
            type="note",
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterCodeBlocks:
    def test_simple_code_block(self, formatter, data_regression):
        node = yuio.doc.Code(lines=["def foo():", "    pass"], syntax="python")
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_code_block_unknown_syntax(self, formatter, data_regression):
        node = yuio.doc.Code(lines=["code"], syntax="unknown-lang")
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_code_block(self, formatter, data_regression):
        node = yuio.doc.Code(lines=[], syntax="python")
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_code_block_with_blank_lines(self, formatter, data_regression):
        node = yuio.doc.Code(lines=["line1", "", "", "line2"], syntax="")
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_very_long_code_line(self, formatter, data_regression):
        node = yuio.doc.Code(lines=["x" * 200], syntax="")
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterFootnotes:
    def test_simple_footnote(self, formatter, data_regression):
        node = yuio.doc.Footnote(
            marker="1", items=[yuio.doc.Paragraph(items=["Note text"])]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_footnote_long_marker(self, formatter, data_regression):
        node = yuio.doc.Footnote(
            marker="[note-123]", items=[yuio.doc.Paragraph(items=["Text"])]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_footnote_container(self, formatter, data_regression):
        node = yuio.doc.FootnoteContainer(
            items=[
                yuio.doc.Footnote(marker="1", items=[yuio.doc.Paragraph(items=["A"])]),
                yuio.doc.Footnote(marker="2", items=[yuio.doc.Paragraph(items=["B"])]),
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_empty_footnote(self, formatter, data_regression):
        node = yuio.doc.Footnote(marker="1", items=[])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterOtherElements:
    def test_thematic_break(self, formatter, data_regression):
        node = yuio.doc.ThematicBreak()
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_raw_colorized_string(self, formatter, data_regression):
        node = yuio.doc.Raw(raw=yuio.string.ColorizedString("pre-formatted text"))
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_no_headings_wrapper(self, formatter, data_regression):
        node = yuio.doc.NoHeadings(items=[yuio.doc.Heading(items=["Title"], level=1)])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterIndentationAndWidth:
    def test_very_narrow_width(self, term, theme, data_regression):
        ctx = yuio.string.ReprContext(term=term, theme=theme, width=10)
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(items=["This is a long paragraph that will wrap"])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_very_wide_width(self, term, theme, data_regression):
        ctx = yuio.string.ReprContext(term=term, theme=theme, width=1000)
        formatter = yuio.doc.Formatter(ctx)
        node = yuio.doc.Paragraph(items=["This is a normal paragraph"])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_complex_nested_indentation(self, formatter, data_regression):
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
        data_regression.check(serialize_formatter_output(node, result))

    def test_long_nowrap_text(self, formatter, data_regression):
        node = yuio.doc.Paragraph(
            items=[yuio.doc.TextRegion(content="x" * 200, no_wrap=True)]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterSeparatorLogic:
    def test_first_element_in_document(self, formatter, data_regression):
        node = yuio.doc.Document(items=[yuio.doc.Heading(items=["Title"], level=1)])
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_multiple_headings_succession(self, formatter, data_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Heading(items=["First"], level=1),
                yuio.doc.Heading(items=["Second"], level=2),
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))

    def test_mixed_empty_non_empty_items(self, formatter, data_regression):
        node = yuio.doc.Document(
            items=[
                yuio.doc.Paragraph(items=[]),
                yuio.doc.Paragraph(items=["Text"]),
                yuio.doc.Paragraph(items=[]),
            ]
        )
        result = formatter.format(node)
        data_regression.check(serialize_formatter_output(node, result))


class TestFormatterIntegration:
    def test_complete_document_structure(self, formatter, data_regression):
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
        data_regression.check(serialize_formatter_output(node, result))
