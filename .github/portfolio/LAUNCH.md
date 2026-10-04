# Concrete launch requirements

## Review now

1. All five initial PRs are merged and their Pages deployment jobs succeeded; see STATUS/STATE for evidence. The central ill.network URL returned Cloudflare 403 from this environment and GitHub's repository URL redirects to HTTP. This is an owner/admin follow-up (P001, issue #34), not evidence that Cloudflare protections should be disabled.
2. Use the personal site's review mirror as the intended mirror URL (PR #63 deployment succeeded but HTTP returned 404; access still unverified): `https://iamjordanrobison.com/domain-previews/review.html`. It generates all 14 previews from the pinned, previously reviewed ILL source commit. Update the pin deliberately after later source changes; it does not follow mutable main automatically.
3. An owner-authenticated local session should inspect actual Pages custom-domain/HTTPS settings and Cloudflare access/security configuration, then test root and /review.html. Do not guess the cause or disrupt DNS/email. Repository administration is not exposed by this connection.
4. Every preview is public. No private operational documents enter the artifact.

## Production from the same repository

A separate repository per brand is not required. Create one Cloudflare Pages project per primary domain, all connected to `jordanistan/illnetwork`. Root directory: repository root. Production branch: `main`.

| Domain | Build command | Output directory |
|---|---|---|
| pawsfectwalks.com | `python3 portfolio/build.py --mode production --domain pawsfectwalks.com --output _production/pawsfectwalks.com` | `_production/pawsfectwalks.com` |
| spaceghostkilla.com | Use the preserved native site plus its `scripts/build_production.sh` when ready; do not replace research with the suite concept without review | `_production` in native repo |
| iamjordanrobison.com | `python3 portfolio/build.py --mode production --domain iamjordanrobison.com --output _production/iamjordanrobison.com` | `_production/iamjordanrobison.com` |
| find-fido.com | `python3 portfolio/build.py --mode production --domain find-fido.com --output _production/find-fido.com` | `_production/find-fido.com` |
| iambirdy.com | `python3 portfolio/build.py --mode production --domain iambirdy.com --output _production/iambirdy.com` | `_production/iambirdy.com` |
| ill.network | `python3 portfolio/build.py --mode production --domain ill.network --output _production/ill.network` | `_production/ill.network` |
| illnet.ai | `python3 portfolio/build.py --mode production --domain illnet.ai --output _production/illnet.ai` | `_production/illnet.ai` |
| hearty.fit | `python3 portfolio/build.py --mode production --domain hearty.fit --output _production/hearty.fit` | `_production/hearty.fit` |
| healthyheart.clinic | Same pattern with `--domain healthyheart.clinic`; keep education-only | `_production/healthyheart.clinic` |
| starfieldstudio.com | Same pattern with `--domain starfieldstudio.com`; hold commercial launch until clearance | `_production/starfieldstudio.com` |

Supporting domains use the same build pattern: `illnet.net`, `starfieldstudio.shop`, `starfieldstudio.store`, `starfieldstudio.info`. Initially prefer a host-managed permanent redirect to the primary brand, rather than paying for separate applications. Their built pages are reviewable fallback pages.

Add each custom domain through Cloudflare's project UI and follow the exact DNS instructions it returns. Preserve mail-routing MX/TXT records. Verify HTTPS, correct destination, security response headers, and the email link before traffic is directed to the production site. `_headers` applies on Cloudflare static Pages, not automatically on GitHub Pages. The meta CSP is only a partial fallback; framing protection requires host response headers.

## Owner inputs before accepting money

- Pawsfect Walks: verify insurance including care/custody/control coverage, approved service area and availability, intake/meet-and-greet process, handling/transport policy, signed service agreement, cancellation/refund terms, and payment method. Do not represent coverage as active until verified. No door codes in GitHub or initial email.
- SpaceGhostKilla: confirm employer outside-work boundaries, final paid-review scope, written authorization, evidence handling, invoicing/payment method, and client terms. No accreditation claims. Leave Field Manual/KubeScan unreleased until their criteria pass.
- Digital products: verified merchant account, catalog, product files/rights, refund/delivery terms, and a real checkout test. No placeholder purchase button or static order confirmation.
- Find Fido: official sources and dates for each listing; distinguish sponsorship from verification. No user submissions, lost-pet personal data, or marketplace bookings until storage/moderation/security are implemented.
- Starfield: brand clearance, approved artwork rights, real print samples, fulfillment and pricing. No invented inventory.
- Health projects: licensed professional review before health content or clinical services. The present worksheet does not diagnose or recommend care.

## Optional repository split

An owner-authenticated local Codex can use `gh repo create` to create brand repos, then copy the matching static export, shared source, and secure workflows. First inspect whether a repo already exists. Do not recreate the five native repositories or overwrite their histories. Do not put a credential in a shell argument, file, or task prompt. Publish only tested commits with a rollback route.

## Security settings

The workflows add CodeQL and Gitleaks. GitHub native secret scanning, push protection, branch rules and protected environments are account/repository settings and remain **unverified** until an administrator checks them. Enable supported protections and require the build/security checks. A workflow file alone does not prove a successful scan or enforced protection.
