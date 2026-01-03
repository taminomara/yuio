# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# You're free to copy this file to your project and edit it for your needs,
# just keep this copyright line please :3

"""
A simple JSON schema representation to describe configs and types.

This module primarily used with
:meth:`Parser.to_json_schema <yuio.parse.Parser.to_json_schema>`
to generate config schemas used in IDEs.

.. class:: JsonValue

    A type alias for JSON values. Can be used as type of a config field,
    in which case it will be parsed with the :class:`~yuio.parse.Json` parser.


JSON types
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


Building a schema
-----------------

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
from dataclasses import dataclass

import yuio
from yuio.util import dedent as _dedent

from typing import TYPE_CHECKING
from typing import ClassVar as _ClassVar

if TYPE_CHECKING:
    import typing_extensions as _t
else:
    from yuio import _typing as _t

__all__ = [
    "AllOf",
    "Any",
    "AnyOf",
    "Array",
    "Boolean",
    "Dict",
    "Enum",
    "Integer",
    "JsonSchemaContext",
    "JsonSchemaType",
    "JsonValue",
    "Meta",
    "Never",
    "Null",
    "Number",
    "Object",
    "OneOf",
    "Opaque",
    "Ref",
    "String",
    "Tuple",
]

T = _t.TypeVar("T")

if _t.TYPE_CHECKING or "__YUIO_SPHINX_BUILD" in os.environ:  # pragma: no cover
    JsonValue: _t.TypeAlias = (
        str
        | int
        | float
        | None
        | _t.Sequence["JsonValue"]
        | _t.Mapping[str, "JsonValue"]
    )

else:  # pragma: no cover

    def _JsonValue(arg: T) -> T:
        """
        JSON value marker, used to detect JSON type hints at runtime.

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
        """
        Add a new type to the ``$defs`` section.

        :param key:
            a python type or object for which we're building a schema. This type
            will be used as a unique key in the ``$defs`` section.
        :param name:
            name of the type, will be used in the ``$defs`` section. If there are
            two types with different `key`\\ s and the same `name`, their names
            will be deduplicated.
        :param make_schema:
            a lambda that will be called if `key` wasn't added to this context before.
            It should build and return the schema for this type.
        :returns:
            a :class:`Ref` type pointing to the just-added schema.

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
        :returns:
            schema that was earlier passed to :meth:`~JsonSchemaContext.add_type`.

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

        :returns:
            complete JSON representation of a schema.

        """

        schema: dict[str, JsonValue] = {
            "$schema": "https://json-schema.org/draft-07/schema",
        }
        if id:
            schema["$id"] = id
        schema.update(root.render())
        schema["$defs"] = {name: ref.render() for name, ref in self._defs.items()}
        return schema


@dataclass(frozen=True, slots=True, init=False)
class JsonSchemaType(abc.ABC):
    """
    Base class for JSON schema representation.

    """

    precedence: _ClassVar[int] = 3
    """
    Precedence, used for pretty-printing types.

    """

    @abc.abstractmethod
    def render(self) -> dict[str, JsonValue]:
        """
        Serialize type as JSON.

        """

        raise NotImplementedError()

    def remove_opaque(self) -> JsonSchemaType | None:
        """
        Return a new type with all instances of :class:`Opaque` removed from it.

        This is usually used before pretty-printing type for documentation.

        """

        return self

    @abc.abstractmethod
    def pprint(self) -> str:
        """
        Pretty-print this type using TypeScript syntax.

        """

        raise NotImplementedError()

    def __str__(self) -> str:
        return self.pprint()


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class Tuple(JsonSchemaType):
    """
    A tuple.

    """

    items: _t.Sequence[JsonSchemaType]
    """
    Types of tuple elements.

    """

    def render(self) -> dict[str, JsonValue]:
        return {
            "type": "array",
            "items": [item.render() for item in self.items],
            "minItems": len(self.items),
            "maxItems": len(self.items),
            "additionalItems": False,
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


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class Null(JsonSchemaType):
    """
    A ``null`` value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "null"}

    def pprint(self) -> str:
        return "null"


@dataclass(frozen=True, slots=True)
class Boolean(JsonSchemaType):
    """
    A boolean value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "boolean"}

    def pprint(self) -> str:
        return "boolean"


