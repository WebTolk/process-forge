# Windows PID observation correction

The sequential repeat also failed with `pid_probe_unknown`. This is a concrete
availability defect in the prior monitor: spawning tasklist can exceed its
0.75-second deadline even on an otherwise functioning machine. It is not proof
that the Runtime or loopback endpoint failed. Original failures are retained.

Within the declared monitor/test scope, Windows now opens a process handle with
SYNCHRONIZE only and calls WaitForSingleObject with zero timeout, then always
closes the handle. Signaled means exited; timeout means currently alive. Failed
checks and access denial remain unknown; invalid PID is false. No full process
list, subprocess fallback, relaxed network budget or lifecycle mutation.

Local precedent inspected: Core `_registry_lock_owner_alive` uses typed ctypes
Win32 process handles. API behavior additionally verified against primary docs:
https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-openprocess

Regression adds actual current/exited process checks and independent Windows
handle results for alive/exited/failed/access-denied/invalid-PID/close behavior.
The original terminal/HTTP/no-write suite is rerun unchanged except these added
PID assertions. Implementation evidence remains immutable and historical.
