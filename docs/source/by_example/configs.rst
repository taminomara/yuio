Configs
=======

    Working with configuration files.


.. invisible-code-block: python

    from typing import Annotated
    import yuio.app


Defining a config
-----------------

Let's create a config for our :doc:`hello world app <hello_world>`:

.. code-block:: python

    import yuio.config

    class Config(yuio.config.Config):
        #: What kind of greeting does a user want?  [1]_
        use_formal_greeting: bool = False

        #: Who the greeting is coming from?
        sender_name: str | None = None

.. code-annotations::

    1.  Yuio can parse comments above config fields or
        docstrings below them, similar to Sphinx.


Configs are similar to dataclasses, but designed specifically for being loaded
from multiple sources.


Customizing field parsing
-------------------------

We can use parsers described in the previous chapter to customize parsing
of config fields:

.. code-block:: python
    :emphasize-lines: 3

    class Config(yuio.config.Config):
        #: Number of threads to use for executing model.
        n_threads: Annotated[int, yuio.parse.Gt(0)] = 4

        ...


Loading a config
----------------

Let's load our config. We can load it from a file, from environment variables,
and from CLI arguments:

.. code-block:: python
    :emphasize-lines: 8-11

    @yuio.app.app
    def main(
        #: Configuration options [1]_
        cli_config: Config = yuio.app.field(
            flags=["--cfg"]  # [2]_
        )
    ):
        config = Config()
        config.update(Config.load_from_json_file(".greet_cfg.json"))
        config.update(Config.load_from_env(prefix="GREET"))
        config.update(cli_config)

.. code-annotations::

    1.  If you provide a documentation comment, or your config has a docstring,
        then all of its fields will be grouped together.

        See details in the :ref:`next section <argument-groups>`.
    2.  All flags from config will be prefixed with ``--cfg-...``.

        Use :func:`yuio.config.inline <yuio.app.inline>` to disable prefixing.

We simply load configs from all available sources and merge them together.

Note that :meth:`~yuio.config.Config.update` will not override fields that have
defaults, but aren't present in a particular config instance. This makes it safe
to merge configs in such a way::

    >>> class Config(yuio.config.Config):
    ...     a: str = "default a"
    ...     b: str = "default b"

    >>> config_1 = Config(a="custom a", b="custom b")

    >>> # Here, `config_1.b` is not overridden, even though it has default.
    >>> config_1.update(Config(a="custom a 2"))
    >>> config_1
    Config(a='custom a 2', b='custom b')


Complex field merging
---------------------

By default, :meth:`~yuio.config.Config.update` overrides fields from the initial config
with fields present in the new config. Sometimes you need to merge them, though.

You can provide a custom merging function to achieve this:

.. code-block:: python
    :emphasize-lines: 4

    class Config(yuio.config.Config):
        plugins: list[str] = yuio.config.field(
            default=[],
            merge=lambda left, right: left + right,
        )

.. warning::

    Merge function shouldn't mutate its arguments.
    It should produce a new value instead.

.. warning::

    Merge function will not be called for default value. It's advisable to keep the
    default value empty, and add the actual default to the initial empty config:

    .. skip: next

    .. code-block:: python

        config = Config(plugins=["markdown", "rst"])
        config.update(...)


Renaming config fields
----------------------

You can adjust names of config fields when loading configs from CLI arguments
or environment variables:

.. code-block:: python
    :emphasize-lines: 5-6,12-13

    class Config(yuio.config.Config):
        #: What kind of greeting does a user want?
        sender_name: str | None = yuio.config.field(
            default=None,
            flags=["-s", "--sender"],
            env="SENDER",
        )

        #: Whether to use formal or informal template.
        use_formal_greeting: bool = yuio.config.field(
            default=False,
            flags=["-f", "--formal"],
            env="FORMAL",
        )

You've already seen that we can prefix all environment variable names when loading
a config:

.. code-block:: python

    # `config.sender_name` will be loaded from `GREET_SENDER`.
    config = Config.load_from_env(prefix="GREET")


Skipping config fields
----------------------

Similarly, you can skip loading a field from a certain source:

.. code-block:: python
    :emphasize-lines: 5,4

    class Config(yuio.config.Config):
        use_formal_greeting: bool = yuio.config.field(
            default=False,
            flags=yuio.DISABLED,
            env=yuio.DISABLED,
        )

        ...


Nesting configs
---------------

Configs can be nested:

.. code-block:: python

    class ExecutorConfig(yuio.config.Config):
        #: Number of threads to use for executing model.
        threads: Annotated[int, yuio.parse.Ge(1)] = 4

        #: Enable or disable gpu.
        gpu: bool = True

    class AppConfig(yuio.config.Config):
        #: Executor options.
        executor: ExecutorConfig

When loading from file, nested configs are parsed from nested objects:

.. code-block:: json

    {
        "executor": {
            "threads": 16,
            "gpu": true
        }
    }

When loading from environment or CLI, names for fields of the nested config
will be prefixed by the name of its field in the parent config. In our example,
``AppConfig.executor.threads`` will be loaded from flag :flag:`--executor-threads`
and environment variable ``EXECUTOR_THREADS``.

You can change prefixes by overriding field's name in the parent config:

.. code-block:: python
    :emphasize-lines: 4-5

    class AppConfig(yuio.config.Config):
        #: Executor options.
        executor: ExecutorConfig = yuio.config.field(
            flags="--ex",
            env="EX",
        )

You can also disable prefixing by using :func:`yuio.config.inline <yuio.app.inline>`:

.. code-block:: python
    :emphasize-lines: 3

    class AppConfig(yuio.config.Config):
        #: Executor options.
        executor: ExecutorConfig = yuio.config.inline()
