from work import *

build=json.loads((HERE/'build.json').read_text())
install=json.loads((HERE/'install.json').read_text())
assert build.get('finished_at') and install.get('finished_at')
assert install['apply']['status']=='applied' and install['preservation']=='PASS'
assert install['egress_qualification']['status']=='passed' and install['egress_qualification']['checks']==53
assert all(sha(ROOT/n)==h for n,h in build['source_sha256'].items())
assert all(sha(Path(n))==h for n,h in build['protected_sha256'].items())
assert all(sha(Path(n))==h for n,h in build['frozen_sha256'].items())
manifest=json.loads((CORE/'processforge-core.manifest.json').read_text())
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in manifest['files'])
patch=command('delivery-patch',['git','diff','347c6d9e9ec36044c77540bb601477173a68db41',build['candidate_commit'],'--'],cwd=ROOT/'.pf/tmp/t07-engine-20260926/final/candidate')
(HERE/'candidate.patch').write_text(patch,encoding='utf-8')
report=f'''# T07 delivered through the standard updater

User-authorized installed Core update and T07 engine implementation are complete.
Final candidate: {build['candidate_commit']}. Main source HEAD remains
{build['main_head']}; unrelated dirty work was preserved.

Archive: {build['archive']}
SHA256: {build['archive_sha256']}
Update: {install['apply']['update_id']}
Automatic backup: {install['apply']['backup_dir']}
Verified installed manifest-owned files: {install['installed_hashes_verified']}.
Verified automatic backed-up prior files: {install['backup_hashes_verified']}.
Plan counts: {json.dumps(build['plan_counts'])}.

Official release-pack/archive-test quick and final candidate/extracted feature
checks passed. Exact final source had 14 required assurance commands plus the
six-command final Work/tool permission correction reassessment. All 53 T07
checks passed again in the installed egress qualify command, including actual
governed CLI, independent HTTP/TLS captures, source/junction swap, process crash,
mandatory audit failure, scope/Work effect denial and prior v1 compatibility.

Runtime was inspected as the owned idle process, stopped normally, updated only
with core-update plan/apply/status and restarted with its existing configuration.
New Runtime instance: {install['new_instance']}; PID at acceptance: {install['new_pid']}.
Runtime and Workplace doctors, T10 live compact metrics/monitor, operator guards
and concurrent journal regression passed. Existing partial activity groups and
unrelated registration warnings remain explicit. No forced stop/update, manual
payload copy or Workplace/project migration occurred. Config, unowned files,
frozen prior evidence, current capsule and source hashes were preserved.

Installed qualification store: {install['egress_store']}
Qualification implementation: {install['egress_qualification']['implementation']}
The store is outside the project, owner-only, excluded from general Work material.

Behavior: explicit v2 security intent; finite trusted classification and optional
whole-unit transformation; immutable views; opaque handles; current policy/Work
authorization; mandatory durable audit/budgets; one-shot nonces and conservative
delivery_unknown recovery; broker resource/tool/result paths; sanitized derivative
export. Native v2 preparation refuses unqualified executors before raw input.

Migration: existing v1 capsules remain unchanged. Strict egress requires a new
governed v2 Work, explicitly bound policy and local qualification. Successors
preserve predecessor fingerprints. The actual historical T06 original and its
single metadata doctor FAIL were preserved; a new conservative derivative and
actual prior-reader v2 rejection are recorded in ../historical-preservation.json.

Supported first route: managed HTTP/JSON on qualified Windows. Codex CLI,
generic-shell and isolated-local have no strict capability. This release does
not claim host-owned MCP reload, arbitrary vendor chat API support or an OS
sandbox for trusted extension tools. Classification depends on correct trusted
declarations; the finite synthetic corpus and latency samples are not a universal
leak guarantee or SLA.

The superseded first candidate 90a977c4 was never installed. Its preserved
source-preservation rejection and the final permission correction are documented
in ../release-review-addendum.md. No original green report was rewritten.

Reproducible commands, outputs and hashes: build.py/build.json, install.py/install.json,
core-update-plan.json, core-update-apply.json, installed-egress-qualification.json,
installed-egress-status.json and candidate.patch. Browser verification is
not_applicable for this CLI/protocol scope; actual socket/TLS tests are supplied.
'''
(HERE/'delivery.md').write_text(report,encoding='utf-8')
(HERE/'evolution.md').write_text('''# T07 evolution

Delivered one explicitly qualified Windows managed route. Provider neutrality
means Core-owned policy, immutable views and audit independent of the model;
it does not imply unproven symmetric native backend support. Native wrapper
bypass evidence is a reason to refuse strict capability, not to lower the level.

Required future review checks: Work effects must intersect every tool policy;
hold the actual Work stage guard through disclosure; exception expiry must
remain attached to immutable views; TLS defaults may consume ambient key-log
configuration; client receipt can precede server-finally completion in tests.
Keep final source hashes tied to candidate/archive/installed proof, and record
late corrections separately before any installation. The official updater and
its original backups remain the only delivery mechanism used here.

Finite detectors and conservative whole-unit replacement are intentional limits.
Additional native isolation, platforms, vendor-specific protocol adapters and
more granular transformations require separate implementation/qualification;
they are not latent claims of this release. Historical metadata defects must
retain their original doctor result; export produces a separate derivative.

No global memory changes, publication, host MCP restart, parallel Work or
delegated agent was performed. Project-local evidence and continuation paths
provide the durable handoff. Close the existing Work through its pinned evolve
stage after the actual delivery evidence has been registered.
''',encoding='utf-8')
print('Actual delivery and evolution evidence written',flush=True)
