# Public-cleanliness false-positive audit

Status: corrective validator work required; do not remove the tested data.

## Current failures

| File | Finding | Classification | Assessment |
| --- | --- | --- | --- |
| `.pf/AGENTS.md` | literal `scratch` | documentation term | The public rule tells workers not to create repository-root scratch directories. It is not private data. |
| `tools/smoke_central_event_replay.py` | literal `scratch` | source-code literal | `scratch_root` is a local variable for `.pf/tmp` test cleanup, not a leak. |
| `tools/smoke_conversation_completeness.py` | `C:\\Users\\private` | security fixture | The smoke proves unsafe automatic content remains raw-only and is not copied into project-visible conversation/event material. |
| `tools/smoke_worker_run_shell.py` | `[A-Za-z]:\\` | regex false positive | The literal `encoding='utf-8'` contains the text sequence `T:\\` across the source literal boundary; it is not a Windows path. |

## Required correction principles

1. Replace broad marker matching with category-aware checks. A word such as `scratch` is neither a path nor a secret.
2. Detect an actual drive-qualified path, not any letter followed by a backslash inside source text.
3. Keep narrow, auditable fixture acknowledgement for intentional unsafe-path values used by security tests. It must not allow a real release document or runtime value to bypass detection.
4. Add regression coverage for both the acknowledged fixtures and an actual private absolute path that must still fail.

No production variable or security fixture should be renamed merely to make a weak validator pass.
