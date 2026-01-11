Parsing user input
==================

    Introduction to parsers and :mod:`yuio.parse`.

Parsers control how Yuio interprets user input; they provide hints about which widgets
to use, how to do autocompletion, and so on. Every time you get data from user,
a parser is involved.

By default, Yuio constructs an appropriate parser from type hints. You can customize
this process by using :obj:`typing.Annotated`, or you can build a parser on your own.


Creating and using a parser
---------------------------

Parser classes are located in :mod:`yuio.parse`. Let's make a simple parser
for positive integers:

.. code-block:: python

    import yuio.parse

    parser = yuio.parse.Gt(yuio.parse.Int(), 0)

We can now use this parser on our own::

    >>> parser.parse("10")  # Parse text input
    10
    >>> data = 5  # Pretend this was loaded from JSON
    >>> parser.parse_config(data)  # Convert raw JSON data
    5

Or pass it to other Yuio methods:

.. code-block::

    yuio.io.ask("Choose a number", parser=parser)

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/parsers_ask.py"
    Enter
    Sleep 1s
    Type "-25"
    Sleep 250ms
    Enter
    Sleep 2s
    Backspace 3
    Sleep 250ms
    Type "15"
    Sleep 250ms
    Enter
    Sleep 4s


Creating a parser from type hints
---------------------------------

You can also build a parser from type hint, should you need one::

    >>> parser = yuio.parse.from_type_hint(dict[str, int])
    >>> parser.parse("x:10 y:-5")
    {'x': 10, 'y': -5}


Annotating type hints
---------------------

Type hints offer a concise way to build a parser. However, they're less expressive
when it comes to constraints or validation. You'll have to use
:obj:`typing.Annotated` to inject parsers that don't map directly to types:

.. code-block:: python

    from typing import Annotated

    type_hint = dict[str, Annotated[int, yuio.parse.Gt(0)]]

Here, we've created a parser for dictionaries that map strings to *positive ints*.
Technically, Yuio will derive a parser from :class:`int`, then it will apply
``yuio.parse.Gt(0)`` on top of it.


Customizing parsers for CLI arguments and config fields
-------------------------------------------------------

Now that we know how to use parsers, we can customize CLI arguments and config fields:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        .. code-block:: python
            :emphasize-lines: 8

            import yuio.app
            import yuio.parse

            @yuio.app.app
            def main(
                n_threads: int | None = yuio.app.field(
                    default=None,
                    parser=yuio.parse.Gt(yuio.parse.Int(), 0),  # [1]_
                )
            ):
                ...

        .. code-annotations::

            1.  Parser type must always match field type.

    .. tab-item:: Annotations
        :sync: annotations

        .. code-block:: python
            :emphasize-lines: 6

            import yuio.app
            import yuio.parse

            @yuio.app.app
            def main(
                n_threads: Annotated[int, yuio.parse.Gt(0)] | None = None
            ):
                ...


Enum parser
-----------

A parser that you will use quite often is :class:`yuio.parse.Enum`.
It parses string-based enumerations derived from :class:`enum.Enum`.
We encourage use of enums over plain strings because they provide
enhanced widgets and autocompletion:

.. vhs:: /_tapes/widget_choice.tape
    :alt: Demonstration of `Choice` widget.
    :scale: 40%

Enum parser has a few useful settings. It can load enumerators by name or by value,
and it also can convert enumerator names to dash case:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        .. code-block::

            class Beverage(enum.Enum):
                COFFEE = 1
                TEA = 2
                SODA = 3
                WATER = 4

            yuio.io.ask(
                "Which beverage would you like?",
                parser=yuio.parse.Enum(Beverage, by_name=True, to_dash_case=True),
            )

    .. tab-item:: Annotations
        :sync: annotations

        .. code-block::

            class Beverage(enum.Enum):
                COFFEE = 1
                TEA = 2
                SODA = 3
                WATER = 4

            yuio.io.ask[
                Annotated[
                    Beverage,
                    yuio.parse.Enum(by_name=True, to_dash_case=True),
                ]
            ]("Which beverage would you like?")


JSON parser
-----------

While Yuio supports parsing collections, it doesn't provide a fully capable
context-free parser; instead, it relies on splitting string by delimiters,
which can be limiting.

To enable parsing more complex structures, Yuio has :class:`yuio.parse.Json`.

It can be used on its own:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        ::

            >>> parser = yuio.parse.Json()
            >>> parser.parse('{"key": "value"}')
            {'key': 'value'}

    .. tab-item:: Annotations
        :sync: annotations

        ::

            >>> parser = yuio.parse.from_type_hint(yuio.parse.JsonValue)
            >>> parser.parse('{"key": "value"}')
            {'key': 'value'}

