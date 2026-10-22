# Governed file-only executor handoff

The native task-create surface grants workplace resources but cannot bind a new
task to the process_execution capsule pin in an existing governed Run. Preparation
therefore refuses work_context_mismatch. No immutable capsule is patched.
The input-only tasks are cancelled and all failed attempts remain preserved.

Use four separate native pf.work.start contributions with disjoint scopes and
frozen source files. Primary advances their PF stages with the accepted design
and owns all Ledger/chat coordination and all external registered QA execution.
This supersedes the earlier architecture's per-worker external QA/coordination
duties only. Product architecture, behavior, interfaces and ownership stay as
written. An executor writes its implementation, meaningful pytest tests and report.
It can perform local standard-library checks with its own scratch paths; it must
not open any external workplace root, invoke external QA tools, run Git, or mutate
PF lifecycle/infrastructure. The primary runs registered pytest, Ruff, mypy,
coverage/security and integrated/archive gates over the actual contributions.

The required local python-source-excerpts.md contains actual sections exported
from the primary's PF-resolved authorized knowledge resources. Read it along with
the frozen guidance/architecture/contract before READ_ACK and implementation.
The provenance JSON records resource IDs, source paths, spans and original hashes.
These files are in the declared read scope; no external knowledge grant is needed
for the executor. The primary has verified the source bytes and owns final QA.

Emit READ_ACK as an actual progress message after reading these materials; native
ingress records the real attempt. Emit RESULT with exact changed paths, interface,
tests and limitations. No self-registration or PF lifecycle changes. Primary
forwards truthful message references through PF chat and collects the report.
Do not claim tool results that the primary has yet to run. Complete the contribution
without claiming the parent result or alpha3 release complete.
