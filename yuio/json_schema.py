# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
A simple Json schema representation to describe configs and types.

This module primarily used with
:meth:`Parser.to_json_schema <yuio.parse.Parser.to_json_schema>`
to generate config schemas used in IDEs.

.. class:: JsonValue

    A type alias for JSON values. Can be used as type of a config field,
    in which case it will be parsed with the :class:`~yuio.parse.Json` parser.


Json types
----------

.. autoclass:: JsonSchemaType
    :members:

.. autoclass:: Ref
    :members:

.. autoclass:: Array
    :members:

.. autoclass:: Tuple
    :members:

.. autoclass:: Dict
    :members:

.. autoclass:: Null
    :members:

.. autoclass:: Boolean
    :members:

.. autoclass:: Number
    :members:

.. autoclass:: Integer
    :members:

.. autoclass:: String
    :members:

.. autoclass:: Any
    :members:

.. autoclass:: Never
    :members:

.. autoclass:: OneOf
    :members:

.. autoclass:: AllOf
    :members:

.. autoclass:: AnyOf
    :members:

.. autoclass:: Enum
    :members:

.. autoclass:: Object
    :members:

.. autoclass:: Opaque
    :members:

.. autoclass:: Meta
    :members:


Building schemas
----------------

Most likely you'll get a schema from
:meth:`Config.to_json_schema <yuio.config.Config.to_json_schema>`
or :meth:`Parser.to_json_schema <yuio.parse.Parser.to_json_schema>`.

To convert it to JSON value, use :meth:`JsonSchemaContext.render`, and possibly
wrap the schema into :class:`Meta`:

.. invisible-code-block: python

    from yuio.config import Config
    import yuio.json_schema
    import json
    class AppConfig(Config): ...

.. code-block:: python

    ctx = yuio.json_schema.JsonSchemaContext()
    schema = yuio.json_schema.Meta(
        AppConfig.to_json_schema(ctx),
        title="Config for my application",
    )
    data = json.dumps(ctx.render(schema), indent=2)

.. autoclass:: JsonSchemaContext
    :members:

"""
from __future__ import annotations

import abc
import json
import os
import textwrap
from dataclasses import dataclass

import yuio
from yuio import _typing as _t

T = _t.TypeVar("T")

if _t.TYPE_CHECKING or "__YUIO_SPHINX_BUILD" in os.environ:
    JsonValue: _t.TypeAlias = (
        str
        | int
        | float
        | None
        | _t.Sequence["JsonValue"]
        | _t.Mapping[str, "JsonValue"]
    )
else:

    def _JsonValue(arg: T) -> T:
        """
        Json value marker, used to detect Json type hints at runtime.

        """

        return arg

    JsonValue: _t.TypeAlias = _JsonValue  # type: ignore


class JsonSchemaContext:
    """
    Context for building schema.

    """

    def __init__(self):
        self._types: dict[type, tuple[str, JsonSchemaType]] = {}
        self._defs: dict[str, JsonSchemaType] = {}

    def add_type(
        self, key: _t.Any, /, name: str, make_schema: _t.Callable[[], JsonSchemaType]
    ) -> Ref:
        r"""
        Add a new type to the ``$defs`` section.

        :param key:
            a python type or object for which we're building a schema. This type
            will be used as a unique key in the ``$defs`` section.
        :param name:
            name of the type, will be used in the ``$defs`` section. If there are
            two types with different ``ty``\ s and the same ``name``, their names
            will be deduplicated.
        :param make_schema:
            a lambda that will be called if ``ty`` wasn't added to this context before.
            It should build and return the schema for this type.

        """

        if key not in self._types:
            i = ""
            while f"{name}{i}" in self._defs:
                i = (i or 1) + 1
            name = f"{name}{i}"
            schema = make_schema()
            self._types[key] = (name, schema)
            self._defs[name] = schema
        return Ref(f"#/$defs/{self._types[key][0]}", self._types[key][0])

    def get_type(self, ref: str) -> JsonSchemaType | None:
        """
        Get saved type by ``$ref``.

        :param ref:
            contents of the ``$ref`` anchor.

        """

        return self._defs.get(ref)

    def render(
        self,
        root: JsonSchemaType,
        /,
        *,
        id: str | None = None,
    ) -> JsonValue:
        """
        Convert schema to a value suitable for JSON serialization.

        """

        schema: dict[str, JsonValue] = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
        }
        if id:
            schema["$id"] = id
        schema.update(root.render())
        schema["$defs"] = {name: ref.render() for name, ref in self._defs.items()}
        return schema


class JsonSchemaType(abc.ABC):
    """
    Base class for JSON schema representation.

    """

    precedence: int = 3
    """
    Precedence, used for pretty-printing types.

    """

    @abc.abstractmethod
    def render(self) -> dict[str, JsonValue]:
        """
        Serialize type as JSON.

        """

    def remove_opaque(self) -> JsonSchemaType | None:
        """
        Return a new type with all instances of :class:`Opaque` removed from it.

        This is usually used before pretty-printing type for documentation.

        """

        return self

    @abc.abstractmethod
    def pprint(self) -> str:
        """
        Pretty-print this type.

        """

    def __str__(self) -> str:
        return self.pprint()


@dataclass(frozen=True, **yuio._with_slots())
class Ref(JsonSchemaType):
    """
    A reference to a sub-schema.

    Use :meth:`JsonSchemaContext.add_type` to create these.

    """

    ref: str
    """
    Referenced type.

    """

    name: str | None = None
    """
    Name of the referenced type, used for debug.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"$ref": self.ref}

    def pprint(self) -> str:
        return self.name or self.ref.removeprefix("#/$defs/")


