# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# Do not edit: this file was generated automatically by Yuio @version@.

using namespace System.Collections.Generic
using namespace System.Management.Automation

Register-ArgumentCompleter -Native -CommandName '@true_prog@' -ScriptBlock {
    param ($WordToComplete, $CommandAst, $CursorPosition)
    try {
        Complete $CommandAst $CursorPosition
    } catch {
        Write-Debug "`nError in completion:`n`n$_`n`nStack trace:`n`n$($_.ScriptStackTrace)"
        return $null
    }
}

class Compspec {
    [string] $Desc
    [string] $Meta
    [object] $Nargs
    [string[]] $Command
}

class Context {
    [string] $Prog
    [int] $APos
    [int] $Pos
    [string[]] $Command
}

# Entry point for completion.
function Complete {
    param (
        [Parameter(Mandatory=$true)][Language.CommandAst] $CommandAst,
        [Parameter(Mandatory=$true)][int] $CursorPosition
    )

    # Build a list of arguments
    [List[string]] $prefixArgs = @()
    [string] $prefix = ''
    [string] $suffix = ''
    foreach ($arg in $CommandAst.CommandElements | Select-Object -Skip 1) {
        if ($arg.Extent.EndOffset -lt $CursorPosition) {
            $text = Unescape-String $arg.Extent.Text
            [void]$prefixArgs.Add($text)
        } else {
            $pos = $CursorPosition - $arg.Extent.StartOffset
            $text = Unescape-String $arg.Extent.Text.Insert($pos, "`0YUIO_CURSOR`0")
            $prefix, $suffix = $text -split "`0YUIO_CURSOR`0", 2
            break
        }
    }
    [void]$prefixArgs.Add("$prefix$suffix")

    # Load compdata
    [Dictionary[string, Dictionary[string, Compspec]]] $compdata = Load-Compdata

    $word = '' # Current word.
    $cmd = '' # Current (sub)command.
    $opt = '' # Current option.
    $nargs = 0 # How many nargs left to process in the current option.
    $freeOpt = 0 # Current free option.
    $freeNargs = 0 # How many nargs left to process in the current free option.
    $freeOptsOnly = $false # Set to `1` when we've seen an `--` token.
    $iprefix = '' # For options in form `--x=y`, this is the prefix `--x=`.

    $freeNargs = (Get-Compspec $compdata $cmd "$freeOpt").Nargs

    foreach ($cur in $prefixArgs) {
        if (-not $freeOptsOnly -and $word -eq '--') {
            $freeOptsOnly = $true
        } elseif (-not $freeOptsOnly -and $word -match '^\-') {
            # Previous word was an option, so in this position we expect option's args,
            # if there are any.
            $opt = $word
            $nargs = (Get-Compspec $compdata $cmd $opt).Nargs
            if ($nargs -eq '-') {  # for options like --help or --version
                return 0
            }
        } elseif (-not $opt -and $freeNargs -eq 0) {
            # We've exhausted current free args.
            $freeOpt += 1
            $freeNargs = (Get-Compspec $compdata $cmd "$freeOpt").Nargs
        } elseif ($opt -match '^\-' -and $nargs -eq 0) {
            # We've exhausted nargs for the current option.
            $opt = ''
        } elseif ($opt -eq 'c') {
            # Previous word was a subcommand, so load it now.
            $cmd = "$cmd/$word"
            $opt = ''
            $nargs = 0
            $freeOpt = 0
            $freeNargs = (Get-Compspec $compdata $cmd "$freeOpt").Nargs
        }

        $word = $cur
        $iprefix = ''

        if (-not $freeOptsOnly -and $word -match '^\-\-.*\=') {
            # This is a long option with a value (i.e. `--foo=bar`).
            # In this position, we complete option's value.
            $split = ($word -split '=', 2)
            $opt = $split[0]
            $iprefix = "$opt="
            $word = $split[1]
            $nargs = 0
        } elseif (-not $freeOptsOnly -and $word -match '^\-') {
            # This is an option without a value (i.e. `-f` or `--foo`).
            # In this position we complete the option itself.

            # TODO: argparse has special handling for options that look
            #       like negative numbers.
            # TODO: handle merged short options and short options with values.
            $opt = ''
            $nargs = 0
        } elseif ($nargs -eq '+') {
            # This is a mandatory argument for an option
            # that takes unlimited arguments.
            $nargs = '*'  # The rest arguments are optional.
        } elseif ($nargs -eq '*') {
            # This is an optional argument for an option
            # that takes unlimited arguments.
        } elseif ($nargs -eq '?') {
            # This is an optional argument for an option that takes
            # up to one argument.
            $nargs = 0
        } elseif ($nargs -is [int] -and $nargs -gt 0) {
            # This is a mandatory argument for an option that takes
            # up to `$nargs` arguments.
            $nargs -= 1
        } elseif ($freeNargs -eq '+') {
            # This is a mandatory free argument.
            $opt = ''
            $freeNargs = '*'  # The rest free arguments are optional.
        } elseif ($freeNargs -eq '*') {
            # This is an optional free argument.
            $opt = ''
        } elseif ($freeNargs -eq '?') {
            # This is an optional free argument.
            # There are no more free arguments in this spec, load the next one.
            $opt = ''
            $freeNargs = 0
        } elseif ($freeNargs -is [int] -and $freeNargs -gt 0) {
            # This is a mandatory free argument.
            $opt = ''
            $freeNargs -= 1
        } else {
            $opt = 'c'
        }
    }

    $result = @()

    if ($opt -eq '') {
        if (-not $freeOptsOnly -and $word -match '^\-') {
            $result = @(Complete-Flags $compdata $cmd)
        } else {
            $compspec = Get-Compspec $compdata $cmd "$freeOpt"
            $apos = 0
            if ($compspec.Nargs -is [int] -and $nargs -is [int]) {
                $apos = $compspec.Nargs - $freeNargs
            }
            $context = [Context]@{
                Prog = $CommandAst.CommandElements[0].Extent.Text
                APos = $apos
                Pos = 0
                Command = $compspec.Command
            }
            $result = @(Complete-Args $context $iprefix $prefix $suffix '' ' ')
        }
    } else {
        $compspec = Get-Compspec $compdata $cmd "$opt"
        $apos = 0
        if ($compspec.Nargs -is [int] -and $nargs -is [int]) {
            $apos = $compspec.Nargs - $nargs
        }
        $context = [Context]@{
            Prog = $CommandAst.CommandElements[0].Extent.Text
            APos = $apos
            Pos = 0
            Command = $compspec.Command
        }
        $result = @(Complete-Args $context $iprefix $prefix $suffix '' ' ')
    }

    $result = @($result | Where-Object { $_.CompletionText.StartsWith($prefix) })

    if ($result.get_Length() -eq 0) {
        return $null
    }

    foreach ($completion in $result) {
        [CompletionResult]::new(
            (Escape-String $completion.CompletionText),
            $completion.ListItemText,
            $completion.ResultType,
            $completion.ToolTip
        )
    }
}

