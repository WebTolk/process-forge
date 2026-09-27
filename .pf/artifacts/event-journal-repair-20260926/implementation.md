# Implemented append protection and tested recovery utility

Changed public paths: tools/processforge.py (append_process_event and one smoke registry entry), tools/smoke_process_event_concurrency.py, EN/RU session-telemetry docs, checksums/processforge.sha256. No event identity, hook routing, raw ingress format or schema changes. Existing source edits are retained; originals/baseline and scoped.patch provide exact delta independent of dirty main HEAD.

Project append uses existing registry_file_lock with immediate dead-owner recovery through its OS guard; check/dedup and UTF-8 binary write+flush+fsync share that lock. Lock SystemExit becomes a RuntimeError handled by service request machinery. Hooks dispatch after lock release, including the existing duplicate-event behavior. Actual four-writer regression reproduced three copies before the fix and passes unchanged after it.

Private repair.py has read-only plan, isolated test and explicit apply modes. It retains the complete original prefix and raw fragment, refuses unexpected/multiple/unterminated corruption, writes only the exact 24-byte historical body as equal-length spaces, preserves CRLF and offsets, verifies complete original prefix except that range plus appended suffix and file identity. One hundred concurrent fixture appends survived; a competing prefix replacement caused an abort without overwriting the new content.

The live journal has not yet been modified. Source-only concurrency fix will join the remaining T10 changes in the next standard updater package; no manual installed-file changes. Candidate public fixture is durable private QA input only. Browser not_applicable. Remaining checks and live repair are assurance/delivery obligations, not claimed complete here.
