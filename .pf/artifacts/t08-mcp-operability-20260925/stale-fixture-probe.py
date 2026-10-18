"""Change and restore only the isolated fixture manifest to test real stale guards."""
import hashlib
import json
import sys
from pathlib import Path
import yaml

out = Path(__file__).resolve().parent
fixture = out.parents[2] / '.pf/tmp/t08-host-acceptance-20260925'
manifest = fixture / 'project/.pf/process-forge.yaml'
backup = fixture / 'manifest.before-stale.yaml'
if sys.argv[1] == 'change':
    assert not backup.exists()
    original = manifest.read_bytes()
    backup.write_bytes(original)
    data = yaml.safe_load(original.decode('utf-8'))
    data['project']['description'] = 'Controlled genuine manifest drift for T08 stale guard acceptance.'
    manifest.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')
    (out / 'stale-fixture-mutation.json').write_text(json.dumps({'scope': 'isolated completed acceptance fixture only', 'original_sha256': hashlib.sha256(original).hexdigest(), 'changed_sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()}, indent=2) + '\n', encoding='utf-8')
    print('Changed isolated fixture manifest; snapshot not refreshed.')
elif sys.argv[1] == 'restore':
    original = backup.read_bytes()
    manifest.write_bytes(original)
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == json.loads((out / 'stale-fixture-mutation.json').read_text(encoding='utf-8'))['original_sha256']
    print('Restored exact original manifest bytes; snapshot not refreshed.')
else:
    raise SystemExit('Expected change or restore')
