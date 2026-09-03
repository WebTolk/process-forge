# Проектирование первого stage projector

Дата: 2026-08-14

## Выбранный slice

Первый projector — `required-output-readiness`. Он активируется только тогда,
когда декларация стадии процесса содержит `technical_obligations` с
`projector: required-output-readiness`. Первая декларация добавлена к
`process-supervisor:collect`.

Это не новый workflow engine: ProcessForge Core по-прежнему владеет
assignment, process definition, Inspector state и exit gate. Runtime Host
лишь детерминированно строит отдельный технический снимок.

## Входы, владение и выход

| Элемент | Владелец | Роль в projector |
| --- | --- | --- |
| `processes/*` stage declaration | PF Core | Объявляет обязательство и gate. |
| assignment `required_outputs` / `expected_report` | PF Core | Объявляет допустимые ожидаемые файлы. |
| agent-run state | Execution Inspector | Определяет активную стадию, без вывода progress из heartbeat. |
| существование и digest output-файла | Файловая система проекта | Даёт проверяемый технический факт. |
| `stage-obligations.json` | Runtime Host projector | Единственный автоматически перезаписываемый артефакт. |

Проектор не записывает в отчёты, handoff, audit или другие semantic artifacts.
Их тело остаётся исключительной ответственностью человека/модели.

## Freshness и восстановление

Каждая строка содержит `source_fingerprint` от process obligation, assignment,
Inspector state и наблюдаемых output facts. При чтении текущий fingerprint
сравнивается с сохранённым:

- `current` — snapshot совпадает с авторитетными входами;
- `stale` — входы изменились, либо строка больше не активна;
- `missing` — derived file отсутствует или обязательный output отсутствует;
- `invalid` — projection или обязательство нельзя корректно интерпретировать.

`runtime-host rebuild-projections` строит command history и stage obligations
без Runtime. Runtime запускает тот же rebuild после ingress event и на
scheduler tick. `runtime-host projection-doctor` делает состояние отдельным
проверяемым gate; MCP только публикует его через существующий read-only
`pf.work_state`.

## Осознанно отложено

`changed-files` не выбран: нормализованный Codex event намеренно не хранит
полную команду или список изменённых путей, а поздний `git diff` не является
восстановимой исторической правдой после restart. Поэтому такой projector
нельзя честно назвать authoritative в этом slice.