function Get-Compspec {
    param (
        [Parameter(Mandatory=$true)][Dictionary[string, Dictionary[string, Compspec]]] $Compdata,
        [string] $CommandPath,
        [Parameter(Mandatory=$true)][string] $Flag
    )

    $pathData = $Compdata[$CommandPath]

    if ($null -eq $pathData) {
        return [Compspec]@{
            Desc = ''
            Meta = ''
            Nargs = 0
            Command = @('-', '0')
        }
    }

    $argspec = $pathData[$Flag]

    if ($null -eq $argspec) {
        return [Compspec]@{
            Desc = ''
            Meta = ''
            Nargs = 0
            Command = @('-', '0')
        }
    }

    $argspec
}

function Load-Compdata {
    [Dictionary[string, Dictionary[string, Compspec]]] $compdata = @{}

    foreach ($line in Get-Content -Path '@data@') {
        $items = $line.Split("`t")

        $path = $items[0]
        $flags = $items[1].Split(" ")
        $desc = $items[2]
        $meta = $items[3].Split(" ")  # TODO: replace \S and \L
        $nargs = $items[4]
        $command = $items[5..$items.Length]

        try {
            $nargs = [convert]::ToInt32($nargs)
        } catch {
            # nothing
        }

        foreach ($flag in $flags) {
            if ($null -eq $compdata[$path]) {
                $compdata[$path] = @{}
            }

            $compdata[$path][$flag] = [Compspec]@{
                Desc = $desc
                Meta = $meta
                Nargs = $nargs
                Command = $command
            }
        }
    }

    $compdata
}

