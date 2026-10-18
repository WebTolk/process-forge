import ast
import copy
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t03_validator',ROOT/'tools/validate-process-forge-schemas.py')
validator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
schema=json.loads((ROOT/'schemas/execution-contract.schema.json').read_text(encoding='utf-8'))
capsule=json.loads((ROOT/'schemas/context-capsule.schema.json').read_text(encoding='utf-8'))
embedded=copy.deepcopy(capsule['$defs']['execution_contract'])
def normalize(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='$ref':
                value[key]=item.replace('#/$defs/execution_contract/$defs/','#/$defs/')
            else:
                normalize(item)
    elif isinstance(value,list):
        for item in value:
            normalize(item)
normalize(embedded)
assert embedded=={k:v for k,v in schema.items() if k not in ('$schema','$id','title','description')}
contract=json.loads((HERE/'developer-probe.json').read_text(encoding='utf-8'))['execution_contract']
assert not validator.validate_instance(contract,schema,schema,'$')
for field in schema['required']:
    invalid=copy.deepcopy(contract)
    del invalid[field]
    assert validator.validate_instance(invalid,schema,schema,'$'),field
invalid=copy.deepcopy(contract)
invalid['contract_version']=99
assert validator.validate_instance(invalid,schema,schema,'$')
invalid=copy.deepcopy(contract)
del invalid['required_sources'][0]['checksum']
assert validator.validate_instance(invalid,schema,schema,'$')
docs=['docs/concepts/work-context.md','docs/ru/concepts/work-context.md','docs/concepts/context-capsule.md','docs/ru/concepts/context-capsule.md','docs/concepts/work-execution-contract.md']
for name in docs:
    path=ROOT/name
    text=path.read_text(encoding='utf-8')
    assert all(line==line.rstrip() for line in text.splitlines()),name
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if not link.startswith(('http:','https:','#')):
            assert (path.parent/link.split('#')[0]).exists(),(name,link)
sources=['src/processforge_core/work_context.py','src/processforge_core/process_execution.py','src/processforge_core/work_resources.py','tools/processforge.py','tools/smoke_work_capsule_contract_parity.py','tools/smoke_work_resource_binding.py','tools/smoke_worker_run_shell.py','tools/smoke_worker_workspace_access.py']
for name in sources:
    ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
result={'status':'PASS','schema_equivalence':'PASS','complete_contract_positive':'PASS','required_field_negatives':len(schema['required']),'unknown_version_and_missing_source_hash':'PASS','docs':len(docs),'python_files':len(sources)}
(HERE/'delivery-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
