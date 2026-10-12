# P005 commercial hosting preflight

## Boundary

This runbook prepares two revenue-priority inquiry exports for owner-reviewed
commercial staging. It does not connect an account, change DNS, accept payment,
send an inquiry, or declare either business ready.

| Target | Source | Build | Reviewed entry |
|---|---|---|---|
| `pawsfectwalks.com` | `jordanistan/illnetwork` | `python3 portfolio/build.py --mode production --domain pawsfectwalks.com --output <fresh-output>` | `index.html` |
| `spaceghostkilla.com` | preserved native `jordanistan/spaceghostkilla` | `bash scripts/build_production.sh <fresh-output>` | `services.html` |

Do not substitute the central SpaceGhostKilla concept for its native site. Do
not publish Pawsfect care as bookable until its seven operating decisions are
confirmed. GitHub Pages remains the educational review surface.

## What the preflight proves

`portfolio/hosting_preflight.py` verifies the fixed two-target manifest, the
exact reviewed export file set, reviewed inquiry entry point, expected email
recipient and subject, no forms or checkout triggers, no external/inline
scripts, no held-domain references in deployable text, and the required
Cloudflare `_headers` rule. The evidence validator prevents a pending record
from being marked complete and requires distinct root-level HTTPS staging
hosts, a dated full commit SHA, header and inquiry checks, inbox receipt, DNS
snapshot and rollback record before a target can be called verified.

Artifact readiness is not deployment readiness. The committed evidence template
is intentionally `pending` for both targets.

## Owner-authenticated staging sequence

1. Confirm the Pawsfect seven-item launch register and SpaceGhostKilla's
   outside-work, scope, authorization, evidence, terms, capacity and invoicing
   decisions. Hosting an inquiry page does not satisfy those gates.
2. In Cloudflare, create a distinct Git-integrated Pages project for each
   repository. Restrict repository access to what each project needs. Keep the
   production branch disconnected or paused while staging is reviewed.
3. Enter the exact build command above and use the fresh output directory as the
   build output. Do not add secrets; both builds are static.
4. Deploy a preview branch first. Record its HTTPS `*.pages.dev` URL, exact source
   SHA and UTC/local timestamp in a private working copy of
   `P005_EVIDENCE_TEMPLATE.json`.
5. Run the repository artifact preflight and inspect the served response, not
   only the generated files. Confirm HTTP 200, TLS, content type, every required
   response header, no unexpected script, the correct inquiry recipient and the
   no-auto-submit notice.
6. From an owner-controlled mailbox, send a harmless inquiry containing no
   customer, pet, credential or system data. Confirm actual inbox receipt and
   reply routing. Do not publish the test address or message in GitHub.
7. Export or screenshot the current DNS records privately. Preserve MX, TXT,
   DMARC, SPF, DKIM, verification and unrelated records. Record the exact prior
   web record, TTL, rollback owner and rollback steps.
8. Associate the custom domain through the Pages project's **Custom domains**
   flow before changing any web record. Review the exact DNS change Cloudflare
   proposes. Do not manually point a record at Pages first.
9. After explicit owner approval, perform one reviewed cutover at a time. Verify
   HTTPS, headers, entry page, inquiry receipt and existing email immediately.
   Roll back on wrong content, TLS failure, missing headers, mail disruption or
   an unexpected redirect/script.
10. Only after both sites pass should the evidence status become
    `cutover_verified` and `cutover_approved` become true. Pawsfect paid-care and
    SpaceGhostKilla client-acceptance gates remain separate.

Cloudflare documentation checked October 12, 2026:

- <https://developers.cloudflare.com/pages/configuration/git-integration/>
- <https://developers.cloudflare.com/pages/configuration/custom-domains/>
- <https://developers.cloudflare.com/pages/configuration/headers/>

Cloudflare documents that Git integration creates preview deployments for branch
commits, `_headers` in the build output controls static-response headers, and a
custom domain should be associated in Pages before its DNS record is pointed at
the deployment. Recheck those documents and the dashboard prompts at cutover.

## Commands

```bash
python3 -m unittest portfolio.test_hosting_preflight -v
python3 portfolio/hosting_preflight.py manifest
python3 portfolio/hosting_preflight.py evidence

output="$(mktemp -d)/pawsfectwalks.com"
python3 portfolio/build.py --mode production --domain pawsfectwalks.com --output "$output"
python3 portfolio/check.py "$output" --domain pawsfectwalks.com
python3 portfolio/hosting_preflight.py artifact \
  --domain pawsfectwalks.com --artifact "$output"
```

For SpaceGhostKilla, run its native checks, build into a fresh directory, then
point this verifier at that directory with `--domain spaceghostkilla.com`. Never
copy credentials, private evidence, DNS exports or customer messages into the
repository.
