"""Combine actual source-suite reports without hiding their failed attempts."""
from pathlib import Path
from collections import Counter
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import processforge as pf

reports = ['source-full-report-attempt1.json', 'source-full-report-remainder.json',
           'source-final-report.json']
latest = {}
attempts = []
for filename in reports:
    report = json.loads((OUT / filename).read_text(encoding='utf-8-sig'))
    counts = Counter(check['status'] for check in report['checks'])
    attempts.append({'report': filename, 'counts': dict(counts)})
    for check in report['checks']:
        latest[check['label']] = {**check, 'evidence_report': filename}
expected = {item.label for item in pf.release_test_commands(ROOT, clean_first=False, public=False)}
assert set(latest) == expected, {'missing': sorted(expected - latest.keys()),
                                'extra': sorted(latest.keys() - expected)}
remaining = {label for label, check in latest.items() if check['status'] != 'PASS'}
assert remaining == {'smoke_user_like_garage_path', 'smoke_release_manifest_provenance_contract'}, remaining
counts = dict(Counter(check['status'] for check in latest.values()))
result = {
    'scope': 'All registered source commands with --no-clean; broad git diff gate replaced by scoped public check.',
    'source_suite_status': 'FAIL',
    'remediation_acceptance': 'PASS for A01-A11 with independently reproduced baseline counterexamples',
    'counts': counts, 'registered_commands': len(expected), 'attempts': attempts,
    'residuals': {
        'smoke_user_like_garage_path': 'Same empty_corpus failure reproduced on original HEAD. Separate pre-existing first-run search contract investigation.',
        'smoke_release_manifest_provenance_contract': 'Correctly refuses non-clean Git source; clean candidate/archive release qualification outside this source-only run.',
    },
    'exclusions': {'clean': 'Preserve existing unrelated generated artifacts.',
                   'git diff --check': 'Whole-checkout private PF dirt preserved; scoped src/tools/docs/checksums check PASS.'},
    'checks': [latest[name] for name in sorted(latest)],
}
(OUT / 'validation-summary.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'source_suite_status': result['source_suite_status'],
                  'remediation_acceptance': result['remediation_acceptance'],
                  'registered_commands': len(expected), 'counts': counts}))
