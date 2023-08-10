import yuio

import pytest


@pytest.mark.parametrize(
    'given,expected',
    [
        ('', ''),
        ('foo', 'foo'),
        ('Foo', 'foo'),
        ('FOO', 'foo'),
        ('FooBar', 'foo-bar'),
        ('FooBAR', 'foo-bar'),
        ('Foo10', 'foo-10'),
        ('Foo#$', 'foo-#$'),
        ('FOOBar', 'foo-bar'),
        ('FOO10', 'foo-10'),
        ('FOO#$', 'foo-#$'),
        ('10Foo', '10-foo'),
        ('10FOO', '10-foo'),
        ('#$Foo', '#$-foo'),
        ('#$FOO', '#$-foo'),
        ('HTMLToXML', 'html-to-xml'),
        ('html_to_xml', 'html-to-xml'),
        ('HTML_To_XML', 'html-to-xml'),
        ('HTTP2.0Processor', 'http-2.0-processor'),
        ('HTTP2.0PROCESSOR', 'http-2.0-processor'),
    ]
)
def test_to_dash_case(given, expected):
    assert yuio.to_dash_case(given) == expected
