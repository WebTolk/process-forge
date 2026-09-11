# R03 summary

A disposable synchronized two-process probe confirmed that two stale
`copy_if_missing` migration plans can both apply and one archive payload
silently overwrites the other at the shared Workplace target. No installed Core
or source file was changed.

The product currently has no stated supported concurrent-apply contract and no
interprocess serialization, so this run records a confirmed race mechanism and
an unsupported-concurrency limitation. A separate design/remediation task must
choose a Workplace-scoped lock or apply-time idempotence rechecks before making
concurrent apply a supported path.