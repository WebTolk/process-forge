from work import *
s=state('completed-state');assert s['run']['status']=='completed' and s['assignment']['status']=='done'
doctor=command('run-doctor',cli('run-doctor','--project-root',ROOT,'--run',RUN))
assert 'FAIL' not in doctor
build=json.loads((HERE/'build.json').read_text());installed=json.loads((HERE/'install.json').read_text())
assert command('main-head-final',['git','rev-parse','HEAD']).strip()==build['main_head']
text='# Closed T10 operator Work\n\nActual PF action run_completed, assignment done; all nine pinned stages completed. Final run-doctor: '+str(doctor.count('PASS:'))+' PASS, no FAIL. Capsule SHA256 '+CAP_SHA+' preserved. Main HEAD '+build['main_head']+' retained.\n\nInstalled '+build['candidate_commit']+' through '+installed['apply']['update_id']+', every 1001 owned payload hashes and six corrective backups verified. Initial 13-file backups retained in core-update-20260926T190618Z. Fresh live compact metrics accepted on the first probe, with partial groups explicitly reported.\n\nNext user-authorized Work: implement T07 egress engine, starting with backend feasibility and explicit supported/unsupported enforcement scope, then versioned intent, policy/views/audit/broker/export and acceptance. Follow the existing design and preserve historical artifacts. Connected host MCP reload remains unclaimed; standard Work CLI fallback is available.\n'
(HERE/'closeout.md').write_text(text,encoding='utf-8')
with (ROOT/'.pf/handoffs/t10-operator-20260926.md').open('a',encoding='utf-8') as handle:handle.write('\n'+text)
print(text,flush=True)
