"""Pure compatibility startup text and exact previous-generator recognition."""
from pathlib import Path
import re
import string

from .contract import BOM, EntryError, SOURCE_ROOT, decode_json, digest, text_bytes


WORK_GUIDANCE = """## Governed Work

Call `pf.work.start` with the objective. If it returns `process_choice_required`,
choose an offered process and retry with `process_id`. Follow `pf.work.state`:
read the returned assignment and immutable Execution Context Package, check
identity, scope and readiness, satisfy the current stage, then use
`pf.work.transition` with outcome and evidence until PF returns `run_completed`.
PF selects stages. Use the exact returned Work/context selectors with
`pf.work.search` and `pf.work.resolve`; project context does not enlarge Work
scope. A missing, denied or revoked required resource blocks dependent work.
"""


def render_start_prompt() -> str:
    """Independent of project history, current Work and stored START contents."""
    return """# Start Agent Here

You are working inside a ProcessForge-enabled project.

## Preferred Path

1. Read the root `AGENTS.md` startup contract. If it is absent in an older
   project, use `.pf/AGENTS.md` as the explicit legacy compatibility entry.
2. Call `pf.context` with this project root. Check freshness, identity, required
   resources and execution readiness before relying on the context. A fresh
   context with a nonblocking warning can continue; missing, stale, broken,
   ambiguous or identity-invalid context blocks dependent work.
3. If MCP is unavailable, use the existing project CLI to verify the current
   snapshot and Work state. Reading a snapshot alone does not prove freshness.
   If no verifier is available, report the operator blocker.
4. Use `pf.search` and `pf.resolve` for project-authorized resources needed for
   local read-only analysis. Load extended `.pf/AGENTS.md` instructions on demand.
5. When work becomes substantive, follow Governed Work below. Keep durable
   outputs in the selected artifacts, reviews, logs and handoffs.

""" + WORK_GUIDANCE + """
## Infrastructure Boundary

During ordinary project work, do not install, start, restart, or repair PF
Runtime, MCP, host hooks, or Agent Ledger. Report an operator-level blocker if
required infrastructure is unavailable. Garage work does not require Runtime,
hooks, or a manually created Ledger session.

Do not expose private paths, configuration or resource contents in public
outputs. Use the existing project CLI entrypoint; a distribution-local CLI path
is appropriate only when this project is the ProcessForge distribution itself.

This START file is a compatibility explanation. The root startup contract is
authoritative; this text does not prove client loading or grant execution access.
`agent-start-prompt` prints a preview. `--plan` reviews placement; `--apply`
explicitly places recognized PF-owned text through the shared transaction service.
"""


def load_start_source() -> tuple[str, str, list[str]]:
    """Bind a placement plan to this renderer and its exact ownership metadata."""
    try:
        with (SOURCE_ROOT / 'templates/legacy-start-agent-here.json').open('rb') as stream:
            raw = stream.read(65537)
        own = Path(__file__).read_bytes()
    except OSError:
        raise EntryError('start_source_unavailable') from None
    value = decode_json(raw)
    if (not isinstance(value, dict) or set(value) != {'schema_version', 'templates'}
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or not isinstance(value['templates'], list) or not 1 <= len(value['templates']) <= 32
            or any(not isinstance(x, list) or not 1 <= len(x) <= 256
                   or any(not isinstance(line, str) or '\n' in line or '\r' in line for line in x)
                   or x[0] != '# Start Agent Here' for x in value['templates'])):
        raise EntryError('start_source_invalid')
    return render_start_prompt(), digest(own + b'\0' + raw), ['\n'.join(lines) for lines in value['templates']]


def _legacy_matches(text: str, template: str) -> bool:
    # Previous writers produced either one terminal LF or the generator's two.
    # Additional blank lines are not evidence of PF ownership.
    if len(text) - len(text.rstrip('\n')) not in (1, 2):
        return False
    fields = {
        'project_id': r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',
        'run_id': r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',
        'assignment_rel': r'\.pf/assignments/(?:first-assignment\.yaml)?',
    }
    parts, seen = [], set()
    try:
        for literal, field, spec, conversion in string.Formatter().parse(template.rstrip('\n')):
            parts.append(re.escape(literal))
            if field is not None:
                if field not in fields or spec or conversion:
                    raise EntryError('start_source_invalid')
                parts.append('(?P='+field+')' if field in seen else '(?P<'+field+'>'+fields[field]+')')
                seen.add(field)
    except ValueError:
        raise EntryError('start_source_invalid') from None
    match = re.fullmatch(''.join(parts), text.rstrip('\n'))
    # Equality to the full reconstructed generator, not a heading/prefix match.
    return bool(match and template.format(**match.groupdict()).rstrip('\n') == text.rstrip('\n'))


def project_start_content(raw: bytes | None, generated: str, legacy: list[str]) -> tuple[bytes, str]:
    wanted = generated.encode('utf-8')
    if raw is None:
        return wanted, 'create'
    text_bytes(raw)
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if text == generated:
        return raw, 'unchanged'
    if not any(_legacy_matches(text, template) for template in legacy):
        raise EntryError('start_content_conflict', '.pf/START_AGENT_HERE.md')
    return (BOM if raw.startswith(BOM) else b'') + wanted, 'replace_known_legacy'
