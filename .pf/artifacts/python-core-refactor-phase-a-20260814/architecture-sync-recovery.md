# Architecture Sync Recovery

## Статус
`target-architecture-recovered`

## Что восстановить
- Взять исходное содержимое target architecture из `.pf/runtime/agent-runs/python-core-refactor-phase-a-20260814/python-core-target-architecture-options/stdout.log`.
- Граница восстановления: от заголовка `# Python Core Target Architecture` до строки непосредственно перед `# Sync Report: Python Core Target Architecture`.
- Хвост `Sync Report` в `.pf/artifacts/python-core-refactor-phase-a-20260814/python-core-target-architecture.md` не переносить.

## Единственная допустимая правка после восстановления
В разделе `## Phased migration для первого среза` нужно оставить исходный текст и изменить только Phase 3:

- заменить `### Phase 3. Convert runtime read surfaces`
- на `### Phase 3. Shared Process Definition API for CLI, runtime host, MCP facade, and hooks`

Смысл Phase 3 должен быть таким:
- `CLI`, `runtime host`, `MCP facade` и hooks переходят на один и тот же `Process Definition API`;
- это общий shared slice, а не отдельный runtime-first шаг;
- `ingest_event`, projections, work-state, runtime transport и worker lifecycle в этот Phase 3 не входят.

`Phase 4` должен остаться отдельным runtime-срезом:
- `### Phase 4. Extract runtime work-state/event slice`

## Сверка
Эта правка синхронизирует target architecture с:
- `architecture-reconciliation.md`
- `python-core-refactor-plan.md`
- `reconciliation-review.md`

Итоговая последовательность должна читаться так:
- `Phase B`: bootstrap/import stabilization
- `Phase C` по смыслу целевого артефакта: общий `Process Definition API` для `CLI + runtime host + MCP facade + hooks`
- следующий отдельный срез: `event/projection/work-state/runtime transport`