Or with a nested parser:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        ::

            >>> parser = yuio.parse.Json(yuio.parse.List(yuio.parse.Int()))
            >>> parser.parse("[1, 2, 3]")
            [1, 2, 3]

    .. tab-item:: Annotations
        :sync: annotations

        ::

            >>> parser = yuio.parse.from_type_hint(Annotated[list[int], yuio.parse.Json()])
            >>> parser.parse("[1, 2, 3]")
            [1, 2, 3]

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/parsers_json.py "
    Sleep 100ms
    Type "--data "
    Sleep 250ms
    Type "'[]'"
    Sleep 100ms
    Left 2
    Sleep 250ms
    Type "1, 2,"
    Sleep 100ms
    Type " 3"
    Right 2
    Sleep 1s
    Enter
    Sleep 6s


Validating parsers
------------------

Yuio provides :ref:`a variety <validating-parsers>` of parsers that validate
user input. If, however, you need a more complex validating procedure,
you can use :class:`yuio.parse.Apply` with a custom function that throws
:class:`yuio.parse.ParsingError` if validation fails.

For example, let's make a parser that checks if the input is even:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        .. code-block:: python
            :emphasize-lines: 8

            def assert_is_even(value: int):
                if value % 2 != 0:
                    raise yuio.parse.ParsingError(
                        "Expected an even value: `%r`", # [1]_
                        value,
                    )

            parser = yuio.parse.Apply(yuio.parse.Int(), assert_is_even)

        .. code-annotations::

            1.  t-strings are also supported here.

    .. tab-item:: Annotations
        :sync: annotations

        .. code-block:: python
            :emphasize-lines: 9

            def assert_is_even(value: int):
                if value % 2 != 0:
                    raise yuio.parse.ParsingError(
                        "Expected an even value: `%r`",  # [1]_
                        value,
                    )

            parser = yuio.parse.from_type_hint(
                Annotated[int, yuio.parse.Apply(assert_is_even)]
            )

        .. code-annotations::

            1.  t-strings are also supported here.

The parser will apply our ``assert_is_even`` to all values that it returns::

    >>> parser.parse("2")
    2
    >>> parser.parse("3")
    Traceback (most recent call last):
    ...
    yuio.parse.ParsingError: Expected an even value: 3


Mutating parsers
----------------

In addition to validation, you can mutate the input. For example:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        ::

            >>> parser = yuio.parse.Lower(yuio.parse.Str())
            >>> parser.parse("UPPER")
            'upper'

    .. tab-item:: Annotations
        :sync: annotations

        ::

            >>> parser = yuio.parse.from_type_hint(
            ...     Annotated[str, yuio.parse.Lower()]
            ... )
            >>> parser.parse("UPPER")
            'upper'

You can also use :class:`yuio.parse.Map` to implement custom mutations.

Note that parsers need to convert parsed values back to their original form
when printing them, rendering examples for documentation, or converting to JSON.
For this reason, :class:`~yuio.parse.Map` allows specifying a function
to undo the change:

.. invisible-code-block: python

    import math

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        ::

            >>> parser = yuio.parse.Map(
            ...     yuio.parse.Int(),
            ...     lambda x: 2 ** x,
            ...     lambda x: int(math.log2(x)),  # [1]_
            ... )
            >>> parser.parse("10")
            1024
            >>> parser.describe_value(1024)
            '10'

        .. code-annotations::

            1.  Reverse mapper is used when rendering documentation
                or converting values to JSON.

    .. tab-item:: Annotations
        :sync: annotations

        ::

            >>> parser = yuio.parse.from_type_hint(Annotated[
            ...     int,
            ...     yuio.parse.Map(
            ...         lambda x: 2 ** x,
            ...         lambda x: int(math.log2(x))),  # [1]_
            ... ])
            >>> parser.parse("10")
            1024
            >>> parser.describe_value(1024)
            '10'

        .. code-annotations::

            1.  Reverse mapper is used when rendering documentation
                or converting values to JSON.


Union parsers
-------------

Yuio supports parsing unions of types:

.. tab-set::
    :sync-group: parser-usage

    .. tab-item:: Parsers
        :sync: parsers

        ::

            >>> parser = yuio.parse.Union(yuio.parse.Int(), yuio.parse.Str())
            >>> parser.parse("10")
            10
            >>> parser.parse("kitten")
            'kitten'

    .. tab-item:: Annotations
        :sync: annotations

        ::

            >>> parser = yuio.parse.from_type_hint(int | str)
            >>> parser.parse("10")
            10
            >>> parser.parse("kitten")
            'kitten'

.. warning::

    Order of parsers matters. Since parsers are tried in the same order as they're
    given, make sure to put parsers that are likely to succeed at the end.

    For example, this parser will always return a string because
    :class:`~yuio.parse.Str` can't fail::

        >>> parser = yuio.parse.Union(yuio.parse.Str(), yuio.parse.Int())  # Always returns a string!
        >>> parser.parse("10")
        '10'

    To fix this, put :class:`~yuio.parse.Str` at the end so that
    :class:`~yuio.parse.Int` is tried first::

        >>> parser = yuio.parse.Union(yuio.parse.Int(), yuio.parse.Str())
        >>> parser.parse("10")
        10
        >>> parser.parse("not an int")
        'not an int'
