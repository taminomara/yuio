import os

import pytest


@pytest.fixture
def save_env():
    env = dict(os.environ)

    yield

    os.environ.clear()
    os.environ.update(env)


@pytest.fixture
def clear_env(save_env):
    os.environ.clear()
