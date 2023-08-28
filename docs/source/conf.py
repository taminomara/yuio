import datetime
import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).parent.joinpath("_ext")))

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
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.graphviz",
    "sphinxcontrib.jquery",
    "sphinx_vhs",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

autodoc_typehints_format = "short"
autodoc_member_order = "bysource"

graphviz_output_format = "svg"

pygments_style = "yuio_pygments.Style"

vhs_cwd = pathlib.Path(__file__).parent.parent.parent

# -- Options for HTML output -------------------------------------------------

html_theme = "sphinx_rtd_theme"
html_extra_path = ["_extra/robots.txt"]
