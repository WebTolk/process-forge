# Evolve Report: Первый опыт работы kimi-агента с ProcessForge

**Дата:** 2026-10-21  
**Агент:** Kimi (kimi-session-20261021)  
**Роль:** Новый агент, впервые работающий с PF  
**Задача:** Аудит, регистрация сессии, проверка хуков, запись evolve-отчёта

---

## Общее впечатление

ProcessForge — мощная, но сложная система. Для агента, впервые сталкивающегося с PF, порог входа очень высокий. Многие действия, которые должны быть автоматическими или очевидными, требуют глубокого знания внутренних контрактов, чтения исходного кода и проб/ошибок.

---

## 1. Что не работает / сломано

### 1.1. Glob не справляется с большими директориями
- **Проблема:** `.pf/runtime/hooks/outbox/wtaicc/` содержит 140 000+ файлов. Glob возвращает «No matches found» или не показывает файлы, хотя они существуют.
- **Влияние:** Невозможно быстро проверить наличие хуков. Пришлось писать Python-скрипт с `glob` и `os.listdir`, что должно быть встроенной функцией PF.
- **Ожидание:** `pf hooks status` или аналогичная команда должна показывать количество и примеры payload'ов без ручного сканирования.

### 1.2. Session hook не регистрирует сессию автоматически
- **Проблема:** При старте сессии `SessionStart` hook не вызвал `agent-checkin` в Ledger. Статус сессии оставался `absent`.
- **Влияние:** Пришлось вручную вызывать `agent-checkin` и `session-heartbeat`, хотя это должна делать инфраструктура PF.
- **Ожидание:** Если host hooks настроены, PF должен сам регистрировать сессию при первом событии от host.

### 1.3. Ошибки MCP/CLI не дают actionable remediation
- **Проблема:** При `work-start` с `scope_intent` получил противоречивые ошибки: `must NOT have additional property 'schema_version'` и `must have required property 'schema_version'`.
- **Влияние:** Потратил время на чтение `src/processforge_core/work/creation_scope.py`, чтобы понять правильный формат.
- **Ожидание:** Ошибка должна содержать пример корректного JSON или ссылку на схему.

### 1.4. Evidence формат не очевиден
- **Проблема:** Для gate evidence нужен `kind: gate` и `status: approved`, для артефактов — `kind: artifact`. Ошибка `evidence_status_not_acceptable` не объясняла, какой статус нужен.
- **Влияние:** Несколько неудачных попыток `work-transition`, пока не нашёл рабочую комбинацию в исторических assignment'ах.
- **Ожидание:** PF должен подсказывать допустимые значения при ошибке или иметь `--evidence-template` для генерации.

### 1.5. Background tasks с большим выводом убиваются
- **Проблема:** `ls -la .pf/runtime/hooks/outbox/wtaicc/` убит из-за output limit (>16 MiB).
- **Влияние:** Невозможно использовать стандартные команды для инспекции больших директорий.
- **Ожидание:** PF CLI должен иметь безопасные команды для работы с большими объемами данных.

---

## 2. Что трудно

### 2.1. Понимание scope и execution readiness
- **Проблема:** `work-start` создал Work с `execution_readiness: blocked` из-за `read_scope_missing`, `product_write_scope_missing`, `artifact_write_scope_missing`. Remediation `create_explicitly_scoped_successor` не объясняла, как именно создать scope.
- **Что пришлось сделать:** Отменить Work, создать `.pf/tmp/pf-audit-hooks-scope.json` с правильной структурой `{schema_version: 1, assignment: {allowed_actions: [...], allowed_files: [...]}}` и перезапустить.
- **Почему трудно:** Формат scope JSON не документирован в стартовом контракте `.pf/AGENTS.md`.

### 2.2. Различие continuation и work-start
- **Проблема:** Непонятно, когда использовать `continuation-create` vs `work-start`. `continuation-create` отказал с `work_scope_not_executable`.
- **Влияние:** Лишние вызовы и отмены Work.

### 2.3. Gate types и статусы
- **Проблема:** `checklist` gate требует `status: approved`, `decision` gate тоже принял `approved`. Но в исторических assignment'ах видел `status: passed` и `result: pass`. Неясно, есть ли разница.
- **Влияние:** Неуверенность в корректности evidence.

---

## 3. Что непонятно

### 3.1. Зачем нужны 8 стадий для простого evolve-отчёта
- **Проблема:** Для записи одного отчёта пришлось пройти orchestration, intake-scope, investigation, domain-modeling, architecture-plan, implementation, code-assurance, release-delivery, evolve.
- **Влияние:** ~80% времени тратится на формальности, а не на содержание отчёта.
- **Вопрос:** Есть ли короткий режим для assurance/evolve-only работ? Если нет — почему?

