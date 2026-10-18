# Оставшийся предрелизный блокер: sessionless search smoke

2026-09-07. Статус: подтверждён до текущих изменений; не исправлялся в задаче документации D01-D08.

Полный source release-test завершился RESULT: FAIL: 102 PASS, 1 FAIL, 924.932 секунды. Отказ: tools/smoke_garage_no_hooks_sessionless.py:85, ожидается один найденный ресурс, получен empty_corpus и total=0. Последующие проверки не выполнялись из-за --fail-fast; самостоятельный git diff --check прошёл отдельно. Исходный полный report и trace сохранены как source-full-1-report.json/.md и source-full-1-trace.ndjson, stdout — source-full-1.json.

Причина тестового несоответствия по коду: add_fixture_resource в tools/smoke_garage_no_hooks_sessionless.py:46 добавляет ресурс только в project snapshot (resolved.available_knowledge_resources и local_search_resources). ResourceSearchService в src/processforge_core/garage.py:135 берёт индекс из workplace_search_runtime_snapshot. tools/processforge.py:23429 строит этот каталог из зарегистрированных пакетов и templates Workplace, а не из вручную дописанного project snapshot. Fixture не регистрирует свой пакет в Workplace, поэтому каталог пуст.

Воспроизводимость: baseline-search-failure.json подтверждает тот же отказ на изолированной публичной копии 933 tracked entries из HEAD 1aecc18b6824204ca45ab30241b92d26e6d583a5. Все файлы копии получены git show HEAD; основной worktree не изменён. В baseline не было текущего required-output fix и правок документации. Exit 0 диагностического helper означает подтверждённое воспроизведение FAIL теста, а не PASS продукта.

Рекомендуемая отдельная задача: привести тестовую регистрацию ресурса к текущему Workplace-контракту, сохранить проверки отсутствия hooks/session/daemon и ожидаемого search/resolve; затем повторить полный source release-test до терминального результата. Не ослаблять assertion, не менять поиск для поддержки неавторизованной fixture, не объявлять оставшиеся тесты пройденными.

До устранения блокера и нового полного прогона релизная готовность не подтверждена. Упаковка/извлечённый архив/публичная публикация также не квалифицированы этим заданием.
