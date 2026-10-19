status: passed

Создан `src/processforge_core/evolution/validation.py`: `KnowledgeCandidateValidationService().validate(data)` компонует неизменённые `KnowledgeCandidateTargetingPolicy` и `EvolvePrivacyPolicy`. Перенесено точное присваивание `EVOLVE_CANDIDATE_CATEGORIES`.

SHA-256 продукта: `136e1a67cf9c735e8a97b7cbf06d20c29ce350888cd866ee2cac8e257c236e2b`.

Доказательства в candidate artifacts: `proof.json`, `normalized-ast.json`, `verify.py`, `log.md`.

- Для `validate_knowledge_candidate`: `full_ast_equal`, `signature_equal`, `annotations_equal` — true после явно перечисленных замен имени, `self` и concrete owners.
- Для константы: полное AST-равенство и равенство значения — true.
- Для checks и обеих политик: `raw_equal` и `ast_equal` frozen-входам — true.
- Компиляция без импорта product modules успешна.
- Пять уникальных синтетических сценариев прошли однократно: порядок checks и Unicode, fallback/raw id/category/summary/private findings, исключение targeting с причиной, JSON TypeError и циклический JSON ValueError.

Текущее состояние assignment проверено: implementation/in_progress; checksum капсулы совпал. Serena/IDE недоступны, применён AST-анализ.

Main и прочие продукты не изменялись. Родительскому исполнителю остаются миграция consumers и parser choices, реальная композиция, copied-Core, affected scripts и штатные lifecycle transitions.