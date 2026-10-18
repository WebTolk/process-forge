from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..common.checks import Check, check
from .schema_checks import UpdateSchemaChecks
from .source_contracts import UpdateSourceContractPolicy


SHA256_HEX_RE = re.compile(r"^[A-Fa-f0-9]{64}$")


class UpdateDocumentValidationService:
    """Validate existing update document semantics through concrete Core owners."""

    def __init__(self, distribution_root: Path) -> None:
        self.schema_checks = UpdateSchemaChecks(distribution_root)
        self.source_contracts = UpdateSourceContractPolicy()

    def site_overrides(self, data: dict[str, Any], path: Path) -> list[Check]:
        checks: list[Check] = []
        if not data:
            return [check("FAIL", f"{path} missing or invalid")]
        self.schema_checks.append(checks, data, "update-site-overrides.schema.json", str(path))
        overrides = data.get("overrides")
        if not isinstance(overrides, list):
            checks.append(check("FAIL", f"{path} overrides must be a list"))
            return checks
        seen: set[str] = set()
        for index, item in enumerate(overrides):
            label = f"overrides[{index}]"
            if not isinstance(item, dict):
                checks.append(check("FAIL", f"{label} must be an object"))
                continue
            site_id = item.get("site_id")
            subject_id = item.get("subject_id")
            if isinstance(site_id, str) and site_id.strip():
                if site_id in seen:
                    checks.append(check("FAIL", f"{label} duplicate site_id {site_id}"))
                seen.add(site_id)
            elif not (isinstance(subject_id, str) and subject_id.strip()) and not isinstance(item.get("subject"), dict):
                checks.append(check("FAIL", f"{label} missing site_id, subject_id, or subject"))
            if "enabled" in item and not isinstance(item.get("enabled"), bool):
                checks.append(check("FAIL", f"{label}.enabled must be boolean"))
            if "disabled" in item and not isinstance(item.get("disabled"), bool):
                checks.append(check("FAIL", f"{label}.disabled must be boolean"))
            if "channels" in item and (
                not isinstance(item.get("channels"), list) or not all(isinstance(channel, str) and channel.strip() for channel in item.get("channels", []))
            ):
                checks.append(check("FAIL", f"{label}.channels must be a list of non-empty strings"))
            self.source_contracts.append_env_checks(checks, item, label)
            preserved = item.get("preserved_local") if isinstance(item.get("preserved_local"), dict) else {}
            self.source_contracts.append_env_checks(checks, preserved, f"{label}.preserved_local")
        if not checks:
            checks.append(check("PASS", f"{path} valid update site overrides"))
        return checks

    def normalized_manifest(self, data: dict[str, Any], path: Path) -> list[Check]:
        checks: list[Check] = []
        self.schema_checks.append(checks, data, "normalized-update-manifest.schema.json", str(path))
        if data.get("schema_version") != 1:
            checks.append(check("FAIL", f"{path} schema_version must be 1"))
        product = data.get("product") if isinstance(data.get("product"), dict) else {}
        if not product.get("id"):
            checks.append(check("FAIL", f"{path} product.id missing"))
        subjects = data.get("subjects")
        if not isinstance(subjects, list):
            checks.append(check("FAIL", f"{path} subjects must be a list"))
            return checks
        for subject_index, subject in enumerate(subjects):
            if not isinstance(subject, dict):
                checks.append(check("FAIL", f"subjects[{subject_index}] must be an object"))
                continue
            for key in ("type", "id"):
                if not isinstance(subject.get(key), str) or not str(subject.get(key)).strip():
                    checks.append(check("FAIL", f"subjects[{subject_index}].{key} missing"))
            versions = subject.get("versions")
            if not isinstance(versions, list):
                checks.append(check("FAIL", f"subjects[{subject_index}].versions must be a list"))
                continue
            for version_index, version in enumerate(versions):
                if not isinstance(version, dict):
                    checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}] must be an object"))
                    continue
                artifacts = version.get("artifacts")
                if not isinstance(artifacts, list):
                    checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts must be a list"))
                    continue
                for artifact_index, artifact in enumerate(artifacts):
                    if not isinstance(artifact, dict):
                        checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}] must be an object"))
                        continue
                    artifact_url = artifact.get("url")
                    if not artifact_url:
                        checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].url missing"))
                    elif not isinstance(artifact_url, str):
                        checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].url must be a string"))
                    else:
                        valid, reason = self.source_contracts.artifact_url_shape(artifact_url, artifact)
                        if not valid:
                            checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].url {reason}"))
                    artifact_sha256 = artifact.get("sha256")
                    if not artifact_sha256:
                        checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].sha256 missing"))
                    elif not isinstance(artifact_sha256, str) or not SHA256_HEX_RE.fullmatch(artifact_sha256):
                        checks.append(check("FAIL", f"subjects[{subject_index}].versions[{version_index}].artifacts[{artifact_index}].sha256 must be 64 hex characters"))
        if not checks:
            checks.append(check("PASS", f"{path} valid normalized update manifest"))
        return checks
