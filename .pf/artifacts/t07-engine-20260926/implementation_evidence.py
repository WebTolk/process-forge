import ast, fnmatch, importlib.util
from work import *

baseline=json.loads((HERE/'baseline.json').read_text(encoding='utf-8'))
patterns=baseline['scope_patterns']+json.loads((HERE/'scope-amendment.json').read_text())['additional_patterns']
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/validate-process-forge-checksums.py')
inv=importlib.util.module_from_spec(spec);spec.loader.exec_module(inv)
files={p.relative_to(ROOT).as_posix():p for p in inv.public_files(ROOT)+[ROOT/'checksums/processforge.sha256']}
changed=sorted(n for n,p in files.items() if baseline['public_sha256'].get(n)!=sha(p))
assert not(set(baseline['public_sha256'])-set(files))
assert all(any(fnmatch.fnmatchcase(n,p) for p in patterns) for n in changed),changed
for name in changed:
    if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
save('implementation-files.json',{'files':changed,'sha256':{n:sha(files[n]) for n in changed},'scope':'baseline plus architecture-approved material exclusion','ast':'passed'})
(HERE/'implementation.md').write_text('''# T07 implementation completed for assurance

New provider-neutral Core egress package provides trusted policy/binding,
bounded whole-unit classification, actual Windows owner-only ACL and source
handles, persistent reservations/revocations/mandatory audit, immutable views,
one-shot tokens, broker reads/tools/results/export and exact HTTP/JSON transport.
v2 is explicit before capsule sealing; old v1 paths remain unchanged. Native
preparation rejects strict contexts before copying raw material. General Work
material excludes the reserved private store. CLI and bilingual docs supplied.

Focused implementation checks: engine34, actual Work9 and TLS/transport8 passed
at the revisions recorded in tool execution; assurance reruns the final source
and adds independent compatibility, failure and historical-original review.
Actual crash, Windows junction and independent recipient capture were exercised.
Initial self-review found and fixed ambient TLS key logging/trust-file use,
exception expiry after preparation, and trusted-tool/result metadata gaps.

The first supported route is managed HTTP/JSON on Windows, requiring explicit
local qualification. Source success does not prove installed or connected-host
acceptance. Native Codex/generic-shell and isolated-local remain unsupported.
No local model/external credentials/real project secrets were sent. No source
main-branch commit, update apply or original capsule rewrite was performed.

Scope and AST evidence: implementation-files.json. Qualification scripts and
fixtures are public source; temporary fixtures stay in OS temp or .pf/tmp.
Shared material exclusion was authorized in architecture and scope amendment.
Next: code-assurance, bounded release candidate, standard Core update, connected
installed-broker acceptance, delivery/evolve closeout.
''',encoding='utf-8')
print('PASS scope and AST',len(changed),'files',flush=True)
