# Доставка blocker fix

delivery-report: готов только минимальный source fix с candidate.json/checks.json.
После native terminal отдельный commit направляется в оба dev; exact receipt
сохраняется в собственном .pf/tmp/pf-update-prerelease-order-20261020/git-delivery.json.
release-readiness-decided: blocker fix принят в source; alpha1 замораживается
следующей Work с реальной release identity и суммарными source gates.
delivery-profile-run-or-skipped-with-reason: release/ZIP suite здесь неприменим
к отдельному исходному fix; общий release suite будет выполнен один раз на
окончательном чистом alpha source. ZIP содержимое не проверять по указанию пользователя.
Handoff: evolve, native terminal и отдельная доставка принятого source.
