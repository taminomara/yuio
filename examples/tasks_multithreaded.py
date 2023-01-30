import threading
import time

import yuio.io


def install_package(package: str, task: yuio.io.Task):
    time.sleep(0.7)

    with task.subtask(package) as pkg_task:
        # Set task's comment.
        pkg_task.comment('downloading')

        for i in range(10):
            # Set progress as percentage, just for demonstration.
            pkg_task.progress(i / 10)

            time.sleep(0.5)

        # Clear progres, update task's comment.
        pkg_task.progress(None)
        pkg_task.comment('installing')

        time.sleep(1.3)


if __name__ == '__main__':
    packages = [
        'htop',
        'pyenv',
        'virtualenv',
        'node',
        'rust',
        'ruby',
        'cpp@20',
    ]

    yuio.io.info('Going to install some packages '
                 'to demonstrate you progressbars!')

    with yuio.io.Task('Installing packages') as task:
        time.sleep(0.5)

        threads = []

        for package in packages:
            thread = threading.Thread(
                target=install_package, args=(package, task))
            thread.start()
            threads.append(thread)

            time.sleep(0.3)

        for thread in threads:
            thread.join()

    yuio.io.info('<c:success>TADA!</c>')
