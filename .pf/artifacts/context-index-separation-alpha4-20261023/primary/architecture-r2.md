# Architecture revision 2: one indexing component, explicit triggers

Operator clarification, 2026-10-23: use the separation exemplified by Joomla Smart
Search: explicit manual indexing and periodic indexing through the future PF
scheduler. The CLI indexing invocation must call the same component.

This is a design revision. architecture.md and all existing capsules remain
immutable. No product files have been changed. The previously proposed immediate
Runtime search thread is withdrawn from alpha4; a future general PF scheduler is
outside this release. Its absence does not trigger indexing from a project.

The single canonical WorkplaceIndexMaintenanceService remains the owner of index
execution, serialization, durable progress/result, crash recovery and retry. Both
the explicit search-index-maintain CLI adapter and a future scheduler job call this
same service. Neither gets an independent index algorithm or source catalogue.
The existing resource-oriented SQLite/FTS5 engine and catalogue are reused.

Project initialization/refresh/repair and project context/search only observe the
existing index. They do not build, queue or wait. Current project/Work access filters
and required context-resource checks remain strict, separate from derived search
availability. Missing/stale/incomplete index is reported with an instruction to
request explicitly authorized workplace maintenance. File-only remains usable.

Revised native composition: primary Main integration and delivery; contributor 1
read-only observation/access; contributor 2 canonical maintenance plus manual CLI;
contributor 3 the cold callable job contract for the future scheduler, with no
Runtime service.py changes, no loop, timer, autostart or live jobs; contributor 4
integration/negative/performance-fixture tests and EN/RU docs after implementation.
One independent reviewer checks all code after implementation. Existing frozen
interfaces for observation/maintenance stay unchanged. Admit contributor 3 through
a scoped successor with this revision pinned, preserving its failed native attempt.

Acceptance mapping: original criterion 3 and periodic-launch parts of criterion 8
are superseded by the user's explicit future-scheduler boundary. Alpha4 must prove
manual CLI invokes the shared service; its cold job callable invokes that same
service when explicitly called in fixtures. Actual periodic scheduling remains a
future task. All other original criteria remain applicable. No live infrastructure,
update, reconnect, actual workplace indexing or paused OOP work is authorized.

Qualification must distinguish fixture/native source/archive proof from actual
installed-device or connected-host acceptance. No alpha4 publication is permitted
until native 1-1-4 implementation, independent review and required QA are complete.
