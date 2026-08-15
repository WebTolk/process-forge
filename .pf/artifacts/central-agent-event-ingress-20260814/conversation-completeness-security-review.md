# Conversation Completeness Security Review

## Вердикт

`FAIL`

Текущая корректировка в предложенном виде не проходит security review. Raw-first и разделение telemetry/conversation реализуемы, но PF-owned input capture сейчас спроектирован в точке и в форме, которые нарушают требование assignment.

## Подтверждённые факты

- Raw-first boundary уже существует: `host.ingest_event()` сначала создаёт `NativeAgentEvent`, затем вызывает `RawIngressKernel.ingest(...)`, и только после успешного raw receipt пытается маршрутизировать derived effect (`tools/pf_runtime/host.py:643-683`, `tools/pf_runtime/raw_ingress_kernel.py:180-231`).
- Private transcript и metadata-only `chat.message.recorded` уже существуют: `append_chat_message()` пишет тело в `.pf/runtime/chat/transcripts/...`, а event по умолчанию содержит только `content_hash`, `redaction`, `content_ref`, `content_mode=metadata_only` (`tools/processforge.py:10526-10590`).
- PF-owned worker output можно безопасно брать из expected report/output file после completed/collectible boundary: `command_worker_run_collect()` сначала проверяет terminal status и наличие expected report, затем завершает задачу и пишет `worker.run.collected` (`tools/processforge.py:17824-17875`).

## Блокирующие замечания

1. Предложение требует писать в transcript “exact PF-owned stdin prompt payload”, но реальный `prompt_payload()` включает полный capsule text и абсолютный путь к `workspace_access_file` (`tools/codex_exec_worker.py:56-74`, фактическая отправка в stdin: `tools/codex_exec_worker.py:150-152`).
   Это конфликтует с boundary assignment: нельзя копировать workplace-only capsule/workspace-access или absolute-path data в project transcript.
   В текущем виде такой input capture перенесёт private absolute-path data в `.pf/runtime/chat/transcripts/...`.

2. Указанная implementation boundary для input capture неточна.
   Proposal говорит о capture “before `subprocess.Popen` in worker run start path”, но `Popen` в `command_worker_run_start()` запускает только wrapper-процесс (`tools/processforge.py:17718-17811`).
   Канонический stdin payload формируется и уходит в Codex уже внутри `tools/codex_exec_worker.py` через `subprocess.run(...)` (`tools/codex_exec_worker.py:150-152`).
   Значит, capture в `worker_run_start` не является доказуемо “exact canonical source”, если не вынести генерацию payload в общий helper и не привязать обе стороны к одному и тому же digest.

## Что нужно изменить, чтобы review мог стать PASS

1. Оставить exact PF-owned stdin payload только в workplace-private raw ingress storage.
   В project transcript нельзя писать полный `prompt_payload()`.

2. Для transcript вводить не exact launch body, а sanitised system message.
   Допустимо хранить только безопасный PF-derived summary:
   `run_id`, `task_id`, worker id/role, expected report artifact, payload hash/content_ref на private raw receipt.
   Нельзя включать:
   `workspace_access_file`, его содержимое, capsule body целиком, absolute paths.

3. Перенести authoritative input capture на реальную boundary точку.
   Либо эмитить `WorkerPromptPayloadSubmitted` из `tools/codex_exec_worker.py` непосредственно перед `subprocess.run(...)`,
   либо вынести `prompt_payload()` в общий детерминированный builder и фиксировать один и тот же hash на стороне `processforge.py` и `codex_exec_worker.py`.

4. Явно закрепить в conversation contract запрет на transcript content/source, содержащие private absolute paths или workspace-access references.
   Иначе proposal всё ещё оставляет путь к утечке даже при “private transcript”.

## Итог

`conversation-completeness-correction.md` пока не проходит.

Неблокирующая часть proposal корректна:
- raw-first через central ingress;
- отдельный sink для `derived_conversation_messages[]`;
- metadata-only `chat.message.recorded`;
- assistant capture только из expected report/output file, а не из heartbeat/exit/stdout/stderr.

Блокирует именно PF-owned input side:
- неправильная authoritative boundary;
- недопустимая запись exact launch payload в project transcript.
