# Ограниченная реализация

changed-files: maintenance/versions.py, tests/update_versions/test_selection.py,
одна checksum row и собственные документы. Candidate hashes — candidate.json.
change-summary: приватный update key, сравнение prerelease в select и sorting;
normalization, channels, payloads, общий resource key не меняются. Готовый regression
17 PASS; исходный 10 FAIL/7 PASS подтверждал именно дефект.
implementation-scope-respected: guards чужого OOP и snapshot сохранены; прежние
методы имеют равный AST. Дальнейший рефакторинг не запускался.
Handoff: assurance проверит зарегистрированные QA и реальные пределы typing.