### 3.2. Как работают хуки в Forge vs Garage режимах
- **Проблема:** `.pf/hooks.yaml` имеет `mode: outbox`, но workplace mode `organized` (Forge). В setup-report написано, что `runtime.garage_hooks: false` irrelevant в Forge mode. Непонятно, что это значит для доставки хуков.
- **Влияние:** Неясно, должны ли хуки работать «из коробки» или требуют daemon.

### 3.3. Связь между PF event и outbox payload
- **Проблема:** Не сразу понятно, что Work transitions автоматически создают outbox payloads. Пришлось читать `process_execution.py`, `work/events.py`, `work/transition_commit.py`, `agents/process_events.py`, `agents/hook_dispatch.py`.
- **Ожидание:** Документация `docs/concepts/hooks-events.md` должна явно показывать эту цепочку.

---

## 4. Что неудобно

### 4.1. Ручное создание артефактов
- **Проблема:** Каждый артефакт (brief, scope, task-record, gates, handoffs) нужно писать вручную. Нет `pf artifact scaffold` или шаблонов.
- **Влияние:** Копипаст и повторение одной и той же структуры.

### 4.2. Evidence через командную строку
- **Проблема:** Передача `--evidence '{"kind": "artifact", ...}'` неудобна, подвержена ошибкам quoting/escaping.
- **Решение:** Использовал `--evidence-file`, но он не заработал с массивом (принял только один объект?).
- **Ожидание:** `--evidence-file` должен поддерживать массив evidence объектов.

### 4.3. Отсутствие dry-run для transitions
- **Проблема:** Нельзя проверить, пройдёт ли transition, не выполняя его.
- **Влияние:** Несколько неудачных переходов, которые могли бы быть проверены заранее.

### 4.4. Windows-специфичные проблемы
- **Проблема:** `ls -la` не работает в `cmd`, Git Bash имеет свои quirks. Пути с обратными слешами требуют экранирования в Python.
- **Влияние:** Дополнительное время на адаптацию команд.

---

## 5. Лишние действия

### 5.1. Отмена и пересоздание Work
- **Что произошло:** Первая Work `processforge-pf-outbox` создана без scope, отменена, создана `processforge-pf-outbox-2` с scope-file.
- **Почему лишнее:** Если scope обязателен, `work-start` должен требовать его сразу или предлагать интерактивный wizard.

### 5.2. Дублирование handoff notes
- **Проблема:** Каждый handoff повторяет objective, known issues, next action. Это boilerplate.
- **Ожидание:** PF должен генерировать handoff template автоматически на основе текущего stage.

### 5.3. Ручная регистрация сессии
- **Проблема:** Пришлось вызывать `agent-checkin` и `session-heartbeat` вручную.
- **Ожидание:** Это должна делать инфраструктура PF при корректно настроенных host hooks.

### 5.4. Поиск больших директорий через Python
- **Проблема:** Для подсчёта файлов в outbox пришлось писать `python -c "import glob, os; ..."`.
- **Ожидание:** `pf hooks status --outbox` или аналог.

---

## 6. Что работает хорошо

- **Work transitions:** После правильного scope и evidence формата, transitions проходят стабильно.
- **Outbox auto-recording:** Хуки действительно записываются автоматически при process events и supervisor ticks.
- **Ledger:** Agent Ledger работает, `agent-ledger-doctor` валидирует 50k+ событий.
- **MCP tools:** `pf.session_heartbeat` и `pf.chat_record` работают корректно и быстро.

---

## 7. Рекомендации по улучшению

### Критичные (для новых агентов)
1. **Автоматическая регистрация сессии:** PF должен регистрировать сессию в Ledger при первом host hook, если host hooks настроены.
2. **Quick-start режим:** Добавить `--mode quick-assurance` или аналог, который пропускает промежуточные стадии для assurance/evolve-only работ.
3. **Actionable ошибки:** Все ошибки валидации должны содержать пример корректного JSON или ссылку на схему.
4. **Scaffold артефактов:** `pf work scaffold --stage <stage>` для генерации шаблонов артефактов и evidence.

### Важные
5. **Evidence file array support:** `--evidence-file` должен принимать JSON-массив evidence объектов.
6. **Dry-run transitions:** `pf work-transition --dry-run` для проверки без выполнения.
7. **Outbox management:** `pf hooks status --outbox` и `pf hooks clean --outbox --before <date>`.
8. **Windows path handling:** Улучшить поддержку Windows путей в CLI и документации.

### Желательные
9. **Interactive work-start:** Wizard для создания scope JSON при `work-start` без `--scope-file`.
10. **Handoff templates:** Автогенерация handoff notes на основе текущего stage и истории.

---

## 8. Заключение

ProcessForge функционально справляется с задачами, но требует от агента глубокого знания внутренних механизмов. Для широкого adoption среди новых агентов необходимо снизить порог входа: автоматизировать сессии, упростить assurance-потоки, сделать ошибки actionable и добавить scaffolding.

Этот отчёт записан для дальнейшего улучшения PF и может быть использован как основа для planning-only Work по улучшению onboarding experience.
