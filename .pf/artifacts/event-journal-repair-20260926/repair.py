"""Reviewed one-fragment recovery. Default is read-only; never replace a live journal."""
import hashlib,json,os,sys,tempfile,threading,time
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
# Full digest of the reviewed historical fragment; no prefix matching.
EXPECTED='6f1fa1694252d1b08e1ac8351716ab6129f302a26135c6bd56d7b1466c088739'
LIMIT=128*1024*1024
def digest(data): return hashlib.sha256(data).hexdigest()
def scan(raw):
    bad=[];valid=0;offset=0
    for number,line in enumerate(raw.splitlines(keepends=True),1):
        if line.strip():
            try: json.loads(line)
            except (ValueError,UnicodeError) as exc:
                body=line.rstrip(b'\r\n')
                bad.append({'line':number,'offset':offset,'length':len(line),'body_length':len(body),'body_sha256':digest(body),'raw_hex':line.hex(),'error':str(exc)})
            else: valid+=1
        offset+=len(line)
    return {'size':len(raw),'sha256':digest(raw),'valid_records':valid,'bad':bad}
def read_snapshot(path):
    with path.open('rb') as f: raw=f.read(LIMIT+1)
    if len(raw)>LIMIT: raise ValueError('journal exceeds explicit recovery budget')
    return raw
def write_json(path,value):
    with path.open('w',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def quarantine(path,backup,expected_fragment):
    assert not path.is_symlink(), 'refuse a symlink target'
    original=read_snapshot(path);report=scan(original)
    assert len(report['bad'])==1, 'expected exactly one invalid record'
    bad=report['bad'][0]
    assert bad['body_sha256']==expected_fragment, 'fragment hash changed'
    assert bad['length']>bad['body_length'], 'unterminated tail requires separate recovery'
    before=path.stat()
    backup.mkdir(parents=True,exist_ok=False)
    with (backup/'events-before.bin').open('xb') as f:
        f.write(original);f.flush();os.fsync(f.fileno())
    assert digest((backup/'events-before.bin').read_bytes())==report['sha256']
    report.update({'status':'prepared','backup':'events-before.bin','identity':[before.st_dev,before.st_ino]})
    write_json(backup/'repair.json',report)
    offset=bad['offset'];length=bad['body_length'];spaces=b' '*length
    expected=original[:offset]+spaces+original[offset+length:]
    with path.open('r+b',buffering=0) as f:
        actual=os.fstat(f.fileno());current=path.stat()
        assert (actual.st_dev,actual.st_ino)==(before.st_dev,before.st_ino)==(current.st_dev,current.st_ino), 'journal identity changed'
        assert f.read(len(original))==original, 'journal prefix changed; no write performed'
        f.seek(offset)
        if f.write(spaces)!=len(spaces): raise OSError('short quarantine range write')
        os.fsync(f.fileno())
        f.seek(0)
        assert f.read(len(original))==expected, 'prefix verification failed after range write'
        current=path.stat()
        assert (actual.st_dev,actual.st_ino)==(current.st_dev,current.st_ino), 'journal path changed'
    after=scan(read_snapshot(path))
    assert not after['bad'] and after['size']>=len(original)
    assert after['valid_records']>=report['valid_records']
    report.update({'status':'applied','after':after,'changed_range':[offset,offset+length],
                   'original_valid_bytes_preserved':True,'newline_and_offsets_preserved':True,
                   'post_snapshot_appended_bytes':after['size']-len(original)})
    write_json(backup/'repair.json',report)
    return report
def test():
    bad=b' incomplete timestamp fragment}'
    with tempfile.TemporaryDirectory(prefix='pf-journal-recovery-') as name:
        root=Path(name);path=root/'events.ndjson'
        prefix=b'{"event_id":"a"}\r\n'+bad+b'\r\n'+b'{"event_id":"b"}\r\n'
        path.write_bytes(prefix)
        started=threading.Event();errors=[]
        def append():
            try:
                for n in range(100):
                    with path.open('ab') as f: f.write((json.dumps({'event_id':f'new{n}'})+'\n').encode())
                    started.set();time.sleep(0.001)
            except BaseException as exc: errors.append(str(exc))
        worker=threading.Thread(target=append);worker.start();assert started.wait(2)
        result=quarantine(path,root/'backup',digest(bad));worker.join(5)
        assert not worker.is_alive() and not errors
        rows=[json.loads(line) for line in path.read_bytes().splitlines() if line.strip()]
        assert len(rows)==102 and {x['event_id'] for x in rows}=={'a','b',*(f'new{n}' for n in range(100))}
        assert path.read_bytes().startswith(prefix.replace(bad,b' '*len(bad)))
        assert (root/'backup/events-before.bin').read_bytes().startswith(prefix)
        for label,raw in [('two',bad+b'\n'+bad+b'\n'),('tail',bad),('wrong',b'another fragment\n')]:
            target=root/(label+'.ndjson');target.write_bytes(raw)
            try: quarantine(target,root/(label+'-backup'),digest(bad))
            except AssertionError: pass
            else: raise AssertionError('unexpected corruption accepted: '+label)
            assert target.read_bytes()==raw
        target=root/'drift.ndjson';target.write_bytes(prefix)
        actual_open=Path.open
        def changed_open(p,mode='r',*args,**kwargs):
            if p==target and mode=='r+b':
                with actual_open(p,'wb') as f: f.write(b'{"replacement":true}\n')
            return actual_open(p,mode,*args,**kwargs)
        with patch.object(Path,'open',changed_open):
            try: quarantine(target,root/'drift-backup',digest(bad))
            except AssertionError as exc: assert 'prefix changed' in str(exc)
            else: raise AssertionError('concurrent replacement was overwritten')
        assert target.read_bytes()==b'{"replacement":true}\n'
        assert (root/'drift-backup/events-before.bin').read_bytes()==prefix
    print('PASS: middle-fragment quarantine with 100 concurrent appends, byte/offset preservation, backup, wrong/multiple/tail rejection and drift abort')
if __name__=='__main__':
    if sys.argv[1:]==['--test']: test()
    elif sys.argv[1:]==['--apply']:
        from work import state
        assert state('repair-work-state')['stage']['id']=='release-delivery'
        result=quarantine(ROOT/'.pf/runtime/events/events.ndjson',ROOT/'.pf/tmp/event-journal-repair-20260926/original-journal',EXPECTED)
        write_json(HERE/'repair-result.json',result)
        print(json.dumps(result,ensure_ascii=True))
    elif not sys.argv[1:]:
        result=scan(read_snapshot(ROOT/'.pf/runtime/events/events.ndjson'))
        write_json(HERE/'journal-plan.json',result);print(json.dumps(result))
    else: raise SystemExit('use no arguments (plan), --test, or --apply')
