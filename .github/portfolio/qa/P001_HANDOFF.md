# P001 public review availability handoff

## Delivered subtask

This change adds a bounded verifier for the public educational-review catalog.
It confirms that an approved HTTPS endpoint returns UTF-8 HTML with the exact 14
allowed domain links, the design-review boundary notice and a CSP meta policy.
It rejects form fields, email inquiry links, payment/checkout links, every script
except the exact expected `assets/site.js`, held-domain links, unsafe CSP, base
elements, inline event handlers, resource hints, inert containers, active URL
schemes, and insecure redirects before following them. The sole CSP must be in
the document head. It also bounds ports, content type, encoding and response
size.

The Action runs offline boundary tests on pull requests and matching pushes. Its
strict live probe runs only by manual dispatch. It receives no secrets and has
read-only repository permission.

## Observation — October 11, 2026

From the managed build environment:

- `https://iamjordanrobison.com/domain-previews/review.html` returned HTTPS 200,
  title `Domain studio / All previews`, and all 14 allowed preview links;
- the served mirror included injected Cloudflare Rocket Loader and Cloudflare
  Insights scripts in addition to the expected `assets/site.js`, so the exact
  script-allowlist probe failed;
- `https://ill.network/` and `https://ill.network/review.html` returned 403;
- the `jordanistan.github.io/illnetwork` fallback redirected to HTTP and then
  returned 403 in this environment.

This verifies that the personal-site mirror is reachable and structurally holds
the catalog from this vantage point, but it does not mark the deployment clean.
The unexpected analytics script conflicts with the portfolio's no-tracker and
no-external-script boundary. Do not add it to an allowlist merely to make the
check pass. This result also does not prove every network can reach the mirror,
that the central custom domain is repaired, or that GitHub/Cloudflare settings
are correct. The mirror remains pinned to a reviewed source commit and does not
automatically follow coordinator `main`.

## Owner/admin gate still required

In an owner-authenticated browser, inspect GitHub Settings → Pages for both
repositories and the current Cloudflare DNS/access/bot configuration. Confirm
the intended source, custom domain, Enforce HTTPS state and absence of a competing
deployment. Inspect Cloudflare Web Analytics/Browser Insights and disable the
injected beacon for these no-tracker review pages if that setting is responsible;
verify the served HTML again rather than assuming. Preserve MX/TXT email records
and existing security controls. Do not change DNS or disable access protections
without a reviewed cutover and rollback.

## Verification

```bash
python3 -m unittest portfolio.test_review_probe -v
python3 portfolio/review_probe.py \
  --url https://iamjordanrobison.com/domain-previews/review.html
```

The strict live command currently exits `2` because it detects the injected
Cloudflare Rocket Loader and Insights scripts. That failure is the evidence to resolve, not a
passing deployment claim. Re-run by manual Action dispatch after the owner/admin
configuration review; mark the live boundary verified only when the strict job
passes against served HTML.

Also run the existing portfolio tests, 37-page preview check, all 14 isolated
production export checks, JavaScript syntax check and workflow YAML parse.

## Coordination

- Task: P001 public-verification subtask
- Issue: #34
- Claim: `claims/P001` at `6c67d176b3a23a8eb3a15710a7238c27cb24783e`
- Branch: `codex/p001-review-availability-20261011`
- Excluded: all website design/source, shared generator/assets, scanner/downloads,
  DNS/settings, customer data, inquiry/payment paths and held domains
