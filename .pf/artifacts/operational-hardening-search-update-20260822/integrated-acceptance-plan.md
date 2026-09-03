# Integrated Acceptance Plan

Run: `operational-hardening-search-update-20260822`

## Search

- Build fresh index.
- Change knowledge file.
- Verify stale detection.
- Run tick.
- Verify new content visible.
- Add file and verify visible after tick.
- Delete file and verify result disappears after tick.
- Repeat with a template fixture.
- Mark dirty through a PF resource event.
- Corrupt schema version and verify tick rebuilds.
- Run search while maintenance refreshes.

## Core Update

- Plan add/change/remove update.
- Apply with confirmation.
- Preserve unknown files.
- Block locally modified PF-owned files.
- Reject malicious paths.
- Inject file-operation failure.
- Verify incomplete update journal and recovery classification.

## Live Host

Live `/hooks` and `/mcp` trust checks require a host session and are recorded separately as not executed in this local slice.
