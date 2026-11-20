#!/usr/bin/env python3
"""Guard the documented Garage/Forge infrastructure boundary."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = {
        "README.md": (
            "Garage mode does not require PF Runtime",
            "Forge MCP connection uses the workplace Runtime",
        ),
        "README.ru.md": (
            "Режим гаража не требует PF Runtime",
            "Подключение MCP в Forge использует Runtime рабочего места",
        ),
        "docs/getting-started/runtime-autostart.md": [
            "Garage does not require PF Runtime"
        ],
        "docs/ru/getting-started/runtime-autostart.md": [
            "Garage не требует PF Runtime"
        ],
    }
    for rel, markers in checks.items():
        text = " ".join((ROOT / rel).read_text(encoding="utf-8").split())
        for marker in markers:
            if marker not in text:
                raise AssertionError(f"{rel} missing: {marker}")
    print("PASS: docs state that Garage work does not require Runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
