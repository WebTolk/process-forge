# Core resources: передача

Primary/product-manifest.json среза pf121-oop-core-resources-20261018 содержит
18 final paths/raw hashes. Report.md, verification.json, native-acceptance-qualified.json,
parity-results.json, bootstrap-resolution.json, consumer-binding-resolution.json
и smoke-results-qualified.json фиксируют
source-only границу; исходная ошибка и успешные receipts сохранены неизменными.
Двенадцать функций и один constant перенесены; все шесть потребителей строгого
чтения Assignment и одиннадцать call targets мигрировали. Assertions сохранены.

Review acceptance и delivery подтверждаются собственными receipts; затем штатно
завершаются шесть exact Work. Перед новым scope — fresh PF context и перечитывание
девяти original architecture inputs. Передача не разрешает инфраструктуру.
Внешний контракт 1.2.0, writes/timestamps/lifecycle/recovery semantics сохранены.
Archive/install/Runtime/connected-host и OOP epic acceptance остаются открытыми.
