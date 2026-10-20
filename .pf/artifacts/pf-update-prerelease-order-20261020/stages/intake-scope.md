# Границы prerelease fix

brief: существующий select использует ResourceVersionPolicy, отбрасывающую
prerelease suffix; alpha2 и final не считаются новее alpha1.
scope: локальная политика выбора update records, SemVer порядок prerelease и
игнорирование build metadata. Публичные payloads, channels, file-only режим,
numeric/v-prefix shorthand и lexical warning сохраняются. Общие resource
constraints не меняются; новый продуктовый функционал не добавляется.
task-record: отдельный обязательный blocker fix перед заморозкой alpha1.
scope-accepted: разрешённые product файлы ограничены maintenance/versions.py,
tests/update_versions и собственной строкой inventory. OOP и alpha identity
здесь запрещены immutable capsule; публикация разрешена пользователем для новой Work.
Handoff: investigation проверит все update/resource consumers и нормативный порядок.
