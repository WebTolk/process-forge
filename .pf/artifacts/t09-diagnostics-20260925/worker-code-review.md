# T09 bounded code review

Verdict: **pass_with_conditions**. Mandatory journal sequencing, optional logger failure containment, and protocol stdout paths inspected are consistent with the accepted architecture. Primary reports the focused diagnostics smoke and journal/privacy checks passed; this review did not run tests.

## Acceptance gaps

1. **Medium — private prompt/environment field aliases pass through.** `src/processforge_core/diagnostics.py:30,165-176` only omits exact key names. An emitted context such as `{"prompt_text":"..."}` or `{"environment_variables":"..."}` is recursively serialized as-is because those names do not match `OMIT_KEY`; the same cleaner is used by export (`:555-557`). This conflicts with scope's bounded safe-context/redaction requirement and the EN runbook claim that prompts/environment data are omitted (`docs/concepts/diagnostics.md:62`). Repro: emit either context key and inspect canonical JSONL/bundle. Extend omission matching to the documented field families and cover local+export paths.

2. **Low/Medium — export can retain expired records beyond configured retention.** `JsonlSink.__call__` removes files older than `retention_seconds` only on a subsequent write (`src/processforge_core/diagnostics.py:253-268`). `export_bundle` iterates all known files and includes records by requested time interval, with no retention cutoff (`:571-590`); therefore after an idle period, an expired file remains exportable indefinitely until another record is written. This weakens the promised bounded retention. Repro: create a record, age its file beyond configured retention, perform no later writes, then export without `--since`; record is included. Filter expired records at export or define and document an explicit retention cleanup boundary.

## Resolved during review

The initially observed `PF_CODEX_HOOK_DEBUG=1` direct stderr logger bypassed project locks. Primary changed `tools/pf_runtime/codex_hooks.py:191-202` to pass the temporary profile as an invocation override through project configuration, with locked-policy fallback through `for_stderr`; primary reports a locked-sink regression check is being added. No remaining hook finding from the current snapshot.

Scope was limited to the accepted T09 architecture/implementation, diagnostics core, and focused CLI/MCP/Runtime/worker/hook integrations. No source edits, tests, transitions, or installation were performed by this reviewer. Broader Runtime startup failure is outside this bounded review and remains separately investigated.
