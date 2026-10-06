#!/usr/bin/env python3
"""Existing stage readiness rules and compatible facade callbacks."""
from __future__ import annotations
import argparse,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
BASELINE=None
SCRATCH=None
import copy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from processforge_core import process_execution

def outcome(call):
    try:return ('return',call())
    except (Exception,SystemExit) as exc:return ('error',type(exc).__name__,getattr(exc,'code',None),str(exc))

def cases():
    result=[];statuses=['ready','present','passed','approved','not_applicable','failed','',None,'READY']
    for kind,evidence_kind,key in [('artifact','artifact','artifact_id'),('input','artifact','artifact_id'),('evidence','attestation','id')]:
        for status in statuses:
            result.append(('_requirement_state',[kind,'report',[{'kind':evidence_kind,key:'report','status':status,'unknown':{'items':[1]}}]],{}))
        result.append(('_requirement_state',[kind,'report',[]],{}))
        result.append(('_requirement_state',[kind,'report',[{'kind':evidence_kind,key:'report','status':'approved'},{'kind':evidence_kind,'id':'report','status':'rejected'}]],{}))
    result.append(('_requirement_state',['unknown','report',[{'kind':'artifact','id':'report'}]],{}))
    for status in statuses:
        result.append(('_gate_state',[{},'check',[{'kind':'gate','id':'check','status':status}]],{'phase':'exit'}))
    for definitions in [None,[None,{'id':'check','type':'manual','blocking':False,'required':False}], [{'id':'check','type':'first'},{'id':'check','type':'second'}]]:
        result.append(('_gate_state',[{'gates':definitions},'check',[{'kind':'gate','gate_id':'check','status':'passed'}]],{'phase':'entry'}))
    result += [('_gate_state',[{},'check',[]],{'phase':'exit'}),('_gate_state',[{},'check',[{'kind':'gate','id':'check','status':'passed'},{'kind':'gate','gate_id':'check','status':'failed'}]],{'phase':'exit'})]
    optional={'artifact_definitions':[None,{'id':'a','required':False},{'id':'b','required':True}]}
    for process,stage in [({},{}),({}, {'required_artifacts':['explicit','',7,None],'produced_artifacts':['ignored']}),({}, {'required_artifacts':'bad','produced_artifacts':['a','b','a']}),(optional,{'produced_artifacts':['a','b']}),(dict(optional,stages=[{'id':'next','required_inputs':['a']}]),{'produced_artifacts':['a','b']}),(dict(optional,stages=[{'id':'next','executable':False,'required_inputs':['a']}]),{'produced_artifacts':['a','b']}),({'artifact_definitions':'bad','stages':[None,{'required_inputs':['a']}]},{'produced_artifacts':[None,0,False,'']})]:
        result.append(('_required_artifact_ids',[process,stage],{}))
    bad={'id':'x','satisfied':False,'diagnostic':{'code':'changed','nested':[1]}}
    ready={'id':'y','satisfied':True}
    for args in [[[],[],[],[],[]],[[bad,ready],[bad],[bad],[dict(bad,required=True,blocking=True)],[{'id':'auto','status':'blocked'}]], [[],[],[],[dict(bad,required=False,blocking=True),dict(bad,required=True,blocking=False)],[{'id':'auto','status':'ready'}]],[[{'id':'x'}],[],[],[],[]],[[],[],[],[{'id':'x','required':True}],[]],[[],[],[],[],[{'id':'auto'}]]]:
        result.append(('_stage_requirements',args,{}))
    for item in [bad,{'id':'x','diagnostic':None},{'id':'x','diagnostic':[]},{}]:
        result.append(('_requirement_blocker',['missing','artifact_id',item],{}))
    return result

def counted(service_type,counts):
    class Counted(service_type):
        def _evidence_file_diagnostic(self,item):counts['diagnostic']+=1;return item.get('_diagnostic') if isinstance(item,dict) else None
        def _string_list(self,value):counts['strings']+=1;return super()._string_list(value)
        def _requirement_blocker(self,*args):counts['blocker']+=1;return super()._requirement_blocker(*args)
    return Counted(Path('project'),Path('work'),SimpleNamespace())

def run_case(service_type,method,args,kwargs):
    counts={'diagnostic':0,'strings':0,'blocker':0,'stages':0}
    instance=counted(service_type,counts)
    namespace=service_type._required_artifact_ids.__globals__
    original=namespace['executable_stages']
    def stages(process):counts['stages']+=1;return original(process)
    with patch.dict(namespace,executable_stages=stages):result=outcome(lambda:getattr(instance,method)(*copy.deepcopy(args),**copy.deepcopy(kwargs)))
    return {'outcome':result,'calls':counts}

def retained(path):
    ns=dict(vars(process_execution));exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),ns)
    return ns['ProcessExecutionService']

from dataclasses import FrozenInstanceError
from processforge_core.stage_readiness import StageReadinessPolicy
from processforge_core.composition import build_stage_readiness_policy

