"""Publish one exact dev SHA to both remotes without interactive auth."""
import base64
import concurrent.futures
import json
import os
import pathlib
import re
import subprocess
from urllib.parse import urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[3]
SHA = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
TOKEN = os.environ.get('GITVERSE_TOKEN', '')
assert TOKEN, 'GITVERSE_TOKEN is unavailable; never start a browser'
url = subprocess.check_output(['git', 'remote', 'get-url', 'gitverse'], cwd=ROOT, text=True).strip()
parsed = urlsplit(url)
assert parsed.scheme == 'https' and parsed.hostname == 'gitverse.ru'
username = parsed.username or parsed.path.strip('/').split('/')[0]
basic = base64.b64encode((username + ':' + TOKEN).encode()).decode()


def environment(remote):
    env = os.environ.copy()
    for key in tuple(env):
        if key.startswith('GIT_TRACE') or key == 'GIT_CURL_VERBOSE':
            env.pop(key, None)
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['GCM_INTERACTIVE'] = 'Never'
    if remote == 'gitverse':
        count = int(env.get('GIT_CONFIG_COUNT', '0'))
        env['GIT_CONFIG_COUNT'] = str(count + 1)
        env['GIT_CONFIG_KEY_' + str(count)] = 'http.https://gitverse.ru/.extraheader'
        env['GIT_CONFIG_VALUE_' + str(count)] = 'Authorization: Basic ' + basic
    return env


def safe(value):
    value = value.replace(TOKEN, '[REDACTED]').replace(basic, '[REDACTED]')
    value = re.sub(r'https://[^/@\s]+@', 'https://[REDACTED]@', value)
    value = re.sub(r'(?im)^.*(?:authorization|cookie):.*$', '[REDACTED header]', value)
    return value


def git(remote, operation):
    command = ['git'] + (['-c', 'credential.helper='] if remote == 'gitverse' else [])
    result = subprocess.run(command + operation, cwd=ROOT, env=environment(remote), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    return {'returncode': result.returncode, 'stdout': safe(result.stdout), 'stderr': safe(result.stderr)}


with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    pushes = dict(zip(['origin', 'gitverse'], pool.map(lambda remote: git(remote, ['push', remote, SHA + ':refs/heads/dev']), ['origin', 'gitverse'])))
print(json.dumps({'sha': SHA, 'pushes': pushes}), flush=True)
assert all(row['returncode'] == 0 for row in pushes.values()), 'Missing remote publication; repeat only the missing push with the same SHA'
readback = {}
for remote in ['origin', 'gitverse']:
    result = git(remote, ['ls-remote', remote, 'refs/heads/dev'])
    assert result['returncode'] == 0, result
    observed = result['stdout'].split()[0]
    readback[remote] = observed
    assert observed == SHA, (remote, observed, SHA)
proof = {'sha': SHA, 'readback': readback, 'all_equal': True, 'gitverse_auth': 'token via child environment; no browser'}
(pathlib.Path(__file__).resolve().parent / 'publication-proof.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
print(json.dumps(proof), flush=True)
