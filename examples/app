#! /usr/bin/env python

from __future__ import annotations

import datetime
import enum
import logging
import pathlib

import yuio.app
import yuio.config
import yuio.io
import yuio.parse
import yuio.ty

from typing import Annotated

_logger = logging.getLogger(__name__)


class ContainerConfig(yuio.config.Config):
    """
    Default config used with :cli:cmd:`app start`.

    """

    #: .. if-opt-doc::
    #:
    #:      Maximum CPU cores the container can use.
    #:
    #:      Default is set via :cli:field:`config.default_container_config.cpu`.
    #:
    #: .. if-not-opt-doc::
    #:
    #:      Default value for maximum CPU cores the container can use.
    cpu: yuio.ty.PosFloat = yuio.app.field(default=1.0, default_desc="")

    #: .. if-opt-doc::
    #:
    #:      Maximum memory in GB.
    #:
    #:      Default is set via :cli:field:`config.default_container_config.memory`.
    #:
    #: .. if-not-opt-doc::
    #:
    #:      Default value for maximum memory in GB.
    memory: yuio.ty.PosFloat = yuio.app.field(default=0.5, default_desc="")


class GlobalConfig(yuio.config.Config):
    """
    Global configuration for the container manager.

    Settings are loaded in this order (later overrides earlier):

    1. default values in code,
    2. configuration file (``./app_config.json``),
    3. environment variables (``APP_*``),
    4. CLI flags and arguments (``--cfg-*``).

    """

    #: Default registry URL.
    registry: str = "https://docker.io"

    #: Data directory for container storage.
    data_dir: yuio.ty.Dir = pathlib.Path("~/.containers")

    #: Default config used with :cli:cmd:`app start`.
    default_container_config: ContainerConfig = yuio.app.field(
        default=yuio.MISSING, flags=yuio.DISABLED, env="APP"
    )


class ListFormat(enum.Enum):
    """
    Format for :cli:cmd:`app list` output.

    """

    #: List containers as text.
    TEXT = "text"

    #: List containers as JSON.
    JSON = "json"


# Global config instance, will be loaded in `main`.
GLOBAL_CONFIG = GlobalConfig()


@yuio.app.app(
    version="1.0.0",  # Adds `--version`.
    bug_report=True,  # Adds `--bug-report`.
    is_dev_mode=True,  # Prints warnings from Yuio.
)
def main(
    #: Global options.
    #:
    #: These options override ones given in :file:`./app_config.json`
    #: and in environment variables. Run application with
    #: :cli:flag:`-vv <-v>` to see loaded config.
    #:
    #: .. if-sphinx::
    #:
    #:      See :cli:cfg:`config documentation <config>` for details.
    #:
    #: .. if-not-sphinx::
    #:
    #:      See `config documentation`__ for details.
    #:
    #:      __ https://yuio.readthedocs.io/en/latest/main_api/sphinx_ext.html#cli-config
    #:
    config: GlobalConfig = yuio.config.field(
        flags="--cfg", usage=yuio.COLLAPSE, help_group=yuio.COLLAPSE
    ),
):
    """
    A lightweight container manager demonstration.

    This tool showcases how to build a CLI application with the Yuio library,
    featuring configuration file loading, environment variables, and CLI flags.

    """

    config_file = pathlib.Path(__file__).parent / "app_config.json"

    GLOBAL_CONFIG.update(GlobalConfig.load_from_json_file(config_file))
    GLOBAL_CONFIG.update(GlobalConfig.load_from_env("APP"))
    GLOBAL_CONFIG.update(config)

    _logger.debug("Global config loaded: %#+r", GLOBAL_CONFIG)


