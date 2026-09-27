import copy
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
schema_path = ROOT/'schemas/execution-contract.schema.json'
schema = json.loads(schema_path.read_text(encoding='utf-8'))
intent = schema['$defs']['assignment_intent']
if 'obligations' not in intent['required']:
    intent['required'].append('obligations')
intent['properties']['obligations'] = {'type':'object','additionalProperties':True}
schema_path.write_text(json.dumps(schema,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
embedded = {k:copy.deepcopy(v) for k,v in schema.items() if k not in ('$schema','$id','title','description')}
def rewrite(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key == '$ref' and isinstance(item,str) and item.startswith('#/$defs/'):
                value[key] = item.replace('#/$defs/', '#/$defs/execution_contract/$defs/', 1)
            else:
                rewrite(item)
    elif isinstance(value,list):
        for item in value:
            rewrite(item)
rewrite(embedded)
capsule_path = ROOT/'schemas/context-capsule.schema.json'
capsule = json.loads(capsule_path.read_text(encoding='utf-8'))
capsule['$defs']['execution_contract'] = embedded
capsule_path.write_text(json.dumps(capsule,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
assignment_path=ROOT/'schemas/assignment.schema.json'
assignment=json.loads(assignment_path.read_text(encoding='utf-8'))
modes=assignment['$defs']['execution_mode']['properties']['kind']['enum']
for mode in ['analysis','analysis_only']:
    if mode not in modes:
        modes.append(mode)
assignment_path.write_text(json.dumps(assignment,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('Updated obligations and equivalent capsule-local definition')
