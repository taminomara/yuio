# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
A Sphinx_ extension for documenting yuio configs.

.. _Sphinx: https://www.sphinx-doc.org/


Installation
------------

Add ``sphinx.ext.autodoc`` and ``yuio.ext.sphinx`` to the list of extensions
in your ``conf.py``:

.. code-block:: python

    extensions = [
        "sphinx.ext.autodoc",
        "yuio.ext.sphinx",
    ]

You'll get four new directives in Python domain: :rst:dir:`py:config`,
:rst:dir:`py:field`, :rst:dir:`py:autoconfig`, :rst:dir:`py:autofield`,
that work with Python Autodoc. You'll also get a new role :rst:role:`flag`
for rendering CLI arguments.


Directives
----------

.. rst:directive:: .. py:config:: name

    This directive is derived from :rst:dir:`py:class`; it allows documenting Yuio
    configs and enums. It adds a few options helpful when working with Yuio objects:

    .. rst:directive:option:: subconfig

        If set, this flag disables rendering ``config`` annotation before
        config's name. This is useful when documenting nested configs
        within their parent configs:

        .. code-block:: rst

            .. py:config:: AppConfig

               Application's config.

               .. py:config:: executor
                  :subconfig:

                  Options related to executor.

        .. dropdown:: Example output

            .. py:config:: AppConfig
               :no-index:

               Application's config.

               .. py:config:: executor
                  :no-index:
                  :subconfig:

                  Options related to executor.

    .. rst:directive:option:: display-name: <name>

        Replaces name of the Python class with arbitrary string when rendering
        config. Cross-references and link anchors should still use python name:

        .. code-block:: rst

            .. py:config:: AppConfig
               :display-name: .app-config.yaml

               Application's config.

            You should refer to config using its python name: :py:class:`AppConfig`.

        .. dropdown:: Example output

            .. py:config:: AppConfig
               :no-contents-entry:
               :display-name: .app-config.yaml

               Application's config.

            You should refer to config using its python name: :py:class:`AppConfig`.

    .. rst:directive:option:: flag-prefix: <prefix>

        Adds prefix to all flags rendered in this config:

        .. code-block:: rst

            .. py:config:: AppConfig
               :flag-prefix: cfg

               Application's config.

               .. py:field:: input
                  :flag: --input

                  Input file, default is ``input.txt``.

        .. dropdown:: Example output

            .. py:config:: AppConfig
               :no-index:
               :flag-prefix: cfg

               Application's config.

               .. py:field:: input
                  :no-index:
                  :flag: --input

                  Input file, default is ``input.txt``.

    .. rst:directive:option:: env-prefix: <prefix>

        Adds prefix to all environment variables rendered in this config:

        .. code-block:: rst

            .. py:config:: AppConfig
               :env-prefix: YUIO

               Application's config.

               .. py:field:: input
                  :env: INPUT
                  :env-value: <path>

                  Input file, default is ``input.txt``.

        .. dropdown:: Example output

            .. py:config:: AppConfig
               :no-index:
               :env-prefix: YUIO

               Application's config.

               .. py:field:: input
                  :no-index:
                  :env: INPUT
                  :env-value: <path>

                  Input file, default is ``input.txt``.

