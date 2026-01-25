# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
A Sphinx_ extension for documenting Yuio apps and configs.

.. _Sphinx: https://www.sphinx-doc.org/


Installation
------------

Add ``yuio.ext.sphinx`` to the list of extensions in your ``conf.py``:

.. code-block:: python

    extensions = [
        "yuio.ext.sphinx",
    ]

Yuio's extension adds new domain ``cli`` with directives and roles to declare
and cross-reference various Yuio objects.


Documented object names
-----------------------

CLI domain maintains two separate namespaces for documented objects.
One is *cfg* namespace which corresponds to names of fields in Python;
the other is *cmd* namespace which contains command names, flags and positional
argument names as they appear on the command line.

This distinction is important. Consider the following application:

.. code-block:: python

    import yuio.app
    import pathlib


    @yuio.app.app(prog="my-app")
    def main(
        quiet: bool,
        input: pathlib.Path = yuio.app.positional(),
    ): ...

In *cfg* namespace you would address `quiet` as ``main.quiet``, while in *cmd*
namespace you would address `quiet` as ``my-app --quiet``.


Declaring commands and arguments
--------------------------------

.. rst:directive:: .. cli:command:: cmd-name

    Documents a command or a subcommand. Can contain :rst:dir:`arguments <cli:argument>`
    and :rst:dir:`flags <cli:flag>`, but not other commands.

    `cmd-name` is name of the command in |cmd| namespace; it can contain spaces
    to separate command from subcommands:

    .. code-block:: rst

        .. cli:command:: app-example create
                         app-example c

            Documentation.

    If command name contains spaces or backslashes, they should be backslash-escaped:

    .. code-block:: rst

        .. cli:command:: app\\ example

    Command names can also contain quoted strings and parens; spaces within them don't
    break command names:

    .. code-block:: rst

        .. cli:command:: <app example>

            Documentation.

    Command's |cfg| name will be automatically derived by trimming leading dashes,
    replacing all dashes and whitespaces with underscores, and removing all
    non-alphanumeric symbols:

    .. code-block:: rst

        Config name for :cli:cmd:`<app example>` would be :cli:obj:`app_example`.

    |cfg| name can be overridden by using :rst:dir:`name` option.


.. rst:directive:: .. cli:argument:: <metavar>
                   .. cli:flag:: -f, --flag <metavar>

    Documents positional arguments and flags for :rst:dir:`commands <cli:command>`.

    Flags should be separated by commas and can be followed by optional metavar;
    positionals are addressed by their metavar only.

    Additional aliases can be added by using ``:flag-alias:`` field-list:

    .. code-block:: rst

        .. cli:flag:: -f, --flag <metavar>

            Documentation.

            :flag-alias --flag={true|false}:


Declaring configs and fields
----------------------------

.. rst:directive:: .. cli:config:: name

    Documents a config. Can contain :rst:dir:`fields <cli:field>` and nested configs.

    Config names usually correspond to names of their Python classes. You can add
    display name to a config to override how config entry and cross-references are
    displayed, though:

    .. code-block:: rst

        .. cli:config:: ConfigExample
            :display-name: .app_config.yaml

            Documentation.

    If your config can be loaded from CLI arguments, add :rst:dir:`parent-command`
    option to specify which command loads it; this will set up proper |cmd| namespace
    for flags within config fields:

    .. code-block:: rst

        .. cli:config:: ConfigExample
            :parent-command: app

            .. cli:field:: example

                Documentation.

                :flag --example:

    Here, Yuio will known that ``--example`` flag belongs to the command ``app``.

.. rst:directive:: .. cli:field:: name: type = default

    Documents a config field with optional type and default value. Should not contain
    nested objects.

    Like with configs, field names correspond to their respective Python names,
    and can be adjusted using :rst:dir:`display-name` option.

    If field can be loaded from CLI or environment variables, you can specify this
    by giving ``:flag:``, ``:flag-alias:``, and ``:env:`` field-lists:

    .. code-block:: rst

        .. cli:field:: example

            Documentation.

            :flag --example:
            :alias --example={true|false}:
            :env APP_EXAMPLE:


Declaring environment variables
-------------------------------

.. rst:directive:: .. cli:envvar:: name: type = value

    Documents an environment variable with optional type and default value:

    .. code-block:: rst

        .. cli:envvar:: ENV_VAR_EXAMPLE: boolean = false

            Documentation.


.. _directive-parameters:

Directive parameters
--------------------

All directives that document Yuio objects accept the standard parameters:

.. rst:directive:option:: no-index
                          no-index-entry
                          no-contents-entry
                          no-typesetting

    The `standard Sphinx options`__ available to all object descriptions.

    __ https://www.sphinx-doc.org/en/master/usage/domains/index.html#basic-markup

.. rst:directive:option:: annotation: <str>

    Adds custom annotation in front of the object.

