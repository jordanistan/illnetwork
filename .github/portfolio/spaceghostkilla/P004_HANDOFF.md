# P004 consulting process checkpoint — 2026-10-05

Task / device / role: P004 / cloud / integration lead. Coordinator issue: [#30](https://github.com/jordanistan/illnetwork/issues/30). Native repository: `jordanistan/spaceghostkilla`.

## Delivered scope

Six linked blank Markdown templates in native `docs/consulting/` cover minimal inquiry, qualification, one Entra OR CI/CD evidence-review boundary, explicit technical authority, private evidence handling, report/closeout and owner launch decisions. Native `.github/portfolio/STATUS.md` records local evidence. These are Obsidian-compatible generic templates, not filled customer records or a signed agreement.

Proposed first offer follows the current services design's **from $800 draft pricing**, with final fee/effort/timing by reviewed quote. No fees, availability or booking are approved by the pack. Direct testing, production changes and product releases are excluded. No client data was collected, inquiry sent, permissions created, merchant account opened or invoice issued.

## Branch and coordination

Branch in both repositories: `agent/cloud/P004-consulting-intake-20261005`.

Atomic lease: `claims/P004` at `5d6305a022eb7dcabc89e23c309a03439f5125fa`, acquired 2026-10-05. Existing P003/P009/P013 leases were not touched. Owned files are native `docs/consulting/*.md`, native `.github/portfolio/STATUS.md`, and this coordinator file. Shared generator, scanner, downloads, site behavior, DNS and other active-task files are excluded.

Native base: `3d2d43a7200dff2ad4e763cea1084094e07d001d`; coordinator base: `5d6305a022eb7dcabc89e23c309a03439f5125fa`. Exact new commits/PRs, current-head checks and any merged/deployed results are appended to issue #30 after they are observed. Existing main already has successful native build/Pages/secret/CodeQL evidence, including Pages run `37183147846`; this does not assert the documentation PR is deployed.

## Checks actually performed

- `python3 scripts/check_site.py`: passed.
- `node --check script.js` and `node --check service-assets/site.js`: passed.
- `bash scripts/stage_site.sh <fresh-output>` and `bash scripts/build_production.sh <fresh-output>`: passed.
- Six Markdown files have valid relative document links.
- Both staged artifacts exclude `docs/` and `.github/`.
- Research `index.html`, free Quick Audit PDF and ZIP are byte-identical to native source in both exports.
- Services preview contains no mailto inquiry; production contains the existing `support@spaceghostkilla.com` email-app link, with no automatic send/payment/booking.
- Bounded read-only template review found no material security, scope, privacy or false-launch issue.

No new UI or runtime code was changed. Additional mobile/browser QA, real inbox receipt, actual client permissions, evidence transfer, payment and commercial cutover were not performed. No new automated tests were written for these reversible templates.

## Exact next owner actions

1. Confirm employer outside-work/confidentiality/conflict boundaries privately.
2. Approve one environment/workflow, expertise/capacity, evidence volume, deliverables, revision allowance, dates and final quote.
3. Have the final client commercial terms reviewed; obtain the actual private authorization record for each engagement.
4. Choose and verify restricted evidence transfer/storage, authorized readers, approved tools, incident contact, retention and deletion process.
5. Verify owner-controlled invoicing/payment arrangements privately; no real charge/refund without specific authorization.
6. Verify commercial staging HTTPS/security headers and support-mailbox receipt; review destination/rollback before DNS or hosting changes.

Paid consulting remains gated on these confirmations. Pawsfect Walks remains the highest revenue priority, but its operating inputs and active P003 claim were not bypassed. P001 hosting administration requires owner access; this run did not change it.

## Local task-lease release after merged checkpoint

The connector has no delete-ref capability. An owner-authenticated local session can release only this unchanged lease after the handoff is integrated:

```bash
git push --force-with-lease=refs/heads/claims/P004:5d6305a022eb7dcabc89e23c309a03439f5125fa origin :refs/heads/claims/P004
```

A failed lease means coordinate with the current owner, not delete a changed ref. Acquire a fresh claim before additional P004 writing. Other independent tasks can proceed under their own claims.
