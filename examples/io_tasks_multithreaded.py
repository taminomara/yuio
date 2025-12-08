import threading
import time

import yuio.io


def install_package(package: str, task: yuio.io.Task):
    time.sleep(0.7)

    with task.subtask(package) as pkg_task:
        # Set task's comment.
        pkg_task.comment("downloading")

        for i in range(101):
            # Set progress as percentage, just for demonstration.
            pkg_task.progress(i / 100)

            time.sleep(0.05)

        # Clear progress, update task's comment.
        pkg_task.progress(None)
        pkg_task.comment("installing")

        time.sleep(1.6)


if __name__ == "__main__":
    packages = [
        "htop",
        "pyenv",
        "virtualenv",
        "node",
        "rust",
        "ruby",
        "cpp",
    ]

    yuio.io.heading("Yuio's tasks showcase")
    yuio.io.info("Going to install some packages to demonstrate you progressbars!")

    with yuio.io.Task("Installing packages") as task:
        time.sleep(2)

        threads = []

        for package in packages:
            thread = threading.Thread(
                target=install_package, args=(package, task), daemon=True
            )
            thread.start()
            threads.append(thread)

            time.sleep(0.3)

        for thread in threads:
            thread.join()

    yuio.io.success("Successfully installed %s", yuio.io.JoinStr(packages))