@dataclass(frozen=True, **yuio._with_slots())
class Array(JsonSchemaType):
    """
    An array or a set of values.

    """

    item: JsonSchemaType
    """
    Type of array elements.

    """

    unique_items: bool = False
    """
    Whether all array items should be unique.

    """

    def render(self) -> dict[str, JsonValue]:
        schema: dict[str, JsonValue] = {"type": "array", "items": self.item.render()}
        if self.unique_items:
            schema["uniqueItems"] = True
        return schema

    def remove_opaque(self) -> JsonSchemaType | None:
        item = self.item.remove_opaque()
        return Array(item, self.unique_items) if item is not None else None

    def pprint(self) -> str:
        if self.item.precedence >= self.precedence:
            return f"{self.item.pprint()}[]"
        else:
            return f"({self.item.pprint()})[]"


@dataclass(frozen=True, **yuio._with_slots())
class Tuple(JsonSchemaType):
    """
    A tuple.

    """

    items: list[JsonSchemaType]
    """
    Types of tuple elements.

    """

    def render(self) -> dict[str, JsonValue]:
        return {
            "type": "array",
            "items": False,
            "prefixItems": [item.render() for item in self.items],
        }

    def remove_opaque(self) -> JsonSchemaType | None:
        return Tuple(
            [
                clear
                for item in self.items
                if (clear := item.remove_opaque()) is not None
            ]
        )

    def pprint(self) -> str:
        return f"[{', '.join(item.pprint() for item in self.items)}]"


@dataclass(frozen=True, **yuio._with_slots())
class Dict(JsonSchemaType):
    """
    A dict. If key is string, this is represented as an object; if key is not a string,
    this is represented as an array of pairs.

    """

    key: JsonSchemaType
    """
    Type of dict keys.

    """

    value: JsonSchemaType
    """
    Type of dict values.

    """

    def render(self) -> dict[str, JsonValue]:
        schema: dict[str, JsonValue] = Array(Tuple([self.key, self.value])).render()
        if isinstance(self.key, String):
            schema["type"] = [schema["type"], "object"]
            schema["propertyNames"] = self.key.render()
            schema["additionalProperties"] = self.value.render()
        return schema

    def remove_opaque(self) -> JsonSchemaType | None:
        key = self.key.remove_opaque()
        value = self.value.remove_opaque()
        if key is not None and value is not None:
            return Dict(key, value)
        else:
            return None

    def pprint(self) -> str:
        return f"{{[{self.key.pprint()}]: {self.value.pprint()}}}"


