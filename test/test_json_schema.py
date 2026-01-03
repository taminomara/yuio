import yuio.json_schema as js


class TestJsonSchemaContext:
    def test_add_type_creates_ref(self):
        ctx = js.JsonSchemaContext()
        ref = ctx.add_type(int, "Integer", lambda: js.Integer())
        assert isinstance(ref, js.Ref)
        assert ref.ref == "#/$defs/Integer"
        assert ref.name == "Integer"

    def test_add_type_returns_same_ref_for_same_key(self):
        ctx = js.JsonSchemaContext()
        ref1 = ctx.add_type(int, "Integer", lambda: js.Integer())
        ref2 = ctx.add_type(int, "Integer", lambda: js.Integer())
        assert ref1 == ref2

    def test_add_type_deduplicates_names(self):
        ctx = js.JsonSchemaContext()
        ref1 = ctx.add_type(int, "Type", lambda: js.Integer())
        ref2 = ctx.add_type(str, "Type", lambda: js.String())
        assert ref1.ref == "#/$defs/Type"
        assert ref2.ref == "#/$defs/Type2"

    def test_get_type_returns_schema(self):
        ctx = js.JsonSchemaContext()
        ctx.add_type(int, "Integer", lambda: js.Integer())
        schema = ctx.get_type("Integer")
        assert schema == js.Integer()

    def test_get_type_returns_none_for_unknown(self):
        ctx = js.JsonSchemaContext()
        assert ctx.get_type("Unknown") is None

    def test_render_includes_schema_and_defs(self):
        ctx = js.JsonSchemaContext()
        ctx.add_type(int, "MyInt", lambda: js.Integer())
        result = ctx.render(js.String())
        assert result["$schema"] == "https://json-schema.org/draft-07/schema"  # type: ignore
        assert result["type"] == "string"  # type: ignore
        assert "$defs" in result  # type: ignore
        assert "MyInt" in result["$defs"]  # type: ignore

    def test_render_with_id(self):
        ctx = js.JsonSchemaContext()
        result = ctx.render(js.String(), id="http://example.com/schema")
        assert result["$id"] == "http://example.com/schema"  # type: ignore


class TestRef:
    def test_render(self):
        ref = js.Ref("#/$defs/MyType", "MyType")
        assert ref.render() == {"$ref": "#/$defs/MyType"}

    def test_pprint_with_name(self):
        ref = js.Ref("#/$defs/MyType", "MyName")
        assert ref.pprint() == "MyName"

    def test_pprint_without_name(self):
        ref = js.Ref("#/$defs/MyType")
        assert ref.pprint() == "MyType"


class TestArray:
    def test_render_basic(self):
        arr = js.Array(js.String())
        assert arr.render() == {"type": "array", "items": {"type": "string"}}

    def test_render_unique_items(self):
        arr = js.Array(js.String(), unique_items=True)
        result = arr.render()
        assert result["uniqueItems"] is True

    def test_remove_opaque(self):
        arr = js.Array(js.String())
        assert arr.remove_opaque() == js.Array(js.String())

    def test_remove_opaque_with_opaque_item(self):
        arr = js.Array(js.Opaque({}))
        assert arr.remove_opaque() is None

    def test_pprint_simple(self):
        arr = js.Array(js.String())
        assert arr.pprint() == "string[]"

    def test_pprint_with_union(self):
        arr = js.Array(js.OneOf([js.String(), js.Integer()]))
        assert arr.pprint() == "(string | integer)[]"


class TestTuple:
    def test_render(self):
        tup = js.Tuple([js.String(), js.Integer()])
        assert tup.render() == {
            "type": "array",
            "items": [{"type": "string"}, {"type": "integer"}],
            "minItems": 2,
            "maxItems": 2,
            "additionalItems": False,
        }

    def test_remove_opaque(self):
        tup = js.Tuple([js.String(), js.Opaque({})])
        result = tup.remove_opaque()
        assert result == js.Tuple([js.String()])

    def test_pprint(self):
        tup = js.Tuple([js.String(), js.Integer()])
        assert tup.pprint() == "[string, integer]"


