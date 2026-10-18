import ast
import copy
import importlib.util
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[3]
base = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('t02_schema_validator', root / 'tools/validate-process-forge-schemas.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
schema = json.loads((root / 'schemas/resource-bindings.schema.json').read_text(encoding='utf-8'))
capsule_schema = json.loads((root / 'schemas/context-capsule.schema.json').read_text(encoding='utf-8'))
embedded = copy.deepcopy(capsule_schema['$defs']['resource_bindings'])
def normalize(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == '$ref':
                value[key] = item.replace('#/$defs/resource_bindings/$defs/', '#/$defs/')
            else:
                normalize(item)
    elif isinstance(value, list):
        for item in value:
            normalize(item)
normalize(embedded)
expected = {key: value for key, value in schema.items() if key not in ('$schema', '$id', 'title')}
assert embedded == expected
probe = json.loads((base / 'developer-probe.json').read_text(encoding='utf-8'))
binding = {key: value for key, value in probe['resolve']['resource'].items() if key not in ('local_root', 'navigation', 'resource_provenance')}
valid = {'schema_version': 1, 'status': 'available', 'resources': [binding]}
assert not validator.validate_instance(valid, schema, schema, '$')
for field in ('generation', 'material_fingerprint', 'metadata_fingerprint', 'reference', 'manifest'):
    invalid = copy.deepcopy(valid)
    del invalid['resources'][0][field]
    assert validator.validate_instance(invalid, schema, schema, '$'), field
docs = ['docs/concepts/work-resources.md', 'docs/ru/concepts/work-resources.md',
        'docs/concepts/work-execution-contract.md', 'docs/concepts/runtime-mcp.md', 'docs/ru/concepts/runtime-mcp.md']
for name in docs:
    path = root / name
    text = path.read_text(encoding='utf-8')
    assert all(line == line.rstrip() for line in text.splitlines()), name
    for link in re.findall(r'\]\(([^)]+)\)', text):
        if not link.startswith(('http:', 'https:', '#')):
            assert (path.parent / link.split('#')[0]).exists(), (name, link)
sources = ['src/processforge_core/work_resources.py', 'src/processforge_core/work_resource_material.py',
           'src/processforge_core/process_execution.py', 'src/processforge_core/local_resource_search.py',
           'src/processforge_core/garage.py', 'tools/processforge.py', 'tools/pf_runtime/mcp_server.py']
for name in sources:
    ast.parse((root / name).read_text(encoding='utf-8'), filename=name)
report = {'binding_schema_equivalence': 'PASS', 'binding_required_fields_positive_negative': 'PASS',
          'document_links_whitespace': 'PASS', 'documents': len(docs), 'python_syntax': 'PASS', 'python_files': len(sources)}
(base / 'delivery-verification.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
