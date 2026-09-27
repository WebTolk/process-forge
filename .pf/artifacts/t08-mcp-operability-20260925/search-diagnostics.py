"""Read-only comparison of project authorization with the Workplace catalogue."""
import json
import sqlite3
import sys
from pathlib import Path
import yaml

installed = Path('D:/.agents/processforge')
sys.path[:0] = [str(installed / 'src'), str(installed / 'tools')]
import processforge as core
from processforge_core.garage import snapshot_with_resolved_search_roots
from processforge_core.local_resource_search import authorized_roots, indexable_resource_ids, index_path
out = Path(__file__).resolve().parent
root = out.parents[2]
workplace = Path('D:/.agents/processforge-workplace')
catalogue = core.workplace_search_runtime_snapshot(workplace)
rows = [{'id': r.resource_id, 'package': r.package_id, 'root': str(r.root), 'title': r.title} for r in authorized_roots(workplace, catalogue)]
result = {'catalogue': rows, 'projects': {}}
for label, project in [('main', root), ('fixture', root / '.pf/tmp/t08-host-acceptance-20260925/project')]:
    snapshot = yaml.safe_load((project / '.pf/contexts/project-context.snapshot.yaml').read_text(encoding='utf-8'))
    runtime = snapshot_with_resolved_search_roots(project, snapshot, workplace, core)
    selected = indexable_resource_ids(authorized_roots(project, runtime))
    result['projects'][label] = {'selected_ids': [r.get('id') for r in snapshot['local_search_resources']], 'resolved_indexable_ids': selected, 'catalogue_intersection': sorted(set(selected) & {r['id'] for r in rows})}
with sqlite3.connect(index_path(root, workplace).as_uri() + '?mode=ro', uri=True) as db:
    result['indexed_resource_ids'] = [r[0] for r in db.execute('select distinct resource_id from documents order by resource_id')]
(out / 'search-catalogue-diagnosis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'projects': result['projects'], 'catalogue_sample': rows[:12]}, ensure_ascii=False, indent=2))
