.. _cookbook-custom-tasks:

Custom tasks
============

    Implementing tasks with custom widget.

Tasks consist of two parts:

1.  a task class derived from :class:`yuio.io.TaskBase`,
2.  a widget derived from :class:`yuio.widget.Widget`.

To implement one, you will need to supply these parts.

1.  You can derive a custom widget from :class:`yuio.widget.Task`,
    override some of its protected methods, then derive a custom task
    from :class:`yuio.io.Task`, and override its :attr:`~yuio.io.Task._widget_class`.

2.  You can build everything from scratch, which we will do in this example.


Custom task example
-------------------

Let's build something that looks like status line from Tox__.

__ https://tox.wiki/


Implementing a widget
~~~~~~~~~~~~~~~~~~~~~

First, we need a widget:

.. literalinclude:: /../../examples/cookbook/custom_task.py
    :language: python
    :lines: 10-38

.. code-annotations::

    1.  We use :data:`typing.Never` to indicate that our widget doesn't handle
        keyboard events.

    2.  First number is minimum number of lines that this widget can span,
        second number is maximum number of lines that this widget can span.

    3.  This method draws task widget using :class:`yuio.widget.RenderContext`.

    4.  We reuse color paths from default task (see :color-path:`task/...:{status}`),
        but you can add your own colors using a custom theme.


Implementing a task
~~~~~~~~~~~~~~~~~~~

Second, we need an actual task:

.. literalinclude:: /../../examples/cookbook/custom_task.py
    :language: python
    :lines: 41-82

.. code-annotations::

    1.  Priority is used to hide tasks when they don't fit in one screen. Default
        priority is ``1`` for running tasks, and ``0`` for pending or finished tasks.

    2.  :data:`None` attaches to the top of the tree; you can also pass
        a parent task here.


Putting it all together
~~~~~~~~~~~~~~~~~~~~~~~

Finally, we can use out new task:

.. vhs-inline::
    :scale: 40%

    Set FontSize 35
    Source "docs/source/_tapes/_config.tape"
    Type "python examples/cookbook/custom_task.py"
    Enter
    Wait
    Sleep 2s

.. dropdown:: Full example

    .. literalinclude:: /../../examples/cookbook/custom_task.py
        :language: python
