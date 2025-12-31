from __future__ import annotations

import enum

import yuio.config
import yuio.parse

from typing import Annotated


class LogLevel(enum.Enum):
    """
    Available parameters for :attr:`~AppConfig.log_level`.

    """

    ERROR = 3
    """
    Prints messages with severity of *error* and above.

    """

    WARNING = 2
    """
    Prints messages with severity of *warning* and above.

    """

    INFO = 1
    """
    Prints messages with severity of *info* and above.

    """

    DEBUG = 0
    """
    Prints messages with severity of *debug* and above.

    """


class AppConfig(yuio.config.Config):
    """
    Main application config.

    """

    log_level: Annotated[LogLevel, yuio.parse.Enum(by_name=True, to_dash_case=True)] = (
        LogLevel.INFO
    )
    """
    Level used for logging.

    """

    strict: bool = False
    """
    Use strict evaluation metrics.

    """

    executor: ExecutorConfig
    """
    Configuration related to executing the algorithm.

    """


class ExecutorConfig(yuio.config.Config):
    """
    Configuration related to executing the algorithm.

    """

    threads: Annotated[int, yuio.parse.Ge(1)] = 4
    """
    Number of threads to use for executing the algorithm.

    """

    gpu: bool = True
    """
    Enable or disable GPU acceleration.

    """
