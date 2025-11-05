import shlex
import subprocess

import pytest

from .conftest import extract_results

SCRIPT = """
COMP_CWORD={cword}
COMP_POINT={prefix_len}
COMP_WORDS=(comptest {args})
COMP_LINE="${{COMP_WORDS[*]}}"
. ./test.bash
"""


@pytest.mark.full
@pytest.mark.linux
@pytest.mark.darwin
def test_bash(test_cases, data_regression):
    subprocess.check_call(["comptest", "--completions"])

    results = []
    for cword, prefix_len, args, orig in test_cases:
        try:
            result = subprocess.check_output(
                [
                    "bash",
                    "-lic",
                    SCRIPT.format(
                        cword=cword + 1,
                        prefix_len=prefix_len + 9,
                        args=" ".join(map(shlex.quote, args)),
                    ),
                ]
            ).decode()
        except subprocess.CalledProcessError as e:
            results.append(dict(cmd=orig, err=str(e)))
        else:
            results.append(dict(cmd=orig, results=extract_results(result)))
    data_regression.check(results)
