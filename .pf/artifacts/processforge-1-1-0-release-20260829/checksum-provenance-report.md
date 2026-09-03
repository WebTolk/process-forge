# Checksum provenance релиза 1.1.0

## Решение

Основной checkout физически содержит часть text files в CRLF, несмотря на
`.gitattributes` с `eol=lf`. Поэтому inventory, рассчитанный напрямую в этом
checkout, не воспроизводился в clean Git worktree.

В `checksums/processforge.sha256` перенесен точный inventory из clean release
candidate commit `8f291ba2f1265d0b426cd4df506d58ba1985a5b5`.

## Доказательства

- candidate checksum validation: PASS;
- source public release-test в candidate: PASS;
- extracted archive public release-test: PASS;
- inventory SHA-256 в candidate и основном checkout:
  `4E3A793614519BA075B37E046FA31A11D621C7A3D39EF2D7ACC8B1A1854FCFF8`;
- unrelated working-tree files не нормализовались и не перезаписывались.

До коммита проверять inventory следует в clean LF checkout. Текущий старый
working tree может показывать byte-level mismatch только из-за его физических
CRLF line endings; release ZIP и clean candidate являются проверенной границей.
