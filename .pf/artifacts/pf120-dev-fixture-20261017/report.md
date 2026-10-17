# Поправка constructor smoke: результат

2026-10-17, primary/test-maintainer. PASS тестовой поправки. Product logic, public CLI/MCP и схемы не изменены. Полный родительский source suite обнаружил несовпадающее ожидание inspect.signature; старый архив с этой проверкой не допускается к установке.

В существующем test_facade_constructor_and_late_callback_override сохранён точный список всех прежних имён и positional __match_args__. В список включён одобренный work_metadata; дополнительно проверены KEYWORD_ONLY и default None. Не ослаблены assertions late callback override, lazy construction, порядок commit/event, ошибки и replay. Новых тестов или production branches нет.

Существующий smoke_work_transition_commit_service.py: 7/7 PASS, exit 0. Python syntax и scoped git diff --check PASS. Inventory изменён ровно в одной строке; SHA256 канонических LF bytes da1e9da4a04f0e9249d6ab08e45506ad9b24e96f368e6d65d456cb1aef9cd2d3. Все прочие строки побайтно сохранены. Детали checksum.json, приватный native output в own scratch.

Primary review выполнено после правки: diff ограничен точным ожиданием и checksum entry, потенциальных продуктовых регрессий не добавлено. Независимый агент не использовался: capsule запрещает subagents. Полная финальная qualification выполняется родительской release Work на новом архиве; этот отчёт не заменяет её и не заявляет install/Runtime/connected-host acceptance.

Native lifecycle/doctors — closeout.json; полный commit и dual dev readback — отдельный publication receipt после commit. Передача: .pf/handoffs/pf120-dev-fixture-20261017.md. Не возобновлять terminal Work.
