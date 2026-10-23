# Trigger policy clarification for the revised component

The user's Joomla Smart Search analogy establishes explicit demand-driven manual
indexing and later periodic invocation by the future PF scheduler. The same
canonical indexing component is invoked by CLI and by a scheduler callback.

Before implementation, characterize every existing trigger, including workplace
initialization, knowledge/template/tool/platform changes and update/rollback.
Registering or changing a resource may mark derived state dirty; it must not hide
an unrequested full index build behind a project refresh or query. Shared source
changes and pending reconciliation stay observable until explicitly serviced.
Any existing explicit indexing command remains a manual trigger, and must use the
same component with its existing authorized scope and output/error mapping.

Do not confuse the DB driver extension boundary with the search backend boundary.
The original baseline supports SQLite FTS5 only. storage-decision-r3.md describes
the concrete alpha4 choice and future extension constraints. The future scheduler,
multi-backend DAL, actual vector adapter and RAG are not implemented by this design.

This document supplements architecture-r2.md and storage-decision-r3.md and must
be pinned by the governed implementation successor. None of R1, its capsules or
the original task's at-admission bytes is modified. A clear contract mapping and
meaningful tests are required for intentional trigger changes before release.