@dataclass(frozen=True, **yuio._with_slots())
class Null(JsonSchemaType):
    """
    A ``null`` value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "null"}

    def pprint(self) -> str:
        return "null"


@dataclass(frozen=True, **yuio._with_slots())
class Boolean(JsonSchemaType):
    """
    A boolean value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "boolean"}

    def pprint(self) -> str:
        return "boolean"


@dataclass(frozen=True, **yuio._with_slots())
class Number(JsonSchemaType):
    """
    A numeric value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "number"}

    def pprint(self) -> str:
        return "number"


@dataclass(frozen=True, **yuio._with_slots())
class Integer(Number):
    """
    An integer value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "integer"}

    def pprint(self) -> str:
        return "integer"


@dataclass(frozen=True, **yuio._with_slots())
class String(JsonSchemaType):
    """
    A string value, possibly with pattern.

    """

    pattern: str | None = None
    """
    Regular expression for checking string elements.

    """

    def render(self) -> dict[str, JsonValue]:
        schema: dict[str, JsonValue] = {"type": "string"}
        if self.pattern is not None:
            schema["pattern"] = self.pattern
        return schema

    def pprint(self) -> str:
        return "string"


@dataclass(frozen=True, **yuio._with_slots())
class Any(JsonSchemaType):
    """
    A value that always type checks, equivalent to schema ``true``.

    """

    def render(self) -> dict[str, JsonValue]:
        return {}

    def pprint(self) -> str:
        return "any"


