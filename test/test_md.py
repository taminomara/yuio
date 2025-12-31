import re

import yuio.md

import pytest


class TestParser:
    @staticmethod
    def d16(s: str) -> str:
        return "".join(l[16:] + "\n" for l in s.splitlines())

    @staticmethod
    def normalize(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip())

    @pytest.fixture
    def parser(self) -> yuio.md._MdParser:
        return yuio.md._MdParser()

    @pytest.mark.parametrize(
        ("md", "expected"),
        [
            (
                """
                \tfoo\tbar
                """,
                """
                (Code '' 'foo bar')
                """,
            ),
            (
                """
                  \tfoo\tbar
                """,
                """
                (Code '' 'foo bar')
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
                    (Paragraph 'foo' 'bar')))
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
                    (Paragraph 'foo')
                    (Code '' 'bar')))
                """,
            ),
            (
                """
                >\t\tfoo
                """,
                """
                (Quote
                  (Code '' '  foo'))
                """,
            ),
            (
                """
                -\t\tfoo
                """,
                """
                (List
                  (ListItem None
                    (Code '' '  foo')))
                """,
            ),
            (
                """
                    foo
                \tbar
                """,
                """
                (Code '' 'foo' 'bar')
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
                    (Paragraph 'foo')
                    (List
                      (ListItem None
                        (Paragraph 'bar')
                        (List
                          (ListItem None
                            (Paragraph 'baz')))))))
                """,
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
                """,
            ),
            (
                """
                1. Item one.
                1. Item two.
                """,
                """
                (List
                  (ListItem 1
                    (Paragraph 'Item one.'))
                  (ListItem 2
                    (Paragraph 'Item two.')))
                """,
            ),
            (
                """
                2. Item two.
                1. Item three.
                """,
                """
                (List
                  (ListItem 2
                    (Paragraph 'Item two.'))
                  (ListItem 3
                    (Paragraph 'Item three.')))
                """,
            ),
            (
                """
                ---
                ***
                ___
                """,
                """
                (ThematicBreak)
                (ThematicBreak)
                (ThematicBreak)
                """,
            ),
            (
                """
                +++

                ===

                --

                **

                __
                """,
                """
                  (Paragraph '+++')
                  (Paragraph '===')
                  (Paragraph '--')
                  (Paragraph '**')
                  (Paragraph '__')
                """,
            ),
            (
                """
                 ***
                  ***
                   ***
                    ***
                """,
                """
                (ThematicBreak)
                (ThematicBreak)
                (ThematicBreak)
                (Code '' '***')
                """,
            ),
            (
                """
                Foo
                    ***
                """,
                """
                (Paragraph 'Foo' ' ***')
                """,
            ),
            (
                """
                _____
                - - -
                _ _ _
                """,
                """
                (ThematicBreak)
                (ThematicBreak)
                (ThematicBreak)
                """,
            ),
            (
                """
                _ _ _ _ a

                a------

                ---a---
                """,
                """
                (Paragraph '_ _ _ _ a')
                (Paragraph 'a------')
                (Paragraph '---a---')
                """,
            ),
            (
                """
                - foo
                ***
                - bar
                """,
                """
                (List
                  (ListItem None
                    (Paragraph 'foo')))
                (ThematicBreak)
                (List
                  (ListItem None
                    (Paragraph 'bar')))
                """,
            ),
            (
                """
                foo
                ***
                bar
                """,
                """
                (Paragraph 'foo')
                (ThematicBreak)
                (Paragraph 'bar')
                """,
            ),
            (
                """
                foo
                ---
                bar
                """,
                """
                (Heading 2 'foo')
                (Paragraph 'bar')
                """,
            ),
            (
                """
                - foo
                - ---
                - bar
                """,
                """
                (List
                  (ListItem None
                    (Paragraph 'foo'))
                  (ListItem None
                    (ThematicBreak))
                  (ListItem None
                    (Paragraph 'bar')))
                """,
            ),
            (
                """
                # foo
                ## foo
                ### foo
                #### foo
                ##### foo
                ###### foo
                """,
                """
                (Heading 1 'foo')
                (Heading 2 'foo')
                (Heading 3 'foo')
                (Heading 4 'foo')
                (Heading 5 'foo')
                (Heading 6 'foo')
                """,
            ),
            (
                """
                ####### foo

                #5 bolt

                #hashtag
                """,
                """
                (Paragraph '####### foo')
                (Paragraph '#5 bolt')
                (Paragraph '#hashtag')
                """,
            ),
            (
                """
                #                  foo
                """,
                """
                (Heading 1 'foo')
                """,
            ),
            (
                """
                 # foo
                  # foo
                   # foo
                    # foo
                """,
                """
                (Heading 1 'foo')
                (Heading 1 'foo')
                (Heading 1 'foo')
                (Code '' '# foo')
                """,
            ),
            (
                """
                ## foo ##
                ###   bar    ###
                # foo ##################################
                ##### foo ##
                """,
                """
                (Heading 2 'foo')
                (Heading 3 'bar')
                (Heading 1 'foo')
                (Heading 5 'foo')
                """,
            ),
            (
                """
                ### foo ### b
                """,
                """
                (Heading 3 'foo ### b')
                """,
            ),
            (
                """
                ****
                ## foo
                ****
                """,
                """
                (ThematicBreak)
                (Heading 2 'foo')
                (ThematicBreak)
                """,
            ),
            # TODO: this is where I left off:
            #       https://spec.commonmark.org/0.31.2/#example-80
        ],
    )
    def test_ast(self, parser: yuio.md._MdParser, md: str, expected: str):
        md = self.d16(md)
        assert (
            self.normalize(parser.parse(md).dump())
            == f"(Document {self.normalize(expected)})"
        )


# I'm pretty sure MD works as expected, barring some rare edge cases.
# Coverage for yuio.md is low priority rn.