def policy(diagnostic=lambda item:None):
    instance=process_execution.ProcessExecutionService(Path('project'),Path('work'),SimpleNamespace())
    return build_stage_readiness_policy(file_diagnostic=diagnostic,string_list=instance._string_list,stage_definitions=process_execution.executable_stages,blocker_callback=instance._requirement_blocker)

class ReadinessTests(unittest.TestCase):
    def test_retained_rules_errors_and_callback_counts(self):
        for method,args,kwargs in cases():
            actual=run_case(process_execution.ProcessExecutionService,method,args,kwargs)
            if BASELINE:self.assertEqual(actual,run_case(BASELINE,method,args,kwargs),(method,args))

    def test_latest_negative_aliases_and_status_sets(self):
        p=policy()
        old={'kind':'artifact','artifact_id':'report','status':'approved'}
        new={'kind':'input','input_id':'report','status':'failed'}
        self.assertFalse(p.requirement('input','report',[old,new])['satisfied'])
        self.assertTrue(p.requirement('artifact','report',[old,new])['satisfied'])
        for status in ['ready','present','passed','approved','not_applicable']:
            self.assertTrue(p.requirement('evidence','proof',[{'kind':'attestation','id':'proof','status':status}])['satisfied'])
            self.assertEqual(p.gate({},'g',[{'kind':'gate','gate_id':'g','status':status}],phase='exit')['satisfied'],status in {'passed','approved','not_applicable'})
        gate=p.gate({'gates':[{'id':'g','required':False,'blocking':False,'type':'manual'}]},'g',[],phase='entry')
        self.assertEqual((gate['required'],gate['blocking'],gate['type'],gate['phase'],gate['satisfied']),(False,False,'manual','entry',False))
        self.assertFalse(p.gate({},'g',[{'kind':'gate','id':'g','status':'passed'},{'kind':'gate','gate_id':'g','status':'failed'}],phase='exit')['satisfied'])

    def test_optional_artifacts_and_executable_consumers(self):
        p=policy();process={'artifact_definitions':[{'id':'a','required':False}]}
        stage={'produced_artifacts':['a','b','a']}
        self.assertEqual(p.required_artifact_ids(process,stage),['b'])
        process['stages']=[{'id':'next','required_inputs':['a']}]
        self.assertEqual(p.required_artifact_ids(process,stage),['a','b','a'])
        process['stages'][0]['executable']=False
        self.assertEqual(p.required_artifact_ids(process,stage),['b'])
        self.assertEqual(p.required_artifact_ids(process,dict(stage,required_artifacts=['explicit','',0,None])),['explicit','0','None'])

    def test_diagnostic_priority_and_copy_reference_contract(self):
        diagnostic={'code':'evidence_file_changed','nested':[1]}
        p=policy(lambda item:diagnostic)
        record={'kind':'artifact','id':'x','status':'failed','unknown':{'items':[1]}}
        result=p.requirement('artifact','x',[record])
        self.assertIs(result['diagnostic'],diagnostic)
        self.assertFalse(result['satisfied'])
        result['evidence']['unknown']['items'].append(2)
        self.assertEqual(record['unknown']['items'],[1])
        blocker=p.blocker('missing','artifact_id',result)
        blocker['diagnostic']['nested'].append(2)
        self.assertEqual(diagnostic['nested'],[1])
        gate=p.gate({},'g',[{'kind':'gate','id':'g','status':'failed'}],phase='exit')
        self.assertIs(gate['diagnostic'],diagnostic)

    def test_group_order_and_optional_gate_filter(self):
        p=policy();bad={'id':'x','satisfied':False};good={'id':'ok','satisfied':True}
        gates=[dict(bad,required=True,blocking=True),dict(bad,required=False,blocking=True),dict(bad,required=True,blocking=False)]
        result=p.requirements([bad,good],[bad],[bad],gates,[{'id':'auto','status':'unavailable'},{'id':'ready','status':'ready'}])
        self.assertEqual([row['code'] for row in result],['required_input_missing','artifact_evidence_missing','required_evidence_missing','gate_evidence_missing','automation_not_ready'])
        self.assertEqual(result[-1],{'code':'automation_not_ready','obligation_id':'auto','status':'unavailable'})
        self.assertEqual(p.requirements([],[],[],gates[1:],[]),[])

    def test_facade_overrides_and_incoming_callback_references(self):
        outcomes=[]
        for cls in ([BASELINE] if BASELINE else [])+[process_execution.ProcessExecutionService]:
            marker={'custom':True};diagnostic={'code':'override'};trace=[]
            class Override(cls):
                def _requirement_blocker(self,*args):trace.append(('blocker',args[0]));return marker
                def _string_list(self,value):trace.append(('strings',value));return ['override']
                def _evidence_file_diagnostic(self,item):trace.append(('diagnostic',item['id']));return diagnostic
            instance=Override(Path('project'),Path('work'),SimpleNamespace())
            requirements=instance._stage_requirements([{'id':'x','satisfied':False}],[],[],[],[])
            self.assertIs(requirements[0],marker)
            artifacts=instance._required_artifact_ids({},{});self.assertEqual(artifacts,['override'])
            requirement=instance._requirement_state('artifact','x',[{'kind':'artifact','id':'x','status':'ready'}])
            self.assertIs(requirement['diagnostic'],diagnostic)
            outcomes.append((requirements,artifacts,requirement,trace))
        if BASELINE:self.assertEqual(outcomes[0],outcomes[1])

    def test_callback_exception_identity(self):
        from processforge_core.work_context import ContextContractError
        for cls in ([BASELINE] if BASELINE else [])+[process_execution.ProcessExecutionService]:
            error=ContextContractError('required_failure')
            class Override(cls):
                def _evidence_file_diagnostic(self,item):raise error
                def _requirement_blocker(self,*args):raise error
            instance=Override(Path('project'),Path('work'),SimpleNamespace())
            for call in [lambda:instance._requirement_state('artifact','x',[{'kind':'artifact','id':'x'}]),lambda:instance._gate_state({},'g',[{'kind':'gate','id':'g'}],phase='exit'),lambda:instance._stage_requirements([{'id':'x','satisfied':False}],[],[],[],[])]:
                caught=None
                try:call()
                except ContextContractError as exc:caught=exc
                self.assertIs(caught,error)

    def test_pure_construction_and_missing_rules(self):
        def forbidden(*args):raise AssertionError('unexpected I/O or callback')
        with patch.object(Path,'resolve',side_effect=forbidden),patch.object(Path,'read_bytes',side_effect=forbidden):
            p=build_stage_readiness_policy(file_diagnostic=forbidden,string_list=forbidden,stage_definitions=forbidden,blocker_callback=forbidden)
            self.assertFalse(p.requirement('artifact','missing',[])['satisfied'])
            self.assertFalse(p.gate({},'missing',[],phase='entry')['satisfied'])
            self.assertEqual(p.requirements([],[],[],[],[]),[])
            self.assertEqual(p.blocker('missing','artifact_id',{'id':'x'}),{'code':'missing','artifact_id':'x'})
        with self.assertRaises(FrozenInstanceError):p.file_diagnostic=lambda item:None

    def test_live_validation_consumer_rejects_changed_and_missing_files(self):
        import hashlib
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            root=Path(temp).resolve();path=root/'report.txt';path.write_bytes(b'original')
            reads=[]
            class Counted(process_execution.ProcessExecutionService):
                def _sha256_file(self,path):reads.append(path);return hashlib.sha256(path.read_bytes()).hexdigest()
            instance=Counted(root,root/'.pf',SimpleNamespace(now_utc=lambda:'fixed',rel=lambda path,project:path.relative_to(project).as_posix()))
            record=instance._normalize_evidence({'kind':'artifact','id':'report','path':'report.txt'})[0][0]
            gate=dict(record,kind='gate',id='check',status='passed')
            for _ in range(2):
                self.assertTrue(instance._requirement_state('artifact','report',[record])['satisfied'])
                self.assertTrue(instance._gate_state({},'check',[gate],phase='exit')['satisfied'])
            self.assertEqual(len(reads),5)
            stat=path.stat();path.write_bytes(b'modified');os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
            self.assertEqual(instance._requirement_state('artifact','report',[record])['diagnostic']['code'],'evidence_file_changed')
            self.assertEqual(instance._gate_state({},'check',[gate],phase='exit')['diagnostic']['code'],'evidence_file_changed')
            self.assertEqual(len(reads),7)
            path.unlink();record['status']='failed';gate['status']='failed'
            self.assertEqual(instance._requirement_state('artifact','report',[record])['diagnostic']['code'],'evidence_file_missing')
            self.assertEqual(instance._gate_state({},'check',[gate],phase='exit')['diagnostic']['code'],'evidence_file_missing')
            self.assertEqual(len(reads),7)

    def test_package_without_cli(self):
        code="import sys; from processforge_core.stage_readiness import StageReadinessPolicy; from processforge_core.composition import build_stage_readiness_policy; p=build_stage_readiness_policy(file_diagnostic=lambda x:None,string_list=lambda x:[],stage_definitions=lambda x:[],blocker_callback=lambda *a:{}); assert p.requirements([],[],[],[],[])==[]; assert not any(n=='processforge' or n.startswith('pf_runtime') for n in sys.modules)"
        result=subprocess.run([sys.executable,'-B','-c',code],env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);parser.add_argument('--scratch-root',type=Path)
    args=parser.parse_args()
    if args.baseline:BASELINE=retained(args.baseline)
    if args.scratch_root:args.scratch_root.mkdir(parents=True,exist_ok=True);SCRATCH=args.scratch_root
    unittest.main(argv=[sys.argv[0]],verbosity=2)
