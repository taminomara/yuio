# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides helpers to run subprocesses and get their output.

It handles subprocesses stderr and stdout in a way that doesn't break
loggers from :mod:`yuio.io`.

.. autofunction:: exec

.. autofunction:: sh

.. autoclass:: ExecError

"""

from __future__ import annotations

import logging
import pathlib
import subprocess
import threading

from yuio import _typing as _t

__all__ = [
    "ExecError",
    "exec",
    "sh",
]

_LOGGER = logging.getLogger("yuio.exec")


class ExecError(subprocess.CalledProcessError):
    """
    Raised when executed command returns a non-zero status.

    """

    def __str__(self):
        res = super().__str__()
        if stderr := getattr(self, "stderr"):
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            res += "\n\nStderr:\n" + stderr
        return res


@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: str | None = None,
    level: int = logging.DEBUG,
    text: _t.Literal[True] = True,
) -> str: ...


@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: bytes | None = None,
    level: int = logging.DEBUG,
    text: _t.Literal[False],
) -> bytes: ...


@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: str | bytes | None = None,
    level: int = logging.DEBUG,
    text: bool,
) -> str | bytes: ...


def exec(
    *args: str | pathlib.Path,
    cwd: None | str | pathlib.Path = None,
    env: dict[str, str] | None = None,
    input: None | str | bytes = None,
    level: int = logging.DEBUG,
    text: bool = True,
):
    """
    Run an executable and return its stdout.

    Command's stderr is interactively printed to the log.

    If the command fails, a :class:`~subprocess.CalledProcessError` is raised.

    :param args:
        command arguments.
    :param cwd:
        set the current directory before the command is executed.
    :param env:
        define the environment variables for the command.
    :param input:
        string with command's stdin.
    :param level:
        logging level for stderr outputs.
        By default, it is set to :data:`logging.DEBUG`, which hides all the output.
    :param text:
        if :data:`True` (default), decode stdout using the system default encoding.
    :return:
        string (or bytes) with command's stdout.

    """

    if cwd is not None:
        if not isinstance(cwd, pathlib.Path):
            cwd = pathlib.Path(cwd)
        cwd = cwd.expanduser().resolve()

    with subprocess.Popen(
        args,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        stdin=None if input is None else subprocess.PIPE,
    ) as process:
        stdout = []
        stderr = []

        if _LOGGER.isEnabledFor(level):
            _LOGGER.log(level, " ".join(map(str, args)))

        def read_stderr(fh):
            while True:
                line = fh.readline()
                if not line:
                    return
                if isinstance(line, bytes):
                    line = line.decode(errors="replace")
                stderr.append(line)
                _LOGGER.log(level, line.rstrip("\n"))

        def read_stdout(fh):
            stdout.append(fh.read())

        assert process.stdout
        stdout_thread = threading.Thread(
            target=read_stdout,
            args=(process.stdout,),
            name=f"yuio stdout handler for sub-process",
        )
        stdout_thread.daemon = True
        stdout_thread.start()

        assert process.stderr
        stderr_thread = threading.Thread(
            target=read_stderr,
            args=(process.stderr,),
            name=f"yuio stderr handler for sub-process",
        )
        stderr_thread.daemon = True
        stderr_thread.start()

        if input is not None:
            assert process.stdin is not None
            process.stdin.write(input)
            process.stdin.flush()
            process.stdin.close()

        stdout_thread.join()
        stderr_thread.join()

        process.wait()

        if process.returncode != 0:
            raise ExecError(
                process.returncode, args, output="".join(stdout), stderr="".join(stderr)
            )

        return stdout[0]


@_t.overload
def sh(
    cmd: str,
    /,
    *,
    shell: str = "/bin/sh",
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: str | None = None,
    level: int = logging.DEBUG,
    text: _t.Literal[True] = True,
) -> str: ...


@_t.overload
def sh(
    cmd: str,
    /,
    *,
    shell: str = "/bin/sh",
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: bytes | None = None,
    level: int = logging.DEBUG,
    text: _t.Literal[False],
) -> bytes: ...


@_t.overload
def sh(
    cmd: str,
    /,
    *,
    shell: str = "/bin/sh",
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: bytes | None = None,
    level: int = logging.DEBUG,
    text: bool,
) -> str | bytes: ...


def sh(
    cmd: str,
    /,
    *,
    shell: str = "/bin/sh",
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: str | bytes | None = None,
    level: int = logging.DEBUG,
    text: bool = True,
):
    """
    Run command in a shell, return its stdout.

    :param cmd:
        shell command.
    :param shell:
        which shell to use. Default is ``/bin/sh``.
    :param cwd:
        set the current directory before the command is executed.
    :param env:
        define the environment variables for the command.
    :param input:
        string with command's stdin.
    :param level:
        logging level for stderr outputs.
        By default, it is set to :data:`logging.DEBUG`, which hides all the output.
    :param text:
        if :data:`True` (default), decode stdout using the system default encoding.
    :return:
        string (or bytes) with command's stdout.

    """

    return exec(
        shell,
        "-c",
        cmd,
        cwd=cwd,
        env=env,
        input=input,
        level=level,
        text=text,
    )
