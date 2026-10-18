# R04 task iteration log

Removed all six tracked `dist/` ZIP/manifest files. GitHub releases remain the
public distribution channel; `release-pack` generates an archive on demand.

`apply_update()` now writes Core files and the Core manifest before a planned
Workplace migration. Its pending-operation journal uses the same order. A
post-Core Workplace failure leaves the target Core manifest installed and the
in-progress state is `manual_repair_required`, avoiding a false safe rollback.

Project `.pf` migration remains an explicit per-project assessment and governed
work after Core and Workplace validation. Independent concurrent Core/Workplace
apply is unsupported. Focused core-update smokes, schema validation, checksum
inventory and diff check pass.