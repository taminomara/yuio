#!/usr/bin/env python3

import pathlib
import re

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

    dry_run: bool = False


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

    if repo.status().has_changes:
        yuio.io.error(
            'Your repository has uncommitted changes. '
            'Either commit them or stash them.'
        )
        exit(1)

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

    changelog = (
        f'# Release parameters:\n'
        f'# \n'
        f'# Release version ..... {next_version}\n'
        f'# Release branch ...... {branch}\n'
        f'# Commit .............. {commit.orig_ref} ({commit.short_hash})\n'
        f'\n'
    )

    if latest_version is not None:
        for entry in repo.log(f'{latest_version}..{commit}', max_entries=None):
            changelog += f'- {entry.title} (by {entry.author})\n'

    changelog = yuio.io.edit(RELEASE_HEADER + changelog)
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
            f'# Changelog\n\n*{next_version}:*\n\n{changelog}\n',
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

    with yuio.io.Task('Committing changes'):
        repo.git('add', '.')
        repo.git('commit', '-m', f'Release {next_version}')

    yuio.io.info('Ready to create a release tag.')
    yuio.io.info('Feel free to look around and add changes before proceeding.')

    while True:
        if not yuio.io.ask('Do you want to proceed?', parser=yuio.parse.Bool()):
            yuio.io.error('Aborting release.')
            exit(1)

        if not repo.status().has_changes:
            break

        yuio.io.error(
            'Your repository has uncommitted changes. '
            'Either commit them or stash them before proceeding.'
        )

    with yuio.io.Task('Creating tag <c:code>%s</c>', next_version):
        repo.git('tag', next_version)

    yuio.io.info('Release branch and tag are ready to be published.')

    if not config.dry_run:
        with yuio.io.Task('Pushing branch and tags to origin'):
            repo.git('push', '-u', 'origin', branch, next_version)

        yuio.io.info('')
        yuio.io.info('<c:success>Release branch is published.</c>')
        yuio.io.info('')
        yuio.io.info('You can view release progress in the github CI,')
        yuio.io.info(
            'see <c:code>'
            'https://github.com/taminomara/yuio/actions?query=branch:%s</c>',
            next_version
        )
        yuio.io.info('')
    else:
        yuio.io.info('<c:success>Dry run is completed successfully.</c>')
        yuio.io.info('')
        yuio.io.info('Release branch and tags were created,')
        yuio.io.info('but were not pushed to the repo.')
        yuio.io.info('')
        yuio.io.info('To publish release to the repo, run:')
        yuio.io.info('<c:code>git push -u origin %s %s</c>', branch, next_version)
        yuio.io.info('')
        yuio.io.info('To roll back the repository, run:')
        yuio.io.info('<c:code>git checkout -f main</c>')
        yuio.io.info('<c:code>git branch -D %s</c>', branch)
        yuio.io.info('<c:code>git tag -d %s</c>', next_version)
        yuio.io.info('')


if __name__ == '__main__':
    main()
