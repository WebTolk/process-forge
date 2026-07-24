#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser(description="ProcessForge neutral test echo worker.")
    parser.add_argument("--capsule", required=True, help="Assignment capsule path.")
    parser.add_argument("--output", required=True, help="Expected report output path.")
    parser.add_argument("--heartbeat", required=True, help="Heartbeat JSON path.")
    args = parser.parse_args()

    capsule = Path(args.capsule)
    output = Path(args.output)
    heartbeat = Path(args.heartbeat)
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "status": "alive",
                "updated_at": now_utc(),
                "capsule": str(capsule),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    output.write_text(
        "\n".join(
            [
                "# Test Echo Worker Report",
                "",
                f"- status: `completed`",
                f"- capsule_exists: `{str(capsule.is_file()).lower()}`",
                f"- completed_at: `{now_utc()}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
