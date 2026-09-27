"""Run isolated installed-Core checks and retain exact output for T08."""
import datetime
import json
import subprocess
import sys
import time
from pathlib import Path

core = Path('D:/.agents/processforge')
out = Path(__file__).resolve().parent
checks = []
for name in ['smoke_classifier_distribution_parity', 'smoke_mcp_jsonrpc_validation', 'smoke_mcp_missing_session_diagnostics', 'smoke_project_init_local_search_mcp', 'smoke_garage_mode_not_promoted_by_session', 'smoke_garage_no_hooks_sessionless']:
    started = time.monotonic()
    r = subprocess.run([sys.executable, '-B', str(core / 'tools' / (name + '.py'))], cwd=core, text=True, encoding='utf-8', capture_output=True, timeout=180)
    checks.append({'name': name, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit_code': r.returncode, 'seconds': round(time.monotonic() - started, 3), 'stdout': r.stdout, 'stderr': r.stderr})
    (out / 'installed-regressions-after-restart.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{name}: {r.returncode}', flush=True)
    if r.returncode:
        raise SystemExit(r.returncode)
