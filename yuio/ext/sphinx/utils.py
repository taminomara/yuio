# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

import contextlib
import re

import sphinx.util.logging
from docutils import nodes
from sphinx import addnodes

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


_TYPE_PARSE_RE = re.compile(
    r"""
    # Skip spaces, they're not meaningful in this context.
    \s+
    |
    (?P<dots>[.]{3})
    |
    # Literal string with escapes.
    # Example: `"foo"`, `"foo-\"-bar"`.
    (?P<string>(?P<string_q>['"`])(?:\\.|[^\\])*?(?P=string_q))
    |
    # Number with optional exponent.
    # Example: `1.0`, `.1`, `1.`, `1e+5`.
    (?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
    |
    # Built-in type.
    # Example: `string`, `string?`.
    (?P<type>null|true|false|boolean|integer|number|string|any|never|object|set|array)\b
    \s*(?P<type_qm>\??)\s*
    |
    # Name component.
    (?P<name>\w[\w.#-]*)
    |
    # Punctuation that we separate with spaces.
    (?P<punct>[=:,|&])
    |
    # Punctuation that we copy as-is, without adding spaces.
    (?P<other_punct>[-!#$%()*+/;<>?@[\]^_{}~]+)
    |
    # Anything else is copied as-is.
    (?P<other>.)
    """,
    re.VERBOSE,
)


def type_to_nodes(typ: str, inliner, xref_role: str = "cli:obj") -> list[nodes.Node]:
    from yuio.ext.sphinx.domain import CfgXRefRole

    res = []

    for match in _TYPE_PARSE_RE.finditer(typ):
        if text := match.group("dots"):
            res.append(addnodes.desc_sig_name(text, text))
        elif text := match.group("string"):
            res.append(addnodes.desc_sig_literal_string(text, text))
        elif text := match.group("number"):
            res.append(addnodes.desc_sig_literal_number(text, text))
        elif text := match.group("type"):
            res.append(addnodes.desc_sig_keyword_type(text, text))
            if qm := match.group("type_qm"):
                res.append(addnodes.desc_sig_punctuation(qm, qm))
        elif text := match.group("name"):
            text = "~" + text
            ref_nodes, warn_nodes = CfgXRefRole(innernodeclass=addnodes.desc_sig_name)(
                xref_role, text, text, 0, inliner
            )
            res.extend(ref_nodes)
            res.extend(warn_nodes)
        elif text := match.group("punct"):
            if text in "=|&":
                res.append(addnodes.desc_sig_space())
            res.append(addnodes.desc_sig_punctuation(text, text))
            res.append(addnodes.desc_sig_space())
        elif text := match.group("other_punct"):
            res.append(addnodes.desc_sig_punctuation(text, text))
        elif text := match.group("other"):
            res.append(nodes.Text(text))

    return res


@contextlib.contextmanager
def patch_document_title_ids(prefix: str, doc: nodes.document):
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
