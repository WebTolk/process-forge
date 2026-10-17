"""One operator cutover while Windows read handles freeze legacy inputs."""
import concurrent.futures
import ctypes
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import zipfile
from ctypes import wintypes

TASK = pathlib.Path(__file__).resolve().parent
PROJECT = TASK.parents[2]
OUT = PROJECT / '.pf/artifacts/hook-sqlite-device-cutover-20261017'
WORKPLACE = pathlib.Path('D:/.agents/processforge-workplace')
CORE = pathlib.Path('D:/.agents/processforge')
PROJECTS = [PROJECT, pathlib.Path('D:/dev/wt-image-resize-and-convert-joomla-plugin')]
ARCHIVE = TASK / 'processforge-1.2.0-dev-20261017-sqlite-69c59ec.zip'
EXPECTED_SHA = '6dbcfdb8090a1fb9f6761fef9d0973e3e17911d577314095c270a25bcc3745db'


def run_command(label, command, timeout=600):
    start = time.monotonic()
    env = os.environ.copy()
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout, env=env)
    receipt = {'command': command, 'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3), 'stdout': result.stdout, 'stderr': result.stderr}
    (OUT / (label + '.json')).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'step': label, 'returncode': result.returncode, 'elapsed_seconds': receipt['elapsed_seconds'], 'tail': (result.stdout + result.stderr)[-1200:]}), flush=True)
    if result.returncode:
        raise RuntimeError(label + ' failed; inspect receipt, do not repeat native apply')
    return receipt


def main():
    if (WORKPLACE / 'runtime/pf-runtime/runtime.lock').exists():
        raise RuntimeError('Runtime lock still present; inspect owner')
    with ARCHIVE.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != EXPECTED_SHA:
            raise RuntimeError('archive_hash_changed')
    if (OUT / 'core-update-apply.json').exists():
        raise RuntimeError('native_apply_already_attempted; inspect status before any repeat')
    sources = sorted(set([p / '.pf/runtime/events/events.ndjson' for p in PROJECTS] + list((WORKPLACE / 'runtime/agent-events/raw/v1').rglob('*.ndjson')) + [p for root in PROJECTS for p in (root / '.pf/runtime/agent-events/raw/v1').rglob('*.ndjson')]))
    sources = [path for path in sources if path.is_file()]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handles = []
    try:
        for source in sources:
            handle = kernel.CreateFileW(str(source), 0x80000000, 1, None, 3, 0x80, None)
            if handle == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle)
        print(json.dumps({'step': 'legacy_sources_frozen', 'files': len(handles), 'mode': 'Windows read handles deny writes and deletion'}), flush=True)
        backup_root = TASK / 'backups'
        backup_root.mkdir(exist_ok=True)
        backup_zip = backup_root / 'all-legacy-inputs.zip'
        manifest = []
        with zipfile.ZipFile(backup_zip, 'x', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for number, source in enumerate(sources):
                stat = source.stat()
                digest = hashlib.sha256()
                member = str(number).zfill(4) + '/' + source.name
                with source.open('rb') as stream, archive.open(member, 'w', force_zip64=True) as target:
                    while chunk := stream.read(1024 * 1024):
                        digest.update(chunk)
                        target.write(chunk)
                manifest.append({'path': str(source), 'member': member, 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'sha256': digest.hexdigest()})
        (OUT / 'legacy-backup-manifest.json').write_text(json.dumps({'backup_zip': str(backup_zip), 'files': manifest}, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'step': 'legacy_backup_complete', 'files': len(manifest), 'bytes': sum(row['size'] for row in manifest)}), flush=True)
        run_command('core-update-before-status', [sys.executable, '-B', str(CORE / 'bin/pf.py'), 'core-update', 'status', '--core-root', str(CORE)])
        run_command('core-update-apply', [sys.executable, '-B', str(CORE / 'bin/pf.py'), 'core-update', 'apply', '--core-root', str(CORE), '--archive', str(ARCHIVE), '--workplace-root', str(WORKPLACE), '--confirm'])
        run_command('core-update-after-status', [sys.executable, '-B', str(CORE / 'bin/pf.py'), 'core-update', 'status', '--core-root', str(CORE)])

        def migrate(project):
            label = 'migration-applied-' + project.name
            return run_command(label + '-command', [sys.executable, '-B', str(TASK / 'migrate_device.py'), '--project-root', str(project), '--workplace', str(WORKPLACE), '--backup', '--apply', '--report', str(OUT / (label + '.json'))])

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(migrate, PROJECTS))
        for row in manifest:
            source = pathlib.Path(row['path'])
            if source.stat().st_size != row['size'] or source.stat().st_mtime_ns != row['mtime_ns']:
                raise RuntimeError('legacy_source_changed_under_freeze')
        (OUT / 'critical-section.json').write_text(json.dumps({'status': 'completed', 'frozen_files': len(manifest), 'originals_unchanged': True, 'native_apply_attempts': 1, 'projects': [str(p) for p in PROJECTS], 'runtime_started': False}, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'step': 'cutover_databases_ready', 'projects': len(results), 'originals_unchanged': True, 'runtime_started': False}), flush=True)
    finally:
        for handle in reversed(handles):
            kernel.CloseHandle(handle)


if __name__ == '__main__':
    main()
