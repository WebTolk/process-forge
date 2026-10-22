# Kimi release inventory repair

2026-10-22. Native release-pack exposed a stale generated inventory after Kimi added adapters. Regenerated from clean qualified source c38b4b09710cf88a336bcf78e86b04c5e78c70dc, excluding unrelated local WIP. Exactly three entries change: builtin registry hash and two new Kimi modules. Native checksum --check passes on that exact candidate. No executable behavior changes; existing Python QA remains applicable. Commit inventory before rebuilding the user-authorized local dev archive.
