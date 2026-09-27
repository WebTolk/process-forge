$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Push-Location $repoRoot
try {
    $links = 0
    foreach ($file in @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.md')) {
        $content = Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8
        foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) {
            $target = $match.Groups[1].Value.Split('#')[0]
            if (!$target -or $target -match '^[a-z]+://') { continue }
            if (!(Test-Path -LiteralPath (Join-Path $file.DirectoryName $target) -PathType Leaf)) { throw "Broken link: $target" }
            $links++
        }
    }
    "PASS links: $links"
    $graph = Get-Content (Join-Path $PSScriptRoot 'task-graph.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $ids = @($graph.tasks.PSObject.Properties.Name | Sort-Object)
    $expected = @(0..9 | ForEach-Object { 'T{0:d2}' -f $_ })
    if (($ids -join ',') -ne ($expected -join ',')) { throw 'Task ID coverage mismatch' }
    $done = [Collections.Generic.HashSet[string]]::new()
    $order = @($graph.recommended_order) + @($graph.separate_followup)
    if ($order.Count -ne 10) { throw 'Expected ten ordered tasks' }
    foreach ($id in $order) {
        if (!$ids.Contains($id) -or $done.Contains($id)) { throw "Unknown/duplicate order ID $id" }
        foreach ($dep in $graph.tasks.$id) {
            if (!$done.Contains($dep)) { throw "Cycle or unordered dependency: $id -> $dep" }
        }
        [void]$done.Add($id)
    }
    if (($graph.tasks.T06 -join ',') -ne 'T02,T03,T04,T05,T08,T09') { throw 'Final gate dependencies incorrect' }
    if (($graph.tasks.T08 -join ',') -ne 'T00' -or ($graph.tasks.T09 -join ',') -ne 'T01') { throw 'New task dependencies incorrect' }
    $plan = Get-Content (Join-Path $PSScriptRoot 'plan.md') -Raw -Encoding utf8
    $rows = [regex]::Matches($plan, '(?m)^\| (T\d{2}) \|')
    if ($rows.Count -ne 10) { throw 'Plan table count mismatch' }
    $tableIds = @($rows | ForEach-Object { $_.Groups[1].Value } | Sort-Object)
    if (($tableIds -join ',') -ne ($ids -join ',')) { throw 'Table IDs mismatch' }
    $tasks = Get-Content (Join-Path $PSScriptRoot 'tasks.md') -Raw -Encoding utf8
    $cards = [regex]::Matches($tasks, '(?ms)^## (T0[89]) [^\r\n]+.*?(?=^## (?:T0[89]|Уточнение)|\z)')
    if ($cards.Count -ne 2) { throw 'Expected two new cards' }
    foreach ($card in $cards) {
        foreach ($field in @('Приоритет:','Сложность:','Зависимости:','Область','Работа:','Приёмка','Артефакты:')) {
            if (!$card.Value.Contains($field)) { throw "Missing card field: $field" }
        }
    }
    foreach ($level in @('debug','info','notice','warning','error','critical','alert','emergency')) {
        if ($tasks -notmatch ('\b'+$level+'\b')) { throw "Missing severity $level" }
    }
    foreach ($term in @('quiet','normal','diagnostic','trace','stdout','redaction','correlation','retention','overhead','process journal','run_completed')) {
        if (!$tasks.Contains($term)) { throw "Missing acceptance term $term" }
    }
    'PASS graph, table, task fields, severity and required safety coverage'
    foreach ($file in @(Get-ChildItem (Join-Path $PSScriptRoot 'evidence') -Filter '*.json')) {
        foreach ($item in @(Get-Content -LiteralPath $file.FullName -Raw -Encoding utf8 | ConvertFrom-Json)) {
            if (!(Test-Path -LiteralPath $item.path -PathType Leaf)) { throw "Missing evidence $($item.path)" }
        }
    }
    $oldBase = '.pf/artifacts/vision-alignment-plan-20260925'
    $hashes = @{
        'plan.md'='116FB10F714C99A4DE45BF4D9FFB3CE43B60CD161A6CD7064F25A8ADC1CE88CD'
        'tasks.md'='7AEA572EAC8E38F62216CBF9FD774A466D82465C4F84CDE4BBE5B5D43518F6D7'
        'baseline.md'='FA5A9EB4CB22E985DCE6623919D77B43690C18091AAD1BDD7B49E5E65A809E5F'
    }
    foreach ($file in $hashes.Keys) {
        if ((Get-FileHash (Join-Path $oldBase $file) -Algorithm SHA256).Hash -ne $hashes[$file]) { throw "Previous evidence changed: $file" }
    }
    'PASS evidence JSON and previous plan hashes'
    & git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Whitespace check failed' }
    $changes = @(& git status --porcelain -- src tools schemas templates docs bin packs requirements.txt pyproject.toml)
    if ($LASTEXITCODE -ne 0 -or $changes.Count) { throw "Product scope changed: $changes" }
    'PASS product scope'
    'RESULT: PASS'
}
finally { Pop-Location }
