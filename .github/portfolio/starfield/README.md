# P011 Starfield release-readiness gate

This is a pending-by-default evidence packet for a future Starfield Studio
product release. It does not clear the name, prove artwork ownership, select a
supplier, approve customer terms, activate checkout or authorize a launch.
The existing native and central website designs remain unchanged.

## Release order

1. **Brand clearance:** retain a qualified trademark professional for the
   proposed name, goods, channels and territories. Record only a non-sensitive
   completion marker here; keep searches and advice private.
2. **Artwork rights:** inventory every design, photograph, font, texture and
   other asset. Record creator, source, license, permitted products/territories
   and any attribution or AI-use terms in a private rights ledger.
3. **Samples and quality:** order physical samples only after Jordan approves
   the spend. Check color, crop, substrate, durability, packaging and defects.
4. **Catalog:** approve exact product names, SKUs, dimensions, variants,
   artwork versions, descriptions and images. Do not imply stock exists.
5. **Fulfillment and shipping:** review provider terms, production locations,
   packaging, tracking, replacement handling, delivery estimates and exit plan.
6. **Pricing and tax:** calculate landed cost, platform/payment fees, shipping,
   refunds and margin; obtain qualified tax guidance for the actual channel.
7. **Customer terms:** obtain a qualified review of terms, privacy, returns,
   refunds, cancellations, damaged orders, support and accessibility.
8. **Commercial hosting:** stage outside the educational GitHub Pages review,
   preserve DNS/email records and verify HTTPS and response headers.
9. **Checkout:** only after gates 1–8, run an owner-controlled low-risk purchase,
   fulfillment, cancellation/refund and support test. Keep order and payment
   evidence out of GitHub.

`release_approved` may become true only when every gate is `verified`, the
release repository, commit and catalog version are fixed, Jordan attests that a
private checkout-test ledger record exists, and he records an approval date no
earlier than the final gate. The release SHA and ledger marker are manual owner
attestations: this offline validator checks their shape and sequence but does
not prove the remote commit or private record exists. Those facts must be
verified separately before release. The validator does not establish that an
evidence claim is true; it prevents incomplete or malformed records from being
presented as complete.

## Official starting points

Checked October 13, 2026:

- [USPTO trademark search](https://www.uspto.gov/trademarks/search) — search
  guidance, not a clearance opinion.
- [U.S. Copyright Office visual arts](https://www.copyright.gov/registration/visual-arts/)
  — registration information, not a substitute for a rights inventory.
- [FTC Mail, Internet, or Telephone Order Merchandise Rule](https://www.ftc.gov/legal-library/browse/rules/mail-internet-or-telephone-order-merchandise-rule)
  — shipping representations, delays and refunds.
- [Texas Comptroller online orders](https://comptroller.texas.gov/taxes/publications/94-171.php)
  — Texas sales-tax starting point for online sellers.

Recheck the official sources and obtain advice appropriate to the actual
products and sales model before relying on them. Do not commit legal advice,
supplier credentials, tax identifiers, addresses, customer information,
payment data, order IDs or private contracts. Public gate notes are fixed
neutral markers; do not replace them with evidence summaries.

## Validation

```bash
python3 -m unittest portfolio.test_starfield_release -v
python3 portfolio/starfield_release.py sources
python3 portfolio/starfield_release.py evidence
```
