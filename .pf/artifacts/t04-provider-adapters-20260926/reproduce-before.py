import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import processforge as core
from pf_runtime import host
from smoke_conversation_completeness import setup_basic_project

with tempfile.TemporaryDirectory(prefix='pf-t04-before-') as temporary:
    workplace,project=setup_basic_project(Path(temporary),'before-project')
    envelope={'provider':'fixture-provider','adapter':'unregistered-fixture','native_event_type':'Start','native_event_id':'fixture-start','raw_payload':{'event':'Start'},'source_session_id':'unregistered-session','source_project_ref':str(project),'derived_event':{'event_type':'agent.session.started','event_id':'fixture-start','session_id':'unregistered-session','agent_id':'fixture-provider','project_root':str(project),'source':{'adapter':'unregistered-fixture','session_id':'unregistered-session'}}}
    response=host.ingest_event(envelope,workplace,core)
    item={'message_role':'user','content':'fixture message','content_source':{'kind':'fixture','content_provenance':'provider_payload'}}
    result={'unknown_adapter_routes_before':bool(response.get('normalized_event_ids')),'alternate_message_allow_before':host._allowed_conversation_message(envelope,item),'raw_event_id':response.get('raw_event_id'),'raw_kernel_sha256':__import__('hashlib').sha256((ROOT/'tools/pf_runtime/raw_ingress_kernel.py').read_bytes()).hexdigest()}
    assert result['unknown_adapter_routes_before'] and not result['alternate_message_allow_before']
    Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
