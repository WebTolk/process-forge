# Knowledge candidates

Knowledge candidate - это sanitised YAML proposal, который создаёт общий
`evolve`. Он использует `kind: processforge.knowledge_candidate` и хранит target
type, category, summary, evidence, sensitivity, review state, curation state и
release inclusion.

Generic target types:

- `knowledge_package`
- `template_package`
- `process_definition`
- `delivery_profile`
- `project_rule`
- `platform_contract`

Candidates остаются локальными, пока оператор не поставит их в очередь, не
санитизирует, не экспортирует, не импортирует и не отберёт их для пакета.
Export блокирует неснятые private paths и secret-like values.

## Targeting И Applicability

Новый кандидат явно разделяет три вопроса:

- `source_context`: где наблюдение было получено.
- `target`: куда предлагается поместить изменение.
- `applicability`: где правило применимо, где не применимо и при каких условиях.

По умолчанию используется самый узкий безопасный scope. Наблюдение из проекта
не становится правилом workplace или parent platform без отдельного
обоснования. Если один вывод смешивает project-specific факт, platform
knowledge, delivery profile и process improvement, его нужно разбить на
несколько кандидатов с разными `target`.

`generalization.level` показывает, является ли запись узким наблюдением,
project rule, package rule, platform rule, parent-platform candidate,
parent-platform rule или universal rule. Child-platform observation не
продвигается в parent platform автоматически; для этого нужен явный
`promotion` block и review evidence.
