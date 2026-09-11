from pathlib import Path
import hashlib
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
if len(sys.argv) > 1:
    dist = Path(sys.argv[1])
    sys.path.insert(0, str(dist / 'tools'))
    import processforge as core
    workplace = Path(sys.argv[2])
    paths = core.project_classifier_paths(workplace, ROOT)
    print(json.dumps({'core_root': str(core.ROOT),
        'classification': core.classify_project(ROOT, workplace),
        'classifiers': [{'path': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]}, indent=2))
else:
    workplace = ROOT / '.pf/process-forge.local.yaml'
    import yaml
    manifest = yaml.safe_load(workplace.read_text(encoding='utf-8'))['workplace']['manifest']
    installed = Path(manifest).parent.parent / 'processforge'
    rows = {}
    for key, dist in [('source', ROOT), ('installed', installed)]:
        value = subprocess.run([sys.executable, __file__, str(dist), manifest], capture_output=True, text=True, check=True, timeout=60)
        rows[key] = json.loads(value.stdout)
    rows['classification_equal'] = rows['source']['classification'] == rows['installed']['classification']
    print(json.dumps(rows, indent=2))
