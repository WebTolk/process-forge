import ast
import json
import runpy
import sys
import tempfile
from pathlib import Path
ROOT=Path.cwd()
base=ROOT/'.pf/artifacts/core-f09-f12-20260910'
# Load original immutable probe definitions without executing their artifact writes.
source=ROOT/'.pf/artifacts/python-core-audit-20260908/reproduce_fast.py'
ns=runpy.run_path(str(source),run_name='audit_baseline')
results={}
for name in ('missing_unchanged','overlapping_sources','file_exclude'):
    with tempfile.TemporaryDirectory(prefix='pf-f0912-baseline-') as raw:
        results[name]=ns[name](Path(raw))
sys.path.insert(0,str(ROOT/'tools'))
import pf_runtime.raw_ingress_kernel as m
src=Path(m.__file__)
tree=ast.parse(src.read_text())
fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_recover_indexes')
line=next(n.lineno for n in ast.walk(fn) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='loads')
for stable in (True,False):
    counts={'new_events':20,'recovery_calls':0,'historical_records_decoded':0}
    def trace(frame,event,arg):
        if frame.f_code.co_filename==str(src) and frame.f_code.co_name=='_recover_indexes':
            if event=='call':counts['recovery_calls']+=1
            if event=='line' and frame.f_lineno==line:counts['historical_records_decoded']+=1
        return trace
    with tempfile.TemporaryDirectory(prefix='pf-f12-baseline-') as raw:
        k=m.RawIngressKernel(raw)
        sys.settrace(trace)
        try:
            for i in range(20):k.ingest(m.NativeAgentEvent('audit','audit','message',{'i':i},native_event_id=str(i) if stable else None))
        finally:sys.settrace(None)
    results['ingress_stable_'+str(stable)]=counts
results['baseline_commit']='52774e4761975ce0cb29095081c5294db882007d'
(base/'baseline-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
