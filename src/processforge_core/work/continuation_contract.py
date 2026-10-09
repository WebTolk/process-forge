"""Existing Continuation record version and binding contract."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True, kw_only=True)
class ContinuationContractPolicy:
    error: Callable[[], type[ValueError]] = field(repr=False, compare=False)

    def validate_record(self, record: dict, continuation_id: str) -> None:
        if record.get('id') != continuation_id or record.get('status') not in {'waiting', 'ready', 'resumed'}:
            raise self.error()('continuation_not_resumable')
        if type(record.get('schema_version')) is not int or record['schema_version'] not in (1, 2):
            raise self.error()('continuation_version_unsupported')
        if record['schema_version'] == 2:
            binding = record.get('work')
            if not isinstance(binding, dict) or set(binding) != {'project_id', 'run_id', 'assignment_id', 'context_id', 'capsule_checksum'}:
                raise self.error()('continuation_binding_invalid')
            if not isinstance(binding['project_id'], str) or not binding['project_id'] or not re.fullmatch(r'sha256:[a-f0-9]{64}', str(binding['capsule_checksum'])):
                raise self.error()('continuation_binding_invalid')

