# Аудит официальных provider event/hook contracts

Исторический контекст из памяти использован только как фон для проверки границ задачи; выводы ниже основаны на текущем чтении разрешённых файлов репозитория и актуальных официальных источников на 2026-08-14.

## 1. Подтверждено по репозиторию

- Реально реализованный inbound provider adapter в разрешённой области: `Codex` через `tools/pf_runtime/codex_hooks.py`.
- Явно намеченные adapters в master prompt: `Codex`, `Claude Code`, `Gemini CLI`.
- Других конкретных ingress-providers в разрешённых источниках не найдено.
- Локальный `Codex` PoC сейчас принимает только `SessionStart`, `SessionEnd`, `PostToolUse`.
- Для `SessionStart` локально обработаны только `startup`, `resume`, `compact`; официальный `clear` в локальном adapter-е не покрыт.
- Локально не реализован inbound capture для `PreToolUse`, `PermissionRequest`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact`, `PostCompact`.
- `docs/concepts/hooks-events.md` согласован с кодом: там также заявлен только узкий Codex adapter на `SessionStart`, `SessionEnd`, `PostToolUse`.

## 2. Официальные контракты

| Provider | Официальный источник | Дата доступа | Что подтверждено официально | Что не подтверждено / отсутствует | Статус в PF |
| --- | --- | --- | --- | --- | --- |
| Codex | https://learn.chatgpt.com/docs/hooks ; https://learn.chatgpt.com/docs/config-file/config-reference | 2026-08-14 | Есть hook events `SessionStart`, `SessionEnd`, `SubagentStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`; общие поля включают `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `model`; для relevant events документирован `permission_mode`; tool hooks дают `tool_name`, `tool_use_id`, `tool_input`; hooks включены по умолчанию; реально исполняются только handlers типа `command` | Отдельный официальный per-message assistant stream hook в найденной документации не подтверждён; `transcript_path` прямо помечен как convenience, а не stable hook interface | Реализован частично |
| Claude Code | https://code.claude.com/docs/en/hooks | 2026-08-14 | Богатый event surface: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `UserPromptExpansion`, `MessageDisplay`, `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`, `PreCompact`, `PostCompact`, `Notification`, `Elicitation`, `ElicitationResult`, др.; доступны handler types `command`, `http`, `mcp_tool`; для части событий также `prompt` и `agent`; `UserPromptSubmit` даёт user prompt, `MessageDisplay` даёт assistant text delta, `PostCompact` даёт `compact_summary` | Отдельный subagent message stream как самостоятельный event в проверенном источнике не подтверждён; есть `SubagentStart/Stop`, но не отдельный per-message subagent transcript event | Намечен, adapter отсутствует |
| Gemini CLI | https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/hooks/reference.md | 2026-08-14 | Документированы `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `SessionStart`, `SessionEnd`, `Notification`, `PreCompress`; общие поля: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `timestamp`; user prompt есть в `BeforeAgent.prompt`; assistant final text есть в `AfterAgent.prompt_response`; model chunks доступны через `AfterModel.llm_response`; hooks currently command-only | Permission event не найден; subagent events не найдены; post-compaction event не найден, есть только `PreCompress` | Намечен, adapter отсутствует |

## 3. Ключевые расхождения между официальным Codex contract и текущим PF adapter

- `[официально]` Codex умеет больше, чем текущий PF PoC: помимо `SessionStart/SessionEnd/PostToolUse` есть `PreToolUse`, `PermissionRequest`, `UserPromptSubmit`, `SubagentStart`, `SubagentStop`, `Stop`, `PreCompact`, `PostCompact`.
- `[локально подтверждено]` PF пока не захватывает эти дополнительные Codex events.
- `[официально]` Для `SessionStart` у Codex есть `startup`, `resume`, `clear`, `compact`.
- `[локально подтверждено]` PF сейчас не покрывает `clear`.
- `[официально]` Codex tool hooks дают стабильные tool-level поля, но не обещают стабильный интерфейс через transcript file.
- `[локальный вывод]` Центральный ingress нельзя строить вокруг чтения transcript как канонического API; raw envelope должен опираться на hook payload.

## 4. Практический вывод для capability matrix

- Честный текущий статус `Codex`: `official contract available`, `provider implemented`, `coverage partial`.
- Честный текущий статус `Claude Code`: `official contract available`, `provider intended`, `adapter absent`.
- Честный текущий статус `Gemini CLI`: `official contract available`, `provider intended`, `adapter absent`.
- Для `Codex` нельзя заявлять автоматический capture user/assistant/subagent chat как уже реализованный в PF.
- Для `Claude Code` можно проектировать richer envelope: есть официальный user prompt, assistant stream, permission, compact, failure, subagent lifecycle.
- Для `Gemini CLI` нельзя выдумывать permission/subagent/post-compact vocabulary: в найденном официальном contract этого нет.
- Минимально честная provider-neutral база сейчас: `provider`, `adapter`, `native_event_type`, `native_event_id`/dedupe key, `received_at`, `session_id`, `cwd`, `raw_payload`, плюс optional capability flags per provider.

## 5. Рекомендуемое обновление матрицы источников

| Provider | Source URL | Accessed at |
| --- | --- | --- |
| Codex | https://learn.chatgpt.com/docs/hooks | 2026-08-14 |
| Codex | https://learn.chatgpt.com/docs/config-file/config-reference | 2026-08-14 |
| Claude Code | https://code.claude.com/docs/en/hooks | 2026-08-14 |
| Gemini CLI | https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/hooks/reference.md | 2026-08-14 |
