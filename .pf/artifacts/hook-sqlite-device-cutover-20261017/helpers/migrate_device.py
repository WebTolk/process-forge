"""Private cutover adapter: preserve originals, coalesce proven legacy retries."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import sqlite3
from contextlib import closing

TASK = pathlib.Path(__file__).resolve().parent
EVIDENCE = TASK.parents[1] / 'artifacts/hook-sqlite-device-cutover-20261017'


def signature(path):
    stat = path.stat()
    return [stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]


def canonical_input(source, project_id, backup):
    target = TASK / 'migration-input' / project_id / 'events.ndjson'
    target.parent.mkdir(parents=True, exist_ok=True)
    before = signature(source)
    digest = hashlib.sha256()
    rows = unique = 0
    repeats = []
    backup_path = TASK / 'backups' / project_id / 'events.ndjson'
    if backup:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        if backup_path.exists():
            raise RuntimeError('backup_already_exists: ' + str(backup_path))
    with closing(sqlite3.connect('')) as index, source.open('rb') as stream, target.open('wb') as output:
        index.execute('CREATE TABLE records (id TEXT PRIMARY KEY, payload TEXT, line INTEGER, offset INTEGER)')
        archive = backup_path.open('xb') if backup else None
        try:
            offset = 0
            for number, line in enumerate(stream, 1):
                digest.update(line)
                if archive:
                    archive.write(line)
                location = offset
                offset += len(line)
                if not line.strip():
                    continue
                rows += 1
                row = json.loads(line)
                identifier = row.get('event_id') or row.get('id')
                if not isinstance(identifier, str) or not identifier:
                    raise ValueError('event_id_required at line ' + str(number))
                payload = json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False)
                previous = index.execute('SELECT payload,line,offset FROM records WHERE id=?', (identifier,)).fetchone()
                if previous:
                    first = json.loads(previous[0])
                    changed = sorted(key for key in set(first) | set(row) if first.get(key) != row.get(key) or (key in first) != (key in row))
                    if any(key != 'time' for key in changed):
                        raise ValueError('substantive_id_conflict at line ' + str(number))
                    repeats.append({'event_id': identifier, 'first_line': previous[1], 'line': number, 'first_offset': previous[2], 'offset': location, 'changed_keys': changed, 'first_time': first.get('time'), 'time': row.get('time'), 'line_sha256': hashlib.sha256(line).hexdigest()})
                else:
                    index.execute('INSERT INTO records VALUES (?,?,?,?)', (identifier, payload, number, location))
                    output.write(line if line.endswith(b'\n') else line + b'\n')
                    unique += 1
        finally:
            if archive:
                archive.close()
    if before != signature(source):
        raise RuntimeError('original_source_changed_during_preparation')
    result = {'source': str(source), 'signature': before, 'sha256': digest.hexdigest(), 'rows': rows, 'unique_ids': unique, 'canonical_source': str(target), 'canonical_sha256': hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(), 'coalesced_deliveries': repeats, 'backup': str(backup_path) if backup else None}
    return target, result


def run(args):
    spec = importlib.util.spec_from_file_location('native_pf_migrator', TASK / 'candidate/tools/migrate-hook-journals.py')
    native = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native)
    project = args.project_root.resolve()
    original_sources = native._sources
    flow, original = original_sources(project, args.workplace)
    originals = []
    replacements = {}
    for kind, source in original:
        if kind == 'events':
            target, receipt = canonical_input(source, project.name, args.backup)
            replacements[source] = target
            originals.append(receipt)

    def staged_sources(selected, workplace):
        selected_flow, sources = original_sources(selected, workplace)
        if sources != original:
            raise RuntimeError('original_source_list_changed')
        for receipt in originals:
            if signature(pathlib.Path(receipt['source'])) != receipt['signature']:
                raise RuntimeError('original_source_changed')
        return selected_flow, [(kind, replacements.get(source, source)) for kind, source in sources]

    native._sources = staged_sources
    report = native.migrate(project, args.workplace, apply=args.apply, skip_invalid=False)
    staged_sources(project, args.workplace)
    report['operator_preparation'] = {'policy': 'first_seen_equivalent_body; only top_level_time_may_differ', 'original_event_sources': originals, 'native_migrator_modified': False, 'invalid_rows_skipped': 0}
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=pathlib.Path, required=True)
    parser.add_argument('--workplace', type=pathlib.Path, required=True)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', action='store_true')
    parser.add_argument('--report', type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args)
        code = 1 if report.get('blocked') else 0
    except Exception as error:
        report = {'status': 'failed', 'error': str(error), 'applied_requested': args.apply}
        code = 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('sources', 'operator_preparation')}, ensure_ascii=True))
    raise SystemExit(code)
