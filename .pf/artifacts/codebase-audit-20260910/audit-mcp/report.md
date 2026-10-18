# Аудит MCP routing и worker collection

Редакция приёмки первичным агентом. Исходный отчёт shell-воркера сохранён в
`recovery-20260911/audit-mcp-original-attempt2.md`. Primary уточнил атрибуцию
примеров и описал абсолютный fixture-путь словами; исходные байты и все
воспроизводители сохранены. Эта редакция является итоговым PF-owned отчётом.

Дата: 2026-09-11  
База: `901d0551773fe7a5b382b89ebe95b212b0747e83`  
Область: `mcp_server.py`, `session_read.py`, `garage.py`, `codex_exec_worker.py`, worker collection в `processforge.py`.

Статус: выявлено 4 подтверждённых дефекта. Изменения в исходный код не вносились.

Примечание по проверке: повторный запуск real-subprocess probe был предпринят, но Windows sandbox запретил создание временной директории (`WinError 5`). Поэтому результаты ниже основаны на предоставленных recovery-артефактах реальных запусков, прямой трассировке исходников и сохранённых stdout/stderr. Это не mock-тесты.

## A02 — обход границы проекта через expected report path

Серьёзность: P1  
Статус: подтверждено реальным collector-прогоном.

Файлы и строки:

- `tools/processforge.py:18404-18410` — вычисление `expected_report_artifact`;
- `tools/processforge.py:12474-12479` — `task_output_path`;
- `tools/processforge.py:19057-19067, 19093` — чтение expected report;
- `tools/pf_runtime/host.py:850-858` — worker authorization проверяет путь, но не гарантирует containment.

Нарушенный контракт: expected report должен быть артефактом текущего проекта. При этом `tools/codex_exec_worker.py:159-161` уже проверяет containment для worker output, но collector и host такую же проверку не выполняют.

Триггер: assignment содержит `expected_report.artifact: ../outside.md`, а внешний файл содержит безопасный текст.

Ожидалось: отклонить traversal/absolute/symlink path до чтения файла, raw-ingress и chat derivation.

Фактически: collector дважды завершился с кодом `0`, прочитал внешний файл, создал одно assistant-сообщение и перевёл задачу в `done`.

Воспроизводимость:

```powershell
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_collection.py
```

Зафиксированный результат из `collection-primary-results.json`:

```text
external_report:
  collect_exit_codes: [0, 0]
  captured_assistant_messages: 1
  task_status: done
  assistant_contents_contains: OUTSIDE_FIXTURE_MARKER
```

Воздействие: assignment может заставить collector прочитать произвольный доступный файл за пределами project root и записать его содержимое в raw/chat storage.

Минимальное исправление: ввести единый canonical resolver для artifact paths:

1. нормализовать и `resolve()` путь;
2. требовать нахождение внутри `project_root.resolve()`;
3. отдельно отклонять absolute paths, `..`-escape и symlink escape;
4. выполнять проверку до открытия файла и до ingest.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/processforge.py`, `tools/pf_runtime/host.py`, regression probe/test.
- Acceptance checks:
  - `../outside.md`, absolute path и symlink escape отклоняются до чтения;
  - обычный `.pf/artifacts/report.md` успешно собирается;
  - при отказе нет assistant-сообщения и task не становится `done`;
  - повторный отказ остаётся детерминированным.
- Оценка: M.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## A06 — авторизованный report с путями теряется на conversation safety gate

Серьёзность: P2  
Статус: подтверждено реальным collector-прогоном.

Файлы и строки:

- `tools/pf_runtime/host.py:923-928` — после provenance authorization применяется `_is_safe_automatic_content`;
- `tools/processforge.py:19127-19130` — collector требует ровно одно chat-сообщение для завершения.

Нарушенный контракт: PF-owned report, прошедший проверку run/task/attempt/path/hash и exact content match, должен быть доступен как assistant transcript и позволять завершить задачу.

Триггер: легитимный report содержит абсолютный Windows-путь к module.py.
Точная строка сохранена в `recovery-20260911/verify_collection.py`; описание
здесь сохраняет смысл и не переносит абсолютные пути в собираемый отчёт.

Ожидалось: одно assistant-сообщение и успешное завершение collection.

Фактически: provenance-проверка проходит, но общий safety regex отклоняет содержимое как `unsafe_automatic_content`.

Воспроизводимость:

```powershell
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_collection.py
```

Зафиксированный результат:

```text
path_content:
  collect_exit_codes: [1, 1]
  first_capture:
    accepted: true
    deduplicated: false
    chat_message_ids: []
    conversation_reason: unsafe_automatic_content
  retry_capture:
    accepted: true
    deduplicated: true
    chat_message_ids: []
    conversation_reason: unsafe_automatic_content
  assistant_count: 0
  task_status: open
```

Это не дефект deduplication: duplicate raw receipt всё равно доходит до conversation derivation и повторно отклоняется тем же safety gate.

Воздействие: диагностические и audit reports с нормальными путями к исходникам невозможно собрать в transcript; raw receipt сохраняется, но task не завершается. Повторная попытка не помогает.

Минимальное исправление: после успешных worker provenance и exact file checks применять отдельную policy для PF-owned output, разрешающую path-like текст в теле отчёта. Secret scanning и проверки provenance/hash должны сохраниться. Общий safety gate должен продолжить применяться к untrusted/provider content.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/pf_runtime/host.py`, при необходимости `tools/processforge.py`, regression probe/test.
- Acceptance checks:
  - report с локальными путями создаёт ровно одно assistant-сообщение;
  - повторная collection не создаёт дубликат;
  - неверные provenance/hash/path/file и secrets по-прежнему отклоняются;
  - успешная collection завершает task.
