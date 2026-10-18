# R04 intake: release archive removal and sequential update policy

User decision: GitHub releases are the public distribution channel; remove all
tracked historical `dist/` ZIP archives and manifests. Core update ordering is
Core first, Workplace second, and project migration only within each project
work process. Concurrent independent Workplace migrations are unsupported.

Scope: tracked `dist/` artifacts, core-update execution ordering, focused
regression coverage, and English/Russian update documentation. No installed
Core update or publication is permitted.

Acceptance: `dist/` is absent from Git; Core manifest is written before any
Workplace migration; migration failure after Core update is recorded as a
manual-repair state; docs state the serial model and project boundary.