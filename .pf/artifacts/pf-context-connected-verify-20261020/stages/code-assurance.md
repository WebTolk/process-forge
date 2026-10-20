# Проверки документальной приёмки

review-findings: основной агент повторно проверил фактические ответы и связность
source/device/connected доказательств. Это документальное ревью, а не новое
независимое source review; прежнее независимое review-result.json сохранено.

test-plan: сопоставить структурированные ответы, resource denial, snapshot hash,
native task/run состояние и отсутствие постороннего изменения очереди/index.
test-cases: текущие три поверхности, exact Work valid/ready, docs.python разрешён,
docs.joomla отвергнут; native task-doctor/run-doctor; исходный снимок и исходный index.
test-report: живые команды и exit0 находятся в raw evidence; assure.py проверяет
JSON и единственную разрешённую замену статуса в run, отчёт — assurance.json.

code-quality-report: pytest/Ruff/mypy продукта not_applicable — в этой Work
не меняется исполняемый продуктовый Python-код. .pf/artifacts/python-quality-context.md
прочитан. Scratch служит сбору фактов, не входит в public source candidate.
Обязательные product QA для двух следующих правок остаются отдельными gates.

assurance-complete: PASS live comparison и native doctors, снимок сохранён,
единственная целевая карточка done, постороннее содержимое run и index сохранено.
Handoff: release-delivery — отдельный локальный коммит и обе удалённые ветки dev.
