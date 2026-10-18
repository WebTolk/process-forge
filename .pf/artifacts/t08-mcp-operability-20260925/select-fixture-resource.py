"""Select an existing, resolvable catalog resource through ordinary refresh."""
import json
import sys
from pathlib import Path
import yaml

installed = Path('D:/.agents/processforge')
sys.path.insert(0, str(installed / 'tools'))
from garage_search_smoke_support import select_fixture_resource
out = Path(__file__).resolve().parent
project = out.parents[2] / '.pf/tmp/t08-host-acceptance-20260925/project'
path = project / '.pf/process-forge.yaml'
manifest = yaml.safe_load(path.read_text(encoding='utf-8'))
manifest['context_requirements']['templates'] = []
path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding='utf-8')
select_fixture_resource(project, Path('D:/.agents/processforge-workplace'), 'docs.api.gitverse', 'root')
snapshot = yaml.safe_load((project / '.pf/contexts/project-context.snapshot.yaml').read_text(encoding='utf-8'))
result = {'reason': 'Existing php.class-doc-block template registry target is unresolved; no shared registry repair in T08. Use existing indexed docs.api.gitverse:root metadata.', 'selected': snapshot['local_search_resources'], 'snapshot': snapshot['snapshot']}
(out / 'fixture-resource-selection.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'snapshot': snapshot['snapshot']['id'], 'resource_ids': [r['id'] for r in snapshot['local_search_resources']]}))
