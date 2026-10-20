# Публикация alpha1

delivery-report: report.md, package.json, tag-readback.json, draft-assets-verified.json,
publication-readback.json и alpha-metadata-checks.json фиксируют настоящее состояние.
Оба public release опубликованы как prerelease; source tag одинаков, четыре
удалённых size/SHA-256 совпадают с canonical archive/sidecar. Release ids:
GitHub 418489329; GitVerse 548932813. Stable latest остаётся v1.2.0.

release-readiness-decided: alpha1 заморожена и опубликована; 274/274 source,
pytest17 и supervisor-stress PASS. Содержимое ZIP не инспектировалось, archive-test
не запускался по прямому указанию пользователя. Эти пределы не скрываются.
delivery-profile-run-or-skipped-with-reason: выполнена source/publication часть
профиля и mirrored byte-hash readback; исключены archive-content/installed/host
проверки, установка и инфраструктурные действия. Alpha metadata schema/discovery
и исключение alpha из stable PASS, stable manifest не изменён.

После native terminal отдельный metadata/evidence commit отправляется в оба dev,
readback сохраняется приватным git-delivery.json. Тег/asset bytes не меняются.
Handoff: evolve завершает ровно этот release; OOP остаётся на паузе.