function Complete-Flags {
    param (
        [Parameter(Mandatory=$true)][Dictionary[string, Dictionary[string, Compspec]]] $Compdata,
        [string] $CommandPath
    )

    $pathData = $Compdata[$CommandPath]

    if ($null -eq $pathData) {
        @()
    } else {
        @(
            $pathData.GetEnumerator() | `
            Where-Object { $_.Key -match "^\-" -and $_.Value.Desc -ne "__yuio_hide__" } | `
            Sort-Object -Property { $_.Key -replace '^--?', '' } | `
            ForEach-Object {
                [CompletionResult]::new(
                    "$($_.Key) ",
                    $_.Key,
                    'ParameterName',
                    (Coalesce $_.Value.Desc $_.Key)
                )
            }
        )
    }
}

function Complete-Args {
    param (
        [Context] $Context,
        [string] $Iprefix,
        [string] $Prefix,
        [string] $Suffix,
        [string] $Isuffix,
        [string] $EndSep,
        [string] $Desc = "",
        [switch] $Skip = $false
    )

    if ($Context.Command.get_Length() -eq 0) {
        return @()
    }

    $completer = Pop-Command $Context
    $size = [int](Pop-Command $Context)
    $endIndex = $Context.Pos + $size

    if ($Skip) {
        $Context.Pos = $endIndex
        return
    }

    [List[CompletionResult]] $results = @()

    switch ($completer) {
        'f' {
            $results = @([Management.Automation.CompletionCompleters]::CompleteFilename($Prefix))
            $results = @(Add-Surroundings $results $Iprefix $Isuffix $EndSep)
        }
        'd' {
            $results = @(
                [Management.Automation.CompletionCompleters]::CompleteFilename($Prefix) | `
                Where-Object { $_.ResultType -eq 'ProviderContainer' }
            )
            $results = @(Add-Surroundings $results $Iprefix $Isuffix $EndSep)
        }
        'c' {
            $results = @(
                Pop-NCommands $Context $size | Foreach-Object {
                    [CompletionResult]::new(
                        $_,
                        $_,
                        'ProviderItem',
                        (Coalesce $Desc $_)
                    )
                }
            )
            $results = @(Add-Surroundings $results $Iprefix $Isuffix $EndSep)
        }
        'cd' {
            $halfSize = [int]($size / 2)
            $choices = @(Pop-NCommands $Context $halfSize)
            $descriptions = @(Pop-NCommands $Context $halfSize)
            for ($i = 0; $i -lt $halfSize; $i++) {
                [void]$results.Add([CompletionResult]::new(
                    $choices[$i],
                    $choices[$i],
                    'ProviderItem',
                    (Coalesce $descriptions[$i] $Desc $choices[$i])
                ))
            }
            $results = @(Add-Surroundings $results $Iprefix $Isuffix $EndSep)
        }
        'g' {
            if (
                (Get-Command git -errorAction SilentlyContinue) -and
                (git rev-parse --is-inside-work-tree 2>$null)
            ) {
                $modes = Pop-Command $Context
                $gitDir = git rev-parse --absolute-git-dir 2>$null
                if ($modes -match 'H') {
                    foreach ($head in @('HEAD', 'ORIG_HEAD')) {
                        if (Test-Path (Join-Path -Path $gitDir -ChildPath $head) -PathType Leaf) {
                            [void]$results.Add([CompletionResult]::new(
                                $head,
                                $head,
                                'ProviderItem',
                                'head'
                            ))
                        }
                    }
                }
                if ($modes -match 'b') {
                    $refs = git for-each-ref --format='%(refname:short)' refs/heads
                    foreach ($ref in $refs) {
                        [void]$results.Add([CompletionResult]::new(
                            $ref,
                            $ref,
                            'ProviderItem',
                            'local Branch'
                        ))
                    }
                }
                if ($modes -match 'r') {
                    $refs = git for-each-ref --format='%(refname:short)' refs/remotes
                    foreach ($ref in $refs) {
                        [void]$results.Add([CompletionResult]::new(
                            $ref,
                            $ref,
                            'ProviderItem',
                            'remote Branch'
                        ))
                    }
                }
                if ($modes -match 't') {
                    $refs = git for-each-ref --format='%(refname:short)' refs/tags
                    foreach ($ref in $refs) {
                        [void]$results.Add([CompletionResult]::new(
                            $ref,
                            $ref,
                            'ProviderItem',
                            'tag'
                        ))
                    }
                }
                $results = @(Add-Surroundings $results $Iprefix $Isuffix $EndSep)
            }
        }
        'l' {
            $delim = Pop-Command $Context

            if ($delim) {
                $prefixParts = $Prefix.split($delim)
                $suffixParts = $Suffix.split($delim)
            } else {
                $prefixParts = $Prefix -split '\s+'
                $suffixParts = $Suffix -split '\s+'
                $delim = ' '
            }

            if ($prefixParts.get_Length() -gt 1) {
                $Iprefix = "$Iprefix$(($prefixParts | Select-Object -SkipLast 1) -join $delim)$delim"
            }
            $Prefix = $prefixParts[-1]
            $Suffix = $suffixParts[0]
            if ($suffixParts.get_Length() -gt 1) {
                $Isuffix = "$delim$(($suffixParts | Select-Object -Skip 1) -join $delim)$Isuffix"
            }
            $results = @(
                Complete-Args $Context $Iprefix $Prefix $Suffix $Isuffix '' $Desc
            )
        }
        'lm' {
            $delim = Pop-Command $Context
            $results = @(
                Complete-Args $Context $Iprefix $Prefix $Suffix $Isuffix $EndSep $Desc
            )
        }
        't' {
            $delim = Pop-Command $Context
            $len = [int](Pop-Command $Context)

            if ($delim) {
                $prefixParts = $Prefix.split($delim)
                $suffixParts = $Suffix.split($delim)
            } else {
                $prefixParts = $Prefix -split '\s+'
                $suffixParts = $Suffix -split '\s+'
                $delim = ' '
            }

            if ($prefixParts.get_Length() -le $len) {
                if ($prefixParts.get_Length() -gt 1) {
                    $Iprefix = "$Iprefix$(($prefixParts | Select-Object -SkipLast 1) -join $delim)$delim"
                }
                $Prefix = $prefixParts[-1]
                $Suffix = $suffixParts[0]
                if ($suffixParts.get_Length() -gt 1) {
                    $Isuffix = "$delim$(($suffixParts | Select-Object -Skip 1) -join $delim)$Isuffix"
                }

                for ($i = 1; $i -lt $prefixParts.get_Length(); $i++) {
                    Complete-Args $Context -Skip
                }

                if ($prefixParts.get_Length() -lt $len) {
                    $EndSep = $delim
                }

                $results = @(
                    Complete-Args $Context $Iprefix $Prefix $Suffix $Isuffix $EndSep $Desc
                )
            }
        }
        'tm' {
            $delim = Pop-Command $Context
            $len = [int](Pop-Command $Context)

            if ($Context.Apos -le $len) {
                for ($i = 1; $i -lt $Context.Apos; $i++) {
                    Complete-Args $Context -Skip
                }
                $results = @(
                    Complete-Args $Context $Iprefix $Prefix $Suffix $Isuffix $EndSep $Desc
                )
            }
        }
        'a' {
            $len = [int](Pop-Command $Context)
            for ($i = 0; $i -lt $len; $i++) {
                $Desc = Pop-Command $Context
                $results += Complete-Args $Context $Iprefix $Prefix $Suffix $Isuffix $EndSep $Desc
            }
        }
        'cc' {
            $data = Pop-Command $Context
            $choices = & $Context.Prog @('--no-color', '--yuio-custom-completer--', $data, $Prefix)
            foreach ($choice in $choices) {
                $choiceParts = $choice -split '\t', 2
                [void]$results.Add([CompletionResult]::new(
                    $choiceParts[0],
                    $choiceParts[0],
                    'ProviderItem',
                    (Coalesce $choiceParts[1] $Desc $choiceParts[0])
                ))
            }
            $results = @(Add-Surroundings $results $Iprefix $Isuffix $EndSep)
        }
    }

    $Context.Pos = $endIndex

    $results
}

