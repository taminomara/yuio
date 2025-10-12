Interactive things
==================

Yuio's interactive capabilities.


Querying user input
-------------------

Last time we've built a simple CLI app that greets the user.
Now, let's make it interactive.

We'll start by querying the user's name, and if they want
a formal or an informal greeting:

.. literalinclude:: code/2_1_querying.py
   :language: python
   :emphasize-lines: 5,11,12,13,14,15

We've used :func:`yuio.io.ask` to get data from the user. It's like :func:`input`,
but automatically parses the user input, and can use different widgets based
on the expected value's type. That's why we've used :class:`~enum.Enum` instead
of a simple string:

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 2_1_querying.py"
   Enter
   Sleep 1s
   Type "Miku"
   Sleep 500ms
   Enter
   Sleep 500ms
   Right
   Sleep 500ms
   Enter
   Sleep 6s


Indicating progress
-------------------

Suppose you have some long-running job, and you want to indicate that it is running.
:class:`yuio.io.Task` to the rescue:

.. literalinclude:: code/2_2_task.py
   :language: python
   :emphasize-lines: 7

And if the job can report its progress, we can even show a progressbar:

.. literalinclude:: code/2_3_progress.py
   :language: python
   :emphasize-lines: 9,11,12

:class:`~yuio.io.Task` has lots of helper methods on it. For example, the above code
can be simplified using :meth:`yuio.io.Task.iter`: a function that automatically
updates progress as you iterate over a collection.

.. vhs-inline::
   :scale: 40%

   Source "docs/source/_tapes/_config_by_example.tape"
   Type "python 2_3_progress.py"
   Enter
   Sleep 12s


Opening an external editor
--------------------------

You know how when you run ``git commit``, it opens an editor and asks you to edit
a commit message? Yuio can do the same:

.. literalinclude:: code/2_4_edit.py
   :language: python
   :lines: 4-12
   :emphasize-lines: 3,4,5,6,7
