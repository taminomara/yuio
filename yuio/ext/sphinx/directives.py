# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

from collections.abc import Sequence

from docutils import nodes
from docutils.transforms.misc import CallBack
from sphinx.util.docutils import SphinxDirective


class IfSphinx(SphinxDirective):
    has_content = True

    def run(self) -> Sequence[nodes.Node]:
        return self.parse_content_to_nodes(allow_section_headings=True)


class IfNotSphinx(SphinxDirective):
    has_content = True

    def run(self) -> Sequence[nodes.Node]:
        return []


class CutIfNotSphinx(SphinxDirective):
    def run(self) -> Sequence[nodes.Node]:
        pending = nodes.pending(CallBack, {"callback": self._process_cut_node})
        self.state.document.note_pending(pending)
        return [pending]

    @staticmethod
    def _process_cut_node(pending: nodes.pending):
        if (
            isinstance(pending.parent, nodes.list_item)
            and len(pending.parent.children) == 1
        ):
            if len(pending.parent.parent.children) == 1:
                pending.parent.parent.replace_self([])
            else:
                pending.parent.replace_self([])


class IfOptDoc(SphinxDirective):
    has_content = True

    def run(self) -> Sequence[nodes.Node]:
        if self.env.ref_context.get("cli:obj_type") in ["command", "flag", "argument"]:
            return self.parse_content_to_nodes(allow_section_headings=True)
        else:
            return []


class IfNotOptDoc(SphinxDirective):
    has_content = True

    def run(self) -> Sequence[nodes.Node]:
        if self.env.ref_context.get("cli:obj_type") in ["command", "flag", "argument"]:
            return []
        else:
            return self.parse_content_to_nodes(allow_section_headings=True)
