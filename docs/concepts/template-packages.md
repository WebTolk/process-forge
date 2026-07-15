# Template Packages

Template packages stay simple in the MVP.

Global templates live on the workplace surface. Project templates live under
`.pf/templates/` and can override global templates only when policy allows it.

The recommended directory shape is:

```text
templates/
  file/
    template-id/
      README.md
      payload-file.ext.tpl
```

`README.md` describes what the template is, when to use it, placeholders,
forbidden modifications, and validation hints.

Machine-readable `template.yaml` metadata is optional. It is useful for
automation, but a template directory with a clear README and payload files is
valid for MVP use.
