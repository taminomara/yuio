from __future__ import annotations

import importlib
import pathlib
import types

import pytest

from yuio import _typing as _t

root = pathlib.Path(__file__).parent.parent / "yuio"
files = [file for file in root.glob("*.py") if not file.name.startswith("_")]


@pytest.mark.parametrize("file", files, ids=[file.name for file in files])
def test_export_consistency(file: pathlib.Path):
    path = "yuio." + ".".join(file.relative_to(root).parts).removesuffix(".py")
    module = importlib.import_module(path)
    all = set(module.__all__)
    missing = set()
    for name, value in module.__dict__.items():
        if name.startswith("_"):
            continue
        if name in all:
            continue
        if isinstance(value, (types.ModuleType, _t.TypeVar, _t.ParamSpec)):
            continue
        if obj_module := getattr(value, "__module__", None):
            if not obj_module.startswith("yuio"):
                continue
        missing.add(name)

    assert not missing, "some items are missing from __all__"
