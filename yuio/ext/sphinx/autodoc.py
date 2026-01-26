# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

from __future__ import annotations

import enum
import importlib
import inspect
import json
import re
import types

import sphinx.util.logging
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.states import RSTState, RSTStateMachine
from docutils.statemachine import StringList
from sphinx import addnodes
from sphinx.util.docutils import switch_source_input
from sphinx.util.inspect import isclass, isenumattribute, isenumclass
from sphinx.util.parsing import nested_parse_to_nodes

import yuio.app
import yuio.cli
import yuio.config
import yuio.json_schema
import yuio.string
import yuio.util
from yuio.doc import _cmd2cfg_part
from yuio.ext.sphinx.domain import (
    CfgPath,
    CliContextManagerMixin,
    CliObject,
    CmdObject,
    CmdPath,
    CmdXRefRole,
    ConfigObject,
    FieldObject,
    OptObject,
    parse_cfg_path,
)
from yuio.ext.sphinx.utils import patch_document_title_ids, type_to_nodes

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t


T = _t.TypeVar("T")


_logger = sphinx.util.logging.getLogger("yuio.ext.sphinx")


def isapp(obj) -> _t.TypeGuard[yuio.app.App[_t.Any]]:
    return isinstance(obj, yuio.app.App)


def isconfigfield(obj) -> _t.TypeGuard[yuio.config._Field]:
    return isinstance(obj, yuio.config._Field)


def isconfig(obj) -> _t.TypeGuard[type[yuio.config.Config]]:
    return isclass(obj) and issubclass(obj, yuio.config.Config)


def can_document(obj):
    return (
        isapp(obj)
        or isconfig(obj)
        or isconfigfield(obj)
        or isenumclass(obj)
        or isenumattribute(obj)
    )


def find_module(path: list[str]) -> tuple[types.ModuleType, list[str]]:
    i = len(path)
    while i > 0:
        module = ".".join(path[:i])
        try:
            return importlib.import_module(module), path[i:]
        except ImportError:
            pass
        i -= 1

    obj = ".".join(path)
    raise ImportError(f"can't find module for object {obj}")


def config_getattr(obj: _t.Any, name: str):
    obj_kind = "object"
    attr_kind = "attribute"
    orig_obj = obj
    if isapp(obj):
        obj_kind = "app"
        attr_kind = "parameter"
        obj = obj._config_type
    elif isconfig(obj):
        obj_kind = "config"
        attr_kind = "field"
    elif isconfigfield(obj):
        if obj.is_subconfig:
            obj_kind = "config"
            attr_kind = "field"
            obj = obj.ty
            orig_obj = obj
        else:
            raise AttributeError(f"field {obj.qualname} is not a sub-config field")
    elif isenumattribute(obj):
        raise AttributeError(
            f"{obj_full_path(obj)} is an enum attribute; "
            "documenting members of enum attributes is not supported"
        )

    try:
        if isinstance(obj, type) and issubclass(obj, yuio.config.Config):
            res = getattr(obj, "_Config__get_fields")()[name]
        else:
            res = getattr(obj, name)
    except (AttributeError, KeyError):
        raise AttributeError(
            f"{obj_kind} {obj_full_path(orig_obj)} has no {attr_kind} {name!r}"
        ) from None

    if isenumclass(obj) and not isenumattribute(res):
        raise AttributeError(
            f"{obj_full_path(obj)} is an enum class, "
            f"yet its member {name} is not an enum attribute"
        )

    return res


def resolve(path: list[str]):
    root, path = find_module(path)
    objpath: list[object] = [root]
    for name in path:
        root = config_getattr(root, name)
        objpath.append(root)
    return objpath


def obj_full_path(obj: _t.Any) -> str:
    qualname = (
        getattr(obj, "__qualname__", None) or getattr(obj, "__name__", None) or ""
    )
    modname = getattr(obj, "__module__", "")
    return ".".join(filter(None, [modname, qualname]))


def extract_command_root_and_path(
    app: yuio.app.App[_t.Any], prog: str | None, location
):
    subcommand_names: list[str] = []
    while True:
        subcommand_names.append(app.prog or "")
        if app._parent is None:
            break
        else:
            app = app._parent
    subcommand_names.reverse()

    if prog:
        subcommand_names[0] = prog
    elif not subcommand_names[0]:
        subcommand_names[0] = "__main__"
        _logger.warning(
            "can't find program name for %s, "
            "please provide it explicitly by giving :prog: option "
            "to the cli:autoobject directive",
            obj_full_path(app),
            location=location,
        )

    return app, subcommand_names


