# P022 — Pawsfect public launch-boundary audit

## Purpose

The public Pawsfect site must remain visibly prelaunch while P003's seven operating decisions and P015's eight recruiting gates are pending. This audit observes the fixed public root and its one same-origin JavaScript module. It does not change the native site, approve launch, send an inquiry, recruit a worker, or inspect any account.

## Initial observation — October 22, 2026

`https://pawsfectwalks.com/` returned HTTPS 200 from Netlify with HSTS and one local module. The public module still contains recruiting and operating claims that conflict with the canonical pending state, including:

- `Hiring now`, `Apply in minutes`, `Walk dogs, get paid`, and `We bring the bookings`;
- `We're onboarding our first local walkers now` and application mail links;
- broad Austin service zones, `Dog Sitting`, and pickup/return oversight;
- a public `$50` rate while the service/rate decision remains pending;
- no explicit prelaunch statement that the waitlist is not a booking, paid care is unavailable, recruiting is not open, or sensitive details should be kept out of the initial inquiry.
- search/social metadata that says Pawsfect currently provides dog walking and sitting services instead of describing a prelaunch waitlist.

The strict live audit therefore fails by design. This is evidence of a public-boundary mismatch, not evidence of hiring, insurance, service capacity, a functioning booking flow, or customer demand.

## Safe owner sequence

1. Do not accept paid care or worker applications from this public copy while P003/P015 remain pending.
2. Preserve the established visual design. Change only the unsupported operating/recruiting statements in a separately reviewed native-site task.
3. Keep the waitlist inquiry minimal and state that it is not a booking. State that paid care and recruiting are not open. Warn people not to send addresses, access codes, payment details, IDs or medical records in the initial inquiry. Remove the current prompt for `any special needs`; health/care details belong in a later approved intake, not ordinary email.
4. Remove the unapproved rate, broad zones, dog-sitting/pickup scope, hiring, earnings, application, candidate-email, and booking-availability claims, or replace them with clear unavailable/prelaunch language. Merely adding `pending` to a prohibited claim will not pass the audit.
5. Replace the page title and Open Graph title with `Pawsfect Walks | Austin Pre-launch Waitlist`. Replace the description and Open Graph description with `Pawsfect Walks is a pre-launch Austin dog-care concept. Join the waitlist; no booking, paid care, or recruiting is available.` These are narrow audit-boundary strings, not launch approval.
6. Build the native site and run its lint, typecheck, build, audit, artifact and browser checks.
7. Deploy the reviewed commit, then manually run **Pawsfect public boundary audit** and record the passing run in issue #99.
8. Only after the real P003/P015 evidence changes should the verifier boundary be deliberately reviewed; a changed gate never authorizes language automatically.

## Technical boundary

- Zero user-supplied URL input.
- Fixed root, exact same-origin hashed module path, bounded redirects/time/bytes and strict MIME/UTF-8 checks.
- GET requests contain no credential, cookie, referrer, secret, form submission, email, or body.
- Pull requests run deterministic offline fixtures only. Scheduled/manual runs on trusted `main` perform at most two public GETs.
- Bundle substring review detects known drift but cannot prove every rendered JavaScript semantic. A separate browser review remains required after remediation.

No website, design, P003/P015 evidence, shared generator/assets, inbox, DNS, hosting, payment, customer/worker data, scanner, download, held domain, or other task claim changed in P022.

## Remediation verification — October 23, 2026

Native [PR #6](https://github.com/jordanistan/PawfectWalks/pull/6) merged as `987fadf8f6687e154ee0426808bb9a31c6147c04` with the established design preserved. Its pinned Action passed. The public host then served the exact pre-launch metadata and all required waitlist, no-booking, no-paid-care, no-recruiting and initial-inquiry privacy boundaries without the prohibited rate, coverage, sitting, transport or staffing claims.

The local strict probe passed: root 1,039 bytes; module 173,369 bytes; module SHA-256 `48f9cb792c03fef579e894ffc59c7cc5580e62cade5455c31c2aeb4de92c3faf`. The verifier's staffing matcher also gained a regression test so React's internal `.apply(...)` method is not mistaken for a worker application; real application and candidate paths remain rejected.

This completes the public-copy boundary only. P003's seven operating confirmations and P015's eight recruiting gates remain pending, so the site is still a waitlist—not a booking, hiring, dispatch or paid-care authorization.
