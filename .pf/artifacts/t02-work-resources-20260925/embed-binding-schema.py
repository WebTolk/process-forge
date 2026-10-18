import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
schema = json.loads((root / 'schemas/resource-bindings.schema.json').read_text(encoding='utf-8'))
for key in ('$schema', '$id', 'title'):
    schema.pop(key, None)
def local_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == '$ref' and item.startswith('#/$defs/'):
                value[key] = item.replace('#/$defs/', '#/$defs/resource_bindings/$defs/', 1)
            else:
                local_refs(item)
    elif isinstance(value, list):
        for item in value:
            local_refs(item)
local_refs(schema)
path = root / 'schemas/context-capsule.schema.json'
text = path.read_text(encoding='utf-8')
text = text.replace('"resource_bindings": { "$ref": "resource-bindings.schema.json" }', '"resource_bindings": { "$ref": "#/$defs/resource_bindings" }')
marker = '  "$defs": {\n'
def block_for(value):
    lines = json.dumps(value, ensure_ascii=False, indent=2).splitlines()
    return '    "resource_bindings": ' + lines[0] + '\n' + '\n'.join('    ' + line for line in lines[1:]) + ',\n'
block = block_for(schema)
old = json.loads(text).get('$defs', {}).get('resource_bindings')
if old is not None:
    old_block = block_for(old)
    assert old_block in text
    text = text.replace(old_block, block, 1)
else:
    assert marker in text
    text = text.replace(marker, marker + block, 1)
path.write_text(text, encoding='utf-8')
print('Embedded equivalent internal-ref resource binding schema; existing validator supports local refs only.')
