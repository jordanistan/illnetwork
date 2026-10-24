# P024 — Pawsfect public inquiry handoff

## Purpose

The public waitlist must open a user-controlled email draft to a reviewed recipient without storing, transmitting or claiming receipt of the visitor's information. This gate inspects the fixed public root and one same-origin JavaScript module. It never sends email, opens an inbox, changes DNS or confirms a booking.

## Observation — October 24, 2026

The live site used `hello@pawsfectwalks.com` for waitlist, partnership, general contact and policy paths. Credential-free Cloudflare DNS-over-HTTPS lookups returned no MX answer for `pawsfectwalks.com`, no root TXT answer and NXDOMAIN for `_dmarc.pawsfectwalks.com`. Those public observations do not establish a functioning mailbox. The canonical portfolio configuration already names `jordan.robison@gmail.com` as the approved public Pawsfect inquiry recipient.

P024 replaces only the native site's recipient text and mailto targets with the already-public approved address. It preserves the visual design, exact waitlist subject, user-initiated email-app behavior, no-storage statement and warning against addresses, access codes, payment details, IDs and medical records.

## Verification boundary

- exact fixed HTTPS root and validated same-origin hashed module;
- only the approved recipient in public mailto routes;
- the placeholder `john@example.com` remains permitted only as the visible email-field example;
- exact waitlist/partnership subjects and privacy/no-storage language;
- no unconfigured alias, form service, background request, browser storage, checkout or booking-confirmation marker;
- PR checks use offline fixtures only; scheduled/manual trusted-main checks perform two bounded credential-free GETs.

## Completion evidence — October 24, 2026

Native [PR #7](https://github.com/jordanistan/PawfectWalks/pull/7) merged as `ea5e02497e9b5d846be3e19e6ab18b68970114e3` after [Action run 40140603830](https://github.com/jordanistan/PawfectWalks/actions/runs/40140603830) passed. After the existing host deployed the change, both bounded public audits passed against root size 1,039 bytes and bundle size 173,376 bytes with SHA-256 `ccf7f50dbcc690e8da20170669b7ef199e81fe240c81729e36623f41fb5c6e7e`.

This proves the reviewed public routes and disclosures are present. It does not prove that a message reaches the inbox.

## Remaining owner acceptance

Jordan must use his own email client to send one harmless test containing no customer, dog, address, access, payment, identity or medical information. Confirm receipt and reply behavior privately, then record only the date, source commit and neutral pass/fail status in GitHub. Do not paste message contents, headers or account details into the repository.

P003's seven operating confirmations and P015's eight recruiting gates remain pending. A working email route does not authorize bookings, recruiting, dispatch, paid care or revenue.
