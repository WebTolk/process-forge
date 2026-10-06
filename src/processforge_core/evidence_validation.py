"""Existing evidence material checks with explicit infrastructure callbacks."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class EvidenceValidationService:
    project_root: Path
    now_utc: Callable[[], str]
    relative_path: Callable[[Path], str]
    sha256_file: Callable[[Path], str]
    path_resolver: Callable[[str], Path | None] | None = None

    def _path(self, value: str) -> Path | None:
        if self.path_resolver is not None:
            return self.path_resolver(value)
        return self.safe_path(value)

    def normalize(self, evidence: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        values = evidence if isinstance(evidence, list) else [] if evidence is None or evidence == '' else [evidence]
        normalized: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        now = self.now_utc()
        for index, value in enumerate(values):
            if isinstance(value, str):
                item = {'kind': 'attestation', 'id': f'attestation-{index + 1}', 'status': 'ready', 'summary': value}
            elif isinstance(value, dict):
                item = copy.deepcopy(value)
            else:
                blockers.append({'code': 'invalid_evidence', 'index': index})
                continue
            item.setdefault('kind', 'attestation')
            item.setdefault('status', 'ready')
            item['recorded_at'] = now
            if str(item.get('status') or '') == 'not_applicable':
                reason = str(item.get('reason') or '').strip()
                supporting = item.get('evidence')
                if not reason or not isinstance(supporting, list) or (not supporting):
                    blockers.append({'code': 'not_applicable_evidence_incomplete', 'index': index})
                    continue
            path_value = str(item.get('path') or '').strip()
            if path_value:
                safe_path = self._path(path_value)
                try:
                    valid_file = safe_path is not None and safe_path.is_file()
                except OSError:
                    valid_file = False
                if not valid_file:
                    blockers.append({'code': 'artifact_path_missing', 'index': index, 'path': path_value})
                    continue
                else:
                    try:
                        item['path'] = self.relative_path(safe_path)
                        item['sha256'] = 'sha256:' + self.sha256_file(safe_path)
                    except OSError:
                        blockers.append({'code': 'artifact_path_unreadable', 'index': index, 'path': path_value})
                        continue
            normalized.append(item)
        return (normalized, blockers)

    def safe_path(self, value: str) -> Path | None:
        try:
            path = Path(value)
            if path.is_absolute():
                return None
            resolved = (self.project_root / path).resolve()
        except (OSError, RuntimeError, ValueError):
            return None
        try:
            resolved.relative_to(self.project_root.resolve())
        except (OSError, RuntimeError, ValueError):
            return None
        return resolved

    def diagnostic(self, evidence: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(evidence, dict):
            return None
        path_value = str(evidence.get('path') or '').strip()
        if not path_value:
            return None
        safe_path = self._path(path_value)
        if safe_path is None:
            return {'code': 'evidence_file_unsafe', 'path': path_value}
        try:
            if not safe_path.exists():
                return {'code': 'evidence_file_missing', 'path': path_value}
            if not safe_path.is_file():
                return {'code': 'evidence_file_not_regular', 'path': path_value}
        except OSError as exc:
            return {'code': 'evidence_file_unreadable', 'path': path_value, 'error': str(exc)}
        stored = str(evidence.get('sha256') or '').strip()
        if not stored:
            return {'code': 'evidence_digest_missing', 'path': path_value}
        try:
            actual = 'sha256:' + self.sha256_file(safe_path)
        except OSError as exc:
            return {'code': 'evidence_file_unreadable', 'path': path_value, 'error': str(exc)}
        if stored.casefold() != actual.casefold():
            return {'code': 'evidence_file_changed', 'path': path_value, 'stored_sha256': stored, 'actual_sha256': actual}
        return None
