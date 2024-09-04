import pathlib
import shutil
import yuio.app

@yuio.app.app
def main():
    pass

main.epilog = """
# usage examples

- this will copy `./prod.sqlite3` to `./prod.sqlite3.bak`:

  ```bash
  python main.py backup ./prod.sqlite3
  ```

- this will move `./prod.sqlite3.bak` to `./prod.sqlite3`:

  ```bash
  python main.py restore ./prod.sqlite3
  ```

"""

@main.subcommand(aliases=["b"])
def backup(file: pathlib.Path = yuio.app.positional()):
    bak = file.parent / (file.name + ".bak")
    shutil.copy(file, bak)

@main.subcommand(aliases=["r"])
def restore(file: pathlib.Path = yuio.app.positional()):
    bak = file.parent / (file.name + ".bak")
    shutil.rmtree(file, ignore_errors=True)
    shutil.move(str(bak), file)

if __name__ == "__main__":
    main.run()
