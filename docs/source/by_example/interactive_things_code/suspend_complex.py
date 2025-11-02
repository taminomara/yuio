import time
import subprocess
import yuio.app
import yuio.io

@yuio.app.app
def main():
    with yuio.io.Task("Performing some task"):
        time.sleep(1)

        # All progress bars, prints, and so on are suspended
        # inside of this context manager.
        with yuio.io.SuspendOutput() as o:
            # But you can manually bypass output suspension.
            o.info("Running `git status`:")

            subprocess.check_call(["git", "status"])

        time.sleep(1)

if __name__ == "__main__":
    main.run()
