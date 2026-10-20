# Исследование фактического подключения

investigation-report: живые ответы сохранены отдельно в собственном .pf/tmp:
connected-context, connected-project-state, connected-work-state, installed-cli,
source-cli, resource-positive и resource-negative. Все три поверхности дают
fresh/continue на ctx-20261020-072238-da5df2; оба CLI имеют fresh resources,
execution ready, blockers [], stale_resources []. Exact MCP Work valid/ready.
Поиск MCP ready; частичное покрытие метаданных двух проектных ресурсов и stale
derived reports не являются stale context или блокерами этой проверки.
Ресурс docs.python:root разрешён; docs.joomla:root отвергнут resource_not_in_work.

MCP найден по цепочке родителя текущего tool host, а не по новейшему PID.
Он запущен 12:55:39 UTC после apply 12:46:59 UTC из настроенного installed Core.
Raw hashes source_check.py, snapshot_sources.py и MCP entry совпадают с исходниками.
Версия обеих установок 1.2.0. Snapshot hash не изменился; refresh и update отсутствуют.
Полные приватные process/module roots находятся только в собственном scratch;
переносимая сводка — provenance.json.

Исторические source доказательства review-result.json, adapter-fixture-parity.json
и assurance.md относятся к тем же двум Core bytes: 16 pytest +4 subtests,
Ruff/mypy/context smokes PASS, независимое source review PASS; четырёхфазная
проверка fresh/fresh/stale/fresh не подменяла actual-host приёмку. Новая живая
проверка закрывает именно ранее отсутствовавшее фактическое подключение.

impact-analysis: продуктовые файлы не меняются. Закрытие затронет одну planning
карточку через native task-complete; dry-run принят. Архивы, OOP и остальные
карточки не входят в результат. Python QA неприменим к этой документальной Work;
живые CLI/MCP проверки обязательны и выполнены.

investigation-complete: источник расхождения LF/CRLF уже исправлен и установлен;
новый подключённый хост фактически согласован с CLI без обновления снимка.
impact-understood: текущая Work только фиксирует доказательства и native closure.

Handoff: domain-modeling разделит контекст проекта, ресурсы, Work и source/device/host proof.
