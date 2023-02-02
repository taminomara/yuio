import dataclasses
import pathlib

import yuio.git
import yuio.io


if __name__ == '__main__':
    repo = yuio.git.Repo(pathlib.Path(__file__).parent.parent)

    status = repo.status()

    yuio.io.info('<c:heading>Repo status:</c>')
    for k, v in dataclasses.asdict(status).items():
        if k != 'changes':
            yuio.io.info('  %s: <c:code>%s</c>', k, v)
        else:
            pass

    yuio.io.info('<c:heading>Changes:</c>')
    for change in status.changes:
        path = change.path if change.path_from is None else f'{change.path_from} -> {change.path}'
        yuio.io.info('  %s: <c:code>%s%s</c>', path, change.staged.value, change.tree.value)

    yuio.io.info('<c:heading>Recent log:</c>')
    for commit in repo.log(max_entries=5):
        yuio.io.info('  %s <c:code>[%s <%s>]</c>', commit.title, commit.author, commit.author_email)