def join_cmd_path(path: _t.Iterable[str]) -> str:
    return " ".join(re.sub(r"([\\\s])", r"\\\1", name) for name in path)


class DocstringTitleConverter(nodes.SparseNodeVisitor):
    def __init__(self, document: nodes.document) -> types.NoneType:
        self._level = 0
        super().__init__(document)

    def unknown_visit(self, node: nodes.Node):
        pass

    def unknown_departure(self, node: nodes.Node):
        pass

    def visit_section(self, node: nodes.section):
        self._level += 1

    def depart_section(self, node: nodes.section):
        self._level -= 1

    def visit_title(self, node: nodes.title):
        new_node = nodes.rubric("", "", *node.children, **node.attributes)
        new_node["classes"].extend(["cli-section", f"cli-section-{self._level}"])
        node.replace_self(new_node)
        raise nodes.SkipNode()


class AutodocUtilsMixin(CliContextManagerMixin):
    option_spec = {
        "flags": directives.flag,
        "env": directives.flag,
        "subcommands": directives.flag,
        "flag-prefix": directives.unchanged,
        "env-prefix": directives.unchanged,
        "name": directives.unchanged_required,
        "prog": directives.unchanged,
        "parent-command": directives.unchanged_required,
        "by-name": directives.flag,
        "no-by-name": directives.flag,
        "to-dash-case": directives.flag,
        "no-to-dash-case": directives.flag,
        **CliObject.option_spec,
    }

    def render_child(
        self,
        name: str,
        obj: _t.Any,
        is_root: bool = False,
        options_ext: dict[str, _t.Any] | None = None,
        as_opt: bool = False,
    ) -> list[nodes.Node]:
        if is_root:
            options = self.options.copy()
        else:
            options = self._prepare_child_options(name, obj)
        if options_ext:
            options.update(options_ext)
        if isapp(obj):
            directive = self._make_directive(
                AutodocAppObject, "cli:command", options, obj
            )
        elif isconfig(obj):
            directive = self._make_directive(
                AutodocConfigObject, "cli:config", options, obj
            )
        elif isconfigfield(obj):
            if as_opt:
                if obj.flags is yuio.POSITIONAL:
                    directive_name = "cli:argument"
                else:
                    directive_name = "cli:flag"
                directive = self._make_directive(
                    AutodocOptObject, directive_name, options, obj
                )
            elif obj.is_subconfig:
                directive = self._make_directive(
                    AutodocConfigObject, "cli:config", options, obj.ty
                )
            else:
                directive = self._make_directive(
                    AutodocFieldObject, "cli:field", options, obj
                )
        elif isenumclass(obj):
            directive = self._make_directive(
                AutodocEnumObject, "cli:config", options, obj
            )
        elif isenumattribute(obj):
            directive = self._make_directive(
                AutodocEnumeratorObject, "cli:field", options, obj
            )
        else:
            _logger.warning(
                "can't document python object %s: object of type %s is not supported",
                obj_full_path(obj),
                _t.type_repr(type(obj)),
                location=self.get_source_info(),
            )
            return []

        return directive.run()

    def _prepare_child_options(self, name: str, obj: object):
        options = self.options.copy()

        if isconfigfield(obj) and obj.is_subconfig:
            flag_prefix: str | yuio.Disabled = options.get("flag-prefix", "")
            if flag_prefix is not yuio.DISABLED and obj.flags not in (
                yuio.DISABLED,
                yuio.POSITIONAL,
            ):
                if flag_prefix:
                    flag_prefix = flag_prefix + "-" + obj.flags[0].lstrip("-")
                else:
                    flag_prefix = obj.flags[0]
            else:
                flag_prefix = yuio.DISABLED
            options["flag-prefix"] = flag_prefix

            env_prefix: str | yuio.Disabled = options.get("env-prefix", "")
            if env_prefix is not yuio.DISABLED and obj.env is not yuio.DISABLED:
                if env_prefix:
                    env_prefix += "_"
                env_prefix += obj.env
            else:
                env_prefix = yuio.DISABLED
            options["env-prefix"] = env_prefix

        options["name"] = name
        options["python-name"] = ".".join(
            filter(None, [self.ctx_python_path, self.make_python_name(obj)])
        )
        options.pop("annotation", None)
        options.pop("display-name", None)
        options.pop("parent-command", None)
        options.pop("enum", None)
        return options

    def _make_directive(
        self,
        ty: type[AutodocObject[T]],
        dirname: str,
        options: dict[str, _t.Any],
        obj: T,
    ) -> AutodocObject[T]:
        return ty(
            dirname,
            [],
            options,
            StringList(),
            self.lineno,
            self.content_offset,
            self.block_text,
            self.state,
            self.state_machine,
            obj,
        )

    def make_repr_ctx(self) -> yuio.string.ReprContext:
        ctx = yuio.string.ReprContext.make_dummy()
        ctx.width = 10000  # made a no wrapping, boss...
        return ctx

    def make_name(self, obj: object) -> str:
        if isapp(obj):
            return obj.wrapped.__name__
        elif isconfig(obj) or isenumclass(obj):
            return obj.__name__
        elif isenumattribute(obj):
            by_name = self.options.get(
                "by-name", getattr(type(obj), "__yuio_by_name__", False)
            )
            if by_name:
                name = obj.name
            else:
                name = str(obj.value)
            to_dash_case = self.options.get(
                "to-dash-case", getattr(type(obj), "__yuio_to_dash_case__", False)
            )
            if to_dash_case:
                name = yuio.util.to_dash_case(name)

            return name
        elif isconfigfield(obj):
            return obj.name
        else:
            assert False, obj

    def make_python_name(self, obj: object) -> str:
        if isapp(obj):
            return obj.wrapped.__name__
        elif isconfig(obj) or isenumclass(obj):
            return obj.__name__
        elif isenumattribute(obj) or isconfigfield(obj):
            return obj.name
        else:
            assert False, obj

    def push_python_path(
        self,
        python_path: str,
    ):
        python_paths = self.env.ref_context.setdefault("cli:python_paths", [])
        python_paths.append(self.env.ref_context.get("cli:python_path"))
        self.env.ref_context["cli:python_path"] = python_path

    def pop_python_path(self):
        python_paths = self.env.ref_context.setdefault("cli:python_paths", [])
        if python_paths:
            self.env.ref_context["cli:python_path"] = python_paths.pop()
        else:
            self.env.ref_context.pop("cli:python_path", None)

    @property
    def ctx_python_path(self) -> str:
        return self.env.ref_context.get("cli:python_path") or ""


