import time
import random
import threading

import yuio


def install_package(package: str, task: yuio.io.Task):
    time.sleep(random.randint(0, 30) / 10)

    sleep_time = random.randint(2, 7) / 10

    with task.subtask(package) as pkg_task:
        pkg_task.comment('downloading')

        for i in range(10):
            pkg_task.progress(i / 10)
            time.sleep(sleep_time)

            if random.randint(1, 70) <= 5:
                yuio.io.warning('Warning: connection lost, retrying')

        pkg_task.progress(None)
        pkg_task.comment('installing')

        time.sleep(random.randint(10, 30) / 10)


if __name__ == '__main__':
    yuio.io.setup()

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
        time.sleep(random.randint(5, 20) / 10)

        threads = []

        for package in packages:
            thread = threading.Thread(
                target=install_package, args=(package, task))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

    yuio.io.info('<c:success>TADA!</c>')
