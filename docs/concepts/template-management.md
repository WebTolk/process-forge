# Template Management

Template Management keeps reusable templates practical. A template package can be only a folder with a `README.md` and payload files.

Default layout:

```text
templates/file/<template-id>/
├── README.md
└── payload files
```

`template.yaml` is optional. It is useful only when the template needs extra compatibility metadata, payload lists, or platform constraints.

The README should document purpose, when to use the template, placeholders, adaptation rules, forbidden changes, and verification hints.
