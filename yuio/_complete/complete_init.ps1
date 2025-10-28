# Yuio project, MIT license.
#
# https://github.com/taminomara/yuio/
#
# Do not edit: this file was generated automatically.

# LOADER_VERSION: 1

if ($null -eq $global:_YUIO_COMPL_V1_INIT_PATHS) {
    $global:_YUIO_COMPL_V1_INIT_PATHS = @()
}

$__YuioComplInitV1__Flags = [System.Reflection.BindingFlags]"Instance, NonPublic"
$__YuioComplInitV1__Context = $ExecutionContext.GetType().GetField("_context", $__YuioComplInitV1__Flags).GetValue($ExecutionContext)
$__YuioComplInitV1__NativeProp = $__YuioComplInitV1__Context.GetType().GetProperty("NativeArgumentCompleters", $__YuioComplInitV1__Flags)

# From https://github.com/PowerShell/PowerShell/issues/17283
function __YuioComplInitV1__Register-LazyCompleter() {
    param ($CommandName, $CompletionScript)

    $Context = $script:__YuioComplInitV1__Context
	$NativeProp = $script:__YuioComplInitV1__NativeProp

    Register-ArgumentCompleter -CommandName $CommandName -ScriptBlock {
        try {
            . $CompletionScript
            $completer = $NativeProp.GetValue($Context)[$CommandName]
        } catch {
            Write-Debug "`nError in completion:`n`n$_`n`nStack trace:`n`n$($_.ScriptStackTrace)"
        }
		return & $completer @Args
    }.GetNewClosure()
}

# Loads and binds completion scripts.
function __YuioCompl__Load-Completers {
    param ($Path)

    foreach ($file in Get-ChildItem $Path) {
        if ($file.Name -match '^_(.*)\.ps1$') {
            $prog = $Matches.1
            $path = $file.FullName
            __YuioComplInitV1__Register-LazyCompleter -CommandName $prog -CompletionScript {
                . $path
            }.GetNewClosure()
        }
    }
}

__YuioCompl__Load-Completers -Path '@data@'
$global:_YUIO_COMPL_V1_INIT_PATHS += @('@data@')