.. rst:directive:: .. py:field:: name

    This directive is derived from :rst:dir:`py:attribute`; it allows documenting
    config and enum fields.

    The main difference is that it allows rendering CLI arguments and environment
    variables from where this field is loaded. Also, field types are specified using
    TypeScript syntax; this is so that they're more consistent with
    Json schema descriptions.

    .. rst:directive:option:: display-name: <name>

        Similar to :rst:dir:`py:config`, this option changes object's displayed name.
        Cross-references should still use full python name.

        This is especially useful when documenting enums that form parts of config
        values; you can change enumerator's name from its python identifier
        to the one expected by the corresponding parser:

        .. code-block:: rst

            .. py:config:: LoggingLevel

               .. py:field:: ERROR
                  :display-name: err

               .. py:field:: WARNING
                  :display-name: warn

               .. py:field:: INFO
                  :display-name: info

        .. dropdown:: Example output

            .. py:config:: LoggingLevel
               :no-index:

               .. py:field:: ERROR
                  :no-index:
                  :display-name: err

               .. py:field:: WARNING
                  :no-index:
                  :display-name: warn

               .. py:field:: INFO
                  :no-index:
                  :display-name: info

    .. rst:directive:option:: flag: <flag-names>

        Adds info about CLI flag from which this option will be parsed:

        .. code-block:: rst

            .. py:field:: strict
               :flag: -s --strict --no-strict

        .. dropdown:: Example output

            .. py:field:: strict
               :no-index:
               :flag: -s --strict --no-strict

    .. rst:directive:option:: flag-value

        Adds expected value for a flag:

        .. code-block:: rst

            .. py:field:: strict
               :flag: --strict
               :flag-value: yes|no

        .. dropdown:: Example output

            .. py:field:: strict
               :no-index:
               :flag: --strict
               :flag-value: yes|no

    .. rst:directive:option:: env

        Adds info about environment variable from which this option will be parsed:

        .. code-block:: rst

            .. py:field:: strict
               :env: STRICT

        .. dropdown:: Example output

            .. py:field:: strict
               :no-index:
               :env: STRICT

    .. rst:directive:option:: env-value

        Adds expected value for an environment variable:

        .. code-block:: rst

            .. py:field:: strict
               :env: STRICT
               :env-value: yes|no

        .. dropdown:: Example output

            .. py:field:: strict
               :no-index:
               :env: STRICT
               :env-value: yes|no


Autodoc directives
------------------

.. rst:directive:: .. autoconfig:: name

    This directive works similarly to :rst:dir:`autoclass`. It's best suited for
    documenting Yuio configs and enums.

    .. rst:directive:option:: display-name: <name>

        Will set display name for this config. See :rst:dir:`py:config:display-name`
        for examples.

    .. rst:directive:option:: show-flags
                              flag-prefix: <prefix>

        Automatically shows flags for all nested fields and configs. If given,
        :rst:dir:`:flag-prefix: <autoconfig:flag-prefix>` will be added to all
        flags, as if it was specified on the `~yuio.app.App`\\ s argument that parses
        this config.

    .. rst:directive:option:: show-env
                              env-prefix: <prefix>

        Automatically shows environment variables for all nested fields and configs.
        If given, :rst:dir:`:env-prefix: <autoconfig:env-prefix>` will be added to all
        variables, as if it was specified on the `~yuio.app.App`\\ s argument that
        parses this config.

    .. rst:directive:option:: enum-by-name
                              enum-to-dash-case

        These flags work when documenting python :class:`~enum.Enum`\\ s.
        They correspond to :class:`enum parser's <yuio.parse.Enum>` ``by_name``
        and ``to_dash_case`` arguments.

.. rst:directive:: .. autofield:: name

    Once again, this directive is based on :rst:dir:`autoattribute` with
    a few additional options:

    .. rst:directive:option:: show-flags
                              show-env
                              enum-by-name
                              enum-to-dash-case

        Same as corresponding options from :rst:dir:`autoconfig`.


Autodoc example
---------------

.. tab-set::

    .. tab-item:: Output

        .. autoconfig:: config_example.AppConfig
           :display-name: config.yaml
           :show-flags:
           :flag-prefix: cfg
           :members:

        .. autoconfig:: config_example.LogLevel
           :enum-by-name:
           :enum-to-dash-case:
           :members:

    .. tab-item:: RST

        .. code-block:: rst

            .. autoconfig:: config_example.AppConfig
               :display-name: config.yaml
               :show-flags:
               :flag-prefix: cfg
               :members:

            .. autoconfig:: config_example.LogLevel
               :enum-by-name:
               :enum-to-dash-case:
               :members:

    .. tab-item:: Python

        .. literalinclude:: /_code/config_example.py
           :language: python


Roles
-----

