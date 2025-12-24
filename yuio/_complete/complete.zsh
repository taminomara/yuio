#compdef @true_prog@

# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# Do not edit: this file was generated automatically by Yuio @version@.

if typeset -f __yuio_compl__@prog@__complete > /dev/null; then
    __yuio_compl__@prog@__complete
    return
fi

# Entry point for completion.
function __yuio_compl__@prog@__complete {
  emulate -L zsh
  setopt EXTENDED_GLOB TYPESET_SILENT

  local compdata=$(cat "@data@");

  # Extract prog from `$cucontext`, and save `$cucontext` as an array.
  # We will use it later.
  local acurcontext=( ${(s.:.)curcontext} )
  local prog=$acurcontext[2]

  local cur_alternative_completer_tag=0

  local ret=1

  # Start with handling top level command and descend down.
  __yuio_compl__@prog@__handle_subcommand ''
  if (( $? )); then
    _message "failed to autocomplete $prog due to an internal error"
    return -1
  fi

  return $ret
}

function __yuio_compl__@prog@__handle_subcommand {
  (( $# != 1 )) && ( echo "$prog: $funcstack[1]: USAGE: $funcstack[1] cmd" >&2; return 2 )

  local cmd=$1
  local args=()
  local subcmd_argspec subcmd_desc

  # Modify `$curcontext` to reflect the current subcommand.
  acurcontext[2]=$prog${cmd//[\/:]/-}
  local curcontext=:${(j.:.)acurcontext}:

  # Read relevant specs from `compdata` and build arg for `_arguments`.
  local _compspec compdata_for_cmd=$(
    printf -- $compdata | \
    awk -F '\t' -v cmd=$cmd '$1==cmd && $3 != "__yuio_hide__" { print $0 }' | \
    tr $'\t' $'\a' | \
    sort -k2 -t $'\a' -V
  )
  for _compspec in ${(f)compdata_for_cmd}; do
    # Read '\a'-separated compspec.
    local a=$'\a' b=$'\b'
    _compspec=${_compspec#*$a}  # skip cmd
    local _opts=${_compspec%%$a*}; _compspec=${_compspec#*$a}
    local opts=( ${(s. .)_opts//(#b)([\\:])/\\$match} )
    local _desc=${_compspec%%$a*}; _compspec=${_compspec#*$a}
    local desc=${_desc//(#b)([\\:])/\\$match}
    local _meta=${_compspec%%$a*}; _compspec=${_compspec#*$a}
    local meta=( "${(@s. .)_meta}" )
    meta=( "${meta[@]//\\S/ }" )
    meta=( "${meta[@]//\\L/\\}" )
    meta=( "${meta[@]//(#b)([\\:])/\\$match}" )
    local _nargs=${_compspec%%$a*}; _compspec=${_compspec#*$a}
    local nargs=${_nargs:-0}

    if [[ $nargs != [-+*?] ]]; then
      __yuio_compl__@prog@__assert_int $nargs || return
    fi

    # When `_arguments` processes action, it first `eval`s its arguments,
    # so we need to escape `$_compspec`. We also replace all colons with backspaces
    # because colon is used to separate argument spec.
    local argspec="__yuio_compl__@prog@__complete_opt --compspec ${(q+)_compspec//:/$b}"

    unset a b

    local opt
    for opt in $opts; do
      case $opt in
        -*|\*-*)
          if [[ $nargs == - ]]; then
            opt="(: * -)$opt"
          elif [[ $opt == -* ]]; then
            local xopt=${(j: :)opts:#"$opt"}
            opt=${xopt:+"($xopt)"}$opt
          fi
          if [[ $nargs == [-0] ]]; then
            : # no argspec needed
          elif [[ $opt == --* ]]; then
            # technically, argspec should be `$opt=`, but zsh doesn't handle this
            # the same way argparse does.
          else
            opt=$opt+
          fi
          local arg=$opt${desc:+"[$desc]"}
          if [[ $nargs == [-0] ]]; then
            : # no argspec needed
          elif [[ $nargs == [+*] ]]; then
            arg=$arg:*-*:${meta[1]:- }:$argspec
          elif [[ $nargs == '?' ]]; then
            # our parser is greedy, so we set up arg as if `$nargs` was set to `1`;
            # otherwise, zsh will mix completions for this option
            # and for the next positional.
            arg=$arg:${meta[1]:- }:$argspec
          else
            local i
            for i in $(seq $nargs); do
              arg=$arg:${meta[(( ($i - 1) % ${#meta} + 1 ))]:- }:$argspec" --apos $i"
            done
          fi
          args+=$arg
        ;;
        c)
          subcmd_argspec=$argspec
          subcmd_desc=$desc
          args+='*::: :->subcmd'
        ;;
        *)
          local arg=":${desc:- }:$argspec"
          if [[ $nargs == - ]]; then
            args+=$arg
          elif [[ $nargs == [+*] ]]; then
            args+='*'$arg
          elif [[ $nargs == '?' ]]; then
            args+=':'$arg
          else
            local i
            for i in $(seq $nargs); do
              args+=$arg" --apos $i"
            done
          fi
        ;;
      esac
    done
  done

  if (( ! $#args )); then
    _message "unknown subcommand${cmd//\// }"
    _default && ret=0
    return 0
  fi

  local state='' line=''
  _arguments -s -S -C -A '-*' ${args[@]} && ret=0

  (( ! ret )) && return 0
  [[ $state != "subcmd" ]] && return 0

  if (( $CURRENT == 1 )); then
    _tags subcommands
    while _tags; do
      if _requested subcommands; then
        local expl=()
        local action; eval "action=( $subcmd_argspec )"
        while _next_label subcommands expl ${subcmd_desc:-subcommand}; do
          $action[1] $expl ${(@)action[2,-1]}
        done
      fi
      (( ! ret )) && break
    done
  else
    __yuio_compl__@prog@__handle_subcommand $cmd/$words[1]
  fi
  return 0
}

function __yuio_compl__@prog@__complete_opt {
  local compspec_opt apos_opt ret=1
  zparseopts -D -E - -compspec:=compspec_opt -apos:=apos_opt

  [[ -z $compspec_opt[1] ]] && ( echo "$prog: $funcstack[1]: USAGE: $funcstack[1] ... --compspec compspec" >&2; return 2 )
  [[ -z $compspec_opt[2] ]] && ( echo "$prog: $funcstack[1]: got an empty compspec; perhaps nargs is invalid?" >&2; return 2 )

  # Read `\a`-separated compspec (or rathe the completer part of it).
  # Also replace back `\b` with colons (because we've replaced colons with `\b`s earlier).
  local compspec=() compspec_i=1 apos=${apos_opt[2]:-1}
  local _IFS=$IFS IFS=$'\a' b=$'\b'
  read -rA compspec <<< ${compspec_opt[2]//$b/:}
  IFS=$_IFS
  unset b

  __yuio_compl__@prog@__complete_arg $* || return
  return $ret
}

function __yuio_compl__@prog@__complete_arg {
  local skip_opt
  zparseopts -D -E - -skip=skip_opt

  __yuio_compl__@prog@__compspec_pop && local completer=$REPLY || return
  __yuio_compl__@prog@__compspec_pop && local size=$REPLY || return
  __yuio_compl__@prog@__assert_int $size || return
  local end_index && ((end_index = compspec_i + size))

  if (( $#skip_opt )); then
    __yuio_compl__@prog@__compspec_set_i $end_index
    return
  fi

  case $completer in
    f)
      # complete files
      __yuio_compl__@prog@__compspec_pop && local ext=$REPLY || return
      _files $* ${ext:+"-g"} ${ext:+"*.(${ext}|${(U)ext})"} && ret=0
    ;;
    d)
      # complete directories
      _files $* -/ && ret=0
    ;;
    c)
      # complete choices
      __yuio_compl__@prog@__compspec_pop_n $size && local choices=( "${reply[@]}" ) || return
      # Add choices directly, re-using tag and description that was passed from `_arguments`.
      local tag=${curtag:-values}
      compadd $* -a -- choices && ret=0
    ;;
    cd)
      # complete choices with descriptions
      local half_size; (( half_size = $size / 2 ))
      __yuio_compl__@prog@__compspec_pop_n $half_size && local choices=( "${reply[@]}" ) || return
      __yuio_compl__@prog@__compspec_pop_n $half_size && local descriptions=( "${reply[@]}" ) || return

      for i in $(seq $half_size); do
        choices[i]="${choices[i]/:/\\:}"
        descriptions[i]="${choices[i]}:${descriptions[i]}"
      done

      local opts; zparseopts -D -E -a opts - o O t:  # extract options for _describe

      # Add choices directly, re-using tag and description that was passed from `_arguments`.
      local tag=${curtag:-values}
      _describe $opts "" descriptions choices $@ && ret=0
    ;;
    g)
      # complete git
      if $(command -v git > /dev/null) && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        __yuio_compl__@prog@__compspec_pop && local modes=$REPLY || return
        __yuio_compl__@prog@__git $* --modes $modes || return
      fi
    ;;
    l)
      # complete list
      __yuio_compl__@prog@__compspec_pop && local delim=${REPLY:- } || return
      _sequence $* -s $delim __yuio_compl__@prog@__complete_arg || return
    ;;
    lm)
      # complete list with "supports many"
      __yuio_compl__@prog@__compspec_pop && local delim=${REPLY:- } || return
      __yuio_compl__@prog@__complete_arg $* || return
    ;;
    t)
      # complete tuple
      __yuio_compl__@prog@__compspec_pop && local delim=${REPLY:- } || return
      __yuio_compl__@prog@__compspec_pop && local len=${REPLY:- } || return
      __yuio_compl__@prog@__assert_int $len || return
      local pos=$(grep -oF -e "$delim" -e "${(q)delim}" <<< "$PREFIX" | wc -l)
      (( ++pos > len )) && pos=$len
      while (( --pos )); do
        __yuio_compl__@prog@__complete_arg --skip
      done
      _sequence $* -s $delim -n $len -d __yuio_compl__@prog@__complete_arg || return
    ;;
    tm)
      # complete tuple with "supports many"
      __yuio_compl__@prog@__compspec_pop && local delim=${REPLY:- } || return
      __yuio_compl__@prog@__compspec_pop && local len=${REPLY:- } || return
      __yuio_compl__@prog@__assert_int $len || return
      local pos=$apos
      (( pos > len )) && pos=$len
      while (( --pos )); do
        __yuio_compl__@prog@__complete_arg --skip
      done
      __yuio_compl__@prog@__complete_arg $* || return
    ;;
    a)
      # complete alternatives
      __yuio_compl__@prog@__compspec_pop && local len=$REPLY || return
      __yuio_compl__@prog@__assert_int $len || return

      local _compspec_i=$compspec_i _ret=$ret
      local tags=( alt-{1..$len} )

      if (( $#tags )); then
        local ignored_opts
        zparseopts -D -E -a ignored_opts - x: X: J: V: 1 2  # override grouping

        _tags $tags
        while _tags; do
          ret=1
          local tag
          for tag in $tags; do
            __yuio_compl__@prog@__compspec_pop && local desc=$REPLY || return
            local __compspec_i=$compspec_i
            if _requested $tag; then
              local expl=()
              while _next_label $tag expl $desc $*; do
                __yuio_compl__@prog@__complete_arg $expl || return
                compspec_i=$__compspec_i
              done
            fi
            __yuio_compl__@prog@__complete_arg --skip
          done
          (( ! ret )) && break
          compspec_i=$_compspec_i
        done
      fi
      (( ! ret || ! _ret )) && ret=0
    ;;
    cc)
      # custom completer
      __yuio_compl__@prog@__compspec_pop && local data=$REPLY || return
      local _IFS=$IFS IFS=$'\n'
      local choices=( $($prog --no-color --yuio-custom-completer-- $data "") )
      IFS=$_IFS
      local descriptions=()

      for i in $(seq ${#choices}); do
        local parts=( ${(@ps.\t.)choices[i]} )
        choices[i]="${parts[1]/:/\\:}"
        shift parts
        descriptions+="${choices[i]}:${(j. .)parts}"
      done

      local opts; zparseopts -D -E -a opts - o O t:  # extract options for _describe

      # Add choices directly, re-using tag and description that was passed from `_arguments`.
      local tag=${curtag:-values}
      _describe $opts "" descriptions choices $@ && ret=0
    ;;
    -)
      local msg=()
      zparseopts -E -K -a msg - x: X:
      if (( $#msg )); then
        _message -r $msg[2]
      fi
      ret=0
    ;;
  esac

  __yuio_compl__@prog@__compspec_set_i $end_index || return
}

# Pop an argument from compspec and assign it to the given variable.
#
# Return value in the `$REPLY` variable.
function __yuio_compl__@prog@__compspec_pop {
  if (( $compspec_i > ${#compspec[@]} )); then
    echo "$prog: $funcstack[2]: compspec index out of range" >&2
    return 2
  fi

  REPLY=${compspec[compspec_i++]}
}

# Pop arguments from compspec and assign them to the given variable as an array.
#
# Return value in the `$reply` variable.
#
# @param $1 number of arguments to pop freom compspec.
function __yuio_compl__@prog@__compspec_pop_n {
  (( $# != 1 )) && ( echo "$prog: $funcstack[1]: USAGE: $funcstack[1] n" >&2; return 2 )

  if (( $compspec_i + $1 > ${#compspec[@]} + 1 )); then
    echo "$prog: $funcstack[2]: compspec index out of range" >&2
    return 2
  fi

  local offset; (( offset = compspec_i - 1 ))
  reply=( "${compspec[@]:$offset:$1}" )
  ((compspec_i+=$1))
}

# Set current index of the compspec argument, therefore skipping
# all arguments before this index.
#
# @param $1 new compspec index.
function __yuio_compl__@prog@__compspec_set_i {
  (( $# != 1 )) && ( echo "$prog: $funcstack[1]: USAGE: $funcstack[1] idx" >&2; return 2 )

  if (( $1 > ${#compspec[@]} + 1 )); then
    echo "$prog: $funcstack[2]: compspec index out of range" >&2
    return 2
  elif (( $1 < $compspec_i )); then
    echo "$prog: $funcstack[2]: moving backwards" >&2
    return 2
  fi

  compspec_i=$1
}

# Check that given arguments are integers.
# Print an error messafe and return `1` if they are not.
#
# @param $@ integers to chek.
function __yuio_compl__@prog@__assert_int {
  while (($#)); do
    if [[ ! $1 =~ [0-9]+ ]]; then
      echo "$prog: $funcstack[2]: '$1' is not an integer" >&2
      return 1
    fi
    shift
  done
}

# Complete git objects.
function __yuio_compl__@prog@__git {
  local modes_opt=( --modes brh ) ignored_opts=() _ret=$ret
  zparseopts -D -E -K -a ignored_opts - -modes:=modes_opt x: X: J: V: 1 2

  local modes=$modes_opt[2]
  [[ -z $modes ]] && ( echo "$prog: $funcstack[1]: USAGE: $funcstack[1] ... --modes modes" >&2; return 2 )

  declare -A all_modes=(
    [heads-local]='b:branch:refs/heads'
    [heads-remote]='r:remote branch:refs/remotes'
    [tags]='t:tag:refs/tags'
    [heads]='h:head:(HEAD ORIG_HEAD)'
  )

  _tags ${(k)all_modes}
  while _tags; do
    local tag mode_data
    ret=1
    for tag mode_data in ${(kv)all_modes}; do
      mode_data=( ${(s.:.)mode_data} )
      if [[ $modes == *$mode_data[1]* ]] && _requested $tag; then
        local expl=()
        while _next_label $tag expl $mode_data[2] $*; do
          local choices=()
          if [[ $mode_data[3] == \(*\) ]]; then
            eval "choices=( ${mode_data[3][2,-2]} )"
          else
            choices=( $( git for-each-ref --format='%(refname:short)' $mode_data[3] ) )
          fi
          compadd $expl -a -- choices && ret=0
        done
      fi
    done
    (( ! ret )) && break
  done

  (( ! ret || ! _ret )) && ret=0

  return 0
}


__yuio_compl__@prog@__complete
