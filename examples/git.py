import dataclasses
import pathlib

import yuio.git
import yuio.io


if __name__ == '__main__':
    repo = yuio.git.Repo(pathlib.Path(__file__).parent.parent)

    status = repo.status()

    yuio.io.heading('Repository status')

    for k, v in dataclasses.asdict(status).items():
        if k != 'changes':
            yuio.io.info('%s: <c:code>%s</c>', k, v)
        else:
            pass

    yuio.io.heading('Changes')

    if changes := status.changes:
        for change in changes:
            path = change.path if change.path_from is None else f'{change.path_from} -> {change.path}'
            yuio.io.info('%s: <c:code>%s%s</c>', path, change.staged.value, change.tree.value)
    else:
        yuio.io.info('No files were changed!')

    yuio.io.heading('Recent log')

    if log := repo.log(max_entries=5):
        for commit in log:
            yuio.io.info('%s <c:code>[%s <%s>]</c>', commit.title, commit.author, commit.author_email)
    else:
        yuio.io.info('Log is empty!')
