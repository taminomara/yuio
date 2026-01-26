Utils
=====

Constants
---------

These constants are used throughout Yuio whenever :data:`None` is too ambiguous.

.. autodata:: yuio.DISABLED

.. autodata:: yuio.MISSING

.. autodata:: yuio.POSITIONAL

.. autodata:: yuio.COLLAPSE


Errors and debugging
--------------------

.. autofunction:: yuio.enable_internal_logging

.. autoclass:: yuio.PrettyException
    :members:

.. autoclass:: yuio.YuioWarning
    :members:


Magic variables
---------------

.. data:: __yuio_by_name__
    :type: bool

    Can be set on :class:`~enum.Enum` classes to control
    how :class:`parse.Enum <yuio.parse.Enum>` parses enum instances.

    When ``__yuio_by_name__`` is :data:`True`, parsers use enumerator names to parse
    values; with it's set to :data:`False`, parsers use enumerator values instead.

.. data:: __yuio_to_dash_case__
    :type: bool

    Can be set on :class:`~enum.Enum` classes to control
    how :class:`parse.Enum <yuio.parse.Enum>` parses enum instances.

    When ``__yuio_to_dash_case__`` is :data:`True`, parsers convert enumerator
    names/values to dash case before look up.

.. data:: __yuio_doc_inline__
    :type: bool

    Can be set on :class:`~enum.Enum` classes to inline their Json schemas and
    documentation.

    Useful for small enums that don't warrant a separate section in documentation.

.. data:: __yuio_short_help__
    :type: bool

    Can be set on :class:`~yuio.config.Config` classes to automatically truncate
    parsed field help to the first paragraph. This is handy when config can be loaded
    from CLI, but you don't want to show full help for every config field in CLI help
    message.


Environment variables
---------------------

.. cli:envvar:: YUIO_DEBUG

    When present, enables internal debug logging.

.. cli:envvar:: YUIO_DEBUG_FILE

    When present, enables internal debug logging and specifies file to write log to.

.. cli:envvar:: FORCE_COLOR

    When present, enables color output even if output stream is redirected or doesn't
    support colors.

.. cli:envvar:: NO_COLOR
            FORCE_NO_COLOR

    When present, disables color output.


Utility functions and types
---------------------------

.. automodule:: yuio.util
