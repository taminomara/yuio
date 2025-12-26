import pathlib
import shutil
import yuio.app

@yuio.app.app
def main():
    pass

@main.subcommand
def backup(file: pathlib.Path = yuio.app.positional()):
    bak = file.parent / (file.name + ".bak")
    shutil.copy(file, bak)

@main.subcommand
def restore(file: pathlib.Path = yuio.app.positional()):
    bak = file.parent / (file.name + ".bak")
    shutil.rmtree(file, ignore_errors=True)
    shutil.move(str(bak), file)

if __name__ == "__main__":
    main.run()
