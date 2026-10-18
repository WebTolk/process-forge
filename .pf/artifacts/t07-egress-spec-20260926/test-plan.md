# T07: план документной проверки

Объект: итоговый пакет T07 после implementation stage. Исполнитель проверки — основной агент; pinned process запрещает subagents, независимая внешняя экспертиза здесь не заявляется. Новый механизм передачи данных отсутствует.

| Проверка | Метод и ожидаемый результат |
|---|---|
| Q01 | Прочитать UTF-8 документы без replacement characters/BOM/trailing whitespace; все локальные Markdown targets существуют |
| Q02 | Пересчитать SHA256 семи source files и проверить AST symbol/line для всех 20 anchors |
| Q03 | Сопоставить реальные R01–R09 из scope и H01–H14 из threat model с matrix; нет дубликатов, неизвестных ссылок или незакрытых требований/угроз |
| Q04 | Проверить пять JSON-примеров: конечная форма recipient view, допустимые решения, block без body, private-only fields отсутствуют в view, allow/redact согласованы с пометкой изменения |
| Q05 | Подтвердить, что все 28 engine cases остаются future_implementation/not_run; не выдавать эти expected outcomes за результаты |
| Q06 | Пересчитать baseline 3736 файлов, проверить отсутствие новых product files вне .pf и выполнить git diff --check |
| Q07 | Содержательное чтение: authorization против disclosure, downgrade/unknown, native bypass, current revocation, dispatch ambiguity, immutability/export, required semantics и false positives |
| Q08 | Перед закрытием и после завершения проверить actual Work lifecycle, run-doctor и hashes зарегистрированных stage evidence |

Q01–Q06 воспроизводятся `python -B .pf/artifacts/t07-egress-spec-20260926/document-check.py document-check-assurance.json`. После delivery применяется новый filename `document-check-final.json`; существующие наблюдения не перезаписываются. Q07 записывается в review-findings; Q08 в отдельных lifecycle evidence. Проверка схемы примеров локальная и документная: её результат не утверждает существования предлагаемого API в product schemas.

Runtime smoke будущего privacy engine: **not_applicable**, engine не реализован; обязательные будущие тесты перечислены в acceptance-matrix.json. Browser verification: **not_applicable**, UI/страницы не менялись. Packaging, build, install и external provider calls: **not_applicable**, поставка внутренних Markdown/JSON artifacts. Применение platform/toolchain overlays для backend отложено до выбора backend в I01; текущие проверки используют стандартный Python и уже установленный PF CLI только для чтения/диагностики Work.

Тестовые данные примеров синтетические; реальные secrets не читаются и не отправляются. Успех документации не снимает исторический T06 metadata finding и не подтверждает installed runtime filtering.
