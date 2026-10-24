# Завершение доставки alpha5 на устройство

Native установка core-update-20261024T010255Z уже была выполнена один раз.
После перезагрузки оператора получены недостающие доказательства фактических
Runtime и подключённого MCP. Оба используют source af68fecf и одинаковый
loaded/installed manifest build alpha5. Device acceptance — PASS.

Code-assurance завершён штатным PF transition; исходная capsule и snapshot
сохранены. Решение и проверенные результаты находятся в
post-reboot-device-acceptance-decision.json и post-reboot-test-report.md.
Старые pending отчёты и guard refusal сохранены как контрольная точка.

Delivery profile выполнен в установочной части предыдущего этапа: qualified
dev archive, native apply, backup/control/preservation, installed pytest и
smokes. Его завершающие actual process gates теперь PASS. Новый архив,
повторный apply и повторная публикация alpha не требуются. Source release и
alpha metadata доставлены отдельной source Work; здесь они не изменяются.

Release readiness для этой device Work — approved. Ограничения global derived
search и partial Runtime metrics указаны в итоговом отчёте и сохраняются.
Широкий рефакторинг и инфраструктурное обслуживание в этот scope не входят.

По окончании native lifecycle новые переносимые доказательства фиксируются
отдельным локальным коммитом поверх общего dev head и направляются в оба
remote с точным readback. Это отдельный учёт evidence, а не новая установка.
Original dirty checkout/index сохраняются; фактические commit/readbacks будут
записаны отдельной delivery receipt после исполнения.