@dataclass(frozen=True, **yuio._with_slots())
class Never(JsonSchemaType):
    """
    A value that never type checks, equivalent to schema ``false``.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"allOf": [False]}

    def pprint(self) -> str:
        return "never"


@dataclass(frozen=True)
class OneOf(JsonSchemaType):
    """
    A union of possible values, equivalent to ``oneOf`` schema.

    """

    precedence = 2

    items: list[JsonSchemaType]
    """
    Inner items.

    """

    def __new__(cls, items: list[JsonSchemaType]) -> JsonSchemaType:
        flatten: list[JsonSchemaType] = []
        for type in items:
            if isinstance(type, Never):
                pass
            elif isinstance(type, OneOf):
                flatten.extend(type.items)
            else:
                flatten.append(type)
        if not flatten:
            return Never()
        elif len(flatten) == 1:
            return flatten[0]
        return super().__new__(cls)

    def render(self) -> dict[str, JsonValue]:
        return {"oneOf": [item.render() for item in self.items]}

    def remove_opaque(self) -> JsonSchemaType | None:
        items = [
            clear for item in self.items if (clear := item.remove_opaque()) is not None
        ]
        if items:
            return OneOf(items)
        else:
            return None

    def pprint(self) -> str:
        return " | ".join(
            f"{item}" if item.precedence >= self.precedence else f"({item})"
            for item in self.items
        )


@dataclass(frozen=True)
class AllOf(JsonSchemaType):
    """
    An intersection of possible values, equivalent to ``allOf`` schema.

    """

    precedence = 1

    items: list[JsonSchemaType]
    """
    Inner items.

    """

    def __new__(cls, items: list[JsonSchemaType]) -> JsonSchemaType:
        flatten: list[JsonSchemaType] = []
        for type in items:
            if isinstance(type, Never):
                pass
            elif isinstance(type, AllOf):
                flatten.extend(type.items)
            else:
                flatten.append(type)
        if not flatten:
            return Never()
        elif len(flatten) == 1:
            return flatten[0]
        return super().__new__(cls)

    def render(self) -> dict[str, JsonValue]:
        return {"allOf": [item.render() for item in self.items]}

    def remove_opaque(self) -> JsonSchemaType | None:
        items = [
            clear for item in self.items if (clear := item.remove_opaque()) is not None
        ]
        if items:
            return AllOf(items)
        else:
            return None

    def pprint(self) -> str:
        return " & ".join(
            f"{item}" if item.precedence >= self.precedence else f"({item})"
            for item in self.items
        )


@dataclass(frozen=True)
class AnyOf(JsonSchemaType):
    """
    A union of possible values, equivalent to ``anyOf`` schema.

    """

    precedence = 2

    items: list[JsonSchemaType]
    """
    Inner items.

    """

    def __new__(cls, items: list[JsonSchemaType]) -> JsonSchemaType:
        flatten: list[JsonSchemaType] = []
        for type in items:
            if isinstance(type, Never):
                pass
            elif isinstance(type, AnyOf):
                flatten.extend(type.items)
            else:
                flatten.append(type)
        if not flatten:
            return Never()
        elif len(flatten) == 1:
            return flatten[0]
        return super().__new__(cls)

    def render(self) -> dict[str, JsonValue]:
        return {"anyOf": [item.render() for item in self.items]}

    def remove_opaque(self) -> JsonSchemaType | None:
        items = [
            clear for item in self.items if (clear := item.remove_opaque()) is not None
        ]
        if items:
            return AnyOf(items)
        else:
            return None

    def pprint(self) -> str:
        return " | ".join(
            f"{item}" if item.precedence >= self.precedence else f"({item})"
            for item in self.items
        )


@dataclass(frozen=True, **yuio._with_slots())
class Enum(JsonSchemaType):
    """
    A enum of primitive constants.

    """

    precedence = 2

    constants: list[str | int | float | bool | None]
    """
    Enum elements.

    """

    def render(self) -> dict[str, JsonValue]:
        types = set()
        for item in self.constants:
            if item is None:
                types.add("null")
            elif isinstance(item, str):
                types.add("string")
            elif isinstance(item, int):
                types.add("integer")
            elif isinstance(item, float):
                types.add("number")
            elif isinstance(item, bool):
                types.add("boolean")
            else:
                assert False, item

        return {"type": list(types), "enum": self.constants}

    def pprint(self) -> str:
        return " | ".join(f"{json.dumps(item)}" for item in self.constants)


@dataclass(frozen=True, **yuio._with_slots())
class Object(JsonSchemaType):
    """
    An object, usually represents a :class:`~yuio.config.Config`.

    """

    properties: dict[str, JsonSchemaType]

    def render(self) -> dict[str, JsonValue]:
        return {
            "type": "object",
            "properties": {
                name: type.render() for name, type in self.properties.items()
            },
            "additionalProperties": False,
        }

    def remove_opaque(self) -> JsonSchemaType | None:
        properties = {
            name: clear
            for name, item in self.properties.items()
            if (clear := item.remove_opaque()) is not None
        }
        if properties:
            return Object(properties)
        else:
            return None

    def pprint(self) -> str:
        items = ", ".join(
            f"{name}: {item.pprint()}" for name, item in self.properties.items()
        )
        return f"{{{items}}}"


@dataclass(frozen=True, **yuio._with_slots())
class Opaque(JsonSchemaType):
    """
    Can contain arbitrary schema, for cases when these classes
    can't represent required constraints.

    """

    schema: dict[str, JsonValue]
    """
    Arbitrary schema.

    """

    def render(self) -> dict[str, JsonValue]:
        return self.schema

    def remove_opaque(self) -> JsonSchemaType | None:
        return None

    def pprint(self) -> str:
        return "..."


@dataclass(frozen=True, **yuio._with_slots())
class Meta(JsonSchemaType):
    """
    Adds title, description and defaults to the wrapped schema.

    """

    item: JsonSchemaType
    """
    Inner type.

    """

    title: str | None = None
    """
    Title for the wrapped item.

    """

    description: str | None = None
    """
    Description for the wrapped item.

    """

    default: JsonValue | yuio.Missing = yuio.MISSING
    """
    Default value for the wrapped item.

    """

    @property
    def precedence(self):  # pyright: ignore[reportIncompatibleVariableOverride]
        return 3 if self.title else self.item.precedence

    def render(self) -> dict[str, JsonValue]:
        schema = self.item.render()
        if self.title is not None:
            schema["title"] = self.title
        if self.description is not None:
            first, *rest = self.description.splitlines(keepends=True)
            schema["description"] = (
                first.strip() + "\n" + textwrap.dedent("".join(rest))
            ).lstrip("\n").rstrip() + "\n"
        if self.default is not yuio.MISSING:
            schema["default"] = self.default
        return schema

    def remove_opaque(self) -> JsonSchemaType | None:
        item = self.item.remove_opaque()
        if item is not None:
            return Meta(item, self.title, self.description, self.default)
        else:
            return None

    def pprint(self) -> str:
        return self.title or self.item.pprint()
