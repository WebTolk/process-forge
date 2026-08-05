# Knowledge hub

Knowledge hub - file-first internal workspace для reviewed learning bundles и
package releases:

```text
knowledge-hub/
  hub.yaml
  inbox/imports/
  candidates/index.yaml
  packages/docs.example/
  updates/
```

MVP импортирует bundles, индексирует candidates, строит package
`candidate-notes.md`, пишет changelog/release plan, создаёт package zip и
локальный манифест обновления.

Hub не переписывает curated docs молча. Candidate notes проходят review, а
released packages распространяются через существующую update system.

## Routing by target

Hub сохраняет `target`, `applicability`, `generalization`, `routing` и
`promotion` при import. Package build выбирает candidates только когда
`routing.recommended_destination.id` или `target.id` совпадает с package id.
`source_context` считается evidence, а не destination.

Candidate, который был observed на child platform, не попадает в parent package
только из-за parent platform в source stack. Если candidate target указывает на
parent package, но promotion не approved, build помещает его в
`resources/incoming-learnings.md` под заголовок `Unreviewed parent-platform
candidates`, а не в curated `candidate-notes.md`.
