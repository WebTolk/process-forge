#!/usr/bin/env python3
"""Smoke domain-shaped fixture ids resolve without hardcoded domain knowledge."""

from __future__ import annotations

import tempfile
from pathlib import Path

from specialization_smoke_helpers import resolve_json, write_process_with_capability, write_project, write_specialization, write_workspace, write_yaml


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="pf-domain-neutral-") as tmp:
        root = Path(tmp)
        workplace = write_workspace(root)
        music_platform = "fixture.platform." + "music-project"
        video_platform = "fixture.platform." + "video-project"
        registry = workplace / "registries" / "platforms.yaml"
        data = {
            "schema_version": 1,
            "platforms": [
                {"id": "music", "package_id": music_platform, "path": f"platform-contracts/{music_platform}/platform-contract.yaml", "status": "available"},
                {"id": "video", "package_id": video_platform, "path": f"platform-contracts/{video_platform}/platform-contract.yaml", "status": "available"},
            ],
        }
        write_yaml(registry, data)
        for platform_id in [music_platform, video_platform]:
            write_yaml(
                workplace / "platform-contracts" / platform_id / "platform-contract.yaml",
                {"schema_version": 1, "id": platform_id, "title": platform_id, "type": "platform_contract", "version": "1.0.0", "status": "draft", "requires": {"capabilities": []}},
            )
        write_specialization(workplace, "fixture.specialization.music-worker", platform=music_platform, provides_capabilities=["fixture.capability.music-score-edit"])
        write_specialization(workplace, "fixture.specialization.video-worker", platform=video_platform, provides_capabilities=["fixture.capability.video-render"])

        music_project = write_project(root / "music", workplace, platform=music_platform)
        write_process_with_capability(music_project, process_id="fixture-process-music", capability="fixture.capability.music-score-edit")
        music = resolve_json(music_project, workplace, "fixture.specialization.music-worker", platform=music_platform, process="fixture-process-music")
        if not music["capability_resolution"]["satisfied"] or music["capability_resolution"]["unsatisfied"]:
            raise AssertionError(music["capability_resolution"])

        video_project = write_project(root / "video", workplace, platform=video_platform)
        write_process_with_capability(video_project, process_id="fixture-process-video", capability="fixture.capability.video-render")
        video = resolve_json(video_project, workplace, "fixture.specialization.video-worker", platform=video_platform, process="fixture-process-video")
        if not video["capability_resolution"]["satisfied"] or video["capability_resolution"]["unsatisfied"]:
            raise AssertionError(video["capability_resolution"])
    print("PASS: smoke_domain_neutral_music_video_fixtures")


if __name__ == "__main__":
    main()
