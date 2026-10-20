# Передача независимому reviewer

Дата: 2026-10-20T11:41:17.835Z. Основной агент -> independent reviewer.
Предмет: готовая реализация pf-context-parity-20261020; только source/doc/checksum/test review.
Основная Work: garage-pf-context-parity-20261020-diagnose-and-fix-pf-cli-mcp-context-co.
Кандидат: primary/candidate.json; точные байты заморожены после scoped форматирования и проверки.
Исследование/модель/архитектура/правила Python: primary/{investigation,domain,architecture,python-knowledge}.md.
Исходный отказ: private regression-before.log; результаты текущих проверок: primary/iteration-checks.json.
Reviewer получает отдельную ограниченную Work и sibling artifact/scratch namespaces pf-context-parity-review-20261020 для непересекающейся записи.
Проверить actual diff от HEAD, false fresh/stale, live reads и races, active selection, raw fingerprint/public contract preservation, отсутствие Core->Main пути, контроль затронутой области и ограничения доставки.
Основной агент не пишет в reviewer namespace; итог reviewer передаётся сообщением вместе с SHA и статусом. Parent captures received review under primary, не расширяя свою immutable read scope.
Повторять успешные проверки только при новом concern или изменении байтов. Продукт reviewer не меняет.

