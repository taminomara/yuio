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

            @yuio.app.app
            def main():
                pass

            main.theme = Theme

    .. tab-item:: Setup

        .. code-block:: python

            yuio.io.setup(theme=Theme)


Configure colors
----------------

Set up accent color
~~~~~~~~~~~~~~~~~~~

The easiest way to customize default theme is to change main colors:

.. literalinclude:: themes_code/accent_colors.py
    :language: python
    :lines: 6-10

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example_themes.tape"
    Type "python -m themes_code.accent_colors"
    Enter
    Wait
    Sleep 1s


Add new color tags
~~~~~~~~~~~~~~~~~~

Any item added to :class:`Theme.colors <yuio.theme.Theme.colors>` will be available
for use as color tag:

.. literalinclude:: themes_code/tags.py
    :language: python
    :lines: 5-12
    :emphasize-lines: 3,8

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example_themes.tape"
    Type "python -m themes_code.tags"
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

.. literalinclude:: themes_code/dynamic_colors.py
    :language: python

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example_themes.tape"
    Type "python -m themes_code.dynamic_colors"
    Enter
    Sleep 6s


Configure decorations
---------------------

Message decorations
~~~~~~~~~~~~~~~~~~~

.. literalinclude:: themes_code/message_decorations.py
    :language: python
    :lines: 5-9

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m themes_code.message_decorations"
    Enter
    Sleep 6s


Progress bars and spinners
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: themes_code/progress_bars.py
    :language: python
    :lines: 6-17

.. vhs-inline::
    :scale: 40%

    Source "docs/source/_tapes/_config_by_example.tape"
    Type "python -m themes_code.progress_bars"
    Enter
    Wait
    Sleep 1s


More decorations
~~~~~~~~~~~~~~~~

See all available decorations in :ref:`decorations reference <all-decorations>`.


Choosing ASCII or Unicode
~~~~~~~~~~~~~~~~~~~~~~~~~

Not all terminals are configured to understand unicode. You can check if terminal
supports unicode output and set decorations dynamically:

.. literalinclude:: themes_code/dynamic_decorations.py
    :language: python
    :lines: 6-23