function Add-Surroundings {
    param(
        [Parameter(Mandatory=$true)][List[CompletionResult]] $Results,
        [string] $Iprefix,
        [string] $Isuffix,
        [string] $EndSep
    )

    if ($Iprefix -or $Isuffix -or $EndSep) {
        $Results | Foreach-Object {
            [CompletionResult]::new(
                "$Iprefix$($_.CompletionText)$Isuffix$EndSep",
                $_.ListItemText,
                $_.ResultType,
                $_.ToolTip
            )
        }
    } else {
        $Results
    }
}

function Pop-Command {
    param (
        [Parameter(Mandatory=$true)][Context] $Context
    )

    $Context.Command[$Context.Pos]
    $Context.Pos += 1
}

function Pop-NCommands {
    param (
        [Parameter(Mandatory=$true)][Context] $Context,
        [Parameter(Mandatory=$true)][int] $n
    )

    $Context.Command[$Context.Pos..($Context.Pos + $n - 1)]
    $Context.Pos += $n
}

function Coalesce {
    param (
        [Parameter(
            Mandatory=$true,
            ValueFromRemainingArguments=$true,
            Position = 0
        )] $listArgs
    )

    foreach ($arg in $listArgs) {
        if ($arg) {
            return $arg
        }
    }
}

function Escape-String {
    param (
        [Parameter(Mandatory=$true)][string] $Arg
    )

    $pattern = '([`^$*+?{}\[\]\\|()\n\r\t\b\a\f\v\e\0,''"])'
    $Arg -replace $pattern, {
        $s = $_.Groups[1].Value
        switch ($s) {
            "`n" { '`n' }
            "`r" { '`r' }
            "`t" { '`t' }
            "`b" { '`b' }
            "`a" { '`a' }
            "`f" { '`f' }
            "`v" { '`v' }
            "`e" { '`e' }
            "`0" { '`0' }
            default { "``$s" }
        }
    }
}

