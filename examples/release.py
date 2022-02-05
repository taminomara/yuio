#!/usr/bin/env python3

import pathlib
import re
import subprocess

import yuio

RELEASE_HEADER = """# Please enter the release changelog. Lines starting
# with '#' will be ignored, and an empty changelog aborts the release.

"""


class Config(yuio.config.Config):
    repo_path: pathlib.Path = yuio.config.field(
        default=pathlib.Path(__file__).parent.parent.resolve(),
        parser=yuio.parse.GitRepo(),
        help='path to the git repo with project'
    )


def find_latest_version(repo: yuio.git.Repo):
    text = repo.git('tag', '--list', '--sort=-version:refname')
    tags = text.decode().split('\n')

    for tag in tags:
        match = re.match(r'^v(\d+)\.(\d+)\.(\d+)$', tag)
        if match is not None:
            return tag, f'v{match.group(1)}.{int(match.group(2)) + 1}.0'

    return None, None


def main():
    yuio.io.setup()

    config = Config()
    config.update(Config.load_from_env())
    config.update(Config.load_from_args())

    yuio.io.debug('config = %r', config)

    if not config.repo_path.joinpath('pyproject.toml').is_file():
        yuio.io.error(
            'File <c:code>pyproject.toml</c> wasn\'t found in the repository.'
        )
        exit(1)

    if not config.repo_path.joinpath('CHANGELOG.md').is_file():
        yuio.io.error(
            'File <c:code>CHANGELOG.md</c> wasn\'t found in the repository.'
        )
        exit(1)

    repo = yuio.git.Repo(config.repo_path)

    # if repo.status().has_changes:
    #     yuio.io.error(
    #         'Your repository has uncommitted changes. '
    #         'Either commit them or stash them.'
    #     )
    #     exit(1)

    latest_version, next_version = find_latest_version(repo)

    head = repo.show('HEAD')
    assert head is not None

    commit = yuio.io.ask(
        'Enter the commit at which you want to cut the release',
        default=head,
        parser=yuio.git.RefParser(repo),
    )

    next_version = yuio.io.ask(
        'Enter the release tag',
        default=next_version,
        parser=yuio.parse.Regex(yuio.parse.Str(), r'^v\d+\.\d+\.\d+$')
    )

    branch = f'release/{next_version}'

    branch = yuio.io.ask(
        'Enter the name of the release branch',
        default=branch,
    )

    yuio.io.info('')
    yuio.io.info('Release parameters:')
    yuio.io.info('')
    yuio.io.info('Release version ..... <c:code>%s</c>', next_version)
    yuio.io.info('Release branch ...... <c:code>%s</c>', branch)
    yuio.io.info('Commit .............. <c:code>%s</c> (<c:code>%s</c>)',
                 commit.orig_ref, commit.short_hash)
    yuio.io.info('')
    yuio.io.info('Release changelog:')
    yuio.io.info('')

    changelog = RELEASE_HEADER
    if latest_version is not None:
        for entry in repo.log(f'{latest_version}..{commit}', max_entries=None):
            yuio.io.info(
                '- %s (by <c:note>%s</c>)', entry.title, entry.author
            )
            changelog += f'- {entry.title} (by {entry.author})\n'
    yuio.io.info('')

    if not yuio.io.ask('Do you want to proceed?', parser=yuio.parse.Bool()):
        yuio.io.error('Aborting release.')
        exit(1)

    if yuio.io.ask(
        'Do you want to edit changelog?',
        parser=yuio.parse.Bool(),
        default=True,
    ):
        changelog = yuio.io.edit(changelog)
        if not changelog:
            yuio.io.error('Got empty changelog, aborting release.')
            exit(1)
        else:
            yuio.io.info('Changelog edit successful.')

    with yuio.io.Task('Checking out <c:code>%s</c>', commit.short_hash):
        repo.git('checkout', commit.hash)

    with yuio.io.Task('Creating release branch'):
        repo.git('branch', branch)
        repo.git('checkout', branch)

    with yuio.io.Task('Modifying <c:code>CHANGELOG.md</c>'):
        file = config.repo_path.joinpath('CHANGELOG.md')
        text = file.read_text()
        text = re.sub(
            r'^# Changelog\n',
            f'# Changelog\n\n*{next_version}:*\n\n{changelog}',
            text,
            flags=re.MULTILINE
        )
        file.write_text(text)

    with yuio.io.Task('Modifying <c:code>pyproject.toml</c>'):
        file = config.repo_path.joinpath('pyproject.toml')
        text = file.read_text()
        text = re.sub(
            r'^version\s*=\s*(?P<q>["\'])\d+\.\d+\.\d+(?P=q)$',
            f'version = "{next_version[1:]}"',
            text,
            flags=re.MULTILINE
        )
        file.write_text(text)

    with yuio.io.Task('Committing <c:code>pyproject.toml</c>'):
        repo.git('add', '.')
        repo.git('commit', '-m', f'Release {next_version}')

    with yuio.io.Task('Creating tag <c:code>%s</c>', next_version):
        repo.git('tag', next_version)

    yuio.io.info('Release branch is ready to be published.')

    if not yuio.io.ask(
        'Do you want to push the release branch '
        'to <c:code>origin</c>?',
        parser=yuio.parse.Bool()
    ):
        yuio.io.info(
            'Nothing more to do. '
            'Push the release branch <c:code>%s</c> and tag <c:code>%s</c> '
            'to origin to start deployment.',
            branch,
            next_version
        )
        exit(0)

    with yuio.io.Task('Pushing branch and tags to origin'):
        repo.git('push', '-u', 'origin', branch, next_version)

    yuio.io.info('<c:success>Release branch is published.</c>')
    yuio.io.info('You can view release progress in the github CI,')
    yuio.io.info(
        'see <c:code>'
        'https://github.com/taminomara/yuio/actions?query=branch:%s</c>',
        next_version
    )


if __name__ == '__main__':
    main()
