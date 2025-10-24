Configs
=======

Adding configuration for our app.


Defining a config
-----------------

Last time we've make an app for greeting users. Let's add a config for it:

.. code-block:: python

    import yuio.config

    class Config(yuio.config.Config):
        #: what kind of greeting does a user want?
        use_formal_greeting: bool = False

        #: who the greeting is coming from?
        sender_name: str | None = None


Configs are similar to dataclasses, but designed specifically for being loaded
from multiple sources.


Customizing field parsing
-------------------------

We can use parsers described in the previous chapter to customize parsing
of config fields:

.. code-block:: python

    from typing import Annotated
    import yuio.config
    import yuio.parse

    class Config(yuio.config.Config):
        #: number of threads to use for executing model
        n_threads: Annotated[int, yuio.parse.Gt(0)] = 4

        ...


Loading a config
----------------

Let's load our config. We can load it from a file, from environment variables,
and from CLI arguments:

.. code-block:: python

    @yuio.app.app
    def main(cli_config: Config = yuio.app.field(flags=["--cfg"])):
        config = Config()
        config.update(Config.load_from_json_file(".greet_cfg.json"))
        config.update(Config.load_from_env(prefix="GREET"))
        config.update(cli_config)

We simply load configs from all available sources and merge them together.


Adding verification
-------------------

You can add additional verification method to your config. It will be called
every time a new config is loaded from a new source:

.. code-block:: python
    :emphasize-lines: 10-12

    class Config(yuio.config.Config):
        #: what kind of greeting does a user want?
        use_formal_greeting: bool = False

        #: who the greeting is coming from?
        sender_name: str | None = None

        def validate_config(self):
            if self.sender_name == "guest":
                raise yuio.parse.ParsingError(
                    f"sending greetings from {self.sender_name} is not allowed"
                )


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
            merge=lambda left, right: [*left, *right],
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
    :emphasize-lines: 4,5,10,11

    class Config(yuio.config.Config):
        #: whether to use formal or informal template
        use_formal_greeting: bool = yuio.config.field(
            default=False,
            flags=["-f", "--formal"],
            env="FORMAL",
        )

        sender_name: str | None = yuio.config.field(
            default=None,
            flags=["-s", "--sender"],
            env="SENDER",
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
        #: number of threads to use for executing model
        threads: Annotated[int, yuio.parse.Ge(1)] = 4

        #: enable or disable gpu
        gpu: bool = True

    class AppConfig(yuio.config.Config):
        #: executor options
        executor: ExecutorConfig

When loading from file, nested configs are parsed from nested objects:

.. code-block:: yaml

    executor:
        threads: 16
        gpu: true

When loading from environment or CLI, names for fields of the nested config
will be prefixed by the name of its field in the parent config. In our example,
``AppConfig.executor.threads`` will be loaded from flag ``--executor-threads``
and environment variable ``EXECUTOR_THREADS``.

You can change the prefixes by overriding field's name in the parent config:

.. code-block:: python

    class AppConfig(yuio.config.Config):
        #: executor options
        executor: ExecutorConfig = yuio.config.field(
            flags="--ex",
            env="EX",
        )

You can also disable prefixing by using :func:`yuio.config.inline <yuio.app.inline>`:

.. code-block:: python

    class AppConfig(yuio.config.Config):
        #: executor options
        executor: ExecutorConfig = yuio.config.inline()
