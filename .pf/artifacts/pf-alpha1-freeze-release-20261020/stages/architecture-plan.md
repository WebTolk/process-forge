# architecture-plan — freeze alpha1

architecture: текущий layout и owners сохраняются; меняются только release identity, docs и Path import. Product source фиксируется отдельным source commit, затем checkout в собственном .pf/tmp; staging/index чужой работы сохраняется. Суммарный source release-test и supervisor-stress выполняются на этом clean commit, pack — на том же exact tree.

implementation-plan: backup/guards → Path+VERSION+notes → focused Python QA → selective source commit и оба dev → clean checkout и cumulative source gates → frozen tag/readback → один pack → mirrored prerelease assets и remote byte hashes → alpha metadata/historical sidecar → native lifecycle/doctor и итоговый evidence commit.

decision-log: не выполнять новые features, OOP, общий Core lint/type audit или ZIP inspection. Обязательные QA относятся к изменённому коду; существующий Core typing debt не расширяет freeze scope. Если source gates выявят дополнительный blocker вне grants, его надо явно зафиксировать и оформить отдельную ограниченную Work, а не расширять capsule.

architecture-plan-ready: source/metadata paths и прямое разрешение публикации есть; процедура использует существующие native commands и token transport. Handoff: implementation замораживает source candidate.
