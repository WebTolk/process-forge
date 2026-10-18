"""Read-only named Runtime activity check, independent of slow /status route."""
from work import *

def inspect_activity():
    host_path=WP/'runtime/pf-runtime-host/state.json'
    cache=json.loads(host_path.read_text(encoding='utf-8-sig'))
    service=json.loads((WP/'runtime/pf-runtime/service.json').read_text(encoding='utf-8-sig'))
    lock=json.loads((WP/'runtime/pf-runtime/runtime.lock').read_text(encoding='utf-8-sig'))
    assert lock['pid']==service['pid'] and lock['instance_id']==service['instance_id']
    projects=[]
    for item in cache.get('projects',[]):
        root=Path(item['project_root'])
        statuses=list((root/'.pf/runtime/agent-runs').glob('*/*/status.json'))
        active=[]
        for path in statuses:
            s=json.loads(path.read_text(encoding='utf-8-sig'))
            if s.get('status')=='running': active.append({'path':str(path),'sha256':sha(path)})
        projects.append({'root':str(root),'status_count':len(statuses),'active':active})
    assert projects and all(not p['active'] for p in projects),projects
    return {'time':datetime.now(timezone.utc).isoformat(),'host_bytes':host_path.stat().st_size,'session_registrations':len(cache.get('sessions',[])), 'projects':projects,'service':service,'lock':lock,'active_worker_records':0,'pending_runtime_jobs':{'value':0,'source':'current service.status_payload literal; no asynchronous runtime job queue'}}

if __name__=='__main__':
    s=inspect_activity();save('activity-before.json',s)
    print(json.dumps({k:s[k] for k in ['host_bytes','session_registrations','projects','active_worker_records']}))
