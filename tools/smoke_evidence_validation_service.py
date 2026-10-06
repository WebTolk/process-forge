#!/usr/bin/env python3
"""Existing evidence validation behavior and explicit facade dependencies."""
from __future__ import annotations
import argparse,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
BASELINE=None
SCRATCH=None
import copy,hashlib
from pathlib import Path
from types import SimpleNamespace
from processforge_core import process_execution

def outcome(call):
    try:return ('return',call())
    except (Exception,SystemExit) as exc:return ('error',type(exc).__name__,getattr(exc,'code',None),str(exc))

def cases(root):
    digest='sha256:'+hashlib.sha256((root/'valid.txt').read_bytes()).hexdigest()
    result=[]
    for value in [None,'',[],42,False,{},'note',[None,'note',{'unknown':{'items':[1]}},7],{'status':'not_applicable'},{'status':'not_applicable','reason':'x','evidence':[]},{'status':'not_applicable','reason':'x','evidence':['proof']},{'kind':None,'status':None},{'recorded_at':'old'},{'path':' valid.txt '},{'path':'missing.txt'},{'path':'dir'},{'path':'../escape.txt'},{'path':str(root/'valid.txt')}]:
        result.append(('_normalize_evidence',[value]))
    for path in ['valid.txt','missing.txt','dir','../escape.txt','nested/../../escape.txt',str(root/'valid.txt'),'a\x00b','', '.']:
        result.append(('_safe_evidence_path',[path]))
    for item in [None,[],{}, {'path':''}, {'path':'../escape.txt'}, {'path':str(root/'valid.txt')}, {'path':'missing.txt','sha256':digest}, {'path':'dir','sha256':digest}, {'path':'valid.txt'}, {'path':'valid.txt','sha256':'bad'}, {'path':'valid.txt','sha256':digest}, {'path':' valid.txt ','sha256':digest.upper()}]:
        result.append(('_evidence_file_diagnostic',[item]))
    return result

def service(service_type,root,counters=None):
    counts=counters if counters is not None else {'clock':0,'rel':0,'hash':0,'path':0}
    def now():counts['clock']+=1;return '2026-10-06T00:00:00Z'
    def rel(path,project):counts['rel']+=1;return path.relative_to(project).as_posix()
    class Counted(service_type):
        def _sha256_file(self,path):counts['hash']+=1;return hashlib.sha256(path.read_bytes()).hexdigest()
        def _safe_evidence_path(self,value):counts['path']+=1;return super()._safe_evidence_path(value)
    return Counted(root,root/'.pf',SimpleNamespace(now_utc=now,rel=rel)),counts

def run_case(service_type,root,method,args):
    instance,counts=service(service_type,root)
    result=outcome(lambda:getattr(instance,method)(*copy.deepcopy(args)))
    if result[0]=='return' and isinstance(result[1],Path):result=('return',result[1].relative_to(root).as_posix())
    return {'outcome':result,'calls':counts}

def retained(path):
    ns=dict(vars(process_execution));exec(compile(path.read_text(encoding='utf-8'),str(path),'exec'),ns)
    return ns['ProcessExecutionService']

