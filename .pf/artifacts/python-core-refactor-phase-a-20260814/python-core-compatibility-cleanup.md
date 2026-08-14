# Python Core Compatibility Cleanup

## Итог

Проверка по разрешённым источникам (`README*`, `QUICKSTART*`, `docs/**`, `examples/**`, `bin/pf.py`, `tools/processforge.py`, `tools/pf_runtime/**`, `.processforge-releaseignore`) подтверждает, что перед extraction нельзя считать весь compatibility-слой мусором. Часть алиасов остаётся публичным контрактом, часть уже явно помечена как transitional/deprecated, а несколько веток выглядят слабыми кандидатами на удаление, потому что в разрешённом публичном слое их потребителей не найдено.

Главная граница такая: публичный запуск = `bin/pf.py` для дистрибутива и `.pf/runtime/bin/pf.py` для подключённого проекта; прямой `tools/processforge.py` является внутренней реализацией launcher-а, а не публичным контрактом.

## Подтверждённые кандидаты

| Кандидат | Доказательство | Класс | Migration impact | Вывод |
|---|---|---|---|---|
| `context-resolve` | `tools/README.md:31-33`, `docs/getting-started.md:127-129`, `docs/concepts/context-resolution.md:89-90`, `tools/processforge.py:19837-19842` | transitional public API | medium | Оставить только как совместимость; при extraction не переносить как core-first API. |
| `context-compile` | `tools/README.md:31-33`, `docs/getting-started.md:127-129`, `docs/concepts/execution-context-package.md:9,24`, `tools/processforge.py:19849-19852`, `26087-26090` | transitional public API | medium | Такой же статус: совместимость для старых ECP-flow, не canonical surface. |
| `init-project` рядом с `project-onboard` | `README.md:252`, `docs/getting-started.md:36-39`, `docs/concepts/project-init.md:24`, `docs/concepts/project-flow-root.md:63` | active compatibility alias | medium | Удалять рано; можно выводить из топ-уровневых списков после миграции docs/examples. |
| `init-workplace` рядом с `workplace-init` | `README.md:249`, `docs/concepts/workplace-init.md:32-33`, `tools/processforge.py:24425-24430`; при этом почти все примеры учат `workplace-init` | lower-level alias behind active public name | low | Canonical оставить `workplace-init`; `init-workplace` можно сужать до low-level/maintainer surface. |
| `gates` alias для stage | `docs/authoring/process-authoring.md:47-50`, `tools/processforge.py:13666-13669`, `14324-14327`; в разрешённых examples употреблений `gates` не найдено | deprecated field alias with no positive public usage evidence | low-medium | Сильный кандидат на cleanup после проверки реальных private processes; в публичном authoring уже вытеснен. |
| `technical_obligations` | `docs/authoring/process-authoring.md:47-50`, `docs/concepts/runtime-model.md:67`, `tools/processforge.py:13668-13669`, `14326-14327` | deprecated but still documented compatibility field | medium | Нельзя объявлять мёртвым: поле ещё читается в docs как совместимое. Нужна явная миграция на `automation_bindings`. |
| `handoff_required` | `examples/process-authoring/*/answers.yaml` использует поле, `tools/processforge.py:14338-14341` помечает deprecated semantics | deprecated but actively consumed in examples | high | Не удалять в Phase A; сначала переписать examples/process templates и зафиксировать новую семантику. |
| legacy flat process layout | `docs/concepts/process-directory-layout.md:19`, `tools/processforge.py:12591-12623`, `12674-12677`, `14773-14818`, `25219-25221` | migration-only compatibility branch | medium | Похоже на brownfield-only ветку. Для core extraction можно выносить за основной API boundary, но не удалять без отдельного migration path. |

## Слабые кандидаты на удаление

| Кандидат | Доказательство | Класс | Impact | Вывод |
|---|---|---|---|---|
| `smoke-all` alias для `release-test` | Есть только в CLI: `tools/processforge.py:24615-24618`; в разрешённых `README/docs/examples` употреблений не найдено | weak alias | low | Лучший кандидат на cleanup или хотя бы на вывод из help/docs. |
| `builtin-process-catalog-doctor --project-root` как alias для `--root` | `tools/processforge.py:25170-25173`; в разрешённых docs/examples употреблений не найдено | weak parameter alias | low | Можно убирать рано, если нет скрытых scripts вне разрешённой области. |

## Не считать cleanup-кандидатами сейчас

| Поверхность | Доказательство | Вывод |
|---|---|---|
| `bin/pf.py` и `.pf/runtime/bin/pf.py` | `docs/concepts/workplace-vs-project.md:38-40`, `tools/README.md:4`, множественные docs/examples | Это не дубли-мусор, а два разных публичных entrypoint-а для distribution root и linked project. |
| прямой `tools/processforge.py` | `bin/pf.py:26-33`, `tools/pf_runtime/service.py:519`, `tools/processforge.py:6476-6483` | Это внутренний executable target launcher-а и runtime service. Публичные docs, наоборот, запрещают учить linked-project пользователей этому пути. |
| `session-*` vs `agent-*` | `docs/concepts/agent-session-model.md:88-95`, `README.md:270-274` | `session-*` уже user-facing thin wrappers; `agent-*` остаётся отдельной предметной поверхностью для ledger/director. Не dead code. |
| `supervisor*` vs `execution-inspector*` | `README.md:279-285`, `docs/concepts/director-ledger-inspector-boundary.md:36-40`, `tools/processforge.py:25362-25428` | Пара всё ещё активна в docs; `supervisor` исторический technical name, `execution-inspector-*` clearer aliases. Удалять рано. |
| `worker-run-*`, `runtime-driver-*`, `orchestrator-shell-plan-*` | Есть и в CLI, и в docs/examples | Это активная публичная поверхность, а не мёртвый compatibility слой. |

## Рекомендуемый cleanup-порядок

1. Считать canonical для extraction: `bin/pf.py`, `.pf/runtime/bin/pf.py`, `project-onboard`, `workplace-init`, `exit_gates`, `automation_bindings`.
2. Пометить как transitional boundary, но не ломать в Phase A: `context-resolve`, `context-compile`, `init-project`, `technical_obligations`, legacy flat process layout.
3. Подготовить ранний cleanup-кандидатный список: `smoke-all`, `builtin-process-catalog-doctor --project-root`, `gates`.
4. Отложить breaking cleanup до миграции examples/templates: `handoff_required`, `supervisor*`, `session-*`/`agent-*` пары.
5. В Python Core boundary не тащить публичный контракт на прямой `tools/processforge.py`; оставить его внутренним adapter target.

## Краткий вывод для Phase A

Минимально безопасная линия для upcoming Python Core extraction: отделять canonical public commands от compatibility aliases, но не удалять всё deprecated механически. По подтверждённым данным самые слабые ветки сейчас: `smoke-all`, `builtin-process-catalog-doctor --project-root`, и `gates`. Самые опасные для преждевременного удаления: `handoff_required`, legacy flat process layout, `supervisor*`, `session-*`, `context-*` compatibility commands.