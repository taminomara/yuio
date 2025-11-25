#!/usr/bin/env bash

set -eo pipefail

. /usr/share/bash-completion/bash_completion
. ${XDG_DATA_HOME}/bash-completion/completions/comptest comptest

COMP_TYPE=9
COMP_KEY=$'\t'
COMPREPLY=()

__yuio_compl__comptest__complete comptest

echo "--BEGIN RESULTS--"
if (( ${#COMPREPLY} > 0 )); then
    printf "%s\n" "${COMPREPLY[@]}"
fi
echo "--END RESULTS--"
