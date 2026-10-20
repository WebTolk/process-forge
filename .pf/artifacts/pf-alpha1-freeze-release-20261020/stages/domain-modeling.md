# domain-modeling — freeze alpha1

domain-notes: alpha1 — предварительный выпуск из принятого dev checkpoint. Название не означает завершение всего OOP epic. Стабильный выпуск остаётся 1.2.0.

domain-model: source commit/tree → immutable v1.3.0-alpha1 → один ZIP/sidecar → одинаковые mirrored assets → mutable alpha update metadata. Sidecar исключён из собственного ZIP, historical copy коммитится после исходного коммита во избежание self-reference.

domain-rules: tag не перемещать, опубликованные bytes не заменять; изменение кандидата возможно только до публикации. API/CLI/MCP payloads и file-only работа сохраняются. Alpha channel не подменяет stable, main не продвигается. Не включать unaccepted OOP54–55; не устанавливать release на устройство.

domain-rules-captured: эти ограничения применяются при source freeze, упаковке и readback. Handoff: architecture определяет один чистый кандидат и минимальные проверки.
