# P007 Find Fido dataset handoff

Updated: 2026-10-08

## Scope

The first Austin starter dataset contains four source-checked outings across parks, patio and short-trip categories:

- Red Bud Isle;
- Great Northern Dam Far West Off Leash Area;
- Meanwhile Brewing Company; and
- McKinney Falls State Park.

Every entry records an official government/operator URL, business- or park-level location, dog-policy summary, evidence URL and check date, uncertainty, and an explicit verify-before-visit state.

## Editorial and privacy boundaries

- This is a reviewed source dataset, not a live availability monitor, rating, ranking, recommendation, sponsorship, booking service, or claim that Jordan or Birdy personally visited.
- No user submissions, personal location history, customer/provider data, exact GPS coordinates, phone numbers, email addresses, or marketplace records are stored.
- Official sources can change after the recorded 2026-10-08 check. Every entry tells the reader to verify current rules and access before visiting.
- Austin's October 6, 2026 advisory reported blue-green algae at Red Bud Isle; the dataset links the current algae page and requires a fresh advisory check before water contact.
- The Find Fido design and existing planning-category cards remain unchanged under Jordan's October 8 design-preservation instruction.

## Coordination boundary

P009 owns `portfolio/build.py`, `portfolio/sites.json`, and shared assets. P007 therefore adds only the source dataset, its validation test, and documentation. A later integration lead can expose the dataset after P009 releases those shared paths and Jordan approves any user-interface change.

## Verification

Run from the repository root:

```bash
python3 -m unittest portfolio.test_find_fido_dataset -v
python3 -m unittest discover -s portfolio -p 'test_*.py' -v
python3 portfolio/build.py --mode preview --output /tmp/find-fido-preview
python3 portfolio/check.py /tmp/find-fido-preview
python3 portfolio/build.py --mode production --domain find-fido.com --output /tmp/find-fido-production
python3 portfolio/check.py /tmp/find-fido-production
```

## Owner follow-ups

1. Decide whether these four outings are a suitable first public set.
2. After P009 releases the shared generator, explicitly approve any presentation change before the dataset is added to the site.
3. Recheck each official source immediately before publication and record the new date; do not present the 2026-10-08 review as live availability.

No outside message, purchase, subscription, DNS change, payment feature, user-data collection, booking, or revenue claim was made.
