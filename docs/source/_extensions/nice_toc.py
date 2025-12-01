import re
import textwrap

import sphinx.addnodes
from docutils.nodes import Node
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.directives.other import TocTree
from sphinx.util import docname_join

explicit_title_re = re.compile(r"^(.+?)\s*(?<!\x00)<([^<]*?)>$", re.DOTALL)
url_re: re.Pattern[str] = re.compile(r"(?P<schema>.+)://.*")
glob_re = re.compile(r".*[*?\[].*")


class NiceTocDirective(TocTree):
    def run(self) -> list[Node]:
        if "hidden" in self.options:
            return super().run()

        self.options["hidden"] = ""

        content = super().run()

        for node in content:
            if toctree := node.next_node(sphinx.addnodes.toctree):
                break
        else:
            return content

        lines = [
            ".. grid:: 1 2 2 2",
            "    :gutter: 1",
            "    :margin: 4 0 0 0",
            "",
        ]

        for title, docname in toctree["entries"]:
            preview_lines = self.previews.get(docname, [])
            preview = textwrap.indent(
                textwrap.dedent("\n".join(preview_lines)), "        "
            )
            lines.extend(
                [
                    f"    .. grid-item-card:: :doc:`/{docname}`",
                    f"        :link: /{docname}",
                    "        :link-type: doc",
                    f"        :link-alt: {title}",
                    "        :class-card: no-link-decorations",
                    "",
                    preview,
                    "",
                ]
            )

        content.extend(self.parse_text_to_nodes("\n".join(lines)))

        return content

    def parse_content(self, toctree: sphinx.addnodes.toctree) -> None:
        entries = []
        last_entry = None
        lines = []
        for source, offset, value in self.content.xitems():
            if not value or value.startswith(" "):
                lines.append(value)
            else:
                if last_entry:
                    entries.append((last_entry, lines))
                last_entry = source, offset, value
                lines = []
        if last_entry:
            entries.append((last_entry, lines))

        self.content = StringList()

        self.previews = {}
        glob = "glob" in self.options
        current_docname = self.env.docname
        for (source, offset, entry), preview in entries:
            self.content.append(entry, source=source, offset=offset)

            explicit = explicit_title_re.match(entry)
            url_match = url_re.match(entry) is not None

            explicit = explicit_title_re.match(entry)
            url_match = url_re.match(entry) is not None
            if glob and glob_re.match(entry) and not explicit and not url_match:
                continue

            if explicit:
                ref = explicit.group(2)
                docname = ref
            else:
                docname = entry
            docname = docname_join(current_docname, docname)
            self.previews[docname] = preview

        return super().parse_content(toctree)


def setup(app: Sphinx):
    app.add_directive("nice-toc", NiceTocDirective)

    return {
        "version": "1.0.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