class TestDict:
    def test_render_with_string_key(self):
        d = js.Dict(js.String(), js.Integer())
        result = d.render()
        assert result["type"] == ["array", "object"]
        assert result["propertyNames"] == {"type": "string"}
        assert result["additionalProperties"] == {"type": "integer"}

    def test_render_with_non_string_key(self):
        d = js.Dict(js.Integer(), js.String())
        result = d.render()
        assert result["type"] == "array"
        assert "propertyNames" not in result

    def test_remove_opaque(self):
        d = js.Dict(js.String(), js.Integer())
        assert d.remove_opaque() == js.Dict(js.String(), js.Integer())

    def test_remove_opaque_with_opaque_key(self):
        d = js.Dict(js.Opaque({}), js.Integer())
        assert d.remove_opaque() is None

    def test_remove_opaque_with_opaque_value(self):
        d = js.Dict(js.String(), js.Opaque({}))
        assert d.remove_opaque() is None

    def test_pprint(self):
        d = js.Dict(js.String(), js.Integer())
        assert d.pprint() == "{[string]: integer}"


class TestNull:
    def test_render(self):
        assert js.Null().render() == {"type": "null"}

    def test_pprint(self):
        assert js.Null().pprint() == "null"


class TestBoolean:
    def test_render(self):
        assert js.Boolean().render() == {"type": "boolean"}

    def test_pprint(self):
        assert js.Boolean().pprint() == "boolean"


class TestNumber:
    def test_render(self):
        assert js.Number().render() == {"type": "number"}

    def test_pprint(self):
        assert js.Number().pprint() == "number"


class TestInteger:
    def test_render(self):
        assert js.Integer().render() == {"type": "integer"}

    def test_pprint(self):
        assert js.Integer().pprint() == "integer"


class TestString:
    def test_render_basic(self):
        assert js.String().render() == {"type": "string"}

    def test_render_with_pattern(self):
        s = js.String(pattern="^[a-z]+$")
        assert s.render() == {"type": "string", "pattern": "^[a-z]+$"}

    def test_pprint(self):
        assert js.String().pprint() == "string"


class TestAny:
    def test_render(self):
        assert js.Any().render() == {}

    def test_pprint(self):
        assert js.Any().pprint() == "any"


class TestNever:
    def test_render(self):
        assert js.Never().render() == {"allOf": [False]}

    def test_pprint(self):
        assert js.Never().pprint() == "never"


class TestOneOf:
    def test_render(self):
        one_of = js.OneOf([js.String(), js.Integer()])
        assert one_of.render() == {"oneOf": [{"type": "string"}, {"type": "integer"}]}

    def test_flattens_nested_one_of(self):
        inner = js.OneOf([js.String(), js.Integer()])
        outer = js.OneOf([inner, js.Boolean()])
        assert isinstance(outer, js.OneOf)
        assert len(outer.items) == 3

    def test_removes_never(self):
        one_of = js.OneOf([js.String(), js.Never()])
        assert one_of == js.String()

    def test_returns_never_if_all_never(self):
        one_of = js.OneOf([js.Never(), js.Never()])
        assert one_of == js.Never()

    def test_returns_single_item_if_only_one(self):
        one_of = js.OneOf([js.String()])
        assert one_of == js.String()

    def test_remove_opaque(self):
        one_of = js.OneOf([js.String(), js.Opaque({})])
        result = one_of.remove_opaque()
        assert result == js.String()

    def test_remove_opaque_all_opaque(self):
        one_of = js.OneOf([js.Opaque({}), js.Opaque({})])
        assert one_of.remove_opaque() is None

    def test_pprint(self):
        one_of = js.OneOf([js.String(), js.Integer()])
        assert one_of.pprint() == "string | integer"


