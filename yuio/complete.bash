# -*- shell-script -*-

function __@prog@ {
    local prog="$1"
    local compdata_path="@data@";
    __yuio_compl_v1
}

complete -F __@prog@ $1


# Load Yuio completion system, if not loaded already.


_YUIO_COMPL_V1_VERSION=1

if (( BASH_VERSINFO[0] < 5 )); then
    _YUIO_COMPL_V1_ERR="bash>=5 is required, you have $BASH_VERSION"
elif [[ -z $BASH_COMPLETION_VERSINFO ]]; then
    _YUIO_COMPL_V1_ERR="bash-completion==2 is required"
elif (( BASH_COMPLETION_VERSINFO[0] != 2 )); then
    _YUIO_COMPL_V1_ERR="bash-completion==2 is required, you have ${BASH_COMPLETION_VERSINFO[0]}"
fi

if [[ -n $_YUIO_COMPL_V1_ERR ]]; then
    function __yuio_compl_v1 {
        echo "${prog:+"$prog: "}$_YUIO_COMPL_V1_ERR" >&2; return 1
    }
    return 1
fi

if [[ -n YUIO_COMPL_V1_VERSION && YUIO_COMPL_V1_VERSION -ge _YUIO_COMPL_V1_VERSION ]]; then
    unset _YUIO_COMPL_V1_VERSION
    return 0
fi

YUIO_COMPL_V1_VERSION=$_YUIO_COMPL_V1_VERSION
unset _YUIO_COMPL_V1_VERSION

