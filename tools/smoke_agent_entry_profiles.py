"""Paired diagnostic fixtures; these are not native-client or model acceptance."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from processforge_core.agent_entry import BOM, EntryError, digest, encoded, load_contract
from processforge_core.agent_entry_migration import manifest
from processforge_core.agent_entry_profiles import diagnose_entry, load_profiles, observations

spec = importlib.util.spec_from_file_location('schema_check', ROOT/'tools/validate-process-forge-schemas.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
SCHEMA = json.loads((ROOT/'schemas/agent-entry-diagnostics.schema.json').read_text(encoding='utf-8'))
CONTRACT = load_contract()
PROFILES = load_profiles()
COUNT = 0


def check(value):
    global COUNT
    errors = validator.validate_instance(value, SCHEMA, SCHEMA, '$')
    assert not errors, errors
    COUNT += 1
    return value


def observed(profile='P-CODEX', **changes):
    p = next(x for x in PROFILES['profiles'] if x['id'] == profile)
    obs = dict(schema_version=1, profile_version=p['version'], client_revision=p['client_revision'],
               settings_source='explicit', injection='enabled', trusted=True, boundary_complete=True,
               single_environment=True, root_markers=['.git'], fallback_names=[], limit=32768)
    obs.update(changes)
    check(obs)
    return obs


def fixture(base):
    root = base/'project'
    (root/'.pf').mkdir(parents=True)
    (root/'.git').mkdir()
    (root/'sub/deep').mkdir(parents=True)
    (root/'AGENTS.md').write_bytes(CONTRACT.raw)
    (root/'.pf/AGENTS.md').write_bytes(CONTRACT.render(extended=True))
    (root/'.pf/agent-entry.json').write_bytes(encoded(manifest(CONTRACT)))
    return root


def diag(root, obs=None, profile='P-CODEX', cwd='.'):
    result = check(diagnose_entry(root, profile_id=profile, observation=obs, cwd=cwd))
    assert result['verdicts']['delivery']['status'] != 'verified'
    assert result['verdicts']['behavior']['status'] == 'unverified'
    assert result['verdicts']['enforcement']['status'] == 'not_applicable'
    assert str(root) not in json.dumps(result) and 'PRIVATE_SENTINEL' not in json.dumps(result)
    return result


def tree(root):
    return {p.relative_to(root).as_posix(): (digest(p.read_bytes()), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


def reject(call):
    try:
        call()
    except EntryError:
        return
    raise AssertionError('invalid input accepted')


def discovery(root):
    result = diag(root, observed(), cwd='sub/deep')
    assert result['verdicts']['file_consistency']['status'] == 'verified'
    assert result['verdicts']['discovery']['status'] == 'conditional'
    assert result['budget_observations'][0]['contract_complete'] is True
    assert diag(root)['verdicts']['discovery']['status'] == 'unverified'
    for change in ({'client_revision':'unknown'}, {'profile_version':'2.0.0'}, {'single_environment':False},
                   {'boundary_complete':False}, {'limit':None}, {'settings_source':'default'}, {'accounting_phase':'unknown'}):
        r=diag(root, observed(**change))
        assert r['verdicts']['discovery']['status'] == 'unverified'
        assert r['budget_observations'][0]['contract_complete'] is None
    for raw in (b'', b'PRIVATE_SENTINEL\n'):
        (root/'AGENTS.override.md').write_bytes(raw)
        r=diag(root, observed())
        assert 'entry_contract_not_selected' in r['blockers']
        assert 'override_selected' in r['verdicts']['discovery']['reasons']
        assert [x['path'] for x in r['budget_observations'][0]['selected_inputs']] == ['AGENTS.override.md']
    (root/'AGENTS.override.md').unlink()
    (root/'.git').rmdir()
    r=diag(root, observed(), cwd='sub')
    assert 'no_marker_cwd_only' in r['verdicts']['discovery']['reasons']
    assert 'entry_contract_not_selected' in r['blockers']
    (root/'.git').mkdir()
    (root/'sub/.git').write_bytes(b'gitdir: PRIVATE_SENTINEL')
    r=diag(root, observed(), cwd='sub/deep')
    assert 'nested_project_boundary' in r['verdicts']['discovery']['reasons']
    assert 'entry_contract_not_selected' in r['blockers']
    (root/'sub/.git').unlink()
    for change, reason in [({'injection':'disabled'},'instruction_injection_disabled'),
                           ({'trusted':False},'project_untrusted'), ({'limit':0},'project_instruction_budget_zero')]:
        assert reason in diag(root, observed(**change))['blockers']
    assert 'unsupported_profile' in diag(root, profile='UNSUPPORTED_PRIVATE_SENTINEL')['blockers']


def budgets(root):
    for size in (32767,32768,32769):
        (root/'AGENTS.md').write_bytes(b'x'*(size-len(CONTRACT.raw)-1)+b'\n'+CONTRACT.raw)
        r=diag(root, observed())['budget_observations'][0]
        assert r['raw_size'] == size
        assert r['contract_complete'] == (size <= 32768)
    raw=BOM+'Привет🙂\r\n'.encode()+CONTRACT.raw.replace(b'\n',b'\r\n')
    (root/'AGENTS.md').write_bytes(raw)
    r=diag(root, observed(limit=len(raw)))
    assert r['budget_observations'][0]['contract_complete'] is True
    assert r['files'][0]['k_normalized_sha256'] == CONTRACT.sha256
    assert r['files'][0]['k_raw_sha256'] != CONTRACT.sha256
    assert 'entry_contract_would_truncate' in diag(root,observed(limit=len(raw)-1))['blockers']
    (root/'AGENTS.md').write_bytes(CONTRACT.raw+'🙂PRIVATE_SENTINEL'.encode())
    r=diag(root,observed(limit=len(CONTRACT.raw)+1))
    assert r['budget_observations'][0]['contract_complete'] is True
    assert r['budget_observations'][0]['required_instructions_complete'] is False
    assert 'required_instructions_would_truncate' in r['blockers']
    (root/'AGENTS.md').write_bytes(CONTRACT.raw+b'x'*(20000-len(CONTRACT.raw)))
    (root/'sub/AGENTS.md').write_bytes(b'x'*20000)
    r=diag(root,observed(),cwd='sub')
    assert r['budget_observations'][0]['raw_size']==40000
    assert 'required_instructions_would_truncate' in r['blockers']
    (root/'sub/AGENTS.md').write_bytes(CONTRACT.raw)
    (root/'AGENTS.md').write_bytes(b' '*40000)
    r=diag(root,observed(),cwd='sub')
    assert r['budget_observations'][0]['contract_complete'] is True, r
    (root/'sub/AGENTS.md').unlink()
    (root/'AGENTS.md').write_bytes(CONTRACT.raw)
    (root/'extra.md').write_bytes('🙂'.encode()*20000)
    obs=observed('P-KIMI',selection=['AGENTS.md','extra.md','AGENTS.md'],accounting_phase='expanded_render')
    r=diag(root,obs,profile='P-KIMI')['budget_observations'][0]
    assert 'rendered_budget_lower_bound_exceeded' in r['warnings']
    assert r['raw_size'] == len(CONTRACT.raw)+80000
    assert r['expanded_size'] is None and r['status']=='budget_unverified'
    (root/'spaces.md').write_bytes(BOM+b' '*40000)
    spaces=observed('P-KIMI',selection=['spaces.md'],accounting_phase='expanded_render')
    r=diag(root,spaces,profile='P-KIMI')['budget_observations'][0]
    assert r['warnings']==[] and r['rendered_lower_bound']==0
    obs=observed('P-OPENCLAW-EMBEDDED',selection=['AGENTS.md','extra.md'],limit=60000,
                 file_limit=20000,workspace_matches=True,context_mode='full')
    r=diag(root,obs,profile='P-OPENCLAW-EMBEDDED')['budget_observations'][0]
    assert r['native_total']==len(CONTRACT.raw.decode())+40000
    assert r['warnings']==['raw_bootstrap_file_budget_exceeded']
    obs.update(limit=20000,file_limit=100000)
    r=diag(root,obs,profile='P-OPENCLAW-EMBEDDED')['budget_observations'][0]
    assert r['warnings']==['raw_bootstrap_total_budget_exceeded'] and r['contract_complete'] is None
    obs.update(workspace_matches=False)
    assert 'workspace_mismatch' in diag(root,obs,profile='P-OPENCLAW-EMBEDDED')['blockers']
    obs=observed('P-AIDER',selection=['AGENTS.md'],explicit_read=False)
    assert 'explicit_read_required' in diag(root,obs,profile='P-AIDER')['blockers']


def context_and_inputs(root):
    ctx=dict(mcp='available',cli='available',status='fresh',policy_action='continue',identity='matched',
             required_resources='available',health='warn')
    assert diag(root,observed(context=ctx))['verdicts']['runtime_context']['status']=='conditional'
    ctx.update(mcp='unavailable')
    assert 'existing_cli_fallback' in diag(root,observed(context=ctx))['verdicts']['runtime_context']['reasons']
    for key,value,reason in [('cli','unavailable','context_verifier_unavailable'),('status','stale','context_stale'),
                             ('status','broken','context_broken'),('identity','mismatch','work_identity_mismatch'),
                             ('required_resources','denied','required_resource_denied')]:
        other=dict(ctx,**{key:value})
        assert reason in diag(root,observed(context=other))['blockers']
    for invalid in ({'schema_version':2},{'schema_version':True},{'schema_version':1,'limit':True},
                    {'schema_version':1,'limit':-1},{'schema_version':1,'limit':2**41},
                    {'schema_version':1,'selection':['../escape']},{'schema_version':1,'selection':['C:/secret']},
                    {'schema_version':1,'root_markers':['nested/path']},{'schema_version':1,'unknown':'PRIVATE_SENTINEL'},
                    {'schema_version':1,'context':{'status':'PRIVATE_SENTINEL'}}, {'schema_version':1,'trusted':1}):
        reject(lambda: observations(invalid))
    assert 'observation_path_invalid' in diag(root,observed(),cwd='../secret')['blockers']
    (root/'AGENTS.md').write_bytes(CONTRACT.raw.replace(b'ProcessForge',b'PrivateForge',1))
    assert 'managed_content_changed' in diag(root,observed())['blockers']
    (root/'AGENTS.md').write_bytes(CONTRACT.raw)
    for version in (2,True,1.0):
        (root/'.pf/agent-entry.json').write_bytes(encoded(dict(manifest(CONTRACT),schema_version=version)))
        assert 'entry_manifest_mismatch' in diag(root,observed())['blockers']
    (root/'.pf/agent-entry.json').write_bytes(encoded(manifest(CONTRACT)))


def cli_readonly(root):
    config=root/'observed.json'
    config.write_bytes(encoded(observed()))
    baseline=tree(root)
    cases=[(['profiles'],0),(['diagnose','--project-root',str(root),'--profile','P-CODEX','--observations-file',str(config)],0),
           (['diagnose','--project-root',str(root),'--profile','PRIVATE_SENTINEL'],1),
           (['diagnose','--project-root',str(root),'--profile','P-CODEX','--cwd','../secret'],1)]
    for args,code in cases:
        result=subprocess.run([sys.executable,'-B',str(ROOT/'bin/pf.py'),'agent-entry',*args],cwd=ROOT,
                              capture_output=True,text=True,encoding='utf-8',timeout=30)
        assert result.returncode==code,result.stdout+result.stderr
        check(json.loads(result.stdout))
        assert tree(root)==baseline, 'read-only command wrote to fixture'
        assert 'PRIVATE_SENTINEL' not in result.stdout and str(root) not in result.stdout
    config.write_text('{"schema_version":1,"schema_version":2}',encoding='utf-8')
    baseline=tree(root)
    result=subprocess.run([sys.executable,'-B',str(ROOT/'bin/pf.py'),'agent-entry','diagnose','--project-root',str(root),
                           '--profile','P-CODEX','--observations-file',str(config)],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==1 and json.loads(result.stdout)['reason']=='duplicate_json_key'
    assert tree(root)==baseline


def main():
    check(PROFILES)
    with tempfile.TemporaryDirectory(prefix='pf-entry-profiles-') as temp:
        root=fixture(Path(temp))
        discovery(root)
        budgets(root)
        context_and_inputs(root)
        cli_readonly(root)
        for profile in PROFILES['profiles']:
            diag(root,profile=profile['id'])
        source=Path(temp)/'registry-source'
        (source/'templates').mkdir(parents=True)
        invalid=copy.deepcopy(PROFILES)
        invalid['profiles'][0]['proof_refs'][0]['level']=[]
        (source/'templates/agent-entry-profiles.json').write_bytes(encoded(invalid))
        reject(lambda:load_profiles(source))
        invalid=copy.deepcopy(PROFILES)
        invalid['profiles'][0]['unit']='utf16_code_units'
        (source/'templates/agent-entry-profiles.json').write_bytes(encoded(invalid))
        reject(lambda:load_profiles(source))
    print(json.dumps({'status':'passed','schema_checked_cases':COUNT,'native_client_delivery':'not_run',
                      'model_behavior':'not_run','enforcement':'not_applicable'}))


if __name__=='__main__':
    main()
