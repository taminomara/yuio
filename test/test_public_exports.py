from __future__ import annotations

import importlib
import pathlib
import types

import pytest

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


root = pathlib.Path(__file__).parent.parent / "yuio"
files = [
    file
    for file in root.glob("*.py")
    if (file.name == "__init__.py" or not file.name.startswith("_"))
]
allowlist = ["commit_id", "version_tuple", "version", "TYPE_CHECKING", "GROUP"]


@pytest.mark.parametrize("file", files, ids=[file.name for file in files])
def test_export_consistency(file: pathlib.Path):
    path = "yuio." + ".".join(file.relative_to(root).parts).removesuffix(".py")
    module = importlib.import_module(path)
    all = set(module.__all__)
    missing = set()
    annotations = _t.get_annotations(module)
    for name, value in module.__dict__.items():
        if name.startswith("_") or name in all or name in allowlist:
            continue
        if isinstance(value, (types.ModuleType, _t.TypeVar, _t.ParamSpec)):
            continue
        if name in annotations:
            missing.add(name)
            continue
        if obj_module := getattr(value, "__module__", ""):
            if not obj_module.startswith("yuio"):
                continue
        missing.add(name)

    if missing:
        raise AssertionError(
            "some items are missing from __all__: " + ", ".join(map(repr, missing))
        )
