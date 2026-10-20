# Приёмка подключённого MCP и CLI

Результат: PASS. Настоящий подключённый MCP, установленный CLI и source CLI
согласованы на неизменном ctx-20261020-072238-da5df2: fresh / continue.
Оба CLI имеют resources fresh, execution ready, blockers [], stale_resources [].
Exact Work подключённого MCP valid/ready. Разрешённый docs.python:root доступен,
невыбранный docs.joomla:root отклонён resource_not_in_work.

MCP этой сессии сопоставлен по цепочке родителя текущего tool host, запущен
после единственного apply 12:46:59 UTC. Два исправленных Core module и MCP entry
побайтно совпадают с source. См. provenance.json и comparison.json.
Snapshot SHA-256 bd7dc7f033fe9f95f4c6903ea168868251db7666ef536c12479f7bcae667a05a
не изменился. Установка, refresh, restart и независимый stdio не выполнялись.

Критерии исторической карточки:
1. Структурированные текущие CLI/MCP ответы и snapshot identity сохранены.
2. Host ancestry, процесс/время старта, installed entry и fingerprints проверены;
   одинаковая строка версии не использована как единственное доказательство.
3. Ранее принятый source fix устраняет LF/CRLF расхождение; данные не обновлялись
   ради маскировки результата. Исходный commit 526c5d13e42e96693802760cce35fe896e208708.
4. Каноническая политика даёт одинаковые freshness/readiness/policy для тех же inputs;
   текущая Work не получила продуктовых или инфраструктурных прав.
5. Предыдущая adapter-fixture-parity.json сохраняет fresh/fresh/stale/fresh и
   source changed reason; новая проверка отдельно доказывает настоящее подключение.
6. 16 pytest +4 subtests, Ruff/mypy/context smokes и независимое source review
   переиспользованы для тех же побайтно проверенных Core modules. EN/RU docs уже
   доставлены принятым source commit. Новой продуктовой правки здесь нет.

Доказательства source: ../pf-context-parity-20261020/primary/review-result.json,
adapter-fixture-parity.json, assurance.md. Доказательства установки:
../pf-context-device-install-20261020/installed-verification.json,
context-parity-after-install.json. Новые полные приватные ответы и process roots
сохранены в собственном .pf/tmp/pf-context-connected-verify-20261020.

Пределы: stale derived reports и частичное покрытие проектных метаданных сохранены;
они не объявлены исправленными. Проверка не означает готовности всей альфы,
новую упаковку или завершение OOP54–55. Python QA для продукта not_applicable:
исполняемый продуктовый код не менялся. Отдельные source исправления идут далее.
