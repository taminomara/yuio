import datetime
import os
import pathlib
import sys

os.environ["__YUIO_SPHINX_BUILD"] = "1"
sys.path.append(str(pathlib.Path(__file__).parent / "_code"))
sys.path.append(str(pathlib.Path(__file__).parent / "_extensions"))

import yuio

# -- Project information -----------------------------------------------------

project = "Yuio"
copyright = f"{datetime.date.today().year}, Tamika Nomara"
author = "Tamika Nomara"
release = version = yuio.__version__


# -- General configuration ---------------------------------------------------

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    "sphinx.ext.todo",
    "yuio.ext.sphinx",
    "sphinx_design",
    "sphinx_vhs",
    "sphinx_syntax",
    "nice_toc",
    "code_annotations",
    "api_ref",
    "yuio_objects",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
nitpick_ignore_regex = [
    (
        r"py:obj",
        r"(.*\.)?([A-Z]\w?|[A-Z]+_co|Cmp|SupportsLt|TAst|NamespaceT|ConfigT|_[^.]*)",
    ),
    (
        r"py:class",
        r"(.*\.)?([A-Z]\w?|[A-Z]+_co|Cmp|SupportsLt|TAst|NamespaceT|ConfigT|_[^.]*)",
    ),
]
autodoc_typehints_format = "short"
autodoc_member_order = "bysource"
autodoc_inherit_docstrings = False
# autodoc_typehints = "description"  # maybe sphinx 9 fixes this mess?
autodoc_type_aliases = {
    "DISABLED": "~yuio.DISABLED",
    "MISSING": "~yuio.MISSING",
    "POSITIONAL": "~yuio.POSITIONAL",
    "COLLAPSE": "~yuio.COLLAPSE",
    **{
        name: path
        for path in [
            "~yuio.app.OptionCtor",
            "~yuio.io.ExcInfo",
            "~yuio.widget.ActionKey",
            "~yuio.widget.ActionKeys",
            "~yuio.widget.Action",
            "~yuio.string.Colorable",
            "~yuio.string.RawString",
            "~yuio.string.AnyString",
            "~yuio.string.NoWrapStart",
            "~yuio.string.NoWrapEnd",
            "~yuio.string.NoWrapMarker",
            "~yuio.json_schema.JsonValue",
            "~yuio.dbg.EnvCollector",
            "~yuio.cli.NArgs",
        ]
        for name in [
            path.rsplit(".", maxsplit=1)[-1].removeprefix("~"),
            path.removeprefix("~"),
        ]
    },
}

vhs_cwd = pathlib.Path(__file__).parent.parent.parent
vhs_min_version = "0.7.2"
vhs_n_jobs_read_the_docs = 4
# vhs_repo = "agentstation/vhs"
# vhs_format = "svg"

toc_object_entries_show_parents = "hide"

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_css_files = ["extra.css"]
html_js_files = [
    "mermaid-init.js",
    (
        "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js",
        {"defer": "defer"},
    ),
    "code-annotations.js",
]
html_theme_options = {
    "source_repository": "https://github.com/taminomara/yuio",
    "source_branch": "main",
    "source_directory": "docs/source",
}

# fmt: off
from sphinx.util import inspect


# See https://github.com/sphinx-doc/sphinx/issues/14003
class TypeAliasForwardRef(inspect.TypeAliasForwardRef):
    def __repr__(self) -> str:
        return self.name

    def __or__(self, value):
        import typing
        return typing.Union[self, value]

    def __ror__(self, value):
        import typing
        return typing.Union[value, self]

inspect.TypeAliasForwardRef = TypeAliasForwardRef
del TypeAliasForwardRef
del inspect

# See https://github.com/sphinx-doc/sphinx/issues/14005
import sphinx.domains.python._annotations
from sphinx.domains.python._annotations import parse_reftarget as _parse_reftarget


def parse_reftarget(*args, **kwargs):
    _, reftarget, title, refspecific = _parse_reftarget(*args, **kwargs)
    if reftarget in ["yuio.Positional", "yuio.Collapse", "yuio.Disabled", "yuio.Missing"]:
        reftarget = "yuio." + reftarget.removeprefix("yuio.").upper()
    elif reftarget.startswith("_t."):
        reftarget = "typing." + reftarget.removeprefix("_t.")
        if title.startswith("_t."):
            title = title.removeprefix("_t.")
    return "obj", reftarget, title, refspecific
sphinx.domains.python._annotations.parse_reftarget = parse_reftarget
# fmt: on
