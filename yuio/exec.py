# Yuio project, MIT licence.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides helpers to run subprocesses.

It handles subprocesses stderr and stdout in a way that doesn't break
loggers from :mod:`yuio.io`.

.. autofunction:: exec

.. autofunction:: sh

"""

import logging
import pathlib
import subprocess
import threading
import typing as _t

import yuio.io


_LOGGER = logging.getLogger('yuio.io.msg.exec')


@_t.overload
def exec(
    *args: str,
    cwd: _t.Union[None, str, pathlib.Path] = None,
    env: _t.Optional[_t.Dict[str, str]] = None,
    input: _t.Optional[str] = None,
    level: int = yuio.io.INFO,
) -> str:
    pass


@_t.overload
def exec(
    *args: str,
    cwd: _t.Union[None, str, pathlib.Path] = None,
    env: _t.Optional[_t.Dict[str, str]] = None,
    input: _t.Union[None, str, bytes] = None,
    level: int = yuio.io.INFO,
    text: bool = True,
) -> _t.Union[str, bytes]:
    pass


def exec(
    *args: str,
    cwd: _t.Union[None, str, pathlib.Path] = None,
    env: _t.Optional[_t.Dict[str, str]] = None,
    input: _t.Union[None, str, bytes] = None,
    level: int = yuio.io.INFO,
    text: bool = True,
):
    """Run an executable and return its stdout.

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
    :param text:
        if true (default), decode stdout the system default encoding.
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

        def read_stderr(fh):
            while True:
                line = fh.readline()
                if not line:
                    return
                if isinstance(line, bytes):
                    line = line.decode()
                _LOGGER.log(level, line.rstrip('\n'))

        def read_stdout(fh):
            stdout.append(fh.read())

        if process.stdout:
            stdout_thread = threading.Thread(
                target=read_stdout, args=(process.stdout,))
            stdout_thread.daemon = True
            stdout_thread.start()
        if process.stderr:
            stderr_thread = threading.Thread(
                target=read_stderr, args=(process.stderr,))
            stderr_thread.daemon = True
            stderr_thread.start()

        if input is not None and process.stdin is not None:
            process.stdin.write(input)

        if process.stdout:
            stdout_thread.join()
        if process.stderr:
            stderr_thread.join()

        process.wait()

        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, args)

        if stdout:
            return stdout[0]
        elif text:
            return ''
        else:
            return b''


@_t.overload
def sh(
    cmd: str,
    shell: str = '/bin/sh',
    *,
    cwd: _t.Union[None, str, pathlib.Path] = None,
    env: _t.Optional[_t.Dict[str, str]] = None,
    input: _t.Optional[str] = None,
    level: int = yuio.io.INFO,
) -> str:
    pass


@_t.overload
def sh(
    cmd: str,
    shell: str = '/bin/sh',
    *,
    cwd: _t.Union[None, str, pathlib.Path] = None,
    env: _t.Optional[_t.Dict[str, str]] = None,
    input: _t.Union[str, bytes] = None,
    level: int = yuio.io.INFO,
    text: bool = True,
) -> _t.Union[str, bytes]:
    pass


def sh(
    cmd: str,
    shell: str = '/bin/sh',
    *,
    cwd: _t.Union[None, str, pathlib.Path] = None,
    env: _t.Optional[_t.Dict[str, str]] = None,
    input: _t.Union[str, bytes] = None,
    level: int = yuio.io.INFO,
    text: bool = True,
):
    """Run command in a shell, returns its stdout.

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
    :param text:
        if true (default), decode stdout the system default encoding.
    :return:
        string (or bytes) with command's stdout.

    """

    return exec(
        shell, '-c', cmd,
        cwd=cwd,
        env=env,
        input=input,
        level=level,
        text=text,
    )
