import subprocess

import pytest

from .conftest import extract_results


@pytest.mark.full
@pytest.mark.linux
def test_zsh(test_cases, data_regression):
    subprocess.check_call(["comptest", "--completions", "zsh"])

    results = []
    for _, prefix_len, _, args, orig in test_cases:
        print(args)
        line = " ".join(args)
        # Repeat left arrow keystroke to get to the desired cursor position.
        line += "\x1b[D" * (len(line) - prefix_len)
        try:
            result = subprocess.check_output(
                [
                    "zsh",
                    "test.zsh",
                    "comptest " + line,
                ],
            ).decode()
        except subprocess.CalledProcessError as e:
            results.append(dict(cmd=orig, err=str(e)))
        else:
            results.append(dict(cmd=orig, results=extract_results(result)))
    data_regression.check(results)
