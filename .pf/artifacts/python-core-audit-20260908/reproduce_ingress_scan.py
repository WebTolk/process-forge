"""Measure actual historical JSON decodes for new raw events, in isolation."""
import ast
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import pf_runtime.raw_ingress_kernel as module

source=Path(module.__file__)
tree=ast.parse(source.read_text(encoding='utf-8'))
func=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_recover_indexes')
line=next(n.lineno for n in ast.walk(func) if isinstance(n,ast.Assign) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='loads')
counts={'recovery_calls':0,'historical_records_decoded':0}
def trace(frame,event,arg):
    if frame.f_code.co_filename==str(source) and frame.f_code.co_name=='_recover_indexes':
        if event=='call':counts['recovery_calls']+=1
        if event=='line' and frame.f_lineno==line:counts['historical_records_decoded']+=1
    return trace
with tempfile.TemporaryDirectory(prefix='pf-audit-ingress-') as raw:
    kernel=module.RawIngressKernel(Path(raw))
    sys.settrace(trace)
    try:
        for i in range(20):kernel.ingest(module.NativeAgentEvent('audit','audit','message',{'i':i},native_event_id=str(i)))
    finally:sys.settrace(None)
result={'new_events':20,**counts,'code_line':line}
Path(__file__).with_name('ingress-scan-results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