# Entry point for completion.
#
# Completion data is passed by variables. `$prog` should contain
# name of the program that is being completed, and `$compdata_path`
# should contain completions data.
function __yuio_compl_v1 {
    [[ -z $prog ]] && (echo "$prog: $FUNCNAME: empty prog" >&2; return 2)
    [[ -z $compdata_path ]] && (echo "$prog: $FUNCNAME: empty compdata_path" >&2; return 2)

    local IFS=$' \t\n'

    # Variable that are used by functions down the stack:
    local words             # List of words, current word.
    local cword             # Current word index.
    local cur               # Portion of the current word before cursor.
    local cur_suffix        # Portion of the current word after cursor.
    local prev              # Previous word.

    # Restore compopts to their defaults:
    compopt +o filenames 2>/dev/null
    compopt +o noquote 2>/dev/null
    compopt +o nospace 2>/dev/null

    # This will fill variables declared above,
    # and handle things like completing redirections.
    _init_completion -n ':=' || return 0

    # We quote everything ourselves, so from now on this should be enabled.
    compopt -o noquote 2>/dev/null

    # Parsing state:
    local word=             # Current word that is being processed.
    local cmd=''            # Current (sub)command.
    local opt=''            # Current option.
    local nargs=0           # How many nargs left to process in the current option.
    local free_opt=0        # Current free option.
    local free_nargs=0      # How many nargs left to process in the current free option.
    local free_opts_only=   # Set to `1` when we've seen an `--` token.

    __yuio_compl_v1__load_nargs_by_ref free_nargs "$cmd" "$free_opt"

    # Look through all arguments and determine (sub)command
    # and option that we're completing:
    local i
    for ((i = 1; i <= $cword; i++)); do
        if [[ -z $free_opts_only && $word == '--' ]]; then
            # We're completing free args form now on.
            free_opts_only=1
        elif [[ -z $free_opts_only && $word == -* ]]; then
            # Previous word was an option, so in this position we expect option's args,
            # if there are any.
            opt=$word
            __yuio_compl_v1__load_nargs_by_ref nargs "$cmd" "$opt"
            if [[ $nargs == '-' ]]; then  # for options like --help or --version
                return 0
            fi
        elif [[ -z $opt && $free_nargs == 0 ]]; then
            # We've exhausted current free args.
            (( free_opt++ ))
            __yuio_compl_v1__load_nargs_by_ref free_nargs "$cmd" "$free_opt"
        elif [[ $opt == -* && $nargs == 0 ]]; then
            # We've exhausted nargs for the current option.
            opt=''
        elif [[ $opt == 'c' ]]; then
            # Previous word was a subcommand, so load it now.
            cmd="$cmd/$word"
            opt=''
            nargs=0
            free_opt=0
            free_nargs=0
            __yuio_compl_v1__load_nargs_by_ref free_nargs "$cmd" "$free_opt"
        fi

        word="${words[$i]}"

        if [[ -z $free_opts_only && $word == --*=* ]]; then
            # This is a long option with a value (i.e. `--foo=bar`).
            # In this position, we complete option's value.
            opt="${word%%=*}"
            word="${word#*=}"
            nargs=0
        elif [[ -z $free_opts_only && $word == -* ]]; then
            # This is an option without a value (i.e. `-f` or `--foo`).
            # In this position we complete the option itself.

            # TODO: argparse has special handling for options that look
            #       like negative numbers.
            # TODO: handle merged short options and short options with values.
            opt=''
            nargs=0
        elif [[ $nargs == '+' ]]; then
            # This is a mandatory argument for an option
            # that takes unlimited arguments.
            nargs='*'  # The rest arguments are optional.
        elif [[ $nargs == '*' ]]; then
            # This is an optional argument for an option
            # that takes unlimited arguments.
            :  # Do nothing, i.e. continue eating option arguments.
        elif [[ $nargs == '?' ]]; then
            # This is an optional argument for an option that takes
            # up to one argument.
            nargs=0
        elif [[ $nargs > 0 ]]; then
            # This is a mandatory argument for an option that takes
            # up to `$nargs` arguments.
            (( nargs-- ))
        elif [[ $free_nargs == '+' ]]; then
            # This is a mandatory free argument.
            opt=''
            free_nargs='*'  # The rest free arguments are optional.
        elif [[ $free_nargs == '*' ]]; then
            # This is an optional free argument.
            opt=''
        elif [[ $free_nargs == '?' ]]; then
            # This is an optional free argument.
            # There are no more free arguments in this spec, load the next one.
            opt=''
            free_nargs=0
        elif [[ $free_nargs > 0 ]]; then
            # This is a mandatory free argument.
            opt=''
            (( free_nargs-- ))
        else
            # This is not a free argument, this is a subcommand.
            opt='c'
            nargs=0
        fi
    done

    local needs_quote=1
    local _dequoted=$( dequote "$cur"__yuio_delim__"${word#"$cur"}" )
    if [[ $? != 0 ]]; then
        # Failed to dequote, probably due to unbalanced quotes in the output.
        # We let the user deal with all escapes on their own.
        # This might break list and tuple completions when delimiters contain
        # special characters, but I don't know any better way of doing this.
        needs_quote=
        _dequoted="$cur"__yuio_delim__"${word#"$cur"}"
    fi
    cur="${_dequoted%%__yuio_delim__*}"
    cur_suffix="${_dequoted##*__yuio_delim__}"
    word="$cur$cur_suffix"
    unset _dequoted

    IFS=$'\n'
    local compspec_i=5 compspec apos=1
    if [[ -z $opt ]]; then
        if [[ -z $free_opts_only && $word == -* ]]; then
            __yuio_compl_v1__complete_opts "$cmd" || return
        else
            __yuio_compl_v1__load_compspec_by_ref compspec "$cmd" "$free_opt"

            if [[ ${compspec[4]} =~ [0-9]+ ]] \
                    && [[ $free_nargs =~ [0-9]+ ]]; then
                ((apos = ${compspec[4]} - $free_nargs))
            fi

            __yuio_compl_v1__complete || return
        fi
    else
        __yuio_compl_v1__load_compspec_by_ref compspec "$cmd" "$opt"

        if [[ ${compspec[4]} =~ [0-9]+ ]] \
                && [[ $nargs =~ [0-9]+ ]]; then
            ((apos = ${compspec[4]} - $nargs))
        fi

        __yuio_compl_v1__complete || return
    fi

    __ltrim_colon_completions "$cur"

    [[ -n $needs_quote ]] && (( ${#COMPREPLY[@]} > 0 )) && COMPREPLY=( $( printf '\n%q' "${COMPREPLY[@]}" ) )
}

# Given (sub)command and option name, load option's `nargs`.
# If option is not found, this function will return 0.
#
# @param $1 name of the variable where to store the result.
# @param $2 (sub)command path, i.e. for `git stash list` it will be `/stash/list`.
# @param $3 option, either a flag name (i.e. `--help`), a free option index (i.e. `0`
#           for the first free option), or `c` for subcommand.
function __yuio_compl_v1__load_nargs_by_ref {
    (( $# != 3 )) && ( echo "$prog: $FUNCNAME: USAGE: $FUNCNAME var cmd opt" >&2 )

    local compspec; __yuio_compl_v1__load_compspec_by_ref compspec "$2" "$3"
    local nargs="${compspec[4]:-0}"
    local $1 && __yuio_compl_v1__upvars -v $1 "$nargs"
}

# Given (sub)command and option name, load option's compspec.
# If option is not found, comspec is set to be an empty array.
#
# @param $1 name of the variable where to store the result.
# @param $2 (sub)command path, i.e. for `git stash list` it will be `/stash/list`.
# @param $3 option, either a flag name (i.e. `--help`), a free option index (i.e. `0`
#           for the first free option), or `c` for subcommand.
function __yuio_compl_v1__load_compspec_by_ref {
    (( $# != 3 )) && ( echo "$prog: $FUNCNAME: USAGE: $FUNCNAME var cmd opt" >&2 )

    local raw_compspec=$(
        awk -F '\t' -v cmd="$2" -v opt="$3" \
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
            ' $compdata_path | tr $'\t' $'\a'
    )

    local IFS=$'\a'
    # We need to split by a non-whitespace character,
    # otherwise `read` ignores empty fields. We also need to add dot to the end,
    # otherwise `read` ignores last field if its empty.
    local compspec; read -ra compspec <<< "$raw_compspec$IFS."
    local $1 && __yuio_compl_v1__upvars -a${#compspec[@]} $1 ${compspec+"${compspec[@]}"}
}

# Add available flags for the given subcommand to compreply.
#
# @param $1 (sub)command path, i.e. for `git stash list` it will be `/stash/list`.
function __yuio_compl_v1__complete_opts {
    (( $# != 1 )) && ( echo "$prog: $FUNCNAME: USAGE: $FUNCNAME cmd" >&2 )

    local opts=$(
        awk -F '\t' -v cmd="$1" \
            '
                $1==cmd {
                    split($2, options, " ");
                    for (i in options) {
                        print options[i]
                    }
                }
            ' $compdata_path
    )

    local IFS=$'\n'
    COMPREPLY+=( $( IFS=$'\n'; compgen -W "$opts" -- "$cur" ) )
}

# Read compspec and apply it, adding results to compreply.
#
# This function requires `compspec_i`, `compspec`, and `apos` variables being set.
function __yuio_compl_v1__complete {
    # compspec will be non-empty due to how we parse it.
    if [[ ${#compspec[@]} -le 2 ]]; then
        return 0
    fi

    local completer; __yuio_compl_v1__complete__pop completer || return
    local size; __yuio_compl_v1__complete__pop size || return

    __yuio_compl_v1__assert_int "$FUNCNAME: $opt" "$size" || return

    local end_index=0
    ((end_index = compspec_i + size))

    while (($#)); do
        case $1 in
            --skip)
                __yuio_compl_v1__complete__set_i $end_index
                return
                ;;
            *)
                echo "$prog: $FUNCNAME: $1: invalid option" >&2
                return 1
                ;;
        esac
    done

    local COMPREPLY=()

    case $completer in
        f)
            # complete files
            local ext; __yuio_compl_v1__complete__pop ext || return
            _filedir ${ext:+"$ext"}
        ;;
        d)
            # complete directories
            _filedir -d
        ;;
        c)
            # complete choices
            local choices=(); __yuio_compl_v1__complete__pop_n $size choices || return
            printf -v choices "%q\n" "${choices[@]}"
            COMPREPLY+=( $(compgen -W "$choices" -- "$cur"))
        ;;
        cd)
            # complete choices with descriptions
            local half_size; (( half_size = $size / 2 ))
            local choices=(); __yuio_compl_v1__complete__pop_n $half_size choices || return
            printf -v choices "%q\n" "${choices[@]}" '$$$'
            COMPREPLY+=( $(compgen -W "$choices" -- "$cur"))
        ;;
        g)
            # complete git
            if $(command -v git > /dev/null) && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
                local modes; __yuio_compl_v1__complete__pop modes || return
                local worktree=$( git rev-parse --show-toplevel 2>/dev/null )/.git
                if [[ $modes == *H* ]]; then
                    local head heads=( HEAD ORIG_HEAD )
                    for head in $heads; do
                        if [[ -e $worktree/$head ]]; then
                            COMPREPLY+=( $( compgen -W "$worktree/$head" -- "$cur" ) )
                        fi
                    done
                fi
                if [[ $modes == *b* ]]; then
                    COMPREPLY+=( $( IFS=$'\n'; compgen -W "$(git for-each-ref --format='%(refname:short)' refs/heads)" -- "$cur" ) )
                fi
                if [[ $modes == *r* ]]; then
                    COMPREPLY+=( $( IFS=$'\n'; compgen -W "$(git for-each-ref --format='%(refname:short)' refs/remotes)" -- "$cur" ) )
                fi
                if [[ $modes == *t* ]]; then
                    COMPREPLY+=( $( IFS=$'\n'; compgen -W "$(git for-each-ref --format='%(refname:short)' refs/tags)" -- "$cur" ) )
                fi
            fi
        ;;
        l)
            # complete list
            compopt -o nospace 2>/dev/null
            local delim; __yuio_compl_v1__complete__pop delim || return
            delim="${delim:- }"

            # split cur by delim
            local prefix=''; [[ $cur == *"$delim"* ]] && prefix="${cur%"$delim"*}$delim"
            local cur="${cur##*"$delim"}"
            local cur_suffix="${cur_suffix#*"$delim"}"
            __yuio_compl_v1__complete || return
            if [[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == "$cur" ]]; then
                # append delim on the second tab
                compopt -o nospace 2>/dev/null
                COMPREPLY=( "${COMPREPLY[0]}$delim" )
            elif [[ ${#COMPREPLY[@]} -eq 0 ]]; then
                compopt -o nospace 2>/dev/null
                COMPREPLY=( "$cur$delim" )
            fi

            local word_prefix_len; ((word_prefix_len=${#cur} + 1))
            local num_word_prefixs=$(printf '%s' "${COMPREPLY[*]}" | cut -c 1-$cur_prefix_len | uniq | wc -l)
            if (( ${#COMPREPLY[@]} == 1 || $num_word_prefixs == 1 )); then
                # COMPREPLY has one element or there is a common prefix that's longer than the current word...
                local i
                for (( i = 0; i < ${#COMPREPLY[@]}; i++ )); do
                    # Add prefix because bash will substitute this completion.
                    COMPREPLY[$i]="$prefix${COMPREPLY[$i]}$cur_suffix"
                done
            elif (( ${#COMPREPLY[@]} > 0 )); then
                # Append zero-width space to prevent bash from deriving common prefix
                # and overriding our entire array with it.
                COMPREPLY+=( $'\u200b' )
            fi
        ;;
        lm)
            # complete list with "supports many"
            local delim; __yuio_compl_v1__complete__pop delim || return

            # now just pass this to the underlying completer, because each positional
            # for "lm" mode is its own separate list.
            __yuio_compl_v1__complete || return
        ;;
        t)
            # complete tuple
            local delim; __yuio_compl_v1__complete__pop delim || return
            delim="${delim:- }"

            # split cur by delim
            local prefix=''; [[ $cur == *"$delim"* ]] && prefix="${cur%"$delim"*}$delim"
            local cur="${cur##*"$delim"}"
            local cur_suffix="${cur_suffix#*"$delim"}"
            __yuio_compl_v1__complete || return
            if [[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == "$cur" ]]; then
                # append delim on the second tab
                compopt -o nospace 2>/dev/null
                COMPREPLY=( "${COMPREPLY[0]}$delim" )
            fi

            local len; __yuio_compl_v1__complete__pop len || return
            __yuio_compl_v1__assert_int "$FUNCNAME: $opt" "$len" || return
            if (( $pos < $len )); then
                local i
                for ((i = 0; i < $pos; i++)); do
                    __yuio_compl_v1__complete --skip || return
                done
                __yuio_compl_v1__complete || return
                if [[ ${#COMPREPLY[@]} -eq 1 ]] && (( $pos + 1 < $len )); then
                    # append delim if we're not at the last tuple element
                    compopt -o nospace 2>/dev/null
                    COMPREPLY=( "$COMPREPLY$delim" )
                fi
            fi

            local word_prefix_len; ((word_prefix_len=${#word} + 1))
            local num_word_prefixs=$(printf '%s' "${COMPREPLY[*]}" | cut -c 1-$cur_prefix_len | uniq | wc -l)
            if (( ${#COMPREPLY[@]} == 1 || $num_word_prefixs == 1 )); then
                # COMPREPLY has one element or there is a common prefix that's longer than the current word...
                local i
                for (( i = 0; i < ${#COMPREPLY[@]}; i++ )); do
                    # Add prefix because bash will substitute this completion.
                    COMPREPLY[$i]="$prefix${COMPREPLY[$i]}$cur_suffix"
                done
            else
                # Append zero-width space to prevent bash from deriving common prefix
                # and overriding our entire array with it.
                COMPREPLY+=( $'\u200b' )
            fi
        ;;
        tm)
            # complete tuple with "supports many"
            local delim; __yuio_compl_v1__complete__pop delim || return

            local len; __yuio_compl_v1__complete__pop len || return
            __yuio_compl_v1__assert_int "$FUNCNAME: $opt" "$len" || return

            if (( $apos <= $len )); then
                local i
                for ((i = 1; i < $apos; i++)); do
                    __yuio_compl_v1__complete --skip || return
                done
                __yuio_compl_v1__complete || return
            fi
        ;;
        a)
            # complete alternatives
            local len; __yuio_compl_v1__complete__pop len || return
            __yuio_compl_v1__assert_int "$FUNCNAME: $opt" "$len" || return
            local i
            for ((i = 0; i < $len; i++)); do
                # TODO: render descriptions when `a` is a top-level completer.
                #       See https://stackoverflow.com/questions/66483519/.
                __yuio_compl_v1__complete__pop # description
                __yuio_compl_v1__complete || return
            done
        ;;
        cc)
            # Custom completer
            local data; __yuio_compl_v1__complete__pop data || return
            local choices=( $( ${words[0]} --no-color --yuio-custom-completer-- "$data" "$cur" "$cur_suffix" ) ) || return
            COMPREPLY+=( $(compgen -W "${choices[*]%$'\t'*}" -- "$cur"))
        ;;
    esac

    __yuio_compl_v1__upvars -A${#COMPREPLY[@]} COMPREPLY ${COMPREPLY+"${COMPREPLY[@]}"}

    __yuio_compl_v1__complete__set_i $end_index
}

# Pop an argument from compspec and assign it to the given variable.
#
# @param $1 name of the variable where to store the result.
function __yuio_compl_v1__complete__pop {
    if (( $compspec_i >= ${#compspec[@]} )); then
        echo "$prog: $FUNCNAME: compspec index out of range" >&2
        return 2
    fi

    [[ "$1" ]] && local $1 && __yuio_compl_v1__upvars -v $1 "${compspec[$compspec_i]}"
    ((compspec_i++))
}

# Pop arguments from compspec and assign them to the given variable as an array.
#
# @param $1 number of arguments to pop freom compspec.
# @param $2 name of the variable where to store the result.
function __yuio_compl_v1__complete__pop_n {
    if (( $compspec_i + $1 > ${#compspec[@]} )); then
        echo "$prog: $FUNCNAME: compspec index out of range" >&2
        return 2
    fi

    [[ "$2" ]] && local $2 && __yuio_compl_v1__upvars -a$1 $2 "${compspec[@]:$compspec_i:$1}"
    ((compspec_i+=n))
}

# Set current index of the compspec argument, therefore skipping
# all arguments before this index.
#
# @param $1 new compspec index.
function __yuio_compl_v1__complete__set_i {
    if (( $1 > ${#compspec[@]} )); then
        echo "$prog: $FUNCNAME: compspec index out of range" >&2
        return 2
    elif (( $1 < $compspec_i )); then
        echo "$prog: $FUNCNAME: moving backwards" >&2
        return 2
    fi

    compspec_i=$1
}

# Set variables one scope above the caller.
#
# Usage: local [name]... && __yuio_compl_v1__upvars [[-v | -aN | -AN] name ...]...
#
# Options:
#     -v name value         assign `value` to variable `name`.
#     -aN name [value ...]  assign next `N` arguments to array `name`.
#     -AN name [value ...]  append next `N` arguments to array `name`.
#
# Example assign `idx=2` and `arr=(x y z)` one scope above:
#     local idx arr && __yuio_compl_v1__upvars -v idx 2 -a3 arr x y z
function __yuio_compl_v1__upvars {
    while (($#)); do
        case $1 in
            -[aA]*)
                local n="${1:2}"
                local op='='; [[ $1 == -A* ]] && op='+='
                unset -v "$2" && eval "$2"$op\(\"\$"{@:3:$n}"\"\) && shift $n && shift 2 || {
                    echo "$prog: $FUNCNAME: \`$1${2+ }$2': missing argument(s)" >&2
                    return 1
                }
                ;;
            -v)
                unset -v "$2" && eval "$2"=\"\$3\" && shift 3 || {
                    echo "$prog: $FUNCNAME: $1: missing argument(s)" >&2
                    return 1
                }
                ;;
            *)
                echo "$prog: $FUNCNAME: $1: invalid option" >&2
                return 1
                ;;
        esac
    done
}

# Check that given arguments are integers.
# Print an error messafe and return `1` if they are not.
#
# @param $1 funcname for error message.
# @param $@ integers to chek.
function __yuio_compl_v1__assert_int {
    local funcname=$1
    shift

    while (($#)); do
        printf '%d' "$1" &>/dev/null || {
            echo "$prog: $funcname: '$1' is not an integer" >&2
            return 1
        }
        shift
    done
}
