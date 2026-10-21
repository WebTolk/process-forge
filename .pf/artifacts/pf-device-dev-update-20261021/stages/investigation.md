# Read-only investigation

Native installed Core status: installed 1.2.0, 1458 managed files, no incomplete
update. Existing Runtime owner PID 9848 is alive, lifecycle/readiness/health ready.
Its instance label is 1.0.0-poc; that label is not the installed Core version.
Installed monitor CLI currently reports 1.2.0.

Accepted local HEAD and live origin/dev both equal
cc690b263b65daaa0e85a21186de89944b1064a9. Compared with the previous clean
qualification commit 99f19b0c32776cd2452f5698b5748751c6587dba, all differences
are under project .pf bookkeeping; shipped public source is unchanged. Reuse the
completed full source qualification: PF 274/274, public 3/3, stress 6/6,
pytest 142 plus 42 subtests and one Windows privilege skip, Ruff and scoped mypy.

Native contracts confirm core-update status/plan/apply, manifest-backed backup,
Workplace migration with --workplace-root, explicit --confirm, and the separate
--force-local-modifications option. Monitor supports JSON, once and interactive
views; noninteractive terminals produce one snapshot. Native server restart has
a protected busy guard; --force explicitly bypasses it and is not the default.

Unknowns to resolve before dependent actions: exact target archive manifest and
local customization conflicts from native plan; post-apply Runtime reload safety;
visible interactive console and actual installed monitor output.
Handoff: model these separate evidence/ownership layers, then execute a bounded
package-plan-backup-apply-verify-monitor operation using the native services.
