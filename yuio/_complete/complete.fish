# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# Do not edit: this file was generated automatically by Yuio @version@.

complete -c '@true_prog@' -f -a '(__yuio_compl__@prog@__complete)'

function __yuio_compl__@prog@__complete
    set words (commandline -pcx; commandline -ct)

    if set -q __yuio_compl__@prog@__cache__words \
            && [ "$words" = "$__yuio_compl__@prog@__cache__words" ]
        printf '%s\n' $__yuio_compl__@prog@__cache__result
        return 0
    end

    set cur ''
    set word ''

    # We parse command line manually to follow how argparse handles its arguments.

    # Parsing state:
    set cmd ''            # Current (sub)command.
    set opt ''            # Current option.
    set nargs 0           # How many nargs left to process in the current option.
    set free_opt 0        # Current free option.
    set free_nargs 0      # How many nargs left to process in the current free option.
    set free_opts_only '' # Set to `1` when we've seen an `--` token.
    set prefix ''         # For options in form `--x=y`, this is the prefix `--x=`.

    set free_nargs (__yuio_compl__@prog@__load_nargs $cmd $free_opt) || return

    for cur in $words[2..]
        if [ -z $free_opts_only ] && [ $word = '--' ]
            # We're completing free args form now on.
            set free_opts_only 1
        else if [ -z $free_opts_only ] && string match -q -- '-*' $word
            # Previous word was an option, so in this position we expect option's args,
            # if there are any.
            set opt $word
            set nargs (__yuio_compl__@prog@__load_nargs $cmd $opt) || return
            if [ $nargs = '-' ]  # for options like --help or --version
                return 0
            end
        else if [ -z $opt ] && [ $free_nargs = 0 ]
            # We've exhausted current free args.
            set free_opt (math $free_opt + 1 )
            set free_nargs (__yuio_compl__@prog@__load_nargs $cmd $free_opt) || return
        else if string match -q -- '-*' $opt && [ $nargs = 0 ]
            # We've exhausted nargs for the current option.
            set opt ''
        else if [ $opt = 'c' ]
            # Previous word was a subcommand, so load it now.
            set cmd "$cmd/$word"
            set opt ''
            set nargs 0
            set free_opt 0
            set free_nargs 0
            set free_nargs (__yuio_compl__@prog@__load_nargs $cmd $free_opt) || return
        end

        set word "$cur"
        set prefix ''

        if [ -z $free_opts_only ] && string match -q -- '--*=*' $word
            # This is a long option with a value (i.e. `--foo=bar`).
            # In this position, we complete option's value.
            set split (string split -m1 -- '=' $word)
            set opt $split[1]
            set prefix "$opt="
            set word $split[2]
            set nargs 0
        else if [ -z $free_opts_only ] && string match -q -- '-*' $word
            # This is an option without a value (i.e. `-f` or `--foo`).
            # In this position we complete the option itself.

            # TODO: argparse has special handling for options that look
            #       like negative numbers.
            # TODO: handle merged short options and short options with values.
            set opt ''
            set nargs 0
        else if [ $nargs = '+' ]
            # This is a mandatory argument for an option
            # that takes unlimited arguments.
            set nargs '*'  # The rest arguments are optional.
        else if [ $nargs = '*' ]
            # This is an optional argument for an option
            # that takes unlimited arguments.
            :  # Do nothing, i.e. continue eating option arguments.
        else if [ $nargs = '?' ]
            # This is an optional argument for an option that takes
            # up to one argument.
            set nargs 0
        else if string match -qr -- '^\d+$' $nargs && [ $nargs -gt 0 ]
            # This is a mandatory argument for an option that takes
            # up to `$nargs` arguments.
            set nargs (math $nargs - 1 )
        else if [ $free_nargs = '+' ]
            # This is a mandatory free argument.
            set opt ''
            set free_nargs '*'  # The rest free arguments are optional.
        else if [ $free_nargs = '*' ]
            # This is an optional free argument.
            set opt ''
        else if [ $free_nargs = '?' ]
            # This is an optional free argument.
            # There are no more free arguments in this spec, load the next one.
            set opt ''
            set free_nargs 0
        else if string match -qr -- '^\d+$' $free_nargs && [ $free_nargs -gt 0 ]
            # This is a mandatory free argument.
            set opt ''
            set free_nargs (math $free_nargs - 1 )
        else
            # This is not a free argument, this is a subcommand.
            set opt 'c'
            set nargs 0
        end
    end

    set -g __yuio_compl__@prog@__compspec_i 6

    set cursor (commandline -Ct)
    if [ -n $word ]
        set word_prefix ''
        [ $cursor -gt 0 ] && set word_prefix (string sub -e $cursor -- $word)
        set word_suffix (string sub -s (math $cursor + 1) -- $word)
        set word (string unescape -- $word_prefix'__yuio_delim__'$word_suffix)
        set word_parts (string split -m1 -- '__yuio_delim__' $word)
        set word "$word_parts[1]""$word_parts[2]"
        set cursor (string length -- "$word_parts[1]")
    end

    if [ -z $opt ]
        if [ -z $free_opts_only ] && string match -q -- '-*' $word
            set result (__yuio_compl__@prog@__complete_opts $cmd) || return
        else
            # completing a free arg
            __yuio_compl__@prog@__load_compspec $cmd $free_opt || return
            set apos '0'
            if string match -qr -- '^\d+$' $__yuio_compl__@prog@__compspec[5] \
                    && string match -qr -- '^\d+$' $free_nargs
                set apos (math $__yuio_compl__@prog@__compspec[5] - $free_nargs)
            end
            set result (__yuio_compl__@prog@__complete_arg $word $cursor '' '' '' --apos=$apos) || return
        end
    else
        # compleing an option value
        __yuio_compl__@prog@__load_compspec $cmd $opt || return
        set apos 1
        if string match -qr -- '^\d+$' $__yuio_compl__@prog@__compspec[5] \
                && string match -qr -- '^\d+$' $nargs
            set apos (math $__yuio_compl__@prog@__compspec[5] - $nargs)
        end
        set result (__yuio_compl__@prog@__complete_arg $word $cursor $prefix '' '' --apos=$apos) || return
    end

    set -g __yuio_compl__@prog@__cache__words $words
    set -g __yuio_compl__@prog@__cache__result $result

    printf '%s\n' $__yuio_compl__@prog@__cache__result
