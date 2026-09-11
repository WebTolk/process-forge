# Native ingress audit — bounded pass

Дата: 2026-09-10  
Базовый commit: `901d0551773fe7a5b382b89ebe95b212b0747e83`  
Граница: `tools/pf_runtime/host.py` (`ingest_event()`, `_conversation_messages()`, `_allowed_conversation_message()`, `_worker_session_authorized()`), `tools/processforge.py` (`command_worker_run_collect()` и helpers expected report). Product files не изменялись.

Проверка выполнена из [probe_native_ingress.py](probe_native_ingress.py). Проба импортирует текущий source, подменяет только RawIngress/Core границы и использует disposable system temp fixture. Результат: [evidence/probe-result.json](evidence/probe-result.json). Команда:

```text
python .pf/artifacts/codebase-audit-20260910/native-ingress/probe_native_ingress.py
```

В пробе provenance для worker report проходит отдельно: `_allowed_conversation_message(...) == true`. Поэтому результат не повторяет прежнее ошибочное утверждение, будто этот сценарий был остановлен provenance-проверкой.

## F1 — P1: корректно авторизованный worker report с путями теряется при collect

Статус: подтверждено изолированной воспроизводимой пробой.

Триггер: `command_worker_run_collect()` читает ожидаемый report и передает его как `WorkerExpectedReportCaptured` (`tools/processforge.py:19093-19127`). Для assistant-сообщения `_allowed_conversation_message()` проверяет PF-owned output и hash native id (`tools/pf_runtime/host.py:824-830`), после чего `_worker_session_authorized()` проверяет run/task/attempt, expected path и точное равенство report-файлу (`tools/pf_runtime/host.py:835-860`). Все эти проверки проходят для fixture report с текстом `Source: C:\workspace\src\module.py`.

Нарушенный контракт: разрешенный PF-owned output должен быть принят как один assistant transcript message; сам collector требует это условие (`tools/processforge.py:19127-19130`). После успешной provenance-проверки `_conversation_messages()` все еще применяет общий path safety regex к самому report (`tools/pf_runtime/host.py:923-928`). `_is_safe_automatic_content()` запрещает `C:\...`, `/home/...`, `/tmp/...` даже когда содержимое пришло из проверенного report-файла.

Ожидание: raw receipt принимается, report получает ровно один `chat_message_id`, `worker-run collect` продолжает `task_complete`.  
Факт: raw receipt `accepted=true`, provenance `true`, но `chat_message_ids=[]`, диагностика `unsafe_automatic_content`, а collector на своих строках `19128-19130` возвращает failure. На повторной попытке receipt становится `deduplicated=true`, но `ingest_event()` не завершает работу на duplicate: условие на `tools/pf_runtime/host.py:992-993` возвращает только для `accepted=false`, а затем снова вызывается `_conversation_messages()` на `tools/pf_runtime/host.py:1025-1032`. Поэтому retry повторяет тот же отказ и не восстанавливает потерянный report.

Фрагмент результата пробы:

```json
{
  "provenance_authorized_before_safety": true,
  "first": {"accepted": true, "chat_message_ids": [], "routing_status": "raw_accepted",
             "diagnostics": {"conversation": {"reason": "unsafe_automatic_content", "status": "denied"}}},
  "retry": {"accepted": true, "deduplicated": true, "chat_message_ids": [], "routing_status": "duplicate_raw",
            "diagnostics": {"conversation": {"reason": "unsafe_automatic_content", "status": "denied"}}}
}
```

Impact: reports from normal code audits and diagnostics that mention absolute Windows/POSIX paths are durably raw-accepted but never become transcript messages; `worker-run collect` remains unsuccessful and the unchanged retry cannot repair it.

Минимальная коррекция: после `_worker_session_authorized()` и `_allowed_conversation_message()` применять отдельную PF-owned-output policy для `WorkerExpectedReportCaptured`: разрешить path-like text в report content, сохранив secret scan, exact file equality, expected path, native id/hash и строгую проверку `content_source`. Общий safety check должен остаться для untrusted/provider-derived content и source metadata.

Изолированная remediation task: изменить только `tools/pf_runtime/host.py` и соответствующее regression coverage для worker report capture (при необходимости — `tools/processforge.py` только для проверки collector contract).  
Acceptance: path-containing report capture дает ровно один message; повтор после raw acceptance дает тот же один deterministic message id; wrong provenance, wrong native hash, wrong report bytes и secret-containing report остаются rejected; `worker-run collect` возвращает success только после одного captured message.  
Оценка: M. Рекомендуемая junior-модель: `gpt-5.3-codex-spark` с низким reasoning effort.

## F2 — P1: expected report path может выйти за пределы project root

Статус: подтверждено изолированной воспроизводимой пробой.

