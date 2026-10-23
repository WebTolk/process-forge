# Fresh assurance for r20

Exact source-candidate-r20.json: 45 owned files, seven-file delta from pushed
23ae1661. Full fresh pytest: `732 passed, 7 skipped, 246 subtests passed in 358.83s (0:05:58)`. All 15 affected native checks, four
corrected Garage smokes and seven actual batch CLI invocations passed on r20.
All original smoke if/assert predicates are retained: 31 before, 37 after.
The four native smokes exercise real CLI/MCP stdio, session/authorization/page
boundaries and Work start before maintenance, then the original empty-corpus case.

Seven new regression cases cover maintained empty status, removal of all registered
resources and refusal of schema-only/stale/inconsistent empty metadata. Two real
red cases preceded the bounded Core fix; all 60 regression cases now pass. No
reader writes/indexes or weakens mandatory context/authorization. Retain the
rejected full source r1 (165 passes before one failure), the remaining-check
diagnostic (104 pass, three failures) and the r19 user-like failure. These were
never accepted as full release qualification.

6 SQLite ResourceWarning records are retained, not suppressed or claimed
fixed. Seven environment skips remain. Nine-new-module coverage: statements
95.28%, branches 91.03%; not whole repo.
All earlier rejected/reviewed trees remain unchanged. Fresh native source and
exact archive full unfiltered profiles remain required after supplemental CODE GO.
No installed, actual connected-host or native POSIX acceptance is claimed.
