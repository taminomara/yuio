# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
This module provides helpers to run subprocesses and get their output.

It handles subprocess' stderr and stdout in a way that doesn't break
loggers from :mod:`yuio.io`.

.. autofunction:: exec

.. autoclass:: ExecError

"""

from __future__ import annotations

import contextlib
import logging
import os
import pathlib
import select
import selectors
import subprocess
import threading

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "ExecError",
    "exec",
]

_logger = logging.getLogger(__name__)


class ExecError(subprocess.CalledProcessError):
    """
    Raised when executed command returns a non-zero status.

    .. py:data:: returncode
        :type: int

        Return code of the called command.

    .. py:data:: cmd
        :type: tuple[str | pathlib.Path, ...]

        Initial `args` passed to the :func:`exec`.

    .. py:data:: output
                 stdout
        :type: str | bytes | None

        Captured stdout.

    .. py:data:: stderr
        :type: str | bytes | None

        Captured stderr.

    """

    def __str__(self):
        res = super().__str__()
        if stderr := getattr(self, "stderr", None):
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
    capture_io: _t.Literal[True] = True,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any] | str | None = None,
    level: int = logging.DEBUG,
    text: _t.Literal[True] = True,
) -> str: ...
@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: bytes | None = None,
    capture_io: _t.Literal[True] = True,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any] | str | None = None,
    level: int = logging.DEBUG,
    text: _t.Literal[False],
) -> bytes: ...
@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: str | None = None,
    capture_io: _t.Literal[False],
    text: _t.Literal[True] = True,
) -> None: ...
@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: str | pathlib.Path | None = None,
    env: dict[str, str] | None = None,
    input: bytes | None = None,
    capture_io: _t.Literal[False],
    text: _t.Literal[False],
) -> None: ...
@_t.overload
def exec(
    *args: str | pathlib.Path,
    cwd: None | str | pathlib.Path = None,
    env: dict[str, str] | None = None,
    capture_io: bool = True,
    input: None | str | bytes = None,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any] | str | None = None,
    level: int | None = None,
    text: bool = False,
) -> str | bytes | None: ...
def exec(
    *args: str | pathlib.Path,
    cwd: None | str | pathlib.Path = None,
    env: dict[str, str] | None = None,
    capture_io: bool = True,
    input: None | str | bytes = None,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any] | str | None = None,
    level: int | None = None,
    text: bool = True,
) -> str | bytes | None:
    """
    Run an executable and return its stdout.

    Command's stderr is interactively printed to the log.

    :param args:
        command arguments.
    :param cwd:
        set the current directory before the command is executed.
    :param env:
        define the environment variables for the command.
    :param input:
        string with command's stdin. If `text` is set to :data:`False`, this should
        be :class:`bytes`, otherwise it should be a :class:`str`.
    :param capture_io:
        if set to :data:`False`, process' stdout and stderr are not captured;
        `logger` and `level` arguments can't be given in this case, and this
        function returns :data:`None` instead of process' output.
    :param logger:
        logger that will be used for logging command's output. Default is to log
        to ``yuio.exec``.
    :param level:
        logging level for stderr outputs. Default is :data:`logging.DEBUG`.
    :param text:
        if set to :data:`False`, stdout is returned as :class:`bytes`.
    :returns:
        string (or bytes) with command's stdout, or :data:`None` if `capture_io`
        is :data:`False`.
    :raises:
        If the command fails, a :class:`~subprocess.CalledProcessError` is raised.
        If command can't be started, raises :class:`OSError`.

    """

    if not capture_io:
        for name, param in [
            ("logger", logger),
            ("level", level),
        ]:
            if param is not None:
                raise ValueError(f"{name} can't be specified when capture_io is False")

    level = level if level is not None else logging.DEBUG

    if logger is None:
        logger = _logger
    elif isinstance(logger, str):
        logger = logging.getLogger(logger)

    logger.log(level, " ".join(map(str, args)))

    with contextlib.ExitStack() as s:
        if not capture_io:
            import yuio.io

            s.enter_context(yuio.io.SuspendOutput())

        process = s.enter_context(
            subprocess.Popen(
                args,
                cwd=cwd,
                env=env,
                stdout=subprocess.PIPE if capture_io else None,
                stderr=subprocess.PIPE if capture_io else None,
                text=text,
                stdin=(
                    (subprocess.DEVNULL if input is None else subprocess.PIPE)
                    if capture_io
                    else None
                ),
            )
        )

        stdout, stderr = _process_io(process, capture_io, input, logger, level)

        process.wait()

        if not capture_io:
            stdout_str = None
        elif text:
            stdout_str = "".join(_t.cast(list[str], stdout))
        else:
            stdout_str = b"".join(_t.cast(list[bytes], stdout))

        if process.returncode != 0:
            if not capture_io:
                stderr_str = None
            elif text:
                stderr_str = "".join(_t.cast(list[str], stderr))
            else:
                stderr_str = b"".join(_t.cast(list[bytes], stderr))

            raise ExecError(
                process.returncode, args, output=stdout_str, stderr=stderr_str
            )

        return stdout_str


def _process_io(
    process: subprocess.Popen[_t.Any],
    capture_io: bool,
    input: str | bytes | None,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any],
    level: int,
):
    if not capture_io:
        return _process_io_nocap(process, input, logger, level)
    elif os.name == "nt":
        return _process_io_threads(process, input, logger, level)
    else:
        return _process_io_selectors(process, input, logger, level)


def _process_io_threads(
    process: subprocess.Popen[_t.Any],
    input: str | bytes | None,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any],
    level: int,
):
    stdout = []
    stderr = []

    def read_stderr(fh: _t.IO[_t.Any]):
        last_line = ""
        while True:
            text = fh.read()
            if not text:
                fh.close()
                return
            stderr.append(text)
            if isinstance(text, bytes):
                text = text.decode(errors="replace")
            for line in text.splitlines(keepends=True):
                if not line.endswith("\n"):
                    last_line += line
                else:
                    logger.log(level, "-> %s", last_line + line.rstrip("\r\n"))
                    last_line = ""

    def read_stdout(fh: _t.IO[_t.Any]):
        while True:
            text = fh.read()
            if not text:
                fh.close()
                return
            stdout.append(text)

    assert process.stdout
    stdout_thread = threading.Thread(
        target=read_stdout,
        args=(process.stdout,),
        name="yuio stdout handler for sub-process",
    )
    stdout_thread.daemon = True
    stdout_thread.start()

    assert process.stderr
    stderr_thread = threading.Thread(
        target=read_stderr,
        args=(process.stderr,),
        name="yuio stderr handler for sub-process",
    )
    stderr_thread.daemon = True
    stderr_thread.start()

    if input is not None:
        assert process.stdin is not None
        try:
            process.stdin.write(input)
            process.stdin.flush()
        except BrokenPipeError:
            pass
        process.stdin.close()

    stdout_thread.join()
    stderr_thread.join()

    return stdout, stderr


# From subprocess implementation: "poll/select have the advantage of not requiring
# any extra file descriptor, contrarily to epoll/kqueue (also, they require a single
# syscall)."
if hasattr(selectors, "PollSelector"):
    _Selector = selectors.PollSelector
else:
    _Selector = selectors.SelectSelector


def _process_io_selectors(
    process: subprocess.Popen[_t.Any],
    input: str | bytes | None,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any],
    level: int,
):
    assert process.stdout
    assert process.stderr
    if input is not None:
        assert process.stdin
        if process.text_mode:  # type: ignore
            input = input.encode(process.stdin.encoding, process.stdin.errors)  # type: ignore
        input_data = memoryview(input)  # type: ignore
    else:
        input_data = None

    stdout: list[bytes] = []
    stderr: list[bytes] = []

    last_line = ""

    def read_stderr(selector: selectors.BaseSelector, fd: int, fh: _t.IO[_t.Any]):
        nonlocal last_line
        text = os.read(fd, 32 * 1024)
        if not text:
            selector.unregister(fd)
            fh.close()
            return
        stderr.append(text)
        if isinstance(text, bytes):
            text = text.decode(errors="replace")
        for line in text.splitlines(keepends=True):
            if not line.endswith("\n"):
                last_line += line
            else:
                logger.log(level, "-> %s", last_line + line.rstrip("\r\n"))
                last_line = ""

    def read_stdout(selector: selectors.BaseSelector, fd: int, fh: _t.IO[_t.Any]):
        text = os.read(fd, 32 * 1024)
        if not text:
            selector.unregister(fd)
            fh.close()
            return
        stdout.append(text)

    index = 0

    def write_stdin(selector: selectors.BaseSelector, fd: int, fh: _t.IO[_t.Any]):
        nonlocal index
        assert input_data is not None
        try:
            index += os.write(fd, input_data[index : index + select.PIPE_BUF])
        except BrokenPipeError:
            selector.unregister(fd)
            fh.close()
            return
        if index >= len(input_data):
            selector.unregister(fd)
            fh.close()

    with _Selector() as selector:
        selector.register(process.stderr, selectors.EVENT_READ, read_stderr)
        selector.register(process.stdout, selectors.EVENT_READ, read_stdout)
        if process.stdin is not None:
            selector.register(process.stdin, selectors.EVENT_WRITE, write_stdin)
            try:
                process.stdin.flush()
            except BrokenPipeError:
                pass

        while selector.get_map():
            for key, _ in selector.select():
                key.data(selector, key.fd, key.fileobj)

    if process.stdin is not None:
        assert process.stdin.closed

    return _decode(process, stdout, process.stdout), _decode(
        process, stderr, process.stderr
    )


def _decode(
    process: subprocess.Popen[_t.Any], lines: list[bytes], stream: _t.IO[_t.Any]
):
    if not process.text_mode:  # type: ignore
        return lines
    raw = b"".join(lines)
    text = raw.decode(stream.encoding, stream.errors)  # type: ignore
    return [text.replace("\r\n", "\n").replace("\r", "\n")]


def _process_io_nocap(
    process: subprocess.Popen[_t.Any],
    input: str | bytes | None,
    logger: logging.Logger | logging.LoggerAdapter[_t.Any],
    level: int,
):
    if input is not None:
        assert process.stdin is not None
        try:
            process.stdin.write(input)
            process.stdin.flush()
        except BrokenPipeError:
            pass
        process.stdin.close()

    return None, None
