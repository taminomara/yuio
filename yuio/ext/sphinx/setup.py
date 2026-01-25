# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

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
from yuio.ext.sphinx.roles import Flag, suppress_auto_ref_warnings


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
    app.connect("warn-missing-reference", suppress_auto_ref_warnings)

    return {
        "version": yuio.__version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
