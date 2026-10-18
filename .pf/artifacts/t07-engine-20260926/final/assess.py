from concurrent.futures import ThreadPoolExecutor, as_completed
import ast
from work import *

prior=json.loads((HERE.parent/'assurance-results.json').read_text())
changed=prior['changed_files']
delta={n for n,h in prior['source_sha256'].items() if sha(ROOT/n)!=h}
assert delta=={'src/processforge_core/egress/engine.py','tools/smoke_egress_engine.py','docs/concepts/egress-engine.md','docs/ru/concepts/egress-engine.md','checksums/processforge.sha256'},delta
jobs=[(s,[sys.executable,'-B',ROOT/'tools'/(s+'.py'),*(['--json'] if s.startswith('smoke_egress') else [])]) for s in ['smoke_egress_engine','smoke_egress_work','smoke_egress_transport']]
jobs += [(label,[sys.executable,'-B',ROOT/'tools'/script,*args]) for label,script,args in [
 ('schemas','validate-process-forge-schemas.py',[]),('public-cleanliness','validate-public-cleanliness.py',[]),('checksums','validate-process-forge-checksums.py',['--check'])]]
passed=[]
with ThreadPoolExecutor(max_workers=2) as pool:
    futures={pool.submit(command,'source-'+name,args,timeout=420):name for name,args in jobs}
    for future in as_completed(futures):
        future.result();passed.append(futures[future])
for n in changed:
    if n.endswith('.py'):ast.parse((ROOT/n).read_text(encoding='utf-8-sig'))
save('assurance-results.json',{'changed_files':changed,'source_sha256':{n:sha(ROOT/n) for n in changed},
 'passed':prior['passed'],'failed':[],'correction_checks':sorted(passed),'correction_delta':sorted(delta),
 'prior_checks':'../assurance-results.json','review':'../release-review-addendum.md'})
print('PASS final tool/Work permission correction: six checks; existing 14-command assurance preserved',flush=True)
