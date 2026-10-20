# Передача подготовки 1.3.0-alpha1

Objective: подготовить выбранную оператором первую альфу после оценки готовности.
Current status: source context fix принят и доставлен; alpha publication NO-GO.
Input artifacts: delivery.md, version-assessment.md, prerelease-ordering.json,
cumulative-source-summary.json, package.json, review-result.json.

Следующая самостоятельная scoped Work должна сначала проверить живой контекст,
выбрать точные identity и разрешить локальные знания PF/Python. Не возобновлять
terminal Work текущего исправления и не расширять её capsule.

Предлагаемая узкая область исследования и исправления:

- ResourceVersionPolicy и UpdateVersionSelectionPolicy: корректный порядок
  предварительных продуктовых версий и build metadata с исследованием влияния
  на остальные ресурсы/constraints. Не назначать заранее глобальную замену
  политики ресурсного версионирования.
- tools/smoke_runtime_no_domain_file_patterns.py: пропущенный pathlib.Path import.
- VERSION, common/release_identity.py, CHANGELOG.md и необходимые release notes:
  настоящее имя `1.3.0-alpha1`, состав принятого OOP checkpoint и совместимых
  функциональных изменений, известные пределы. Не переименовывать dev ZIP.
- Зарегистрированные pytest/Ruff/mypy, независимое ревью готового изменения,
  native cumulative source gates и применимый supervisor-stress из разрешённого
  полного исходного checkout. Содержимое ZIP не проверять, archive-test не запускать
  согласно действующему указанию пользователя.

Files not to touch: незавершённые OOP54-55 и чужой dirty/staged слой; утверждённые
capsules/process versions; исторический stable 1.2.0 и stable channel.

Known issues: настоящий connected MCP после текущего source fix всё ещё stale на
исходном снимке; установленный Core в этой Work не обновлялся. До полного закрытия
исходной карточки нужен отдельный разрешённый native Core delivery и реальный
host reconnect/readback. Independent stdio/in-process adapter не заменяет эту приёмку.
Не повторять прежний core-update-20261020T081547Z и завершённый App Server restart.

Next recommended action: исправить два source препятствия в отдельной области,
принять настоящий alpha source candidate, собрать пакет и получить отдельное
решение оператора о публикации/установке конкретных подготовленных байтов.
Этот документ не запускает следующую задачу и не даёт инфраструктурных прав.
