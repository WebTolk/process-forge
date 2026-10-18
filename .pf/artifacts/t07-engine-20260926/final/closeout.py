from work import *

s=state('completed-state')
assert s['run']['status']=='completed' and s['assignment']['status']=='done'
doctor=command('run-doctor',cli('run-doctor','--project-root',ROOT,'--run',RUN))
assert 'FAIL' not in doctor
build=json.loads((HERE/'build.json').read_text())
install=json.loads((HERE/'install.json').read_text())
assert command('main-head-final',['git','rev-parse','HEAD']).strip()==build['main_head']
assert all(sha(ROOT/n)==h for n,h in build['source_sha256'].items())
assert all(sha(Path(n))==h for n,h in build['protected_sha256'].items())
assert all(sha(Path(n))==h for n,h in build['frozen_sha256'].items())
manifest=json.loads((CORE/'processforge-core.manifest.json').read_text())
assert all(sha(CORE/x['relative_path'])==x['sha256'] for x in manifest['files'])
assert all(sha(CORE/n)==h for n,h in install['unowned_sha256'].items())
text=f'''# Closed T07 engine Work

Actual Work action run_completed; assignment done. All nine pinned stages
completed. Final run-doctor: {doctor.count('PASS:')} PASS, no FAIL. Capsule
SHA256 {CAP_SHA} and main HEAD {build['main_head']} preserved.

Installed candidate {build['candidate_commit']} through standard update
{install['apply']['update_id']}; {install['installed_hashes_verified']} owned file
hashes and {install['backup_hashes_verified']} automatic backups verified.
Archive SHA256 {build['archive_sha256']}.
Backup: {install['apply']['backup_dir']}.

Installed managed egress qualification: 53 checks passed, including actual
Work/CLI and independent HTTP/TLS capture. Runtime restarted normally, ready;
T10 monitor/metrics and journal regression preserved. Config/unowned/frozen
evidence and source hashes remain intact. See delivery.md and install.json.

Supported T07 route: Windows managed HTTP/JSON. Strict native Codex/generic-shell
and isolated-local remain unsupported. Host-owned MCP reload is not claimed.
Original historical T06 metadata doctor FAIL remains intentional and unchanged;
the new derivative does not relabel it. No remaining task in this qualified
delivery scope is left open. Future backend/OS/transform extensions are separate
scope, not silently enabled capabilities.
'''
(HERE/'closeout.md').write_text(text,encoding='utf-8')
handoff=ROOT/'.pf/handoffs/t07-engine-20260926.md'
handoff.write_text('# Handoff: primary agent -> operator\n\n'+text+'\nInput artifacts: .pf/artifacts/t07-engine-20260926/final/delivery.md and closeout.md.\nFiles not to touch: original capsules, frozen stage evidence, source/archive/update backups.\nNext action: ordinary project work; use explicit v2 Work and qualified broker for strict egress.\n',encoding='utf-8')
with (ROOT/'.pf/logs/t07-engine-20260926.md').open('a',encoding='utf-8') as f:
    f.write('\n## '+datetime.now(timezone.utc).isoformat()+' - primary agent\n\nTask: final delivery closeout.\nStatus: Work completed, assignment done, doctor passes, final hashes preserved.\nArtifacts: '+str((HERE/'closeout.md').relative_to(ROOT))+'; .pf/handoffs/t07-engine-20260926.md.\nResidual boundaries: unsupported native/isolated routes and unclaimed host MCP reload, documented in delivery.\n')
print(text,flush=True)
