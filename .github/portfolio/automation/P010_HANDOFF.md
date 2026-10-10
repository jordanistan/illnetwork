# P010 ILLNET AI approval pilot handoff

## Delivered scope

`automation-pilot/` is an offline, standard-library demonstration that prepares
a deterministic plan from exact-schema synthetic JSON, records an approve or
reject decision against the plan hash, and verifies that the decision still
matches. It never produces the described business output or executes an
external action.

This task does not modify the `illnet.ai` website or any shared generator/asset.
It does not connect to a model, inbox, customer system, scheduler, payment
processor, deployment, DNS, analytics, or live account.

## Security and privacy boundaries

- synthetic classification is mandatory but self-declared; the best-effort
  filter cannot prove that input is synthetic, secret-free or PII-free;
- unexpected fields, common sensitive names/values, oversized files, traversal,
  nested/hidden output names, symlink ancestors/members and overwrites are rejected;
- outputs are created with mode `0600`;
- every plan stays `pending_human_review`;
- approval means only `approved_for_demo_handoff` and always records
  `live_execution_authorized: false`;
- changing the plan after review invalidates its SHA-256 binding;
- review and verification recompute the plan from the supplied request;
- `reviewer_label` is unauthenticated: the hash binds files for integrity but
  does not prove a person's identity, authorship or non-repudiation;
- the Action is read-only, fully pinned, secret-free and offline after checkout.

## Verification

Run:

```bash
python3 -m unittest discover -s automation-pilot -p 'test_*.py' -v
```

Then run the three README example commands. Also run the existing portfolio test,
preview and 14 separate production-export checks to prove the site artifacts did
not change.

## Future owner gate

Jordan chooses a real workflow only after reviewing employer/outside-work rules,
data ownership, privacy, permissions, vendor terms, operating cost and support
responsibility. A new scoped task must document and test the actual integration.
Never reuse this demo's approval as authority for production access or external
messages.

## Coordination

- Task: P010
- Issue: #64
- Claim: `claims/P010` at `a65e6d7e7c40ec2002ab9b3c256f8f8445ad965f`
- Branch: `codex/p010-approval-pilot-20261010`
- Excluded: shared portfolio generator/assets, native site design, scanner, Birdy
  media, DNS, held domains and unreleased products
