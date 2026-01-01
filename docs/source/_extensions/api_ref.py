from docutils.nodes import Element, bullet_list, inline, list_item, paragraph, strong
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.domains.python import PythonDomain
from sphinx.environment import BuildEnvironment
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.docutils import SphinxDirective

import typing_extensions as _t


class ApiRefNode(Element):
    pass


class ApiRefDirective(SphinxDirective):
    required_arguments = 1
    option_spec = {"filter": lambda x: (x or "").split()}

    def run(self):
        return [
            ApiRefNode(root=self.arguments[0], filter=self.options.get("filter", []))
        ]


class ApiRefTransform(SphinxPostTransform):
    default_priority = 200

    def apply(self, **kwargs: _t.Any):
        self.domain: PythonDomain = self.env.get_domain("py")  # type: ignore
        for node in self.document.findall(ApiRefNode):
            node.replace_self(self.render(node["root"], set(node["filter"])))

    def render(self, root: str, filter: set[str]):
        object = collect_objects(self.env, root)
        return self.make_children(object, root, root, filter)

    def make_object_ref(
        self, object: dict[str, _t.Any], name: str, path: str, filter: set[str]
    ):
        if path in filter:
            return []
        type: str = object.get("@type", "module")
        reftype = self.domain.role_for_objtype(type, "obj")
        text = path
        if type in ("function", "method", "classmethod", "staticmethod"):
            text += "()"
        if type == "module":
            contnode = strong("", text)
        else:
            *prefix, text = text.split(".")
            prefix = ".".join(prefix)
            if prefix:
                prefix += "."
            contnode = inline(
                "", "", inline("", prefix, classes=["api-ref-prefix"]), inline("", text)
            )
        nodes = list_item(
            "",
            paragraph(
                "",
                "",
                self.domain.resolve_xref(
                    self.env,
                    self.env.docname,
                    self.app.builder,
                    reftype,
                    path,
                    pending_xref("", contnode),
                    contnode,
                )
                or contnode,
            ),
        )
        if type == "module":
            nodes += self.make_children(object, name, path, filter)
        return nodes

    def make_children(
        self, object: dict[str, _t.Any], name: str, path: str, filter: set[str]
    ):
        nodes = bullet_list("")
        children = [name for name in object if not name.startswith("@")]
        for name in sorted(children, key=lambda name: sortkey(name, object[name])):
            nodes += self.make_object_ref(object[name], name, f"{path}.{name}", filter)
        return nodes


def collect_objects(env: BuildEnvironment, filter: str):
    domain: PythonDomain = env.get_domain("py")  # type: ignore

    objects = {}

    for name, data in domain.modules.items():
        if not name.startswith(filter):
            continue
        root = objects
        for part in name.split("."):
            root = root.setdefault(part, {})
        root["@type"] = "module"
        root["@synopsis"] = data.synopsis
    for name, data in domain.objects.items():
        if not name.startswith(filter):
            continue
        root = objects
        for part in name.split("."):
            root = root.setdefault(part, {})
        root["@type"] = data.objtype
        root["@synopsis"] = ""

    root = objects
    for name in filter.split("."):
        root = objects[name]
    return root


_SORTKEYS = {
    "data": 0,
    "function": 1,
    "class": 2,
    "exception": 2,
    "attribute": 3,
    "property": 3,
    "classmethod": 4,
    "staticmethod": 5,
    "method": 6,
    "type": 7,
    "module": 8,
}


def sortkey(name, object):
    return _SORTKEYS.get(object.get("@type", "module"), 8), name


def setup(app: Sphinx):
    app.add_directive("api-ref", ApiRefDirective)
    app.add_post_transform(ApiRefTransform)

    return {
        "version": "1.0.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
