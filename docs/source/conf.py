import datetime
import pathlib
import sys
import os

sys.path.append(str(pathlib.Path(__file__).parent.joinpath("_ext")))
os.environ["__YUIO_SPHINX_BUILD"] = '1'

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
    "sphinxcontrib.jquery",
    "sphinx_vhs",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "sphinx": ("https://www.sphinx-doc.org/en/master/", None),
}

autodoc_typehints_format = "short"
autodoc_member_order = "bysource"

pygments_style = "yuio_pygments.Style"

vhs_cwd = pathlib.Path(__file__).parent.parent.parent
vhs_min_version = "0.7.2"

# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_extra_path = ["_extra/robots.txt"]
