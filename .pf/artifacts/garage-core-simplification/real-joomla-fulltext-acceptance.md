# Real Joomla Fulltext Acceptance

Date: 2026-08-24
Status: pass

Evidence:

```text
python tools/smoke_garage_real_joomla_search.py
PASS: real Joomla article fulltext and source-tree metadata are searchable

python tools/processforge.py release-test --root . --no-clean --only smoke_garage_real_joomla_search
PASS smoke_garage_real_joomla_search
```

Covered behavior:

- real Joomla documentation articles are indexed as fulltext;
- real Joomla core source tree is indexed as metadata navigation only;
- article search finds the real phrase `Ядро использует префикс v1`;
- source-tree search finds the metadata resource `docs.joomla-core.v6-1-2`.
