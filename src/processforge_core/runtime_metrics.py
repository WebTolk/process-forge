"""Bounded, read-only observations of local PF records, never activity guesses.

Budgets bound work/bytes between filesystem calls, not kernel IO latency. A
partial group has observed lower bounds but no exact counts. No source text,
identities, paths or exception messages leave this module's projection.
"""
from __future__ import annotations

import json
import os
import stat
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

FIELDS = {"registrations": ("projects", "sessions"),
          "sessions": ("online", "stale", "offline"),
          "workers": ("running",), "work": ("in_progress", "blocked"),
          "leases": ("held", "expired", "inactive")}
SOURCES = dict(registrations="host_registration_cache", sessions="agent_presence_ttl",
               workers="worker_status_records", work="run_records", leases="lease_records")
ISSUES = {"coverage", "budget", "invalid", "unreadable", "unsafe_path"}
MAX_AGE = 45


def epoch(value: Any) -> float:
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp needs timezone")
    return stamp.timestamp()


def linked(path: Path) -> bool:
    st = path.lstat()
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def contained(path: Path, root: Path) -> None:
    path.relative_to(root)
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            if linked(item):
                raise ValueError("unsafe path")
        if item == root:
            return
    raise ValueError("unsafe path")


class Budget:
    def __init__(self, *, entries=512, files=128, bytes_=4 * 1024 * 1024, seconds=1.0):
        self.entries, self.files, self.bytes = entries, files, bytes_
        self.deadline = time.monotonic() + seconds
        self.issues: set[str] = set()

    def check(self):
        if min(self.entries, self.files, self.bytes) < 0 or time.monotonic() > self.deadline:
            self.issues.add("budget")
            raise TimeoutError

    def walk(self, root: Path, parts: tuple[str, ...], base: Path):
        """Walk only fixed-depth patterns, accounting for every visited entry."""
        self.check()
        try:
            contained(root, base)
            if not root.exists():
                return
            with os.scandir(root) as entries:
                for entry in entries:
                    self.entries -= 1
                    self.check()
                    path = Path(entry.path)
                    if parts[0] != "*" and entry.name != parts[0] and not (parts[0].startswith("*.") and entry.name.endswith(parts[0][1:])):
                        continue
                    if linked(path):
                        self.issues.add("unsafe_path")
                        continue
                    if len(parts) > 1:
                        if entry.is_dir(follow_symlinks=False):
                            yield from self.walk(path, parts[1:], base)
                    elif entry.is_file(follow_symlinks=False):
                        yield path
                    else:
                        self.issues.add("invalid")
        except TimeoutError:
            raise
        except ValueError:
            self.issues.add("unsafe_path")
        except OSError:
            self.issues.add("unreadable")

    def read(self, path: Path, base: Path, maximum=131072):
        self.files -= 1
        self.check()
        contained(path, base)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("invalid record")
        with path.open("rb") as handle:
            opened = os.fstat(handle.fileno())
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                raise ValueError("record changed")
            raw = handle.read(min(maximum, self.bytes) + 1)
        self.bytes -= len(raw)
        self.check()
        if len(raw) > maximum:
            self.issues.add("budget")
            raise ValueError("oversize record")
        data = json.loads(raw) if path.suffix == ".json" else yaml.load(raw.decode("utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
        if not isinstance(data, dict):
            raise ValueError("invalid record")
        return data


def group(name, observed, issues=()):
    issues = sorted(set(issues))
    return {"source": SOURCES[name], "coverage": "partial" if issues else "complete",
            "counts": {k: None if issues else observed[k] for k in FIELDS[name]},
            "observed": observed, "issues": issues}


def registrations(cache):
    valid = (isinstance(cache, dict) and isinstance(cache.get("projects"), list)
             and isinstance(cache.get("sessions"), dict))
    return group("registrations", {"projects": len(cache["projects"]) if valid else 0,
                                    "sessions": len(cache["sessions"]) if valid else 0}, () if valid else ("coverage",))


def observe(name, workplace, roots, core, *, now, coverage=True, budget=None):
    budget = budget or Budget()
    counts = dict.fromkeys(FIELDS[name], 0)
    if not coverage and name in {"workers", "work"}:
        budget.issues.add("coverage")
    rows = {}
    try:
        if name == "sessions":
            presence_dir = core.workplace_agent_presence_dir(workplace)
            paths = ((path, workplace) for parts in (("*.json",), ("*", "*.json")) for path in budget.walk(presence_dir, parts, workplace))
        elif name == "leases":
            paths = ((path, workplace) for path in budget.walk(core.workplace_agent_leases_dir(workplace), ("*.yaml",), workplace))
        else:
            def project_paths():
                for project in roots[:128]:
                    budget.check()
                    if name == "workers":
                        folder, pattern = project / ".pf/runtime/agent-runs", ("*", "*", "status.json")
                    else:
                        folder, pattern = project / ".pf/runs", ("*", "run.yaml")
                    yield from ((path, project) for path in budget.walk(folder, pattern, project))
                if len(roots) > 128:
                    budget.issues.add("budget")
            paths = project_paths()
        for path, base in paths:
            try:
                item = budget.read(path, base)
                status = item.get("status")
                if name == "sessions":
                    agent, session = item.get("agent_id"), item.get("session_id")
                    if not isinstance(agent, str) or not agent or not isinstance(session, str) or not session:
                        raise ValueError
                    canonical = core.agent_presence_path(workplace, agent, session)
                    legacy = core.workplace_agent_presence_dir(workplace) / core.safe_id(agent, "agent") / (core.safe_id(session, "session") + ".json")
                    if path not in {canonical, legacy, core.legacy_agent_presence_path(workplace, agent)}:
                        raise ValueError
                    key = (agent, session)
                    if key not in rows or path == canonical:
                        rows[key] = (path == canonical, item)
                elif name == "workers":
                    if status not in {"planned", "ready", "starting", "running", "completed", "failed", "timed_out", "unknown_exit", "lost", "blocked", "cancelled", "manual_required"}:
                        raise ValueError
                    if status in {"starting", "unknown_exit", "lost"}:
                        budget.issues.add("coverage")
                    counts["running"] += status == "running"
                elif name == "work":
                    if status not in {"draft", "open", "in_progress", "blocked", "review", "completed", "cancelled", "failed"}:
                        raise ValueError
                    if status in counts:
                        counts[status] += 1
                else:
                    issued, expires = epoch(item.get("issued_at")), epoch(item.get("expires_at"))
                    if issued > now or expires < issued or status not in {"active", "released", "revoked", "expired", "stale"}:
                        raise ValueError
                    counts["held" if status == "active" and expires > now else "expired" if status in {"active", "expired"} else "inactive"] += 1
            except (ValueError, TypeError, OverflowError, RecursionError, yaml.YAMLError):
                budget.issues.add("invalid")
            except OSError:
                budget.issues.add("unreadable")
        for _canonical, item in rows.values():
            try:
                status, ttl = item.get("status"), item.get("heartbeat_ttl_seconds")
                age = now - epoch(item.get("last_seen_at"))
                if type(ttl) is not int or ttl < 1 or age < 0 or status not in {"online", "offline", "stale", "checked_out", "failed"}:
                    raise ValueError
                counts["online" if status == "online" and age <= ttl else "stale" if status in {"online", "stale"} else "offline"] += 1
            except (ValueError, TypeError, OverflowError):
                budget.issues.add("invalid")
    except TimeoutError:
        budget.issues.add("budget")
    except (OSError, ValueError, TypeError):
        budget.issues.add("unreadable")
    return group(name, counts, budget.issues)


def collect(workplace, roots, core, instance_id, registration, *, coverage=True, now=None, interval_seconds=None):
    now = time.time() if now is None else now
    groups = {name: observe(name, workplace, roots, core, now=now, coverage=coverage)
              for name in ("sessions", "workers", "work", "leases")}
    groups["registrations"] = registration
    result = {"schema_version": 1, "instance_id": instance_id,
              "observed_at": datetime.fromtimestamp(now, timezone.utc).isoformat(), "groups": groups}
    if interval_seconds is not None:
        from .configuration import MetricsConfig
        result["interval_seconds"] = MetricsConfig(interval_seconds).interval_seconds
    return result


def project(snapshot, instance_id, *, now):
    """Allowlist and strictly validate a fresh instance-bound compact snapshot."""
    try:
        if not isinstance(snapshot, dict) or type(snapshot.get("schema_version")) is not int or snapshot["schema_version"] != 1 or not instance_id or snapshot.get("instance_id") != instance_id:
            raise ValueError
        age = now - epoch(snapshot.get("observed_at"))
        interval = snapshot.get("interval_seconds")
        maximum_age = MAX_AGE
        if "interval_seconds" in snapshot:
            from .configuration import MetricsConfig
            interval = MetricsConfig(interval).interval_seconds
            maximum_age = max(5, 4.5 * interval)
        if not 0 <= age <= maximum_age:
            raise ValueError
        result = {}
        for name, fields in FIELDS.items():
            item = snapshot["groups"][name]
            if item["source"] != SOURCES[name] or item["coverage"] not in {"complete", "partial"}:
                raise ValueError
            issues = item["issues"]
            if not isinstance(issues, list) or len(issues) > len(ISSUES) or any(type(i) is not str or i not in ISSUES for i in issues):
                raise ValueError
            counts, observed = {}, {}
            for key in fields:
                v, o = item["counts"][key], item["observed"][key]
                if type(o) is not int or not 0 <= o <= 2147483647:
                    raise ValueError
                if item["coverage"] == "complete":
                    if type(v) is not int or v != o or issues:
                        raise ValueError
                elif v is not None or not issues:
                    raise ValueError
                counts[key], observed[key] = v, o
            result[name] = group(name, observed, issues)
        return {"age_seconds": round(age, 1), "groups": result, "interval_seconds": interval}
    except (KeyError, ValueError, TypeError, OverflowError):
        return None


def registered_projects(workplace, *, budget=None):
    """Bounded cache routing for observation; no project execution/context build."""
    budget = budget or Budget()
    try:
        cache = budget.read(workplace / "runtime/pf-runtime-host/state.json", workplace, maximum=4194304)
        projects = cache.get("projects")
        if not isinstance(projects, list) or len(projects) > 128:
            raise ValueError
        roots = []
        complete = True
        for item in projects:
            budget.check()
            try:
                if not isinstance(item, dict) or not isinstance(item.get("project_root"), str):
                    raise ValueError
                root = Path(item["project_root"])
                if not root.is_absolute() or not (root / ".pf/process-forge.yaml").is_file():
                    raise ValueError
                contained(root / ".pf/process-forge.yaml", root)
                if root not in roots:
                    roots.append(root)
            except (ValueError, OSError):
                complete = False
        return roots, registrations(cache), complete
    except (OSError, ValueError, TypeError, TimeoutError):
        return [], registrations({}), False


def shutdown_workers(workplace, core):
    """Fresh worker-only guard, including invalid/unroutable registrations."""
    budget = Budget(seconds=0.5)
    roots, _registration, coverage = registered_projects(workplace, budget=budget)
    return observe("workers", workplace, roots, core, now=time.time(), coverage=coverage, budget=budget)
