"""Root-independent resource identifiers and declared-root containment rules."""

from __future__ import annotations

import re
from pathlib import Path


RESOURCE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$")

WINDOWS_RESERVED_DEVICE_BASENAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *{f"com{index}" for index in range(1, 10)},
    *{f"lpt{index}" for index in range(1, 10)},
}


class ResourceIdentityPolicy:
    """Validate resource identities and paths without capturing a project root."""

    def validate_resource_id(self, raw: str, resource_kind: str='resource') -> str:
        value = str(raw)
        invalid_reason = ''
        if not value:
            invalid_reason = 'must not be empty'
        elif value != value.strip() or any((ord(char) < 32 or ord(char) == 127 for char in value)):
            invalid_reason = 'must not contain whitespace or control characters'
        elif '%' in value:
            invalid_reason = 'must not contain percent-encoded path characters'
        elif '/' in value or '\\' in value:
            invalid_reason = 'must not contain path separators'
        elif ':' in value or re.match('^[a-zA-Z]:', value):
            invalid_reason = 'must not contain drive, URI, or alternate-stream syntax'
        elif value.endswith(('.', ' ')):
            invalid_reason = 'must not end with a Windows-trimmed dot or space'
        elif any((segment in {'', '.', '..'} for segment in value.split('.'))):
            invalid_reason = 'must not contain empty or relative dot segments'
        elif value.split('.', 1)[0] in WINDOWS_RESERVED_DEVICE_BASENAMES:
            invalid_reason = 'must not use a Windows reserved device basename'
        elif not RESOURCE_ID_PATTERN.fullmatch(value):
            invalid_reason = 'must match ^[a-z][a-z0-9]*(?:[.-][a-z0-9]+)*$'
        if invalid_reason:
            raise SystemExit(f'FAIL: invalid {resource_kind} id {value!r}: {invalid_reason}')
        return value

    def contained_resource_path(self, root: Path, target: Path, resource_kind: str='resource') -> Path:
        try:
            resolved_root = root.expanduser().resolve()
            resolved_target = target.expanduser().resolve()
            resolved_target.relative_to(resolved_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise SystemExit(f'FAIL: invalid {resource_kind} target cannot be contained under declared root: {target.as_posix()}') from exc
        return resolved_target
