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

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
