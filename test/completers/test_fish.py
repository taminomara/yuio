import shlex
import subprocess

import pytest

from .conftest import extract_results

# We mock `commandline` instead of using `complete --do-complete` because the later
# doesn't give precise control over cursor position.
SCRIPT = """
function commandline
    argparse p c x t C -- $argv
    if set -q _flag_C
        printf '%s' {token_prefix_len}
    else if set -q _flag_x
        echo "comptest"
        for arg in {quoted_args}
            printf '%s\\n' $arg
        end
    else if set -q _flag_t
        printf '%s\\n' '{current_token}'
    else
        echo "This mock doesn't support flags $argv" 1>&2
        return 1
    end
end

source ./test.fish
"""


@pytest.mark.full
@pytest.mark.linux
def test_fish(test_cases, data_regression):
    subprocess.check_call(["comptest", "--completions", "fish"])

    results = []
    for cword, _, token_prefix_len, args, orig in test_cases:
        print(args, cword, repr(args[cword]), token_prefix_len)
        print(" ".join(map(shlex.quote, args[:cword])))
        try:
            result = subprocess.check_output(
                [
                    "fish",
                    "-c",
                    SCRIPT.format(
                        quoted_args=" ".join(map(shlex.quote, args[:cword])),
                        token_prefix_len=token_prefix_len,
                        current_token=args[cword],
                    ),
                ],
                stderr=subprocess.STDOUT,
            ).decode()
        except subprocess.CalledProcessError as e:
            results.append(dict(cmd=orig, err=e.output.decode()))
        else:
            results.append(dict(cmd=orig, results=extract_results(result)))

    data_regression.check(results)
