# R03 task result

Investigation complete. A synchronized disposable two-process fixture reproduced
a stale-plan overwrite: both migration apply calls reported `applied`, while the
single shared `copy_if_missing` target retained one competing archive payload.

This is a confirmed race mechanism. It is not classified as a shipped
regression because ProcessForge currently documents no supported concurrent
independent Core-update apply contract and provides no lock/serialization API.

Recommended separate design decision: either explicitly serialize Core update
and Workplace migration applies with a Workplace-scoped interprocess lock, or
state that concurrent applies are unsupported and add apply-time idempotence
rechecks. No production change is made under R03.