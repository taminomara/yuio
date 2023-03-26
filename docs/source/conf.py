import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).parent.joinpath('_ext')))
sys.path.append(str(pathlib.Path(__file__).parent.parent.parent))

# -- Project information -----------------------------------------------------

project = 'Yuio'
copyright = '2022, Tamika Nomara'
author = 'Tamika Nomara'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx.ext.graphviz',
]

templates_path = ['_templates']

exclude_patterns = []

intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
}

autodoc_typehints_format = 'short'
autodoc_member_order = 'bysource'

graphviz_output_format = 'svg'

pygments_style = 'yuio_pygments.Style'

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
