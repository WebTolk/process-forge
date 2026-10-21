# Bounded operator implementation plan

Create a clean detached worktree under owned task-private storage at accepted
dev commit cc690b263b65daaa0e85a21186de89944b1064a9. Build one private dev archive
through its existing release-pack command. Record archive SHA-256 and source
provenance; do not publish a tag/channel or perform a broad ZIP audit.

Use the existing installed updater to plan against the actual Core and Workplace.
Read the plan and migration scope. If local managed-file modifications exist,
inspect and back up their exact preimages before deciding on the native supported
preservation/override route; do not blindly force. One --confirm apply is authorized
by the current user request. Retain native journal and backup evidence, then
verify all managed hashes, no incomplete update and doctor-workplace.

Observe the existing Runtime through native status, use a safe canonical restart
if needed for the newly installed build, and verify PID/start/provenance/readiness.
Launch the installed monitor in a visible console with real terminal input/output
and UTF-8. Verify actual uptime fields in that view and separately capture its
allowlisted JSON/plain once observations. Keep the current host MCP untouched.

Assurance reuses unchanged source test/style receipts and adds native packaging,
plan/apply, installed integrity/doctor, Runtime and monitor evidence. There is no
new executable project code requiring another source QA cycle. Handoff: perform
these operator actions in order, recording real outcomes and stopping any dependent
action at an actual native blocker. Finish native lifecycle and artifact delivery.
