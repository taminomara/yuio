from __future__ import annotations

import enum
import functools
import json
import operator
import re
import typing as _t

import docutils.nodes
import sphinx.addnodes
import sphinx.application
from docutils.parsers.rst import directives
from sphinx.addnodes import desc_signature
from sphinx.domains.python import PyAttribute, PyClasslike, PyXRefRole
from sphinx.ext.autodoc import AttributeDocumenter, ClassDocumenter, bool_option
from sphinx.ext.autodoc.mock import ismock
from sphinx.util.docstrings import separate_metadata
from sphinx.util.inspect import isenumattribute, object_description

import yuio
import yuio.config
import yuio.json_schema

_TYPE_PARSE_RE = re.compile(
    r"""
    # Skip spaces, they're not meaningful in this context.
    \s+
    |
    (?P<dots>[.]{3})
    |
    # Literal string with escapes.
    # Example: `"foo"`, `"foo-\"-bar"`.
    (?P<string>(?P<string_q>['"`])(?:\\.|[^\\])*?(?P=string_q))
    |
    # Number with optional exponent.
    # Example: `1.0`, `.1`, `1.`, `1e+5`.
    (?P<number>(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)
    |
    # Built-in type.
    # Example: `string`, `string?`.
    (?P<type>null|true|false|boolean|integer|number|string|any|never|object|set|array)\b
    \s*(?P<type_qm>\??)\s*
    |
    # Name component.
    (?P<name>\w[\w.#-]*)
    |
    # Punctuation that we separate with spaces.
    (?P<punct>[=:,|&])
    |
    # Punctuation that we copy as-is, without adding spaces.
    (?P<other_punct>[-!#$%()*+/;<>?@[\]^_{}~]+)
    |
    # Anything else is copied as-is.
    (?P<other>.)
    """,
    re.VERBOSE,
)


def type_to_nodes(typ: str, inliner) -> list[docutils.nodes.Node]:
    res = []

    for match in _TYPE_PARSE_RE.finditer(typ):
        if text := match.group("dots"):
            res.append(sphinx.addnodes.desc_sig_name(text, text))
        elif text := match.group("string"):
            res.append(sphinx.addnodes.desc_sig_literal_string(text, text))
        elif text := match.group("number"):
            res.append(sphinx.addnodes.desc_sig_literal_number(text, text))
        elif text := match.group("type"):
            res.append(sphinx.addnodes.desc_sig_keyword_type(text, text))
            if qm := match.group("type_qm"):
                res.append(sphinx.addnodes.desc_sig_punctuation(qm, qm))
        elif text := match.group("name"):
            text = "~" + text
            ref_nodes, warn_nodes = PyXRefRole(
                innernodeclass=sphinx.addnodes.desc_sig_name
            )("py:obj", text, text, 0, inliner)
            res.extend(ref_nodes)
            res.extend(warn_nodes)
        elif text := match.group("punct"):
            if text in "=|&":
                res.append(sphinx.addnodes.desc_sig_space())
            res.append(sphinx.addnodes.desc_sig_punctuation(text, text))
            res.append(sphinx.addnodes.desc_sig_space())
        elif text := match.group("other_punct"):
            res.append(sphinx.addnodes.desc_sig_punctuation(text, text))
        elif text := match.group("other"):
            res.append(docutils.nodes.Text(text))

    return res


def _get_fields(
    config: yuio.config.Config | type[yuio.config.Config],
) -> dict[str, yuio.config._Field]:
    return getattr(config, "_Config__get_fields")()


class Config(PyClasslike):
    option_spec = PyClasslike.option_spec.copy()
    option_spec["is-subconfig"] = directives.flag
    option_spec["display-name"] = directives.unchanged

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        result = super().handle_signature(sig, signode)

        if canonical_name := self.options.get("display-name"):
            for node in signode.findall(sphinx.addnodes.desc_name):
                node.clear()
                node += docutils.nodes.Text(canonical_name)
            for node in signode.findall(sphinx.addnodes.desc_addname):
                node.parent.replace(node, [])

        return result

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        if canonical_name := self.options.get("display-name"):
            return (canonical_name,)
        else:
            return super()._object_hierarchy_parts(sig_node)

    def _toc_entry_name(self, sig_node: desc_signature) -> str:
        if canonical_name := self.options.get("display-name"):
            return canonical_name
        else:
            return super()._toc_entry_name(sig_node)

    def get_signature_prefix(self, sig: str):
        if "is-subconfig" in self.options:
            return []
        else:
            return super().get_signature_prefix(sig)


class ConfigDocumenter(ClassDocumenter):
    objtype = "config"

    option_spec = ClassDocumenter.option_spec.copy()
    option_spec["enum-by-name"] = bool_option
    option_spec["enum-to-dash-case"] = bool_option
    option_spec["display-name"] = directives.unchanged

    @classmethod
    def can_document_member(
        cls, member: _t.Any, membername: str, isattr: bool, parent: _t.Any
    ):
        return (
            isinstance(parent, ConfigDocumenter)
            and isinstance(member, type)
            and issubclass(member, yuio.config.Config)
        )

    def format_signature(self, **kwargs) -> str:
        return ""

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)
        if ret and (
            isinstance(self.parent, type)
            and issubclass(self.parent, yuio.config.Config)
        ):
            self.doc_as_attr = False
            self.is_nested_config = True
        else:
            self.is_nested_config = False
        return ret

    def add_directive_header(self, sig: str):
        super().add_directive_header(sig)
        if self.is_nested_config:
            self.add_line("   :is-subconfig:", self.get_sourcename())
        if self.options.display_name:
            self.add_line(
                "   :display-name: " + self.options.display_name, self.get_sourcename()
            )


