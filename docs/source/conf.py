import datetime
import os
import pathlib

os.environ["__YUIO_SPHINX_BUILD"] = "1"

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
    "sphinx_design",
    "sphinx_vhs",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}
nitpick_ignore_regex = [
    (r"py:class", r"(.*\.)?([A-Z]{1,2}|[A-Z]+_co|Cmp|SupportsLt|Sz|TAst|_[^.]*)")
]
autodoc_typehints_format = "short"
autodoc_member_order = "bysource"

vhs_cwd = pathlib.Path(__file__).parent.parent.parent
vhs_min_version = "0.7.2"

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
html_js_files = [
    "mermaid-init.js",
    (
        "https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js",
        {"defer": "defer"},
    ),
]
html_theme_options = {
    "source_repository": "https://github.com/taminomara/yuio",
    "source_branch": "main",
    "source_directory": "docs/source",
}
