"""Read-only, bounded profile predictions. No client invocation or host certification."""
from __future__ import annotations

from pathlib import Path
import re

from .contract import (EntryError, SOURCE_ROOT, decode_json, digest,
                          inspect_projection, load_contract, text_bytes)
from .migration import manifest, measure, read_file, root_path, safe_path


PROFILE_FIELDS = {"id", "version", "surface", "route", "client_revision", "selector", "unit", "scope",
                  "accounting_phase", "overflow", "default_limit", "default_file_limit", "prerequisites", "proof_refs",
                  "input_deduplication"}
CONTEXT_ENUMS = {"mcp": {"available", "unavailable", "unknown"},
                 "cli": {"available", "unavailable", "unknown"},
                 "status": {"fresh", "stale", "broken", "unknown"},
                 "policy_action": {"continue", "block", "unknown"},
                 "identity": {"matched", "mismatch", "unknown"},
                 "required_resources": {"available", "denied", "unknown"},
                 "health": {"ok", "warn", "blocked", "unknown"}}
OBS_ENUMS = {"settings_source": {"explicit", "default", "unknown"},
             "injection": {"enabled", "disabled", "unknown"},
             "accounting_phase": {"raw_concat", "expanded_render", "unknown"},
             "context_mode": {"full", "lightweight", "unknown"}}
OBS_BOOLS = {"trusted", "boundary_complete", "single_environment", "workspace_matches", "explicit_read"}
OBS_LISTS = {"root_markers", "fallback_names", "selection"}


def _limit(value):
    return value is None or type(value) is int and 0 <= value <= 2**40


def _relative(value, *, filename=False):
    if (not isinstance(value, str) or not 1 <= len(value) <= 512 or "\\" in value or ":" in value
            or any(ord(c) < 32 for c in value) or value.startswith("/")
            or any(p in {"", ".", ".."} or p.endswith((".", " ")) for p in value.split("/"))
            or filename and "/" in value):
        raise EntryError("observation_path_invalid")
    return value


