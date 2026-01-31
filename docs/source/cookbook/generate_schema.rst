Generate config schema
======================

    Generate Json schema for configs when rendering documentation.

To enable better development experience, it is a good idea to provide schema files
for your configs.

The generation process is simple: create :class:`~yuio.json_schema.JsonSchemaContext`,
call :meth:`Config.to_json_schema <yuio.config.Config.to_json_schema>`, then call
:class:`JsonSchemaContext.render() <yuio.json_schema.JsonSchemaContext.render>`:

.. invisible-code-block: python

    import yuio.config

    class MyConfig(yuio.config.Config):
        pass

.. code-block:: python

    import json
    import yuio.json_schema

    ctx = yuio.json_schema.JsonSchemaContext()
    schema = MyConfig.to_json_schema(ctx)
    schema_str = json.dumps(ctx.render(schema), indent=2)
    # Write `schema_str` to a file.

If you know canonical url where your schema will be available, you can give it
as schema id:

.. code-block:: python

    id = "https://example.com/schema.json"
    schema_str = json.dumps(ctx.render(schema, id=id), indent=2)


Generating schema on Sphinx build
---------------------------------

If you're using Sphinx for building documentation, you can implement a hook to create
schema file whenever you build HTML.

In your ``conf.py``:

.. code-block:: python

    import json

    import sphinx.application
    import sphinx.builders
    import sphinx.builders.html

    import yuio.json_schema

    def on_write_started(
        app: sphinx.application.Sphinx,
        builder: sphinx.builders.Builder,
    ):
        if not isinstance(builder, sphinx.builders.html.StandaloneHTMLBuilder):
            return

        ctx = yuio.json_schema.JsonSchemaContext()
        schema = MyConfig.to_json_schema(ctx)
        schema_str = json.dumps(ctx.render(schema), indent=2)
        schema_path = app.outdir.joinpath("schema.json")  # [1]_
        schema_path.write_text(schema_str, encoding="utf-8")  # [2]_


    def setup(app: sphinx.application.Sphinx):
        app.connect("write-started", on_write_started)

        return {
            "version": "0.0.0",
            "parallel_read_safe": True,
            "parallel_write_safe": True,
        }

.. code-annotations::

    1.  Place schema file in output directory.
    2.  Don't rely on default system encoding, specify one manually!
