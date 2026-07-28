# Порядок инициализации

Используйте этот порядок для новой установки ProcessForge, workplace и проекта:

1. Установить дистрибутив ProcessForge.
2. Проверить сам ProcessForge.
3. Для настройки с участием человека по умолчанию запустить пошаговую настройку
   workplace; direct workplace-init использовать только для явно автоматического
   пути.
4. Настроить константы путей и корневые каталоги.
5. Настроить корни знаний, особенно корни локальной документации.
6. Зарегистрировать инструменты и MCP servers.
7. Создать или импортировать пакеты знаний.
8. Создать повторно используемые шаблоны.
9. Создать platform contracts.
10. Подключить проект.
11. Создать рабочий сценарий run/task.
12. Создать собственные процессы, если они нужны.

## Почему platform contracts создаются позже

Platform contract не является первичным ресурсом. Это композиция поверх уже
существующих packages, templates, tools, MCP servers, processes, coding
standards и capabilities.

Не начинайте с platform contract, если его обязательные packages, templates или
tools ещё не созданы. Сначала создайте или зарегистрируйте зависимости, затем
создавайте platform contract.

Base languages и web technologies относятся к этим dependencies. Моделируйте их
как knowledge packages и capabilities, затем подключайте из platform contracts,
которым они нужны.

Тяжёлая локальная документация и исходники не записываются в public package
manifests. Ссылайтесь на них через workplace knowledge roots и package resources
с `path_ref`.

## Agent environments

Не копируйте весь репозиторий ProcessForge в `.codex`, `.claude`, `.agents` или
похожие папки конфигурации агентов.

Установите ProcessForge один раз как инструмент, инициализируйте workplace и
добавьте короткую инструкцию в конфигурацию агента: где установлен ProcessForge
и что проектные инструкции находятся в `.pf/START_AGENT_HERE.md`.
