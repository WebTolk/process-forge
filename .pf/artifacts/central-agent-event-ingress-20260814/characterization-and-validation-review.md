# characterization-and-validation-review

Дата: `2026-08-14`
Задача: `central-ingress-characterization-review-20260814`
Итог: `CONDITIONAL PASS`
Режим: planning-only, без изменений кода.

## Вывод

`characterization-and-validation-plan.md` в целом покрывает текущий observable baseline и обязательные требования первого slice Central Agent Event Ingress. Implementation можно начинать после фиксации нескольких условий ниже как обязательных gates, а не как пожеланий.

План корректно отделяет целевую raw-first архитектуру от текущего normalized-first пути: сейчас `codex_hooks.py` сначала строит normalized event (`tools/pf_runtime/codex_hooks.py:46-70`), затем отправляет его в Runtime `/event` или fallback `host.ingest_event()` (`tools/pf_runtime/codex_hooks.py:73-107`). В `host.ingest_event()` project/session checks выполняются до `normalize_event()`, Ledger и project journal append (`tools/pf_runtime/host.py:569-599`). Это нужно сохранить именно как pre-change characterization baseline, а raw accepted + route rejected считать post-implementation expectation.

## Coverage Review

| Область | Статус | Ревью |
|---|---:|---|
| Raw-first ordering | `PASS` | План явно требует durable raw append до normalization/routing и тест crash-after-raw. Это соответствует master prompt sections 7, 40, 53. |
| Текущие Codex semantics | `PASS WITH ADDITION` | План покрывает `SessionStart/startup|resume|compact`, `SessionEnd`, `PostToolUse Bash`, `PostToolUse non-Bash`. Это совпадает с `EVENTS` и special-case non-Bash (`tools/pf_runtime/codex_hooks.py:21-24,46-70`). Нужно добавить baseline case: `SessionStart` с неизвестным `source` сейчас `ignored`, потому что для `SessionStart` нет `default`. |
| Unsupported / unknown hooks | `PASS` | План верно фиксирует current `status=ignored` и future raw accepted + no false PF normalization (`tools/pf_runtime/codex_hooks.py:73-76`). |
| Native-identity conflict index | `CONDITIONAL PASS` | План уже требует conflict index без `raw_payload_hash`; это обязательно. Без отдельного native-identity key poisoned duplicate с тем же provider id и другим payload получит другой `raw_event_id` и пройдет как новый факт. Условие из `idempotency-and-replay-review.md` должно стать implementation blocker. |
| Deterministic derived ids | `PASS` | План и idempotency contract сохраняют legacy Codex normalized id path: `codex:{hook}:...` -> `evt_<sha256(...)[:32]>`, что совпадает с `stable_event_id()` (`tools/pf_runtime/host.py:364-370`). |
| Runtime/fallback equivalence | `PASS` | План правильно требует один Core ingress для Runtime и direct fallback. Текущий split подтвержден в adapter dispatch (`tools/pf_runtime/codex_hooks.py:87-107`). |
| Cross-project / mismatch | `PASS` | Current baseline: mismatch raises `PermissionError` before event append (`tools/pf_runtime/host.py:581-587`). Future expectation raw accepted + derived route blocked is correctly described. |
| Crash/replay | `PASS` | Replay smoke, missing-only repair, checkpoint interruption and changed normalizer version covered. Atomic checkpoint/index write must remain a gate. |
| Interprocess concurrency | `CONDITIONAL PASS` | План требует interprocess locking and atomic append. Это важно: current lock is only `threading.RLock` inside one process (`tools/pf_runtime/host.py:23-31`), and current project journal append is ordinary file append with pre-read dedupe (`tools/processforge.py:10422-10440`). |
| Chat/manual compatibility | `PASS` | Plan preserves transcript layout, `msg_<uuid>`, metadata-only default and private `chat.message.recorded`; this matches `append_chat_message()` (`tools/processforge.py:10525-10598`). Automatic capture is correctly limited to provider events with real content. |
| Auth/security | `PASS BY PLAN` | Plan covers bearer auth, malformed/oversized, forged project root, path escape, operator diagnostics. Runtime service code was outside this worker’s allowed read scope, so `/event` auth itself is accepted via the supplied inventory review, not reverified here. |
| Release/privacy | `PASS WITH ADDITION` | Plan correctly separates `events-validate` structural validation from schema validation (`tools/processforge.py:19537-19565`, release steps `tools/processforge.py:6561-6563,6703-6706`). Add an explicit fixture/archive assertion that generated raw/blobs/transcripts/checkpoints/errors are absent from release archives. |

## Required Corrections Before Implementation

1. Add a characterization case for `SessionStart` with unknown `source`: current result must be `ignored`; after implementation it should be raw-only/unsupported mapping unless a real semantic mapping is defined.

2. Keep pre-change and post-change expectations separated in test names. Current mismatch and unknown-session behavior rejects before any raw record exists; future behavior accepts raw and blocks/defer routes.

3. Treat the native-identity conflict index without `raw_payload_hash` as mandatory acceptance, not optional design detail.

4. Clarify raw fidelity wording. If “byte-for-byte” means original transport bytes, store/test an original payload byte hash or source representation. Canonical JSON with sorted keys/NFC is deterministic, but it is not byte-identical to arbitrary inbound JSON text.

5. Make release/privacy validation construct private runtime raw/chat/error fixtures and inspect the built archive, not only run generic cleanliness checks.

## Decision

`CONDITIONAL PASS`: the plan is strong enough for first-slice implementation after the five corrections above are folded into the implementation checklist or tracked as blocking acceptance gates. No code changes or tests were run in this review.
