# Пошаговая настройка workplace

Пошаговая настройка workplace (guided workplace setup) - это путь по умолчанию
для настройки новой рабочей машины с участием человека. Агент задаёт вопросы
блоками, обновляет `answers.yaml`, до применения создаёт `proposal.md`,
применяет workplace через существующую механику инициализации, запускает
`doctor-workplace` и записывает следующие шаги для создания ресурсов и
`project-onboard`.

CLI поддерживает файловый сценарий, но не является мастером, который работает
только в терминале.

Порядок остаётся строгим: сначала workplace, затем ресурсы workplace (знания,
шаблоны, инструменты, MCP, корни пакетов, platform contracts), затем подключение
проекта.

Агент может быть запущен из любой удобной папки. Место запуска не имеет
семантики: текущая папка не становится автоматически workplace или проектом.
Пошаговая настройка должна явно записывать пути установленного дистрибутива
ProcessForge, workplace, необязательных global agent root и реальных корней
проектов.

Исследование устройства в пошаговом режиме необязательно. Агент может предложить
его, если нужно разобрать уже существующие `AGENTS.md`, навыки, локальные
документы, платформы, цепочки инструментов, настройки MCP или корни проектов и
перевести их в сущности ProcessForge.

## Команды

```bash
python bin/pf.py workplace-setup start --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup review --workplace <workplace-root> --session-id first-machine
python bin/pf.py workplace-setup apply --workplace <workplace-root> --session-id first-machine --apply
python bin/pf.py workplace-setup status --workplace <workplace-root> --session-id first-machine
```

Артефакты сессии хранятся здесь:

```text
<workplace-root>/setup-sessions/<session-id>/
```

Создаются `answers.yaml`, `proposal.yaml`, `proposal.md`, `review.md`, `apply-report.md`, `agent-instructions.md` и `next-steps.md`.

## Блоки диалога

1. Размещение на машине: ProcessForge root, путь workplace, путь локальной документации, корни проектов.
2. Среда агентов: инструменты агентов, целевые файлы инструкций, глобальная политика AGENTS.
3. Необязательное исследование устройства: нужно ли читать существующие `AGENTS.md`, навыки, документы, платформы, цепочки инструментов, настройки MCP и корни проектов.
4. Приватность и безопасность: локальные пути, public `path_ref`, secrets, доверие к обновлениям.
5. Ресурсы: knowledge roots, package roots, инструменты, MCP servers, шаблоны.
6. Platform contracts: нейтральные по умолчанию; реальные platforms только при явном описании.
7. Координация: Director capability, default project mode и нужно ли сразу создать Director Office.
8. Первый проект: необязательный план немедленного `project-onboard`, включая project coordination mode.

## Инструкция для агента

`apply` создаёт короткий фрагмент:

```text
ProcessForge установлен в <processforge-root>.
Workplace находится в <workplace-root>.

Не копируйте ProcessForge в папки конфигурации агентов или проекты.

Не считайте текущую рабочую папку корнем проекта, пока оператор явно не выбрал
её для project onboarding.

Внутри подключённых проектов:
1. Сначала прочитайте .pf/START_AGENT_HERE.md.
2. Из корня проекта используйте python .pf/runtime/bin/pf.py.

Вне проектов используйте python <processforge-root>/bin/pf.py.
```
