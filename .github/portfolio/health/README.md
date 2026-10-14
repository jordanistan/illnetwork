# P012 qualified health-content review gate

This packet keeps the existing `healthyheart.clinic` educational worksheet and
`hearty.fit` general routine planner pending until their exact content receives
a qualified review. It organizes evidence; it does not provide medical or legal
advice, verify a reviewer's credentials, turn Healthy Heart into a clinic, or
authorize health-data collection. Both established website designs remain
unchanged.

## Fixed review scope

- **Healthy Heart:** a blank visit-preparation worksheet. It must not present a
  medical practice, clinical service, diagnosis, treatment, appointment,
  telehealth, symptom/record intake, or interpretation of clinician advice.
- **Hearty:** a general lifestyle routine planner. It must not prescribe
  exercise or nutrition, personalize recommendations, assess health, or promise
  health outcomes.
- **Both:** review the whole consumer impression, including the domain and brand
  name, headlines, worksheet labels, calls to action, disclaimers, images and
  generated page. A disclaimer cannot repair a contradictory health claim.

The validator freshly builds preview and production exports for both domains,
checks their strict artifact allowlists, and calculates a deterministic SHA-256
digest over every deployable file. An eventual publication approval is limited
to those four artifact digests and one full source commit SHA. Changes to site
copy, templates, styles, scripts or generated resources invalidate the recorded
digests and require a new review. A digest is a version marker, not proof that
the content is accurate or safe.

## Review order

1. **Content inventory:** Jordan freezes the four exact artifact-tree digests
   and an owner-attested full source SHA and privately records all eight rendered HTML pages
   supplied to the reviewer: `index.html` and `privacy.html` for both domains
   in preview and production modes.
2. **Healthy Heart review:** a qualified, currently licensed health-content
   reviewer reviews the entire education-only experience for inaccurate,
   unsafe, clinical or misleading express and implied claims.
3. **Hearty review:** a qualified, currently licensed health-content reviewer reviews the entire
   general-lifestyle experience for prescriptive, personalized or outcome
   claims and unsafe omissions.
4. **Claims and consumer impression:** the qualified, currently licensed reviewer
   checks claim substantiation, conspicuous boundaries and the net impression.
5. **Data flow:** an owner technical reviewer verifies that worksheet entries
   stay in the browser, are not transmitted or persistently stored by the site,
   and that there is no upload, account, intake, appointment or analytics path.
6. **Owner publication:** only after gates 1–5, Jordan approves the exact
   repository commit and content digest for the two existing educational pages.

Reviewer-role labels are owner attestations. This offline validator cannot
prove qualifications, inspect private review notes, or verify that a remote
commit exists or produced the artifacts. The artifact digests—not the attested
SHA—are the machine-checked content binding. Jordan must verify that the SHA and
artifacts correspond, plus the reviewer's active professional healthcare
license and current standing, jurisdiction, relevant consumer-health and
patient-education competence, conflicts, and scope of practice. Retain that
review, source snapshot and approval privately.
Names, license numbers, medical details, reviewer contact information and
private advice do not belong in GitHub.

`publication_approved` may become true only when every gate is `verified`, the
owner approval date is not earlier than the final gate, and the recorded source
SHA and all four artifact-tree digests match the exact current build. Approval
covers only the existing educational pages.
It does not approve clinical services, intake, health claims, individualized
advice, products, payment, commercial launch or future content.

## Official starting points

Checked October 14, 2026:

- [FTC Health Products Compliance Guidance](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)
  — review express and implied claims and the whole consumer impression; health
  claims require appropriate substantiation. This is guidance, not an approval.
- [FDA General Wellness: Policy for Low Risk Devices](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices)
  — a starting point for distinguishing general wellness from diagnosis,
  treatment and other disease-related functions. Obtain advice for any changed
  functionality or intended use.
- [HHS Health Literacy Online](https://odphp.health.gov/healthliteracyonline/)
  — people-first, understandable, accessible content and content-governance
  practices.
- [HHS HIPAA Privacy Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html)
  — official scope and safeguards reference. It does not establish that this
  project is a covered entity or authorize collection of health information.

Recheck these official sources and obtain review appropriate to the actual
content before relying on them. Public gate notes are fixed neutral markers;
do not replace them with review summaries.

## Validation

```bash
python3 -m unittest portfolio.test_health_review -v
python3 portfolio/health_review.py sources
python3 portfolio/health_review.py evidence
python3 portfolio/health_review.py content
```
