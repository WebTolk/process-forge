#!/usr/bin/env python3
"""Retained evidence collection rules and compatible facade callbacks."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
BASELINE=None
SCRATCH=None
import copy
from pathlib import Path
from types import SimpleNamespace
from processforge_core import process_execution

def outcome(call):
    try:return ('return',call())
    except (Exception,SystemExit) as exc:return ('error',type(exc).__name__,getattr(exc,'code',None),str(exc))

def cases():
    record={'kind':'artifact','artifact_id':'report','status':'ready','unknown':{'items':[1]}}
    result=[]
    for assignment in [{},{'stage_execution':None},{'stage_execution':{'evidence':'bad'}},{'stage_execution':{'evidence':[None,'bad',record,record]}},{'stage_history':[None,{'evidence':[record,'bad']},{'evidence':'bad'}],'stage_execution':{'evidence':[{'kind':'input','input_id':'report','status':'rejected'}]}}]:
        result += [('_current_evidence',[assignment]),('_accumulated_evidence',[assignment])]
    for kind in ['gate','input','artifact','evidence','attestation','other','',None]:
        result.append(('_evidence_merge_identity',[{'kind':kind,'gate_id':'gate','input_id':'input','artifact_id':'artifact','evidence_id':'evidence','id':'fallback'}]))
    result += [('_evidence_merge_identity',[{}]),('_evidence_merge_identity',[{'kind':'artifact','artifact_id':0,'id':'fallback'}])]
    for existing,incoming in [(None,[]),({},[record]),([None,'bad',record],[]),([record],[{'kind':'input','input_id':'report','status':'rejected'}]),([{'kind':'gate','id':'check','status':'passed'},record],[{'kind':'gate','gate_id':'check','status':'failed'}]),([record],[record,{'kind':'artifact','id':'report','status':'failed'}]),([record],[42])]:
        result.append(('_merge_evidence',[existing,incoming]))
    return result

def run_case(service_type,method,args):
    service=service_type(Path('p'),Path('w'),SimpleNamespace())
    return outcome(lambda:getattr(service,method)(*copy.deepcopy(args)))
from processforge_core.evidence.collection import EvidenceCollectionPolicy

class CollectionTests(unittest.TestCase):
    def test_retained_algorithms(self):
        for method,args in cases():
            actual=run_case(process_execution.ProcessExecutionService,method,args)
            if BASELINE:self.assertEqual(actual,run_case(BASELINE['ProcessExecutionService'],method,args),(method,args))

    def test_alias_replacement_and_history_order(self):
        policy=EvidenceCollectionPolicy()
        old={'kind':'artifact','artifact_id':'report','status':'ready'}
        incoming={'kind':'input','input_id':'report','status':'rejected'}
        result=policy.merge([old], [incoming], identity=policy.identity)
        self.assertEqual(result,[incoming])
        self.assertIs(result[0],incoming)
        assignment={'stage_history':[{'evidence':[old]}],'stage_execution':{'evidence':[incoming]}}
        self.assertEqual(policy.accumulated(assignment,current=policy.current),[old,incoming])
        service=process_execution.ProcessExecutionService(Path('p'),Path('w'),SimpleNamespace())
        self.assertFalse(service._requirement_state('input','report',result)['satisfied'])

    def test_copy_and_incoming_reference_contract(self):
        policy=EvidenceCollectionPolicy()
        old={'kind':'artifact','id':'old','unknown':{'items':[1]}}
        incoming={'kind':'gate','id':'new','unknown':{'items':[2]}}
        current=policy.current({'stage_execution':{'evidence':[old]}})
        current[0]['unknown']['items'].append(3)
        self.assertEqual(old['unknown']['items'],[1])
        result=policy.merge([old],[incoming],identity=policy.identity)
        result[0]['unknown']['items'].append(3)
        self.assertEqual(old['unknown']['items'],[1])
        self.assertIs(result[1],incoming)
        result[1]['unknown']['items'].append(4)
        self.assertEqual(incoming['unknown']['items'],[2,4])

    def test_facade_subclass_dispatch(self):
        results=[]
        constructors=[process_execution.ProcessExecutionService]
        if BASELINE:constructors.insert(0,BASELINE['ProcessExecutionService'])
        for base in constructors:
            events=[]
            sentinel={'id':'custom','unknown':[1]}
            class Override(base):
                def _current_evidence(self,assignment):
                    events.append('current')
                    return [sentinel]
                def _evidence_merge_identity(self,item):
                    events.append(('identity',item['id']))
                    return ('custom',item['id'])
            service=Override(Path('p'),Path('w'),SimpleNamespace())
            accumulated=service._accumulated_evidence({'stage_history':[]})
            self.assertIs(accumulated[0],sentinel)
            incoming={'id':'same','status':'negative'}
            merged=service._merge_evidence([{'id':'same','kind':'other'}],[incoming])
            self.assertIs(merged[0],incoming)
            results.append((accumulated,merged,events))
        self.assertTrue(all(item==results[0] for item in results))
        self.assertEqual(results[0][2],['current',('identity','same'),('identity','same')])

    def test_callback_failure_and_no_io(self):
        policy=EvidenceCollectionPolicy()
        failure=ValueError('callback-failure')
        def denied(*args):raise failure
        with patch.object(Path,'read_bytes',side_effect=AssertionError('unexpected I/O')):
            self.assertEqual(policy.current({}),[])
            with self.assertRaises(ValueError) as caught:
                policy.accumulated({},current=denied)
            self.assertIs(caught.exception,failure)
            with self.assertRaises(ValueError) as caught:
                policy.merge([],[{}],identity=denied)
            self.assertIs(caught.exception,failure)

    def test_package_without_cli(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            root=Path(directory)
            shutil.copytree(ROOT/'src/processforge_core',root/'processforge_core',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            code="import sys; from processforge_core.evidence.collection import EvidenceCollectionPolicy; p=EvidenceCollectionPolicy(); assert p.current({})==[]; assert 'processforge' not in sys.modules"
            result=subprocess.run([sys.executable,'-B','-c',code],cwd=root,capture_output=True,text=True,env=dict(os.environ,PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)

def main():
    global BASELINE,SCRATCH
    parser=argparse.ArgumentParser()
    parser.add_argument('--baseline',type=Path)
    parser.add_argument('--scratch-root',type=Path)
    args=parser.parse_args()
    if args.baseline:
        BASELINE=dict(vars(process_execution))
        exec(compile(args.baseline.read_text(encoding='utf-8'),str(args.baseline),'exec'),BASELINE)
    if args.scratch_root:
        args.scratch_root.mkdir(parents=True,exist_ok=True);SCRATCH=args.scratch_root
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CollectionTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())
