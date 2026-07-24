# BidOps_Final — Backlog

Carried forward from `BidOps_VetrexAi/very_imp/imp_to_add.md`, trimmed to only what's still
unresolved. The two frontend bugs that file originally flagged (`tender_id`/`id` response
contract mismatch, missing explicit analysis-trigger step on the New Tender page) are already
fixed — see `99_DECISIONS_LOG.md` D-143 and the prior session's typechecked fix in
`frontend/src`.

## 1. Document-type taxonomy doesn't match real Indian tender requirements

While prepping the OpenAI Build Week demo, it became clear the document-type taxonomy was
never validated against how real Indian government/PSU tenders actually work — it was
designed early on without first mapping it to real-world tender eligibility requirements.

**What real Indian tenders (GeM, CPPP, state e-procurement) actually ask a bidding company
to submit, by category:**

1. Legal/registration proof — Certificate of Incorporation, PAN, GST registration, Udyam/
   MSME registration (for exemptions/preference).
2. Financial standing — audited financial statements / turnover certificates (usually last
   3 years, CA-certified), bank solvency certificate.
3. Quality/technical certifications — ISO (9001, 27001), CMMI level, sector-specific
   licenses.
4. Past performance / experience — completion certificates or client-issued work orders for
   similar past projects. Usually the single most scrutinized category in evaluation.
5. Manpower / team — CVs of key technical personnel, sometimes with their own individual
   certifications attached.
6. Compliance declarations — no-blacklisting undertaking, litigation history declaration,
   EMD/bid security proof, labour law compliance (PF/ESI registration).

**Current taxonomy** (`certification`, `employee_resume`, `project_record`,
`equipment_record`, `financial_record`, `other`): categories 1–5 above have a reasonable home
(legal/registration docs awkwardly but workably fit under `certification`). Category 6 —
compliance declarations — has no home at all today.

**What to add:** a new document type (or types) for compliance/declaration paperwork — bid
security/EMD proof, no-blacklisting declaration, litigation history declaration, labour
compliance (PF/ESI) documents. These are procedurally different from the other five types:
binary "attached or not" checklist items, not something needing AI-driven structured
extraction or freshness/staleness tracking. Decide during design whether they belong in the
Capability Graph model at all, or need a separate lightweight "checklist" concept. Possibly
split or rename `certification` so GST/PAN/Incorporation-type legal documents don't feel
misfiled under a name that reads as "quality certification" only.

**Status:** postponed, deliberately — see the Technical Debt Register in the migration plan.
Designing this taxonomy *speculatively*, before a real tender's real requirements are in
hand, risks repeating the exact mistake that created this gap in the first place. Pick this
up once a real Track A/B/C pilot customer's actual tender surfaces the concrete need.

## 2. GitHub/Vercel deployment identity mismatch

Hit during OpenAI Build Week deployment: a merge commit combining a commit made locally (via
GitHub Desktop) with a commit made directly on github.com's web editor got blocked by Vercel
with "GitHub could not associate the committer with a GitHub user," and the Hobby plan
couldn't resolve it by adding the committer as a collaborator either. The only thing that
actually worked: a fresh commit made directly through github.com's web editor.

**Root cause:** the local machine's git identity (`git config --global user.email`) doesn't
match the verified email on the GitHub account, so commits pushed from GitHub Desktop/
terminal aren't recognized as coming from an authenticated collaborator.

**Action item:** before connecting `BidOps_Final` to any deployment target, run
`git config --global user.email` and confirm it exactly matches the verified email on the
GitHub account that will own/collaborate on this repo. Fixing this once, up front, avoids
hitting the same deployment block later under real time pressure.

**Status:** nothing to fix yet — `BidOps_Final` has no git remote or deployment target
configured. Execute this check at the start of Milestone 8 (production hardening) or
whenever deployment work actually begins, whichever comes first.