class TestAllOf:
    def test_render(self):
        all_of = js.AllOf([js.String(), js.Integer()])
        assert all_of.render() == {"allOf": [{"type": "string"}, {"type": "integer"}]}

    def test_flattens_nested_all_of(self):
        inner = js.AllOf([js.String(), js.Integer()])
        outer = js.AllOf([inner, js.Boolean()])
        assert isinstance(outer, js.AllOf)
        assert len(outer.items) == 3

    def test_removes_never(self):
        all_of = js.AllOf([js.String(), js.Never()])
        assert all_of == js.String()

    def test_returns_never_if_all_never(self):
        all_of = js.AllOf([js.Never(), js.Never()])
        assert all_of == js.Never()

    def test_returns_single_item_if_only_one(self):
        all_of = js.AllOf([js.String()])
        assert all_of == js.String()

    def test_remove_opaque(self):
        all_of = js.AllOf([js.String(), js.Opaque({})])
        result = all_of.remove_opaque()
        assert result == js.String()

    def test_remove_opaque_all_opaque(self):
        all_of = js.AllOf([js.Opaque({}), js.Opaque({})])
        assert all_of.remove_opaque() is None

    def test_pprint(self):
        all_of = js.AllOf([js.String(), js.Integer()])
        assert all_of.pprint() == "string & integer"


class TestAnyOf:
    def test_render(self):
        any_of = js.AnyOf([js.String(), js.Integer()])
        assert any_of.render() == {"anyOf": [{"type": "string"}, {"type": "integer"}]}

    def test_flattens_nested_any_of(self):
        inner = js.AnyOf([js.String(), js.Integer()])
        outer = js.AnyOf([inner, js.Boolean()])
        assert isinstance(outer, js.AnyOf)
        assert len(outer.items) == 3

    def test_removes_never(self):
        any_of = js.AnyOf([js.String(), js.Never()])
        assert any_of == js.String()

    def test_returns_never_if_all_never(self):
        any_of = js.AnyOf([js.Never(), js.Never()])
        assert any_of == js.Never()

    def test_returns_single_item_if_only_one(self):
        any_of = js.AnyOf([js.String()])
        assert any_of == js.String()

    def test_remove_opaque(self):
        any_of = js.AnyOf([js.String(), js.Opaque({})])
        result = any_of.remove_opaque()
        assert result == js.String()

    def test_remove_opaque_all_opaque(self):
        any_of = js.AnyOf([js.Opaque({}), js.Opaque({})])
        assert any_of.remove_opaque() is None

    def test_pprint(self):
        any_of = js.AnyOf([js.String(), js.Integer()])
        assert any_of.pprint() == "string | integer"


class TestEnum:
    def test_render_without_descriptions(self):
        enum = js.Enum(["a", "b", "c"])
        assert enum.render() == {"enum": ["a", "b", "c"]}

    def test_render_with_descriptions(self):
        enum = js.Enum(["a", "b"], descriptions=["First", "Second"])
        result = enum.render()
        assert result == {
            "oneOf": [
                {"const": "a", "description": "First"},
                {"const": "b", "description": "Second"},
            ]
        }

    def test_render_with_partial_descriptions(self):
        enum = js.Enum(["a", "b"], descriptions=["First", None])
        result = enum.render()
        assert result == {
            "oneOf": [
                {"const": "a", "description": "First"},
                {"const": "b"},
            ]
        }

    def test_render_with_mixed_types(self):
        enum = js.Enum([1, "two", 3.0, True, None])
        assert enum.render() == {"enum": [1, "two", 3.0, True, None]}

    def test_pprint(self):
        enum = js.Enum(["a", "b", 1])
        assert enum.pprint() == '"a" | "b" | 1'


class TestObject:
    def test_render(self):
        obj = js.Object({"name": js.String(), "age": js.Integer()})
        assert obj.render() == {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "additionalProperties": False,
        }

    def test_remove_opaque(self):
        obj = js.Object({"name": js.String(), "hidden": js.Opaque({})})
        result = obj.remove_opaque()
        assert result == js.Object({"name": js.String()})

    def test_remove_opaque_all_opaque(self):
        obj = js.Object({"hidden": js.Opaque({})})
        assert obj.remove_opaque() is None

    def test_pprint(self):
        obj = js.Object({"name": js.String()})
        assert obj.pprint() == "{name: string}"


