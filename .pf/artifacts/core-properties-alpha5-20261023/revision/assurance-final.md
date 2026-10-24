# R03 source/archive assurance: PASS

Source commit `af68fecfc539959d2b732e45016f5d09a700ec3d`, tree
`13c36327a4f4aa0561a61e66f822e9230eb503f8`,31 task files.
Независимый native reviewer дал CODE GO/pass без открытых findings; исходный
CP-A5-R01 на b2dc2ec0 исправлен и проверен настоящими adapter probes.

Registered full pytest:858 passed,7 прежних skips,383 subtests; Core97 passed.
Native source full:274/274 PASS. Scoped quality пройден, новых lint/type
diagnostics нет; старый монолит в целом lint/type clean не объявляется.
Owner combined branch coverage97%, три missing statements сохранены в отчёте.

Полный native archive R3: настоящий bin/pf.py entrypoint вернул0; ordinary
nested `release-test --public --timeout-scale3` и итоговая archive команда PASS.
ZIP SHA256 `5bba94c513b5bbf3261f1c64ca8a8f537b2d8e4aac47d89597a70ba230eb79d3`,
sidecar SHA256 `8d9ab711c2edda53c1037bb0ddd2bb2972462b34bdd0aa32b6d457606b5027e9`.
Архив и source bytes не менялись между попытками. Actual ZIP inventory и
relocation/default composition прошли отдельно:1501 entries/1500 managed files.

Неудачные попытки сохранены: первый source full/negative JSON, archive1200s
timeout, второй archive full FAIL1 с утраченной штатным outer tail причиной.
Третий native archive действительно PASS0. Дополнительный private collector
вернул1: Windows bin/pf.py делегирует через os.spawnv, profiler остался в shim
и не сохранил nested JSON. Этот collector failure не переписан; entrypoint exit0
и явный native full PASS записаны отдельно в native-archive-r3-native-result.json.
Количество nested checks не придумывается. Никакой guard/selection/product code
для получения PASS не менялся. Это qualified native результат конкретного
повтора; причины старых нерепродуцированных отказов не объявлены исправленными.

Final package.json и assurance-decision.json запечатаны из настоящих source,
archive, actual payload и independent-review evidence. Device installation,
actual services, публикация/tag/assets/metadata остаются отдельными следующими
действиями; сейчас их успех не заявляется.

Source CLI в nested checkout показал stale только из-за двух project-relative
classifier provenance refs. Semantics и bytes classifier совпадают, установленный
Core даёт точную классификацию действующего snapshot. Snapshot не обновлялся;
после actual alpha5 apply всё равно обязателен физический strict context check.
