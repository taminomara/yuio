# Contributing to Yuio

## Set up your environment

We use [`uv`] and [`poe`] to run tasks, but it is possible to use pure pip as well.

[`uv`]: https://docs.astral.sh/uv/
[`poe`]: https://poethepoet.natn.io/index.html

### Using pip

1. Create a virtual environment with python `3.13` or newer
   (some of dev tools don't work with older pythons).

2. Make sure your pip is up to date:

   ```shell
   pip install -U pip
   ```

2. Install Yuio in development mode, and install dev dependencies:

   ```shell
   pip install -e . --group dev
   ```

3. Install pre-commit hooks:

   ```shell
   prek install
   ```

4. [Install `poe`], either globally or in virtual environment:

   ```shell
   pip install poethepoet
   ```

[Install `poe`]: https://poethepoet.natn.io/installation.html

### Using uv

1. Sync your virtual environment:

   ```shell
   uv sync
   ```

2. Install pre-commit hooks:

   ```shell
   uv run prek install
   ```

3. [Install `poe`] if you don't have it already:

   ```shell
   uv tool install poethepoet
   ```


## Run commands

We use `poe` for most of the tasks:

```shell
poe lint  # Lint and fix code style.
poe test  # Run tests.
poe test-all  # Run tests for all pythons.
poe test-extra  # Run tests for all pythons, including slow tests.
```

You can see all commands in `poe`'s help:

```shell
poe --help
```

Note: the full test suite requires `bash`, `zsh`, `fish`, and `pwsh`
installed on your system.


## Build docs

To build docs, you'll need to install a latest [`VHS`] release.
If you run linux, [`sphinx-vhs`] will download the binaries for you,
otherwise you will have to install it yourself. Note that if you're running WSL
or other system that doesn't have a browser,
you might need to install additional packages:

```shell
sudo apt-get update
sudo apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxkbcommon0 libxdamage1 libgbm1 libpango1.0-0 libasound2
```

After that, use `poe` commands:

```shell
poe doc  # Build HTML.
poe doc-watch  # Run sphinx-autobuild.
```

The first build will take a couple of minutes to record terminal GIFs.

[`VHS`]: https://github.com/charmbracelet/vhs?tab=readme-ov-file#installation
[`sphinx-vhs`]: https://github.com/taminomara/sphinx-vhs