end

function __yuio_compl__@prog@__load_nargs -a cmd -a opt
    __yuio_compl__@prog@__load_compspec $cmd $opt
    set nargs $__yuio_compl__@prog@__compspec[5]
    test -z $nargs && set nargs 0
    echo $nargs
end

function __yuio_compl__@prog@__load_compspec -a cmd -a opt
    set -g __yuio_compl__@prog@__compspec (
        awk -F '\t' -v cmd="$cmd" -v opt="$opt" \
            '
                $1==cmd {
                    split($2, options, " ");
                    for (i in options) {
                        if (options[i]==opt) {
                            print $0
                            exit
                        }
                    }
                }
            ' '@data@' | tr '\t' '\n'
    )
end

function __yuio_compl__@prog@__complete_opts -a cmd
    awk -F '\t' -v OFS='\t' -v cmd="$cmd" \
        '
            $1==cmd && $3 != "__yuio_hide__" {
                split($2, options, " ");
                for (i in options) {
                    print options[i], $3
                }
            }
        ' '@data@'
end

# Read compspec and apply it, adding results to compreply.
#
# This function requires `compspec_i` and `compspec` variables being set.
function __yuio_compl__@prog@__complete_arg -a word cursor prefix suffix desc
    set word "$argv[1]"
    set cursor "$argv[2]"
    set prefix "$argv[3]"
    set suffix "$argv[4]"
    set desc "$argv[5]"
    argparse skip apos= -- $argv[6..] || return

    if [ (count $__yuio_compl__@prog@__compspec) = 0 ]
        return 0
    end

    set completer (__yuio_compl__@prog@__compspec_pop) || return
    set size (__yuio_compl__@prog@__compspec_pop) || return

    __yuio_compl__@prog@__assert_int $size || return

    set end_index (math $__yuio_compl__@prog@__compspec_i + $size)

    if set -q _flag_skip
        __yuio_compl__@prog@__compspec_set_i $end_index || return
        return 0
    end

    switch $completer
        case f
            # complete files
            set ext (__yuio_compl__@prog@__compspec_pop) || return
            printf '%s\n' $prefix(__fish_complete_path $word $desc)$suffix
        case d
            # complete directories
            printf '%s\n' $prefix(__fish_complete_directories $word $desc)$suffix
        case c
            # complete choices
            set choices (__yuio_compl__@prog@__compspec_pop_n $size) || return
            printf '%s\n' $prefix$choices$suffix\t$desc
        case cd
            # complete choices with descriptions
            set half_size (math $size / 2)
            set choices (__yuio_compl__@prog@__compspec_pop_n $half_size) || return
            set descriptions (__yuio_compl__@prog@__compspec_pop_n $half_size) || return
            for i in (seq $half_size)
                printf '%s\n' $prefix$choices[$i]$suffix\t$descriptions[$i]
            end
        case g
            # complete git
            if command -v git > /dev/null && git rev-parse --is-inside-work-tree >/dev/null 2>&1
                set modes (__yuio_compl__@prog@__compspec_pop) || return
                set worktree ( git rev-parse --absolute-git-dir 2>/dev/null )
                if string match -q -- '*H*' $modes
                    for head in (HEAD ORIG_HEAD)
                        if [ -e $worktree/$head ]
                            printf '%s\n' $prefix$head$suffix\t'head'
                        end
                    end
                end
                if string match -q -- '*b*' $modes
                    for ref in (git for-each-ref --format='%(refname:short)' refs/heads)
                        printf '%s\n' $prefix$ref$suffix\t'local branch'
                    end
                end
                if string match -q -- '*r*' $modes
                    for ref in (git for-each-ref --format='%(refname:short)' refs/remotes)
                        printf '%s\n' $prefix$ref$suffix\t'remote branch'
                    end
                end
                if string match -q -- '*t*' $modes
                    for ref in (git for-each-ref --format='%(refname:short)' refs/tags)
                        printf '%s\n' $prefix$ref$suffix\t'tag'
                    end
                end
            end
        case l
            # complete list
            set delim (__yuio_compl__@prog@__compspec_pop) || return
            [ -z $delim ] && set delim ' '

            # split word by delim
            set word_prefix ''
            set word_suffix ''
            if [ -n $word ]
                [ $cursor -gt 0 ] && set word_prefix (string sub -e $cursor -- $word)
                set word_suffix (string sub -s (math $cursor + 1) -- $word)
            end
            set word_prefix_parts (string split -m1 -r -- $delim $word_prefix )
            [ (count $word_prefix_parts) -lt 2 ] && set -p word_prefix_parts ""
            [ -n "$word_prefix_parts[1]" ] && set word_prefix_parts[1] $word_prefix_parts[1]$delim
            set word_suffix_parts (string split -m1 -- $delim $word_suffix )
            set word_suffix_parts[2] "$delim$word_suffix_parts[2]"
            set word "$word_prefix_parts[2]$word_suffix_parts[1]"
            set cursor (string length -- "$word_prefix_parts[2]")
            set prefix $prefix"$word_prefix_parts[1]"
            set suffix "$word_suffix_parts[2]"$suffix
            __yuio_compl__@prog@__complete_arg $word $cursor $prefix $suffix $desc || return
        case lm
            # complete list with "supports many"
            set delim (__yuio_compl__@prog@__compspec_pop) || return

            # now just pass this to the underlying completer, because each positional
            # for "lm" mode is its own separate list.
            __yuio_compl__@prog@__complete_arg $word $cursor $prefix $suffix $desc || return
        case t
            # complete tuple
            set delim (__yuio_compl__@prog@__compspec_pop) || return
            [ -z $delim ] && set delim ' '

            set len (__yuio_compl__@prog@__compspec_pop) || return
            __yuio_compl__@prog@__assert_int $len || return

            # split word by delim
            set word_prefix ''
            set word_suffix ''
            if [ -n $word ]
                [ $cursor -gt 0 ] && set word_prefix (string sub -e $cursor -- $word)
                set word_suffix (string sub -s (math $cursor + 1) -- $word)
            end
            set word_prefix_parts (string split -m1 -r -- $delim $word_prefix )
            [ (count $word_prefix_parts) -lt 2 ] && set -p word_prefix_parts ""
            [ -n "$word_prefix_parts[1]" ] && set word_prefix_parts[1] $word_prefix_parts[1]$delim
            set word_suffix_parts (string split -m1 -- $delim $word_suffix )
            [ -n "$word_suffix_parts[2]" ] && set word_suffix_parts[2] $delim$word_suffix_parts[2]
            set word "$word_prefix_parts[2]$word_suffix_parts[1]"
            set cursor (string length -- "$word_prefix_parts[2]")
            set prefix $prefix"$word_prefix_parts[1]"
            set suffix "$word_suffix_parts[2]"$suffix

            # find out position in the tuple
            set pos (count (string split -- $delim "$word_prefix_parts[1]"))
            if [ $pos -le $len ]
                set i
                for i in (seq (math $pos - 1))
                    __yuio_compl__@prog@__complete_arg $word $cursor $prefix $suffix $desc --skip || return
                end
                [ $pos -lt $len ] && [ -z "$word_suffix_parts[2]" ] && set suffix $delim$suffix
                __yuio_compl__@prog@__complete_arg $word $cursor $prefix $suffix $desc || return
            end
        case tm
            # complete tuple with "supports many"
            set apos "$_flag_apos"
            [ -z $_flag_apos ] && set _flag_apos '1'

            set delim (__yuio_compl__@prog@__compspec_pop) || return

            set len (__yuio_compl__@prog@__compspec_pop) || return
            __yuio_compl__@prog@__assert_int $len || return

            # find out position in the tuple
            if [ $apos -le $len ]
                set i
                for i in (seq (math $apos - 1))
                    __yuio_compl__@prog@__complete_arg --skip || return
                end
                __yuio_compl__@prog@__complete_arg $word $cursor $prefix $suffix $desc || return
            end
        case a
            # complete alternatives
            set len (__yuio_compl__@prog@__compspec_pop) || return
            __yuio_compl__@prog@__assert_int $len || return
            set i
            for i in (seq $len)
                set desc (__yuio_compl__@prog@__compspec_pop)
                __yuio_compl__@prog@__complete_arg $word $cursor $prefix $suffix $desc || return
            end
        case cc
            # custom completer
            set words (commandline -pcx)
            set data (__yuio_compl__@prog@__compspec_pop) || return
            set choices ($words[1] --no-color --yuio-custom-completer-- $data $word) || return
            for choice in $choices
                set choice_parts (string split -r -m1 -- \t $choice)
                printf '%s\n' $prefix$choice_parts[1]$suffix\t$choice_parts[2]
            end
    end

    __yuio_compl__@prog@__compspec_set_i $end_index
