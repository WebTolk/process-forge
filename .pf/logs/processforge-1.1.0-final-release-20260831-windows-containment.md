# Журнал Windows containment fix

## 2026-08-31T08:44:00+04:00 — codex-main / developer

- Область: raw-ingress path containment и long-lived Runtime smoke.
- Evidence: один parallel SessionStart вернул HTTP 400 с extended-path false
  escape; 11 соседних запросов — 200; три немедленных повтора smoke — PASS.
- Исправление: canonical Win32 spelling перед `relative_to` containment check.
- Следующий шаг: checksum refresh, clean exact-tag full suite, archive suite.