from processforge_core.evidence_validation import EvidenceValidationService
from processforge_core.composition import build_evidence_validation_service
from dataclasses import FrozenInstanceError
from unittest.mock import patch

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        (self.root/'valid.txt').write_bytes(b'original')
        (self.root/'dir').mkdir()

    def test_retained_results_errors_and_counts(self):
        for method,args in cases(self.root):
            actual=run_case(process_execution.ProcessExecutionService,self.root,method,args)
            if BASELINE:self.assertEqual(actual,run_case(BASELINE,self.root,method,args),(method,args))

    def test_copy_clock_and_not_applicable_contract(self):
        instance,counts=service(process_execution.ProcessExecutionService,self.root)
        original={'unknown':{'items':[1]},'recorded_at':'old'}
        result,blockers=instance._normalize_evidence([original,{'status':'not_applicable'},None,'note'])
        self.assertEqual(counts,{'clock':1,'rel':0,'hash':0,'path':0})
        self.assertEqual(blockers,[{'code':'not_applicable_evidence_incomplete','index':1},{'code':'invalid_evidence','index':2}])
        self.assertEqual(result[1]['id'],'attestation-4')
        result[0]['unknown']['items'].append(2)
        self.assertEqual(original['unknown']['items'],[1])
        self.assertEqual(original['recorded_at'],'old')
        result,blockers=instance._normalize_evidence({'status':'not_applicable','reason':'x','evidence':['proof'],'path':'valid.txt'})
        self.assertFalse(blockers);self.assertIn('sha256',result[0]);self.assertEqual(counts['clock'],2)
        instance._normalize_evidence(None);self.assertEqual(counts['clock'],3)

    def test_live_bytes_digest_deletion_and_directory(self):
        instance,counts=service(process_execution.ProcessExecutionService,self.root)
        record=instance._normalize_evidence({'kind':'artifact','id':'report','path':'valid.txt'})[0][0]
        self.assertIsNone(instance._evidence_file_diagnostic(record))
        self.assertIsNone(instance._evidence_file_diagnostic(record))
        self.assertEqual(counts['hash'],3)
        path=self.root/'valid.txt';stat=path.stat();path.write_bytes(b'modified')
        os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
        self.assertEqual(instance._evidence_file_diagnostic(record)['code'],'evidence_file_changed')
        path.unlink()
        self.assertEqual(instance._evidence_file_diagnostic(record)['code'],'evidence_file_missing')
        self.assertEqual(instance._evidence_file_diagnostic({'path':'dir'})['code'],'evidence_file_not_regular')
        self.assertEqual(counts['hash'],4)

    def test_resolve_failures_and_live_containment(self):
        instance=process_execution.ProcessExecutionService(self.root,self.root/'.pf',SimpleNamespace())
        self.assertIsNone(instance._safe_evidence_path(str(self.root/'valid.txt')))
        self.assertIsNone(instance._safe_evidence_path('../outside.txt'))
        nul=process_execution.ProcessExecutionService(self.root,self.root/'.pf',SimpleNamespace(now_utc=lambda:'fixed'))
        self.assertEqual(nul._normalize_evidence({'path':'a\x00b'})[1][0]['code'],'artifact_path_missing')
        for failure in [OSError('io'),RuntimeError('loop'),ValueError('invalid')]:
            with patch.object(Path,'resolve',side_effect=failure):self.assertIsNone(instance._safe_evidence_path('valid.txt'))
        outside=self.root.parent/'outside.txt'
        with patch.object(Path,'resolve',side_effect=[outside,self.root,self.root/'valid.txt',self.root]):
            self.assertIsNone(instance._safe_evidence_path('valid.txt'))
            self.assertEqual(instance._safe_evidence_path('valid.txt'),self.root/'valid.txt')

    def test_material_failures_and_facade_callback_order(self):
        class FakePath:
            def __init__(self,fail):self.fail=fail
            def exists(self):
                if self.fail=='exists':raise OSError('exists denied')
                return True
            def is_file(self):
                if self.fail=='is_file':raise OSError('stat denied')
                return True
        for fail in ['exists','is_file','rel','hash']:
            observed=[]
            for cls in ([BASELINE] if BASELINE else [])+[process_execution.ProcessExecutionService]:
                trace=[]
                def now():trace.append('clock');return 'fixed'
                def rel(path,root):
                    trace.append('rel')
                    if fail=='rel':raise OSError('rel denied')
                    return 'file'
                class Override(cls):
                    def _safe_evidence_path(self,value):trace.append('path');return FakePath(fail)
                    def _sha256_file(self,path):
                        trace.append('hash')
                        if fail=='hash':raise OSError('hash denied')
                        return 'digest'
                instance=Override(self.root,self.root/'.pf',SimpleNamespace(now_utc=now,rel=rel))
                normalized=instance._normalize_evidence({'path':'file'})
                diagnostic=instance._evidence_file_diagnostic({'path':'file','sha256':'sha256:digest'})
                observed.append((normalized,diagnostic,trace))
                if fail=='is_file':self.assertEqual(normalized[1][0]['code'],'artifact_path_missing')
                if fail in ('rel','hash'):self.assertEqual(normalized[1][0]['code'],'artifact_path_unreadable')
                if fail in ('exists','is_file','hash'):self.assertEqual(diagnostic['code'],'evidence_file_unreadable')
            if BASELINE:self.assertEqual(observed[0],observed[1])

    def test_callback_exception_identity_and_deferred_core(self):
        from processforge_core.work_context import ContextContractError
        for source in ['clock','path','rel','hash']:
            error=ContextContractError('required_failure')
            def fail(*args):raise error
            class Override(process_execution.ProcessExecutionService):
                def _safe_evidence_path(self,value):
                    if source=='path':raise error
                    return self.project_root/'valid.txt'
                def _sha256_file(self,path):
                    if source=='hash':raise error
                    return 'digest'
            instance=Override(self.root,self.root/'.pf',SimpleNamespace(now_utc=fail if source=='clock' else lambda:'fixed',rel=fail if source=='rel' else lambda *args:'valid.txt'))
            caught=None
            try:instance._normalize_evidence({'path':'valid.txt'})
            except ContextContractError as exc:caught=exc
            self.assertIs(caught,error)
        instance=process_execution.ProcessExecutionService(self.root,self.root/'.pf',SimpleNamespace())
        self.assertIsNone(instance._evidence_file_diagnostic(None))
        self.assertIsNone(instance._evidence_file_diagnostic({}))
        self.assertEqual(instance._safe_evidence_path('valid.txt'),self.root/'valid.txt')

    def test_rootless_facade_preserves_existing_early_returns(self):
        for cls in ([BASELINE] if BASELINE else [])+[process_execution.ProcessExecutionService]:
            instance=object.__new__(cls)
            for evidence in [None,[],{}, {'path':'  '}, {'kind':'gate','id':'example','status':'passed'}]:
                self.assertIsNone(instance._evidence_file_diagnostic(evidence))
            self.assertIsNone(instance._safe_evidence_path(str(self.root/'valid.txt')))
            if cls is process_execution.ProcessExecutionService:
                gate=instance._gate_state({},'example',[{'kind':'gate','id':'example','status':'passed'}],phase='exit')
                self.assertTrue(gate['satisfied'])
            calls=[]
            object.__setattr__(instance,'core',SimpleNamespace(now_utc=lambda:calls.append('clock') or 'fixed'))
            normalized,blockers=instance._normalize_evidence([{'unknown':{'items':[1]}},'note',{'path':str(self.root/'valid.txt')}])
            self.assertEqual(calls,['clock'])
            self.assertEqual(normalized,[{'unknown':{'items':[1]},'kind':'attestation','status':'ready','recorded_at':'fixed'},
                                         {'kind':'attestation','id':'attestation-2','status':'ready','summary':'note','recorded_at':'fixed'}])
            self.assertEqual(blockers,[{'code':'artifact_path_missing','index':2,'path':str(self.root/'valid.txt')}])

    def test_deferred_root_preserves_file_branch_order_and_exceptions(self):
        trace=[]
        selected=[self.root]
        def root():trace.append('root');return selected[0]
        validator=build_evidence_validation_service(root,now_utc=lambda:trace.append('clock') or 'fixed',
                    relative_path=lambda path:trace.append('rel') or 'valid.txt',
                    sha256_file=lambda path:trace.append('hash') or 'digest')
        self.assertEqual(trace,[])
        self.assertIsNone(validator.diagnostic(None))
        self.assertIsNone(validator.diagnostic({'path':' '}))
        self.assertEqual(validator.diagnostic({'path':str(self.root/'valid.txt')})['code'],'evidence_file_unsafe')
        self.assertEqual(trace,[])
        self.assertFalse(validator.normalize('note')[1]);self.assertEqual(trace,['clock'])
        trace.clear()
        self.assertEqual(validator.normalize({'path':'valid.txt'})[0][0]['sha256'],'sha256:digest')
        self.assertEqual(trace,['clock','root','root','rel','hash'])
        selected[0]=self.root/'dir';trace.clear()
        self.assertEqual(validator.safe_path('valid.txt'),self.root/'dir'/'valid.txt')
        self.assertEqual(trace,['root','root'])
        error=LookupError('required_root_failure')
        def fail():raise error
        validator=build_evidence_validation_service(fail,now_utc=lambda:'fixed',relative_path=str,sha256_file=lambda path:'digest')
        self.assertIsNone(validator.diagnostic({}))
        self.assertIsNone(validator.safe_path(str(self.root/'valid.txt')))
        caught=None
        try:validator.safe_path('valid.txt')
        except LookupError as exc:caught=exc
        self.assertIs(caught,error)

    def test_construction_is_pure_and_dependencies_frozen(self):
        def forbidden(*args):raise AssertionError('unexpected callback')
        with patch.object(Path,'resolve',side_effect=forbidden),patch.object(Path,'read_bytes',side_effect=forbidden):
            validator=build_evidence_validation_service(self.root,now_utc=forbidden,relative_path=forbidden,sha256_file=forbidden)
        with self.assertRaises(FrozenInstanceError):validator.project_root=Path('other')
        class FalseyResolver:
            def __bool__(self):return False
            def __call__(self,value):return None
        validator=EvidenceValidationService(self.root,lambda:'fixed',lambda path:'file',forbidden,FalseyResolver())
        self.assertEqual(validator.diagnostic({'path':'file'})['code'],'evidence_file_unsafe')

    def test_package_without_cli(self):
        code="import sys; from pathlib import Path; from processforge_core.composition import build_evidence_validation_service; s=build_evidence_validation_service(Path('.'),now_utc=lambda:'x',relative_path=str,sha256_file=lambda p:'x'); assert s.diagnostic(None) is None; assert not any(n=='processforge' or n.startswith('pf_runtime') for n in sys.modules)"
        env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([sys.executable,'-B','-c',code],cwd=self.root,env=env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--baseline',type=Path);parser.add_argument('--scratch-root',type=Path)
    args=parser.parse_args()
    if args.baseline:BASELINE=retained(args.baseline)
    if args.scratch_root:args.scratch_root.mkdir(parents=True,exist_ok=True);SCRATCH=args.scratch_root
    unittest.main(argv=[sys.argv[0]],verbosity=2)
