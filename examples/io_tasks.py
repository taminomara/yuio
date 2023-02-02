import time

import yuio.io

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
        time.sleep(0.5)

        # `task.iter` will update progress as we iterate over packages.
        for package in task.iter(packages):
            # Set task's comment.
            task.comment(f'downloading {package}')

            # Some heavy work.
            time.sleep(0.4)

            # Update task's comment.
            task.comment(f'installing {package}')

            # More heavy work.
            time.sleep(0.6)
