# P008 learning labs handoff

Updated: 2026-10-07

## Delivered scope

- Three standard-library-only exercises under `learning-labs/`:
  - a deliberately limited local Linux inventory;
  - a synthetic archive/restore integrity drill; and
  - a deterministic human-review gate evaluator.
- Per-exercise setup, expected outcome, verification, limitations, and cleanup guidance.
- Offline tests and a least-privilege, SHA-pinned GitHub Actions workflow.
- A repository-map link that keeps the learning labs visibly separate from Illnet Rx.

## Boundaries preserved

- No network requests, credentials, package installs, elevated privileges, or external services.
- No remote scanning. The Linux exercise observes only the local machine and does not intentionally collect direct user/host identifiers, addresses, process identities, file contents, environment variables, or secrets. OS and kernel labels can be administrator-customized, so reports must be inspected before sharing.
- Infrastructure and intelligent-workflow inputs are synthetic.
- No changes to Illnet Rx scanner/runtime/downloads, `portfolio/build.py`, `portfolio/sites.json`, shared site assets, production exports, DNS, or held domains.
- The current GitHub Pages site remains an educational review; these source exercises are not a production service or security claim.

## Verification

Run from the repository root:

```bash
python3 -m unittest discover -s learning-labs/tests -v
python3 -m unittest discover -s portfolio -p 'test_*.py' -v
python3 portfolio/build.py --mode preview --output /tmp/illnetwork-p008-preview
python3 portfolio/check.py /tmp/illnetwork-p008-preview
```

## Owner follow-ups

1. Review the exercises and decide which track should receive the next lesson.
2. Keep generated evidence private unless intentionally reviewed for publication.
3. Decide later whether the Pages review should link directly to these repository paths after P009 releases the shared generator; do not collide with the active Birdy claim.

No purchase, entity formation, production deployment, DNS change, insurance assertion, clinical claim, brand clearance, or revenue claim was made.
