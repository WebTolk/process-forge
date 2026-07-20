# Base Technology Knowledge Packages

Base languages and web technologies are modeled as knowledge packages plus
capabilities. They are reusable input for application platforms, not platform
contracts of their own.

```bash
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.php --title "PHP Documentation" --package-root global --apply
python bin/pf.py knowledge-package-create --workplace ./workplace --id docs.web.html --title "HTML Documentation" --package-root global --apply
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.php --package-root global
python bin/pf.py knowledge-package-doctor --workplace ./workplace --package docs.web.html --package-root global
```

Typical base packages:

- `docs.php`
- `docs.web.html`
- `docs.web.css`
- `docs.web.javascript`
- `docs.web.accessibility`
- `docs.web.performance`

A domain platform includes the packages it needs:

```yaml
id: platform.example-app
requires:
  capabilities:
    - php
    - html
    - css
    - javascript
    - web.accessibility
    - web.performance
  knowledge_packages:
    - docs.php
    - docs.web.html
includes:
  knowledge_packages:
    - id: docs.php
      required: true
      load_policy: on_demand
    - id: docs.web.html
      required: true
      load_policy: on_demand
    - id: docs.web.css
      required: false
      load_policy: on_demand
    - id: docs.web.javascript
      required: false
      load_policy: on_demand
    - id: docs.web.accessibility
      required: false
      load_policy: on_demand
    - id: docs.web.performance
      required: false
      load_policy: on_demand
```

Do not create platform contracts for base technology knowledge. Use packages
and capabilities instead.
