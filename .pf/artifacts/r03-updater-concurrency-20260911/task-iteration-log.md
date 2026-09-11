# R03 task iteration log

Static contract: `workplace_migration_plan()` determines `copy_if_missing` and
registry operations from the observed Workplace state. `apply_workplace_migration()`
uses those operations without a second existence/uniqueness check. `apply_update()`
has no interprocess migration lock.

Fixture reproduction: `.pf/tmp/r03-workplace-migration-race/reproduce.py` created
two separate archives A and B and one disposable Workplace. Both plans observed
an absent `runtime-drivers/shared.yaml` and each contained one operation. Two
spawned processes were synchronized immediately before their target writes.
Both returned `applied`; the final target contained only `driver: A` (the winner
is scheduling-dependent). This proves that stale concurrent plans can overwrite
a competing `copy_if_missing` payload.

Classification: a real TOCTOU behavior exists, but no source/docs contract was
found that declares simultaneous independent Core applies supported. Therefore
it is an unsupported-concurrency design limitation, not a confirmed regression
against a supported guarantee. No installed Core or product source was touched.