function Unescape-String {
    param (
        [Parameter(Mandatory=$true)][string] $Arg
    )

    $isSingleQuoted = $false
    if ($Arg.StartsWith('"') -and $Arg.EndsWith('"')) {
        $Arg = $Arg.Substring(1, $Arg.Length - 2)
        $isSingleQuoted = $false
    } elseif ($Arg.StartsWith("'") -and $Arg.EndsWith("'")) {
        $Arg = $Arg.Substring(1, $Arg.Length - 2)
        $isSingleQuoted = $true
    }

    $result = ''
    $i = 0

    while ($i -lt $Arg.Length) {
        $char = $Arg[$i]

        if ($isSingleQuoted) {
            if ($char -eq "'" -and ($i + 1) -lt $Arg.Length -and $Arg[$i + 1] -eq "'") {
                $result += "'"
                $i += 2
            } else {
                $result += $char
                $i++
            }
        } else {
            if ($char -eq '`' -and ($i + 1) -lt $Arg.Length) {
                $nextChar = $Arg[$i + 1]
                switch ($nextChar) {
                    'n' { $result += "`n"; $i += 2 }
                    'r' { $result += "`r"; $i += 2 }
                    't' { $result += "`t"; $i += 2 }
                    'b' { $result += "`b"; $i += 2 }
                    'a' { $result += "`a"; $i += 2 }
                    'f' { $result += "`f"; $i += 2 }
                    'v' { $result += "`v"; $i += 2 }
                    'e' { $result += "`e"; $i += 2 }
                    '0' { $result += "`0"; $i += 2 }
                    '"' { $result += '"'; $i += 2 }
                    "'" { $result += "'"; $i += 2 }
                    '`' { $result += '`'; $i += 2 }
                    'u' {
                        if (($i + 2) -lt $Arg.Length -and $Arg[$i + 2] -eq '{') {
                            $j = $i + 3
                            $hexDigits = ''

                            while ($j -lt $Arg.Length -and $Arg[$j] -ne '}') {
                                if ($Arg[$j] -match '[0-9A-Fa-f]') {
                                    $hexDigits += $Arg[$j]
                                } else {
                                    break
                                }
                                $j++
                            }

                            if (
                                $j -lt $Arg.Length -and
                                $Arg[$j] -eq '}' -and
                                $hexDigits.Length -ge 1 -and
                                $hexDigits.Length -le 6
                            ) {
                                try {
                                    $codePoint = [Convert]::ToInt32($hexDigits, 16)
                                    $result += [char]::ConvertFromUtf32($codePoint)
                                    $i = $j + 1
                                } catch {
                                    $result += $char
                                    $i++
                                }
                            } else {
                                $result += $char
                                $i++
                            }
                        } else {
                            $result += $char
                            $i++
                        }
                    }
                    default {
                        $result += $nextChar
                        $i += 2
                    }
                }
            } else {
                $result += $char
                $i++
            }
        }
    }

    $result
}
