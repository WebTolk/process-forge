import argparse
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('archive',type=Path);a=p.parse_args()
out=Path(__file__).resolve().parent
tests=['smoke_core_update_missing_owned','smoke_search_source_integrity','smoke_raw_ingress_incremental_recovery','smoke_central_event_ingress_kernel']
with tempfile.TemporaryDirectory(prefix='pf-f0912-public-') as raw:
    root=Path(raw)
    with zipfile.ZipFile(a.archive) as z:z.extractall(root)
    result=subprocess.run([sys.executable,str(out/'checks.py'),'--root',str(root),'--label','extracted-focused','--tests',*tests],text=True)
    assert result.returncode==0,'extracted focused regression failed'
print('RESULT: PASS (extracted focused regressions)',flush=True)