class TestOpaque:
    def test_render(self):
        opaque = js.Opaque({"custom": "schema"})
        assert opaque.render() == {"custom": "schema"}

    def test_remove_opaque(self):
        opaque = js.Opaque({})
        assert opaque.remove_opaque() is None

    def test_pprint(self):
        assert js.Opaque({}).pprint() == "..."


class TestMeta:
    def test_render_with_title(self):
        meta = js.Meta(js.String(), title="My Title")
        result = meta.render()
        assert result["title"] == "My Title"
        assert result["type"] == "string"

    def test_render_with_description(self):
        meta = js.Meta(js.String(), description="My Description")
        result = meta.render()
        assert result["description"] == "My Description\n"

    def test_render_with_default(self):
        meta = js.Meta(js.String(), default="default_value")
        result = meta.render()
        assert result["default"] == "default_value"

    def test_render_without_default_when_missing(self):
        meta = js.Meta(js.String())
        result = meta.render()
        assert "default" not in result

    def test_render_with_all_metadata(self):
        meta = js.Meta(
            js.Integer(),
            title="Count",
            description="Number of items",
            default=0,
        )
        result = meta.render()
        assert result == {
            "type": "integer",
            "title": "Count",
            "description": "Number of items\n",
            "default": 0,
        }

    def test_remove_opaque(self):
        meta = js.Meta(js.String(), title="Test")
        result = meta.remove_opaque()
        assert result == js.Meta(js.String(), title="Test")

    def test_remove_opaque_with_opaque_item(self):
        meta = js.Meta(js.Opaque({}), title="Test")
        assert meta.remove_opaque() is None

    def test_pprint_with_title(self):
        meta = js.Meta(js.String(), title="MyString")
        assert meta.pprint() == "MyString"

    def test_pprint_without_title(self):
        meta = js.Meta(js.String())
        assert meta.pprint() == "string"

    def test_precedence_with_title(self):
        meta = js.Meta(js.OneOf([js.String(), js.Integer()]), title="MyType")
        assert meta.precedence == 3

    def test_precedence_without_title(self):
        meta = js.Meta(js.OneOf([js.String(), js.Integer()]))
        assert meta.precedence == 2


class TestPrettyPrinting:
    def test_str_returns_pprint(self):
        schema = js.String()
        assert str(schema) == schema.pprint()

    def test_nested_precedence_in_one_of(self):
        all_of = js.AllOf([js.String(), js.Integer()])
        one_of = js.OneOf([all_of, js.Boolean()])
        assert one_of.pprint() == "(string & integer) | boolean"

    def test_nested_precedence_in_all_of(self):
        one_of = js.OneOf([js.String(), js.Integer()])
        all_of = js.AllOf([one_of, js.Boolean()])
        assert all_of.pprint() == "string | integer & boolean"


class TestEdgeCases:
    def test_empty_one_of(self):
        result = js.OneOf([])
        assert result == js.Never()

    def test_empty_all_of(self):
        result = js.AllOf([])
        assert result == js.Never()

    def test_empty_any_of(self):
        result = js.AnyOf([])
        assert result == js.Never()

    def test_empty_tuple(self):
        tup = js.Tuple([])
        assert tup.render() == {
            "type": "array",
            "items": [],
            "minItems": 0,
            "maxItems": 0,
            "additionalItems": False,
        }
        assert tup.pprint() == "[]"

    def test_empty_object(self):
        obj = js.Object({})
        assert obj.render() == {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        }
        assert obj.pprint() == "{}"

    def test_empty_enum(self):
        enum = js.Enum([])
        assert enum.render() == {"enum": []}
        assert enum.pprint() == ""

    def test_default_can_be_none(self):
        meta = js.Meta(js.String(), default=None)
        result = meta.render()
        assert result["default"] is None

    def test_description_dedent(self):
        meta = js.Meta(
            js.String(),
            description="""
                This is a multi-line
                description that should
                be dedented.
            """,
        )
        result = meta.render()
        # The description should be dedented
        assert (
            result["description"]
            == "This is a multi-line\ndescription that should\nbe dedented.\n"
        )
