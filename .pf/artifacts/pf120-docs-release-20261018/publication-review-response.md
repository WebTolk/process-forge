# Publication preparation review response

The original independent FINDINGS remain unchanged in
`.pf/artifacts/pf120-publication-review-20261018/report.md`.
This is the primary response and verification, not a rewritten independent PASS.

1. Mandatory release conditions use explicit `require` calls and remain active
under `python -O` and `-OO`. Native product smokes execute with optimize=0 and no
PYTHONOPTIMIZE. Seven gate helpers contain no optional assert statements.
2. All 1,318 retained consumer release files match both the frozen canonical ZIP
and sidecar during the running complete profile. Frozen hashes were observed from
the canonical build before profile execution. A separate after-completion payload
and final-log hash observation is mandatory for qualification. The record explicitly
does not pretend that a new pre-start observation was performed retroactively.
3. Source publication and stable preparation validate both exact files against
accepted qualification, then validate sidecar source/tree/clean eligibility and ZIP
hash/size. Identity-file changes cannot substitute new asset bytes by themselves.

Twelve positive/negative guard cases passed under optimized Python, including
identity drift, replaced ZIP/sidecar bytes, and inconsistent source/tree/eligibility.
See `publication-guards.json`. Private scripts and test fixtures only; no product,
remote, release or device mutation. The exact product source and archive are unchanged.

GitVerse mutation helpers additionally require accepted qualification, draft creation,
qualified asset uploads and a verified two-draft asset receipt before publishing.
The final orchestrator must still perform actual remote/asset readbacks. Previous
client evidence claims only isolated Core/fixture byte preservation and no device
update invocation, rather than a machine-wide unchanged-state assertion.

Full package profile and publication are still pending at this response. Review
Work completed as delivery of findings only.
