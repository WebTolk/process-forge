"""Analysis-only defect probes; all mutations are confined to TemporaryDirectory."""
from __future__ import annotations
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
import processforge as core
from processforge_core import core_update as cu
from processforge_core import local_resource_search as ls
from smoke_core_update_manifest import install_old_core, write_archive

RESULTS = []

def probe(name, fn):
    with tempfile.TemporaryDirectory(prefix='pf-audit-') as raw:
        try:
            result = fn(Path(raw))
            RESULTS.append({'probe': name, 'result': result})
        except Exception as exc:
            RESULTS.append({'probe': name, 'error': repr(exc), 'traceback': traceback.format_exc()})
    print(json.dumps(RESULTS[-1], ensure_ascii=False), flush=True)

def undefined_presence(root):
    p = root / 'runtime/agent-presence/agent/session.json'
    p.parent.mkdir(parents=True)
    p.write_text('{"status":"offline"}', encoding='utf-8')
    return core.active_organized_project_sessions(root)

def undefined_report(root):
    return core.normalized_orchestrator_plan(root, {'run': {'id':'audit'}, 'workers':[{'id':'worker'}]})

def update_collision(root):
    target=root/'core'; target.mkdir(); install_old_core(target)
    (target/'user-note.txt').write_text('USER OWNED DATA',encoding='utf-8')
    archive=root/'candidate.zip'
    write_archive(archive, {'a.txt':'old-a','dir/b.txt':'old-b','dir/c.txt':'same-c','user-note.txt':'NEW CORE PAYLOAD'})
    plan=cu.build_plan(target,archive)
    result=cu.apply_update(target,archive,confirm=True)
    return {'plan_status':plan['status'],'blockers':plan['blockers'],'apply_status':result['status'],
            'user_file_after':(target/'user-note.txt').read_text(),'backed_up':result['backed_up']}

def missing_unchanged(root):
    target=root/'core'; target.mkdir(); install_old_core(target)
    (target/'dir/c.txt').unlink()
    archive=root/'candidate.zip'; write_archive(archive, {'a.txt':'new-a','dir/b.txt':'old-b','dir/c.txt':'same-c'})
    plan=cu.build_plan(target,archive); result=cu.apply_update(target,archive,confirm=True)
    return {'missing_owned':plan['missing_owned'],'unchanged':plan['unchanged'],'apply_status':result['status'],
            'required_file_exists':(target/'dir/c.txt').is_file(),'reported_version':cu.core_status(target)['version']}

def live_lock_reaped(root):
    path=root/'registry.yaml'; lock=path.with_name('.registry.yaml.lock')
    with core.registry_file_lock(path):
        # Simulate the real default 300-second age without waiting five minutes.
        age=time.time()-301; os.utime(lock,(age,age))
        owner=json.loads(lock.read_text())
        with core.registry_file_lock(path,timeout_seconds=0.2):
            return {'first_owner_pid':owner['pid'],'live_pid':os.getpid(),'second_writer_entered_while_first_held_lock':True}

def resource(identifier, root, sources=None):
    return {'id':identifier,'content_roots':[str(root)],'indexing':{'mode':'fulltext','sources':sources or [{'path':'.','mode':'fulltext','include':['**/*.md']} ]}}

def symlink_search(root):
    allowed=root/'allowed'; allowed.mkdir(); secret=root/'outside.md'; secret.write_text('OutsideBoundaryNeedle')
    try: (allowed/'linked.md').symlink_to(secret)
    except OSError as exc:return {'not_reproduced':'symlink creation unavailable','error':str(exc)}
    snap={'snapshot':{'id':'audit'},'local_search_resources':[resource('docs',allowed)]}
    ls.build_index(root,snap)
    result=ls.search(root,snap,query='OutsideBoundaryNeedle')
    return {'outside_root':str(secret),'symlink_target':str((allowed/'linked.md').resolve()),'total':result['total'],'results':result['results']}

def overlapping_sources(root):
    docs=root/'docs'; docs.mkdir(); (docs/'guide.md').write_text('OverlapNeedle')
    source={'path':'.','mode':'fulltext','include':['**/*.md']}
    snap={'snapshot':{'id':'overlap'},'local_search_resources':[resource('docs',docs,[source,{'path':'guide.md','mode':'fulltext','include':['**/*.md']}])]}
    ls.build_index(root,snap); result=ls.search(root,snap,query='OverlapNeedle',limit=1)
    return {'total':result['total'],'returned':len(result['results']),'page':result['page'],'verified_status':ls.index_status(root,snap,verify_files=True)['status']}

def file_exclude(root):
    docs=root/'docs'; docs.mkdir(); (docs/'secret.md').write_text('ExcludedNeedle')
    snap={'snapshot':{'id':'excluded'},'local_search_resources':[resource('docs',docs,[{'path':'secret.md','mode':'fulltext','include':['*.txt'],'exclude':['**/*.md']}])]}
    ls.build_index(root,snap); result=ls.search(root,snap,query='ExcludedNeedle')
    return {'total':result['total'],'results':result['results']}

if __name__ == '__main__':
    for name,fn in [('undefined_presence',undefined_presence),('undefined_report',undefined_report),('update_unowned_collision',update_collision),('update_missing_unchanged',missing_unchanged),('live_lock_reaped',live_lock_reaped),('symlink_search',symlink_search),('overlapping_sources',overlapping_sources),('explicit_file_exclusion',file_exclude)]:probe(name,fn)
    Path(__file__).with_name('fast-results.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding='utf-8')
