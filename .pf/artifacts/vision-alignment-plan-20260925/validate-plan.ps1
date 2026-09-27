$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Push-Location $repoRoot
try {
    $documents = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md')
    $linkCount = 0
    foreach ($doc in $documents) {
        $content = Get-Content -LiteralPath $doc.FullName -Raw -Encoding utf8
        foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) {
            $target = $match.Groups[1].Value.Split('#')[0]
            if (!$target -or $target -match '^[a-z]+://') { continue }
            $resolved = [IO.Path]::GetFullPath((Join-Path $doc.DirectoryName $target))
            if (!(Test-Path -LiteralPath $resolved -PathType Leaf)) { throw "Broken link: $($doc.Name) -> $target" }
            $linkCount++
        }
    }
    "DOC-01 PASS: $linkCount local links in $($documents.Count) documents"
    $body = Get-Content (Join-Path $PSScriptRoot 'tasks.md') -Raw -Encoding utf8
    $cards = [regex]::Matches($body, '(?ms)^## (T\d{2}) [^\r\n]+.*?(?=^## T\d{2} |\z)')
    $expected = [ordered]@{ T00=@(); T01=@('T00'); T02=@('T01'); T03=@('T02'); T04=@('T01'); T05=@('T03','T04'); T06=@('T02','T03','T04','T05'); T07=@('T01','T05') }
    $graph = @{}
    foreach ($card in $cards) {
        $id = $card.Groups[1].Value
        if ($graph.ContainsKey($id) -or !$expected.Contains($id)) { throw "Unexpected/duplicate card $id" }
        foreach ($field in @('Приоритет:','Сложность:','Зависимости:','Область','Работа:','Приёмка','Артефакты:')) {
            if (!$card.Value.Contains($field)) { throw "$id missing field $field" }
        }
        $depText = [regex]::Match($card.Value, 'Зависимости:\s*([^\r\n.]+)').Groups[1].Value
        $deps = @([regex]::Matches($depText, 'T\d{2}') | ForEach-Object Value)
        foreach ($range in [regex]::Matches($depText, 'T(\d{2})[–-]T(\d{2})')) {
            $deps += @([int]$range.Groups[1].Value..[int]$range.Groups[2].Value | ForEach-Object { 'T{0:d2}' -f $_ })
        }
        $graph[$id] = @($deps | Sort-Object -Unique)
        if (($graph[$id] -join ',') -ne ($expected[$id] -join ',')) { throw "$id dependency mismatch: $($graph[$id])" }
    }
    if ($graph.Count -ne 8) { throw "Expected eight cards, got $($graph.Count)" }
    'DOC-02 PASS: eight unique cards with required fields'
    $visited = [Collections.Generic.HashSet[string]]::new()
    $visiting = [Collections.Generic.HashSet[string]]::new()
    function Visit-PlanNode([string]$id) {
        if ($visiting.Contains($id)) { throw "Cycle at $id" }
        if ($visited.Contains($id)) { return }
        [void]$visiting.Add($id)
        foreach ($dep in $graph[$id]) {
            if (!$graph.ContainsKey($dep)) { throw "Unknown dependency $dep" }
            Visit-PlanNode $dep
        }
        [void]$visiting.Remove($id)
        [void]$visited.Add($id)
    }
    foreach ($id in $graph.Keys) { Visit-PlanNode $id }
    $plan = Get-Content (Join-Path $PSScriptRoot 'plan.md') -Raw -Encoding utf8
    $tableIds = @([regex]::Matches($plan, '(?m)^\| (T\d{2}) \|') | ForEach-Object { $_.Groups[1].Value })
    if (($tableIds -join ',') -ne ($expected.Keys -join ',')) { throw 'Plan table/card IDs differ' }
    'DOC-03 PASS: table parity, expected graph, no cycles'
    $evidenceFiles = @(Get-ChildItem (Join-Path $PSScriptRoot 'evidence') -Filter '*.json')
    foreach ($file in $evidenceFiles) {
        $items = Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8 | ConvertFrom-Json
        foreach ($item in $items) {
            if (!(Test-Path -LiteralPath $item.path -PathType Leaf)) { throw "Missing evidence $($item.path)" }
        }
    }
    "DOC-04 PASS: $($evidenceFiles.Count) evidence JSON files and referenced paths"
    & git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Working-tree whitespace check failed' }
    & git diff --cached --check
    if ($LASTEXITCODE -ne 0) { throw 'Index whitespace check failed' }
    $productChanges = @(& git status --porcelain -- src tools schemas templates docs bin requirements.txt pyproject.toml)
    if ($LASTEXITCODE -ne 0 -or $productChanges.Count) { throw "Product scope changed: $productChanges" }
    $manifestDelta = @(& git diff HEAD -- .pf/process-forge.yaml | Where-Object { $_ -match '^[+-]' -and $_ -notmatch '^(\+\+\+|---)' -and $_ -notmatch '^[+-]$' })
    if ($LASTEXITCODE -ne 0 -or $manifestDelta.Count -ne 1 -or $manifestDelta[0] -ne '+process: software-feature-development') { throw "Unexpected manifest changes: $manifestDelta" }
    'DOC-05 PASS: whitespace, product scope and process selection'
    'RESULT: PASS'
}
finally { Pop-Location }
