# Pawsfect offline synthetic launch rehearsal

P016 is a deterministic, offline review tool for the eleven synthetic scenarios named in the native Pawsfect launch-test handoff. It lets a reviewer compare a selected synthetic control with a fixed expected control, then records a separate hash-bound offline review.

It does **not** verify insurance, service area, intake, handling, agreements, cancellation terms, payments, recruiting, inbox delivery, worker readiness or any other launch prerequisite. Every prerequisite is permanently recorded as `not_evaluated_by_p016`. No report or review authorizes launch, booking, dispatch, payment, refunds, recruiting or external actions.

## Frozen source

- Repository: `jordanistan/PawfectWalks`
- Path: `docs/launch/09_Launch_Test_and_Agent_Handoff.md`
- Git blob: `b62e010eedbc42f7d110ff3e903efae15a670e76`

Source changes require an explicit fixture review and code update. The workflow never fetches another repository.

## Trust boundary

- accepts strict UTF-8 JSON no larger than 64 KiB;
- rejects duplicate keys, non-finite numbers, symlink components, traversal, held domains and common sensitive-data patterns;
- accepts only the fixed prerequisite, scenario, variant and control enums;
- hashes both the exact request bytes and its canonical normalized form;
- binds the offline review to the report hash;
- does not authenticate the reviewer: hashes show artifact integrity and binding, not identity, independence, authorship, owner approval or non-repudiation;
- creates new owner-only artifacts and refuses overwrites;
- contains no network, customer, worker, booking, payment or messaging integration.

The example is synthetic. Do not add names, contacts, pet details, addresses, access instructions, payment data, health details or live incident details.

## Run locally

```bash
tmp_dir="$(mktemp -d)"
python3 portfolio/pawsfect_rehearsal.py run \
  .github/portfolio/pawsfect-rehearsal/example.json \
  "$tmp_dir/report.json"
python3 portfolio/pawsfect_rehearsal.py review \
  .github/portfolio/pawsfect-rehearsal/example.json \
  "$tmp_dir/report.json" "$tmp_dir/review.json" \
  --decision accept_offline_result \
  --reason synthetic_controls_match
python3 portfolio/pawsfect_rehearsal.py verify \
  .github/portfolio/pawsfect-rehearsal/example.json \
  "$tmp_dir/report.json" "$tmp_dir/review.json"
rm "$tmp_dir/report.json" "$tmp_dir/review.json"
rmdir "$tmp_dir"
```

An acceptance means only that the submitted synthetic controls match this frozen offline fixture. A mismatch may be recorded only with `reject_offline_result` and one of the fixed rejection reasons.

## Owner handoff before any real pilot

1. Complete P003’s seven owner decisions and retain the real evidence privately.
2. Complete P015 before recruiting. P015 can authorize recruiting only; engagement, hire, assignment, dispatch and paid care require separate lawful owner-reviewed steps plus P003 evidence.
3. Approve versioned policies and rehearse with fictional roles/internal reviewers until actual personnel prerequisites separately pass.
4. Verify the real hosting, inquiry and inbox path under P003/P005; do not use this tool as delivery evidence.
5. Confirm rollback is available, cap the first pilot, confirm every first-pilot client individually, and review the first completed visits before expansion.
6. Record Jordan’s dated go/no-go decision and recheck every gate for every client. Never publish private evidence; publish only approved summaries or hashes if needed.