- Оценка: M.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## A07 — mixed-case session ID не маршрутизируется

Серьёзность: P2  
Статус: подтверждено реальным MCP subprocess-прогоном.

Файлы и строки:

- `tools/processforge.py:17084-17085` — имя presence-файла строится через `safe_id`;
- `tools/processforge.py:17137-17148` — lookup session также применяет `safe_id`;
- `tools/processforge.py:17263-17274` — check-in сохраняет исходный session ID;
- `tools/pf_runtime/session_read.py:43-69` — authorization зависит от `find_agent_presence`.

Нарушенный контракт: session ID является opaque identity и должен использоваться без изменения регистра. Check-in сохраняет `Case-Session`, но lookup фактически ищет нормализованный идентификатор.

Триггер:

```text
agent-checkin --session Case-Session
MCP call pf.session_context --session Case-Session
```

Ожидалось: успешный `pf.session_context` с тем же session ID.

Фактически: check-in завершается успешно, но MCP возвращает `unknown_session`.

Контрольный lower-case session работает.

Воспроизводимость:

```powershell
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_primary.py
```

Зафиксированный результат:

```text
lower-session:
  checkin: 0
  pf.session_context: success

Case-Session:
  checkin: 0
  pf.session_context:
    error: unknown_session
    isError: true
```

Предыдущая collision-проверка также показала, что `Case-Session` и `case-session` используют одно нормализованное имя и могут сталкиваться.

Воздействие: MCP session context/chat/activity и Forge tools не работают для mixed-case IDs; разные opaque IDs могут быть ошибочно объединены.

Минимальное исправление: сохранить exact session ID. Для filesystem storage использовать collision-resistant encoding или digest с exact metadata/reverse lookup; не применять case-folding для сравнения. Проверить миграцию существующих presence-файлов.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/processforge.py`, `tools/pf_runtime/session_read.py`, при необходимости `tools/pf_runtime/host.py`, regression probe/test.
- Acceptance checks:
  - `Case-Session` успешно проходит check-in и MCP lookup;
  - `Case-Session` и `case-session` создают независимые presence records;
  - chat/activity используют правильную exact identity;
  - существующие lowercase IDs продолжают работать.
- Оценка: M.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## A08 — MCP JSON-RPC envelope и notification semantics не валидируются

Серьёзность: P2  
Статус: подтверждено реальным MCP subprocess-прогоном.

Файлы и строки:

- `tools/pf_runtime/mcp_server.py:290-308` — dispatch без полноценной JSON-RPC validation;
- `tools/pf_runtime/mcp_server.py:311-327` — обработка malformed input.

Нарушенный контракт:

- принимать только JSON-RPC 2.0;
- notification без `id` не должен получать response;
- невалидные `params` должны возвращать `-32602`;
- невалидный envelope/version должен возвращать `-32600`;
- malformed JSON должен возвращать `-32700`.

Триггеры и фактическое поведение:

1. Notification:

```json
{"jsonrpc":"2.0","method":"tools/list"}
```

Ожидалось отсутствие ответа. Фактически сервер возвращает `tools/list` response с `id: null`.

2. Неверная версия:

```json
{"jsonrpc":"1.0","id":2,"method":"initialize"}
```

Ожидалось `-32600`. Фактически возвращается обычный успешный JSON-RPC 2.0 response.

3. Неверные параметры:

```json
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"pf.context","arguments":[]}}
```

Ожидалось `-32602`. Фактически dispatch доходит до PF business logic и возвращает вложенную ошибку `missing_project_root` с `isError: true`.

При `params` в виде массива аналогично возвращается вложенная business error `missing_session`, вместо protocol error.

Воспроизводимость:

```powershell
python .pf/artifacts/codebase-audit-20260910/recovery-20260911/verify_primary.py
```

Зафиксированные результаты находятся в `.pf/artifacts/codebase-audit-20260910/recovery-20260911/mcp-primary-results.json`.

Воздействие: MCP-клиенты не могут надёжно отличить notification, malformed request, invalid params и PF runtime error. Это нарушает response counting, request correlation и может провоцировать повторные вызовы.

Минимальное исправление: до dispatch добавить bounded JSON-RPC validation:

1. проверить object envelope и `jsonrpc == "2.0"`;
2. проверить строковый `method`;
3. проверить object `params`;
4. проверить object `tools/call.arguments`;
5. применить schema validation, включая `additionalProperties`;
6. при отсутствии `id` подавлять response;
7. возвращать `-32600`/`-32602`, сохранив `-32700` для malformed JSON.

Изолированная remediation-задача:

- Разрешённые файлы: `tools/pf_runtime/mcp_server.py`, regression probe/test.
- Acceptance checks:
  - valid requests сохраняют текущие ответы;
  - notification не выдаёт response;
  - `jsonrpc != "2.0"` даёт `-32600`;
  - array/non-object params и arguments дают `-32602`;
  - malformed JSON даёт `-32700`;
  - неизвестные дополнительные поля отклоняются согласно schema.
- Оценка: S.
- Рекомендуемая junior-модель: `gpt-5.3-codex-spark`.

## Итог

В bounded-аудите подтверждены:

- обход project boundary через expected report path;
- потеря авторизованных reports с path-like содержимым;
- нарушение routing для mixed-case session IDs;
- нарушение JSON-RPC protocol semantics.

В `garage.py` и `codex_exec_worker.py` в рамках заданной области новых подтверждённых дефектов не установлено.
