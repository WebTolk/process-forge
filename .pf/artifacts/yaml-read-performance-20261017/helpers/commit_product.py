"""Commit only qualified task paths, then prove the isolated tree is identical."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
CANDIDATE = TASK / 'candidate'
paths = json.loads((TASK / 'product-paths.json').read_text())

def git(arguments, root=ROOT):
    return subprocess.check_output(['git'] + arguments, cwd=root, text=True, encoding='utf-8').strip()

assert not git(['diff', '--cached', '--name-only']), 'Unrelated staged state; do not replace it'
git(['add', '--'] + paths)
staged = set(git(['diff', '--cached', '--name-only']).splitlines())
assert staged == set(paths), staged
git(['diff', '--cached', '--check'])
print(git(['commit', '-m', 'Reuse safe YAML parsing across requests and project Run discovery']), flush=True)
sha = git(['rev-parse', 'HEAD'])
git(['add', '--'] + paths, CANDIDATE)
git(['diff', '--cached', '--exit-code', sha], CANDIDATE)
# Only the detached candidate's HEAD moves. Its index/tree already equal sha.
git(['reset', '--soft', sha], CANDIDATE)
assert not git(['status', '--porcelain'], CANDIDATE), 'Candidate not clean'
(TASK / 'source-commit.json').write_text(json.dumps({'sha': sha, 'paths': paths, 'clean_candidate_exact_tree': True}, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'sha': sha, 'clean_candidate_exact_tree': True}), flush=True)
