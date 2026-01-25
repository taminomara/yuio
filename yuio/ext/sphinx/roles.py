# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

from docutils import nodes
from sphinx.util.docutils import SphinxRole

FLAG_CLASSES = ["flag"]


class Flag(SphinxRole):
    def run(
        self,
    ) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        classes = FLAG_CLASSES.copy()
        if "classes" in self.options:
            classes.extend(self.options["classes"])
        text = self.text
        return [nodes.literal(self.rawtext, text, classes=classes)], []
