# R02 Release Command Review

Status: pass with command-boundary note

Required command sequence:

1. Source validation:

```bash
python bin/pf.py release-test --root <candidate-root> --public --fail-fast
```

For a source-only suite that avoids the automatic `release package` step, add `--no-clean`.

2. Archive creation:

```bash
python bin/pf.py release-pack --root <candidate-root> --output <candidate-root>/dist/processforge-1.1.0.zip
```

This performs release checks, public-cleanliness and checksum preflight, requires a clean Git checkout, records Git provenance, writes the ZIP and manifest, and performs consumer archive inspection. Record the archive SHA-256 separately.

3. Archive/source parity and extracted validation:

```bash
python bin/pf.py release-archive-test --archive <candidate-root>/dist/processforge-1.1.0.zip --root <candidate-root> --extracted-test quick
```

Use `--extracted-test full` for the complete extracted release suite. The command validates archive entries, forbidden paths, manifest hashes, source freshness/parity, extracted CLI help, and extracted release tests.

Safety boundary:

- Operate only in the detached candidate worktree under `.pf/tmp/`.
- Do not publish, tag, install/update Core, modify `VERSION`, or update checksums.
- Do not package from the active source checkout when it contains PF runtime state or other changes.
- Release output must exclude `.pf/runtime/`, `.pf/artifacts/`, `.pf/reviews/`, `.pf/handoffs/`, `.pf/runs/`, `.pf/contexts/`, `.pf/assignments/`, runtime/cache data, temporary smoke directories, private paths, secrets, hook payloads, and stale distribution archives.
- `release-pack` writes the archive and adjacent `.manifest.json`; use `--dry-run` when inspecting intended contents without writing.
- The assigned `tools/release_test.py` path is absent in the current checkout; release-test functionality is implemented in `tools/processforge.py`.