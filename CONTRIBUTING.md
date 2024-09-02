# Contributing to Yuio

## Set up your environment

1. Check out the repo:

   ```shell
   git clone git@github.com:taminomara/yuio.git
   ```

2. Create a virtual environment.

3. Install Yuio in development mode, and install dev dependencies:

   ```shell
   pip install -e .[test,doc]
   ```

4. Install pre-commit hooks:

   ```
   pre-commit install
   ```

## Run tests

To run tests, simply invoke `pytest` in the project root:

```shell
pytest
```

To check typing, invoke `pyright`:

```shell
pyright
```

To fix the codestyle, run:

```shell
black . && isort .
```

Code formatting tools run automatically before every commit.


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

After that, just run `sphinx` as usual:

```shell
cd docs/
make html
```

The first build will take a couple of minutes to record terminal GIFs.

[`VHS`]: https://github.com/charmbracelet/vhs?tab=readme-ov-file#installation
[`sphinx-vhs`]: https://github.com/taminomara/sphinx-vhs