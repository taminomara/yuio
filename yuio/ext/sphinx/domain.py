# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass

import sphinx.addnodes
import sphinx.builders
import sphinx.util.logging
from docutils import nodes
from docutils.parsers.rst import directives
from sphinx import addnodes
from sphinx.builders import Builder
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, ObjType
from sphinx.environment import BuildEnvironment
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.docfields import Field
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import make_id, make_refnode

from yuio.ext.sphinx.roles import FLAG_CLASSES
from yuio.ext.sphinx.utils import (
    CfgPath,
    CmdPath,
    cmd2cfg,
    parse_cfg_path,
    parse_cmd_path,
    read_parenthesized_until,
    type_to_nodes,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

T = _t.TypeVar("T")


_logger = sphinx.util.logging.getLogger("yuio.ext.sphinx")


class CliContextManagerMixin(SphinxDirective):
    @property
    def cli_domain(self) -> CliDomain:
        return _t.cast(CliDomain, self.env.get_domain("cli"))

    def push_context(
        self,
        cfg_path: CfgPath,
        cmd_path: CmdPath | None,
    ):
        cfg_paths = self.env.ref_context.setdefault("cli:cfg_paths", [])
        cfg_paths.append(self.env.ref_context.get("cli:cfg_path"))
        self.env.ref_context["cli:cfg_path"] = cfg_path

        if cmd_path is None:
            cmd_path = self.cmd_path

        cmd_paths = self.env.ref_context.setdefault("cli:cmd_paths", [])
        cmd_paths.append(self.env.ref_context.get("cli:cmd_path"))
        self.env.ref_context["cli:cmd_path"] = cmd_path

    def pop_context(self):
        cfg_paths = self.env.ref_context.setdefault("cli:cfg_paths", [])
        if cfg_paths:
            self.env.ref_context["cli:cfg_path"] = cfg_paths.pop()
        else:
            self.env.ref_context.pop("cli:cfg_path", None)

        cmd_paths = self.env.ref_context.setdefault("cli:cmd_paths", [])
        if cmd_paths:
            self.env.ref_context["cli:cmd_path"] = cmd_paths.pop()
        else:
            self.env.ref_context.pop("cli:cmd_path", None)

    @property
    def cfg_path(self) -> CfgPath:
        return self.env.ref_context.get("cli:cfg_path") or CfgPath(())

    @property
    def cmd_path(self) -> CmdPath:
        return self.env.ref_context.get("cli:cmd_path") or CmdPath(())


class CliField(Field):
    is_grouped = True
    list_type = nodes.bullet_list
    classes = []

    def make_field(  # pyright: ignore[reportIncompatibleMethodOverride]
        self,
        types: dict[str, list[nodes.Node]],
        domain: str,
        items: list[tuple[str, list[nodes.Node]]],
        env: BuildEnvironment | None = None,
        inliner: _t.Any | None = None,
        location: _t.Any | None = None,
    ) -> nodes.field:
        fieldname = nodes.field_name("", self.label)
        listnode = self.list_type()
        for fieldarg, content in items:
            par = nodes.paragraph()
            if fieldarg:
                par += nodes.literal(fieldarg, fieldarg, classes=self.classes)
            if fieldarg and content and content[0].children:
                par += nodes.Text(" -- ")
            par += content
            listnode += nodes.list_item("", par)

        if len(items) == 1:
            fieldbody = nodes.field_body("", listnode[0][0])  # type: ignore
            field = nodes.field("", fieldname, fieldbody)
        else:
            fieldbody = nodes.field_body("", listnode)
            field = nodes.field("", fieldname, fieldbody)
        return field


class FlagField(CliField):
    classes = FLAG_CLASSES

    def __init__(
        self,
        name: str,
        names: tuple[str, ...] = (),
        label: str = "",
        has_arg: bool = True,
        rolename: str = "",
        bodyrolename: str = "",
        link_to_parent: bool = False,
    ) -> None:
        super().__init__(name, names, label, has_arg, rolename, bodyrolename)
        self._link_to_parent = link_to_parent

    def make_field(
        self,
        types: dict[str, list[nodes.Node]],
        domain: str,
        items: list[tuple[str, list[nodes.Node]]],
        env: BuildEnvironment | None = None,
        inliner: _t.Any | None = None,
        location: nodes.Element | None = None,
    ) -> nodes.field:
        field = super().make_field(types, domain, items, env, inliner, location)
        fieldname = _t.cast(nodes.field_name, field.children[0])
        if not env or not inliner:
            return field
        cli_domain = _t.cast(CliDomain, env.get_domain("cli"))
        if location is not None and location.source and location.line:
            location_tuple = (location.source, location.line)
        else:
            location_tuple = ("<unknown>", 0)
        for fieldarg, _content in items:
            name, _ = read_parenthesized_until(
                fieldarg, lambda c: c.isspace() or c in ",="
            )
            id = self.make_id(env, inliner.document, name)
            if not id:
                continue
            self.register(env, location_tuple, cli_domain, name, id)
            fieldname["ids"].append(id)
        return field

    def make_id(
        self, env: BuildEnvironment, document: nodes.document, name: str
    ) -> str:
        cfg_path = env.ref_context.get("cli:cfg_path") or CfgPath(())
        cfg_path += cmd2cfg(CmdPath((name,)))
        return make_id(env, document, "cli", ".".join(cfg_path))

    def register(
        self,
        env: BuildEnvironment,
        location: tuple[str, int],
        cli_domain: CliDomain,
        name: str,
        id: str,
    ):
        cfg_path = env.ref_context.get("cli:cfg_path") or CfgPath(())

        cmd_path = env.ref_context.get("cli:cmd_path") or CmdPath(())
        if self._link_to_parent:
            cmd_path = cmd_path[:-1]
        cmd_path += CmdPath((name,))

        cli_domain.note_object(
            location,
            env.docname,
            "flag",
            cfg_path,
            cmd_path,
            id,
            None,
            None,
            priority=0,
        )


class EnvField(FlagField):
    classes = []

    def make_id(
        self, env: BuildEnvironment, document: nodes.document, name: str
    ) -> str:
        return make_id(env, document, "cli", name)

    def register(
        self,
        env: BuildEnvironment,
        location: tuple[str, int],
        cli_domain: CliDomain,
        name: str,
        id: str,
    ):
        cli_domain.note_envvar(
            location,
            env.docname,
            name,
            id,
            priority=0,
        )


_SIG_RE = re.compile(r"^(?P<name>\w+(?:\.\w+)*)$")


class CliObject(
    ObjectDescription[tuple[CfgPath, CmdPath | None]], CliContextManagerMixin
):
    option_spec: _t.ClassVar[dict[str, _t.Callable[[str], _t.Any]]] = {  # type: ignore
        "annotation": directives.unchanged,
        "display-name": directives.unchanged_required,
        "python-name": directives.unchanged_required,
        **ObjectDescription.option_spec,
    }

    doc_field_types: list[Field] = [
        FlagField(
            name="flags",
            names=("flag", "flags"),
            label="Flags",
            has_arg=True,
        ),
        FlagField(
            name="aliases",
            names=("flag-alias", "flag-aliases"),
            label="Aliases",
            has_arg=True,
        ),
        EnvField(
            name="env-vars",
            names=("env", "env-var", "envs", "env-vars"),
            label="Environment variables",
            has_arg=True,
        ),
        Field(name="default", names=("default",), label="Default", has_arg=False),
    ]

    allow_nesting = False

    def run(self) -> list[nodes.Node]:
        self.ids = []
        return super().run()

    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        raise NotImplementedError()

    def handle_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        cfg_name, cmd_name = self.parse_signature(sig, signode)
        cfg_path = signode["cli:cfg_path"] = self.cfg_path + cfg_name
        cmd_path = signode["cli:cmd_path"] = (
            self.cmd_path + cmd_name if cmd_name is not None else None
        )

        self.signature_add_annotations(sig, signode)

        if display_name := self.options.get("display-name"):
            signode += addnodes.desc_name(display_name, display_name)
            signode["cli:display_name"] = signode["cli:toc_name"] = display_name
        elif page_name := signode.get("cli:page_name"):
            signode += addnodes.desc_name(page_name, page_name)
            if "cli:toc_name" not in signode:
                signode["cli:toc_name"] = page_name
        elif toc_name := signode.get("cli:toc_name"):
            signode += addnodes.desc_name(toc_name, toc_name)
        elif cmd_name:
            toc_name = signode["cli:toc_name"] = " ".join(cmd_name)
            signode += addnodes.desc_name(toc_name, toc_name)
        else:
            toc_name = signode["cli:toc_name"] = ".".join(cfg_name)
            signode += addnodes.desc_name(toc_name, toc_name)

        self.signature_add_post_annotations(sig, signode)

        if (cfg_path, cmd_path) in self.names:
            # Need to process aliases here, `add_target_and_index` will not be called
            # because this object is already registered.
            for alias in signode.get("cli:cmd_aliases"):
                self.cli_domain.note_cmd_alias(
                    self.get_source_info(),
                    self.env.docname,
                    cfg_path,
                    alias,
                )

        return cfg_path, cmd_path

    def signature_add_annotations(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ):
        if annotation := self.options.get("annotation"):
            signode += [
                addnodes.desc_sig_keyword(annotation, annotation),
                addnodes.desc_sig_space(),
            ]

    def signature_add_post_annotations(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ):
        if suffix := signode.get("cli:suffix"):
            signode += [
                addnodes.desc_sig_keyword(suffix, suffix),
            ]

    def get_index_text(self, cfg_path: CfgPath, cmd_path: CmdPath | None) -> str:
        if cmd_path:
            *parents, name = cmd_path
            parent = " ".join(parents)
        else:
            *parents, name = cfg_path
            parent = ".".join(parents)

        if parent:
            return f"{name} ({self.objtype} in {parent})"
        else:
            return f"{name} ({self.objtype})"

    def add_target_and_index(
        self,
        name: tuple[CfgPath, CmdPath | None],
        sig: str,
        signode: addnodes.desc_signature,
    ) -> None:
        cfg_path, cmd_path = name
        id = make_id(self.env, self.state.document, "cli", ".".join(cfg_path))
        if id not in self.state.document.ids:
            signode["names"].append(id)
            signode["ids"].append(id)
            self.ids.append(id)
            signode["first"] = not self.names
            self.state.document.note_explicit_target(signode)

            self.cli_domain.note_object(
                self.get_source_info(),
                self.env.docname,
                self.objtype,
                cfg_path,
                cmd_path,
                id,
                signode.get("cli:display_name"),
                signode.get("cli:cmd_aliases"),
            )

            if python_name := self.options.get("python-name"):
                self.cli_domain.note_python_obj(
                    self.get_source_info(),
                    self.env.docname,
                    cfg_path,
                    python_name,
                )

        if "no-index-entry" not in self.options:
            indextext = self.get_index_text(cfg_path, cmd_path)
            if indextext:
                self.indexnode["entries"].append(("single", indextext, id, "", None))

    def _object_hierarchy_parts(
        self, sig_node: addnodes.desc_signature
    ) -> tuple[str, ...]:
        return sig_node["cli:cfg_path"]

    def _toc_entry_name(self, sig_node: addnodes.desc_signature) -> str:
        if not sig_node.get("_toc_parts"):
            return ""

        if self.config.toc_object_entries_show_parents in ["hide", "domain"]:
            return sig_node["cli:toc_name"]
        elif sig_node["cli:cmd_path"]:
            return " ".join(sig_node["cli:cmd_path"])
        else:
            return ".".join(sig_node["cli:cfg_path"])

    def before_content(self) -> None:
        if self.names:
            self.push_context(*self.names[-1])

        obj_types = self.env.ref_context.setdefault("cli:obj_types", [])
        obj_types.append(self.env.ref_context.get("cli:obj_type"))
        self.env.ref_context["cli:obj_type"] = self.objtype

    def after_content(self) -> None:
        if self.names:
            self.pop_context()

        obj_types = self.env.ref_context.setdefault("cli:obj_types", [])
        if obj_types:
            self.env.ref_context["cli:obj_type"] = obj_types.pop()
        else:
            self.env.ref_context.pop("cli:obj_type", None)


class FieldObject(CliObject):
    def run(self) -> list[nodes.Node]:
        return super().run()

    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        name, sig = read_parenthesized_until(
            sig, lambda c: not (c.isalnum() or c in "_-")
        )
        sig = sig.strip()
        if sig.startswith("="):
            sig = " " + sig
        signode["cli:suffix"] = sig

        return parse_cfg_path(name), None

    def signature_add_post_annotations(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ):
        if suffix := signode.get("cli:suffix"):
            signode += type_to_nodes(suffix, self.state.inliner)


class OptObject(CliObject):
    option_spec = {
        "name": directives.unchanged_required,
        **CliObject.option_spec,
    }

    doc_field_types: list[Field] = [
        FlagField(
            name="flags",
            names=("flag", "flags"),
            label="Flags",
            has_arg=True,
            link_to_parent=True,
        ),
        FlagField(
            name="aliases",
            names=("flag-alias", "flag-aliases"),
            label="Aliases",
            has_arg=True,
            link_to_parent=True,
        ),
        EnvField(
            name="env-vars",
            names=("env", "env-var", "envs", "env-vars"),
            label="Environment variables",
            has_arg=True,
        ),
        Field(name="default", names=("default",), label="Default", has_arg=False),
    ]


class FlagObject(OptObject):
    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        names: list[str] = []

        while True:
            sig = sig.removeprefix(",").lstrip()
            name, sig = read_parenthesized_until(
                sig, lambda c: not c.isalnum() and c not in "_+/.-"
            )
            if name := name.strip():
                names.append(name)
            if not sig.startswith(","):
                break

        main_name = ""
        priority = -1
        for name in names:
            if name.startswith("--"):
                new_priority = 2
            elif name.startswith("-"):
                new_priority = 1
            else:
                new_priority = 0
            if new_priority > priority:
                main_name = name
                priority = new_priority

        cmd_path = CmdPath((main_name,))
        if "name" in self.options:
            cfg_path = parse_cfg_path(self.options["name"])
        else:
            cfg_path = cmd2cfg(cmd_path)

        signode["cli:page_name"] = ", ".join(names)
        signode["cli:toc_name"] = main_name
        signode["cli:cmd_aliases"] = [
            self.cmd_path + (name,) for name in names if name != main_name
        ]
        signode["cli:suffix"] = sig

        return cfg_path, cmd_path


class ArgObject(OptObject):
    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        cmd_path = CmdPath((sig,))
        if "name" in self.options:
            cfg_path = parse_cfg_path(self.options["name"])
        else:
            cfg_path = cmd2cfg(cmd_path)

        return cfg_path, cmd_path


class ConfigObject(CliObject):
    allow_nesting = True

    option_spec = {
        "parent-command": directives.unchanged_required,
        "enum": directives.flag,
        **CliObject.option_spec,
    }

    def run(self) -> list[nodes.Node]:
        needs_new_context = "parent-command" in self.options
        if needs_new_context:
            self.push_context(
                self.cfg_path, parse_cmd_path(self.options["parent-command"])
            )
        try:
            return super().run()
        finally:
            if needs_new_context:
                self.pop_context()

    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        return parse_cfg_path(sig.strip()), None

    def signature_add_annotations(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ):
        super().signature_add_annotations(sig, signode)

        # Only add annotation if we're not inside another object.
        if not self.cfg_path or "enum" in self.options:
            if "enum" in self.options:
                annotation = "enum"
            else:
                annotation = "config"
            signode += [
                addnodes.desc_sig_keyword(annotation, annotation),
                addnodes.desc_sig_space(),
            ]


class CmdObject(CliObject):
    allow_nesting = True

    option_spec = {
        "name": directives.unchanged_required,
        **CliObject.option_spec,
    }

    _first_sig_paths = None

    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        cmd_path = parse_cmd_path(sig)
        if "name" in self.options:
            cfg_path = parse_cfg_path(self.options["name"])
        else:
            cfg_path = cmd2cfg(cmd_path)

        if self._first_sig_paths is None:
            self._first_sig_paths = cfg_path, cmd_path
        else:
            cfg_path, main_cmd_path = self._first_sig_paths
            signode["cli:cmd_aliases"] = [cmd_path]
            signode["cli:toc_name"] = " ".join(cmd_path)
            cmd_path = main_cmd_path

        return cfg_path, cmd_path


class EnvVarObject(CliObject):
    def parse_signature(
        self, sig: str, signode: sphinx.addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        name, sig = read_parenthesized_until(
            sig, lambda c: not (c.isalnum() or c in "_-")
        )

        sig = sig.strip()
        if sig.startswith("="):
            sig = " " + sig
        signode["cli:suffix"] = sig

        return parse_cfg_path(name), None


class CliXRefRole(XRefRole):
    def process_link(
        self,
        env: BuildEnvironment,
        refnode: nodes.Element,
        has_explicit_title: bool,
        title: str,
        target: str,
    ) -> tuple[str, str]:
        refnode["cli:cfg_path"] = env.ref_context.get("cli:cfg_path")
        refnode["cli:cmd_path"] = env.ref_context.get("cli:cmd_path")
        return title, target


class CfgXRefRole(CliXRefRole):
    def process_link(
        self,
        env: BuildEnvironment,
        refnode: nodes.Element,
        has_explicit_title: bool,
        title: str,
        target: str,
    ) -> tuple[str, str]:
        title, target = super().process_link(
            env, refnode, has_explicit_title, title, target
        )

        if not has_explicit_title:
            title = title.removeprefix(".")
            target = target.removeprefix("~")
            if title.startswith("~"):
                title = parse_cfg_path(title[1:])[-1]

        if target.startswith("."):
            target = target[1:]
            refnode["refspecific"] = True

        return title, target


class FlagLiteralNode(nodes.literal):
    def __init__(
        self, rawsource: str = "", text: str = "", *children: nodes.Node, **attributes
    ) -> None:
        super().__init__(rawsource, text, *children, **attributes)
        self["classes"].extend(FLAG_CLASSES)


class CmdXRefRole(CliXRefRole):
    innernodeclass = FlagLiteralNode

    def process_link(
        self,
        env: BuildEnvironment,
        refnode: nodes.Element,
        has_explicit_title: bool,
        title: str,
        target: str,
    ) -> tuple[str, str]:
        title, target = super().process_link(
            env, refnode, has_explicit_title, title, target
        )

        if not has_explicit_title:
            title = title.removeprefix(". ")
            target = target.removeprefix("~")
            if title.startswith("~"):
                title = parse_cmd_path(title[1:])[-1]

        if target.startswith(". "):
            target = target[2:]
            refnode["refspecific"] = True

        return title, target


class EnvXRefRole(CliXRefRole):
    pass


class CliDomain(Domain):
    @dataclass
    class IndexEntry:
        docname: str
        objtype: str
        cfg_path: CfgPath
        cmd_path: CmdPath | None
        id: str | None
        display_name: str | None
        location: str
        priority: int

        @property
        def human_readable_full_name(self) -> str:
            if self.cmd_path is not None:
                return " ".join(self.cmd_path)
            else:
                return " ".join(self.cfg_path)

    @dataclass
    class EnvIndexEntry:
        docname: str
        objtype: str
        name: str
        id: str | None
        location: str
        priority: int

        @property
        def human_readable_full_name(self) -> str:
            return self.name

    name = "cli"

    label = "cli"

    object_types = {
        "command": ObjType(_("command"), "cmd", "cli", "any", "_auto", cli_priority=6),
        "flag": ObjType(
            _("flag"), "flag", "opt", "cli", "any", "_auto", cli_priority=5
        ),
        "argument": ObjType(
            _("argument"), "arg", "opt", "cli", "any", "_auto", cli_priority=4
        ),
        "config": ObjType(_("config"), "cfg", "obj", "any", "_auto", cli_priority=3),
        "field": ObjType(_("field"), "field", "obj", "any", "_auto", cli_priority=2),
        "envvar": ObjType(_("environment variable"), "env", "any", "_auto"),
    }

    directives = {
        "command": CmdObject,
        "flag": FlagObject,
        "argument": ArgObject,
        "config": ConfigObject,
        "field": FieldObject,
        "envvar": EnvVarObject,
    }

    roles = {
        # cmd ns
        "cmd": CmdXRefRole(),  # command
        "flag": CmdXRefRole(),  # flag
        "arg": CmdXRefRole(),  # argument
        "opt": CmdXRefRole(),  # flag or argument
        "cli": CmdXRefRole(),  # command or flag or argument
        # cfg ns
        "cfg": CfgXRefRole(),  # config
        "field": CfgXRefRole(),  # field
        "obj": CfgXRefRole(),  # config or field
        # env ns
        "env": EnvXRefRole(),  # envvar
        # any ns
        "any": CliXRefRole(),  # any object
        "_auto": CliXRefRole(),  # any object
    }

    initial_data = {
        "cmd_ns": {},
        "cfg_ns": {},
        "env_ns": {},
        "py_ns": {},
    }

    @property
    def cmd_ns(self) -> dict[CmdPath, IndexEntry]:
        return self.data["cmd_ns"]

    @property
    def cfg_ns(self) -> dict[CfgPath, IndexEntry]:
        return self.data["cfg_ns"]

    @property
    def env_ns(self) -> dict[str, EnvIndexEntry]:
        return self.data["env_ns"]

    @property
    def py_ns(self) -> dict[str, IndexEntry]:
        return self.data["py_ns"]

    def default_priority(self, objtype) -> int:
        return self.object_types[objtype].attrs.get("cli_priority", 0)

    def note_object(
        self,
        location: tuple[str, int],
        docname: str,
        objtype: str,
        cfg_path: CfgPath,
        cmd_path: CmdPath | None,
        id: str | None,
        display_name: str | None,
        cmd_aliases: list[CmdPath] | None,
        priority: int | None = None,
    ):
        if objtype == "envvar":
            self.note_envvar(
                location,
                docname,
                "".join(cfg_path),
                id,
                priority,
            )

        if priority is None:
            priority = self.default_priority(objtype)

        entry = CliDomain.IndexEntry(
            docname=docname,
            objtype=objtype,
            cfg_path=cfg_path,
            cmd_path=cmd_path,
            id=id,
            display_name=display_name,
            location=f"{location[0]}:{location[1]}",
            priority=priority,
        )

        if cfg_path in self.cfg_ns:
            if priority > 0:
                self._report_duplicate(".".join(cfg_path), entry, self.cfg_ns[cfg_path])
                if self.cfg_ns[cfg_path].priority < priority:
                    self.cfg_ns[cfg_path] = entry
        else:
            self.cfg_ns[cfg_path] = entry

        if cmd_path is not None:
            if cmd_path in self.cmd_ns:
                if priority > 0:
                    self._report_duplicate(
                        " ".join(cmd_path), entry, self.cmd_ns[cmd_path]
                    )
                    if self.cmd_ns[cmd_path].priority < priority:
                        self.cmd_ns[cmd_path] = entry
            else:
                self.cmd_ns[cmd_path] = entry

        for alias in cmd_aliases or []:
            self.note_cmd_alias(location, docname, cfg_path, alias)

    def note_envvar(
        self,
        location: tuple[str, int],
        docname: str,
        name: str,
        id: str | None,
        priority: int | None = None,
    ):
        if priority is None:
            priority = self.default_priority("envvar")

        entry = CliDomain.EnvIndexEntry(
            docname=docname,
            objtype="envvar",
            name=name,
            id=id,
            location=f"{location[0]}:{location[1]}",
            priority=priority,
        )

        if name in self.env_ns:
            if priority > 0:
                self._report_duplicate(name, entry, self.env_ns[name])
                if priority > self.env_ns[name].priority:
                    self.env_ns[name] = entry
        else:
            self.env_ns[name] = entry

    def note_cmd_alias(
        self,
        location: tuple[str, int],
        docname: str,
        cfg_path: CfgPath,
        alias: CmdPath,
    ):
        entry = self.cfg_ns.get(cfg_path)
        if not entry:
            return
        entry = dataclasses.replace(
            entry, location=f"{location[0]}:{location[1]}", docname=docname
        )
        if alias in self.cmd_ns:
            self._report_duplicate(" ".join(alias), entry, self.cmd_ns[alias])
        else:
            self.cmd_ns[alias] = entry

    def note_python_obj(
        self,
        location: tuple[str, int],
        docname: str,
        cfg_path: CfgPath,
        python_name: str,
    ):
        entry = self.cfg_ns.get(cfg_path)
        if not entry:
            return
        entry = dataclasses.replace(
            entry, location=f"{location[0]}:{location[1]}", docname=docname
        )
        if python_name in self.py_ns:
            self._report_duplicate(python_name, entry, self.py_ns[python_name])
        else:
            self.py_ns[python_name] = entry

    def _report_duplicate(
        self, path: str, l: IndexEntry | EnvIndexEntry, r: IndexEntry | EnvIndexEntry
    ):
        _logger.warning(
            "duplicate object description of %s %s, "
            "other instance in %s, "
            "use :no-index: for one of them",
            l.objtype,
            path,
            r.location,
            location=l.location,
        )

    def clear_doc(self, docname):
        for fullname, entry in list(self.cfg_ns.items()):
            if entry.docname == docname:
                self.cfg_ns.pop(fullname)

        for fullname, entry in list(self.cmd_ns.items()):
            if entry.docname == docname:
                self.cmd_ns.pop(fullname)

        for fullname, entry in list(self.env_ns.items()):
            if entry.docname == docname:
                self.env_ns.pop(fullname)

        for fullname, entry in list(self.py_ns.items()):
            if entry.docname == docname:
                self.py_ns.pop(fullname)

    def merge_domaindata(self, docnames, otherdata):
        cfg_ns: dict[CfgPath, CliDomain.IndexEntry] = otherdata["cfg_ns"]
        for fullname, entry in cfg_ns.items():
            if entry.docname in docnames:
                should_override = self._check_duplicates(
                    fullname, self.cfg_ns, cfg_ns, lambda p: " ".join(p)
                )
                if should_override:
                    self.cfg_ns[fullname] = entry

        cmd_ns: dict[CmdPath, CliDomain.IndexEntry] = otherdata["cmd_ns"]
        for fullname, entry in cmd_ns.items():
            if entry.docname in docnames:
                should_override = self._check_duplicates(
                    fullname, self.cmd_ns, cmd_ns, lambda p: ".".join(p)
                )
                if should_override:
                    self.cmd_ns[fullname] = entry

        env_ns: dict[str, CliDomain.EnvIndexEntry] = otherdata["env_ns"]
        for fullname, entry in env_ns.items():
            if entry.docname in docnames:
                should_override = self._check_duplicates(
                    fullname, self.env_ns, env_ns, lambda p: p
                )
                if should_override:
                    self.env_ns[fullname] = entry

        py_ns: dict[str, CliDomain.IndexEntry] = otherdata["py_ns"]
        for fullname, entry in py_ns.items():
            if entry.docname in docnames:
                should_override = self._check_duplicates(
                    fullname, self.py_ns, py_ns, lambda p: p
                )
                if should_override:
                    self.py_ns[fullname] = entry

    def _check_duplicates(
        self,
        path: T,
        l: dict[T, IndexEntry] | dict[T, EnvIndexEntry],
        r: dict[T, IndexEntry] | dict[T, EnvIndexEntry],
        path_to_str: _t.Callable[[T], str],
    ):
        if path in l and path in r:
            self._report_duplicate(path_to_str(path), l[path], r[path])
            return l[path].priority < r[path].priority
        else:
            return True

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        typ: str,
        target: str,
        node: addnodes.pending_xref,
        contnode: nodes.Element,
    ) -> nodes.reference | None:
        entries = self._resolve_object(node, target, typ)

        if not entries:
            return None
        if len(entries) > 1:
            _logger.warning(
                "ambiguous reference %r, can refer to %s",
                target,
                ", ".join(opt.human_readable_full_name for opt in entries),
                location=node,
            )

        return self._make_refnode(fromdocname, builder, node, contnode, entries[0], typ)

    def resolve_any_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        target: str,
        node: addnodes.pending_xref,
        contnode: nodes.Element,
    ) -> list[tuple[str, nodes.reference]]:
        if not target:
            return []

        entries = self._resolve_object(node, target, None)

        res = []
        for entry in entries:
            typ = self.role_for_objtype(entry.objtype, None) or "obj"
            res.append(
                (
                    f"cli:{typ}",
                    self._make_refnode(
                        fromdocname, builder, node, contnode, entry, typ
                    ),
                )
            )
        return res

    def _resolve_object(
        self, node: addnodes.pending_xref, target: str, typ: str | None
    ):
        if typ is not None:
            typ_cls = self.roles.get(typ)
            allowed_objects = self.objtypes_for_role(typ)
            if typ == "_auto":
                if py_res := self._search_in_py(node, target, allowed_objects):
                    return py_res
                else:
                    return self._search_in_cfg(node, target, allowed_objects)
            elif isinstance(typ_cls, CfgXRefRole):
                return self._search_in_cfg(node, target, allowed_objects)
            elif isinstance(typ_cls, CmdXRefRole):
                return self._search_in_cmd(node, target, allowed_objects)
            elif isinstance(typ_cls, EnvXRefRole):
                return self._search_in_env(node, target, allowed_objects)
        else:
            allowed_objects = None

        res = []

        if _SIG_RE.match(target):
            res.extend(self._search_in_cfg(node, target, allowed_objects))
        res.extend(self._search_in_cmd(node, target, allowed_objects))
        res.extend(self._search_in_env(node, target, allowed_objects))

        return res

    def _search_in_cfg(
        self,
        node: addnodes.pending_xref,
        target: str,
        allowed_objects: list[str] | None,
    ):
        path: CfgPath = node.get("cli:cfg_path") or CfgPath(())
        target_path = parse_cfg_path(target)

        if refspecific := node.get("refspecific", False):
            # Start from inner namespace.
            path_slice_indices = range(len(path), -1, -1)
        else:
            # Start from outer namespace.
            path_slice_indices = range(len(path) + 1)

        for i in path_slice_indices:
            candidate = self._canonize_cfg_path(path[:i] + target_path)
            if (entry := self.cfg_ns.get(candidate)) and (
                not allowed_objects or entry.objtype in allowed_objects
            ):
                return [entry]

        candidates: list[CliDomain.IndexEntry] = []
        if refspecific:
            for path, entry in self.cfg_ns.items():
                if path[-len(target_path) :] == target_path:
                    candidates.append(entry)
        return candidates

    def _canonize_cfg_path(self, path: CfgPath):
        canonical_path = ()
        for part in path:
            canonical_path += CfgPath((part,))
            if entry := self.cfg_ns.get(CfgPath(canonical_path)):
                canonical_path = entry.cfg_path
        return CfgPath(canonical_path)

    def _search_in_cmd(
        self,
        node: addnodes.pending_xref,
        target: str,
        allowed_objects: list[str] | None,
    ):
        path: CmdPath = node.get("cli:cmd_path") or CmdPath(())
        target_path = parse_cmd_path(target)

        if refspecific := node.get("refspecific", False):
            # Start from inner namespace.
            path_slice_indices = range(len(path), -1, -1)
        else:
            # Start from outer namespace.
            path_slice_indices = range(len(path) + 1)

        for i in path_slice_indices:
            candidate = self._canonize_cmd_path(path[:i] + target_path)
            if (entry := self.cmd_ns.get(candidate)) and (
                not allowed_objects or entry.objtype in allowed_objects
            ):
                return [entry]

        candidates: list[CliDomain.IndexEntry] = []
        if refspecific:
            for path, entry in self.cmd_ns.items():
                if path[-len(target_path) :] == target_path:
                    candidates.append(entry)
        return candidates

    def _canonize_cmd_path(self, path: CmdPath):
        canonical_path = ()
        for part in path:
            canonical_path += CmdPath((part,))
            if (
                entry := self.cmd_ns.get(CmdPath(canonical_path))
            ) and entry.cmd_path is not None:
                canonical_path = entry.cmd_path
        return CmdPath(canonical_path)

    def _search_in_env(
        self,
        node: addnodes.pending_xref,
        target: str,
        allowed_objects: list[str] | None,
    ):
        if (entry := self.env_ns.get(target)) and (
            not allowed_objects or entry.objtype in allowed_objects
        ):
            return [entry]
        else:
            return []

    def _search_in_py(
        self,
        node: addnodes.pending_xref,
        target: str,
        allowed_objects: list[str] | None,
    ):
        if (entry := self.py_ns.get(target)) and (
            not allowed_objects or entry.objtype in allowed_objects
        ):
            return [entry]
        else:
            return []

    def _make_refnode(
        self,
        fromdocname: str,
        builder: sphinx.builders.Builder,
        node: addnodes.pending_xref,
        contnode: nodes.Element,
        entry: IndexEntry | EnvIndexEntry,
        typ: str,
    ) -> nodes.reference:
        if (
            not node["refexplicit"]
            and isinstance(entry, CliDomain.IndexEntry)
            and entry.display_name
        ):
            contnode = contnode.deepcopy()
            contnode.clear()
            contnode += nodes.Text(entry.display_name)
        if (ref_role := self.roles.get(typ)) and isinstance(ref_role, CmdXRefRole):
            for cls in FLAG_CLASSES:
                if cls not in contnode["classes"]:
                    contnode["classes"].append(cls)
        return make_refnode(
            builder,
            fromdocname,
            entry.docname,
            entry.id,
            contnode,
            entry.human_readable_full_name,
        )

    def get_objects(self):
        for fullname, entry in self.cfg_ns.items():
            if entry.id:
                display_name = entry.display_name or entry.cfg_path[-1]
                yield (
                    ".".join(fullname),
                    display_name,
                    entry.objtype,
                    entry.docname,
                    entry.id,
                    1,
                )

    def get_full_qualified_name(self, node: nodes.Element) -> str | None:
        path = node.get("cli:path")
        target = node.get("reftarget")
        if target is None:
            return None
        else:
            return ".".join(filter(None, [path, target]))
