# Integrated assurance reviewer report

- Agent: `codex-remediation-first-review`
- Session: `pre-release-remediation-20260730-integrated-review`
- Lease: `lease-remediation-integrated-review-20260730`
- Scope: `PF-AUD-001—PF-AUD-006`
- Result: **FAIL**

## Decision

`PF-AUD-001—004` и `PF-AUD-006` независимо подтверждены как исправленные.
`PF-AUD-005` остаётся blocking partial fix.

Оба blocker первого review закрыты:

```text
public-gate only+skip: exit=1, calls=0
reusable v2 files: []: PASS
reusable v2 missing files: FAIL
```

Transient observations после freeze:

```text
template-create + doctor + schema: PASS
platform include-levels: PASS
knowledge hub build + package schema: FAIL
```

## Sole blocker

`knowledge-package-build-from-candidates --package docs.example --version
1.1.0 --apply` возвращает `0`, но создаёт:

```yaml
kind: knowledge_package
```

Authoritative package schema запрещает это значение. Source
`tools/processforge.py:13204,13210-13211` не выполняет schema/doctor
postcondition и публикует success. Release/update-manifest positive control
затем успешно упаковывает такой build.

## Green assurance set

- security boundary smoke;
- exact 8-manifest schema inventory;
- aggregate/public group smoke;
- template/platform generator alignment smoke;
- doctor contract smoke;
- registry preservation smoke;
- platform include-level regression;
- invalid YAML full-tree no-mutation fingerprints;
- repository schema validator;
- targeted py_compile and diff check.

## Required next action

Исправить semantic kind hub-generated package, добавить schema postcondition и
прямую manifest validation в build/release regressions. После этого повторить
только hub build/schema и release/update surface перед следующим
интеграционным gate.

Полное evidence:
`.pf/reviews/pre-release-remediation-integrated-review-20260730.md`.
