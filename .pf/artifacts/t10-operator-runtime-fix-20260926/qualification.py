from work import *
build=json.loads((HERE/'build.json').read_text());assert build.get('finished_at')
candidate=ROOT/'.pf/tmp/t10-operator-runtime-fix-20260926/candidate'
patch=command('combined-delivery-patch',['git','diff','40c9894227738472976546849047550415099486',build['candidate_commit'],'--'],cwd=candidate)
(HERE/'candidate.patch').write_text(patch,encoding='utf-8')
(HERE/'qualification.md').write_text('# Correction candidate qualified\n\nCommit '+build['candidate_commit']+'; exact six-file correction of a5eeac53. Source focused reassessment, candidate schemas/checksums/cleanliness and feature/scheduler checks, official release-pack/archive-test quick and extracted metrics/server/monitor checks passed. All '+str(build['archive_files_verified'])+' archive-owned hashes verified.\n\nArchive: '+build['archive']+'\nSHA256: '+build['archive_sha256']+'\nPlan: '+json.dumps(build['plan_counts'])+'; no conflicts or migration.\n\nApply only through the installed official updater, preserving automatic backup and config/unowned/frozen/source hashes. Reconcile the actual prior successful update core-update-20260926T190618Z; do not rerun its failed acceptance script. After this new transaction, wait boundedly for the independent first observation and verify live snapshot and installed features. Same existing Work remains in release-delivery.\n',encoding='utf-8')
previous=ROOT/'.pf/artifacts/t10-operator-20260926'
s=(previous/'close_evidence.py').read_text(encoding='utf-8')
s=s.replace('Source 18 focused checks, clean candidate validation,', 'Original 18 source checks plus focused six-file delivery correction reassessment, clean candidate validation,')
s=s.replace('Actual installed server status publishes compact activity metrics;', 'Actual installed server status publishes compact activity metrics independently of slow scheduler routing;')
s=s.replace('Exact build/update commands, hashes and preservation evidence:', 'Initial a5eeac53 installation and its failed live observation are retained in ../t10-operator-20260926/; corrected final build/update commands, hashes and preservation evidence:')
(HERE/'close_evidence.py').write_text(s,encoding='utf-8')
print('Qualified corrective official update plan recorded',flush=True)