@dataclass(frozen=True, slots=True)
class Number(JsonSchemaType):
    """
    A numeric value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "number"}

    def pprint(self) -> str:
        return "number"


@dataclass(frozen=True, slots=True)
class Integer(Number):
    """
    An integer value.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"type": "integer"}

    def pprint(self) -> str:
        return "integer"


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class Any(JsonSchemaType):
    """
    A value that always type checks, equivalent to schema ``true``.

    """

    def render(self) -> dict[str, JsonValue]:
        return {}

    def pprint(self) -> str:
        return "any"


@dataclass(frozen=True, slots=True)
class Never(JsonSchemaType):
    """
    A value that never type checks, equivalent to schema ``false``.

    """

    def render(self) -> dict[str, JsonValue]:
        return {"allOf": [False]}

    def pprint(self) -> str:
        return "never"


@dataclass(frozen=True, slots=True, init=False)
class OneOf(JsonSchemaType):
    """
    A union of possible values, equivalent to ``oneOf`` schema.

    """

    precedence = 2

    items: _t.Sequence[JsonSchemaType]
    """
    Inner items.

    """

    def __new__(cls, items: _t.Sequence[JsonSchemaType]) -> JsonSchemaType:
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
        self = object.__new__(cls)
        object.__setattr__(self, "items", flatten)
        return self

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


@dataclass(frozen=True, slots=True, init=False)
class AllOf(JsonSchemaType):
    """
    An intersection of possible values, equivalent to ``allOf`` schema.

    """

    precedence = 1

    items: _t.Sequence[JsonSchemaType]
    """
    Inner items.

    """

    def __new__(cls, items: _t.Sequence[JsonSchemaType]) -> JsonSchemaType:
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
        self = object.__new__(cls)
        object.__setattr__(self, "items", flatten)
        return self

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


@dataclass(frozen=True, slots=True, init=False)
class AnyOf(JsonSchemaType):
    """
    A union of possible values, equivalent to ``anyOf`` schema.

    """

    precedence = 2

    items: _t.Sequence[JsonSchemaType]
    """
    Inner items.

    """

    def __new__(cls, items: _t.Sequence[JsonSchemaType]) -> JsonSchemaType:
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
        self = object.__new__(cls)
        object.__setattr__(self, "items", flatten)
        return self

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


@dataclass(frozen=True, slots=True)
class Enum(JsonSchemaType):
    """
    An enum of primitive constants.

    """

    precedence = 2

    constants: _t.Sequence[str | int | float | bool | None]
    """
    Enum elements.

    """

    descriptions: _t.Sequence[str | None] | None = None
    """
    Descriptions for enum items. If given, list of descriptions should have the same
    length as the list of constants.

    """

    def render(self) -> dict[str, JsonValue]:
        if self.descriptions is None:
            return {"enum": list(self.constants)}
        else:
            assert len(self.descriptions) == len(self.constants)
            return {
                "oneOf": [
                    {
                        "const": const,
                        **({"description": description} if description else {}),
                    }
                    for const, description in zip(self.constants, self.descriptions)
                ]
            }

    def pprint(self) -> str:
        return " | ".join(f"{json.dumps(item)}" for item in self.constants)


@dataclass(frozen=True, slots=True)
class Object(JsonSchemaType):
    """
    An object, usually represents a :class:`~yuio.config.Config`.

    """

    properties: dict[str, JsonSchemaType]
    """
    Object keys and their types.

    """

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


@dataclass(frozen=True, slots=True)
class Opaque(JsonSchemaType):
    """
    Can contain arbitrary schema, for cases when these classes
    can't represent required constraints.

    """

    schema: dict[str, JsonValue]
    """
    Arbitrary schema. This should be a dictionary so that :class:`Meta` can add
    additional data to it.

    """

    def render(self) -> dict[str, JsonValue]:
        return self.schema

    def remove_opaque(self) -> JsonSchemaType | None:
        return None

    def pprint(self) -> str:
        return "..."


@dataclass(frozen=True, slots=True)
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
            schema["description"] = _dedent(self.description)
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
