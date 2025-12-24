from docutils.nodes import Element
from sphinx.addnodes import desc_addname
from sphinx.application import Sphinx
from sphinx.domains.std import GenericObject
from sphinx.environment import BuildEnvironment
from sphinx.roles import EmphasizedLiteral


class PathRole(GenericObject):
    def parse_node(self, env: BuildEnvironment, sig: str, signode: Element) -> str:  # type: ignore
        sig = sig.strip()
        if not (sig.startswith("`") and sig.endswith("`")):
            signode += desc_addname(sig, sig)
            return sig
        sig = sig[1:-1]
        nodes, msgs = EmphasizedLiteral()(
            "samp",
            sig,
            sig,
            self.lineno,
            self.state.inliner,
        )
        signode += desc_addname(
            "",
            "",
            *nodes[0].children,
            role=self.name.lower(),
            classes=["color-path-hl"],
        )
        signode += msgs
        return sig


def setup(app: Sphinx):
    app.add_object_type("color-path", "color-path", "%s")
    app.add_directive_to_domain("std", "color-path", PathRole, override=True)

    app.add_object_type("decoration-path", "decoration-path", "%s")
    app.add_directive_to_domain("std", "decoration-path", PathRole, override=True)

    return {
        "version": "1.0.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
