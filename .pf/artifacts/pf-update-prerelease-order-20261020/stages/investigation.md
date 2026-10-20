# Исследование минимального version blocker

investigation-report: Serena показала единственный UpdateVersionSelectionPolicy.select
consumer в update-candidate discovery. Общая ResourceVersionPolicy также участвует
в knowledge constraints и snapshot comparison; менять её ключ нельзя.
Probe baseline.py воспроизводит отказ выбрать alpha2/final после alpha1.
Числовая часть и распознавание прежних numeric/v-prefix значений уже находятся
в ResourceVersionPolicy; update key может добавить только порядок suffix.

impact-analysis: локальный составной ключ в существующем maintenance owner;
короткие числа и lexical fallback используют прежнюю resource policy. Каналы
отбираются normalize до select и не изменяются. API/ошибки/record payloads прежние.
Никаких зависимостей, миграций, переносов классов или дополнительного framework.

Локально прочитаны packaging/version-specifiers.md, practices/sorting.md,
python-quality-context.md и python/toolchain.json. Product SemVer не подменяется
PEP440 нормализацией. Приоритет prerelease numeric/lexical и build metadata
сверяется с первичным SemVer 2.0.0; Python tuple sorting используется локально.
Архитектурные границы из oop-05 и принятого архитектурного checkpoint сохранены.

investigation-complete: причина известна и ограничена selection.
impact-understood: общий resource owner и незавершённый OOP защищены hashes.
Handoff: domain фиксирует только необходимые precedence правила.
