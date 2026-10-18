"""Fresh installed stdio connection resumes the Work created by the actual host."""
import datetime
import json
import subprocess
import sys
from pathlib import Path

out = Path(__file__).resolve().parent
root = out.parents[2]
project = root / '.pf/tmp/t08-host-acceptance-20260925/project'
expected = 'garage-t08-real-host-acceptance-verify-selected-resource-authorization-r'
objective = 'T08 real host acceptance: verify selected resource authorization, required evidence and continuation through a fresh installed stdio connection.'
requests = [
    {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'},
    {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'pf.work.start', 'arguments': {'project_root': str(project), 'objective': objective}}},
    {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'pf.work.state', 'arguments': {'project_root': str(project)}}},
]
argv = [sys.executable, '-B', 'D:/.agents/processforge/tools/pf_runtime/mcp_server.py', '--workplace', 'D:/.agents/processforge-workplace']
r = subprocess.run(argv, cwd=root, text=True, encoding='utf-8', input='\n'.join(json.dumps(v) for v in requests) + '\n', capture_output=True, timeout=120)
responses = [json.loads(line) for line in r.stdout.splitlines() if line.strip()]
evidence = {'time_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'layer': 'fresh installed stdio connection, separate from actual host calls', 'argv': argv, 'requests': requests, 'responses': responses, 'exit_code': r.returncode, 'stderr': r.stderr}
(out / 'reconnect-proof.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
assert r.returncode == 0 and r.stderr == ''
assert [v['id'] for v in responses] == [1, 2, 3]
resume, state = [json.loads(v['result']['content'][0]['text']) for v in responses[1:]]
assert resume['run_id'] == state['run']['id'] == expected
assert resume['action'] != 'created_new'
assert state['stage']['id'] == 'finish'
assert state['required_inputs'][0]['satisfied'] is True
print(json.dumps({'status': 'PASS', 'action': resume['action'], 'run_id': expected, 'stage': 'finish', 'notification_silent': True, 'stdout_protocol_only': True}))