.. rst:directive:option:: name: <cfg-path>

    For :rst:dir:`commands <cli:command>`, :rst:dir:`flags <cli:flag>`, and
    :rst:dir:`arguments <cli:argument>`, overrides automatically generated |cfg| name.

    These objects primarily referenced via |cmd| namespace, but their names in |cfg|
    namespace are used for other purposes (for example, they're used in HTML anchors).

    It is generally a good idea to keep |cfg| object names in sync with names used
    in Python code.

.. rst:directive:option:: display-name: <str>

    Overrides object name that's shown on the pace, in table of contents, and
    in cross-references.

.. rst:directive:option:: python-name: <python-path>

    Explicitly links a manually documented object with a Python object. This can help
    with linking objects in auto-generated field type signatures.

    .. note::

        This will not make an object referenceable via Python domain.

.. rst:directive:option:: parent-command: <cmd-path>

    For :rst:dir:`configs <cli:config>`, specifies |cmd| path to a command that
    loads them.

    Specifying this option will ensure that config fields with flags are correctly
    nested within the respective command.

.. rst:directive:option:: enum

    For :rst:dir:`configs <cli:config>`, changes "config" annotation to "enum"
    annotation. This can be used to document enums with :rst:dir:`cli:config`.


Referencing objects
-------------------

.. rst:role:: cli:cmd
              cli:flag
              cli:arg
              cli:opt
              cli:cli

    References objects in |cmd| namespace:

    -   :rst:role:`cli:cmd` references :rst:dir:`commands <cli:command>`,
    -   :rst:role:`cli:flag` references :rst:dir:`flags <cli:flag>`,
    -   :rst:role:`cli:arg` references :rst:dir:`arguments <cli:argument>`,
    -   :rst:role:`cli:opt` references :rst:dir:`flags <cli:flag>` and :rst:dir:`arguments <cli:argument>`,
    -   :rst:role:`cli:cli` references all of the above.

    Space and escaping rules from :rst:dir:`cli:command` apply to all |cmd| references;
    be aware that Sphinx processes escapes to separate explicit titles from references,
    so you'll have to double escape slashes:

    -   ``:cli:cmd:`app\\\\ example``` will reference command ``app example``
        (notice the double escape);

    -   ``:cli:arg:`my-app \\<input>``` will reference argument ``<input>``
        in command ``my-app``;

    -   ``:cli:arg:`my-app <input>``` will reference argument ``input`` and give
        this reference an explicit title ``my-app``. This is because role text matches
        Sphinx's syntax for explicit titles: ``:role-name:`title <reference>```.

    :example:

        .. code-block:: rst

            Reference to :cli:cmd:`app-example create`, or to :cli:flag:`app --verbose`.

.. rst:role:: cli:cfg
              cli:field
              cli:obj

    References objects in |cfg| namespace:

    -   :rst:role:`cli:cfg` references :rst:dir:`configs <cli:config>`,
    -   :rst:role:`cli:field` references :rst:dir:`fields <cli:field>`,
    -   :rst:role:`cli:obj` references any Yuio object except for environment variables.

    :example:

        .. code-block:: rst

            Reference to :cli:cfg:`ConfigExample`, or to :cli:field:`Config.sub_config.field`.

.. rst:role:: cli:env

    References environment variables.

    :example:

        .. code-block:: rst

            Reference to :cli:env:`YUIO_DEBUG`.

.. rst:role:: cli:any

    References any Yuio object. First it tries to look up object in |cmd| namespace,
    then in |cfg| namespace, and finally in namespace for environment variables.


Target specification
--------------------

Yuio extension follows the `standard Sphinx rules`__ for target specification:

-   you may supply an explicit title and reference target:
    ``:cli:app:`application <app>``` will refer to the application ``app``,
    but the link text will be "application";

-   if you prefix the content with an exclamation mark (``!``),
    no reference/hyperlink will be created.

-   if you prefix the content with ``~``, the link text will only be the last
    component of the target. For example, ``:cli:field:`~AppConfig.suppress_errors```
    will refer to ``AppConfig.suppress_errors``, but only display ``suppress_errors``
    as the link text.

__ https://www.sphinx-doc.org/en/master/usage/referencing.html#xref-modifiers


Target resolution
-----------------

Target resolution process also follows the `standard Sphinx behavior`__.

First, it tries searching an object at the top level, then within each object
in the current path.

For example, reference ``:cli:field:`AppConfig.suppress_errors``` that appears
in documentation for object ``AppConfig.verbosity`` will try the following paths,
in order:

1.  ``suppress_errors``,
#.  ``AppConfig.suppress_errors``,
#.  ``AppConfig.verbosity.suppress_errors``.

__ https://www.sphinx-doc.org/en/master/usage/domains/python.html#target-resolution

If object path begins with a dot (in case of |cmd| references, dot should be
followed by space), search order is reversed. For example,
``:cli:field:`.suppress_errors``` or ``:cli:cmd:`. ls``` will start search from the
current object.

Also, if object path begins with a dot, and no exact match is found,
the target is taken as a suffix and all object paths with that suffix are searched.
For example, ``:cli:flag:`. --help``` will search for any flag named ``--help``.


Generating documentation
------------------------

.. rst:directive:: .. cli:autoobject:: <python-path>

    This directive takes a fully qualified path to a Python object, and recursively
    generates documentation for it.

    A given object can be an :class:`~yuio.app.App` instance, a
    :class:`~yuio.config.Config`, an :class:`~enum.Enum`, or a field or enumerator
    within.

    .. rst:directive:option:: no-index
                              no-index-entry
                              no-contents-entry
                              no-typesetting
        :no-index:

        The `standard Sphinx options`__ available to all object descriptions.

        __ https://www.sphinx-doc.org/en/master/usage/domains/index.html#basic-markup

    .. rst:directive:option:: annotation: <str>
                              display-name: <str>
                              name: <cfg-path>
                              parent-command: <cmd-path>
        :no-index:

        These options work like their counterparts from
        :ref:`CLI directives <directive-parameters>`.

    .. rst:directive:option:: flags
                              flag-prefix: <str>

        If documenting a config, enables generation of flags, and adds the given
        prefix to them. Has no effect if documenting a non-config.

    .. rst:directive:option:: env
                              env-prefix: <str>

        If documenting a config, enables generation of flags, and adds the given
        prefix to them. Has no effect if documenting a non-config.

    .. rst:directive:option:: subcommands

        If documenting a command, this option will add documentation for all its
        subcommands as well.

    .. rst:directive:option:: prog: <str>

        If documenting a command or a subcommand, this option overrides program name
        of the top-most :class:`~yuio.app.App` object.

    .. rst:directive:option:: by-name
                              no-by-name
                              to-dash-case
                              no-to-dash-case

        If documenting an enum or its member, this option allows specifying
        how enumerators are parsed (see :class:`yuio.parse.Enum`).

        :data:`__yuio_by_name__` and :data:`__yuio_to_dash_case__` are respected
        as well.


Controlling content of generated help
-------------------------------------

.. rst:directive:: if-sphinx
                   if-not-sphinx

    This directive renders its content when generating documentation with Sphinx,
    but how when rendering CLI help messages. This can be useful to adjust help text
    in docstrings to better suit the environment.

    For example, we can add a link to online documentation when user runs our program
    with :flag:`--help`:

    .. code-block:: python

        import yuio.app

        @yuio.app.app
        def main():
            \"""
            A program that does a thing.

            .. if-not-sphinx::

                See full documentation at https://www.example.com  [1]_

            \"""

            ...

    .. code-annotations::

        1. This paragraph will not be visible in Sphinx.

.. rst:directive:: if-opt-doc
                   if-not-opt-doc

    This directive renders its content when it is evaluated as part of a flag/argument
    help, but not when it's part of a config help.

    This becomes handy when the same config class appears in documentation twice,
    one time as part of a command, and another time on its own.

    For example, see ``ContainerConfig`` in :ref:`autodoc example below <autodoc-example>`.
    It can be loaded from flags in the :cli:cmd:`app start` command, but it also
    appears on its own in :cli:cfg:`~config.default_container_config`.

.. rst:directive:: cut-if-not-sphinx

    This directive cuts help message short when it's rendered in CLI. This way, you can
    show a brief help in CLI, but extended help in Sphinx:

    .. code-block:: python

        import yuio.app

        @yuio.app.app
        def main():
            \"""
            A program that does a thing.

            .. cut-if-not-sphinx::

            This portion of docstring would not be visible in CLI, only in Sphinx.

            \"""

            ...

    .. note::

        If you find yourself using this directive in every docstring of a config,
        consider setting :data:`__yuio_short_help__=True <__yuio_short_help__>`
        as class attribute:

        .. code-block:: python

            import yuio.config

            class MyConfig(yuio.config.Config):
                __yuio_short_help__ = True

                socket: str | None = None
                \"""
                First paragraph will always be visible.

                All consequent paragraphs will only show up in Sphinx, not in CLI.

                \"""


.. _autodoc-example:

Autodoc example
---------------

.. tab-set::

    .. tab-item:: Output

        .. cli:autoobject:: app_example.main
            :prog: app
            :subcommands:
            :no-contents-entry:

        .. cli:autoobject:: app_example.GlobalConfig
            :name: config
            :display-name: app_config.json
            :parent-command: app
            :flags:
            :flag-prefix: --cfg
            :env:
            :env-prefix: APP
            :no-contents-entry:

    .. tab-item:: RST

        .. code-block:: rst

            .. cli:autoobject:: app_example.main
                :prog: app
                :subcommands:
                :no-contents-entry:

            .. cli:autoobject:: app_example.GlobalConfig
                :name: config
                :display-name: app_config.json
                :parent-command: app
                :flags:
                :flag-prefix: --cfg
                :env:
                :env-prefix: APP
                :no-contents-entry:

    .. tab-item:: Python

        .. literalinclude:: /_code/app_example.py
           :language: python


.. |cmd| replace:: :abbr:`cmd (Namespace with command names, flags and arguments)`
.. |cfg| replace:: :abbr:`cfg (Namespace with pythonic names for documented objects)`

"""

from __future__ import annotations

from sphinx.application import Sphinx


def setup(app: Sphinx):
    import yuio.ext.sphinx.setup

    return yuio.ext.sphinx.setup.setup(app)