def load_profiles(source: Path = SOURCE_ROOT) -> dict:
    try:
        with (source / "templates/agent-entry-profiles.json").open("rb") as stream:
            data = decode_json(stream.read(65537))
    except OSError:
        raise EntryError("profile_registry_unavailable") from None
    if (not isinstance(data, dict) or set(data) != {"schema_version", "kind", "registry_version", "profiles"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["kind"] != "pf.agent-entry.profiles" or data["registry_version"] != "1.0.0"
            or not isinstance(data["profiles"], list) or not 1 <= len(data["profiles"]) <= 32):
        raise EntryError("profile_registry_invalid")
    ids = set()
    for p in data["profiles"]:
        if (not isinstance(p, dict) or set(p) != PROFILE_FIELDS
                or any(not isinstance(p[k], str) for k in PROFILE_FIELDS - {"default_limit", "default_file_limit", "prerequisites", "proof_refs"})
                or not re.fullmatch(r"P-[A-Z0-9-]{1,40}", p["id"]) or p["id"] in ids
                or p["version"] != "1.0.0" or not re.fullmatch(r"[a-z0-9.-]{1,80}", p["client_revision"])
                or any(not re.fullmatch(r"[a-z0-9-]{1,64}", p[k]) for k in ("surface", "route"))
                or p["selector"] not in {"codex", "observed"}
                or p["input_deduplication"] not in {"same_path", "none"}
                or p["unit"] not in {"utf8_bytes", "utf16_code_units", "unknown"}
                or p["scope"] not in {"chain", "file_and_chain"}
                or p["accounting_phase"] not in {"codex_read", "expanded_render", "bootstrap_render", "unknown"}
                or p["overflow"] not in {"truncate", "warn", "unknown"}
                or not _limit(p["default_limit"]) or not _limit(p["default_file_limit"])
                or not isinstance(p["prerequisites"], list) or len(p["prerequisites"]) > 16
                or any(not isinstance(x, str) or not re.fullmatch(r"[a-z_]{1,64}", x) for x in p["prerequisites"])
                or not isinstance(p["proof_refs"], list) or not 1 <= len(p["proof_refs"]) <= 8):
            raise EntryError("profile_registry_invalid")
        for ref in p["proof_refs"]:
            if (not isinstance(ref, dict) or set(ref) != {"level", "reference"} or not isinstance(ref["level"], str) or ref["level"] not in {"D", "S"}
                    or not isinstance(ref["reference"], str) or not re.fullmatch(
                        r"(?:https://[A-Za-z0-9./_#-]{1,512}|docs/concepts/agent-entry.md#[a-z-]+)", ref["reference"])):
                raise EntryError("profile_registry_invalid")
        models = {
            "codex_read": ("codex", "utf8_bytes", "chain", "truncate", "none"),
            "expanded_render": ("observed", "utf8_bytes", "chain", "warn", "same_path"),
            "bootstrap_render": ("observed", "utf16_code_units", "file_and_chain", "truncate", "none"),
            "unknown": ("observed", "unknown", "chain", "unknown", "none"),
        }
        if tuple(p[k] for k in ("selector", "unit", "scope", "overflow", "input_deduplication")) != models[p["accounting_phase"]]:
            raise EntryError("profile_registry_invalid")
        ids.add(p["id"])
    return data


def observations(value=None) -> dict:
    if value is None:
        return {"schema_version": 1}
    keys = {"schema_version", "profile_version", "client_revision", "limit", "file_limit", "context"} | OBS_BOOLS | OBS_LISTS | set(OBS_ENUMS)
    if (not isinstance(value, dict) or set(value) - keys or type(value.get("schema_version")) is not int
            or value["schema_version"] != 1):
        raise EntryError("observations_invalid")
    for key, item in value.items():
        if key in OBS_ENUMS and (not isinstance(item, str) or item not in OBS_ENUMS[key]):
            raise EntryError("observations_invalid")
        if key in OBS_BOOLS and item is not None and type(item) is not bool:
            raise EntryError("observations_invalid")
        if key in {"limit", "file_limit"} and not _limit(item):
            raise EntryError("observations_invalid")
        if key in {"profile_version", "client_revision"} and (not isinstance(item, str)
                or not re.fullmatch(r"[A-Za-z0-9.-]{1,80}", item)):
            raise EntryError("observations_invalid")
        if key in OBS_LISTS:
            if not isinstance(item, list) or len(item) > (64 if key == "selection" else 16):
                raise EntryError("observations_invalid")
            for name in item:
                _relative(name, filename=key != "selection")
    context = value.get("context", {})
    if not isinstance(context, dict) or set(context) - set(CONTEXT_ENUMS):
        raise EntryError("observations_invalid")
    for key, item in context.items():
        if not isinstance(item, str) or item not in CONTEXT_ENUMS[key]:
            raise EntryError("observations_invalid")
    return value


def adapter_spec(profile_id: str, route: str) -> dict:
    """Render only an explicitly selected route; this does not inspect a client."""
    profile = next((p for p in load_profiles()["profiles"] if p["id"] == profile_id), None)
    if profile is None:
        raise EntryError("unsupported_profile")
    routes = {"root-agents": ("root-agents",),
              "selected-native-or-import": ("root-agents", "native-import"),
              "selected-native-import": ("root-agents", "native-import"),
              "explicit-read": ("explicit-read",),
              "workspace-agents": ("prerequisites",), "host-carrier": ("prerequisites",)}
    if route not in routes.get(profile["route"], ()):
        raise EntryError("adapter_route_invalid")
    target, section = None, None
    if route == "native-import":
        targets = {"P-CLAUDE": ("CLAUDE.md", "@AGENTS.md"), "P-GEMINI": ("GEMINI.md", "@./AGENTS.md")}
        if profile_id not in targets:
            raise EntryError("adapter_route_invalid")
        target, reference = targets[profile_id]
        section = (f"<!-- PF:ADAPTER:BEGIN profile={profile_id} version=1.0.0 -->\n"
                   f"{reference}\n<!-- PF:ADAPTER:END -->\n")
    return {"profile_id": profile["id"], "profile_version": profile["version"],
            "client_revision": profile["client_revision"], "adapter_version": "1.0.0",
            "route": route, "target": target, "generated_section": section,
            "prerequisites": list(profile["prerequisites"])}


def verdict(status, *reasons):
    return {"status": status, "reasons": sorted(set(reasons))}


def context_verdict(obs):
    ctx = obs.get("context", {})
    reasons = []
    for key, bad, reason in (("status", "stale", "context_stale"), ("status", "broken", "context_broken"),
                             ("policy_action", "block", "context_policy_blocked"),
                             ("identity", "mismatch", "work_identity_mismatch"),
                             ("required_resources", "denied", "required_resource_denied"),
                             ("health", "blocked", "context_health_blocked")):
        if ctx.get(key) == bad:
            reasons.append(reason)
    if ctx.get("mcp") == ctx.get("cli") == "unavailable":
        reasons.append("context_verifier_unavailable")
    if reasons:
        return verdict("blocked", *reasons)
    complete = (ctx.get("status") == "fresh" and ctx.get("policy_action") == "continue"
                and ctx.get("identity") == "matched" and ctx.get("required_resources") == "available"
                and ctx.get("health") in {"ok", "warn"})
    if complete and "available" in (ctx.get("mcp"), ctx.get("cli")):
        return verdict("conditional", "caller_observed_context", *(["existing_cli_fallback"] if ctx.get("mcp") == "unavailable" else []))
    return verdict("unverified", "context_unverified")


def _codex_selection(root, cwd, obs):
    current = root if cwd == "." else safe_path(root, _relative(cwd))
    if not current.is_dir():
        raise EntryError("cwd_missing")
    dirs = [current, *current.parents]
    dirs = dirs[:dirs.index(root) + 1]
    if len(dirs) > 64:
        raise EntryError("discovery_depth_limit")
    markers = obs.get("root_markers", [".git"])
    boundary = None
    for directory in dirs:
        for name in markers:
            rel = (directory / name).relative_to(root).as_posix()
            if safe_path(root, rel).exists():
                boundary = directory
                break
        if boundary is not None:
            break
    search = list(reversed(dirs[:dirs.index(boundary) + 1])) if boundary else [current]
    names = list(dict.fromkeys(["AGENTS.override.md", "AGENTS.md", *obs.get("fallback_names", [])]))
    selected, reasons = [], []
    for directory in search:
        for name in names:
            rel = (directory / name).relative_to(root).as_posix()
            candidate = safe_path(root, rel)
            if candidate.is_file():
                selected.append(rel)
                if name == "AGENTS.override.md":
                    reasons.append("override_selected")
                break
    if boundary is None and current != root:
        reasons.append("no_marker_cwd_only")
    if boundary is not None and boundary != root:
        reasons.append("nested_project_boundary")
    return selected, reasons


def _budget(profile, obs, inputs, contract, exact):
    unit = profile["unit"]
    limit = obs.get("limit", profile["default_limit"])
    file_limit = obs.get("file_limit", profile["default_file_limit"])
    explicit = obs.get("settings_source") == "explicit" and "limit" in obs
    def value_source(key, default):
        if key in obs:
            return obs.get("settings_source", "unknown") if obs[key] is not None else "unknown"
        return "default" if default is not None else "unknown"
    phase = profile["accounting_phase"]
    precise = exact and phase == "codex_read" and limit is not None and explicit
    remaining = limit
    offset = 0
    rendered_lower_bound = 0
    rows, blockers, warnings = [], [], []
    complete_k, complete_required, found_k = True, True, False
    for name, raw in inputs:
        inspected = inspect_projection(raw, contract)
        span = (inspected["k_start"], inspected["k_end"]) if inspected["status"] == "verified" else None
        size = measure(raw, unit) if unit != "unknown" else None
        start = measure(raw[:span[0]], unit) if span and size is not None else None
        end = measure(raw[:span[1]], unit) if span and size is not None else None
        found_k |= bool(span)
        full = k_full = None
        before = offset
        if phase == "codex_read" and limit is not None:
            cut = raw[:remaining]
            loaded = bool(cut.decode("utf-8", errors="replace").strip())
            full = len(cut) == len(raw) or not raw.decode("utf-8").strip()
            k_full = bool(loaded and span and len(cut) >= span[1]) if span else None
            if loaded:
                remaining -= len(cut)
                offset += len(cut)
            complete_required &= full
            if span:
                complete_k &= k_full
        elif size is not None:
            offset += size
            if phase == "expanded_render":
                # Strip a superset of ECMAScript whitespace. This is deliberately
                # a lower bound, excluding native wrappers and their path spelling.
                trim = " \t\n\r\v\f\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
                rendered_lower_bound += len(raw.decode("utf-8").strip(trim).encode("utf-8"))
                if limit is not None and rendered_lower_bound > limit:
                    warnings.append("rendered_budget_lower_bound_exceeded")
            if phase == "bootstrap_render":
                if file_limit is not None and size > file_limit:
                    warnings.append("raw_bootstrap_file_budget_exceeded")
                if limit is not None and offset > limit:
                    warnings.append("raw_bootstrap_total_budget_exceeded")
        rows.append({"path": name, "sha256": digest(raw), "raw_size": len(raw), "native_size": size,
                     "used_before_k": before + start if precise and start is not None else None,
                     "k_start": start, "k_end": end,
                     "remaining": remaining if phase == "codex_read" else None,
                     "contract_complete": k_full if precise else None,
                     "required_instructions_complete": full if precise else None})
    if precise:
        if not found_k:
            blockers.append("entry_contract_not_selected")
        elif not complete_k:
            blockers.append("entry_contract_would_truncate")
        if not complete_required:
            blockers.append("required_instructions_would_truncate")
    return {"profile": profile["id"], "unit": unit, "scope": profile["scope"],
            "accounting_phase": phase, "effective_limit": limit, "file_limit": file_limit,
            "value_source": value_source("limit", profile["default_limit"]),
            "file_limit_source": value_source("file_limit", profile["default_file_limit"]),
            "overflow_behavior": profile["overflow"], "selected_inputs": rows,
            "raw_size": sum(len(raw) for _, raw in inputs), "expanded_size": None,
            "rendered_lower_bound": rendered_lower_bound if phase == "expanded_render" else None,
            "native_total": sum(row["native_size"] for row in rows) if unit != "unknown" else None,
            "status": "accounted" if precise else "budget_unverified",
            "contract_complete": bool(found_k and complete_k) if precise else None,
            "required_instructions_complete": complete_required if precise else None,
            "evidence_level": "S" if any(r["level"] == "S" for r in profile["proof_refs"]) else "D",
            "basis": "conditional_source_model",
            "warnings": sorted(set(warnings))}, blockers


def diagnose_entry(project: Path, *, profile_id: str, observation=None, cwd: str = ".") -> dict:
    """Never writes, expands imports, scans home settings, or calls client/Runtime APIs."""
    registry = load_profiles()
    obs = observations(observation)
    profile = next((p for p in registry["profiles"] if p["id"] == profile_id), None)
    report = {"schema_version": 1, "kind": "pf.agent-entry.diagnostics", "profile": profile,
              "contract": None, "files": [], "budget_observations": [], "blockers": [],
              "verdicts": {"file_consistency": verdict("unverified", "files_unchecked"),
                           "discovery": verdict("unverified", "profile_unverified"),
                           "delivery": verdict("unverified", "native_delivery_not_observed"),
                           "behavior": verdict("unverified", "model_behavior_not_observed"),
                           "enforcement": verdict("not_applicable", "separate_host_boundary"),
                           "runtime_context": context_verdict(obs)}}
    if profile is None:
        report["blockers"] = ["unsupported_profile"]
        report["verdicts"]["discovery"] = verdict("blocked", "unsupported_profile")
        return report
    try:
        root = root_path(project)
        contract = load_contract()
        report["contract"] = {"version": contract.version, "sha256": contract.sha256, "canonical_bytes": len(contract.raw)}
        cache = {}
        def read(name):
            if name not in cache:
                raw, _ = read_file(root, name)
                cache[name] = raw
                if sum(len(v) for v in cache.values() if v is not None) > 8 * 1048576:
                    raise EntryError("diagnostic_input_limit")
            return cache[name]
        file_reasons = []
        for name in ("AGENTS.md", ".pf/AGENTS.md"):
            row = inspect_projection(read(name), contract)
            report["files"].append(dict(path=name, **row))
            if row["status"] != "verified":
                file_reasons.append(row["reason"])
        manifest_raw = read(".pf/agent-entry.json")
        if manifest_raw is None:
            file_reasons.append("entry_manifest_missing")
        else:
            entry_manifest = decode_json(manifest_raw)
            if (not isinstance(entry_manifest, dict) or type(entry_manifest.get("schema_version")) is not int
                    or entry_manifest != manifest(contract)):
                file_reasons.append("entry_manifest_mismatch")
        report["verdicts"]["file_consistency"] = verdict("blocked", *file_reasons) if file_reasons else verdict("verified", "current_projections")
        exact = (obs.get("profile_version") == profile["version"] and obs.get("client_revision") == profile["client_revision"]
                 and obs.get("settings_source") == "explicit")
        unknown = []
        if not exact:
            unknown.append("profile_settings_unverified")
        discovery_reasons = []
        blocked = []
        if obs.get("injection") == "disabled":
            blocked.append("instruction_injection_disabled")
        elif obs.get("injection") != "enabled":
            unknown.append("injection_unverified")
        if obs.get("trusted") is False:
            blocked.append("project_untrusted")
        elif obs.get("trusted") is not True:
            unknown.append("trust_unverified")
        if profile["selector"] == "codex":
            selected, discovery_reasons = _codex_selection(root, cwd, obs)
            if obs.get("boundary_complete") is not True:
                unknown.append("discovery_boundary_unverified")
            if obs.get("single_environment") is not True:
                unknown.append("environment_budget_unverified")
            if "root_markers" not in obs or "fallback_names" not in obs:
                unknown.append("selection_settings_unverified")
            if obs.get("accounting_phase", "raw_concat") != "raw_concat":
                unknown.append("accounting_phase_unverified")
            if exact and obs.get("limit") == 0:
                blocked.append("project_instruction_budget_zero")
        else:
            selected = obs.get("selection", [])
            unknown.append("native_selector_not_qualified")
            if not selected:
                unknown.append("selection_unverified")
            if profile["route"] == "explicit-read":
                if obs.get("explicit_read") is False:
                    blocked.append("explicit_read_required")
                elif obs.get("explicit_read") is not True:
                    unknown.append("explicit_read_unverified")
            if profile["route"] == "workspace-agents":
                if obs.get("workspace_matches") is False:
                    blocked.append("workspace_mismatch")
                elif obs.get("workspace_matches") is not True:
                    unknown.append("workspace_unverified")
                if obs.get("context_mode") == "lightweight":
                    blocked.append("full_context_mode_required")
                elif obs.get("context_mode") != "full":
                    unknown.append("context_mode_unverified")
        if profile["input_deduplication"] == "same_path":
            selected = list(dict.fromkeys(selected))
        inputs = []
        for name in selected:
            raw = read(name)
            if raw is None:
                raise EntryError("selected_input_missing")
            text_bytes(raw)
            inputs.append((name, raw))
        if not unknown and not any(inspect_projection(raw, contract)["status"] == "verified" for _, raw in inputs):
            blocked.append("entry_contract_not_selected")
        budget, budget_blockers = _budget(profile, obs, inputs, contract, exact and not unknown and not blocked)
        report["budget_observations"].append(budget)
        blocked.extend(budget_blockers)
        if budget["status"] == "budget_unverified":
            unknown.append("budget_unverified")
        report["verdicts"]["discovery"] = (verdict("blocked", *blocked, *discovery_reasons) if blocked else
                                             verdict("unverified", *unknown, *discovery_reasons) if unknown else
                                             verdict("conditional", "pinned_selector_prediction", *discovery_reasons))
        if blocked:
            report["verdicts"]["delivery"] = verdict("blocked", "conditional_source_model", *blocked)
        report["blockers"] = sorted(set(file_reasons + blocked + (report["verdicts"]["runtime_context"]["reasons"]
                                     if report["verdicts"]["runtime_context"]["status"] == "blocked" else [])))
    except (EntryError, OSError) as exc:
        reason = exc.reason if isinstance(exc, EntryError) else "storage_error"
        report["blockers"] = sorted(set(report["blockers"] + [reason]))
        report["verdicts"]["discovery"] = verdict("blocked", reason)
    return report