class AutodocObject(AutodocUtilsMixin, CliObject, _t.Generic[T]):
    def __init__(
        self,
        name: str,
        arguments: list[str],
        options: dict[str, _t.Any],
        content: StringList,
        lineno: int,
        content_offset: int,
        block_text: str,
        state: RSTState,
        state_machine: RSTStateMachine,
        obj: T,
    ):
        super().__init__(
            name,
            arguments,
            options,
            content,
            lineno,
            content_offset,
            block_text,
            state,
            state_machine,
        )

        self.obj = obj

    def patch_document_title_ids(self):
        return patch_document_title_ids(
            self.ids[0] + "--" if self.ids else "", self.state.document
        )

    def nested_parse_docstring(self, docs: str, obj: _t.Any, what: str):
        if isconfigfield(obj):
            source = f"{what} of field {obj.qualname}"
        else:
            try:
                file = inspect.getfile(obj) + ":"
            except TypeError:
                file = ""
            source = f"{file}{what} of {obj_full_path(obj)}"

        lines = docs.splitlines()
        items = [(source, i) for i in range(len(lines))]
        content = StringList(lines, items=items, source=source)
        container = nodes.container()
        with (
            switch_source_input(self.state, content),
            self.patch_document_title_ids(),
        ):
            container += nested_parse_to_nodes(self.state, content)

        container.walkabout(DocstringTitleConverter(self.state.document))

        return container.children

    def nested_parse_inline(self, docs: str, obj: _t.Any, what: str = "docstring"):
        source = f"{what} of {obj!r}"

        docs = yuio.util.dedent(docs)
        lines = docs.splitlines()
        items = [(source, i) for i in range(len(lines))]
        content = StringList(lines, items=items, source=source)
        with switch_source_input(self.state, content):
            return self.parse_inline(docs, lineno=1)

    def get_signatures(self) -> list[str]:
        raise NotImplementedError()

    def before_content(self):
        self.push_python_path(self.options["python-name"])
        super().before_content()

    def after_content(self):
        super().after_content()
        self.pop_python_path()


