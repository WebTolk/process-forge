"""Startup preview/placement and context-reference qualification in isolated trees."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import processforge as core
from processforge_core.agent_entry import migration
from processforge_core.agent_entry import start_prompt as startup
from processforge_core.agent_entry.contract import BOM, EntryError, digest, encoded


def tree(root):
    return {p.relative_to(root).as_posix(): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file()}


def reject(reason, call):
    try:
        call()
    except EntryError as exc:
        assert exc.reason == reason, (reason, exc.reason)
    else:
        raise AssertionError('expected '+reason)


def cli(root, *args, ok=True):
    result = subprocess.run([sys.executable, '-B', str(ROOT/'bin/pf.py'), 'agent-start-prompt',
                             '--project-root', str(root), *args], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert (result.returncode == 0) == ok, result.stdout+result.stderr
    return result.stdout


def fixture(base, name):
    root = base/name
    (root/'.pf/contexts').mkdir(parents=True)
    (root/'.pf/process-forge.yaml').write_text('schema_version: 1\nproject:\n  id: fixture\n  type: generic\n', encoding='utf-8')
    (root/'.pf/AGENTS.md').write_text('Legacy fixture instructions\n', encoding='utf-8')
    (root/'.pf/contexts/old.capsule.yaml').write_bytes(b'IMMUTABLE CAPSULE\n')
    return root


def previews(base):
    generated, _, legacy = startup.load_start_source()
    old = legacy[0].format(project_id='fixture')
    for index,value in enumerate((None, generated, old, '# Custom START\nUSER DATA\n')):
        for count in (0,1,3):
            root = fixture(base,'preview-'+str(index)+'-'+str(count))
            target = root/'.pf/START_AGENT_HERE.md'
            if value is not None:
                target.write_text(value, encoding='utf-8')
            # If startup code enumerates these intentionally malformed records,
            # it has crossed from a static preview into Work selection.
            for number in range(count):
                folder=root/'.pf/runs'/('unselected-'+str(number))
                folder.mkdir(parents=True,exist_ok=True)
                (folder/'run.yaml').write_text('INVALID RUN: [',encoding='utf-8')
            before=tree(root)
            assert cli(root) == generated
            assert tree(root)==before, 'preview wrote files'
    with patch.object(core,'active_run_ids',side_effect=AssertionError('must not enumerate Runs')):
        assert core.default_start_agent_here(root)==generated
        assert core.start_agent_run_block(root)==startup.WORK_GUIDANCE
        assert core.refresh_start_agent_run_block(root,old)==generated
    reject('start_content_conflict',lambda:core.refresh_start_agent_run_block(root,'# user text'))
    for template in legacy:
        raw=template.format(project_id='fixture',run_id='selected-run',assignment_rel='.pf/assignments/first-assignment.yaml').encode()
        assert startup.project_start_content(raw,generated,legacy)[0]==generated.encode()
        assert startup.project_start_content(BOM+raw.replace(b'\n',b'\r\n'),generated,legacy)[0]==BOM+generated.encode()
        reject('start_content_conflict',lambda:startup.project_start_content(raw+b'CUSTOM SUFFIX\n',generated,legacy))
    raw=BOM+generated.replace('\n','\r\n').encode()
    assert startup.project_start_content(raw,generated,legacy)==(raw,'unchanged')


def placement(base):
    root=fixture(base,'placement')
    target=root/'.pf/START_AGENT_HERE.md'
    before=tree(root)
    plan=json.loads(cli(root,'--plan'))
    assert plan['kind']=='pf.agent-start-prompt.plan'
    assert tree(root)==before
    reject('explicit_apply_required',lambda:migration.apply_start_prompt(root,plan))
    receipt=json.loads(cli(root,'--apply'))
    assert receipt['action']=='applied',receipt
    assert target.read_text(encoding='utf-8')==startup.render_start_prompt()
    for name,state in before.items():assert tree(root)[name]==state,name
    assert not (root/'AGENTS.md').exists() and not (root/'.pf/agent-entry.json').exists()
    current=tree(root)
    assert json.loads(cli(root,'--apply'))['action']=='unchanged'
    assert tree(root)==current
    assert migration.rollback_entry(root,receipt['transaction'],apply=True)['action']=='rolled_back'
    assert not target.exists()
    current=tree(root)
    migration.rollback_entry(root,receipt['transaction'],apply=True)
    assert tree(root)==current

    plan=migration.plan_start_prompt(root)
    tampered=copy.deepcopy(plan);tampered['generated_prompt']='tampered'
    reject('plan_invalid',lambda:migration.apply_start_prompt(root,tampered,apply=True))
    target.write_text('Custom content\n',encoding='utf-8')
    before=tree(root)
    assert json.loads(cli(root,'--plan',ok=False))['reason']=='start_content_conflict'
    cli(root,'--apply',ok=False)
    assert tree(root)==before
    target.write_text(startup.render_start_prompt(),encoding='utf-8')
    reject('plan_stale',lambda:migration.apply_start_prompt(root,plan,apply=True))
    linked=fixture(base,'linked')
    os.link(target,linked/'.pf/START_AGENT_HERE.md')
    before=tree(linked)
    reject('unsupported_path',lambda:migration.plan_start_prompt(linked))
    assert tree(linked)==before


def recovery(base):
    for point in ('staged','replaced:.pf/START_AGENT_HERE.md'):
        root=fixture(base,'fault-'+point.replace(':','-').replace('/','-'))
        target=root/'.pf/START_AGENT_HERE.md'
        raw=BOM+startup.load_start_source()[2][0].format(project_id='fixture').replace('\n','\r\n').encode()
        target.write_bytes(raw)
        before=tree(root)
        def fault(at,tx):
            if at==point:raise EntryError('injected')
        receipt=migration.apply_start_prompt(root,migration.plan_start_prompt(root),apply=True,_fault=fault)
        assert receipt['action']=='incomplete',receipt
        assert migration.pending(root)==[receipt['transaction']]
        assert 'entry_transaction_incomplete' in migration.plan_start_prompt(root)['blockers']
        migration.rollback_entry(root,receipt['transaction'],apply=True)
        assert target.read_bytes()==raw
        for name,state in before.items():
            if name!='.pf/START_AGENT_HERE.md':assert tree(root)[name]==state
    root=fixture(base,'source-change')
    plan=migration.plan_start_prompt(root)
    source=startup.load_start_source()
    with patch.object(startup,'load_start_source',side_effect=[source,source,(source[0],'changed',source[2])]):
        receipt=migration.apply_start_prompt(root,plan,apply=True)
    assert receipt['action']=='incomplete' and receipt['reason']=='contract_source_changed',receipt
    migration.rollback_entry(root,receipt['transaction'],apply=True)
    # The shared journal reader never accepts a user-chosen file target.
    journal=root/migration.JOURNALS/(receipt['transaction']+'.json')
    envelope=json.loads(journal.read_text(encoding='utf-8'))
    envelope['payload']['files'][0]['path']='arbitrary.md'
    envelope['sha256']=digest(encoded(envelope['payload']))
    journal.write_bytes(encoded(envelope))
    reject('journal_invalid',lambda:migration.pending(root))


def references(base):
    root=fixture(base,'references')
    before=tree(root)
    legacy=core.collect_context_sources(root)
    boot=next(row for row in legacy if row['kind']=='agent-boot')
    assert boot['path']=='.pf/AGENTS.md' and 'legacy' in boot['selection_reason']
    snapshot=core.build_project_context_snapshot(root)
    assert snapshot['session']['startup_read_order'][0]=='.pf/AGENTS.md'
    assert tree(root)==before
    (root/'AGENTS.md').write_text('Root startup contract\n',encoding='utf-8')
    before=tree(root)
    records=core.collect_context_sources(root)
    boot=next(row for row in records if row['kind']=='agent-boot')
    extended=next(row for row in records if row['kind']=='agent-extended')
    assert boot['path']=='AGENTS.md' and boot['required']
    assert extended['path']=='.pf/AGENTS.md' and not extended['required'] and extended['load_policy']=='available'
    current=core.build_project_context_snapshot(root)
    assert current['session']['startup_read_order'][0]=='AGENTS.md'
    assert any('pf.work.resolve' in x for x in current['session']['startup_read_order'])
    rendered=core.render_project_context_snapshot_md(current)
    assert '1. AGENTS.md' in rendered
    old=copy.deepcopy(snapshot)
    old['session']['startup_read_order']=['pinned legacy entry','pinned capsule']
    original=copy.deepcopy(old)
    rendered=core.render_project_context_snapshot_md(old)
    assert '1. pinned legacy entry' in rendered and old==original
    assert tree(root)==before,'source/render changed a capsule or snapshot'


def main():
    with tempfile.TemporaryDirectory(prefix='pf-start-prompt-') as folder:
        base=Path(folder)
        previews(base);placement(base);recovery(base);references(base)
    print('PASS: startup previews, explicit placement/recovery, ownership and context references')


if __name__=='__main__':main()
