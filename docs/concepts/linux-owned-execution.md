# Linux owned execution

Linux native workers use an owned user/PID namespace rather than treating a
process group as the complete descendant tree. Windows continues to use retained,
non-breakaway Job objects. SQLite alone does not enable either backend.

The Linux adapter launches a small carrier from captured trusted source. It
creates a user namespace, maps the caller UID/GID, and forks namespace-init as PID
1 in a new PID namespace. Init starts the target and reaps orphaned descendants.
When the target root exits, init waits for the remaining descendants, including
children that call `setsid()` or change their process group. When init dies, the
kernel tears down the namespace and kills its remaining descendants.

Init installs a parent-death signal against carrier death, checking an inherited
carrier pidfd to close the fork/prctl race. Normal exit or death of the PF CLI
after a committed detached launch leaves the carrier observable and permits
subsequent status/stop/collection by exact identity. Killing the carrier tears
down its namespace. This is a per-attempt child helper, not a Runtime daemon.

Before target code can execute, the caller validates carrier/init birth and
namespace facts and publishes the native ownership receipt, when requested.
The helper releases its target only after the caller sends GO. EOF or failure
before that barrier cannot run the target. The existing SQL path still commits
its reservation before spawn and keeps spawn/signal/wait outside SQL transactions.

The carrier starts with a fixed interpreter environment. Target loader settings,
including `LD_PRELOAD`, travel over its private socket and take effect only for
the target inside the committed namespace. They cannot run target code in the
carrier before containment or receipt publication.

Process receipts name the PID visible in the controller procfs. Namespace PID 1
or the target local PID must not be substituted for that PID. The private Linux
tree identifier binds the launch token, namespace-init PID/start ticks, and PID
and user namespace identities. Reopen retains pidfds first, then checks boot/birth,
namespace membership and the launch token on the actual processes. Stop signals
only the retained init pidfd. PID reuse, a foreign owner, malformed facts or
unreadable observations never authorize signalling a replacement process.

Private lifecycle lock owners also record the PID visible in their shared procfs,
with boot/start identity and procfs view. Recovery distinguishes that identity
from a namespace-local PID or a reused PID. A foreign or unreadable view stays
unknown. The persistent OS guard and existing caller-selected stale-age policy
still govern owner-marker recovery; Windows and legacy owner records keep their
existing behavior.

An exit receipt describes the root result; it does not by itself retire the
attempt. The SQL state remains non-idle until the owned carrier/namespace are
proven absent. Missing or inaccessible evidence stays unknown. Legacy
`linux-pgid` receipts retain their conservative behavior and are not upgraded to
whole-tree proof from a missing PID or process group.

Fresh SQL observation also reads the attempt-bound native receipt before a
wrapper process receipt exists. It verifies the launch token, attempt identity
and native birth facts before reopening ownership. A successful stop waits for
positive whole-tree absence; unavailable or conflicting evidence returns a
bounded refusal and keeps the attempt current.
The controller persists stop intent before admitting a newly published root
exit. A root exit can change the execution projection to unresolved, but cannot
cancel that intent; ordinary status can resume the stop after a controller crash.
Control decisions retain exact attempt/token identity and accept platform-native
LF or CRLF line endings without weakening the identity comparison.

Detached starts enforce their configured deadline on subsequent status, stop or
collection observation. The pre-GO receipt publication time supplies the launch
boundary even when the target loader stalls before its first wrapper receipt.
A private timeout decision survives a failed stop or controller restart. Only
after confirmed tree absence does the controller record `timed_out`, preserving
an available root exit code or using controller timeout code 124. This controller
result does not claim a missing root receipt or overwrite a wrapper receipt file.
Detached file-only execution has no autonomous timer between observations.

## Prerequisites and limits

Use Linux with user/PID namespace creation enabled, readable procfs mounted for
the controller PID namespace, and Python 3.11+ with pidfd APIs. Seccomp, AppArmor,
container policy or unavailable kernel features can refuse a launch. The real
capability probe returns false on refusal; it never silently advertises groups
as equivalent containment. The platform error retains the existing
`execution_activity_unknown` code and records a Linux refusal reason such as
`linux_user_pid_namespace_unavailable`, `linux_pidfd_unavailable` or
`linux_controller_procfs_mismatch`.

Ordinary nested targets inherit their verified outer namespace. Starting an
independent token/receipt-owned attempt from inside that namespace is refused as
`linux_nested_owned_launch_unsupported`; run its controller in the supported
host procfs context. Namespace containment is a process-lifetime guarantee,
not a filesystem/network sandbox or a substitute for current PF grants. It does
not isolate hostile processes with the same host authority from one another.

The maintained native tests cover real namespace lifetime, escaped descendants,
controller/carrier death, reopen, interrupted pre-GO publication, kernel-denied
namespace creation and foreign/unreadable identity refusal. The fresh SQL and
collection-cycle tests execute the same native lifecycle on Windows and Linux.
Required native scenarios must run; a skipped or unsupported scenario is not a
qualification pass. Source, installed archive, Runtime and actual-host release
acceptance remain separate delivery layers.
