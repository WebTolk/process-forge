# Матрица возможностей provider/event ingress

## Граница сверки
- Разрешённые источники этой сверки: `tools/pf_runtime/codex_hooks.py`, `.pf/artifacts/central-agent-event-ingress-20260814/provider-official-contracts-audit.md`, текущая версия этой матрицы.
- Ниже раздельно показаны:
  - фактическая реализация в PF;
  - наличие официального provider contract;
  - design target в PF.
- Утверждения, которые нельзя подтвердить в этой области чтения, удалены. Поэтому здесь нет отдельных provider-строк для `Cursor`, `OpenCode`, `WTAICC`, `webhook`, `command hooks`.

## Provider matrix
| Provider | Фактическая реализация в PF | Официальный contract | Design target в PF | Локально подтверждённое покрытие PF | Официально подтверждённое покрытие provider | Source URL | Accessed at | Локальное доказательство |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Codex` | `implemented, partial` | `available` | `yes` | В `tools/pf_runtime/codex_hooks.py` реализованы только `SessionStart`, `SessionEnd`, `PostToolUse`. Для `SessionStart` покрыты только `startup`, `resume`, `compact`. Требуются `cwd` и `session_id`. `PostToolUse` нормализуется в `agent.command.completed`, а при `tool_name != Bash` в `agent.tool.completed`. Доставка идёт через Runtime `/event` с fallback на `host.ingest_event()`. | По аудиту официальный contract шире: есть `SessionStart`, `SessionEnd`, `SubagentStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`; для `SessionStart` документированы `startup`, `resume`, `clear`, `compact`. | `https://learn.chatgpt.com/docs/hooks`<br>`https://learn.chatgpt.com/docs/config-file/config-reference` | `2026-08-14` | `tools/pf_runtime/codex_hooks.py:21-25,46-70,73-107` |
| `Claude Code` | `not implemented` | `available` | `yes` | В разрешённой области нет отдельного PF adapter-а. | По аудиту официальный contract доступен и богаче локального Codex PoC: включает user prompt, assistant display/stream, permission, failures, compact, subagent lifecycle и др. | `https://code.claude.com/docs/en/hooks` | `2026-08-14` | Отсутствие adapter-а зафиксировано в `.pf/artifacts/central-agent-event-ingress-20260814/provider-official-contracts-audit.md` |
| `Gemini CLI` | `not implemented` | `available` | `yes` | В разрешённой области нет отдельного PF adapter-а. | По аудиту официальный contract доступен: `BeforeTool`, `AfterTool`, `BeforeAgent`, `AfterAgent`, `BeforeModel`, `AfterModel`, `BeforeToolSelection`, `SessionStart`, `SessionEnd`, `Notification`, `PreCompress`. При этом permission/subagent/post-compact surface официально не подтверждён. | `https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/hooks/reference.md` | `2026-08-14` | Отсутствие adapter-а зафиксировано в `.pf/artifacts/central-agent-event-ingress-20260814/provider-official-contracts-audit.md` |

## Локальный ingress, который не является provider contract
| Adapter | Роль | Статус | Что можно подтвердить в этой области |
| --- | --- | --- | --- |
| `Runtime /event` | Локальный PF transport, не внешний provider | `present as transport target` | `codex-hooks` пытается доставить нормализованное событие в Runtime `/event`, а при недоступности использует fallback на `host.ingest_event()`. Полный contract самого `/event` в этой assignment-сверке не подтверждался, потому что соответствующие файлы вне разрешённой области чтения. |

## Короткий вывод
- Подтверждённый provider adapter в PF сейчас только один: `Codex`, и он покрыт частично.
- `Claude Code` и `Gemini CLI` имеют подтверждённые официальные hook contracts, но в разрешённой области PF adapter-ы для них отсутствуют.
- `Runtime /event` важно не путать с provider adapter: в этой сверке он подтверждён только как локальный транспорт, через который `codex-hooks` пытается отправить уже нормализованное событие.
