"""Check whether collision protection preserves owned file-to-directory updates."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
import smoke_core_update_manifest as fixture
from processforge_core import core_update
source=subprocess.check_output(['git','show','1aecc18b6824204ca45ab30241b92d26e6d583a5:src/processforge_core/core_update.py'],cwd=ROOT)
old=types.ModuleType('f0102_baseline_updater')
sys.modules[old.__name__]=old
exec(compile(source,'baseline_core_update.py','exec'),old.__dict__)
rows=[]
for name,module in [('baseline',old),('current',core_update)]:
    with tempfile.TemporaryDirectory(prefix='pf-owned-ancestor-') as raw:
        root=Path(raw); core=root/'core'; core.mkdir()
        fixture.install_old_core(core)
        archive=root/'candidate.zip'
        fixture.write_archive(archive,{'a.txt/child.txt':'new child','dir/b.txt':'old-b','dir/c.txt':'same-c'})
        plan=module.build_plan(core,archive)
        try:
            applied=module.apply_update(core,archive,confirm=True)
            outcome=applied['status']
        except module.CoreUpdateError as exc:
            outcome=exc.code
        rows.append(dict(version=name,plan=plan['status'],blockers=plan['blockers'],outcome=outcome,child_exists=(core/'a.txt/child.txt').is_file()))
out=Path(__file__).with_name('owned_ancestor_probe-final.json') if len(sys.argv)>1 else Path(__file__).with_suffix('.json')
out.write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print(json.dumps(rows))
