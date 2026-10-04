# Decisions — 2026-10-04

- Jordan requested GitHub-backed builds for the active domain portfolio, Actions, resumable AI memory, and scheduled progress.
- All 14 allowed domains have a build. Ten are primary concepts; four are supporting domains. Domains do not imply formed legal entities.
- Existing repositories: `jordanistan/illnetwork`, `spaceghostkilla`, `iamjordanrobison`, `iambirdy`, and `starfieldstudio`.
- The GitHub connector supports writes to existing repositories but does not expose repository creation, Pages administration, DNS, or security-settings administration. New brands live in the `illnetwork/portfolio` source until an owner/admin creates separate repositories if needed. Separate repos are optional for Cloudflare monorepo builds.
- GitHub Pages excludes sites primarily used for commercial transactions or paid SaaS. Its build is strictly an educational review. Production static builds are ready for commercial hosting; Cloudflare is the proposed host because Jordan already uses it. Do not silently change existing DNS.
- The original SpaceGhostKilla branding, research, free downloads, and unreleased-product state are preserved. A service-review page is additive.
- Pawsfect Walks pricing ($22 / 30 minutes, $35 / 60 minutes) is draft pricing. Paid care must wait for verified insurance, service terms, intake, and readiness.
- Initial email inquiries use Jordan's established public professional email; SpaceGhostKilla uses its established routed support address. No domain aliases are invented. Preview builds expose no email capture.
- No fake testimonials, customer counts, revenue, checkout confirmations, automated health recommendations, or marketplace providers.
- The three ILL learning tracks share a single umbrella. Existing Illnet Rx remains a local-first scanner, not an online SaaS.
- Healthy Heart remains an education project and is explicitly not a licensed clinic. Hearty is a general routine planner. Starfield remains a concept pending name clearance and product approval.
- Costs are kept low: Python standard library generator, plain HTML/CSS/JS, no frontend package installation, no new paid services provisioned.

Sources: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits and https://developers.cloudflare.com/pages/configuration/git-integration/ .
