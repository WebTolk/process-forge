# T08 — MCP operability: scope and context

- date: 2026-09-25
- process: software-feature-development@1.1.0
- lifecycle_mode: bug_fix
- coordination: single_agent
- run: garage-t08-mcp-operability-reproduce-current-source-versus-installed-mcp
- source_assignment: t08-mcp-operability-reproduce-current-source-versus-installed-mcp-freshn
- source_commit: a180ad624442d4fbe8ac1710073ef7d4c44babc4
- status: ready_for_review

## Task record / brief

Оператор поручил выполнять план r02 поэтапно. Первый обязательный срез после
preflight T00 — T08. Реализация плана теперь разрешена; прежняя пометка
operator_implementation_approval: pending относится к исторической поставке
плана и не отменяет новое прямое поручение. T01/T09 и следующие задачи не
объединяются с текущим ремонтом MCP. Удалённый веб — далеко позже, local web UI
исключён; T10 остаётся отдельным предложением.

Цель: устранить реальное расхождение MCP/source CLI без отключения freshness,
сохранить авторизацию/протокол и подтвердить работу через реальный клиент.

## Execution context / lifecycle decision

Source CLI context-check --session-start дал fresh, execution ready,
policy continue для ctx-20260925-140110-0dbc7c; health warn, не полный health PASS.
Подключённый MCP для того же snapshot сообщает stale; pf.work.start блокирован
snapshot_not_fresh. Для ремонта создана отдельная Work source CLI.
Assignment и immutable capsule прочитаны; generic implementation permission
ограничивается scope ниже. Process pin cc411028e9585dd8f56e07faa8997d9e7af1a39a801a0d8c0ca9c8c1e89dfd49.

Platform selected: none. Shared toolchain overlay не выбран; в доступном
toolchain root нет Python контракта. Используются локальные Python smoke tests.
Serena Active languages: []; fallback — узкий rg/UTF-8 анализ и Git history.
Применимых development skills в разрешённом skills root не найдено;
проектный PF процесс и его agent prompt определяют поток.

## Allowed / forbidden scope

Разрешены .pf/artifacts/t08-mcp-operability-20260925/**, .pf/logs/t08-mcp-operability-20260925.md,
.pf/handoffs/t08-mcp-operability-20260925.md, штатные состояния нового Run.
Исходники, история Git, установленный Core, конфигурация/identity процессов,
существующие журналы и release metadata читаются для диагностики.

До подтверждения новой причины продуктовые исходники не меняются.
Если нужен новый source patch, уточнить file scope после investigation и
архитектуры, добавить регрессию; не дублировать уже исправленный дефект.
Установленные Core/Workplace и конкретный MCP-клиент не менять/перезапускать
без записанного плана воздействия, сохранения журналов, rollback и согласования
соответствующих операций. Никакого массового рестарта или горячей подмены памяти.
Чужие dirty-файлы, прошлые runs/capsules/планы остаются неизменными.

## Acceptance

1. Точная причина подтверждена одинаковым snapshot, classifier content и
   сравнением classification/provenance, а не только предположением о версии.
2. Минимальный source repair либо существующий fix подтверждён регрессиями.
3. Реальный MCP context/search/resolve и изолированный Work lifecycle проходят;
   отсутствие/чужая session и genuinely stale данные корректно отвергаются.
4. Live acceptance не подменяется source subprocess tests.
5. Если необходим установленный update или reconnect, работа не объявляется
   завершённой до этого; конкретный операторский выбор фиксируется отдельно.

## Initial observations

MCP entry point относится к installed-core/tools/pf_runtime/mcp_server.py,
workplace — установленное рабочее место. Direct installed CLI воспроизвёл
stale с единственной причиной project classification changed.
В source есть project_classifier_source_label, добавленный c810381;
в installed используется legacy basename для внешнего classifier.
Это сильное основание; точное comparison evidence собирается следующим шагом.
