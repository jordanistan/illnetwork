# Task-claim audit

Remote `claims/P###` branches are atomic coordination leases. They are not deployment branches and their age alone never authorizes deletion. `CLAIMS.json` records the reviewed lifecycle state and exact expected SHA for each known lease.

## Safe audit

From an authenticated or read-only checkout:

```bash
git ls-remote origin 'refs/heads/claims/*' > /tmp/portfolio-claim-refs.txt
python3 portfolio/claim_audit.py --refs /tmp/portfolio-claim-refs.txt
```

The auditor performs no network call and no Git mutation. It emits a release command only when all of these are true:

1. the ledger marks the task `release_ready`;
2. the remote task exists;
3. the remote SHA exactly matches the reviewed `expected_sha`; and
4. the task/ref/SHA pass strict allowlists.

An unknown task, changed SHA, missing active lease, or supposedly released task with a remaining ref makes the audit fail. Do not weaken those checks to clear a warning.

## Status meanings

- `active`: a current task owns the lease. Coordinate with its issue owner.
- `retain_owner_blocked`: keep the lease while an owner/admin-only completion step is pending.
- `release_ready`: implementation is integrated and the exact compare-and-swap deletion command may be run from an authenticated checkout.
- `released`: the remote lease must be absent.

After releasing a lease, change its ledger status to `released` and clear `expected_sha` in a reviewed PR. If a release command fails, the ref may have changed: stop and coordinate. Never delete or overwrite the new SHA.

## Boundaries

The ledger is a coordination record, not evidence of deployment, insurance, legal review, brand clearance, customer activity, revenue, or authorization for live work. Keep credentials and private evidence out of this file.

P027 was acquired at `963e492d03fa294bedfea1ffb9effeca858fbdd0` for issue #110. After its reviewed implementation is merged, that exact lease is release-ready; no owner decision or per-engagement authorization is transferred to the lease.
