# Официальные packs

Посмотрите готовые packs, входящие в поставку ProcessForge:

```bash
python bin/pf.py pack-list --origin official --available
python bin/pf.py process-list --origin official --available
```

Generic workplace оставляет их доступными, но неактивными:

```bash
python bin/pf.py workplace-init --profile generic --workplace ../pf-workplace --apply
```

Software workflow можно активировать профилем инициализации либо отдельной
командой:

```bash
python bin/pf.py workplace-init --profile software-development --workplace ../pf-workplace --apply
python bin/pf.py pack-activate --id processforge.official.software-development --workplace ../pf-workplace --apply
```

Проверьте активный каталог:

```bash
python bin/pf.py process-list --active --project-root ./my-project --workplace ../pf-workplace
python bin/pf.py process-show software-feature-development --project-root ./my-project --workplace ../pf-workplace
```

Процесс используется непосредственно из дистрибутива. Не копируйте его
определение из `examples/`. Если доступный процесс ещё не активирован,
ProcessForge сообщает id владеющего pack и команду активации.

Официальные packs остаются обычными пакетами данных. Пользовательские процессы
и packs создаются теми же authoring-инструментами и сохраняют ту же границу с
ядром.
