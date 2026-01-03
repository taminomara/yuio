Themes
======

    Customizing Yuio's appearance.


Create and install a theme class
--------------------------------

All visual settings are configured in :class:`yuio.theme.Theme`. Create a new class
and derive if from :class:`yuio.theme.DefaultTheme`:

.. code-block:: python

    import yuio.theme

    class Theme(yuio.theme.DefaultTheme):
        ...

If you're using Yuio apps, set :attr:`App.theme <yuio.app.App.theme>`, otherwise
pass theme to :func:`yuio.io.setup`:

.. tab-set::

    .. tab-item:: App

        .. code-block:: python

            import yuio.app

            @yuio.app.app
            def main():
                ...

            main.theme = Theme

    .. tab-item:: Setup

        .. code-block:: python

            yuio.io.setup(theme=Theme)


Configure colors
----------------

Set up accent color
~~~~~~~~~~~~~~~~~~~

The easiest way to customize default theme is to change main colors:

.. literalinclude:: /../../examples/docs/themes_accent_colors.py
    :language: python
    :lines: 6-11

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Env "YUIO_THEME_PATH" "docs/source/_tapes/theme_custom.json"
    Type "python examples/docs/themes_accent_colors.py"
    Enter
    Wait
    Sleep 1s


Add new color tags
~~~~~~~~~~~~~~~~~~

Any item added to :class:`Theme.colors <yuio.theme.Theme.colors>` will be available
for use as color tag:

.. literalinclude:: /../../examples/docs/themes_tags.py
    :language: python
    :lines: 5-12
    :emphasize-lines: 3,8

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Env "YUIO_THEME_PATH" "docs/source/_tapes/theme_custom.json"
    Type "python examples/docs/themes_tags.py"
    Enter
    Sleep 6s


More color changes
~~~~~~~~~~~~~~~~~~

All other colors can be configured in the same way. See documentation
for :class:`Theme.colors <yuio.theme.Theme.colors>` to learn about structure
of Yuio's color namespaces, and see all available color paths in
:ref:`color paths reference <all-color-paths>`.


Set colors dynamically
~~~~~~~~~~~~~~~~~~~~~~

:class:`~yuio.theme.DefaultTheme` receives a :class:`~yuio.term.Term` instance
in its constructor, allowing you to set colors dynamically depending on the terminal's
color scheme:

.. literalinclude:: /../../examples/docs/themes_dynamic_colors.py
    :language: python

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Env "YUIO_THEME_PATH" "docs/source/_tapes/theme_custom.json"
    Type "python examples/docs/themes_dynamic_colors.py"
    Enter
    Sleep 6s


Configure decorations
---------------------

Message decorations
~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /../../examples/docs/themes_message_decorations.py
    :language: python
    :lines: 5-14

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/themes_message_decorations.py"
    Enter
    Sleep 6s


Progress bars and spinners
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /../../examples/docs/themes_progress_bars.py
    :language: python
    :lines: 6-17

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/docs/themes_progress_bars.py"
    Enter
    Wait
    Sleep 1s


More decorations
~~~~~~~~~~~~~~~~

See all available decorations in :ref:`decorations reference <all-decorations>`.
