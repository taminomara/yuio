from __future__ import annotations

from sphinx.application import Sphinx

import yuio
from yuio.ext.sphinx.autodoc import AutodocDirective
from yuio.ext.sphinx.directives import (
    CutIfNotSphinx,
    IfNotOptDoc,
    IfNotSphinx,
    IfOptDoc,
    IfSphinx,
)
from yuio.ext.sphinx.domain import CliDomain
from yuio.ext.sphinx.roles import Flag


def setup(app: Sphinx):
    app.require_sphinx((8, 0))
    app.add_domain(CliDomain)
    app.add_directive_to_domain("cli", "autoobject", AutodocDirective)
    app.add_directive("if-sphinx", IfSphinx)
    app.add_directive("if-not-sphinx", IfNotSphinx)
    app.add_directive("cut-if-not-sphinx", CutIfNotSphinx)
    app.add_directive("if-opt-doc", IfOptDoc)
    app.add_directive("if-not-opt-doc", IfNotOptDoc)
    app.add_role("flag", Flag())

    return {
        "version": yuio.__version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
