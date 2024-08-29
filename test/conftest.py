import os
import sys

import pytest


@pytest.fixture
def save_env():
    env = dict(os.environ)

    yield

    os.environ.clear()
    os.environ.update(env)


@pytest.fixture
def save_stdin():
    stdin = sys.stdin

    yield

    sys.stdin = stdin
