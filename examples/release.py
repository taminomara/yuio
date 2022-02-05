#!/usr/bin/env python3

import pathlib
import re

import yuio


class Config(yuio.config.Config):
    repo_path: pathlib.Path = yuio.config.field(
        default=pathlib.Path(__file__).parent.parent.resolve(),
        parser=yuio.parse.GitRepo(),
        help='path to the git repo with project'
    )


def find_latest_version(repo: yuio.git.Git):
    text = repo.git('tag', '--list', '--sort=-version:refname')
    tags = text.decode().split('\n')

    for tag in tags:
        match = re.match(r'^v(\d+)\.(\d+)\.(\d+)$', tag)
        if match is not None:
            return tag, f'v{match.group(1)}.{int(match.group(2)) + 1}.0'

    return None, None


def main():
    yuio.log.setup()

    config = Config()
    config.update(Config.load_from_env())
    config.update(Config.load_from_args())

    yuio.log.debug('config = %r', config)

    if not config.repo_path.joinpath('pyproject.toml').is_file():
        yuio.log.error(
            'File <c:code>pyproject.toml</c> wasn\'t found in the repository.'
        )
        exit(1)

    repo = yuio.git.Git(config.repo_path)

    # if repo.status().has_changes:
    #     yuio.log.error(
    #         'Your repository has uncommitted changes. '
    #         'Either commit them or stash them.'
    #     )
    #     exit(1)

    latest_version, next_version = find_latest_version(repo)

    head = repo.show('HEAD')
    assert head is not None

    commit = yuio.log.ask(
        'Enter the commit at which you want to cut the release',
        default=head,
        parser=yuio.git.RefParser(repo),
    )

    next_version = yuio.log.ask(
        'Enter the release tag',
        default=next_version,
        parser=yuio.parse.Regex(yuio.parse.Str(), r'^v\d+\.\d+\.\d+$')
    )

    branch = f'release/{next_version}'

    branch = yuio.log.ask(
        'Enter the name of the release branch',
        default=branch,
    )

    yuio.log.info('')
    yuio.log.info('Release parameters:')
    yuio.log.info('')
    yuio.log.info('Release version .. <c:code>%s</c>', next_version)
    yuio.log.info('Release branch ... <c:code>%s</c>', branch)
    yuio.log.info('Commit ........... <c:code>%s</c> (<c:code>%s</c>)',
                  commit.orig_ref, commit.short_hash)
    yuio.log.info('')
    yuio.log.info('Release changelog:')
    yuio.log.info('')
    if latest_version is not None:
        for entry in repo.log(f'{latest_version}..{commit}', max_entries=None):
            yuio.log.info(
                '- %s (by <c:note>%s</c>)', entry.title, entry.author
            )
    yuio.log.info('')

    if not yuio.log.ask('Do you want to proceed?', parser=yuio.parse.Bool()):
        yuio.log.info('Aborting release.')
        exit(0)

    with yuio.log.Task('Checking out <c:code>%s</c>', commit.short_hash):
        repo.git('checkout', commit.hash)

    with yuio.log.Task('Creating release branch'):
        repo.git('branch', branch)
        repo.git('checkout', branch)

    with yuio.log.Task('Modifying <c:code>pyproject.toml</c>'):
        pyproject = config.repo_path.joinpath('pyproject.toml')
        text = pyproject.read_text()
        text = re.sub(
            r'^version\s*=\s*(?P<q>["\'])\d+\.\d+\.\d+(?P=q)$',
            f'version = "{next_version[1:]}"',
            text,
            flags=re.MULTILINE
        )
        pyproject.write_text(text)

    with yuio.log.Task('Committing <c:code>pyproject.toml</c>'):
        repo.git('add', 'pyproject.toml')
        repo.git('commit', '-m', f'Release {next_version}')

    with yuio.log.Task('Creating tag <c:code>%s</c>', next_version):
        repo.git('tag', next_version)

    yuio.log.info('Release branch is ready to be published.')

    if not yuio.log.ask(
        'Do you want to push the release branch '
        'to <c:code>origin</c>?',
        parser=yuio.parse.Bool()
    ):
        yuio.log.info(
            'Nothing more to do. '
            'Push the release branch <c:code>%s</c> and tag <c:code>%s</c> '
            'to origin to start deployment.',
            branch,
            next_version
        )
        exit(0)

    with yuio.log.Task('Pushing branch and tags to origin'):
        repo.git('push', '-u', 'origin', branch, next_version)

    yuio.log.info('<c:success>Release branch is published.</c>')
    yuio.log.info('You can view release progress in the github CI,')
    yuio.log.info(
        'see <c:code>'
        'https://github.com/taminomara/yuio/actions?query=branch:%s</c>',
        next_version
    )


if __name__ == '__main__':
    main()
