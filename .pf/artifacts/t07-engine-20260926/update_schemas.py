from pathlib import Path
import json, copy
ROOT = Path(__file__).resolve().parents[3]
limits = {"unit_bytes":1048576,"envelope_bytes":4194304,"attempt_bytes":33554432,"disclosures":128,"json_depth":16,"classification_ms":2000,"token_seconds":30}
identifier = {'type':'string','pattern':'^[a-z][a-z0-9-]{0,63}$'}
digest = {'type':'string','pattern':'^sha256:[a-f0-9]{64}$'}
props = {k:copy.deepcopy(identifier) for k in ['policy_id','recipient','purpose']}
props.update(policy_checksum=digest,detector_checksum=digest,minimum_enforcement={'const':'mediated_session'},limits={'type':'object','required':list(limits),'properties':{k:{'type':'integer','minimum':1,'maximum':v} for k,v in limits.items()},'additionalProperties':False})
binding = {'type':'object','required':list(props),'properties':props,'additionalProperties':False}
predecessor = {'type':'object','required':['assignment_id','capsule_checksum'],'properties':{'assignment_id':{'type':'string','pattern':'^[a-z0-9][a-z0-9-]{0,159}$'},'capsule_checksum':digest},'additionalProperties':False}
def save(path,doc):
    path.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
save(ROOT/'schemas/egress-binding.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','$id':'https://processforge.local/schemas/egress-binding.schema.json','title':'Explicit immutable egress binding',**binding})
p=ROOT/'schemas/execution-contract.schema.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['properties']['contract_version']={'enum':[1,2]}
d['properties']['egress']=copy.deepcopy(binding)
intent=d['$defs']['assignment_intent']
intent['properties']['egress']=copy.deepcopy(binding)
intent['properties']['egress_predecessor']=copy.deepcopy(predecessor)
d.pop('allOf',None)
v1_props={key:{} for key in d['properties'] if key!='egress'}
v1_props['contract_version']={'const':1}
v1_props['assignment_intent']={'properties':{key:{} for key in intent['properties'] if key not in {'egress','egress_predecessor'}},'additionalProperties':False}
d['oneOf']=[{'properties':v1_props,'additionalProperties':False},
            {'required':['egress'],'properties':{'contract_version':{'const':2},'assignment_intent':{'required':['egress']}}}]
save(p,d)
p=ROOT/'schemas/context-capsule.schema.json'
c=json.loads(p.read_text(encoding='utf-8'))
embedded=copy.deepcopy(d)
for key in ['$schema','$id','title']:
    embedded.pop(key,None)
def refs(value):
    if isinstance(value,dict):
        for key,item in value.items():
            if key=='$ref' and isinstance(item,str) and item.startswith('#/$defs/'):
                value[key]='#/$defs/execution_contract/$defs/'+item[len('#/$defs/'):]
            else:
                refs(item)
    elif isinstance(value,list):
        for item in value:
            refs(item)
refs(embedded)
c['$defs']['execution_contract']=embedded
save(p,c)
for name in ['assignment','assignment-front-matter']:
    p=ROOT/'schemas'/(name+'.schema.json')
    doc=json.loads(p.read_text(encoding='utf-8'))
    doc['properties']['egress']=copy.deepcopy(binding)
    doc['properties']['egress_predecessor']=copy.deepcopy(predecessor)
    save(p,doc)
save(Path(__file__).with_name('scope-amendment.json'),{'additional_patterns':['src/processforge_core/work_resource_material.py'],'reason':'Architecture-approved private store exclusion from broad registered resource roots; baseline unchanged.'})
print('PASS schema generation')
