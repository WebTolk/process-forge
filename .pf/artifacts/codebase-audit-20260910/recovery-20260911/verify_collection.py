"""Exercise real collection on disposable PF projects, observing ingress unchanged."""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import processforge as core
from pf_runtime import host
from smoke_conversation_completeness import setup_worker_project, transcript


def main():
    results = []
    with tempfile.TemporaryDirectory(prefix='pf-primary-collection-') as raw:
        for name in ('plain', 'path_content', 'external_report'):
            root = Path(raw) / name
            root.mkdir()
            workplace, project, _, run_id, task_id, attempt, report_rel = setup_worker_project(root)
            content = '# Report\n\nVerified local result.\n'
            if name == 'path_content':
                content += 'Source: C:\\workspace\\src\\module.py\n'
            if name == 'external_report':
                report_rel = '../outside.md'
                content = '# Harmless external fixture\n\nOUTSIDE_FIXTURE_MARKER\n'
                task = core.load_task(project, task_id)
                task['expected_report']['artifact'] = report_rel
                task['required_outputs'][0]['path'] = report_rel
                core.save_task(project, task)
            report = project / report_rel
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(content, encoding='utf-8')
            captures = []
            original = host.ingest_event
            def observe(*args, **kwargs):
                result = original(*args, **kwargs)
                captures.append(result)
                return result
            host.ingest_event = observe
            invocations = []
            try:
                for retry in range(2):
                    stream = io.StringIO()
                    with contextlib.redirect_stdout(stream):
                        code = core.command_worker_run_collect(argparse.Namespace(project_root=str(project), task=task_id))
                    invocations.append({'exit': code, 'stdout': stream.getvalue()})
            finally:
                host.ingest_event = original
            rows = transcript(project, f'pf-worker:{run_id}:{task_id}:attempt:{attempt}')
            assistants = [row for row in rows if row.get('message', {}).get('role') == 'assistant']
            result = {'case': name, 'collect': invocations, 'capture': captures, 'assistant_count': len(assistants), 'assistant_contents': [row['message']['content'] for row in assistants], 'task_status': core.load_task(project, task_id)['status']}
            results.append(result)
            (OUT / 'collection-primary-results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
            print(name, 'exit', [x['exit'] for x in invocations], 'assistant_count', len(assistants), 'diagnostics', [x.get('diagnostics') for x in captures], flush=True)


if __name__ == '__main__':
    main()
