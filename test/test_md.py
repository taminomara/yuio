import yuio.md
import yuio.term

import pytest




class TestParser:
    @staticmethod
    def d16(s: str) -> str:
        return "".join(l[16:] + "\n" for l in s.splitlines())

    @pytest.fixture
    def parser(self) -> yuio.md._MdParser:
        return yuio.md._MdParser()

    @pytest.mark.parametrize(
        "md,expected",
        [
            (
                """
                \tfoo\tbar
                """,
                """
                (Code ''
                  'foo bar')
                """,
            ),
            (
                """
                  \tfoo\tbar
                """,
                """
                (Code ''
                  'foo bar')
                """,
            ),
            (
                """
                  - foo
                \tbar
                """,
                """
                (List
                  (ListItem None
                    (Paragraph
                      'foo'
                      'bar')))
                """,
            ),
            (
                """
                  - foo

                \t\tbar
                """,
                """
                (List
                  (ListItem None
                    (Paragraph
                      'foo')
                    (Code ''
                      'bar')))
                """,
            ),
            (
                """
                >\t\tfoo
                """,
                """
                (Quote
                  (Code ''
                    '  foo'))
                """,
            ),
            (
                """
                -\t\tfoo
                """,
                """
                (List
                  (ListItem None
                    (Code ''
                      '  foo')))
                """,
            ),
            (
                """
                    foo
                \tbar
                """,
                """
                (Code ''
                  'foo'
                  'bar')
                """,
            ),
            (
                """
                - foo
                   - bar
                \t - baz
                """,
                """
                (List
                  (ListItem None
                    (Paragraph
                      'foo')
                    (List
                      (ListItem None
                        (Paragraph
                          'bar')
                        (List
                          (ListItem None
                            (Paragraph
                              'baz')))))))
                """,
            ),
            # (
            #     d16(
            #         r"""
            #         \!\#\$\%\&\'\(\)\*\+\,\-\.\/\:\;\<\=\>\?\@\[\\\]\^\_\`\{\|\}\~
            #         """
            #     ),
            #     d16(
            #         r"""
            #         (Paragraph
            #           "\\!\\#\\$\\%\\&\\'\\(\\)\\*\\+\\,\\-\\.\\/\\:\\;\\<\\=\\>\\?\\@\\[\\\\\\]\\^\\_\\`\\{\\|\\}\\~")
            #         """
            #     ),
            # ),
            # (
            #     d16(
            #         r"""
            #         \	\A\a\ \φ\«
            #         """
            #     ),
            #     d16(
            #         """
            #         (List
            #           (ListItem None
            #             (Code ''
            #               '  foo')))
            #         """
            #     ),
            # ),
            # (r"\→\A\a\ \φ\«", "(P '\\\\→\\\\A\\\\a\\\\ \\\\φ\\\\«')"),

            (
                """
                    foo
                \tbar
                """,
                """
                (Code ''
                  'foo'
                  'bar')
                """
            ),
            (

                """
                1\\. not a list
                \\* not a list
                \\# not a heading
                """,
                """
                (Paragraph
                  '1\\\\. not a list'
                  '\\\\* not a list'
                  '\\\\# not a heading')
                """
            ),
            (
                """
                1. Item one.
                1. Item two.
                """,
                """
                (List
                  (ListItem 1
                    (Paragraph
                      'Item one.'))
                  (ListItem 2
                    (Paragraph
                      'Item two.')))
                """
            ),
            (
                """
                2. Item two.
                1. Item three.
                """,
                """
                (List
                  (ListItem 2
                    (Paragraph
                      'Item two.'))
                  (ListItem 3
                    (Paragraph
                      'Item three.')))
                """
            )
        ],
    )
    def test_ast(self, parser: yuio.md._MdParser, md: str, expected: str):
        md = self.d16(md)
        expected = self.d16(expected)
        assert parser.parse(md).dump().strip() == expected.strip()
