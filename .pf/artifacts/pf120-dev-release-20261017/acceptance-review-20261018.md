# Итоговое primary review: приёмка фактического MCP

Дата: 2026-10-17 20:38 UTC. Результат: PASS в границах dev-поставки 1.2.0 / 8ea152b. Проверка выполнена после функциональной приёмки; subagent_policy.allow=false, независимое ревью не заявляется.

Сопоставлены immutable capsule, exact continuation, source/archive/install provenance, новый владелец фактически подключённого MCP и вызовы его инструментов. Новая единственная пара MCP запущена после post-apply checkpoint, launcher принадлежит Codex, script/workplace совпадают с установленной поставкой. Никакой новый независимый stdio для закрытия этого гейта не создавался. Сохранённый manifest, work/metadata.py и 1307 payload files совпали с финальным архивом; локальная конфигурация и пять защищённых файлов сохранились.

Все шесть context responses fresh/continue и полностью равны; Work valid/ready с прежним capsule checksum, разрешённый docs.python:root available, Work search ready. Медиана пяти actual-host вызовов после warm-up 2.021 с. Это время инструмента целиком на одном устройстве; сравнение с прежним одиночным вызовом не объявляется контролируемым A/B. Runtime ready, scheduler alive, тот же post-update instance, workers0/jobs0, raw_hooks=false/events=true.

Прежний consumer full PASS и 13 installed checks остаются исходными доказательствами; повтор всего suite после изменения только evidence не требовался. Единственный первоначальный source FAIL, его test-only исправление и полный финальный consumer suite описаны точно; single-run full final source PASS не заявляется.

Подтверждена доставка предыдущего evidence commit: обе remote dev = 246803873c78fe9c3fd77c3dec3b20aa63d3cc9b. GitVerse прочитан с токеном через существующий helper; секреты не записаны в URL, argv или evidence. Product files/index перед этой работой чисты; unrelated dirty state сохраняется. Новый commit ограничивается результатами этой Work.

Оставшиеся ограничения не скрыты: bounded shutdown history/partial metrics, прежние presence records, непроверенные платформенные варианты и новый реальный worker после последней установки. Для stable потребуются отдельная release-поставка и обычные release gates на её точном payload. Изменений продукта, private configuration, инфраструктуры, immutable inputs или истории в этом продолжении нет.
