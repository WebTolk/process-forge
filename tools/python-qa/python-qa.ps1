param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ToolArguments
)

$ErrorActionPreference = 'Stop'
$qaPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $qaPython -PathType Leaf)) {
    Write-Error 'Shared Python QA is not installed. Run install.py first.'
    exit 2
}
& $qaPython (Join-Path $PSScriptRoot 'qa.py') @ToolArguments
exit $LASTEXITCODE
