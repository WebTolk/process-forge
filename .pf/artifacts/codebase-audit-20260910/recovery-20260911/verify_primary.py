"""Disposable primary audit probes; never touches installed Runtime state."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from smoke_garage_session_enhanced import cli


def invoke(workplace, requests):
    result = subprocess.run(
        [sys.executable, str(ROOT / 'tools/pf_runtime/mcp_server.py'), '--workplace', str(workplace)],
        input=''.join(json.dumps(row) + '\n' for row in requests),
        text=True, encoding='utf-8', capture_output=True, timeout=90,
    )
    if result.returncode:
        raise AssertionError(result.stderr)
    return [json.loads(line) for line in result.stdout.splitlines() if line.strip()]


def main():
    started = time.time()
    with tempfile.TemporaryDirectory(prefix='pf-primary-mcp-audit-') as raw:
        temp = Path(raw)
        workplace, project = temp / 'workplace', temp / 'project'
        cli('workplace-init', '--workplace', str(workplace), '--apply')
        cli('project-onboard', '--project-root', str(project), '--workplace', str(workplace), '--type', 'generic', '--apply')
        cases = {}
        for session in ('lower-session', 'Case-Session'):
            checked = cli('agent-checkin', '--workplace', str(workplace), '--agent', 'fixture-agent', '--session', session, '--project-root', str(project))
            response = invoke(workplace, [{'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'pf.session_context', 'arguments': {'session_id': session, 'project_root': str(project)}}}])
            cases[session] = {'checkin_exit': checked.returncode, 'response': response}
        malformed = {
            'notification': {'jsonrpc': '2.0', 'method': 'tools/list'},
            'bad_version': {'jsonrpc': '1.0', 'id': 2, 'method': 'initialize'},
            'bad_arguments': {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'pf.context', 'arguments': []}},
            'bad_params': {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': []},
        }
        cases['protocol'] = {key: invoke(workplace, [request]) for key, request in malformed.items()}
        cases['seconds'] = round(time.time() - started, 2)
        (OUT / 'mcp-primary-results.json').write_text(json.dumps(cases, indent=2), encoding='utf-8')
        for key, value in cases.items():
            print(key, json.dumps(value)[:900], flush=True)
    for name in ('runtime_health', 'classification_origin'):
        result = subprocess.run([sys.executable, str(OUT.parent / ('probe_' + name + '.py'))], capture_output=True, text=True, encoding='utf-8', timeout=150)
        (OUT / (name + '.stdout.json')).write_text(result.stdout, encoding='utf-8')
        (OUT / (name + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        if result.returncode:
            raise AssertionError(result.stderr)
        print(name, 'recorded', flush=True)


if __name__ == '__main__':
    main()