class Field(PyAttribute):
    option_spec = PyAttribute.option_spec.copy()
    option_spec["display-name"] = directives.unchanged

    def handle_signature(self, sig: str, signode: desc_signature) -> tuple[str, str]:
        fullname, prefix = super(PyAttribute, self).handle_signature(sig, signode)

        if canonical_name := self.options.get("display-name"):
            for node in signode.findall(sphinx.addnodes.desc_name):
                node.clear()
                node += docutils.nodes.Text(canonical_name)

        typ = self.options.get("type")
        if typ:
            annotations = type_to_nodes(typ, self.state.inliner)
            signode += sphinx.addnodes.desc_annotation(
                typ,
                "",
                sphinx.addnodes.desc_sig_punctuation("", ":"),
                sphinx.addnodes.desc_sig_space(),
                *annotations,
            )

        value = self.options.get("value")
        if value:
            signode += sphinx.addnodes.desc_annotation(
                value,
                "",
                sphinx.addnodes.desc_sig_space(),
                sphinx.addnodes.desc_sig_punctuation("", "="),
                sphinx.addnodes.desc_sig_space(),
                docutils.nodes.Text(value),
            )

        return fullname, prefix

    def _object_hierarchy_parts(self, sig_node: desc_signature) -> tuple[str, ...]:
        parts = super()._object_hierarchy_parts(sig_node)
        if parts and (canonical_name := self.options.get("display-name")):
            parts = parts[:-1] + (canonical_name,)
        return parts

    def _toc_entry_name(self, sig_node: desc_signature) -> str:
        if not sig_node.get("_toc_parts"):
            return ""

        config = self.config
        *parents, name = sig_node["_toc_parts"]
        if config.toc_object_entries_show_parents == "domain":
            return name
        if config.toc_object_entries_show_parents == "hide":
            return name
        if config.toc_object_entries_show_parents == "all":
            return ".".join([*parents, name])
        return ""


class FieldDocumenter(AttributeDocumenter):
    objtype = "field"

    option_spec = AttributeDocumenter.option_spec.copy()
    option_spec["enum-by-name"] = bool_option
    option_spec["enum-to-dash-case"] = bool_option

    @classmethod
    def can_document_member(
        cls, member: _t.Any, membername: str, isattr: bool, parent: _t.Any
    ):
        return super().can_document_member(member, membername, isattr, parent) and (
            isinstance(parent, ConfigDocumenter)
        )

    def should_suppress_directive_header(self) -> bool:
        return True

    def add_directive_header(self, sig: str):
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if self.options.annotation:
            self.add_line("   :annotation: " + self.options.annotation, sourcename)
            return

        if not isinstance(self.parent, type):
            return
        if issubclass(self.parent, yuio.config.Config):
            if field := _get_fields(self.parent).get(self.object_name):
                self._add_header_for_field(field)
        elif issubclass(self.parent, enum.Enum):
            enumerator = getattr(self.parent, self.object_name, None)
            if enumerator and isenumattribute(enumerator):
                self._add_header_for_enum_field(enumerator)

    def _add_header_for_field(self, field: yuio.config._Field):
        if field.is_subconfig:
            return
        assert field.parser
        sourcename = self.get_sourcename()

        doc = self.get_doc() or []
        _, metadata = separate_metadata(
            "\n".join(functools.reduce(operator.iadd, doc, []))
        )
        if "hide-value" in metadata:
            return True

        if "type" in metadata:
            self.add_line("   :type: " + metadata["type"], sourcename)
        elif self.config.autodoc_typehints != "none":
            schema = field.parser.to_json_schema(
                yuio.json_schema.JsonSchemaContext()
            ).remove_opaque()
            if schema is not None:
                self.add_line("   :type: " + schema.pprint(), sourcename)

        if "value" in metadata:
            self.add_line("   :value: " + metadata["value"], sourcename)
        else:
            try:
                if (
                    self.options.no_value
                    or field.default is yuio.MISSING
                    or self.should_suppress_value_header()
                    or ismock(self.object)
                ):
                    pass
                else:
                    try:
                        objrepr = json.dumps(field.parser.to_json_value(field.default))
                    except TypeError:
                        objrepr = object_description(field.default)
                    self.add_line("   :value: " + objrepr, sourcename)
            except ValueError:
                pass

    def _add_header_for_enum_field(self, enumerator: enum.Enum):
        enum_by_name = self.options.enum_by_name
        enum_to_dash_case = self.options.enum_to_dash_case
        if enum_by_name:
            name = enumerator.name
        else:
            name = str(enumerator.value)
        if enum_to_dash_case:
            name = yuio.to_dash_case(name)
        self.add_line("   :display-name: " + name, self.get_sourcename())


def setup(app: sphinx.application.Sphinx):
    app.add_directive_to_domain("py", "config", Config)
    app.add_directive_to_domain("py", "field", Field)
    app.add_autodocumenter(ConfigDocumenter)
    app.add_autodocumenter(FieldDocumenter)

    return {
        "version": yuio.__version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
