import time
import random

import yuio

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

    with yuio.io.Task('Installing packages') as task:
        # A bit of work.
        time.sleep(random.randint(5, 10) / 10)

        for i, package in enumerate(packages):
            task.progress((i, len(packages)))

            task.comment(f'downloading {package}')

            # Some heavy work.
            time.sleep(random.randint(5, 20) / 10)

            task.comment(f'installing {package}')

            # More heavy work.
            time.sleep(random.randint(5, 20) / 10)