Триггер: `normalize_assignment_path()` нормализует разделители и `./`, но не запрещает `..` (`tools/processforge.py:12371-12376`). `expected_report_artifact()` возвращает это значение без containment check (`tools/processforge.py:18404-18410`). Collector затем строит `project_root / expected_report_artifact(task)` и читает файл (`tools/processforge.py:19065-19067`, `19093`). Та же небезопасная композиция используется при authorization report-файла (`tools/pf_runtime/host.py:850-858`).

Нарушенный контракт: expected report — артефакт текущего project/workspace и должен быть создан worker в его project scope. Нормальный `codex_exec_worker` отдельно требует, чтобы output оставался внутри project (`tools/codex_exec_worker.py:159-161`), но collector не защищает тот же boundary для task configuration.

Ожидание: `expected_report: ../outside.md` отклоняется до чтения либо нормализуется в безопасный project-relative путь.  
Факт: fixture с project `.../project`, внешним `.../outside.md` и `expected_report.artifact: ../outside.md` получает `helper_value: ../outside.md`, `resolved_inside_project: false`, а `ingest_event()` принимает внешний текст как assistant report и возвращает один `chat_message_id`.

Фрагмент результата пробы:

```json
{
  "helper_value": "../outside.md",
  "resolved_inside_project": false,
  "outside_file_exists": true,
  "worker_session_authorized": true,
  "capture": {"accepted": true, "chat_message_ids": ["msg_..."], "diagnostics": {}}
}
```

Impact: task configuration can direct collect/host to read and persist a file outside the project as a PF worker transcript. Это обходит ожидаемый project boundary и может раскрыть локальные данные, включая содержимое, которое не является секретом по текущему scanner pattern.

Минимальная коррекция: в одном общем helper для expected report и перед `read_text()` требовать `path.resolve().is_relative_to(project_root.resolve())` (с совместимым fallback для поддерживаемых Python), отклонять absolute/traversal paths и передавать в envelope только canonical project-relative path. Проверить тот же boundary в `_worker_session_authorized()`.

Изолированная remediation task: изменить только `tools/processforge.py`, `tools/pf_runtime/host.py` и regression coverage для expected report path.  
Acceptance: `../outside.md`, абсолютный path и symlink escape не читаются и не попадают в raw/chat payload; нормальный `.pf/artifacts/report.md` проходит; failed path не меняет task на done и не создает assistant message.  
Оценка: M. Рекомендуемая junior-модель: `gpt-5.3-codex-spark` с низким reasoning effort.

## Граница и корректировка прежнего материала

Предыдущий `context-collection-20260910/report-capture/report.md` был неточен в двух местах для этого fixture: provenance не была доказана как прошедшая, а текущая проба показывает `unsafe_automatic_content` после успешной provenance-проверки. Его утверждение, что raw dedup сам по себе останавливает retry, для текущего `ingest_event()` не подтверждается: duplicate receipt остается `accepted=true` и доходит до повторной conversation derivation. Реальная причина невосстановимого report в F1 — повторная deterministic safety-denial того же path-containing content. Raw-ingress duplicate acceptance отдельно не объявляется дефектом.

Другие runtime/service проблемы из основной проверки в этот bounded pass не включались.

## Follow-up: real collector/Core verification

Чтобы исключить ограничение исходной boundary probe, выполнена [probe_real_collector.py](probe_real_collector.py). Она в disposable system temp создает настоящий workplace и project через CLI `workplace-init`, `project-onboard`, `run-create`, `task-create`, записывает настоящий task/status/report, запускает реальный `worker-run collect` как отдельный процесс и читает реальные PF artifacts. Вызовы `required_output_checks`, `RawIngressKernel`, Core task/state loader, chat writer и task completion не подменялись.

Результат F2 подтвержден полным collector path: для task с `expected_report.artifact: ../outside.md` и required output `../outside.md` CLI вернул `DONE: task-fixture`; task стал `done`, а реальный transcript содержит `# Outside fixture` из файла за пределами project root. В evidence это отражено как `expected_report_helper: "../outside.md"`, `collector_report_resolves_inside_project: false` и один assistant transcript message. Следовательно, F2 не является только результатом прямого вызова Host.

Результат F1 также подтвержден реальным collector path: для project-relative `.pf/artifacts/path-report.md` с `C:\\workspace\\src\\module.py` CLI дважды вернул `FAIL: collectible expected report was not captured as exactly one assistant transcript message`; task остался `open`, transcript пуст, а настоящий workplace raw journal содержит `WorkerExpectedReportCaptured` с тем же report body. Это подтверждает raw-first acceptance и последующую `unsafe_automatic_content` потерю. Повтор не восстанавливает report.

Артефакты follow-up: [evidence/real-collector-result.json](evidence/real-collector-result.json) и [evidence/real-collector-stdout.txt](evidence/real-collector-stdout.txt). Повторный запуск probe завершился успешно; временные project/workplace удалены контекстным cleanup.
