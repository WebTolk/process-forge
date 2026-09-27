import importlib.util, tempfile, time
from work import *
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from smoke_egress_engine import Fixture

run='garage-t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-cont'
capsule=ROOT/'.pf/contexts/assignment-capsules/t06-delivery-prerequisite-qualify-a-clean-isolated-candidate-containing.capsule.yaml'
original=ROOT/'.pf/runs'/run/'run.yaml'
before={'run':sha(original),'capsule':sha(capsule)}
assert before['capsule']=='465307848dbbc2b1b898c551ea8ccac907a0b0d77b7f17fa37b48c36a643c7e1'
argv=[sys.executable,'-B',ROOT/'bin/pf.py','run-doctor','--project-root',ROOT,'--run',run]
def doctor():
    p=subprocess.run(list(map(str,argv)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=180)
    failures=[x for x in p.stdout.splitlines() if x.startswith('FAIL:')]
    assert p.returncode==1 and len(failures)==1 and failures[0].endswith('run.yaml has no private absolute paths'),p.stdout
    return {'exit_code':p.returncode,'failures':failures,'pass_count':p.stdout.count('PASS:')}
result={'before':before,'doctor_before':doctor()}
with tempfile.TemporaryDirectory(prefix='pf-egress-legacy-proof-') as raw:
    fixture=Fixture(Path(raw),'http://127.0.0.1:1/broker',{'legacy.txt':original.read_bytes()})
    try:
        fixture.policy['sources']['legacy.txt'].update(required=False,transform='redact')
        # This known generated YAML contains long Work identifiers, a benign
        # match for the conservative opaque-encoding detector. Exact bytes only;
        # private-path/raw-hash findings still require whole-unit replacement.
        fixture.policy['exceptions']=[{'checksum':'sha256:'+before['run'],'detector':'opaque_encoding',
                                      'recipient':'fixture','purpose':'qualification','expires':int(time.time())+300}]
        session=fixture.session()
        view=session.prepare_view()
        derivative=session.export_view(view)
        content=json.loads(derivative)
        assert content['items'][0]['text']=='[REDACTED]'
        assert str(ROOT).encode() not in derivative and str(CORE).encode() not in derivative
        assert b'legacy.txt' not in derivative and before['run'].encode() not in derivative
        (HERE/'legacy-derived.json').write_bytes(derivative)
        result['derivative']={'sha256':sha(HERE/'legacy-derived.json'),'bytes':len(derivative),'decision':'whole-unit-redaction','no_network':True,'review_exception':'exact known generated YAML identifiers; no content released'}
    finally:
        fixture.finish()
assert {'run':sha(original),'capsule':sha(capsule)}==before
result['doctor_after']=doctor()
assert result['doctor_before']==result['doctor_after']
old_reader=CORE/'src/processforge_core/work_context.py'
spec=importlib.util.spec_from_file_location('processforge_core._t07_previous_reader',old_reader)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
legacy=module.validate_execution_contract(ROOT,ROOT/'unused.yaml',{}, {'execution_contract':{'contract_version':2}},None)
assert legacy['status']=='blocked' and legacy['reason']=='contract_version_unsupported',legacy
result['actual_old_reader']={'path':str(old_reader),'sha256':sha(old_reader),'result':legacy}
save('historical-preservation.json',result)
print('PASS actual legacy derivative preserves original hashes/doctor FAIL; installed old reader rejects v2',flush=True)
