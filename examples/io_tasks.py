import logging
import time

import yuio.io


def download(package):
    logging.debug("%s: fetching versions", package)
    time.sleep(0.7)
    logging.debug("%s: will use latest version", package)
    time.sleep(0.4)
    logging.debug("%s: downloading package...", package)
    time.sleep(0.9)
    logging.info("%s: download successful", package)
    time.sleep(0.1)


def install(package):
    logging.debug("%s: unpacking %s.tar.gz into %s", package, package, package)
    time.sleep(0.4)
    logging.debug("%s: running `configure`", package)
    time.sleep(0.4)
    logging.debug("%s: `configure` successful", package)
    time.sleep(0.2)
    logging.debug("%s: building a package", package)
    time.sleep(1.2)
    logging.debug("%s: build successful", package)
    time.sleep(0.2)
    logging.debug("%s: installing a package to `/usr/local`", package)
    time.sleep(0.3)
    logging.info("%s: install successful", package)
    time.sleep(0.1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, handlers=[yuio.io.Handler()])

    packages = [
        "pyenv",
        "virtualenv",
        "yuio",
    ]

    yuio.io.heading("Yuio's tasks and logging showcase")
    yuio.io.info("Going to install some packages to demonstrate you tasks and logging!")

    with yuio.io.Task("Installing packages") as task:
        # A bit of work.
        time.sleep(0.5)

        # `task.iter` will update progress as we iterate over packages.
        for package in task.iter(packages):
            # Set task's comment.
            task.comment("downloading %s", package)

            # Some heavy work.
            download(package)

            # Update task's comment.
            task.comment("installing %s", package)

            # More heavy work.
            install(package)

        time.sleep(0.3)

    yuio.io.success("Successfully installed %s", yuio.io.JoinStr(packages))
