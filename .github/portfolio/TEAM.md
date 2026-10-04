# Agent operating team

These are role instructions for supported Codex agents, not legal officers, paid employees, or already-running processes. Jordan is CEO; he sets goals, approves spending and business commitments, and provides owner-only account inputs. The integration lead owns the shared roadmap and final integration.

| Role | Responsibility | Deliverable |
|---|---|---|
| Chief of staff / integration lead | Choose the highest-value task, resolve dependencies, maintain status, integrate PRs | One tested change and truthful CEO update |
| Revenue & product | Define the offer, inquiry path, and customer problem; keep scope small | Reviewed offer and acceptance criteria |
| Web engineer | Implement scoped site work with accessible, responsive UI | Branch + tested PR |
| Security engineer | Threat model, review secrets, permissions, DOM, evidence, deployment | Findings with paths/severity/fix; no unbounded audit |
| QA / accessibility | Desktop/mobile, keyboard, links, interactive tools, print, no false confirmations | Evidence and reproducible issues |
| Research / editorial | Verify directory details and claims using official sources | Source URL + date + claim; no fabricated content |
| Business operations | Draft launch checklist, intake/terms requirements, and approved cost proposals | Concrete owner actions, no unauthorized commitments |

## Two-machine protocol

Default device lanes: laptop = Pawsfect Walks / Find Fido / Birdy customer experience; desktop = security, QA, ILL labs and shared infrastructure. Both may inspect anything. The lane is a default, not permission to edit files another task has claimed.

1. Pull/fetch current GitHub state and inspect issues, PRs, STATUS, and ROADMAP.
2. Pick an unclaimed task. Assign one manager and declare exact file ownership/acceptance criteria.
3. Acquire an atomic task lease with `python3 portfolio/claim.py P002 --device desktop`. It creates `claims/P002` only if that remote ref does not exist. A failed claim means choose another task. GitHub issue assignments/comments alone are not a lock.
4. Record the task, device, branch, claimed ref SHA, start time, owned files, and intended checkpoint in the issue. Lease refs are coordination markers, not PR branches. Do not run code from a claim branch as a deployment.
5. Create a branch such as `agent/desktop/P002-mobile-qa`, and a separate Git worktree per writing agent. Each task owns distinct files; the lead owns shared generator/CSS/JS files. Review agents are read-only.
6. Work, test, commit, push, and open a PR. A reviewer checks the scope and tests. No force pushes to default branches; no shared worktree; no blind auto-merge.
7. After merged completion, update the issue and STATE/STATUS, then release the lease using the exact recorded SHA. `portfolio/claim.py --release` uses a compare-and-swap lease and cannot remove a changed claim.
8. If blocked, checkpoint and stop that task; continue a different independent task. Do not silently steal a claim because it looks old. A stale claim requires coordination with the owner; delete only the expected recorded ref, never an arbitrary branch.

A manager may spawn a few bounded supported sub-agents once the task is claimed. Each gets objective, owned paths, excluded paths, acceptance criteria, and handoff format. Do not spawn a large idle team. The manager remains accountable for integration and security. If agent support is unavailable, execute the roles sequentially and say so.

## Checkpoint format

Task ID / device / owner role / branch / commit / claimed-ref SHA / changed paths / passing checks / skipped checks / next exact command or task / blockers / owner inputs. Never include credentials or personal client data. At a context limit, push the work and write this handoff before starting another feature.

## Approval boundaries

Continue authorized reversible implementation, testing, repo writes, fixes and draft PRs. Obtain Jordan's explicit authorization for spending, entity filings, legal agreements, outside messages, collecting sensitive data, new subscriptions, or commitments to customers. Do not bypass platform approval controls. Preserve existing DNS until the production replacement and cutover have been reviewed. This is a business workflow, not a blanket mandate to do anything to increase money.

## Stop condition for a work session

Ship one measurable task or create a complete reviewable result with a precisely identified blocker. Report actual work, tests, PR/deploy links, next task, and owner action. No guaranteed financial outcomes, imaginary staff activity, or claimed background execution.