end

function __yuio_compl__@prog@__compspec_pop
    __yuio_compl__@prog@__compspec_pop_n 1
end

function __yuio_compl__@prog@__compspec_pop_n -a n
    __yuio_compl__@prog@__assert_int $n || return

    set i (math $__yuio_compl__@prog@__compspec_i + $n)

    if [ $i -gt (math (count $__yuio_compl__@prog@__compspec) + 1) ];
        echo "$prog: $(status current-function): compspec index out of range" >&2
        status print-stack-trace >&2
        return 2
    end

    printf '%s\n' $__yuio_compl__@prog@__compspec[$__yuio_compl__@prog@__compspec_i..(math $i - 1)]
    set -g __yuio_compl__@prog@__compspec_i $i
end

function __yuio_compl__@prog@__compspec_set_i -a i
    __yuio_compl__@prog@__assert_int $i || return
    if [ $i -gt (math (count $__yuio_compl__@prog@__compspec) + 1) ]
        echo "$prog: $(status current-function): compspec index out of range" >&2
        status print-stack-trace >&2
        return 2
    else if [ $i -lt $__yuio_compl__@prog@__compspec_i ]
        echo "$prog: $(status current-function): moving backwards" >&2
        status print-stack-trace >&2
        return 2
    end

    set -g __yuio_compl__@prog@__compspec_i "$i"
end

function __yuio_compl__@prog@__assert_int
    for arg in $argv
      if not string match -qr -- '^\d+$' $arg
        echo "$prog: $(status current-function): '$arg' is not an integer" >&2
        status print-stack-trace >&2
        return 2
      end
    end
end
