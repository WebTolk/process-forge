# T04 review acceptance

Verdict: PASS for source after repairs. Independent source-only report: worker-code-review.md. Deterministic proof remains separately attributed in test-report.md. No unresolved blocking source finding remains.

Resolved: canonical Codex derived actor/payload validation; policy-owned raw ID/scope/stability/version; deterministic rejected-identity receipt namespace preventing forged controls from aliasing or poisoning canonical receipts; replay canonical identity/hash/metadata checks; partial-native denial instead of normalized Runtime fallback; fail-closed default policy and immutable registry; optional callback exception isolation; worker participant bound to launcher/current task owner; canonical turn/delivery/parent metadata. These repairs preserve raw payloads and the unchanged raw kernel rather than weakening provenance checks.

The source design keeps registry construction in trusted Python application code. Native event fields cannot load code or mutate policy. Normalized Runtime remains the existing authenticated transport compatibility path, not proof that the originating provider is independently authenticated. Raw durability and permission to create effects remain separate.

Legacy task-batch compatibility repair is deliberately narrow: unpinned task-batch Run plus exact task membership/assignment path and a real declared per-task process. Governed pinned process identity stays strict. The old fixture's nonexistent prompt-only process was replaced by an explicit local definition; no missing-pin fallback was added.
