# Investigation Report: Проблемы первого опыта PF от kimi-агента

## Общая оценка
ProcessForge — мощная система управления процессами, но для нового агента порог входа высокий. Требуется чтение множества документов, точное следование контрактам и понимание внутренних механизмов.

## Классификация проблем

### 1. Технические проблемы / Не работает
- **Glob не видит большие директории**: outbox с 140k+ файлов не перечисляется через Glob, приходится использовать Bash/Python. Это неудобно и замедляет работу.
- **Background tasks с большим выводом**: команды вроде `ls -la` на outbox убиваются из-за output limit. Нужны безопасные способы обхода.
- **MCP work-start валидация**: schema_version в scope_intent вызвал путаницу (сначала не принимал на верхнем уровне, потом требовал). Ошибка `must NOT have additional property` vs `must have required property` контринтуитивна.
- **Evidence формат**: для gate evidence нужен `kind: gate` и `status: approved`, для артефактов — `kind: artifact`. Это не очевидно из ошибок.
- **Continuation creation**: `work_scope_not_executable` при попытке создать continuation без явного scope. Требуется scope-file, что не документировано в первом сообщении.
- **Session absent**: hook на SessionStart не сработал, потому что сессия не была зарегистрирована в Ledger. Ожидалось автоматическое поведение, но его нет без ручной регистрации.

### 2. Трудно / Непонятно
- **Стартовый контракт**: `.pf/AGENTS.md` говорит "Call `pf.context`", но не объясняет, что после этого нужно еще и `pf.work.start` с явным scope для реальной работы.
- **Различие между continuation и work-start**: непонятно, когда использовать continuation vs новую Work.
- **Execution readiness blockers**: `read_scope_missing`, `product_write_scope_missing`, `artifact_write_scope_missing` — непонятно, как их устранить без изучения исходного кода (`creation_scope.py`).
- **Gate types**: checklist vs decision gates требуют разных статусов (`approved` vs `passed`). Нет явной подсказки в ошибках.
- **Allowed files syntax**: `.pf/artifacts/kimi-first-pf-evolve-*/**/*` — нужно догадаться про wildcard в scope JSON.

### 3. Неудобно
- **Многостадийность для простых задач**: 8 стадий (orchestration, intake, investigation, domain, architecture, implementation, assurance, release, evolve) для записи одного отчета — избыточно. Хотелось бы короткий режим для assurance/evolve-only работ.
- **Ручное создание артефактов**: каждый артефакт (brief, scope, task-record, gates, handoffs) нужно писать вручную. Нет автоматической генерации шаблонов.
- **Evidence JSON в командной строке**: передача evidence как JSON строк в `--evidence` неудобна и подвержена ошибкам. Лучше `--evidence-file`.
- **Отсутствие dry-run для transitions**: нельзя проверить, пройдет ли transition без реального вызова.
- **Windows-specific issues**: `ls -la` не работает в cmd, Git Bash имеет свои quirks с путями. PF CLI не всегда удобен на Windows.

### 4. Лишние действия
- **Повторное создание work**: первая Work `processforge-pf-outbox` была отменена из-за отсутствия scope. Пришлось создавать `processforge-pf-outbox-2` с scope-file.
- **Дублирование артефактов**: handoff notes для каждой стадии повторяют одну и ту же информацию (objective, known issues). Можно автоматизировать.
- **Session registration**: пришлось вручную вызывать `agent-checkin` и `session-heartbeat`, хотя hook `SessionStart` должен был это сделать. Это лишний шаг для агента.
- **Проверка outbox**: пришлось писать Python-скрипты для подсчета файлов в outbox вместо готовой команды PF.

## Выводы
- PF функционально работает, но требует глубокого понимания внутренних контрактов.
- Для новых агентов нужен упрощенный стартовый сценарий (quick start) и автоматические проверки.
- Хуки и Ledger работают, но регистрация сессии должна быть более прозрачной/автоматической.
