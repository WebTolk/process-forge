import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import processforge as core
from processforge_core.prepared_input import private_file

result={}
with tempfile.TemporaryDirectory(prefix='pf-t05-path-') as raw:
    project=Path(raw).resolve()
    agent=project/'.pf/runtime/agent-runs/path-run/path-task'
    target=project/'.pf/artifacts/public-fixture'
    agent.mkdir(parents=True)
    target.mkdir(parents=True)
    link=agent/'attempts'
    if os.name=='nt':
        quoted=lambda s: "'"+str(s).replace("'","''")+"'"
        command='New-Item -ItemType Junction -Path '+quoted(link)+' -Target '+quoted(target)+' | Out-Null'
        run=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=15)
        assert run.returncode==0,run.stderr
    else:
        link.symlink_to(target,target_is_directory=True)
    try:
        private_file(project,'.pf/runtime/agent-runs/path-run/path-task/attempts/1/prepared-input.json')
    except ValueError as exc:
        result['in_project_directory_redirect_denied']=str(exc)
    else:
        raise AssertionError('private manifest redirect accepted')
    assert list(target.iterdir())==[]
    result['no_private_bytes_written']=True
    # Both link and target are isolated under this verified temporary root.
    assert link.parent.resolve().is_relative_to(project) and target.resolve().is_relative_to(project)
    if os.name=='nt':
        link.rmdir()
    else:
        link.unlink()
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
