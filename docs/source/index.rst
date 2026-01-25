Yuio
====

Yuio is everything you'll ever need to write a good CLI, deps-free.

Forget searching for *that one progressbar library*,
figuring out how to keep loading configs DRY,
or having headaches because autocompletion was just an afterthought.
Yuio got you.

.. vhs:: /_tapes/demo.tape
    :alt: Demonstration of yuio capabilities.
    :scale: 50%


.. invisible-code-block: python

    import io
    import pathlib
    import sys
    import yuio.app
    import yuio.config
    import yuio.term
    import yuio.io


Features
--------

-   Easy to setup CLI apps with autocompletion, helpful error messages,
    and lots of customization points:

    .. code-block:: python

        @yuio.app.app
        def main(
            #: Input files for the program.
            inputs: list[pathlib.Path] = yuio.app.positional(),
        ):
            ...

        if __name__ == "__main__":
            main.run()

-   Colored output with inline tags and markdown:

    .. code-block:: python

        yuio.io.info('<c bold>Yuio</c>: a user-friendly io library!')

-   Status indication with progress bars that don't break your console:

    .. invisible-code-block: python

        sources = []

    .. code-block:: python

        with yuio.io.Task('Loading sources') as task:
            for source in task.iter(sources):
                ...

    They even hide themselves when you send process to background!

-   User interactions, input parsing and simple widgets:

    .. code-block:: python

        answer = yuio.io.ask("What's your favorite treat?", default="waffles")

-   Loading configs from all sorts of places:

    .. skip: next

    .. code-block:: python

        from typing import Annotated

        class AppConfig(yuio.config.Config):
            #: Number of threads to use, default is auto-detect.
            n_threads: Annotated[int, yuio.parse.Ge(1)] | None = None

        config = AppConfig()
        config.update(AppConfig.load_from_toml_file(path))
        config.update(AppConfig.load_from_env(prefix="APP"))
        ...

-   No dependencies, perfect for use in un-configured environments.

-   And many more!


Contents
--------

.. nice-toc::

    installation
        Installation options.

    by_example/index
        A simple step-by-step guide that will walk you through Yuio's essentials.

    main_api/index
        The primary interface.

    internals/index
        For advanced use-cases.

    ext/index
        Integrations with other tools and libraries.

    cookbook/index
        Recipes for common tasks.

    api
        Full Yuio API at a glance.

.. toctree::
    :hidden:
    :caption: Links

    GitHub <https://github.com/taminomara/yuio>
    Issues <https://github.com/taminomara/yuio/issues>
    Changelog <https://github.com/taminomara/yuio/blob/main/CHANGELOG.md>


More examples
-------------

See more examples at `taminomara/yuio`_.

.. _taminomara/yuio: https://github.com/taminomara/yuio/blob/main/examples/
