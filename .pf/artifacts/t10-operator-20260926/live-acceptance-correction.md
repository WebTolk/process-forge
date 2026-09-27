# Installed acceptance correction

The official update core-update-20260926T190618Z succeeded: candidate a5eeac53,
1001 installed hashes and 13 backup hashes verified, Runtime restarted with
instance 5b7f3b87010e4571992c5c91abcf8296 (observed PID 15900). Do not reapply the
original install.py. Its final metrics assertion failed; earlier successful
source/manual publisher tests did not prove actual scheduler independence.

Real service.json remained at its startup state while the scheduler was still
routing/replaying projects. The observer was published only at the end of that
pass. Bounded per-record collection alone did not bound publication latency.
The installed payload itself is intact; this is an acceptance defect, not an
updater failure, and no manual installed edit or process hot reload is allowed.

Bounded delivery correction within the declared file scope: move metrics to a
separate read-only observation thread in the same Runtime. Core reads a bounded
registration cache and validates roots without rebuilding project context;
partial registrations remain unknown. Runtime independently publishes through
the same state lock and atomic service.json. Ordinary scheduler/request stop
admission remains unchanged. New regression holds ordinary routing blocked
while the real observer thread must publish the new instance's snapshot.

Architecture correction, implementation, focused reassessment, new clean
candidate/archive and second official updater transaction are tracked in
../t10-operator-runtime-fix-20260926/. Current Work remains at release-delivery;
original approved artifacts and failed observations stay unchanged. Release
and evolve completion wait for successful installed acceptance of this correction.
