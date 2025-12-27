#!/usr/bin/env fish

source $XDG_DATA_HOME/fish/vendor_completions.d/comptest.fish

echo "--BEGIN RESULTS--"
__yuio_compl__comptest__complete
echo "--END RESULTS--"
