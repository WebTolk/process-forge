# Приёмка исправления CLI/MCP: исходный код

## review-findings
Независимое ревью: PASS, существенных замечаний нет; сообщение reviewer принято в review-result.json.
Проверены все семь frozen hashes, фактический diff и границы классов, чистота raw fingerprint, четыре собственные строки inventory и сохранность семи inherited OOP строк.
Reviewer Work штатно run_completed, assignment done; точные selectors, report SHA и receipt SHA в review-result.json.

## test-plan
Точечные регрессии воспроизводят исправляемый LF/CRLF дефект, реальные изменения и guards.
Existing context-policy/context-lock/context-core группы проверяют прежние политики stale/broken, pinned capsule и работу default Core без Main/transport.
Одна нормальная чистая дистрибуция и private native project проверяют CLI и один долгоживущий in-process MCP adapter на равном снимке.
Отдельно тот же repaired Core читает исходный снимок настоящего проекта и реальные source/installed pack DATA.

## test-cases
Manifest/classifier LF<->CRLF; content/comment/lone CR; same-size/mtime; read-after-write; изменение между первым fingerprint и probe; project/workplace raw strictness; add/remove; inactive/no-workplace; raw fields/digest; import без Main/transport.
Adapter фазы: initial LF fresh; CRLF того же текста fresh без refresh; real package version change stale; восстановление LF fresh в том же загруженном adapter. Snapshot SHA не менялся.

## test-report
16 pytest passed +4 subtests, exit0; source red regression до фикса зафиксирована в scratch.
Три existing context smoke группы: exit0; Core группа содержит 13 PASS checks.
existing-snapshot-source-parity.json: исходный ctx-20261020-072238-da5df2, прежний snapshot SHA, обе реальные distribution DATA дают [] reasons.
adapter-fixture-parity.json: все четыре CLI/MCP проекции совпали; snapshot unchanged.
Прямая проверка nested materialized distribution также дала CLI=MCP, но stale из-за двух changed matched_rules.source путей — это другой provenance, не false EOL drift. Точный annex: nested-candidate-classification.json.
Source-only clean candidate checksum validation и release-check прошли. Нативная упаковка materialized tree отказалась без Git source provenance; будет повторена в release-delivery из принятого Git commit.
ZIP contents/audit/tests исключены прямым последующим указанием пользователя. Доказательство архива не подменяется распаковкой или запуском archive-test.

## code-quality-report
Зарегистрированные команды и версии в iteration-checks.json; QA root разрешён через фактический workplace registry.
Python3.14.3; pytest9.1.1; Ruff0.17.1; mypy2.4.0.
Ruff lint PASS, формат четырёх Python-файлов PASS, mypy четырёх файлов PASS (follow-imports=silent/ignore-missing-imports). Все exit0, актуальные candidate hashes совпадают.
Типизация зависимостей, общий lint и coverage Core не заявлены; зависимости/security/UI здесь не менялись, дополнительные широкие проверки не требуются.
Повторная архитектурная сверка D01/D02/D05/D06/D07/D09/D11 и R03/R06/R07/R10/R12: прежние owners и imports, live bytes, immutable evidence/capsules, file-only и scoped ownership сохранены.

## assurance-complete
Приёмка соответствует bounded source fix. Actual installed Core/MCP ещё не обновлялись; действующий подключённый хост не объявляется принятым через library/adapter proof.
Следующий этап: selective source commit, оба dev, native pack из clean Git source, alpha readiness report и конкретная дальнейшая delivery boundary.

