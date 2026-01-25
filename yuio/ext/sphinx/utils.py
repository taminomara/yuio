from __future__ import annotations

import contextlib

import sphinx.util.logging
from docutils.nodes import document

from yuio.doc import (
    _cmd2cfg,
    _parse_cfg_path,
    _parse_cmd_path,
    _read_parenthesized_until,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


_logger = sphinx.util.logging.getLogger("yuio.ext.sphinx")


if TYPE_CHECKING:

    class CmdPath(tuple[str, ...]):
        __slots__ = ()

        def __new__(cls, iterable: tuple[str, ...] | list[str] = ...) -> CmdPath: ...
        @_t.overload
        def __add__(self, rhs: CmdPath) -> CmdPath: ...  # type: ignore
        @_t.overload
        def __add__(self, rhs: tuple[str, ...]) -> tuple[str, ...]: ...  # type: ignore
        @_t.overload
        def __getitem__(self, rhs: _t.SupportsIndex) -> str: ...  # type: ignore
        @_t.overload
        def __getitem__(self, rhs: slice) -> CmdPath: ...

    class CfgPath(tuple[str, ...]):
        __slots__ = ()

        def __new__(cls, iterable: tuple[str, ...] | list[str] = ...) -> CfgPath: ...
        @_t.overload
        def __add__(self, rhs: CfgPath) -> CfgPath: ...  # type: ignore
        @_t.overload
        def __add__(self, rhs: tuple[str, ...]) -> tuple[str, ...]: ...  # type: ignore
        @_t.overload
        def __getitem__(self, rhs: _t.SupportsIndex) -> str: ...  # type: ignore
        @_t.overload
        def __getitem__(self, rhs: slice) -> CfgPath: ...
else:
    CmdPath = tuple
    CfgPath = tuple


@contextlib.contextmanager
def patch_document_title_ids(prefix: str, doc: document):
    old_prefix = doc.settings.id_prefix or ""
    doc.settings.id_prefix = prefix + old_prefix

    try:
        yield
    finally:
        doc.settings.id_prefix = old_prefix


def parse_cfg_path(path: str) -> CfgPath:
    return CfgPath(_parse_cfg_path(path))


def parse_cmd_path(path: str) -> CmdPath:
    return CmdPath(_parse_cmd_path(path))


def cmd2cfg(cmd: CmdPath) -> CfgPath:
    return CfgPath(_cmd2cfg(cmd))


read_parenthesized_until = _read_parenthesized_until
