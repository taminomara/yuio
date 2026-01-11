import pathlib
import shutil
import yuio.app

@yuio.app.app
def main(
    #: Overwrite old backup file if it exists.
    force: bool = False,
):
    """
    A simple tool for creating ``.bak`` files.

    """

main.epilog = """
Usage examples
--------------

-   This will copy ``./prod.sqlite3`` to ``./prod.sqlite3.bak``:

    .. code-block:: bash

        python main.py backup ./prod.sqlite3

-   This will move ``./prod.sqlite3.bak`` to ``./prod.sqlite3``:

    .. code-block:: bash

        python main.py restore ./prod.sqlite3

"""

@main.subcommand(aliases=["b"])
def backup(file: pathlib.Path = yuio.app.positional()):
    """
    Move ``file`` to ``file.bak``.

    """

    bak = file.parent / (file.name + ".bak")
    shutil.copy(file, bak)

@main.subcommand(aliases=["r"])
def restore(file: pathlib.Path = yuio.app.positional()):
    """
    Move ``file.bak`` to ``file``.

    """
    bak = file.parent / (file.name + ".bak")
    shutil.rmtree(file, ignore_errors=True)
    shutil.move(str(bak), file)

if __name__ == "__main__":
    main.run()