main.epilog = """
.. if-not-sphinx::

    Formatting
    ----------

    Prolog is formatted using ReStructuredText. Yuio supports all RST formatting except
    tables and option lists. It also doesn't have access to all RST directives and roles,
    so only a limited subset of them is available.

    Example of what we can do:


    Quotes
    ~~~~~~

        | Beautiful python
        | Explicit and simple form
        | Winding through clouds
        |
        | -- from heroku art


    Numbered lists
    ~~~~~~~~~~~~~~

    1.  First item,
    #.  second item,

    a.  or using letters,
    #.  continues.


    Code blocks
    ~~~~~~~~~~~

    .. code-block:: python

        for i in range(10):
            print(f"Hello, {i}!")


    Admonitions
    ~~~~~~~~~~~

    .. note::

        This is an admonition.


    Definition and field lists
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    term
        Definition of the term.

    :field: Contents of the field.


    Inline markup
    ~~~~~~~~~~~~~

    -   **strong emphasis**;
    -   *emphasis*;
    -   ``code``;
    -   flag: :flag:`--flag`;
    -   python roles: :class:`~yuio.app.App`;
    -   other roles: :file:`{HOME}/.config`, click :menuselection:`&File-->New &Window`,
        then :guilabel:`&Create`;
    -   footnotes [#]_ and hyperlinks__.

    __ https://example.com
    .. [#] This is a footnote.
"""


@main.subcommand(name="list", aliases=["ls"])
def ls(
    #: Filter containers by name pattern.
    filter: Annotated[str, yuio.parse.WithMeta(desc="<regexp>")] | None = None,
    #: Output format (text, json).
    format: ListFormat = ListFormat.TEXT,
):
    """
    List running containers.

    """

    yuio.io.info("Listing containers (filter=%r, format=%r)", filter, format)


CONTAINER_CONFIG_GROUP = yuio.app.HelpGroup("Container configuration")


@main.subcommand()
def start(
    #: Base image for the container.
    image: str = yuio.config.positional(),
    #: Container name.
    name: str | None = yuio.config.field(default=None, flags=["-n", "--name"]),
    #: Override the default command.
    command: str | None = yuio.config.field(default=None, flags=["-c", "--cmd"]),
    #: Run in interactive mode.
    interactive: bool = yuio.config.field(default=False, flags=["-i", "--interactive"]),
    #: Mount points (can be used multiple times).
    mounts: dict[
        Annotated[
            pathlib.Path,
            yuio.parse.WithMeta(desc="<host-path>"),
        ],
        Annotated[
            yuio.ty.NonEmptyStr,
            yuio.parse.WithMeta(desc="<container-path>"),
        ],
    ] = yuio.config.field(
        default={},
        flags="--mount",
        option_ctor=yuio.config.collect_option(),
        help_group=CONTAINER_CONFIG_GROUP,
    ),
    #: Environment variables (can be used multiple times).
    env_vars: Annotated[
        dict[
            Annotated[
                str,
                yuio.parse.WithMeta(desc="<name>"),
            ],
            Annotated[
                str,
                yuio.parse.WithMeta(desc="<value>"),
            ],
        ],
        yuio.parse.Dict(pair_delimiter="="),
    ] = yuio.config.field(
        default={},
        flags="--env",
        option_ctor=yuio.config.collect_option(),
        help_group=CONTAINER_CONFIG_GROUP,
    ),
    #: Container configuration.
    container_config: ContainerConfig = yuio.config.inline(
        usage=yuio.COLLAPSE,
        help_group=CONTAINER_CONFIG_GROUP,
    ),
):
    """
    Start a container.

    Starts and runs a container from the given image.
    The container will run the specified command or the default entry point.

    """

    yuio.io.info(
        "Running container %s (name=%r, interactive=%r)", image, name, interactive
    )
    yuio.io.info("Command: %s", command or "(default)")

    full_container_config = ContainerConfig()
    full_container_config.update(GLOBAL_CONFIG.default_container_config)
    full_container_config.update(container_config)

    yuio.io.info("Container config: %#+r", full_container_config)
    yuio.io.info("Mounts: %#+r", mounts)
    yuio.io.info("Env vars: %#+r", env_vars)


@main.subcommand()
def stop(
    #: Container name or ID to stop.
    container_id: str = yuio.config.positional(),
    #: Timeout before force-killing.
    timeout: yuio.ty.NonNegSeconds | yuio.ty.NonNegTimeDelta = yuio.config.field(
        default=datetime.timedelta(seconds=10), flags=["-t", "--timeout"]
    ),
):
    """
    Stop a running container.

    Sends ``SIGTERM`` to the container process. If it doesn't stop within the timeout,
    ``SIGKILL`` is sent.

    """

    yuio.io.info("Stopping container %s (timeout: %r)", container_id, timeout)


if __name__ == "__main__":
    main.run()
