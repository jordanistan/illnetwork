# P015 Pawsfect recruiting-readiness gate

This packet prepares a reviewable process for a future **two-to-three-person
Pawsfect Walks pilot**. It is not a job posting, contractor solicitation,
application form, hiring decision, insurance confirmation or authorization to
recruit. The worker classification remains pending. The existing Pawsfect
website, native launch documents and designs are unchanged.

## Required order

1. **Pilot role scope:** freeze the proposed duties, exclusions, service zone,
   scheduling, training, supervision, equipment, expenses, compensation and
   termination facts. Bind later reviews to that exact commit; this is a facts
   packet, not a classification decision.
2. **Classification review:** obtain project-specific qualified review of the
   frozen facts, including behavioral control, financial control and the
   parties' relationship. Do not choose a label because it appears simpler.
3. **Pay and control terms:** revise and approve the private role policy so its
   actual pay, scheduling, training, supervision, equipment and termination
   terms match the reviewed model.
4. **Insurance:** give the insurer the accurate role model and duties. Obtain
   written confirmation of the required business, worker, care/custody/control
   and any driving or transportation coverage before recruiting or assigning
   care. This repository does not prove coverage.
5. **Screening and consent:** obtain a qualified review of the exact screening
   process. If a third party supplies a background report, use the required
   standalone disclosure, written authorization, notices and dispute process.
   Apply job-related criteria consistently. Keep all candidate data private.
6. **Candidate-data controls:** approve a restricted private system, access
   list, multifactor authentication, retention/deletion rules, incident owner
   and secure reference workflow. GitHub and ordinary email are not approved.
7. **Interview and vetting:** approve the structured scorecard, interviewers,
   evidence standard and private record retention/access rules. Do not collect
   applications through GitHub or the educational Pages preview.
8. **Owner authorization:** Jordan records a final approval only after every
   prior gate is verified. That approval permits only recruiting under
   separately reviewed materials; it does not authorize a hire, assignment,
   booking or paid-care launch.

The validator enforces order and prevents incomplete records from presenting
as approved. It cannot prove that a review, insurance confirmation or private
record exists. Those facts must be independently verified before action.

## Public/private boundary

GitHub may contain only gate status, approved reviewer-role labels, timestamps,
fixed neutral notes and a non-identifying private-ledger marker. Never commit a
candidate's name, contact details, address, date of birth, government or driver
identifier, application, resume, availability, references, screening consent,
background or motor-vehicle result, bank/tax information, interview notes,
score, decision or agreement. Do not put insurer documents, legal advice,
compensation details or signed records here.

## Official starting points

Checked October 15, 2026:

- [Texas Workforce Commission: classifying employees and independent contractors](https://www.twc.texas.gov/programs/unemployment-tax/classifying-employees-independent-contractors)
  — Texas classification starting point; not a classification decision.
- [IRS: independent contractor or employee](https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee)
  — federal tax factors and the right-to-control analysis.
- [FTC: background checks—what employers need to know](https://www.ftc.gov/business-guidance/resources/background-checks-what-employers-need-know)
  — FCRA disclosure, authorization and notice starting point when a reporting
  company is used.
- [EEOC: background checks—what employers need to know](https://www.eeoc.gov/laws/guidance/background-checks-what-employers-need-know)
  — equal-treatment and nondiscrimination guidance.

Recheck current official sources and obtain advice for the actual operating
model before relying on them. This packet is an operational control, not legal,
tax, insurance or employment advice.

## Validation

```bash
python3 -m unittest portfolio.test_pawsfect_recruiting -v
python3 portfolio/pawsfect_recruiting.py sources
python3 portfolio/pawsfect_recruiting.py evidence
```
