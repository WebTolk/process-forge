# Alpha5: проверка реальных процессов после перезагрузки

Результат: PASS для установленной alpha5 и двух реальных процессов. Источник
`af68fecfc539959d2b732e45016f5d09a700ec3d`; build
`manifest:sha256:2df87b89853b2df2000e8da85d05fcc8c226b9c24ac92dd86e85af74c89365ee`.
Проверки выполнены Python 3.14.3 без изменения продуктового кода.

| Проверка | Выполненная команда или вызов | Результат |
| --- | --- | --- |
| Установленные байты и сохранность | `python -B -X utf8 .pf/tmp/alpha5-device-install-20261024/post_reboot_acceptance.py` | Exit 0; все 1500 managed hashes совпадают; конфигурация, оба файла индекса и восемь защищённых хешей сохранены |
| Native installed status | `<installed-cli> core-update status --core-root <registered-core>` | Exit 0; alpha5, incomplete_update=false |
| Native Workplace doctor | `<installed-cli> doctor-workplace --root <registered-workplace>` | Exit 0; 197 PASS, без FAIL/ERROR |
| Actual Runtime | Неизменённый physical_probe.py runtime; native server status и authenticated status_payload с прежним timeout | Owner/lock/readyz согласованы; actual loaded=installed alpha5; doctor exit 0, build current |
| Повторное наблюдение Runtime | `python -B -X utf8 .pf/tmp/alpha5-device-install-20261024/post_reboot_runtime_status.py` | Exit 0; первый запрос ready, scheduler_alive=true, status/scheduler errors отсутствуют |
| Actual MCP | Подключённые pf.actions.list, pf.context, точный pf.work.state | Contract 2, loaded=installed source/build, reload_required=false, context fresh/continue, Work valid/ready |
| Work material | Подключённые pf.work.search и pf.work.resolve с exact selectors | Coverage complete 7/7, 80 документов, 79 результатов Python; docs.python:root verified; чужой ресурс blocked/resource_not_in_work |
| Syntax private helpers | ast.parse трёх новых приватных помощников | PASS; pyc/cache не создаются |

Наблюдаемые процессы зарегистрированного Core запущены после apply и после
перезагрузки устройства. PID, команды, локальные пути и raw ответы сохранены
приватно. Свежее CLI или fixture stdio не использовались вместо connected proof.

Первое подробное наблюдение Runtime сохранило health=degraded и warning doctor;
следующий штатный authenticated status вернул ready и живой scheduler без ошибок.
Причина промежуточного состояния не установлена. Оба результата сохранены;
таймауты, guard и бюджеты не менялись.

Ранее выполненный registered pytest на точной копии установленного payload:
858 passed, 7 skipped, 383 subtests, exit 0; восемь native smokes также exit 0.
Повторная проверка всех 1500 хешей подтверждает применимость этих результатов.
Новых продуктовых изменений нет, поэтому полный корпус повторно не запускался.
Команды и receipts: installed-pytest.json, installed-native-smokes.json и
исходный test-plan.md. Source QA/review отдельно подтверждены revision и review-v2.

Global derived search остаётся stale/allowed_resources_changed с coverage 5/7;
точный Work material complete 7/7. Session/work/worker metrics явно partial.
Они не объявлены полными и не исправлялись в scope device acceptance.

Данные: post-reboot-acceptance.json и post-reboot-device-acceptance-decision.json.
Raw receipts сохранены под .pf/tmp/alpha5-device-install-20261024/.
