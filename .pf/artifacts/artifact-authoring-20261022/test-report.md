# Final test report

2026-10-22. PASS on the final clean public snapshot of
a88607af49dbde56fb6672f6ad658a184dec3381 plus exactly five owned public
source/docs overrides. Raw and LF SHA-256 for eleven source/docs/test files are
recorded in qualification-inputs.json; snapshot/current owned bytes match.
Unrelated dirty facade/resources/architecture work was excluded.

Final results, all exit 0:
- 104 pytest cases: new authoring suite plus the existing evidence-guidance suite.
- Eight existing smoke scripts: current stage, missing gate, linear transition,
  evidence recording, invalid-evidence recovery, pinned process, identity/file
  freshness, and Windows UTF-8 documentation.
- Registered Ruff lint/format and scoped mypy all passed.

Real source CLI JSON and ordinary stdio MCP agree on authoring review after a
successful transition. Invalid UTF-8 remains advisory, file bytes/history stay
unchanged, a later file edit retains its stored observation while authoritative
freshness fails, valid resubmission recovers and the fixture reaches run_completed.
Source normalizer/matcher tests verify unchanged structural N/A/path/status rules.
Stream-byte, reference, findings and adversarial parser cases verify bounded work.

Execution: registered qa.py test -- -q tests/artifact_authoring
tests/evidence_guidance with task-local pytest cache/basetemp; existing smoke
scripts execute under the same project interpreter in the clean source root.
Exact local invocation vectors and raw output are retained in the task's
verify_clean.py and clean-verification.json / clean-*.log. Earlier pre-refinement
proof is retained separately as pre-bounds-verification.json. Final counts above
refer only to the corrected final candidate.

Limits: primary self-review, no independent-agent review permitted by capsule.
Source/independent stdio proof only; no ZIP, installed Core, actual connected-host,
browser, Runtime/app-server restart or token-accounting implementation.
