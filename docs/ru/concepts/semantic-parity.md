# Semantic parity

Semantic parity сравнивает смысл process definitions, а не байтовое совпадение
YAML.

Проверяются:

- process id;
- run model;
- roles;
- stages;
- artifact definitions;
- gates;
- emitted events;
- required resources и tools.

Порядок ключей YAML и форматирование не должны ломать parity. Потеря stage,
gate, artifact definition или `run_model` является FAIL. Unsupported fields
фиксируются как WARN, чтобы их можно было явно обработать.
