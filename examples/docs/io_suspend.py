import subprocess
import yuio.app
import yuio.io

@yuio.app.app
def main():
    with yuio.io.SuspendOutput():
        subprocess.check_call(["git", "status"])

if __name__ == "__main__":
    main.run()
