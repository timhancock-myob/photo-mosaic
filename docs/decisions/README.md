# Architecture decision records

One short file per significant decision. Number sequentially; never rewrite an accepted record — supersede it with a new one and update the old record's status.

Format: **Status**, **Context**, **Decision**, **Consequences**.

| ADR | Title | Status |
|---|---|---|
| [0001](0001-local-first-deployment.md) | Local-first deployment, hosted-ready seams | Accepted |
| [0002](0002-grid-columns-and-rows.md) | Grid: user sets columns and rows independently | Accepted |
| [0003](0003-neighbour-seam-matching.md) | Matching: cell fit plus neighbour seam blending | Accepted |
| [0004](0004-default-reuse-policy.md) | Default reuse policy: reuse freely | Accepted |
| [0005](0005-developer-setup-distribution.md) | Distribution: developer setup only for v1 | Accepted (commands amended by 0006) |
| [0006](0006-poe-task-runner.md) | Task runner: poe tasks in pyproject.toml, no Makefile | Accepted |
| [0007](0007-seams-relative-to-base.md) | Seams are measured against the base photo's own edges | Accepted (refines 0003) |
