# Contributing to Yuio

## Set up your environment

1. Check out the repo:

   ```shell
   git clone git@github.com:taminomara/yuio.git
   ```

2. Create a virtual environment with python `3.12` or newer
   (some of dev tools don't work with older pythons).

3. Install Yuio in development mode, and install dev dependencies:

   ```shell
   pip install -e .[dev]
   ```

4. Install pre-commit hooks:

   ```shell
   pre-commit install
   ```

## Run tests

To run tests, simply run `pytest` and `pyright`:

```shell
pytest  # Run unit tests.
pyright  # Run type check.
```

To fix code style, you can manually run pre-commit hooks:

```shell
pre-commit run -a  # Fix code style.
```

To generate HTML coverage report
(will be available in the `htmlcov` directory):

```shell
pytest --cov=yuio --cov-report=html  # Generate coverage.
open ./htmlcov/index.html  # Open the generated page.
```


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