.. rst:role:: flag

    This directive adds the new ``flag`` role for rendering CLI options and flags.
    It uses styles from :rst:role:`kbd`, which is consistent with how Sphinx
    renders `option lists`__.

    __ https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html#option-lists

    Example:

    .. code-block:: rst

        Use the :flag:`--quiet` flag to suppress output.

    .. dropdown:: Example output

        Use the :flag:`--quiet` flag to suppress output.

"""

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
from sphinx.util.docutils import SphinxRole
from sphinx.util.inspect import isenumattribute, object_description

import yuio
import yuio.config
import yuio.json_schema
import yuio.parse

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
    option_spec["subconfig"] = bool_option
    option_spec["display-name"] = directives.unchanged
    option_spec["flag-prefix"] = directives.unchanged
    option_spec["env-prefix"] = directives.unchanged

    def before_content(self):
        flag_prefixes = self.env.ref_context.setdefault("py:yuio:flag_prefixes", [])
        if "flag-prefix" in self.options:
            flag_prefixes.append(self.options["flag-prefix"])
        env_prefixes = self.env.ref_context.setdefault("py:yuio:env_prefixes", [])
        if "env-prefix" in self.options:
            env_prefixes.append(self.options["env-prefix"])
        return super().before_content()

    def after_content(self):
        flag_prefixes = self.env.ref_context.setdefault("py:yuio:flag_prefixes", [])
        if "flag-prefix" in self.options:
            flag_prefixes.pop()
        env_prefixes = self.env.ref_context.setdefault("py:yuio:env_prefixes", [])
        if "env-prefix" in self.options:
            env_prefixes.pop()
        return super().after_content()

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
        if "subconfig" in self.options:
            return []
        else:
            return super().get_signature_prefix(sig)


class ConfigDocumenter(ClassDocumenter):
    objtype = "config"

    option_spec = ClassDocumenter.option_spec.copy()
    option_spec["enum-by-name"] = bool_option
    option_spec["enum-to-dash-case"] = bool_option
    option_spec["display-name"] = directives.unchanged
    option_spec["show-flags"] = bool_option
    option_spec["flag-prefix"] = directives.unchanged
    option_spec["show-env"] = bool_option
    option_spec["env-prefix"] = directives.unchanged

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
        self._flags = None
        self._env = None
        if ret and (
            isinstance(self.object, type)
            and issubclass(self.object, yuio.config.Config)
        ):
            # Make sure the config is fully initialized by explicitly
            # calling _get_fields and running all lazy logic.
            _get_fields(self.object)
        if ret and (
            isinstance(self.parent, type)
            and issubclass(self.parent, yuio.config.Config)
        ):
            self.doc_as_attr = False
            self.is_nested_config = True

            if field := _get_fields(self.parent).get(self.object_name):
                self._flags = field.flags
                self._env = field.env
        else:
            self.is_nested_config = False
        return ret

    def add_directive_header(self, sig: str):
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if self.is_nested_config:
            self.add_line("   :subconfig:", self.get_sourcename())
        if self.options.display_name and not self.is_nested_config:
            self.add_line("   :display-name: " + self.options.display_name, sourcename)
        if self.options.show_flags:
            if self.is_nested_config:
                flag_prefix = (
                    self._flags[0].removeprefix("--")
                    if isinstance(self._flags, list)
                    else "__disabled__"
                )
                self.add_line("   :flag-prefix: " + flag_prefix, sourcename)
            elif self.options.flag_prefix:
                self.add_line(
                    "   :flag-prefix: " + self.options.flag_prefix, sourcename
                )
        if self.options.show_env:
            if self.is_nested_config:
                env_prefix = self._env if isinstance(self._env, str) else "__disabled__"
                self.add_line("   :env-prefix: " + env_prefix, sourcename)
            elif self.options.env_prefix:
                self.add_line("   :env-prefix: " + self.options.env_prefix, sourcename)


class Field(PyAttribute):
    option_spec = PyAttribute.option_spec.copy()
    option_spec["display-name"] = directives.unchanged
    option_spec["flag"] = directives.unchanged
    option_spec["flag-value"] = directives.unchanged
    option_spec["env"] = directives.unchanged
    option_spec["env-value"] = directives.unchanged

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

    def transform_content(self, content_node: sphinx.addnodes.desc_content):
        super().before_content()

        nodes = content_node.parent
        index = 0
        for i, node in enumerate(nodes):
            index = i
            if not isinstance(node, sphinx.addnodes.desc_signature):
                break

        flag_prefixes = self.env.ref_context.setdefault("py:yuio:flag_prefixes", [])
        if "flag" in self.options and "__disabled__" not in flag_prefixes:
            orig_flags: list[str] = self.options["flag"].split()
            flag_value = self.options.get("flag-value", None)

            if flag_prefixes:
                prefix = "--" + "-".join(flag_prefixes) + "-"
                flags = [prefix + flag.lstrip("-") for flag in orig_flags]
            else:
                prefix = ""
                flags = orig_flags

            if flag_value == "__bool__":
                for flag in orig_flags:
                    if flag.startswith("--"):
                        flags.append((prefix or "--") + "no-" + flag[2:])
                        break
                flag_value = ""
            for flag in flags:
                signode = sphinx.addnodes.desc_signature(
                    "",
                    "",
                    sphinx.addnodes.desc_annotation("", "flag"),
                    sphinx.addnodes.desc_sig_space(),
                    sphinx.addnodes.desc_name("", flag, classes=["yuio-flag"]),
                    classes=["yuio-sig", "yuio-sig-flag"],
                )
                self.set_source_info(signode)

                if flag_value:
                    signode += sphinx.addnodes.desc_sig_space()
                    signode += sphinx.addnodes.desc_sig_element("", flag_value)

                nodes.insert(index, signode)
                index += 1

        env_prefixes = self.env.ref_context.setdefault("py:yuio:env_prefixes", [])
        if "env" in self.options and "__disabled__" not in env_prefixes:
            env = self.options["env"]
            if env_prefixes:
                env = "_".join(env_prefixes) + "_" + env
            if env:
                signode = sphinx.addnodes.desc_signature(
                    "",
                    "",
                    sphinx.addnodes.desc_annotation("", "env"),
                    sphinx.addnodes.desc_sig_space(),
                    sphinx.addnodes.desc_name("", env, classes=["yuio-env"]),
                    classes=["yuio-sig", "yuio-sig-env"],
                )
                self.set_source_info(signode)

                if env_value := self.options.get("env-value", None):
                    signode += sphinx.addnodes.desc_sig_space()
                    signode += sphinx.addnodes.desc_sig_element("", env_value)

                nodes.insert(index, signode)
                index += 1

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
    option_spec["show-flags"] = bool_option
    option_spec["show-env"] = bool_option

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

        if self.options.show_flags and isinstance(field.flags, list):
            self.add_line("   :flag: " + " ".join(field.flags), sourcename)
            if yuio.parse._is_bool_parser(field.parser):
                content = "__bool__"
            else:
                content = field.parser.describe_or_def()
            self.add_line("   :flag-value: " + content, sourcename)

        if self.options.show_env and isinstance(field.env, str):
            self.add_line("   :env: " + field.env, sourcename)
            self.add_line(
                "   :env-value: " + field.parser.describe_or_def(), sourcename
            )

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


class Flag(SphinxRole):
    def run(
        self,
    ) -> tuple[list[docutils.nodes.Node], list[docutils.nodes.system_message]]:
        classes = ["kbd", "flag"]
        if "classes" in self.options:
            classes.extend(self.options["classes"])
        text = self.text
        return [docutils.nodes.literal(self.rawtext, text, classes=classes)], []


def setup(app: sphinx.application.Sphinx):
    app.add_directive_to_domain("py", "config", Config)
    app.add_directive_to_domain("py", "field", Field)
    app.add_autodocumenter(ConfigDocumenter)
    app.add_autodocumenter(FieldDocumenter)
    app.add_role("flag", Flag())

    return {
        "version": yuio.__version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
