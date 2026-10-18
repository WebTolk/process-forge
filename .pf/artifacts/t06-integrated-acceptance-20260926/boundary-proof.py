from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
INSTALLED = Path('D:/.agents/processforge')
WORKPLACE = Path('D:/.agents/processforge-workplace')
RUN = 'garage-t06-pf-vision-alignment-r02-integrate-acceptance-for-work-resourc'
TASK = 't06-pf-vision-alignment-r02-integrate-acceptance-for-work-resources-norm'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None

protected = [ROOT / '.pf/assignments' / (TASK + '.yaml'),
             ROOT / '.pf/runs' / RUN / 'run.yaml',
             ROOT / '.pf/contexts/assignment-capsules' / (TASK + '.capsule.yaml'),
             ROOT / '.pf/contexts/project-context.snapshot.yaml',
             WORKPLACE / 'workplace.yaml', *sorted((WORKPLACE / 'registries').glob('*.yaml'))]
before = {str(path): digest(path) for path in protected}
result = {'time_utc': datetime.now(timezone.utc).isoformat(),
          'layer': 'read-only source/installed CLI and separate stdio connections; not host reconnection',
          'before': before, 'build_files': {}, 'cli': {}, 'mcp': {}}
for relative in ['VERSION', 'tools/pf_runtime/mcp_server.py', 'tools/pf_runtime/host.py',
                 'src/processforge_core/work_context.py', 'src/processforge_core/diagnostics.py']:
    result['build_files'][relative] = {'source': digest(ROOT / relative), 'installed': digest(INSTALLED / relative)}
for label, base in [('source', ROOT), ('installed', INSTALLED)]:
    cmd = [sys.executable, '-B', str(base / 'bin/pf.py'), 'work-state', '--project-root', str(ROOT),
           '--workplace', str(WORKPLACE), '--run', RUN, '--assignment', TASK, '--json']
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert proc.returncode == 0, (label, proc.stdout, proc.stderr)
    state = json.loads(proc.stdout)
    assert state['run']['id'] == RUN and state['assignment']['id'] == TASK, state
    assert state['stage']['id'] == 'code-assurance', state
    result['cli'][label] = {'argv': cmd, 'state': state, 'stderr': proc.stderr}
    requests = [{'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {
                    'name': 'pf.context', 'arguments': {'project_root': str(ROOT)}}},
                {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {
                    'name': 'pf.work.state', 'arguments': {'project_root': str(ROOT)}}}]
    argv = [sys.executable, '-B', str(base / 'tools/pf_runtime/mcp_server.py'), '--workplace', str(WORKPLACE)]
    proc = subprocess.run(argv, cwd=ROOT, input='\n'.join(json.dumps(row) for row in requests) + '\n',
                          capture_output=True, text=True, encoding='utf-8', timeout=120)
    assert proc.returncode == 0, (label, proc.stderr)
    responses = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    assert [row['id'] for row in responses] == [1, 2, 3, 4], responses
    assert all('error' not in row and not row['result'].get('isError') for row in responses), responses
    tools = [item['name'] for item in responses[1]['result']['tools']]
    context = json.loads(responses[2]['result']['content'][0]['text'])
    state = json.loads(responses[3]['result']['content'][0]['text'])
    assert context['context']['status'] == 'fresh', context
    assert state['run']['id'] == RUN and state['assignment']['id'] == TASK, state
    assert state['stage']['id'] == 'code-assurance', state
    result['mcp'][label] = {'argv': argv, 'tools': tools, 'context': context, 'state': state,
                            'stdout_jsonrpc_only': True, 'notification_silent': True,
                            'eof_exit': proc.returncode, 'stderr': proc.stderr}
result['after'] = {str(path): digest(path) for path in protected}
assert result['after'] == before, 'read-only boundary checks changed protected state/config'
result['missing_installed_tools'] = sorted(set(result['mcp']['source']['tools']) - set(result['mcp']['installed']['tools']))
assert {'pf.work.search', 'pf.work.resolve'}.issubset(result['missing_installed_tools']), result['missing_installed_tools']
(HERE / 'boundary-proof.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print('PASS: source/installed reconnect retain exact Work/stage and protected state; missing installed tools:', result['missing_installed_tools'])
