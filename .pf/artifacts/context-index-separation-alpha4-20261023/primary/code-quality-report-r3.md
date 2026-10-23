# Final alpha4 code quality

Registered Ruff lint/format passed all 30 owned Python modules/tests/smokes in
the final r13 tree. Four actual Main-owned functions passed extraction checks;
their ASTs match the candidate. Legacy Main/composition are not claimed fully
linted: the clean-HEAD projection and canonical-import/composition tests bind
their precise change. Unrelated Main/OOP bytes remain preserved in the root.

Strict mypy passed 14 production modules with follow-imports=silent and
ignore-missing-imports bounding legacy traversal; those production bytes are
identical in r13. Bandit passed ten explicit modules, 1596 LOC, zero findings,
zero nosec or disabled-check skips. No dependency was added and no external QA
environment audit is presented as product dependency proof.

Applied actual PF Python/Protocol/dataclass/pathlib/PEP8/257/OOP sources: cold
composition and per-invocation dependencies, one canonical maintenance owner,
a real narrow existing-backend Protocol, separate project/workplace scope,
OS-owned bounded writer locks, durable atomic state/notifications and explicit
connection/file ownership. Native authoring remains the per-item transaction
owner; the batch layer sequences it and calls one final selected operation.

Independent notifications cannot overwrite one another. Selected acknowledgement
requires all captured changes to be known and covered, no old failure and no
concurrent token. Exact captured files retire while the durable guard is still
running; failed token publication remains visible by notification names. SQLite
catalogue projection reads only stored metadata and keeps the prior full-pass
timestamp. Private metadata hashes are removed from public query payloads.

The local schema correction permits exactly one bundled indexing schema and its
internal definitions; arbitrary external URLs/paths remain refused. No new DB
backend, DAL, scheduler loop, Runtime job or infrastructure operation was added.
Actual native contribution/acknowledgement/failure evidence is retained separately.
Fresh independent native review is required before source delivery/publication.
