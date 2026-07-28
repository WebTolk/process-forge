# Общий механизм evolve

`evolve` - общий механизм ProcessForge для извлечения повторно используемых
знаний из процесса. Он объявляется отдельным top-level блоком в process
definition. Механизм не привязан к разработке ПО: его могут включать процессы
testing, content, authoring, setup и registration, либо отключать с явной
причиной.

Включённый evolve пишет локальные артефакты, обычно в конце run:

```text
.pf/artifacts/evolve/
  evolution-report.md
  evolution-report.yaml
  knowledge-candidates/
  instruction-update-proposals/
  process-improvement-proposals/
```

MVP создаёт только candidates. Он не обучает LLM, не меняет глобальные пакеты
автоматически и не обходит review/export boundary. Изменения общих пакетов идут
через file-first knowledge hub и существующую update system.

Отсутствующий `evolve` даёт WARN для draft/experimental процессов и FAIL для
PUBLIC_STABLE catalog validation.

## Targeting candidates

Извлечение candidates учитывает назначение изменения. Каждый candidate должен
содержать `source_context`, `target`, `applicability`, `generalization`,
`routing` и `promotion`, чтобы hub отличал место наблюдения от места курации.

Default policy - самый узкий безопасный scope. Project facts остаются
project-scoped, build/release findings идут в delivery profile, process-flow
изменения идут в process definition, а platform constraints попадают в
platform contract или knowledge package только с явным applicability.

Если одно наблюдение объединяет process improvement, platform knowledge и
delivery-profile policy, его нужно разделить до export.
