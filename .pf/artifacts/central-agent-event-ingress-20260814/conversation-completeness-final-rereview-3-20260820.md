# conversation-completeness-final-rereview-3-20260820

**Итог: PASS_WITH_CONDITIONS.**

Каноническая правка закрывает ранее отмеченный blocker по изменяемому `native_event_id`: worker input/output теперь принимаются только с PF-каноническими native id. Условие: я не запускал smoke-тесты, потому что задание и текущий sandbox read-only; вывод основан на разрешённых source-файлах и уже предоставленном correction report.

## Evidence

- Durable lifecycle reconciliation закрыт: `codex_exec_worker.py:165-174,228-235` пишет durable `exit.json`; `processforge.py:17380-17385,17631-17643` наблюдает этот exit-contract и переводит `running` в terminal state; `worker-run status/collect` повторно reconcile-ит state перед выводом/сбором (`processforge.py:17832-17836,17876-17880`). Smoke покрывает это в `smoke_worker_run_shell.py:417-485`.

- Collectible report ordering закрыт: `worker-run collect` сначала требует collectible status и required outputs (`processforge.py:17884-17922`), затем читает expected report из PF-owned файла, формирует `WorkerExpectedReportCaptured`, вызывает Runtime ingress и требует ровно один captured assistant message (`processforge.py:17923-17960`). Только после этого вызывается `task_complete` (`processforge.py:17961`).

- Privacy filtering сохранён: unsafe automatic content отсекается по локальным путям/secret-like значениям (`host.py:647-651,775`; `processforge.py:1311-1316`), project-visible chat event по умолчанию содержит `content_mode: metadata_only`, а не полный текст (`processforge.py:10608-10623`). Smoke дополнительно проверяет отсутствие report content и workspace/capsule markers в runtime-visible output (`smoke_conversation_completeness.py:398-414`).

- PF-owned input/output provenance закрыт: input capture пишет `worker-input-contract.json` с hash, expected report и canonical summary (`codex_exec_worker.py:105-119`), Runtime заново сверяет payload hash и contract (`host.py:661-682`). Output capture принимается только если `report_content` совпадает с actual expected report file (`host.py:737-740`).

- Strict canonical native IDs закрыт: `WorkerPromptPayloadSubmitted` принимается только как `worker-input:<run>:<task>:attempt:<attempt>` (`host.py:699-704`), `WorkerExpectedReportCaptured` только как `worker-output:<run>:<task>:attempt:<attempt>:<sha256 report content>` (`host.py:705-711`; генерация в `processforge.py:17931-17933`). Negative smoke теперь явно отвергает alternate input/output ids (`smoke_conversation_completeness.py:351-356,401-406`).

- Logical idempotency теперь достаточна: derived `message_id` всё ещё зависит от raw receipt id (`host.py:777-792`), но для PF worker input/output raw id больше не произволен из-за строгих canonical native ids. Повторная доставка не создаёт вторую transcript строку: `append_chat_message` дедуплицирует под transcript lock по `message_id` (`processforge.py:10550-10584`), а `append_process_event` не пишет второй event с тем же `event_id` (`processforge.py:10424-10441`). Parallel smoke проверяет один message и один chat event (`smoke_conversation_completeness.py:391-396`).

## Conclusion

Блокеры из rereview-2 закрыты по коду: worker lifecycle reconciliation, ordering перед `task_complete`, privacy boundary, PF-owned provenance, canonical worker native IDs и logical idempotency согласованы. Остаточный риск только в том, что в рамках этого read-only rereview smoke-пакеты не были перезапущены; correction report заявляет `python tools/smoke_conversation_completeness.py`, `python tools/smoke_codex_exec_worker.py` и `events-validate --project-root .` как PASS.