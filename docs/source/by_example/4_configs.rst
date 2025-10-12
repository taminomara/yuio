Configs
=======

Adding configuration for our app.


Defining a config
-----------------

Last time we've make an app for greeting users. Let's add a config for it:

.. literalinclude:: code/4_1_define_a_config.py
   :language: python

Configs are similar to dataclasses, but designed specifically for being loaded
from multiple sources.


Loading a config
----------------

Let's load our config. We can load it from a file, from environment variables,
and from CLI arguments:

.. literalinclude:: code/4_2_load_a_config.py
   :language: python
   :lines: 11-20

We simply load configs from all available sources and merge them together.


Adding verification
-------------------

You can add additional verification method to your config. It will be called
every time a new config is loaded from a new source:

.. literalinclude:: code/4_3_verification.py
   :language: python
   :lines: 2-16
   :emphasize-lines: 2,11-15


Complex field merging
---------------------

By default, :meth:`~yuio.config.Config.update` overrides fields from the initial config
with fields present in the new config. Sometimes you need to merge them, though.

You can provide a custom merging function to achieve this:

.. literalinclude:: code/4_4_merging.py
   :language: python
   :emphasize-lines: 6

.. warning::

    Merge function shouldn't mutate its arguments.
    It should produce a new value instead.

.. warning::

    Merge function will not be called for default value. It's advisable to keep the
    default value empty, and add the actual default to the initial empty config:

    .. skip: next

    .. code-block:: python

        config = Config(plugins=["markdown", "rst"])
        config.update(...)


Renaming config fields
----------------------

You can adjust names of config fields when loading configs from CLI arguments
or environment variables:

.. literalinclude:: code/4_5_renaming.py
   :language: python
   :emphasize-lines: 6,7,12,13

You've already seen that we can prefix all environment variable names when loading
a config:

.. literalinclude:: code/4_6_env_prefix.py
   :language: python
   :lines: 17-24
   :emphasize-lines: 6


Skipping config fields
----------------------

Similarly, you can skip loading a field from a certain source:

.. literalinclude:: code/4_7_skipping.py
   :language: python
   :emphasize-lines: 6,7
