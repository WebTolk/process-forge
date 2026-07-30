#!/usr/bin/env python3
"""Run the established domain-neutral core regression shield as one contract."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKES = [
    "smoke_core_has_no_domain_knowledge_seeds.py",
    "smoke_empty_workplace_has_no_domain_resources.py",
    "smoke_project_classification_data_driven.py",
    "smoke_no_hardcoded_file_project_detection.py",
    "smoke_optional_domain_pack_not_default.py",
    "smoke_domain_pack_can_classify_after_install.py",
    "smoke_core_process_catalog_domain_neutral.py",
    "smoke_core_prompts_domain_neutral.py",
    "smoke_runtime_no_domain_file_patterns.py",
    "smoke_no_builtin_user_capability_satisfaction.py",
    "smoke_capability_resolution_data_driven_only.py",
    "smoke_domain_neutral_music_video_fixtures.py",
    "smoke_runtime_no_domain_capability_constants.py",
]


def main() -> None:
    for filename in SMOKES:
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools" / filename)],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=180,
            check=False,
        )
        assert result.returncode == 0, f"{filename}\n{result.stdout}{result.stderr}"
    print("PASS: smoke_core_domain_neutral_still_passes")


if __name__ == "__main__":
    main()
