#!/usr/bin/env python3
"""Install the reviewed contributor knowledge into a new standard PF workplace.

This initial-install helper preserves existing packages. Use PF's native updater
for subsequent releases. A preview is the default; --apply writes the packages
and their exact installed-subject records.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

import yaml

PROFILE = (
    Path(__file__).resolve().parents[1] / "docs/contributors/knowledge-packages.json"
)


def checked_archive(data: bytes, package: dict) -> zipfile.ZipFile:
    """Verify the pinned digest and reject paths unsafe to extract."""
    if hashlib.sha256(data).hexdigest() != package["sha256"]:
        raise ValueError(f"SHA-256 mismatch: {package['id']}")
    archive = zipfile.ZipFile(io.BytesIO(data))
    for member in archive.infolist():
        path = PurePosixPath(member.filename)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in member.filename
            or ":" in member.filename
            or stat.S_ISLNK(member.external_attr >> 16)
        ):
            archive.close()
            raise ValueError(f"Unsafe archive member: {member.filename}")
    manifest = yaml.safe_load(archive.read("package.yaml"))
    if (
        manifest.get("id") != package["id"]
        or manifest.get("version") != package["version"]
    ):
        archive.close()
        raise ValueError(f"Package identity/version mismatch: {package['id']}")
    return archive


def write_registry(path: Path, document: dict) -> None:
    """Replace the registry atomically, preserving unrelated records."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        yaml.safe_dump(document, stream, sort_keys=False, allow_unicode=True)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install(workplace: Path, archives: Path | None, apply: bool) -> None:
    """Install all profile packages without replacing an existing installation."""
    workplace = workplace.resolve()
    if not (workplace / "workplace.yaml").is_file():
        raise ValueError("Initialize the workplace with workplace-init first.")
    roots = yaml.safe_load(
        (workplace / "registries/package-roots.yaml").read_text(encoding="utf-8")
    )
    global_root = next(
        item for item in roots["package_roots"] if item["id"] == "global"
    )
    root_path = str(global_root["path"]).replace("${PF_WORKPLACE}", str(workplace))
    selected_root = (workplace / root_path).resolve()
    if selected_root != (workplace / "packages").resolve():
        raise ValueError(
            "This helper requires the standard global root <workplace>/packages."
        )
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    registry_path = workplace / "registries/installed-subjects.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    subjects = registry.setdefault("subjects", [])
    pending = []
    for package in profile["packages"]:
        identity = package["id"]
        if not re.fullmatch(r"[a-z][a-z0-9.-]*", identity):
            raise ValueError(f"Invalid package id: {identity}")
        destination = selected_root / identity
        record = next(
            (
                item
                for item in subjects
                if item.get("type") == "knowledge_package"
                and item.get("id") == identity
            ),
            None,
        )
        if record and destination.is_dir():
            manifest = yaml.safe_load(
                (destination / "package.yaml").read_text(encoding="utf-8")
            )
            if (
                record.get("artifact", {}).get("sha256") == package["sha256"]
                and manifest.get("version") == package["version"]
            ):
                sources = json.loads(
                    (destination / "sources.json").read_text(encoding="utf-8")
                )
                if all(
                    hashlib.sha256(
                        (destination / item["path"]).read_bytes()
                    ).hexdigest()
                    == item["sha256"]
                    for item in sources["documents"]
                ):
                    print(
                        f"PRESENT: {identity}@{package['version']} (document hashes verified)"
                    )
                    continue
        if destination.exists() or record:
            raise ValueError(
                f"Existing package {identity}: preserve it and use the native PF updater."
            )
        pending.append(package)
        print(
            f"{'INSTALL' if apply else 'PREVIEW'}: {identity}@{package['version']} -> {destination}"
        )
    if not apply:
        return
    selected_root.mkdir(parents=True, exist_ok=True)
    for package in pending:
        if archives is not None:
            data = (archives / package["archive"]).read_bytes()
        else:
            url = package["download_url"]
            if not url.startswith("https://github.com/WebTolk/"):
                raise ValueError("Expected a reviewed WebTolk HTTPS release URL.")
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
        with checked_archive(data, package) as archive:
            with tempfile.TemporaryDirectory(
                prefix=".contributor-install-", dir=selected_root
            ) as raw:
                staged = Path(raw) / "package"
                archive.extractall(staged)
                staged.rename(selected_root / package["id"])
        subjects.append(
            {
                "type": "knowledge_package",
                "id": package["id"],
                "scope": "workplace",
                "version": package["version"],
                "source_id": package["source_id"],
                "install_path": f"packages/{package['id']}",
                "artifact": {
                    "sha256": package["sha256"],
                    "url": package["download_url"],
                },
            }
        )
        write_registry(registry_path, registry)
        print(f"REGISTERED: {package['id']} (SHA-256 verified)")


def main() -> int:
    """Parse initial-setup options and report concrete installation failures."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workplace", type=Path, required=True)
    parser.add_argument(
        "--archives-dir",
        type=Path,
        help="Use previously downloaded ZIPs; hashes are still checked.",
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        install(args.workplace, args.archives_dir, args.apply)
    except (OSError, ValueError, KeyError, StopIteration, zipfile.BadZipFile) as error:
        print(f"FAIL: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