class AutodocAppObject(AutodocObject[yuio.app.App[_t.Any]], CmdObject):
    def run(self) -> list[nodes.Node]:
        self.options.pop("env", None)
        self.options["flags"] = None

        return super().run()

    def get_signatures(self) -> list[str]:
        root, cmd_path = extract_command_root_and_path(
            self.obj, self.options.get("prog"), self.get_source_info()
        )
        self._root = root
        *self._cmd_prefix, self._cmd_name = cmd_path
        self._prog = " ".join(cmd_path)

        root_command = root._make_cli_command(root=True)
        subcommands: list[yuio.cli.Command[_t.Any]] = [root_command]
        for name in cmd_path[1:]:
            root_command = root_command.subcommands[name]
            subcommands.append(root_command)
        self._command = subcommands[-1]
        inherited_options: list[yuio.cli.Option[_t.Any]] = []
        for subcommand in subcommands[:-1]:
            inherited_options.extend(
                (
                    option
                    for option in subcommand.options
                    if option.flags is not yuio.POSITIONAL
                )
            )
        self._inherited_options = inherited_options

        self.collapsed_paths: set[str] = set()

        return [self._cmd_name] + (self.obj._aliases or [])

    _first_sig_paths = None

    def parse_signature(
        self, sig: str, signode: addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        cfg_path = parse_cfg_path(self.options["name"])
        cmd_path = CmdPath(self._cmd_prefix + [sig])
        if self._first_sig_paths is None:
            self._first_sig_paths = cfg_path, cmd_path
        else:
            cfg_path, main_cmd_path = self._first_sig_paths
            signode["cli:cmd_aliases"] = [cmd_path]
            signode["cli:toc_name"] = " ".join(cmd_path)
            cmd_path = main_cmd_path

        return cfg_path, cmd_path

    def _format_usage(self):
        formatter = yuio.cli._CliFormatter(
            self._root._make_help_parser(), self.make_repr_ctx()
        )
        usage_lines = formatter.format(
            yuio.cli._Usage(
                self._prog, self._command, self._inherited_options, prefix=""
            )
        )
        usage = "$ " + "\n".join(map(str, usage_lines)).replace("\n", "\n$ ")

        return nodes.literal_block("", usage, language="console")

    def _format_options(self):
        groups: dict[yuio.cli.HelpGroup, list[yuio.cli.Option[_t.Any]]] = {}
        for opt in self._command.options:
            if opt.flags is not yuio.POSITIONAL:
                continue
            if opt.help is yuio.DISABLED:
                continue
            group = opt.help_group or yuio.cli.ARGS_GROUP
            if group.help is yuio.DISABLED:
                continue
            if group not in groups:
                groups[group] = []
            groups[group].append(opt)

        res: list[nodes.Node] = []
        for group, options in groups.items():
            res.extend(self._format_arg_group(group, options))
        return res

    def _format_subcommands(self):
        subcommands: dict[yuio.cli.Command[_t.Any], list[str]] = {}
        for name, subcommand in self._command.subcommands.items():
            if subcommand.help is yuio.DISABLED:
                continue
            if subcommand not in subcommands:
                subcommands[subcommand] = [name]
            else:
                subcommands[subcommand].append(name)
        if not subcommands:
            return []
        group = yuio.cli.SUBCOMMANDS_GROUP
        section = _t.cast(nodes.section, self._format_arg_group(group, [])[0])

        subcommands_list = nodes.definition_list("")
        section += subcommands_list
        for subcommand, names in subcommands.items():
            assert subcommand.help is not yuio.DISABLED

            item = nodes.definition_list_item("")
            subcommands_list += item

            term = nodes.term("")
            item += term

            sep = False
            for name in names:
                if sep:
                    term += nodes.Text(", ")
                ref_target = f"{name} <{join_cmd_path(self.cmd_path + (name,))}>"
                ref_nodes, warn_nodes = CmdXRefRole()(
                    "cli:cmd", ref_target, ref_target, 0, self.state.inliner
                )
                term += ref_nodes
                term += warn_nodes
                sep = True

            sub_app = self.obj._subcommands[names[0]]
            body = nodes.definition(
                "",
                *self.nested_parse_docstring(subcommand.help, sub_app, what="help"),
            )
            item += body

        return [section]

    def _format_flags(self):
        groups: dict[
            yuio.cli.HelpGroup,
            tuple[list[yuio.cli.Option[_t.Any]], list[yuio.cli.Option[_t.Any]], int],
        ] = {}

        # TODO: to properly display inherited options, we need to track where they're
        # inherited from, in order to find relevant field.

        # for i, opt in enumerate(self._command.options + self._inherited_options):
        for opt in self._command.options:
            if not opt.flags:
                continue
            if opt.help is yuio.DISABLED:
                continue
            group = opt.help_group or yuio.cli.OPTS_GROUP
            if group.help is yuio.DISABLED:
                continue
            # is_inherited = i >= len(self._inherited_options)
            is_inherited = False
            if group not in groups:
                groups[group] = ([], [], 0)
            if opt.required or (opt.mutex_group and opt.mutex_group.required):
                groups[group][0].append(opt)
            elif is_inherited and not opt.show_if_inherited:
                required, optional, n_inherited = groups[group]
                groups[group] = required, optional, n_inherited + 1
            else:
                groups[group][1].append(opt)

        res: list[nodes.Node] = []
        for group, (required, optional, n_inherited) in groups.items():
            res.extend(self._format_arg_group(group, required + optional))
        return res

    def _format_arg_group(
        self, group: yuio.cli.HelpGroup, options: list[yuio.cli.Option[_t.Any]]
    ) -> list[nodes.Node]:
        assert group.help is not yuio.DISABLED

        section = nodes.section()
        section["name"] = nodes.fully_normalize_name(group.title)
        section["names"].append(section["name"])

        title, messages = self.nested_parse_inline(group.title, group, what="title")
        section += nodes.rubric(
            "", "", *title, *messages, classes=["cli-section", "cli-section-1"]
        )

        with self.patch_document_title_ids():
            self.state.document.note_implicit_target(section, section)

        if group.collapse:
            all_flags: set[str] = set()
            for option in options:
                all_flags.update(option.primary_long_flags or [])
            if len(all_flags) == 1:
                prefix = all_flags.pop()
            else:
                prefix = yuio.util.commonprefix(all_flags)
            if not prefix:
                prefix = "--*"
            elif prefix.endswith("-"):
                prefix += "*"
            else:
                prefix += "-*"

            path = group._slug or _cmd2cfg_part(group.title)

            section += self._format_field(
                yuio.config._Field(
                    name=path,
                    qualname=path,
                    default=yuio.MISSING,
                    parser=None,
                    help=group.help,
                    full_help=group.help,
                    env=yuio.DISABLED,
                    flags=[prefix],
                    is_subconfig=True,
                    ty=object,
                    required=False,
                    merge=None,
                    mutex_group=None,
                    help_group=None,
                    usage=None,
                    show_if_inherited=False,
                    option_ctor=None,
                    default_desc=None,
                ),
                None,
                path,
                prefix,
            )
        else:
            section += self.nested_parse_docstring(group.help, group, what="help")
            for option in options:
                section += self._format_option(option)

        return [section]

    def _format_option(self, option: yuio.cli.Option[_t.Any]) -> list[nodes.Node]:
        field = self.obj

        path = ""
        cfg_path = self.cfg_path
        for name in option.dest.split("."):
            if path:
                path += "."
            path += name
            cfg_path += (name,)

            if field is not None:
                try:
                    field = config_getattr(field, name)
                except AttributeError:
                    if not name.startswith("_"):
                        _logger.warning(
                            "failed to get option %s from app %s",
                            path,
                            obj_full_path(self.obj),
                            location=self.get_source_info(),
                        )
                    field = None

        if field is None:
            field = yuio.config._Field(
                name=path,
                qualname=path,
                default=getattr(option, "default", None),
                parser=getattr(option, "parser", None),
                help=option.help,
                full_help=option.help or "",
                env=yuio.DISABLED,
                flags=option.flags,
                is_subconfig=False,
                ty=object,
                required=option.required,
                merge=getattr(option, "merge", None),
                mutex_group=option.mutex_group,
                help_group=option.help_group,
                usage=option.usage,
                show_if_inherited=option.show_if_inherited,
                option_ctor=None,
                default_desc=option.default_desc,
            )

        if not isconfigfield(field):
            _logger.warning(
                "failed to get option %s from app %s: expected a field, got %s",
                path,
                obj_full_path(self.obj),
                _t.type_repr(type(field)),
                location=self.get_source_info(),
            )
            return []

        return self._format_field(field, option, path, None)

    def _format_field(
        self,
        field: yuio.config._Field,
        option: yuio.cli.Option[_t.Any] | None,
        path: str,
        display_name: str | None,
    ):
        options_ext: dict[str, _t.Any] = {"__option": option}

        if display_name is not None:
            options_ext["display-name"] = display_name

        return self.render_child(path, field, options_ext=options_ext, as_opt=True)

    def _format_prolog(self):
        docs = self.obj.description
        if not docs:
            return []

        return self.nested_parse_docstring(docs, self.obj, what="doc_description")

    def _format_epilog(self):
        docs = self.obj.epilog
        if not docs:
            return []

        return self.nested_parse_docstring(docs, self.obj, what="epilog")

    def transform_content(self, content_node: addnodes.desc_content):
        content_node += self._format_usage()
        content_node += self._format_prolog()
        content_node += self._format_options()
        content_node += self._format_subcommands()
        content_node += self._format_flags()
        content_node += self._format_epilog()
        return super().transform_content(content_node)


class AutodocBaseFieldObject(AutodocObject[yuio.config._Field]):
    all_flags = False

    def _make_option(self):
        option: yuio.cli.Option[_t.Any] | None = self.options.get("__option")

        if option is None:
            if self.obj.flags is yuio.DISABLED:
                return None
            if self.obj.is_subconfig:
                return None
            if self.obj.parser is None:
                return None

            option_ctor = self.obj.option_ctor or yuio.config._default_option

            flags = self.obj.flags
            prefix = self.options.get("flag-prefix", "")
            if prefix is yuio.DISABLED:
                return None
            if prefix and flags is not yuio.POSITIONAL:
                prefix += "-"
                flags = [prefix + flag.lstrip("-") for flag in flags]

            option = option_ctor(
                yuio.config.OptionSettings(
                    name=self.obj.name,
                    qualname=self.obj.qualname,
                    parser=self.obj.parser,
                    flags=flags,
                    required=self.obj.required,
                    mutex_group=self.obj.mutex_group,
                    usage=self.obj.usage if self.obj.usage is not None else True,
                    help=self.obj.full_help,
                    help_group=(self.obj.help_group or None),
                    show_if_inherited=self.obj.show_if_inherited or False,
                    merge=self.obj.merge,
                    dest="_dummy_dest",
                    default=self.obj.default,
                    default_desc=self.obj.default_desc,
                    long_flag_prefix=prefix or "--",
                )
            )

        return option

    def _find_field_list(self, content_node: addnodes.desc_content):
        for node in content_node:
            if isinstance(node, nodes.field_list):
                return node
        field_list = nodes.field_list()
        content_node += field_list
        return field_list

    def _render_flags(
        self, field_list: nodes.field_list, option: yuio.cli.Option[_t.Any] | None
    ):
        if not option:
            return

        if option.flags is yuio.POSITIONAL:
            return

        flags = []
        if option.primary_short_flag:
            flags.append(option.primary_short_flag)
        if option.primary_long_flags:
            flags.extend(option.primary_long_flags)
        metavar = str(option.format_metavar(self.make_repr_ctx()))

        for flag in flags:
            if isinstance(flag, tuple):
                flag, description = flag
            else:
                description = None
            flag = str(flag)
            field = nodes.field(
                "",
                nodes.field_name("", f"flag {flag}{metavar}"),
            )
            field_list += field

            if description:
                field += nodes.field_body("", nodes.Text(description))
            else:
                field += nodes.field_body("")

    def _render_flag_aliases(
        self, field_list: nodes.field_list, option: yuio.cli.Option[_t.Any] | None
    ):
        if not option:
            return

        aliases = option.format_alias_flags(self.make_repr_ctx(), all=self.all_flags)

        for alias in aliases or []:
            if isinstance(alias, tuple):
                alias, description = alias
            else:
                description = None
            alias = str(alias)
            field = nodes.field(
                "",
                nodes.field_name("", f"flag-alias {alias}"),
            )
            field_list += field

            if description:
                field += nodes.field_body("", nodes.Text(description))
            else:
                field += nodes.field_body("")

    def _render_env_vars(self, field_list: nodes.field_list):
        if self.obj.env is yuio.DISABLED:
            return
        env = self.obj.env
        prefix = self.options.get("env-prefix", "")
        if prefix:
            env = f"{prefix}_{env}"
        field_list += nodes.field(
            "",
            nodes.field_name("", f"env {env}"),
            nodes.field_body(""),
        )

    def _render_flag_defaults(
        self, field_list: nodes.field_list, option: yuio.cli.Option[_t.Any] | None
    ):
        if not option:
            return

        default = option.format_default(self.make_repr_ctx(), all=self.all_flags)
        if not default:
            return

        field = nodes.field(
            "",
            nodes.field_name("", "default"),
            nodes.field_body("", nodes.literal("", str(default))),
        )
        field_list += field


class AutodocOptObject(AutodocBaseFieldObject, OptObject):
    def get_signatures(self) -> list[str]:
        self._option = self._make_option()

        self._primary_flags: list[str] = []
        self._primary_flag: str = ""

        if self._option and self._option.flags is not yuio.POSITIONAL:
            if self._option.primary_short_flag:
                self._primary_flag = self._option.primary_short_flag
                self._primary_flags.append(self._option.primary_short_flag)
            if self._option.primary_long_flags:
                self._primary_flag = self._option.primary_long_flags[0]
                self._primary_flags.extend(self._option.primary_long_flags)

        return [""]

    def parse_signature(
        self, sig: str, signode: addnodes.desc_signature
    ) -> tuple[CfgPath, CmdPath | None]:
        cfg_path = parse_cfg_path(self.options["name"])

        if not self._option:
            cmd_path = None
        elif self._option.flags is yuio.POSITIONAL:
            metavar = self._option.nth_metavar(0)
            cmd_path = CmdPath((metavar,))
            signode["cli:page_name"] = metavar
            signode["cli:toc_name"] = metavar
        elif self._primary_flag:
            cmd_path = CmdPath((self._primary_flag,))
            signode["cli:page_name"] = ", ".join(self._primary_flags)
            signode["cli:toc_name"] = self._primary_flag
            signode["cli:cmd_aliases"] = [
                self.cmd_path + (name,)
                for name in self._primary_flags
                if name != self._primary_flag
            ]
            signode["cli:suffix"] = str(
                self._option.format_metavar(self.make_repr_ctx())
            )
        else:
            cmd_path = None

        return cfg_path, cmd_path

    def signature_add_annotations(self, sig: str, signode: addnodes.desc_signature):
        super().signature_add_annotations(sig, signode)

        if self.obj.required and self.obj.flags is not yuio.POSITIONAL:
            signode += [
                addnodes.desc_sig_keyword("required", "required"),
                addnodes.desc_sig_space(),
            ]

    def _render_default(self):
        if (
            self.obj.parser
            and "flags-only" not in self.options
            and "post-annotation" not in self.options
        ):
            return []
        if not self._option:
            return []

        default = self._option.format_default(self.make_repr_ctx(), all=self.all_flags)
        if not default:
            return []

        return nodes.field_list(
            "",
            nodes.field(
                "",
                nodes.field_name("", "default"),
                nodes.field_body("", nodes.literal("", str(default))),
            ),
        )

    def transform_content(self, content_node: addnodes.desc_content):
        if help := self.obj.full_help:
            content_node += self.nested_parse_docstring(help, self.obj, "help")

        field_list = self._find_field_list(content_node)
        self._render_flag_aliases(field_list, self._option)
        self._render_flag_defaults(field_list, self._option)
        if not field_list.children:
            field_list.replace_self([])

        return super().transform_content(content_node)


class AutodocConfigObject(
    AutodocObject[type[yuio.config.Config]],
    ConfigObject,
):
    def get_signatures(self) -> list[str]:
        return [self.options["name"]]

    def transform_content(self, content_node: addnodes.desc_content):
        if help := self.obj.__doc__:
            help = yuio.util.dedent(help)
            content_node += self.nested_parse_docstring(help, self.obj, "docstring")
        for name, field in getattr(self.obj, "_Config__get_fields")().items():
            if field.help is not yuio.DISABLED:
                content_node += self.render_child(name, field)
        return super().transform_content(content_node)


class AutodocFieldObject(AutodocBaseFieldObject, FieldObject):
    all_flags = True

    def get_signatures(self) -> list[str]:
        return [self.options["name"]]

    def signature_add_post_annotations(
        self, sig: str, signode: addnodes.desc_signature
    ):
        if self.obj.parser:
            post_annotation = ""
            schema = self.obj.parser.to_json_schema(
                yuio.json_schema.JsonSchemaContext()
            ).remove_opaque()
            if schema:
                post_annotation += f": {schema.pprint()}"
            if self.obj.default is not yuio.MISSING:
                default = self.obj.parser.to_json_value(self.obj.default)
                post_annotation += " = " + json.dumps(default, ensure_ascii=False)

            signode += type_to_nodes(
                post_annotation, self.state.inliner, xref_role="cli:_auto"
            )

    def transform_content(self, content_node: addnodes.desc_content):
        if help := self.obj.full_help:
            content_node += self.nested_parse_docstring(help, self.obj, "help")

        field_list = self._find_field_list(content_node)
        if "flags" in self.options:
            option = self._make_option()
            self._render_flags(field_list, option)
            self._render_flag_aliases(field_list, option)
        if "env" in self.options:
            self._render_env_vars(field_list)
        if not field_list.children:
            field_list.replace_self([])

        return super().transform_content(content_node)


class AutodocEnumObject(
    AutodocObject[type[enum.Enum]],
    ConfigObject,
):
    def get_signatures(self) -> list[str]:
        self.options["enum"] = None
        return [self.options["name"]]

    def transform_content(self, content_node: addnodes.desc_content):
        if help := self.obj.__doc__:
            help = yuio.util.dedent(help)
            content_node += self.nested_parse_docstring(help, self.obj, "docstring")
        for field in self.obj:
            content_node += self.render_child(self.make_name(field), field)
        return super().transform_content(content_node)


class AutodocEnumeratorObject(AutodocObject[enum.Enum], FieldObject):
    def get_signatures(self) -> list[str]:
        return [self.options["name"]]

    def transform_content(self, content_node: addnodes.desc_content):
        docs = yuio.util.find_docs(type(self.obj))
        if help := docs.get(self.obj.name):
            content_node += self.nested_parse_docstring(help, self.obj, "docstring")
        return super().transform_content(content_node)


class AutodocDirective(AutodocUtilsMixin):
    optional_arguments = 0
    required_arguments = 1
    final_argument_whitespace = True
    has_content = True

    def __init__(
        self,
        name: str,
        arguments: list[str],
        options: dict[str, _t.Any],
        content: StringList,
        lineno: int,
        content_offset: int,
        block_text: str,
        state: RSTState,
        state_machine: RSTStateMachine,
        *,
        obj_data: tuple[list[object], object] | yuio.Missing = yuio.MISSING,
    ) -> types.NoneType:
        super().__init__(
            name,
            arguments,
            options,
            content,
            lineno,
            content_offset,
            block_text,
            state,
            state_machine,
        )

        self.obj_data: tuple[list[object], object] | yuio.Missing = obj_data

    def run(self) -> list[nodes.Node]:
        signatures = self.get_signatures()

        if not signatures:
            raise self.error("got an empty object name")
        elif len(signatures) > 1:
            raise self.error(f"got multiple object names: {signatures}")

        if self.obj_data is yuio.MISSING:
            path, objects = self.load(signatures[0])
            parents, obj = self.resolve(objects)
        else:
            parents, obj = self.obj_data
            path = obj_full_path(obj)

        if "flag-prefix" not in self.options:
            self.options["flag-prefix"] = self._make_flag_prefix(parents)

        if "env-prefix" not in self.options:
            self.options["env-prefix"] = self._make_env_prefix(parents)

        if "name" in self.options:
            name = self.options["name"]
        else:
            name = self.make_name(obj)

        res = self.render_child(
            name,
            obj,
            is_root=True,
            options_ext={
                "python-name": path,
                "name": name,
            },
            as_opt=bool(parents) and isapp(parents[0]),
        )

        if isapp(obj) and "subcommands" in self.options:
            for subcommand in obj._ordered_subcommands:
                if subcommand.help is yuio.DISABLED:
                    continue
                directive = AutodocDirective(
                    self.name,
                    self.arguments,
                    self.options,
                    self.content,
                    self.lineno,
                    self.content_offset,
                    self.block_text,
                    self.state,
                    self.state_machine,
                    obj_data=(
                        parents + [obj],
                        subcommand,
                    ),
                )
                res.extend(directive.run())

        return res

    def get_signatures(self):
        return CliObject.get_signatures(self)  # type: ignore

    def load(self, path: str):
        path = path.strip()

        if not path:
            raise self.error("got an empty object path")

        try:
            return path, resolve(path.split("."))
        except (ImportError, AttributeError) as e:
            raise self.error(f"can't find python object {path}: {e}")

    def resolve(self, objects: list[object]):
        assert objects

        path_start = 0
        for obj in objects:
            if can_document(obj):
                break
            path_start += 1

        if path_start == len(objects):
            raise self.error(
                f"can't document object {obj_full_path(objects[-1])}: "
                f"unsupported type {_t.type_repr(type(objects[-1]))}"
            )

        parents = objects[path_start:-1]
        obj = objects[-1]

        # Sanity check parents path.
        if parents:
            if isenumclass(parents[0]):
                # `config_getattr` doesn't allow indexing into enum attributes,
                # so this assert should always hold.
                assert len(parents) == 1
                assert isenumattribute(obj)
            else:
                # we known that `can_document(parents[0])` is `True`, so `parents[0]`
                # can be an app, a config, or a field. `config_getattr` always returns
                # fields from these objects, so this assert should always hold.
                assert all(
                    isconfigfield(parent) and parent.is_subconfig
                    for parent in parents[1:]
                )
                assert isconfigfield(obj)

        return parents, obj

    def _make_env_prefix(self, parents: list[object]):
        env_path = []
        for parent in parents:
            if isconfigfield(parent):
                if parent.env is yuio.DISABLED:
                    return yuio.DISABLED
                elif parent.env:
                    env_path.append(parent.env)

        return "_".join(filter(None, env_path))

    def _make_flag_prefix(self, parents: list[object]):
        flag_path = []
        for parent in parents:
            if isconfigfield(parent):
                if parent.flags is yuio.DISABLED:
                    return yuio.DISABLED
                elif parent.flags and parent.flags[0]:
                    flag_path.append(parent.flags[0].lstrip("-"))

        if flag_path:
            return "--" + "-".join(flag_path)
        else:
            return ""
